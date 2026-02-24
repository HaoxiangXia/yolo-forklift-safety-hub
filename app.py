"""
Flask + SocketIO 主程序
整合目标：保留日志记录、完整API、清晰注释，优化异步逻辑和异常处理
"""
import eventlet
# 猴子补丁：确保eventlet异步模式下sleep/网络操作正常
eventlet.monkey_patch()

import time
from datetime import datetime
from flask import Flask, jsonify, render_template
from flask_socketio import SocketIO
# 自定义模块：数据库、MQTT客户端、日志工具
import db
import mqtt_client
from logger import log_event  # 保留日志功能

# ==================== 应用配置 ====================
app = Flask(__name__)
# SocketIO配置：允许跨域，显式指定eventlet异步模式（兼容两段代码）
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='eventlet'
)

# ==================== 服务初始化 ====================
def init_services():
    """初始化数据库和MQTT客户端（整合两段代码的初始化逻辑）"""
    try:
        # 初始化数据库
        db.init_db()
        log_event("INFO", "system.db.init", "ops", "app", "Database initialized successfully")
        
        # 配置并启动MQTT客户端
        mqtt_client.set_socketio(socketio)
        mqtt_client_inst = mqtt_client.start_mqtt()
        log_event("INFO", "system.mqtt.start", "ops", "app", "MQTT client started successfully")
        
        return mqtt_client_inst
    except Exception as e:
        log_event("CRITICAL", "system.init.failed", "ops", "app", f"Service initialization failed: {str(e)}")
        raise  # 初始化失败终止程序

# 执行初始化
mqtt_client_inst = init_services()

# ==================== 后台任务：设备离线检测 ====================
def offline_check_loop():
    """
    后台循环检测设备离线状态（整合两段代码的逻辑）
    逻辑：每5秒检查一次，若设备最后上报时间超过10秒则标记为离线，并推送更新
    """
    log_event(
        "INFO", 
        "system.background.offline_check_started", 
        "ops", 
        "app", 
        "Offline detection loop started", 
        extra={"interval_sec": 5}
    )
    
    while True:
        try:
            # 必须使用eventlet.sleep（而非time.sleep）让出控制权，保证异步正常
            eventlet.sleep(5)
            
            devices = db.get_all_devices()
            now = datetime.now()
            changed = False  # 标记是否有设备状态变更
            
            for dev in devices:
                # 仅检查当前标记为在线的设备
                if dev['online_status'] == 1:
                    try:
                        # 解析设备最后上报时间
                        last_seen_time = datetime.strptime(dev['last_seen'], "%Y-%m-%d %H:%M:%S")
                        offline_seconds = (now - last_seen_time).total_seconds()
                        
                        # 超过10秒未上报则标记为离线
                        if offline_seconds > 10:
                            db.set_device_offline(dev['device_id'])
                            # 同时记录日志和打印（兼顾两段代码的输出方式）
                            log_event(
                                "WARNING", 
                                "device.status.offline_marked", 
                                "biz", 
                                "app", 
                                f"Device marked offline", 
                                device_id=dev['device_id'],
                                extra={"offline_seconds": offline_seconds}
                            )
                            print(f"Device {dev['device_id']} is now offline (offline for {offline_seconds:.1f}s)")
                            changed = True
                    except Exception as e:
                        # 单个设备处理失败不中断整个循环
                        log_event(
                            "ERROR", 
                            "device.status.check_failed", 
                            "biz", 
                            "app", 
                            f"Failed to check device {dev['device_id']}", 
                            error=str(e)
                        )
            
            # 有设备状态变更时，推送更新到前端
            if changed:
                full_data = db.get_latest_data_with_stats()
                socketio.emit('device_update', full_data)
                log_event(
                    "INFO", 
                    "socket.broadcast.device_update", 
                    "ops", 
                    "app", 
                    "Broadcasted device_update (offline event)"
                )
                print("SocketIO: Broadcasted device_update (offline event)")
                
        except Exception as e:
            # 循环整体异常处理（不终止循环）
            log_event(
                "ERROR", 
                "system.background.offline_check_failed", 
                "ops", 
                "app", 
                f"Offline check loop error: {str(e)}"
            )
            print(f"Error in offline_check_loop: {e}")

# 启动离线检测后台任务（使用SocketIO适配的方式，兼容eventlet）
socketio.start_background_task(offline_check_loop)

# ==================== API接口 & 页面路由 ====================
@app.route("/")
def index():
    """渲染前端主页"""
    return render_template("index.html")

@app.route("/api/latest")
def get_latest():
    """API：获取所有设备的最新状态及统计信息"""
    data = db.get_latest_data_with_stats()
    log_event("DEBUG", "api.latest.requested", "ops", "api", "Latest device data requested")
    return jsonify(data)

@app.route("/api/biz_logs")
def get_biz_logs():
    """API：获取最新业务日志（保留第一段代码的该接口）"""
    logs = db.get_latest_biz_logs()
    log_event("DEBUG", "api.biz_logs.requested", "ops", "api", "Business logs requested")
    return jsonify(logs)

# ==================== 程序入口 ====================
if __name__ == "__main__":
    log_event("INFO", "system.app.starting", "ops", "app", "Flask + SocketIO app starting")
    print("Starting Flask + SocketIO app on http://0.0.0.0:5000")
    # 启动应用（关闭debug，避免eventlet冲突）
    socketio.run(app, host="0.0.0.0", port=5000, debug=False)
