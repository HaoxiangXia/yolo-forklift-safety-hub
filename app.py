"""
Flask + SocketIO 主程序
集成离线检测后台线程 - 升级版
"""

import time
import threading
from datetime import datetime
from flask import Flask, jsonify, render_template
from flask_socketio import SocketIO
import db
import mqtt_client

app = Flask(__name__)
# 初始化 SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")

# 初始化数据库（创建新表结构）
db.init_db()

# 将 SocketIO 实例传递给 MQTT 模块
mqtt_client.set_socketio(socketio)
# 启动 MQTT 订阅客户端
mqtt_client_inst = mqtt_client.start_mqtt()

def offline_check_thread():
    """
    后台线程：每 5 秒检查一次设备在线状态
    规则：超过 10 秒未上报则判定为离线
    """
    print("Offline detection thread started...")
    while True:
        try:
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
                        print(f"Device {dev['device_id']} is now offline (last seen {diff}s ago)")
                        changed = True
            
            if changed:
                latest_data = db.get_latest_status()
                socketio.emit('device_update', latest_data)
                print("SocketIO: Broadcasted device_update (offline event)")
                
        except Exception as e:
            print(f"Error in offline_check_thread: {e}")
        
        time.sleep(5)

# 启动离线检测后台线程
daemon_thread = threading.Thread(target=offline_check_thread, daemon=True)
daemon_thread.start()

@app.route("/")
def index():
    """渲染主页"""
    return render_template("index.html")

@app.route("/api/latest")
def get_latest():
    """API: 获取所有设备的最新状态"""
    data = db.get_latest_status()
    return jsonify(data)

# 如果不再需要历史记录接口，可以删除或保留，但注意数据库里现在主要维护实时状态
@app.route("/api/history")
def get_history_stub():
    """历史记录接口（占位）"""
    return jsonify([])

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=False)
