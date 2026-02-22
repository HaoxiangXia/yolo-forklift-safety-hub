"""
Flask + SocketIO 主程序
"""

import time
from datetime import datetime
from flask import Flask, jsonify, render_template
from flask_socketio import SocketIO
import db
import mqtt_client
from config import (
    OFFLINE_CHECK_INTERVAL_SEC,
    OFFLINE_TIMEOUT_SEC,
    HISTORY_LIMIT,
    TREND_LIMIT,
)

app = Flask(__name__)
# 显式指定 async_mode 为 threading
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# 初始化数据库
db.init_db()

# 配置 MQTT 并传递 SocketIO
mqtt_client.set_socketio(socketio)
mqtt_client_inst = mqtt_client.start_mqtt()

def offline_check_loop():
    """
    后台循环：每 5 秒检查一次离线
    在线程模式下使用 time.sleep 即可
    """
    print("Offline detection loop started...")
    while True:
        try:
            time.sleep(OFFLINE_CHECK_INTERVAL_SEC)
            
            devices = db.get_all_devices()
            now = datetime.now()
            changed = False
            
            for dev in devices:
                if dev['online_status'] == 1:
                    # 解析最近看到的时间
                    last_seen_time = datetime.strptime(dev['last_seen'], "%Y-%m-%d %H:%M:%S")
                    diff = (now - last_seen_time).total_seconds()
                    
                    if diff > OFFLINE_TIMEOUT_SEC:
                        db.set_device_offline(dev['device_id'])
                        print(f"Device {dev['device_id']} is now offline")
                        changed = True
            
            if changed:
                full_data = db.get_latest_data_with_stats()
                socketio.emit('device_update', full_data)
                print("SocketIO: Broadcasted device_update (offline event)")
                
        except Exception as e:
            print(f"Error in offline_check_loop: {e}")

# 使用 SocketIO 提供的后台任务启动方式，它会自动适应 async_mode
socketio.start_background_task(offline_check_loop)

@socketio.on("connect")
def handle_connect():
    """WebSocket 连接事件"""
    print("SocketIO client connected")

@socketio.on("disconnect")
def handle_disconnect():
    """WebSocket 断开事件"""
    print("SocketIO client disconnected")

@app.route("/")
def index():
    """渲染主页"""
    return render_template("index.html")

@app.route("/api/latest")
def get_latest():
    return jsonify(db.get_latest_data_with_stats())

@app.route("/device/<device_id>/history")
def get_device_history(device_id):
    """
    API: 返回设备详情，包括原始历史和趋势统计
    """
    # 趋势聚合数据（柱状图用）
    trend = db.get_device_alarm_trend(device_id, limit=TREND_LIMIT)
    # 原始明细记录（列表用）
    raw_history = db.get_device_history_raw(device_id, limit=HISTORY_LIMIT)
    
    return jsonify({
        "device_id": device_id,
        "labels": trend["labels"],
        "counts": trend["counts"],
        "raw_history": raw_history
    })

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
