"""
Flask + SocketIO 主程序
"""

import sys
import time
from datetime import datetime
from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO

import db
import mqtt_client
from logger import log_event, get_latest_biz_logs
from config import (
    OFFLINE_CHECK_INTERVAL_SEC,
    OFFLINE_TIMEOUT_SEC,
    HISTORY_LIMIT,
    TREND_LIMIT,
    AUTH_ENABLED,
    AUTH_TOKEN,
)

app = Flask(__name__)
# 显式指定 async_mode 为 threading
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

def extract_request_token(req):
    """从请求头提取 token，兼容 Bearer 与 X-Auth-Token，便于联调与脚本调用。"""
    auth_header = req.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:].strip()
    return req.headers.get("X-Auth-Token", "").strip()

def validate_token(token):
    """统一校验逻辑，避免 REST 与 SocketIO 出现不一致行为。"""
    if not AUTH_ENABLED:
        return True
    if not AUTH_TOKEN:
        print("[鉴权错误] 已启用鉴权但未配置 AUTH_TOKEN，请检查配置。")
        return False
    return token == AUTH_TOKEN

def require_auth():
    """REST 鉴权入口：失败返回 401，且中文提示方便排查。"""
    token = extract_request_token(request)
    if validate_token(token):
        return None
    log_event("WARNING", "auth.failed.rest", "sec", "app", "REST API authentication failed", error="Token invalid or missing", extra={"path": request.path, "ip": request.remote_addr})
    return jsonify({"message": "鉴权失败：Token 无效或缺失"}), 401

# 初始化数据库
try:
    db.init_db()
    log_event("INFO", "system.db.init", "ops", "app", "Database initialized successfully")
except Exception as e:
    log_event("CRITICAL", "system.init.failed", "ops", "app", f"Database initialization failed: {str(e)}")
    raise

# 启动MQTT客户端
mqtt_client.set_socketio(socketio)
try:
    mqtt_client_inst = mqtt_client.start_mqtt()
    log_event("INFO", "system.mqtt.start", "ops", "app", "MQTT client started successfully")
except Exception as exc:
    log_event("CRITICAL", "system.init.failed", "ops", "app", f"MQTT client start failed: {str(exc)}")
    sys.exit(1)

def offline_check_loop():
    """
    后台离线检测循环 (恢复为版本2的 time.sleep)
    """
    log_event("INFO", "system.background.offline_check_started", "ops", "app", "Offline detection loop started", extra={"interval_sec": OFFLINE_CHECK_INTERVAL_SEC})
    while True:
        try:
            time.sleep(OFFLINE_CHECK_INTERVAL_SEC)

            devices = db.get_all_devices()
            now = datetime.now()
            changed = False

            for dev in devices:
                if dev['online_status'] == 1:
                    last_seen_time = datetime.strptime(dev['last_seen'], "%Y-%m-%d %H:%M:%S")
                    offline_seconds = (now - last_seen_time).total_seconds()

                    if offline_seconds > OFFLINE_TIMEOUT_SEC:
                        db.set_device_offline(dev['device_id'])
                        log_event("WARNING", "device.status.offline_marked", "biz", "app", f"Device marked offline", device_id=dev['device_id'], extra={"offline_seconds": offline_seconds})
                        changed = True

            if changed:
                full_data = db.get_latest_data_with_stats()
                socketio.emit('device_update', full_data)
                log_event("INFO", "socket.broadcast.device_update", "ops", "app", "Broadcasted device_update (offline event)")

        except Exception as e:
            log_event("ERROR", "system.background.offline_check_failed", "ops", "app", f"Offline check loop error: {str(e)}")

# 启动后台检测线程
socketio.start_background_task(offline_check_loop)

@socketio.on("connect")
def handle_connect(auth):
    """WebSocket 连接事件。"""
    token = ""
    # 兼容 auth payload 与 query 参数，减少不同前端接入方式的改造成本。
    if isinstance(auth, dict):
        token = str(auth.get("token", "")).strip()
    if not token:
        token = request.args.get("token", "").strip()

    if not validate_token(token):
        log_event("WARNING", "auth.failed.ws", "sec", "app", "SocketIO authentication failed", error="Token invalid or missing", extra={"sid": request.sid, "ip": request.remote_addr})
        raise ConnectionRefusedError("鉴权失败：Socket Token 无效或缺失")
    log_event("INFO", "socket.client.connected", "ops", "app", "SocketIO client connected", sid=request.sid)

@socketio.on("disconnect")
def handle_disconnect():
    """WebSocket 断开事件"""
    log_event("INFO", "socket.client.disconnected", "ops", "app", "SocketIO client disconnected", sid=request.sid)

@app.route("/")
def index():
    """渲染主页"""
    return render_template("index.html", app_auth_token=AUTH_TOKEN)

@app.route("/api/latest")
def get_latest():
    auth_failed = require_auth()
    if auth_failed:
        return auth_failed
    data = db.get_latest_data_with_stats()
    return jsonify(data)

@app.route("/api/biz_logs")
def get_biz_logs_route():
    """暴露给前端访问历史业务日志"""
    auth_failed = require_auth()
    if auth_failed:
        return auth_failed
    logs = get_latest_biz_logs(100)
    return jsonify(logs)

@app.route("/device/<device_id>/history")
def get_device_history(device_id):
    """返回设备详情，包括原始历史和趋势统计"""
    auth_failed = require_auth()
    if auth_failed:
        return auth_failed

    # 趋势聚合数据
    trend = db.get_device_alarm_trend(device_id, limit=TREND_LIMIT)
    # 原始明细记录
    raw_history = db.get_device_history_raw(device_id, limit=HISTORY_LIMIT)

    return jsonify({
        "device_id": device_id,
        "labels": trend["labels"],
        "counts": trend["counts"],
        "raw_history": raw_history
    })

if __name__ == "__main__":
    log_event("INFO", "system.app.starting", "ops", "app", "Flask + SocketIO app starting")
    print("Starting Flask + SocketIO app on http://0.0.0.0:5000")
    socketio.run(app, host="0.0.0.0", port=5000, debug=False)
