"""
Flask + SocketIO 主程序
集成离线检测后台线程
"""

import time
import threading
from datetime import datetime
from flask import Flask, jsonify, render_template
from flask_socketio import SocketIO
import db
import mqtt_client

app = Flask(__name__)
# 初始化 SocketIO，允许跨域，使用 threading 模式保持简单
socketio = SocketIO(app, cors_allowed_origins="*")

# 初始化数据库（创建表）
db.init_db()

# 将 SocketIO 实例传递给 MQTT 模块，以便在收到消息时推送
mqtt_client.set_socketio(socketio)
# 启动 MQTT 订阅客户端
mqtt_client_inst = mqtt_client.start_mqtt()

def offline_check_thread():
    """
    后台线程：每 5 秒检查一次设备在线状态
    如果超过 10 秒未上报，标记为离线并通过 WebSocket 推送
    """
    print("Offline detection thread started...")
    while True:
        try:
            devices = db.get_all_devices()
            now = datetime.now()
            changed = False
            
            for dev in devices:
                if dev['online_status'] == 1:
                    # 解析最后看到的时间
                    last_seen_time = datetime.strptime(dev['last_seen'], "%Y-%m-%d %H:%M:%S")
                    # 计算时间差（秒）
                    diff = (now - last_seen_time).total_seconds()
                    
                    if diff > 10:
                        # 超过 10 秒，标记为离线
                        db.set_device_offline(dev['device_id'])
                        print(f"Device {dev['device_id']} is now offline (last seen {diff}s ago)")
                        changed = True
            
            # 如果有设备状态发生变化，通过 WebSocket 推送最新状态
            if changed:
                latest_data = db.get_latest_status()
                socketio.emit('device_update', latest_data)
                print("SocketIO: Broadcasted device_update (offline event)")
                
        except Exception as e:
            print(f"Error in offline_check_thread: {e}")
        
        # 每 5 秒检查一次
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
    """API: 获取所有设备的最新状态（用于页面初始加载）"""
    data = db.get_latest_status()
    return jsonify(data)

@app.route("/api/history")
def get_history():
    """API: 获取最近 50 条报警历史记录"""
    data = db.get_history(limit=50)
    return jsonify(data)

if __name__ == "__main__":
    # 使用 socketio.run 代替 app.run 以启用 WebSocket 支持
    socketio.run(app, host="0.0.0.0", port=5000, debug=False)
