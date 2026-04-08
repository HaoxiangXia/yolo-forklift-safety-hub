"""
SQLite 数据访问与表初始化 - 增加趋势统计功能
"""

import sqlite3
import json
import os
import base64
from datetime import datetime, timedelta

from config import DB_PATH, HISTORY_LIMIT, TREND_LIMIT, DB_BUSY_TIMEOUT_MS, LLM_RETRY_INTERVAL_SEC

# 图片存储目录
IMAGE_DIR = "images/alarms"
IMAGE_BASE_DIR = os.path.abspath("images")
os.makedirs(IMAGE_DIR, exist_ok=True)

def _is_safe_image_path(image_path):
    if not image_path or not isinstance(image_path, str):
        return False
    lower = image_path.lower()
    if lower.startswith("http://") or lower.startswith("https://"):
        return False
    abs_path = os.path.abspath(image_path)
    if abs_path == IMAGE_BASE_DIR:
        return True
    return abs_path.startswith(IMAGE_BASE_DIR + os.sep)


def get_db_connection():
    """获取数据库连接，设置 row_factory 为 Row 以便通过键名访问"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # 使用 WAL 让读写并发更友好，读请求不会轻易被写事务阻塞。
    conn.execute("PRAGMA journal_mode=WAL;")
    # 设置 busy_timeout 后，遇到锁竞争会等待一段时间，降低 database is locked 概率。
    conn.execute(f"PRAGMA busy_timeout={DB_BUSY_TIMEOUT_MS};")
    return conn


def init_db():
    """初始化数据库表结构"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 报警明细表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alarms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT,
            alarm INTEGER,
            timestamp TEXT
        )
    """)

    # 设备状态表
    cursor.execute("""
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
    """)

    # 数据库迁移：添加缺失的列（如果表已存在）
    try:
        cursor.execute("ALTER TABLE devices ADD COLUMN pos_x REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # 列已存在
    try:
        cursor.execute("ALTER TABLE devices ADD COLUMN pos_y REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # 列已存在

    # 业务日志表 (由 V1 引入)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS biz_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT,
            level TEXT,
            event TEXT,
            device_id TEXT,
            message TEXT,
            extra TEXT
        )
    """)

    # 报警图片表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alarm_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT,
            image_path TEXT,
            timestamp TEXT
        )
    """)

    # 报警图片描述列（异步生成）
    try:
        cursor.execute("ALTER TABLE alarm_images ADD COLUMN description TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE alarm_images ADD COLUMN description_status TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE alarm_images ADD COLUMN description_model TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE alarm_images ADD COLUMN description_updated_at TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE alarm_images ADD COLUMN description_error TEXT")
    except sqlite3.OperationalError:
        pass

    # 报警会话表（记录每次报警的起止时间和时长）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alarm_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT,
            duration_sec REAL,
            status INTEGER DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_alarm_sessions_device
        ON alarm_sessions(device_id, status)
    """)

    # 添加唯一索引，防止重复记录
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_alarm_unique
        ON alarm_images(device_id, timestamp)
    """)
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_alarm_unique_path
        ON alarm_images(device_id, image_path)
    """)

    conn.commit()
    conn.close()


def update_device_data(device_id, alarm, mqtt_timestamp=None):
    """
    更新设备数据并插入历史记录。
    返回变更状态字典，供日志使用。
    mqtt_timestamp: MQTT payload中的时间戳（叉车端上报）
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    changed = {}

    # 1. 插入历史明细表
    cursor.execute(
        """
        INSERT INTO alarms (device_id, alarm, timestamp)
        VALUES (?, ?, ?)
    """,
        (device_id, alarm, now_str),
    )

    # 2. 更新设备实时状态逻辑
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
            # 创建报警会话记录
            session_start = mqtt_timestamp if mqtt_timestamp else now_str
            cursor.execute(
                """
                INSERT INTO alarm_sessions (device_id, start_time, status)
                VALUES (?, ?, 0)
            """,
                (device_id, session_start),
            )

        if old_alarm == 1 and alarm == 0:
            changed["alarm_cleared"] = True
            # 结束最近的未结束会话
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
                end_time = mqtt_timestamp if mqtt_timestamp else now_str
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
            INSERT INTO devices (device_id, alarm_status, error_count, boot_time, last_seen, online_status, update_time)
            VALUES (?, ?, ?, ?, ?, 1, ?)
        """,
            (device_id, alarm, (1 if alarm == 1 else 0), now_str, now_str, now_str),
        )
        changed["online_marked"] = True
        if alarm == 1:
            changed["alarm_raised"] = True
            session_start = mqtt_timestamp if mqtt_timestamp else now_str
            cursor.execute(
                """
                INSERT INTO alarm_sessions (device_id, start_time, status)
                VALUES (?, ?, 0)
            """,
                (device_id, session_start),
            )

    conn.commit()
    conn.close()
    return changed


def set_device_offline(device_id):
    """标记设备为离线"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE devices SET online_status = 0 WHERE device_id = ?", (device_id,)
    )
    conn.commit()
    conn.close()


def get_all_devices():
    """获取所有设备的当前状态列表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM devices")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_latest_data_with_stats():
    """获取所有设备数据及统计信息"""
    devices = get_all_devices()
    # 活跃报警会话映射: device_id -> start_time
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT device_id, start_time
        FROM alarm_sessions
        WHERE status = 0
    """)
    active_rows = cursor.fetchall()
    conn.close()
    active_map = {row["device_id"]: row["start_time"] for row in active_rows}
    now_dt = datetime.now()
    for dev in devices:
        dev_id = dev.get("device_id")
        start_time = active_map.get(dev_id)
        if dev.get("alarm_status") == 1 and start_time:
            try:
                start_dt = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
                dev["alarm_start_time"] = start_time
                dev["current_duration_sec"] = max(
                    0, (now_dt - start_dt).total_seconds()
                )
            except Exception:
                dev["alarm_start_time"] = start_time
                dev["current_duration_sec"] = None
        else:
            dev["alarm_start_time"] = None
            dev["current_duration_sec"] = None
    total = len(devices)
    online = sum(1 for d in devices if d["online_status"] == 1)
    alarm = sum(
        1 for d in devices if d["alarm_status"] == 1 and d["online_status"] == 1
    )

    return {
        "devices": devices,
        "stats": {"total": total, "online": online, "alarm": alarm},
    }


def get_device_history_raw(device_id, limit=HISTORY_LIMIT):
    """获取原始最近记录，用于列表展示"""
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
    return [dict(row) for row in rows]


def get_device_alarm_trend(device_id, limit=TREND_LIMIT):
    """
    报警次数趋势聚合统计：
    1. 取最近 limit 条记录
    2. 按分钟分组统计 alarm=1 的次数
    3. 返回 labels(分钟) 和 counts(次数)
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # 子查询取最近 limit 条，外部查询进行分钟级聚合
    query = """
        SELECT 
            strftime('%H:%M', timestamp) as minute,
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
    """
    cursor.execute(query, (device_id, limit))
    rows = cursor.fetchall()
    conn.close()

    labels = [row["minute"] for row in rows]
    counts = [row["alarm_count"] for row in rows]

    return {"labels": labels, "counts": counts}


def get_device_alarm_hourly_today(device_id):
    """
    统计设备“当天每小时报警次数”（本地时间）。
    Get per-hour alarm counts for the current local day.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            strftime('%H', timestamp) AS hour,
            COUNT(*) AS alarm_count
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

    # 预置 00-23 点，保证前端始终拿到完整 24 小时数组。
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
    """
    缁熻鎵€鏈夎澶囩殑鈥滀粖澶? / 鏄ㄥぉ姣忓皬鏃舵姤璀︽鏁扳€濓紙鏈湴鏃堕棿锛夈€?
    Return 24-hour arrays for today and yesterday (local time) across all devices.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # 浠婃棩姣忓皬鏃?
    cursor.execute(
        """
        SELECT
            strftime('%H', timestamp) AS hour,
            COUNT(*) AS alarm_count
        FROM alarms
        WHERE alarm = 1
          AND date(timestamp) = date('now', 'localtime')
        GROUP BY hour
        ORDER BY hour ASC
    """
    )
    today_rows = cursor.fetchall()

    # 鏄ㄥぉ姣忓皬鏃?
    cursor.execute(
        """
        SELECT
            strftime('%H', timestamp) AS hour,
            COUNT(*) AS alarm_count
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

    for row in today_rows:
        try:
            hour_idx = int(row["hour"])
        except (TypeError, ValueError):
            continue
        if 0 <= hour_idx <= 23:
            today_counts[hour_idx] = int(row["alarm_count"] or 0)

    for row in yesterday_rows:
        try:
            hour_idx = int(row["hour"])
        except (TypeError, ValueError):
            continue
        if 0 <= hour_idx <= 23:
            yesterday_counts[hour_idx] = int(row["alarm_count"] or 0)

    return {
        "labels": labels,
        "today_counts": today_counts,
        "yesterday_counts": yesterday_counts,
    }


def get_alarm_trend_multi_device(range_type, device_ids):
    """
    多设备趋势聚合（alarm=1 次数）：
    - day: 当天 0-23 点
    - week: 最近 7 天（含今天）
    - month: 最近 30 天（含今天）

    返回：
      {
        "labels": [...],
        "series": { "<device_id>": [..counts..], ... }
      }
    """
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
            SELECT
                device_id,
                strftime('%H', timestamp) AS hour,
                COUNT(*) AS alarm_count
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
        for row in rows:
            device_id = row["device_id"]
            if device_id not in series:
                continue
            try:
                hour_idx = int(row["hour"])
            except (TypeError, ValueError):
                continue
            if 0 <= hour_idx <= 23:
                series[device_id][hour_idx] = int(row["alarm_count"] or 0)

        conn.close()
        return {"labels": labels, "series": series}

    if range_type == "week":
        days = 7
    else:
        days = 30

    # 最近 N 天（含今天）
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days - 1)
    date_keys = [
        (start_date + timedelta(days=offset)).strftime("%Y-%m-%d")
        for offset in range(days)
    ]
    labels = [
        (start_date + timedelta(days=offset)).strftime("%m-%d") for offset in range(days)
    ]

    for device_id in device_ids:
        series[device_id] = [0 for _ in range(days)]

    cursor.execute(
        f"""
        SELECT
            device_id,
            date(timestamp) AS day,
            COUNT(*) AS alarm_count
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
        device_id = row["device_id"]
        if device_id not in series:
            continue
        day = row["day"]
        idx = index_by_day.get(day)
        if idx is None:
            continue
        series[device_id][idx] = int(row["alarm_count"] or 0)

    return {"labels": labels, "series": series}


def save_alarm_image(device_id, image_path, timestamp):
    """保存报警图片记录到数据库"""
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
    """保存报警图片描述"""
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
    """记录报警图片描述失败"""
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
    """获取待生成/可重试的报警图片记录"""
    conn = get_db_connection()
    cursor = conn.cursor()
    retry_before = datetime.now() - timedelta(seconds=LLM_RETRY_INTERVAL_SEC)
    retry_before_str = retry_before.strftime("%Y-%m-%d %H:%M:%S")
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
    return [dict(row) for row in rows]


def get_device_images(device_id, limit=20):
    """获取设备的报警图片列表"""
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
    return [dict(row) for row in rows]


def get_latest_image(device_id):
    """获取设备的最新报警图片"""
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
    """
    保存 base64 编码的图片到文件系统
    :param device_id: 设备ID
    :param base64_data: base64 编码的图片数据
    :param timestamp: 时间戳字符串
    :return: 保存的文件路径
    """
    try:
        # 解析 data URL 格式 (data:image/jpeg;base64,...)
        if "," in base64_data:
            header, base64_data = base64_data.split(",", 1)

        # 解码 base64
        image_bytes = base64.b64decode(base64_data)

        # 生成文件名
        safe_timestamp = timestamp.replace(":", "-").replace(" ", "_")
        filename = f"{device_id}_{safe_timestamp}.jpg"
        filepath = os.path.join(IMAGE_DIR, filename)

        # 写入文件
        with open(filepath, "wb") as f:
            f.write(image_bytes)

        # 保存到数据库
        save_alarm_image(device_id, filepath, timestamp)

        return filepath
    except Exception as e:
        print(f"[错误] 保存报警图片失败: {e}")
        return None


def init_device_positions():
    """初始化设备位置（随机生成）"""
    import random

    conn = get_db_connection()
    cursor = conn.cursor()

    # 获取所有设备
    cursor.execute("SELECT device_id FROM devices")
    devices = cursor.fetchall()

    for dev in devices:
        device_id = dev["device_id"]
        # 检查是否已有位置
        cursor.execute(
            "SELECT pos_x, pos_y FROM devices WHERE device_id = ?", (device_id,)
        )
        row = cursor.fetchone()
        if row and (row["pos_x"] is None or row["pos_x"] == 0):
            # 随机生成位置
            pos_x = random.uniform(0, 1920)
            pos_y = random.uniform(0, 1080)
            cursor.execute(
                "UPDATE devices SET pos_x = ?, pos_y = ? WHERE device_id = ?",
                (pos_x, pos_y, device_id),
            )

    conn.commit()
    conn.close()


def update_device_position(device_id, pos_x, pos_y):
    """更新设备位置"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE devices SET pos_x = ?, pos_y = ? WHERE device_id = ?",
        (pos_x, pos_y, device_id),
    )
    conn.commit()
    conn.close()


def get_all_devices_with_positions():
    """获取所有设备及其位置"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT device_id, alarm_status, online_status, pos_x, pos_y, last_seen
        FROM devices
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_recent_alarms(limit=5):
    """获取最近报警事件（关联图片）"""
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
    return [dict(row) for row in rows]


def get_alarm_sessions(device_id, limit=20):
    """获取设备的报警会话记录，包含时长信息"""
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
    return [dict(row) for row in rows]


def get_active_alarm_session(device_id):
    """获取设备当前正在进行的报警会话"""
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
    """获取报警时长统计：平均时长、最大时长、总时长"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            COUNT(*) as total_sessions,
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
    if row:
        return {
            "total_sessions": row["total_sessions"] or 0,
            "avg_duration": round(row["avg_duration"], 2) if row["avg_duration"] else 0,
            "max_duration": row["max_duration"] or 0,
            "total_duration": row["total_duration"] or 0,
        }
    return {
        "total_sessions": 0,
        "avg_duration": 0,
        "max_duration": 0,
        "total_duration": 0,
    }
