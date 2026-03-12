"""
MQTT 订阅客户端
"""
import traceback
import paho.mqtt.client as mqtt
import json
import db
from logger import log_event
from config import MQTT_BROKER, MQTT_PORT, MQTT_TOPIC

# 全局 SocketIO 实例引用
socketio_inst = None

def set_socketio(sio):
    """设置 SocketIO 实例，用于推送消息"""
    global socketio_inst
    socketio_inst = sio

def on_connect(client, userdata, flags, rc):
    """连接成功回调函数"""
    if rc == 0:
        log_event("INFO", "mqtt.client.connected", "ops", "mqtt", "Connected to MQTT broker successfully", topic=MQTT_TOPIC)
        client.subscribe(MQTT_TOPIC)
        log_event("INFO", "mqtt.topic.subscribed", "ops", "mqtt", "Subscribed to target MQTT topic", topic=MQTT_TOPIC)
    else:
        log_event("ERROR", "mqtt.client.connect_failed", "ops", "mqtt", f"Failed to connect to MQTT broker, return code {rc}", topic=MQTT_TOPIC, error=rc)

def on_message(client, userdata, msg):
    """收到消息回调函数"""
    try:
        log_event("DEBUG", "mqtt.message.received", "ops", "mqtt", "MQTT message received", topic=msg.topic, extra={"payload_size": len(msg.payload)})
        
        payload = json.loads(msg.payload.decode())
        topic_parts = msg.topic.split('/')
        device_id = topic_parts[2] if len(topic_parts) >= 3 else payload.get("device_id", "unknown")
        alarm = payload.get("alarm", 0)
        timestamp = payload.get("timestamp", "")
        
        # 更新数据库
        changed = db.update_device_data(device_id=device_id, alarm=alarm)
        
        # 如果有报警且包含图片，保存图片
        if alarm == 1 and payload.get("image"):
            image_path = db.save_base64_image(device_id, payload["image"], timestamp)
            if image_path:
                log_event("INFO", "device.alarm.image_saved", "biz", "mqtt", "Alarm image saved", device_id=device_id, extra={"image_path": image_path})
        
        log_event("INFO", "mqtt.message.processed", "biz", "mqtt", "MQTT message processed and DB updated", device_id=device_id, topic=msg.topic, extra={"changed": changed})

        # 通过 WebSocket 推送包含统计信息的数据包
        if socketio_inst:
            full_data = db.get_latest_data_with_stats()
            socketio_inst.emit('device_update', full_data)
            log_event("DEBUG", "socketio.data.pushed", "biz", "socketio", "Pushed device data to frontend via SocketIO", device_id=device_id)
        
    except Exception as e:
        log_event("ERROR", "mqtt.message.parse_failed", "ops", "mqtt", "Failed to process MQTT message", topic=msg.topic, error=str(e))

def start_mqtt():
    """初始化并启动 MQTT 客户端"""
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
        log_event("INFO", "mqtt.client.started", "ops", "mqtt", "MQTT client started successfully", extra={"broker": MQTT_BROKER, "port": MQTT_PORT})
        return client
    except Exception as e:
        # 启动阶段必须失败即退出，避免服务看似可用但实际上没有消费任何 MQTT 消息。
        log_event("CRITICAL", "mqtt.client.start_failed", "ops", "mqtt", "MQTT client failed to start", extra={"broker": MQTT_BROKER, "port": MQTT_PORT}, error=str(e))
        print(traceback.format_exc())
        raise
