"""
Flask + SocketIO 主程序
"""

import eventlet
eventlet.monkey_patch()

import time
from datetime import datetime
from flask import Flask, jsonify, render_template
from flask_socketio import SocketIO
import db
import mqtt_client

app = Flask(__name__)
# 显式指定 async_mode 为 eventlet
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# 初始化数据库
db.init_db()

# 配置 MQTT 并传递 SocketIO
mqtt_client.set_socketio(socketio)
mqtt_client_inst = mqtt_client.start_mqtt()

def offline_check_loop():
    """
    后台循环：每 5 秒检查一次离线
    在 eventlet 架构下，使用 socketio.start_background_task 或 eventlet.spawn
    """
    print("Offline detection loop started...")
    while True:
        try:
            # 必须使用 eventlet.sleep 而不是 time.sleep 来让出控制权
            eventlet.sleep(5)
            
            devices = db.get_all_devices()
            now = datetime.now()
            changed = False
            
            for dev in devices:
                if dev['online_status'] == 1:
                    # 解析最近看到的时间
                    last_seen_time = datetime.strptime(dev['last_seen'], "%Y-%m-%d %H:%M:%S")
                    diff = (now - last_seen_time).total_seconds()
                    
                    if diff > 10:
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

@app.route("/")
def index():
    """渲染主页"""
    return render_template("index.html")

@app.route("/api/latest")
def get_latest():
    """API: 获取所有设备的最新状态及统计信息"""
    data = db.get_latest_data_with_stats()
    return jsonify(data)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=False)
