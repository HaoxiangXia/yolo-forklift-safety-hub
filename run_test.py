from __future__ import annotations

import os
import json
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


class DemoHeartbeatKeeper:
    def __init__(self, device_ids: list[str], interval_sec: float = 3.0) -> None:
        self.device_ids = device_ids
        self.interval_sec = interval_sec
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                conn = sqlite3.connect(ROOT / "alarm.db")
                try:
                    cursor = conn.cursor()
                    cursor.executemany(
                        """
                        UPDATE devices
                        SET last_seen = ?, update_time = ?, online_status = 1
                        WHERE device_id = ?
                        """,
                        [(now_str, now_str, device_id)
                         for device_id in self.device_ids],
                    )
                    conn.commit()
                finally:
                    conn.close()
            except Exception:
                pass
            self._stop_event.wait(self.interval_sec)


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
            "pos_x": 320.0,
            "pos_y": 240.0,
        },
        {
            "device_id": "FORK-002",
            "alarm_status": 1,
            "error_count": 8,
            "boot_time": (now - timedelta(hours=4, minutes=20)).strftime("%Y-%m-%d %H:%M:%S"),
            "last_seen": now.strftime("%Y-%m-%d %H:%M:%S"),
            "online_status": 1,
            "update_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "pos_x": 1320.0,
            "pos_y": 320.0,
        },
        {
            "device_id": "FORK-003",
            "alarm_status": 0,
            "error_count": 5,
            "boot_time": (now - timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S"),
            "last_seen": (now - timedelta(minutes=18)).strftime("%Y-%m-%d %H:%M:%S"),
            "online_status": 0,
            "update_time": (now - timedelta(minutes=18)).strftime("%Y-%m-%d %H:%M:%S"),
            "pos_x": 540.0,
            "pos_y": 780.0,
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
            None,
            None,
            0,
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
        ((now - timedelta(minutes=18)).isoformat() + "Z", "ERROR", "device.status.offline_marked",
         "ops", "FORK-003", "Device marked offline after timeout", {"timeout_sec": 10}),
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
    heartbeat_keeper = DemoHeartbeatKeeper(["FORK-001", "FORK-002"])
    try:
        backup = backup_database()
        rebuild_demo_database()

        app_host = "127.0.0.1"
        app_port = find_available_port(app_host)
        service_url = f"http://localhost:{app_port}"

        heartbeat_keeper.start()
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

        code = runner.monitor()
        runner.stop()
        return code
    except Exception as exc:
        print(f"运行失败: {exc}")
        runner.stop()
        return 1
    finally:
        heartbeat_keeper.stop()
        if backup is not None:
            try:
                restore_database(backup)
            except Exception as exc:
                print(f"恢复数据库失败: {exc}")


if __name__ == "__main__":
    raise SystemExit(main())
