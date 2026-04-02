"""
MQTT 妯℃嫙涓婃姤鑴氭湰 - 鍚屾鍗囩骇鐗?
鐢ㄤ簬閰嶅悎"鍙夎溅浣滀笟浜鸿溅浜掓枼鎶ヨ绯荤粺"杩涜娴嬇する
鍖呭惈璁惧浣嶇疆妯℃嫙鍔熃兘
"""

import paho.mqtt.client as mqtt
import json
import time
import random
from datetime import datetime
import sys
import os
import requests

# 娣诲姞鐖剁洰褰曞埌璺緞锛屼互渚垮鍏?db 鍜?config
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db
from config import POSITION_UPDATE_INTERVAL_SEC, POSITION_MOVE_RANGE

# MQTT 閰嶇疆
MQTT_BROKER = "localhost"
MQTT_PORT = 1883

# 妯ṁ-
DEVICES = ["FORK-001", "FORK-002", "FORK-003"]

# 鍥剧墖涓Ѡ 上传配置（批量）
UPLOAD_URL = "http://localhost:5000/api/upload-image"
IMAGE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images", "alarms", "bqb.jpg")
UPLOAD_DEVICE = "FORK-003"  # 只有这个设备进行图片上传

def upload_alarm_images(device_id, base_timestamp, count=4):
    """
    模拟批量上传报警图片（老 -> 新顺序）
    返回 image_urls 数组；失败返回空列表
    """
    if not os.path.exists(IMAGE_PATH):
        print(f"[Upload] Image file not found: {IMAGE_PATH}")
        return []
    
    files = []
    file_handles = []
    try:
        for i in range(count):
            fh = open(IMAGE_PATH, "rb")
            file_handles.append(fh)
            filename = f"{device_id}_mock_{i}.jpg"
            files.append(("images", (filename, fh, "image/jpeg")))
        
        data = {
            "device_id": device_id,
            "base_timestamp": base_timestamp
        }
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
    client = mqtt.Client()
    
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
                    print(f"[Simulation] {dev_id} chooses to stay SILENT (testing offline detection)")
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
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                # FORK-003 报警触发时先批量上传图片，再通过 MQTT 携带 image_urls
                if dev_id == UPLOAD_DEVICE and next_state == 1 and current_state == 0:
                    base_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    image_urls = upload_alarm_images(dev_id, base_ts, count=4)
                    if image_urls:
                        payload["image_urls"] = image_urls
                        print(f"[Image] {dev_id} alarm triggered with images: {image_urls}")
                    else:
                        print(f"[Image] {dev_id} alarm triggered but upload failed")
                
                topic = f"factory/forklift/{dev_id}/alarm"
                client.publish(topic, json.dumps(payload))
                
                status_str = "ALARM ON" if next_state == 1 else "NORMAL"
                print(f"[Published] {topic} -> {status_str} | Payload: {json.dumps(payload)}")
            
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
    
    print(f"[Position Sim] Starting position update loop (interval: {POSITION_UPDATE_INTERVAL_SEC}s)...")
    
    while True:
        try:
            time.sleep(POSITION_UPDATE_INTERVAL_SEC)
            
            devices = db.get_all_devices_with_positions()
            for dev in devices:
                if dev['online_status'] == 1:
                    # 随机移动
                    new_x = (dev['pos_x'] or 0) + random.uniform(-POSITION_MOVE_RANGE, POSITION_MOVE_RANGE)
                    new_y = (dev['pos_y'] or 0) + random.uniform(-POSITION_MOVE_RANGE, POSITION_MOVE_RANGE)
                    
                    # 限制范围
                    new_x = max(0, min(1920, new_x))
                    new_y = max(0, min(1080, new_y))
                    
                    db.update_device_position(dev['device_id'], new_x, new_y)
                    print(f"[Position Sim] {dev['device_id']}: ({new_x:.1f}, {new_y:.1f})")
            
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
