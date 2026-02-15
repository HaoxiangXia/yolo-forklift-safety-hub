import paho.mqtt.client as mqtt
import json
import time
import random
from datetime import datetime

# MQTT 配置
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
# 我们模拟两个不同的设备
DEVICES = ["FORK-001", "FORK-002"]

def simulate_publish():
    client = mqtt.Client()
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        print(f"Connected to Broker at {MQTT_BROKER}")
        
        while True:
            for dev_id in DEVICES:
                # 构造模拟数据
                # 随机生成报警状态，大部分时间是正常的
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
            time.sleep(5)
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.disconnect()

if __name__ == "__main__":
    simulate_publish()
