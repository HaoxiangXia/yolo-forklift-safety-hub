"""SQLite repository helpers."""

from __future__ import annotations

import base64
import os
import random
import sqlite3
from datetime import datetime, timedelta

from config import (
    DB_BUSY_TIMEOUT_MS,
    DB_PATH,
    HISTORY_LIMIT,
    LLM_RETRY_INTERVAL_SEC,
    TREND_LIMIT,
)
from backend.paths import ALARMS_IMAGE_DIR, IMAGES_DIR

ALARMS_IMAGE_DIR.mkdir(parents=True, exist_ok=True)


def _rows_to_dicts(rows):
    return [dict(row) for row in rows]


def is_safe_image_path(image_path: str) -> bool:
    if not image_path or not isinstance(image_path, str):
        return False
    lower = image_path.lower()
    if lower.startswith("http://") or lower.startswith("https://"):
        return False
    abs_path = os.path.abspath(image_path)
    base_dir = str(IMAGES_DIR.resolve())
    if abs_path == base_dir:
        return True
    return abs_path.startswith(base_dir + os.sep)


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute(f"PRAGMA busy_timeout={DB_BUSY_TIMEOUT_MS};")
    return conn


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS alarms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT,
            alarm INTEGER,
            timestamp TEXT
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT UNIQUE,
            alarm_status INTEGER DEFAULT 0,
            error_count INTEGER DEFAULT 0,
            boot_time TEXT,
            last_seen TEXT,
            online_status INTEGER DEFAULT 0,
            update_time TEXT,
            pos_x REAL DEFAULT 0,
            pos_y REAL DEFAULT 0
        )
        """
    )
    for stmt in (
        "ALTER TABLE devices ADD COLUMN pos_x REAL DEFAULT 0",
        "ALTER TABLE devices ADD COLUMN pos_y REAL DEFAULT 0",
    ):
        try:
            cursor.execute(stmt)
        except sqlite3.OperationalError:
            pass

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS biz_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT,
            level TEXT,
            event TEXT,
            device_id TEXT,
            message TEXT,
            extra TEXT
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS alarm_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT,
            image_path TEXT,
            timestamp TEXT
        )
        """
    )
    for stmt in (
        "ALTER TABLE alarm_images ADD COLUMN description TEXT",
        "ALTER TABLE alarm_images ADD COLUMN description_status TEXT",
        "ALTER TABLE alarm_images ADD COLUMN description_model TEXT",
        "ALTER TABLE alarm_images ADD COLUMN description_updated_at TEXT",
        "ALTER TABLE alarm_images ADD COLUMN description_error TEXT",
    ):
        try:
            cursor.execute(stmt)
        except sqlite3.OperationalError:
            pass

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS alarm_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT,
            duration_sec REAL,
            status INTEGER DEFAULT 0
        )
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_alarm_sessions_device
        ON alarm_sessions(device_id, status)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_alarm_unique
        ON alarm_images(device_id, timestamp)
        """
    )
    cursor.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_alarm_unique_path
        ON alarm_images(device_id, image_path)
        """
    )
    conn.commit()
    conn.close()


def update_device_data(device_id, alarm, mqtt_timestamp=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    changed = {}
    cursor.execute(
        """
        INSERT INTO alarms (device_id, alarm, timestamp)
        VALUES (?, ?, ?)
        """,
        (device_id, alarm, now_str),
    )
    cursor.execute(
        "SELECT alarm_status, online_status, error_count, boot_time FROM devices WHERE device_id = ?",
        (device_id,),
    )
    row = cursor.fetchone()
    if row:
        old_alarm = row["alarm_status"]
        old_online = row["online_status"]
        error_count = row["error_count"]
        boot_time = row["boot_time"]
        if old_online == 0:
            boot_time = now_str
            changed["online_marked"] = True
        if old_alarm == 0 and alarm == 1:
            error_count += 1
            changed["alarm_raised"] = True
            cursor.execute(
                """
                INSERT INTO alarm_sessions (device_id, start_time, status)
                VALUES (?, ?, 0)
                """,
                (device_id, mqtt_timestamp or now_str),
            )
        if old_alarm == 1 and alarm == 0:
            changed["alarm_cleared"] = True
            cursor.execute(
                """
                SELECT id, start_time FROM alarm_sessions
                WHERE device_id = ? AND status = 0
                ORDER BY id DESC LIMIT 1
                """,
                (device_id,),
            )
            active_session = cursor.fetchone()
            if active_session:
                end_time = mqtt_timestamp or now_str
                start_dt = datetime.strptime(
                    active_session["start_time"], "%Y-%m-%d %H:%M:%S"
                )
                end_dt = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
                duration = (end_dt - start_dt).total_seconds()
                cursor.execute(
                    """
                    UPDATE alarm_sessions
                    SET end_time = ?, duration_sec = ?, status = 1
                    WHERE id = ?
                    """,
                    (end_time, duration, active_session["id"]),
                )
        cursor.execute(
            """
            UPDATE devices SET
                alarm_status = ?,
                error_count = ?,
                boot_time = ?,
                last_seen = ?,
                online_status = 1,
                update_time = ?
            WHERE device_id = ?
            """,
            (alarm, error_count, boot_time, now_str, now_str, device_id),
        )
    else:
        cursor.execute(
            """
            INSERT INTO devices
                (device_id, alarm_status, error_count, boot_time, last_seen, online_status, update_time)
            VALUES (?, ?, ?, ?, ?, 1, ?)
            """,
            (device_id, alarm, 1 if alarm == 1 else 0, now_str, now_str, now_str),
        )
        changed["online_marked"] = True
        if alarm == 1:
            changed["alarm_raised"] = True
            cursor.execute(
                """
                INSERT INTO alarm_sessions (device_id, start_time, status)
                VALUES (?, ?, 0)
                """,
                (device_id, mqtt_timestamp or now_str),
            )
    conn.commit()
    conn.close()
    return changed


def set_device_offline(device_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE devices SET online_status = 0 WHERE device_id = ?", (device_id,))
    conn.commit()
    conn.close()


def get_all_devices():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM devices")
    rows = cursor.fetchall()
    conn.close()
    return _rows_to_dicts(rows)


def get_latest_data_with_stats():
    devices = get_all_devices()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT device_id, start_time
        FROM alarm_sessions
        WHERE status = 0
        """
    )
    active_rows = cursor.fetchall()
    conn.close()
    active_map = {row["device_id"]: row["start_time"] for row in active_rows}
    now_dt = datetime.now()
    for dev in devices:
        start_time = active_map.get(dev.get("device_id"))
        if dev.get("alarm_status") == 1 and start_time:
            try:
                start_dt = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
                dev["alarm_start_time"] = start_time
                dev["current_duration_sec"] = max(0, (now_dt - start_dt).total_seconds())
            except Exception:
                dev["alarm_start_time"] = start_time
                dev["current_duration_sec"] = None
        else:
            dev["alarm_start_time"] = None
            dev["current_duration_sec"] = None
    total = len(devices)
    online = sum(1 for d in devices if d["online_status"] == 1)
    alarm = sum(1 for d in devices if d["alarm_status"] == 1 and d["online_status"] == 1)
    return {"devices": devices, "stats": {"total": total, "online": online, "alarm": alarm}}


def get_device_history_raw(device_id, limit=HISTORY_LIMIT):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT alarm, timestamp
        FROM alarms
        WHERE device_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
        """,
        (device_id, limit),
    )
    rows = cursor.fetchall()
    conn.close()
    return _rows_to_dicts(rows)


def get_device_alarm_trend(device_id, limit=TREND_LIMIT):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT strftime('%H:%M', timestamp) as minute,
               SUM(CASE WHEN alarm = 1 THEN 1 ELSE 0 END) as alarm_count
        FROM (
            SELECT alarm, timestamp
            FROM alarms
            WHERE device_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        )
        GROUP BY minute
        ORDER BY minute ASC
        """,
        (device_id, limit),
    )
    rows = cursor.fetchall()
    conn.close()
    return {
        "labels": [row["minute"] for row in rows],
        "counts": [row["alarm_count"] for row in rows],
    }


def get_device_alarm_hourly_today(device_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT strftime('%H', timestamp) AS hour, COUNT(*) AS alarm_count
        FROM alarms
        WHERE device_id = ?
          AND alarm = 1
          AND date(timestamp) = date('now', 'localtime')
        GROUP BY hour
        ORDER BY hour ASC
        """,
        (device_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    labels = [f"{h:02d}:00" for h in range(24)]
    counts = [0 for _ in range(24)]
    for row in rows:
        try:
            hour_idx = int(row["hour"])
        except (TypeError, ValueError):
            continue
        if 0 <= hour_idx <= 23:
            counts[hour_idx] = int(row["alarm_count"] or 0)
    return {"labels": labels, "counts": counts}


def get_alarm_hourly_today_yesterday():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT strftime('%H', timestamp) AS hour, COUNT(*) AS alarm_count
        FROM alarms
        WHERE alarm = 1
          AND date(timestamp) = date('now', 'localtime')
        GROUP BY hour
        ORDER BY hour ASC
        """
    )
    today_rows = cursor.fetchall()
    cursor.execute(
        """
        SELECT strftime('%H', timestamp) AS hour, COUNT(*) AS alarm_count
        FROM alarms
        WHERE alarm = 1
          AND date(timestamp) = date('now', 'localtime', '-1 day')
        GROUP BY hour
        ORDER BY hour ASC
        """
    )
    yesterday_rows = cursor.fetchall()
    conn.close()
    labels = [f"{h:02d}:00" for h in range(24)]
    today_counts = [0 for _ in range(24)]
    yesterday_counts = [0 for _ in range(24)]
    for rows, counts in ((today_rows, today_counts), (yesterday_rows, yesterday_counts)):
        for row in rows:
            try:
                hour_idx = int(row["hour"])
            except (TypeError, ValueError):
                continue
            if 0 <= hour_idx <= 23:
                counts[hour_idx] = int(row["alarm_count"] or 0)
    return {"labels": labels, "today_counts": today_counts, "yesterday_counts": yesterday_counts}


def get_alarm_trend_multi_device(range_type, device_ids):
    if not device_ids:
        return {"labels": [], "series": {}}
    range_type = (range_type or "day").lower()
    if range_type not in ("day", "week", "month"):
        range_type = "day"
    conn = get_db_connection()
    cursor = conn.cursor()
    placeholders = ",".join(["?"] * len(device_ids))
    series = {device_id: [] for device_id in device_ids}
    if range_type == "day":
        labels = [f"{h}:00" for h in range(24)]
        for device_id in device_ids:
            series[device_id] = [0 for _ in range(24)]
        cursor.execute(
            f"""
            SELECT device_id, strftime('%H', timestamp) AS hour, COUNT(*) AS alarm_count
            FROM alarms
            WHERE alarm = 1
              AND device_id IN ({placeholders})
              AND date(timestamp) = date('now', 'localtime')
            GROUP BY device_id, hour
            ORDER BY device_id, hour ASC
            """,
            tuple(device_ids),
        )
        rows = cursor.fetchall()
        conn.close()
        for row in rows:
            try:
                hour_idx = int(row["hour"])
            except (TypeError, ValueError):
                continue
            if 0 <= hour_idx <= 23:
                series[row["device_id"]][hour_idx] = int(row["alarm_count"] or 0)
        return {"labels": labels, "series": series}
    days = 7 if range_type == "week" else 30
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days - 1)
    date_keys = [(start_date + timedelta(days=offset)).strftime("%Y-%m-%d") for offset in range(days)]
    labels = [(start_date + timedelta(days=offset)).strftime("%m-%d") for offset in range(days)]
    for device_id in device_ids:
        series[device_id] = [0 for _ in range(days)]
    cursor.execute(
        f"""
        SELECT device_id, date(timestamp) AS day, COUNT(*) AS alarm_count
        FROM alarms
        WHERE alarm = 1
          AND device_id IN ({placeholders})
          AND date(timestamp) >= ?
        GROUP BY device_id, day
        ORDER BY device_id, day ASC
        """,
        tuple(device_ids) + (start_date.strftime("%Y-%m-%d"),),
    )
    rows = cursor.fetchall()
    conn.close()
    index_by_day = {d: i for i, d in enumerate(date_keys)}
    for row in rows:
        idx = index_by_day.get(row["day"])
        if idx is not None:
            series[row["device_id"]][idx] = int(row["alarm_count"] or 0)
    return {"labels": labels, "series": series}


def save_alarm_image(device_id, image_path, timestamp):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR IGNORE INTO alarm_images
            (device_id, image_path, timestamp, description_status)
        VALUES (?, ?, ?, ?)
        """,
        (device_id, image_path, timestamp, "pending"),
    )
    cursor.execute(
        """
        UPDATE alarm_images
        SET description_status = 'pending'
        WHERE image_path = ?
          AND (description_status IS NULL OR description_status = '')
        """,
        (image_path,),
    )
    conn.commit()
    conn.close()


def mark_alarm_image_description(image_id, description, model_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        """
        UPDATE alarm_images
        SET description = ?,
            description_status = 'done',
            description_model = ?,
            description_updated_at = ?,
            description_error = NULL
        WHERE id = ?
        """,
        (description, model_name, now_str, image_id),
    )
    conn.commit()
    conn.close()


def mark_alarm_image_failed(image_id, error_msg, model_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        """
        UPDATE alarm_images
        SET description_status = 'failed',
            description_model = ?,
            description_updated_at = ?,
            description_error = ?
        WHERE id = ?
        """,
        (model_name, now_str, error_msg, image_id),
    )
    conn.commit()
    conn.close()


def get_pending_alarm_images(limit=10):
    conn = get_db_connection()
    cursor = conn.cursor()
    retry_before_str = (datetime.now() - timedelta(seconds=LLM_RETRY_INTERVAL_SEC)).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        """
        SELECT id, device_id, image_path, timestamp, description_status, description_updated_at
        FROM alarm_images
        WHERE description_status IS NULL
           OR description_status = 'pending'
           OR (description_status = 'failed' AND (description_updated_at IS NULL OR description_updated_at < ?))
        ORDER BY id ASC
        LIMIT ?
        """,
        (retry_before_str, limit),
    )
    rows = cursor.fetchall()
    conn.close()
    return _rows_to_dicts(rows)


def get_device_images(device_id, limit=20):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, image_path, timestamp,
               description, description_status, description_model, description_updated_at
        FROM alarm_images
        WHERE device_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
        """,
        (device_id, limit),
    )
    rows = cursor.fetchall()
    conn.close()
    return _rows_to_dicts(rows)


def get_latest_image(device_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT image_path, timestamp,
               description, description_status, description_model, description_updated_at
        FROM alarm_images
        WHERE device_id = ?
        ORDER BY timestamp DESC
        LIMIT 1
        """,
        (device_id,),
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def save_base64_image(device_id, base64_data, timestamp):
    try:
        if "," in base64_data:
            _, base64_data = base64_data.split(",", 1)
        image_bytes = base64.b64decode(base64_data)
        safe_timestamp = timestamp.replace(":", "-").replace(" ", "_")
        filename = f"{device_id}_{safe_timestamp}.jpg"
        filepath = ALARMS_IMAGE_DIR / filename
        filepath.write_bytes(image_bytes)
        save_alarm_image(device_id, str(filepath), timestamp)
        return str(filepath)
    except Exception:
        return None


def init_device_positions():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT device_id FROM devices")
    devices = cursor.fetchall()
    for dev in devices:
        device_id = dev["device_id"]
        cursor.execute("SELECT pos_x, pos_y FROM devices WHERE device_id = ?", (device_id,))
        row = cursor.fetchone()
        if row and (row["pos_x"] is None or row["pos_x"] == 0):
            cursor.execute(
                "UPDATE devices SET pos_x = ?, pos_y = ? WHERE device_id = ?",
                (random.uniform(0, 1920), random.uniform(0, 1080), device_id),
            )
    conn.commit()
    conn.close()


def update_device_position(device_id, pos_x, pos_y):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE devices SET pos_x = ?, pos_y = ? WHERE device_id = ?", (pos_x, pos_y, device_id))
    conn.commit()
    conn.close()


def get_all_devices_with_positions():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT device_id, alarm_status, online_status, pos_x, pos_y, last_seen, error_count, boot_time, update_time
        FROM devices
        """
    )
    rows = cursor.fetchall()
    conn.close()
    return _rows_to_dicts(rows)


def get_recent_alarms(limit=5):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT a.id, a.device_id, a.timestamp, a.alarm,
               (SELECT image_path FROM alarm_images ai
                WHERE ai.device_id = a.device_id
                ORDER BY ai.timestamp DESC LIMIT 1) as image_path,
               (SELECT description FROM alarm_images ai
                WHERE ai.device_id = a.device_id
                ORDER BY ai.timestamp DESC LIMIT 1) as image_description,
               (SELECT description_status FROM alarm_images ai
                WHERE ai.device_id = a.device_id
                ORDER BY ai.timestamp DESC LIMIT 1) as image_description_status
        FROM alarms a
        WHERE a.alarm = 1
        ORDER BY a.timestamp DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = cursor.fetchall()
    conn.close()
    return _rows_to_dicts(rows)


def get_alarm_sessions(device_id, limit=20):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, device_id, start_time, end_time, duration_sec, status
        FROM alarm_sessions
        WHERE device_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (device_id, limit),
    )
    rows = cursor.fetchall()
    conn.close()
    return _rows_to_dicts(rows)


def get_active_alarm_session(device_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, device_id, start_time, end_time, duration_sec, status
        FROM alarm_sessions
        WHERE device_id = ? AND status = 0
        ORDER BY id DESC
        LIMIT 1
        """,
        (device_id,),
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_alarm_duration_stats(device_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT COUNT(*) as total_sessions,
               AVG(duration_sec) as avg_duration,
               MAX(duration_sec) as max_duration,
               SUM(duration_sec) as total_duration
        FROM alarm_sessions
        WHERE device_id = ? AND status = 1
        """,
        (device_id,),
    )
    row = cursor.fetchone()
    conn.close()
    if not row:
        return {"total_sessions": 0, "avg_duration": 0, "max_duration": 0, "total_duration": 0}
    return {
        "total_sessions": row["total_sessions"] or 0,
        "avg_duration": round(row["avg_duration"], 2) if row["avg_duration"] else 0,
        "max_duration": row["max_duration"] or 0,
        "total_duration": row["total_duration"] or 0,
    }
