from __future__ import annotations

import os
import json
import math
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import webbrowser
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import urlopen

import socketio

import db

ROOT = Path(__file__).resolve().parent
DB_FILES = ("alarm.db", "alarm.db-shm", "alarm.db-wal")


@dataclass
class DatabaseBackup:
    backup_dir: Path
    had_original: bool


class ProcessRunner:
    def __init__(self) -> None:
        self.process: subprocess.Popen[str] | None = None

    def start(self, script: str, extra_env: dict[str, str] | None = None) -> None:
        env = os.environ.copy()
        if extra_env:
            env.update(extra_env)
        self.process = subprocess.Popen(
            [sys.executable, script],
            cwd=ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        thread = threading.Thread(target=self._stream_output, daemon=True)
        thread.start()

    def _stream_output(self) -> None:
        if self.process is None or self.process.stdout is None:
            return
        for line in self.process.stdout:
            print(f"[APP] {line}", end="")

    def stop(self) -> None:
        if self.process is None:
            return
        if self.process.poll() is None:
            print("正在停止 APP...")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print("APP 未在超时时间内退出，执行强制终止。")
                self.process.kill()

    def monitor(self) -> int:
        if self.process is None:
            return 1
        try:
            while True:
                return_code = self.process.poll()
                if return_code is not None:
                    print(f"APP 已退出，返回码: {return_code}")
                    return return_code
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\n检测到 Ctrl + C，准备退出...")
            return 0


@dataclass(frozen=True)
class AlarmTrigger:
    zone: str
    x_min: float
    x_max: float
    y_min: float
    y_max: float

    def contains(self, pos_x: float, pos_y: float) -> bool:
        return self.x_min <= pos_x <= self.x_max and self.y_min <= pos_y <= self.y_max


@dataclass(frozen=True)
class DemoVehicle:
    device_id: str
    route: tuple[tuple[float, float], ...]
    step_px: float
    offset: int = 0
    alarm_trigger: AlarmTrigger | None = None


DEMO_ALARM_IMAGE_URL = "images/alarms/FORK-003_20260408_003836.png"
DEMO_ALARM_DESCRIPTION = "演示预设图片：FORK-001 行驶到装卸区固定风险点，触发人车距离过近报警。"
DEMO_VEHICLES = (
    DemoVehicle(
        device_id="FORK-001",
        route=(
            (435, 55),
            (435, 505),
            (695, 505),
            (915, 505),
            (1010, 505),
            (1010, 380),
            (1010, 215),
            (1010, 95),
            (1120, 95),
            (1010, 95),
            (1010, 505),
            (435, 505),
        ),
        step_px=4.0,
        alarm_trigger=AlarmTrigger("主通道固定风险点", 880, 950, 480, 530),
    ),
    DemoVehicle(
        device_id="FORK-002",
        route=(
            (305, 520),
            (435, 520),
            (435, 635),
            (435, 735),
            (435, 635),
            (435, 520),
        ),
        step_px=3.8,
        offset=70,
    ),
    DemoVehicle(
        device_id="FORK-003",
        route=(
            (1010, 95),
            (1135, 95),
            (1135, 150),
            (1010, 150),
            (1010, 300),
            (1010, 505),
            (1010, 300),
            (1010, 150),
        ),
        step_px=3.5,
        offset=120,
    ),
)
DEMO_DEVICE_IDS = tuple(vehicle.device_id for vehicle in DEMO_VEHICLES)


class FixedPathDemoPlayer:
    """Drive all forklifts through fixed smooth demo routes."""

    def __init__(
        self,
        service_url: str,
        frame_interval_sec: float = 0.2,
    ) -> None:
        self.service_url = service_url
        self.frame_interval_sec = frame_interval_sec
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._socket = socketio.Client(reconnection=True)
        self._tracks = {
            vehicle.device_id: self._build_track(vehicle.route, vehicle.step_px)
            for vehicle in DEMO_VEHICLES
        }
        self._alarm_states = {vehicle.device_id: 0 for vehicle in DEMO_VEHICLES}
        self._tick = 0

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name="fixed-demo-player", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        with suppress(Exception):
            self._socket.disconnect()

    def _run(self) -> None:
        self._connect_socket()
        self._alarm_states = self._load_alarm_states()
        print("仿真模式已启动：三辆叉车在线，按厂区道路闭环匀速移动。")
        while not self._stop_event.is_set():
            devices, status_changed = self._advance_frame()
            self._broadcast_update(devices, status_changed)
            self._tick += 1
            self._stop_event.wait(self.frame_interval_sec)

    def _connect_socket(self) -> None:
        for _ in range(20):
            if self._stop_event.is_set():
                return
            try:
                self._socket.connect(self.service_url, transports=["polling"])
                return
            except Exception:
                self._stop_event.wait(0.5)
        print("[DEMO] Socket.IO 连接失败，页面可能需要手动刷新才能看到最新位置。")

    def _build_track(
        self,
        route: tuple[tuple[float, float], ...],
        step_px: float,
    ) -> tuple[tuple[float, float], ...]:
        points: list[tuple[float, float]] = []
        for index, start in enumerate(route):
            end = route[(index + 1) % len(route)]
            distance = math.dist(start, end)
            steps = max(1, round(distance / step_px))
            for step in range(steps):
                t = step / steps
                points.append((
                    start[0] + (end[0] - start[0]) * t,
                    start[1] + (end[1] - start[1]) * t,
                ))
        return tuple(points)

    def _load_alarm_states(self) -> dict[str, int]:
        conn = sqlite3.connect(ROOT / "alarm.db")
        try:
            cursor = conn.cursor()
            cursor.execute(
                f"""
                SELECT device_id, alarm_status
                FROM devices
                WHERE device_id IN ({','.join(['?'] * len(DEMO_DEVICE_IDS))})
                """,
                DEMO_DEVICE_IDS,
            )
            states = {row[0]: int(row[1] or 0) for row in cursor.fetchall()}
            return {device_id: states.get(device_id, 0) for device_id in DEMO_DEVICE_IDS}
        finally:
            conn.close()

    def _advance_frame(self) -> tuple[list[dict], bool]:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        devices = []
        status_changed = False

        for vehicle in DEMO_VEHICLES:
            track = self._tracks[vehicle.device_id]
            pos_x, pos_y = track[(self._tick + vehicle.offset) % len(track)]
            alarm = 1 if vehicle.alarm_trigger and vehicle.alarm_trigger.contains(pos_x, pos_y) else 0
            if self._alarm_states.get(vehicle.device_id, 0) != alarm:
                self._record_alarm_transition(vehicle, alarm, pos_x, pos_y, now_str)
                self._alarm_states[vehicle.device_id] = alarm
                status_changed = True
            devices.append(
                {
                    "device_id": vehicle.device_id,
                    "alarm_status": alarm,
                    "online_status": 1,
                    "pos_x": round(pos_x, 1),
                    "pos_y": round(pos_y, 1),
                    "last_seen": now_str,
                    "update_time": now_str,
                }
            )

        self._write_frame(devices, now_str)
        return devices, status_changed

    def _write_frame(self, devices: list[dict], now_str: str) -> None:
        conn = sqlite3.connect(ROOT / "alarm.db")
        try:
            cursor = conn.cursor()
            cursor.executemany(
                """
                UPDATE devices
                SET pos_x = ?,
                    pos_y = ?,
                    alarm_status = ?,
                    online_status = 1,
                    last_seen = ?,
                    update_time = ?
                WHERE device_id = ?
                """,
                [
                    (
                        device["pos_x"],
                        device["pos_y"],
                        device["alarm_status"],
                        now_str,
                        now_str,
                        device["device_id"],
                    )
                    for device in devices
                ],
            )
            conn.commit()
        finally:
            conn.close()

    def _record_alarm_transition(
        self,
        vehicle: DemoVehicle,
        alarm: int,
        pos_x: float,
        pos_y: float,
        now_str: str,
    ) -> None:
        conn = sqlite3.connect(ROOT / "alarm.db")
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT error_count, boot_time FROM devices WHERE device_id = ?", (vehicle.device_id,))
            row = cursor.fetchone()
            error_count = int(row[0] or 0) if row else 0
            boot_time = row[1] if row else now_str

            cursor.execute(
                "INSERT INTO alarms (device_id, alarm, timestamp) VALUES (?, ?, ?)",
                (vehicle.device_id, alarm, now_str),
            )
            if alarm == 1:
                zone = vehicle.alarm_trigger.zone if vehicle.alarm_trigger else "固定风险点"
                print(f"[DEMO] {vehicle.device_id} 到达{zone}，触发报警")
                error_count += 1
                cursor.execute(
                    "INSERT INTO alarm_sessions (device_id, start_time, status) VALUES (?, ?, 0)",
                    (vehicle.device_id, now_str),
                )
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO alarm_images (
                        device_id, image_path, timestamp, description,
                        description_status, description_model,
                        description_updated_at, description_error
                    ) VALUES (?, ?, ?, ?, 'done', 'demo-fixture', ?, NULL)
                    """,
                    (
                        vehicle.device_id,
                        DEMO_ALARM_IMAGE_URL,
                        now_str,
                        DEMO_ALARM_DESCRIPTION,
                        now_str,
                    )
                )
            else:
                print(f"[DEMO] {vehicle.device_id} 离开固定风险点，报警解除")
                cursor.execute(
                    """
                    SELECT id, start_time
                    FROM alarm_sessions
                    WHERE device_id = ? AND status = 0
                    ORDER BY id DESC LIMIT 1
                    """,
                    (vehicle.device_id,),
                )
                active_session = cursor.fetchone()
                if active_session:
                    start_dt = datetime.strptime(active_session[1], "%Y-%m-%d %H:%M:%S")
                    end_dt = datetime.strptime(now_str, "%Y-%m-%d %H:%M:%S")
                    duration = max(0.0, (end_dt - start_dt).total_seconds())
                    cursor.execute(
                        """
                        UPDATE alarm_sessions
                        SET end_time = ?, duration_sec = ?, status = 1
                        WHERE id = ?
                        """,
                        (now_str, duration, active_session[0]),
                    )

            cursor.execute(
                """
                UPDATE devices
                SET alarm_status = ?,
                    error_count = ?,
                    boot_time = ?,
                    online_status = 1,
                    last_seen = ?,
                    update_time = ?,
                    pos_x = ?,
                    pos_y = ?
                WHERE device_id = ?
                """,
                (alarm, error_count, boot_time, now_str, now_str, pos_x, pos_y, vehicle.device_id),
            )
            conn.commit()
        finally:
            conn.close()

    def _broadcast_update(self, devices: list[dict], status_changed: bool) -> None:
        if not self._socket.connected:
            return
        try:
            self._socket.emit(
                "edge_node_update",
                {
                    "mode": "demo",
                    "devices": devices,
                    "status_changed": status_changed,
                    "image_url": DEMO_ALARM_IMAGE_URL if status_changed else None,
                },
            )
        except Exception:
            pass


def find_available_port(host: str = "127.0.0.1") -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def backup_database() -> DatabaseBackup:
    backup_dir = Path(tempfile.mkdtemp(prefix="forklift-demo-db-"))
    had_original = False
    for name in DB_FILES:
        src = ROOT / name
        if src.exists():
            had_original = True
            shutil.copy2(src, backup_dir / name)
    return DatabaseBackup(backup_dir=backup_dir, had_original=had_original)


def remove_database_files() -> None:
    for name in DB_FILES:
        with suppress(FileNotFoundError):
            (ROOT / name).unlink()


def restore_database(backup: DatabaseBackup) -> None:
    try:
        remove_database_files()
        if backup.had_original:
            for name in DB_FILES:
                src = backup.backup_dir / name
                if src.exists():
                    shutil.copy2(src, ROOT / name)
    finally:
        shutil.rmtree(backup.backup_dir, ignore_errors=True)


def ensure_demo_assets() -> tuple[str, str]:
    primary = ROOT / "images" / "alarms" / "FORK-003_20260408_003836.png"
    secondary = ROOT / "images" / "alarms" / "MANUAL-TEST_20260408_002811.png"
    if not primary.exists() or not secondary.exists():
        raise FileNotFoundError("缺少演示图片资源")
    return (
        "images/alarms/FORK-003_20260408_003836.png",
        "images/alarms/MANUAL-TEST_20260408_002811.png",
    )


def ensure_frontend_build() -> None:
    index_file = ROOT / "frontend" / "dist" / "index.html"
    if index_file.exists():
        return
    raise FileNotFoundError(
        "缺少前端构建产物：frontend/dist/index.html\n"
        "请先执行：\n"
        "  cd frontend\n"
        "  npm install\n"
        "  npm run build\n"
        "  cd .."
    )


def rebuild_demo_database() -> None:
    image_primary, image_secondary = ensure_demo_assets()
    remove_database_files()
    db.init_db()

    now = datetime.now().replace(second=0, microsecond=0)
    today = now.replace(hour=8, minute=0)
    yesterday = today - timedelta(days=1)
    week_anchor = today - timedelta(days=4)

    devices = [
        {
            "device_id": "FORK-001",
            "alarm_status": 0,
            "error_count": 3,
            "boot_time": (now - timedelta(hours=6)).strftime("%Y-%m-%d %H:%M:%S"),
            "last_seen": (now - timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S"),
            "online_status": 1,
            "update_time": (now - timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S"),
            "pos_x": 435.0,
            "pos_y": 55.0,
        },
        {
            "device_id": "FORK-002",
            "alarm_status": 0,
            "error_count": 8,
            "boot_time": (now - timedelta(hours=4, minutes=20)).strftime("%Y-%m-%d %H:%M:%S"),
            "last_seen": now.strftime("%Y-%m-%d %H:%M:%S"),
            "online_status": 1,
            "update_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "pos_x": 305.0,
            "pos_y": 520.0,
        },
        {
            "device_id": "FORK-003",
            "alarm_status": 0,
            "error_count": 5,
            "boot_time": (now - timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S"),
            "last_seen": now.strftime("%Y-%m-%d %H:%M:%S"),
            "online_status": 1,
            "update_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "pos_x": 1010.0,
            "pos_y": 95.0,
        },
    ]

    alarm_rows = [
        ("FORK-001", 1, (now - timedelta(hours=3, minutes=25)
                         ).strftime("%Y-%m-%d %H:%M:%S")),
        ("FORK-001", 0, (now - timedelta(hours=3, minutes=12)
                         ).strftime("%Y-%m-%d %H:%M:%S")),
        ("FORK-001", 1, (today + timedelta(hours=2, minutes=15)
                         ).strftime("%Y-%m-%d %H:%M:%S")),
        ("FORK-001", 0, (today + timedelta(hours=2, minutes=26)
                         ).strftime("%Y-%m-%d %H:%M:%S")),
        ("FORK-002", 1, (today + timedelta(hours=1, minutes=5)
                         ).strftime("%Y-%m-%d %H:%M:%S")),
        ("FORK-002", 0, (today + timedelta(hours=1, minutes=18)
                         ).strftime("%Y-%m-%d %H:%M:%S")),
        ("FORK-002", 1, (today + timedelta(hours=4, minutes=10)
                         ).strftime("%Y-%m-%d %H:%M:%S")),
        ("FORK-002", 1, (now - timedelta(minutes=22)).strftime("%Y-%m-%d %H:%M:%S")),
        ("FORK-002", 1, (now - timedelta(minutes=8)).strftime("%Y-%m-%d %H:%M:%S")),
        ("FORK-003", 1, (yesterday + timedelta(hours=3,
         minutes=40)).strftime("%Y-%m-%d %H:%M:%S")),
        ("FORK-003", 0, (yesterday + timedelta(hours=3,
         minutes=56)).strftime("%Y-%m-%d %H:%M:%S")),
        ("FORK-003", 1, (week_anchor + timedelta(hours=1,
         minutes=25)).strftime("%Y-%m-%d %H:%M:%S")),
        ("FORK-003", 0, (week_anchor + timedelta(hours=1,
         minutes=45)).strftime("%Y-%m-%d %H:%M:%S")),
    ]

    image_rows = [
        (
            "FORK-001",
            image_secondary,
            (now - timedelta(hours=3, minutes=24)).strftime("%Y-%m-%d %H:%M:%S"),
            "通道转角处视线受阻",
            "done",
            "gpt-4.1-mini",
            (now - timedelta(hours=3, minutes=23)).strftime("%Y-%m-%d %H:%M:%S"),
            None,
        ),
        (
            "FORK-002",
            image_primary,
            (now - timedelta(minutes=8)).strftime("%Y-%m-%d %H:%M:%S"),
            "行人低头搬运未注意叉车",
            "done",
            "gpt-4.1-mini",
            (now - timedelta(minutes=7)).strftime("%Y-%m-%d %H:%M:%S"),
            None,
        ),
        (
            "FORK-003",
            image_primary,
            (yesterday + timedelta(hours=3, minutes=40)
             ).strftime("%Y-%m-%d %H:%M:%S"),
            "货物遮挡导致注意力不足",
            "done",
            "gpt-4.1-mini",
            (yesterday + timedelta(hours=3, minutes=41)
             ).strftime("%Y-%m-%d %H:%M:%S"),
            None,
        ),
    ]

    session_rows = [
        (
            "FORK-001",
            (now - timedelta(hours=3, minutes=25)).strftime("%Y-%m-%d %H:%M:%S"),
            (now - timedelta(hours=3, minutes=12)).strftime("%Y-%m-%d %H:%M:%S"),
            780.0,
            1,
        ),
        (
            "FORK-001",
            (today + timedelta(hours=2, minutes=15)).strftime("%Y-%m-%d %H:%M:%S"),
            (today + timedelta(hours=2, minutes=26)).strftime("%Y-%m-%d %H:%M:%S"),
            660.0,
            1,
        ),
        (
            "FORK-002",
            (today + timedelta(hours=1, minutes=5)).strftime("%Y-%m-%d %H:%M:%S"),
            (today + timedelta(hours=1, minutes=18)).strftime("%Y-%m-%d %H:%M:%S"),
            780.0,
            1,
        ),
        (
            "FORK-002",
            (now - timedelta(minutes=22)).strftime("%Y-%m-%d %H:%M:%S"),
            (now - timedelta(minutes=12)).strftime("%Y-%m-%d %H:%M:%S"),
            600.0,
            1,
        ),
        (
            "FORK-003",
            (yesterday + timedelta(hours=3, minutes=40)
             ).strftime("%Y-%m-%d %H:%M:%S"),
            (yesterday + timedelta(hours=3, minutes=56)
             ).strftime("%Y-%m-%d %H:%M:%S"),
            960.0,
            1,
        ),
    ]

    log_rows = [
        ((now - timedelta(minutes=40)).isoformat() + "Z", "INFO", "system.demo.seeded",
         "ops", None, "Loaded fixed demo dataset", {"mode": "presentation"}),
        ((now - timedelta(minutes=32)).isoformat() + "Z", "INFO", "device.status.online",
         "biz", "FORK-001", "Device heartbeat received", {"zone": "A区"}),
        ((now - timedelta(minutes=22)).isoformat() + "Z", "WARNING", "device.alarm.raised",
         "biz", "FORK-002", "Pedestrian close to forklift", {"zone": "B区"}),
        ((now - timedelta(minutes=21)).isoformat() + "Z", "INFO", "llm.image.analysis.generated",
         "biz", "FORK-002", "AI generated alarm summary", {"summary": "行人低头搬运未注意叉车"}),
        ((now - timedelta(minutes=18)).isoformat() + "Z", "INFO", "device.status.online",
         "biz", "FORK-003", "Device heartbeat received", {"zone": "C区"}),
        ((now - timedelta(minutes=12)).isoformat() + "Z", "WARNING", "auth.failed.ws", "sec",
         None, "Socket client connected without token in demo mode", {"path": "/socket.io/"}),
        ((now - timedelta(minutes=6)).isoformat() + "Z", "INFO", "socket.broadcast.position_update",
         "ops", None, "Position update emitted", {"devices": 3}),
    ]

    conn = sqlite3.connect(ROOT / "alarm.db")
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS all_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT,
                level TEXT,
                event TEXT,
                category TEXT,
                device_id TEXT,
                message TEXT,
                extra TEXT
            )
            """
        )
        cursor.execute("DELETE FROM alarm_sessions")
        cursor.execute("DELETE FROM alarm_images")
        cursor.execute("DELETE FROM alarms")
        cursor.execute("DELETE FROM devices")
        cursor.execute("DELETE FROM biz_logs")
        cursor.execute("DELETE FROM all_logs")

        cursor.executemany(
            """
            INSERT INTO devices (
                device_id, alarm_status, error_count, boot_time,
                last_seen, online_status, update_time, pos_x, pos_y
            ) VALUES (
                :device_id, :alarm_status, :error_count, :boot_time,
                :last_seen, :online_status, :update_time, :pos_x, :pos_y
            )
            """,
            devices,
        )
        cursor.executemany(
            "INSERT INTO alarms (device_id, alarm, timestamp) VALUES (?, ?, ?)",
            alarm_rows,
        )
        cursor.executemany(
            """
            INSERT INTO alarm_images (
                device_id, image_path, timestamp, description,
                description_status, description_model, description_updated_at, description_error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            image_rows,
        )
        cursor.executemany(
            """
            INSERT INTO alarm_sessions (
                device_id, start_time, end_time, duration_sec, status
            ) VALUES (?, ?, ?, ?, ?)
            """,
            session_rows,
        )
        cursor.executemany(
            """
            INSERT INTO all_logs (ts, level, event, category, device_id, message, extra)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [(ts, level, event, category, device_id, message, json.dumps(extra, ensure_ascii=False))
             for ts, level, event, category, device_id, message, extra in log_rows],
        )
        conn.commit()
    finally:
        conn.close()


def wait_for_server(url: str, timeout_sec: float = 20.0) -> bool:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            with urlopen(url, timeout=1.5) as response:
                if 200 <= response.status < 500:
                    return True
        except Exception:
            time.sleep(0.25)
    return False


def main() -> int:
    if not (ROOT / "app.py").exists():
        print("未找到文件：app.py")
        return 1

    backup = None
    runner = ProcessRunner()
    demo_player: FixedPathDemoPlayer | None = None
    try:
        ensure_frontend_build()
        backup = backup_database()
        rebuild_demo_database()

        app_host = "127.0.0.1"
        app_port = find_available_port(app_host)
        service_url = f"http://localhost:{app_port}"

        runner.start(
            "app.py",
            {
                "APP_HOST": app_host,
                "APP_PORT": str(app_port),
                "OFFLINE_TIMEOUT_SEC": "7200",
                "POSITION_MOVE_RANGE": "0",
                "POSITION_UPDATE_INTERVAL_SEC": "86400",
            },
        )
        if not wait_for_server(service_url + "/"):
            print("服务启动失败")
            runner.stop()
            return 1

        print(service_url)
        with suppress(Exception):
            webbrowser.open(service_url + "/", new=2, autoraise=True)

        demo_player = FixedPathDemoPlayer(
            service_url,
            frame_interval_sec=float(os.getenv("DEMO_FRAME_INTERVAL_SEC", "0.2")),
        )
        demo_player.start()

        code = runner.monitor()
        demo_player.stop()
        demo_player = None
        runner.stop()
        return code
    except Exception as exc:
        print(f"运行失败: {exc}")
        if demo_player is not None:
            demo_player.stop()
            demo_player = None
        runner.stop()
        return 1
    finally:
        if demo_player is not None:
            demo_player.stop()
        if backup is not None:
            try:
                restore_database(backup)
            except Exception as exc:
                print(f"恢复数据库失败: {exc}")


if __name__ == "__main__":
    raise SystemExit(main())
