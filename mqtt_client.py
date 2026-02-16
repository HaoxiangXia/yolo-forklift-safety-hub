"""
MQTT 订阅客户端，收到消息后写入数据库并通过 WebSocket 推送
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
        # 订阅主题
        client.subscribe(MQTT_TOPIC)
        print(f"Subscribed to topic: {MQTT_TOPIC}")
    else:
        print(f"Failed to connect, return code {rc}")

def on_message(client, userdata, msg):
    """收到消息回调函数"""
    try:
        # 1. 解析 JSON 数据
        payload = json.loads(msg.payload.decode())
        
        # 2. 从主题或 Payload 中获取设备 ID
        topic_parts = msg.topic.split('/')
        device_id = topic_parts[2] if len(topic_parts) >= 3 else payload.get("device_id", "unknown")
        
        # 3. 提取报警状态
        alarm = payload.get("alarm", 0)
        
        # 4. 更新数据库状态 (处理 boot_time 和 error_count 逻辑)
        db.update_device_data(
            device_id=device_id,
            alarm=alarm
        )
        print(f"MQTT: Updated data for device {device_id}")

        # 5. 通过 WebSocket 主动推送到前端
        if socketio_inst:
            # 获取所有设备的最新状态并广播
            latest_data = db.get_latest_status()
            socketio_inst.emit('device_update', latest_data)
            print("SocketIO: Broadcasted device_update")
        
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
