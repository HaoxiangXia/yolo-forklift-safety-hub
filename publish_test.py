"""
MQTT 模拟上报脚本

用于配合"叉车作业人车互斥报警系统"进行测试

功能概述：
1. MQTT 报警数据模拟：模拟多台叉车设备定时上报报警状态、驾驶员状态、入侵检测等数据
2. 报警状态切换：模拟设备在正常/报警状态间的随机切换，支持状态保持概率配置
3. 离线检测测试：模拟设备静默不发送数据，用于测试服务端离线检测机制
4. 报警图片上传：模拟设备报警时通过HTTP批量上传图片并获取URL，再通过MQTT携带image_urls上报
5. 设备位置模拟：初始化设备随机位置并定期更新坐标，模拟叉车在厂区内的移动轨迹
"""

import paho.mqtt.client as mqtt
import json
import time
import random
from datetime import datetime
import sys
import os
import requests
from urllib.parse import urljoin

# 添加父目录到路径，以便导入 db 和 config
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db
from config import POSITION_UPDATE_INTERVAL_SEC, POSITION_MOVE_RANGE

# MQTT 配置
MQTT_BROKER = "localhost"
MQTT_PORT = 1883

# 模拟设备
DEVICES = ["FORK-001", "FORK-002", "FORK-003"]

# 图片上传配置（批量）
SERVER_BASE_URL = os.getenv("SERVER_BASE_URL", "http://localhost:5000").rstrip("/") + "/"
UPLOAD_URL = urljoin(SERVER_BASE_URL, "api/upload-image")
IMAGE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "images", "alarms", "bqb.jpg"
)
UPLOAD_DEVICE = "FORK-003"  # 只有这个设备进行图片上传


def upload_alarm_images(device_id, base_timestamp, count=4):
    """
    模拟批量上传报警图片（老 -> 新顺序）
    返回 image_urls 数组；失败返回空列表
    """
    if not os.path.exists(IMAGE_PATH):
        print(f"[Upload] Image file not found: {IMAGE_PATH}")
        return []

    file_handles = []
    try:
        for i in range(count):
            fh = open(IMAGE_PATH, "rb")
            file_handles.append(fh)

        files = [
            ("images", (f"{device_id}_mock_{i}.jpg", fh, "image/jpeg"))
            for i, fh in enumerate(file_handles)
        ]

        data = {"device_id": device_id, "base_timestamp": base_timestamp}
        res = requests.post(UPLOAD_URL, data=data, files=files, timeout=10)
        if res.status_code != 200:
            print(f"[Upload] Failed: {res.status_code} {res.text}")
            return []
        payload = res.json()
        return payload.get("image_urls", [])
    except Exception as e:
        print(f"[Upload] Error: {e}")
        return []
    finally:
        for fh in file_handles:
            try:
                fh.close()
            except Exception:
                pass


def simulate_publish():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        print(f"Successfully connected to MQTT Broker at {MQTT_BROKER}:{MQTT_PORT}")
        print("Starting simulation... Press Ctrl+C to stop.")

        # 记录每个设备的上一次报警状态，用于模拟状态切换
        device_states = {dev: 0 for dev in DEVICES}

        while True:
            for dev_id in DEVICES:
                # --- 模拟离线逻辑 ---
                if dev_id == "FORK-003" and random.random() < 0.4:
                    print(
                        f"[Simulation] {dev_id} chooses to stay SILENT (testing offline detection)"
                    )
                    continue

                # --- 模拟报警切换 ---
                current_state = device_states[dev_id]

                if current_state == 1:
                    next_state = 1 if random.random() < 0.7 else 0
                else:
                    next_state = 1 if random.random() < 0.15 else 0

                device_states[dev_id] = next_state

                payload = {
                    "device_id": dev_id,
                    "alarm": next_state,
                    "driver_present": 1 if random.random() > 0.1 else 0,
                    "outer_intrusion": 1 if random.random() > 0.9 else 0,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }

                # FORK-003 报警触发时先批量上传图片，再通过 MQTT 携带 image_urls
                if dev_id == UPLOAD_DEVICE and next_state == 1 and current_state == 0:
                    base_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    image_urls = upload_alarm_images(dev_id, base_ts, count=4)
                    if image_urls:
                        payload["image_urls"] = image_urls
                        print(
                            f"[Image] {dev_id} alarm triggered with images: {image_urls}"
                        )
                    else:
                        print(f"[Image] {dev_id} alarm triggered but upload failed")

                topic = f"factory/forklift/{dev_id}/alarm"
                client.publish(topic, json.dumps(payload))

                status_str = "ALARM ON" if next_state == 1 else "NORMAL"
                print(
                    f"[Published] {topic} -> {status_str} | Payload: {json.dumps(payload)}"
                )

            time.sleep(5)

    except KeyboardInterrupt:
        print("\nSimulation stopped by user.")
    except Exception as e:
        print(f"Simulation Error: {e}")
    finally:
        client.disconnect()


def simulate_position_update():
    """
    设备位置模拟更新函数
    初始化随机位置并定期更新位置（模拟叉车移动）
    """
    print(f"[Position Sim] Initializing device positions...")

    # 初始化设备位置
    db.init_device_positions()

    print(
        f"[Position Sim] Starting position update loop (interval: {POSITION_UPDATE_INTERVAL_SEC}s)..."
    )

    while True:
        try:
            time.sleep(POSITION_UPDATE_INTERVAL_SEC)

            devices = db.get_all_devices_with_positions()
            for dev in devices:
                if dev["online_status"] == 1:
                    # 随机移动
                    new_x = (dev["pos_x"] or 0) + random.uniform(
                        -POSITION_MOVE_RANGE, POSITION_MOVE_RANGE
                    )
                    new_y = (dev["pos_y"] or 0) + random.uniform(
                        -POSITION_MOVE_RANGE, POSITION_MOVE_RANGE
                    )

                    # 限制范围
                    new_x = max(0, min(1920, new_x))
                    new_y = max(0, min(1080, new_y))

                    db.update_device_position(dev["device_id"], new_x, new_y)
                    print(
                        f"[Position Sim] {dev['device_id']}: ({new_x:.1f}, {new_y:.1f})"
                    )

        except KeyboardInterrupt:
            print("\n[Position Sim] Stopped by user.")
            break
        except Exception as e:
            print(f"[Position Sim] Error: {e}")


if __name__ == "__main__":
    import threading

    # 启动 MQTT 上报线程
    mqtt_thread = threading.Thread(target=simulate_publish, daemon=True)
    mqtt_thread.start()

    # 启动位置模拟线程
    simulate_position_update()
