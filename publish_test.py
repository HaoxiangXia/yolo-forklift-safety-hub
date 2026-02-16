"""
MQTT 模拟上报脚本 - 同步升级版
用于配合“叉车作业人车互斥报警系统”进行测试
"""

import paho.mqtt.client as mqtt
import json
import time
import random
from datetime import datetime

# MQTT 配置
MQTT_BROKER = "localhost"
MQTT_PORT = 1883

# 模拟三个不同的设备
DEVICES = ["FORK-001", "FORK-002", "FORK-003"]

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

if __name__ == "__main__":
    simulate_publish()
