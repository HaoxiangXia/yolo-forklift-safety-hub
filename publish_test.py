"""
MQTT 模拟上报脚本 - 同步升级版
用于配合"叉车作业人车互斥报警系统"进行测试
包含设备位置模拟功能
"""

import paho.mqtt.client as mqtt
import json
import time
import random
from datetime import datetime
import sys
import os

# 添加父目录到路径，以便导入 db 和 config
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db
from config import POSITION_UPDATE_INTERVAL_SEC, POSITION_MOVE_RANGE

# MQTT 配置
MQTT_BROKER = "localhost"
MQTT_PORT = 1883

# 模拟三个不同的设备
DEVICES = ["FORK-001", "FORK-002", "FORK-003"]

# 图片配置（模拟用，不真正上传）
IMAGE_URL = "/images/alarms/bqb.jpg"
UPLOAD_DEVICE = "FORK-003"  # 只有这个设备携带图片

def simulate_publish():
    client = mqtt.Client()
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        print(f"Successfully connected to MQTT Broker at {MQTT_BROKER}:{MQTT_PORT}")
        print("Starting simulation... Press Ctrl+C to stop.")
        
        # 记录每个设备的上一个报警状态，用于模拟状态切换
        # 这样可以测试后端“报警触发（0->1）”时错误计数增加的逻辑
        device_states = {dev: 0 for dev in DEVICES}
        
        while True:
            for dev_id in DEVICES:
                # --- 模拟离线逻辑 ---
                # FORK-003 有较大概率连续几次不发数据，从而触发系统的 10秒离线判定
                if dev_id == "FORK-003" and random.random() < 0.4:
                    print(f"[Simulation] {dev_id} chooses to stay SILENT (testing offline detection)")
                    continue

                # --- 模拟报警切换逻辑 ---
                current_state = device_states[dev_id]
                
                if current_state == 1:
                    # 如果当前在报警，70% 概率继续报警（测试不重复计数），30% 概率恢复正常
                    next_state = 1 if random.random() < 0.7 else 0
                else:
                    # 如果当前正常，15% 概率触发新报警（测试错误计数+1），85% 概率保持正常
                    next_state = 1 if random.random() < 0.15 else 0
                
                device_states[dev_id] = next_state

                # --- 构造 JSON 数据包 ---
                # 包含基本字段和扩展字段（即使后端暂时不存，也符合扩展性要求）
                payload = {
                    "device_id": dev_id,
                    "alarm": next_state,
                    "driver_present": 1 if random.random() > 0.1 else 0,
                    "outer_intrusion": 1 if random.random() > 0.9 else 0,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                # FORK-003 报警触发时添加图片路径
                if dev_id == UPLOAD_DEVICE and next_state == 1 and current_state == 0:
                    payload["image_url"] = IMAGE_URL
                    print(f"[Image] {dev_id} alarm triggered with image: {IMAGE_URL}")
                
                # 发布到 Topic: factory/forklift/DEVICE_ID/alarm
                topic = f"factory/forklift/{dev_id}/alarm"
                client.publish(topic, json.dumps(payload))
                
                status_str = "ALARM ON" if next_state == 1 else "NORMAL"
                print(f"[Published] {topic} -> {status_str} | Payload: {json.dumps(payload)}")
            
            # 每 5 秒循环一次
            # 由于系统离线判定是 10 秒，5 秒一次上报能保证在线状态稳定（除非触发上面的静默逻辑）
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
                    # 随机移动 -POSITION_MOVE_RANGE 到 +POSITION_MOVE_RANGE
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
