"""
MQTT 模拟上报脚本
符合系统升级后的数据结构要求
"""

import paho.mqtt.client as mqtt
import json
import time
import random
from datetime import datetime

# MQTT 配置
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
# 模拟三个不同的设备，其中一个偶尔“失联”用于测试离线检测
DEVICES = ["FORK-001", "FORK-002", "FORK-003"]

def simulate_publish():
    client = mqtt.Client()
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        print(f"Connected to Broker at {MQTT_BROKER}")
        
        while True:
            for dev_id in DEVICES:
                # 模拟逻辑：FORK-003 有 30% 概率跳过上报，模拟掉线
                if dev_id == "FORK-003" and random.random() < 0.3:
                    print(f"Simulating: {dev_id} is silent this turn...")
                    continue

                # 构造模拟数据
                is_alarm = 1 if random.random() > 0.8 else 0
                is_present = 1 if random.random() > 0.2 else 0
                is_intrusion = 1 if random.random() > 0.9 else 0
                
                payload = {
                    "device_id": dev_id,
                    "alarm": is_alarm,
                    "driver_present": is_present,
                    "outer_intrusion": is_intrusion,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                # 发布到对应的 Topic: factory/forklift/DEVICE_ID/alarm
                topic = f"factory/forklift/{dev_id}/alarm"
                client.publish(topic, json.dumps(payload))
                
                print(f"Published to {topic}: {payload}")
            
            # 每 5 秒发布一次
            # 注意：离线判定是 10 秒，所以 5 秒上报一次是正常的
            time.sleep(5)
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.disconnect()

if __name__ == "__main__":
    simulate_publish()
