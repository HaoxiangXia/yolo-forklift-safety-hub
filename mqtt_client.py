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
        changed = db.update_device_data(
            device_id=device_id, 
            alarm=alarm, 
            mqtt_timestamp=timestamp
        )
        
        # 如果有报警且包含图片URL（MQTT+HTTP混合方案）
        # 图片已通过HTTP上传，这里只记录图片URL到数据库
        if alarm == 1 and isinstance(payload.get("image_urls"), list) and payload.get("image_urls"):
            image_urls = payload.get("image_urls", [])
            for image_url in image_urls:
                if not isinstance(image_url, str):
                    continue
                if image_url.startswith("/images/"):
                    image_path = image_url[1:]
                else:
                    image_path = image_url
                db.save_alarm_image(device_id, image_path, timestamp)
            log_event("INFO", "device.alarm.image_urls_recorded", "biz", "mqtt",
                      "Alarm image URLs recorded", device_id=device_id,
                      extra={"image_urls": image_urls})
        elif alarm == 1 and payload.get("image_url"):
            image_url = payload["image_url"]
            # 从URL中提取文件路径
            if image_url.startswith("/images/"):
                image_path = image_url[1:]  # 去掉开头的"/"
            else:
                image_path = image_url
            
            # 保存图片记录到数据库
            db.save_alarm_image(device_id, image_path, timestamp)
            log_event("INFO", "device.alarm.image_url_recorded", "biz", "mqtt", "Alarm image URL recorded", device_id=device_id, extra={"image_url": image_url})
        
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
