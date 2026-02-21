"""
MQTT 订阅客户端 - 升级推送结构
"""

import paho.mqtt.client as mqtt
import json
import db
from datetime import datetime

# MQTT 配置
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "factory/forklift/+/alarm"

# 全局 SocketIO 实例引用
socketio_inst = None

def set_socketio(sio):
    """设置 SocketIO 实例，用于推送消息"""
    global socketio_inst
    socketio_inst = sio

def on_connect(client, userdata, flags, rc):
    """连接成功回调函数"""
    if rc == 0:
        print("Connected to MQTT Broker!")
        client.subscribe(MQTT_TOPIC)
    else:
        print(f"Failed to connect, return code {rc}")

def on_message(client, userdata, msg):
    """收到消息回调函数"""
    try:
        payload = json.loads(msg.payload.decode())
        topic_parts = msg.topic.split('/')
        device_id = topic_parts[2] if len(topic_parts) >= 3 else payload.get("device_id", "unknown")
        alarm = payload.get("alarm", 0)
        
        # 更新数据库
        db.update_device_data(device_id=device_id, alarm=alarm)
        print(f"MQTT: Updated data for device {device_id}")

        # 通过 WebSocket 推送包含统计信息的数据包
        if socketio_inst:
            full_data = db.get_latest_data_with_stats()
            socketio_inst.emit('device_update', full_data)
            print("SocketIO: Broadcasted device_update with stats")
        
    except Exception as e:
        print(f"Error processing MQTT message: {e}")

def start_mqtt():
    """初始化并启动 MQTT 客户端"""
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
        return client
    except Exception as e:
        print(f"MQTT start error: {e}")
        return None
