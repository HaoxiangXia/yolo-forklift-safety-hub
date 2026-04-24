"""
一键联调脚本：同时启动 app.py 与 publish_test.py

使用方法：
    python run_test.py

退出：
    Ctrl + C
"""

from __future__ import annotations

import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class ProcessPairRunner:
    def __init__(self) -> None:
        self.processes: list[tuple[str, subprocess.Popen[str]]] = []

    def start(self, name: str, script: str) -> None:
        process = subprocess.Popen(
            [sys.executable, script],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        self.processes.append((name, process))
        thread = threading.Thread(
            target=self._stream_output,
            args=(name, process),
            daemon=True,
        )
        thread.start()

    @staticmethod
    def _stream_output(name: str, process: subprocess.Popen[str]) -> None:
        if process.stdout is None:
            return
        for line in process.stdout:
            print(f"[{name}] {line}", end="")

    def stop_all(self) -> None:
        for name, process in self.processes:
            if process.poll() is None:
                print(f"正在停止 {name}...")
                process.terminate()

        for name, process in self.processes:
            if process.poll() is None:
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    print(f"{name} 未在超时时间内退出，执行强制终止。")
                    process.kill()

    def monitor(self) -> int:
        try:
            while True:
                for name, process in self.processes:
                    return_code = process.poll()
                    if return_code is not None:
                        print(f"{name} 已退出，返回码: {return_code}")
                        return return_code
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\n检测到 Ctrl + C，准备退出...")
            return 0


def main() -> int:
    for required in ("app.py", "publish_test.py"):
        if not (ROOT / required).exists():
            print(f"未找到文件：{required}")
            return 1

    runner = ProcessPairRunner()
    runner.start("APP", "app.py")
    runner.start("PUBLISH", "publish_test.py")

    print("已启动 app.py 和 publish_test.py，按 Ctrl + C 结束。")
    code = runner.monitor()
    runner.stop_all()
    return code


if __name__ == "__main__":
    raise SystemExit(main())
