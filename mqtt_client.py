"""
MQTT 订阅客户端，收到消息后写入数据库
"""

import paho.mqtt.client as mqtt
import json
import db
from datetime import datetime

# MQTT 配置
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "factory/forklift/+/alarm"

def on_connect(client, userdata, flags, rc):
    """连接成功回调函数"""
    if rc == 0:
        print("Connected to MQTT Broker!")
        # 订阅主题
        client.subscribe(MQTT_TOPIC)
        print(f"Subscribed to topic: {MQTT_TOPIC}")
    else:
        print(f"Failed to connect, return code {rc}")

def on_message(client, userdata, msg):
    """收到消息回调函数"""
    try:
        # 1. 打印原始信息
        print(f"Received message on topic {msg.topic}")
        
        # 2. 解析 JSON 数据
        payload = json.loads(msg.payload.decode())
        
        # 3. 从主题或 Payload 中获取设备 ID
        # 主题格式: factory/forklift/DEVICE_ID/alarm
        topic_parts = msg.topic.split('/')
        device_id = topic_parts[2] if len(topic_parts) >= 3 else payload.get("device_id", "unknown")
        
        # 4. 提取各字段数据
        alarm = payload.get("alarm", 0)
        driver_present = payload.get("driver_present", 0)
        outer_intrusion = payload.get("outer_intrusion", 0)
        # 如果 JSON 里没有时间戳，则使用系统当前时间
        timestamp = payload.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        # 5. 调用数据库模块保存数据
        db.insert_alarm_data(
            device_id=device_id,
            alarm=alarm,
            timestamp=timestamp,
            driver_present=driver_present,
            outer_intrusion=outer_intrusion
        )
        print(f"Saved data for device {device_id} to database.")
        
    except Exception as e:
        print(f"Error processing MQTT message: {e}")

def start_mqtt():
    """初始化并启动 MQTT 客户端"""
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        # 连接 Broker
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        # 开启后台循环，非阻塞运行
        client.loop_start()
        return client
    except Exception as e:
        print(f"MQTT start error: {e}")
        return None
