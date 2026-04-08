"""
Flask + SocketIO 主程序
"""

import os
import re
import sys
import time
import random
import json
from datetime import datetime, timedelta
from flask import (
    Flask,
    abort,
    jsonify,
    make_response,
    render_template,
    request,
    send_from_directory,
)
from flask_socketio import SocketIO

import db
import mqtt_client
from logger import log_event, get_latest_biz_logs, get_logs_by_page
from llm_client import analyze_alarm_image
from config import (
    OFFLINE_CHECK_INTERVAL_SEC,
    OFFLINE_TIMEOUT_SEC,
    HISTORY_LIMIT,
    TREND_LIMIT,
    ALLOWED_IMAGE_EXTENSIONS,
    MAX_IMAGE_SIZE_MB,
    AUTH_ENABLED,
    AUTH_TOKEN,
    POSITION_UPDATE_INTERVAL_SEC,
    POSITION_MOVE_RANGE,
    LLM_ENABLED,
    LLM_PROVIDER,
    LLM_MODEL,
    LLM_TIMEOUT_SEC,
    LLM_MAX_RETRIES,
    LLM_POLL_INTERVAL_SEC,
)

app = Flask(__name__)

VUE_DIST_DIR = os.path.join(app.root_path, "vue-app", "dist")
VUE_ASSETS_DIR = os.path.join(VUE_DIST_DIR, "assets")
STATIC_DIR = os.path.join(app.root_path, "static")
app.config["MAX_CONTENT_LENGTH"] = MAX_IMAGE_SIZE_MB * 1024 * 1024  # 全局文件大小限制

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
    log_event(
        "WARNING",
        "auth.failed.rest",
        "sec",
        "app",
        "REST API authentication failed",
        error="Token invalid or missing",
        extra={"path": request.path, "ip": request.remote_addr},
    )
    return jsonify({"message": "鉴权失败：Token 无效或缺失"}), 401


# 初始化数据库
try:
    db.init_db()
    log_event(
        "INFO", "system.db.init", "ops", "app", "Database initialized successfully"
    )
except Exception as e:
    log_event(
        "CRITICAL",
        "system.init.failed",
        "ops",
        "app",
        f"Database initialization failed: {str(e)}",
    )
    raise

# 启动MQTT客户端
mqtt_client.set_socketio(socketio)
try:
    mqtt_client_inst = mqtt_client.start_mqtt()
    log_event(
        "INFO", "system.mqtt.start", "ops", "app", "MQTT client started successfully"
    )
except Exception as exc:
    log_event(
        "CRITICAL",
        "system.init.failed",
        "ops",
        "app",
        f"MQTT client start failed: {str(exc)}",
    )
    sys.exit(1)


def offline_check_loop():
    """
    后台离线检测循环 (恢复为版本2的 time.sleep)
    """
    log_event(
        "INFO",
        "system.background.offline_check_started",
        "ops",
        "app",
        "Offline detection loop started",
        extra={"interval_sec": OFFLINE_CHECK_INTERVAL_SEC},
    )
    while True:
        try:
            time.sleep(OFFLINE_CHECK_INTERVAL_SEC)

            devices = db.get_all_devices()
            now = datetime.now()
            changed = False

            for dev in devices:
                if dev["online_status"] == 1:
                    last_seen_time = datetime.strptime(
                        dev["last_seen"], "%Y-%m-%d %H:%M:%S"
                    )
                    offline_seconds = (now - last_seen_time).total_seconds()

                    if offline_seconds > OFFLINE_TIMEOUT_SEC:
                        db.set_device_offline(dev["device_id"])
                        log_event(
                            "WARNING",
                            "device.status.offline_marked",
                            "biz",
                            "app",
                            f"Device marked offline",
                            device_id=dev["device_id"],
                            extra={"offline_seconds": offline_seconds},
                        )
                        changed = True

            if changed:
                full_data = db.get_latest_data_with_stats()
                socketio.emit("device_update", full_data)
                log_event(
                    "INFO",
                    "socket.broadcast.device_update",
                    "ops",
                    "app",
                    "Broadcasted device_update (offline event)",
                )

        except Exception as e:
            log_event(
                "ERROR",
                "system.background.offline_check_failed",
                "ops",
                "app",
                f"Offline check loop error: {str(e)}",
            )


# 启动后台检测线程
socketio.start_background_task(offline_check_loop)


def position_broadcast_loop():
    """
    位置信息推送循环
    定期从数据库读取设备位置并推送给前端
    注意：位置更新由 publish_test.py 写入数据库
    """
    log_event(
        "INFO",
        "system.background.position_broadcast_started",
        "ops",
        "app",
        "Position broadcast loop started",
    )

    while True:
        try:
            time.sleep(POSITION_UPDATE_INTERVAL_SEC)

            # 从数据库获取最新位置
            devices_data = db.get_all_devices_with_positions()
            socketio.emit("position_update", devices_data)

        except Exception as e:
            log_event(
                "ERROR",
                "system.background.position_broadcast_failed",
                "ops",
                "app",
                f"Position broadcast error: {str(e)}",
            )


# 启动位置推送线程
socketio.start_background_task(position_broadcast_loop)


def _resolve_alarm_image_path(image_path):
    if not image_path:
        return None
    if not db._is_safe_image_path(image_path):
        return None
    abs_path = os.path.abspath(image_path)
    if not os.path.isfile(abs_path):
        return None
    return abs_path


def _fallback_analysis_for_error(error_text):
    """Return a short, honest placeholder when the upstream AI service is unreachable."""
    if not error_text:
        return None
    lower = str(error_text).lower()
    network_markers = (
        "connection error",
        "apiconnectionerror",
        "ssl",
        "tls",
        "wrong version number",
        "unexpected eof while reading",
        "connecterror",
        "relay blocked image request",
        "http 468",
    )
    if any(marker in lower for marker in network_markers):
        return "AI服务暂不可用"
    return None


def alarm_image_description_loop():
    """
    后台异步生成报警图片分析
    """
    if not LLM_ENABLED:
        return
    if (LLM_PROVIDER or "").lower() != "openai":
        log_event(
            "ERROR",
            "llm.provider.unsupported",
            "ops",
            "llm",
            f"Unsupported LLM provider: {LLM_PROVIDER}",
        )
        return

    log_event(
        "INFO",
        "llm.image.analysis.started",
        "ops",
        "llm",
        "Alarm image analysis loop started",
        extra={"model": LLM_MODEL, "poll_sec": LLM_POLL_INTERVAL_SEC},
    )

    while True:
        try:
            time.sleep(LLM_POLL_INTERVAL_SEC)
            pending = db.get_pending_alarm_images(limit=5)
            for item in pending:
                image_id = item.get("id")
                device_id = item.get("device_id")
                image_path = item.get("image_path")

                abs_path = _resolve_alarm_image_path(image_path)
                if not abs_path:
                    db.mark_alarm_image_failed(
                        image_id,
                        "Invalid or missing image path",
                        LLM_MODEL,
                    )
                    continue

                analysis = None
                last_error = None
                for _ in range(max(1, LLM_MAX_RETRIES)):
                    try:
                        analysis = analyze_alarm_image(abs_path)
                        break
                    except Exception as exc:
                        last_error = str(exc)
                        time.sleep(1)

                if analysis:
                    db.mark_alarm_image_description(image_id, analysis, LLM_MODEL)
                    log_event(
                        "INFO",
                        "llm.image.analysis.generated",
                        "biz",
                        "llm",
                        f"AI分析：{analysis}",
                        device_id=device_id,
                        extra={
                            "image_path": image_path,
                            "model": LLM_MODEL,
                            "analysis": analysis,
                        },
                    )
                else:
                    fallback_analysis = _fallback_analysis_for_error(last_error)
                    if fallback_analysis:
                        db.mark_alarm_image_description(
                            image_id, fallback_analysis, "fallback-unavailable"
                        )
                        log_event(
                            "WARNING",
                            "llm.image.analysis.fallback",
                            "biz",
                            "llm",
                            f"AI分析降级：{fallback_analysis}",
                            device_id=device_id,
                            error=last_error or "LLM unavailable",
                            extra={"image_path": image_path},
                        )
                    else:
                        db.mark_alarm_image_failed(
                            image_id,
                            last_error or "LLM failed",
                            LLM_MODEL,
                        )
                        log_event(
                            "ERROR",
                            "llm.image.analysis.failed",
                            "ops",
                            "llm",
                            "Alarm image analysis failed",
                            device_id=device_id,
                            error=last_error or "LLM failed",
                            extra={"image_path": image_path},
                        )

        except Exception as e:
            log_event(
                "ERROR",
                "llm.image.analysis.loop_failed",
                "ops",
                "llm",
                f"LLM analysis loop error: {str(e)}",
            )


if LLM_ENABLED:
    socketio.start_background_task(alarm_image_description_loop)


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
        log_event(
            "WARNING",
            "auth.failed.ws",
            "sec",
            "app",
            "SocketIO authentication failed",
            error="Token invalid or missing",
            extra={"sid": request.sid, "ip": request.remote_addr},
        )
        raise ConnectionRefusedError("鉴权失败：Socket Token 无效或缺失")
    log_event(
        "INFO",
        "socket.client.connected",
        "ops",
        "app",
        "SocketIO client connected",
        sid=request.sid,
    )


@socketio.on("disconnect")
def handle_disconnect():
    """WebSocket 断开事件"""
    log_event(
        "INFO",
        "socket.client.disconnected",
        "ops",
        "app",
        "SocketIO client disconnected",
        sid=request.sid,
    )


def _vue_dist_ready():
    return os.path.isfile(os.path.join(VUE_DIST_DIR, "index.html"))


def _attach_auth_cookie(resp):
    if AUTH_ENABLED and AUTH_TOKEN:
        resp.set_cookie("app_auth_token", AUTH_TOKEN, samesite="Lax")
    else:
        resp.delete_cookie("app_auth_token")
    return resp


@app.route("/")
def index():
    """返回Vue前端的index.html"""
    if _vue_dist_ready():
        resp = make_response(send_from_directory(VUE_DIST_DIR, "index.html"))
        return _attach_auth_cookie(resp)
    abort(404)


@app.route("/devices")
def devices_page():
    """返回Vue前端的index.html"""
    if _vue_dist_ready():
        resp = make_response(send_from_directory(VUE_DIST_DIR, "index.html"))
        return _attach_auth_cookie(resp)
    abort(404)


@app.route("/logs")
def logs_page():
    """返回Vue前端的index.html"""
    if _vue_dist_ready():
        resp = make_response(send_from_directory(VUE_DIST_DIR, "index.html"))
        return _attach_auth_cookie(resp)
    abort(404)




@app.route("/trend")
def trend_page():
    """返回Vue前端的index.html"""
    if _vue_dist_ready():
        resp = make_response(send_from_directory(VUE_DIST_DIR, "index.html"))
        return _attach_auth_cookie(resp)
    abort(404)

@app.route("/assets/<path:path>")
def serve_assets(path):
    """提供Vue前端的静态资源"""
    if not _vue_dist_ready():
        abort(404)
    return send_from_directory(VUE_ASSETS_DIR, path)


@app.route("/vite.svg")
def serve_vite_svg():
    """提供Vite的SVG图标"""
    if _vue_dist_ready() and os.path.isfile(os.path.join(VUE_DIST_DIR, "vite.svg")):
        return send_from_directory(VUE_DIST_DIR, "vite.svg")
    return send_from_directory(STATIC_DIR, "vite.svg")


@app.route("/Dashboard.png")
def serve_dashboard_png():
    """兼容前端历史路径：返回 Dashboard 背景图。"""
    return send_from_directory(app.root_path, "map.jpg")


@app.route("/api/latest")
def get_latest():
    auth_failed = require_auth()
    if auth_failed:
        return auth_failed
    data = db.get_latest_data_with_stats()
    return jsonify(data)


@app.route("/api/logs")
def get_logs_route():
    """暴露给前端访问所有日志（支持分页和筛选）"""
    auth_failed = require_auth()
    if auth_failed:
        return auth_failed

    # 获取分页参数（默认第1页，每页20条）
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))

    # 获取筛选参数
    level = request.args.get("level", "").strip() or None
    device_id = request.args.get("device_id", "").strip() or None
    category = request.args.get("category", "").strip() or None

    # 分页查询日志（支持筛选）
    log_data = get_logs_by_page(page, page_size, level, device_id, category)
    return jsonify(log_data)


# 兼容旧接口
@app.route("/api/biz_logs")
def get_biz_logs_route():
    """兼容旧接口：仅返回业务日志"""
    return get_logs_route()


@app.route("/api/device/<device_id>/history")
def get_device_history(device_id):
    """返回设备详情，包括原始历史和趋势统计"""
    auth_failed = require_auth()
    if auth_failed:
        return auth_failed

    # 趋势聚合数据
    trend = db.get_device_alarm_trend(device_id, limit=TREND_LIMIT)
    # 当天每小时报警次数（用于设备详情图表）。
    hourly = db.get_device_alarm_hourly_today(device_id)
    # 原始明细记录
    raw_history = db.get_device_history_raw(device_id, limit=HISTORY_LIMIT)

    # 转换为前端期望的格式：保留机器字段并补充事件文本
    history = []
    for item in raw_history:
        alarm_value = 1 if item.get("alarm") == 1 else 0
        history.append(
            {
                "timestamp": item.get("timestamp", ""),
                "alarm": alarm_value,
                "alarm_status": alarm_value,
                "event": "报警" if alarm_value == 1 else "正常",
            }
        )

    return jsonify(
        {
            "device_id": device_id,
            "labels": trend["labels"],
            "counts": trend["counts"],
            "hourly_labels": hourly["labels"],
            "hourly_counts": hourly["counts"],
            "history": history,
        }
    )


@app.route("/api/device/<device_id>/images")
def get_device_images(device_id):
    """获取设备的报警图片列表"""
    auth_failed = require_auth()
    if auth_failed:
        return auth_failed

    limit = int(request.args.get("limit", 20))
    images = db.get_device_images(device_id, limit=limit)
    return jsonify({"device_id": device_id, "images": images})


@app.route("/api/device/<device_id>/latest-image")
def get_latest_image(device_id):
    """获取设备的最新报警图片"""
    auth_failed = require_auth()
    if auth_failed:
        return auth_failed

    image = db.get_latest_image(device_id)
    return jsonify(image if image else {})


@app.route("/images/<path:filename>")
def serve_image(filename):
    """提供图片访问服务"""
    return send_from_directory("images", filename)


# ============图片上传接口（MQTT+HTTP混合方案）============


def _allowed_image_file(filename):
    """检查文件扩展名是否在允许列表中"""
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in ALLOWED_IMAGE_EXTENSIONS


@app.route("/api/upload-image-legacy", methods=["POST"])
def upload_image_legacy():
    return jsonify({"error": "单图上传已废弃，请使用 /api/upload-image 批量上传"}), 410
    """
    接收设备上传的报警图片
    用于MQTT+HTTP混合方案：设备先通过HTTP上传图片，再通过MQTT发送报警+图片URL
    
    请求参数（multipart/form-data）：
    - device_id: 设备ID
    - image: 图片文件
    
    返回：
    - image_url: 图片访问URL
    """
    # 暂时不启用鉴权，允许设备直接上传图片
    # 如需鉴权，可取消注释下一行：auth_failed = require_auth()
    # if auth_failed: return auth_failed

    # 获取设备ID
    device_id = request.form.get("device_id")
    if not device_id:
        return jsonify({"error": "缺少device_id参数"}), 400

    # 路径遍历防护：清理 device_id 中的非法字符
    device_id = re.sub(r"[^\w\-]", "", device_id)
    if not device_id:
        return jsonify({"error": "无效的device_id"}), 400

    # 获取图片文件
    image_file = request.files.get("image")
    if not image_file:
        return jsonify({"error": "缺少image参数"}), 400

    # 文件类型验证
    if not _allowed_image_file(image_file.filename):
        return jsonify({"error": "不支持的图片格式"}), 400

    # 文件大小限制
    image_file.seek(0, 2)  # 跳到文件末尾
    file_size = image_file.tell()  # 获取文件大小
    image_file.seek(0)  # 回到文件开头

    max_size_bytes = MAX_IMAGE_SIZE_MB * 1024 * 1024
    if file_size > max_size_bytes:
        return jsonify({"error": f"文件大小超过{MAX_IMAGE_SIZE_MB}MB限制"}), 400

    # 生成文件名：设备ID_时间戳.jpg
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{device_id}_{timestamp}.jpg"
    filepath = os.path.join("images", "alarms", filename)

    try:
        # 保存图片文件
        image_file.save(filepath)

        # 获取时间戳（用于数据库记录）
        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 保存到数据库
        db.save_alarm_image(device_id, filepath, timestamp_str)

        # 记录日志
        log_event(
            "INFO",
            "device.image.uploaded",
            "biz",
            "app",
            "Image uploaded via HTTP",
            device_id=device_id,
            extra={"image_path": filepath},
        )

        # 返回图片URL
        image_url = f"/images/alarms/{filename}"
        return jsonify({"image_url": image_url})

    except Exception as e:
        log_event(
            "ERROR",
            "device.image.upload_failed",
            "biz",
            "app",
            "Image upload failed",
            device_id=device_id,
            error=str(e),
        )
        return jsonify({"error": f"图片上传失败: {str(e)}"}), 500


@app.route("/api/upload-image", methods=["POST"])
def upload_image():
    """
    批量上传报警图片（仅批量）
    multipart/form-data:
    - device_id: 设备ID
    - images: 多文件列表
    - base_timestamp: 可选，最后一张的时间（%Y-%m-%d %H:%M:%S）
    - image_timestamps: 可选，JSON数组，逐张时间戳
    返回：
    - image_urls: 图片URL数组（顺序与上传一致）
    """
    # 设备端直传，暂不启用鉴权
    # auth_failed = require_auth()
    # if auth_failed: return auth_failed

    device_id = request.form.get("device_id")
    if not device_id:
        return jsonify({"error": "缺少device_id参数"}), 400

    device_id = re.sub(r"[^\w\-]", "", device_id)
    if not device_id:
        return jsonify({"error": "无效的device_id"}), 400

    if request.files.get("image"):
        return jsonify({"error": "单图上传已禁用，请使用images批量上传"}), 400

    image_files = request.files.getlist("images")
    if not image_files:
        return jsonify({"error": "缺少images参数"}), 400

    base_timestamp_raw = (request.form.get("base_timestamp") or "").strip()
    image_timestamps_raw = (request.form.get("image_timestamps") or "").strip()
    timestamps = []

    try:
        if image_timestamps_raw:
            ts_list = json.loads(image_timestamps_raw)
            if not isinstance(ts_list, list):
                return jsonify({"error": "image_timestamps必须是JSON数组"}), 400
            if len(ts_list) != len(image_files):
                return jsonify({"error": "image_timestamps长度与图片数量不匹配"}), 400
            for ts in ts_list:
                timestamps.append(datetime.strptime(str(ts), "%Y-%m-%d %H:%M:%S"))
        else:
            if base_timestamp_raw:
                base_dt = datetime.strptime(base_timestamp_raw, "%Y-%m-%d %H:%M:%S")
            else:
                base_dt = datetime.now()
            total = len(image_files)
            for i in range(total):
                delta_sec = total - 1 - i
                timestamps.append(base_dt - timedelta(seconds=delta_sec))
    except ValueError:
        return jsonify({"error": "时间格式错误，请使用 YYYY-MM-DD HH:MM:SS"}), 400
    except json.JSONDecodeError:
        return jsonify({"error": "image_timestamps JSON解析失败"}), 400

    image_urls = []
    try:
        for idx, image_file in enumerate(image_files):
            if not _allowed_image_file(image_file.filename):
                return jsonify({"error": "不支持的图片格式"}), 400

            image_file.seek(0, 2)
            file_size = image_file.tell()
            image_file.seek(0)

            max_size_bytes = MAX_IMAGE_SIZE_MB * 1024 * 1024
            if file_size > max_size_bytes:
                return jsonify({"error": f"文件大小超过{MAX_IMAGE_SIZE_MB}MB限制"}), 400

            ts = timestamps[idx]
            ts_str = ts.strftime("%Y-%m-%d %H:%M:%S")
            safe_ts = ts.strftime("%Y-%m-%d_%H-%M-%S")
            ext = image_file.filename.rsplit(".", 1)[1].lower()
            filename = f"{device_id}_{safe_ts}_{idx}.{ext}"
            filepath = os.path.join("images", "alarms", filename)

            image_file.save(filepath)

            db.save_alarm_image(device_id, filepath, ts_str)
            log_event(
                "INFO",
                "device.image.uploaded",
                "biz",
                "app",
                "Image uploaded via HTTP",
                device_id=device_id,
                extra={"image_path": filepath},
            )

            image_urls.append(f"/images/alarms/{filename}")

        return jsonify({"image_urls": image_urls})

    except Exception as e:
        log_event(
            "ERROR",
            "device.image.upload_failed",
            "biz",
            "app",
            "Image upload failed",
            device_id=device_id,
            error=str(e),
        )
        return jsonify({"error": f"图片上传失败: {str(e)}"}), 500


@app.route("/map.jpg")
def serve_dashboard_map():
    """提供工厂地图图片"""
    # 允许 ECharts 直接加载图片，不附加鉴权逻辑。
    return send_from_directory(app.root_path, "map.jpg")


# =========================
# Dashboard 数据接口
# =========================


@app.route("/api/devices")
def get_devices():
    """获取所有设备位置和状态（Dashboard用）"""
    auth_failed = require_auth()
    if auth_failed:
        return auth_failed

    devices = db.get_all_devices_with_positions()
    return jsonify({"devices": devices})


@app.route("/api/recent-alarms")
def get_recent_alarms():
    """获取最近报警事件（Dashboard用）"""
    auth_failed = require_auth()
    if auth_failed:
        return auth_failed

    limit = int(request.args.get("limit", 10))
    alarms = db.get_recent_alarms(limit=limit)

    devices = {d["device_id"]: d for d in db.get_all_devices_with_positions()}

    for alarm in alarms:
        device = devices.get(alarm["device_id"], {})
        pos_x = device.get("pos_x", 0) or 0
        pos_y = device.get("pos_y", 0) or 0
        if pos_x < 600:
            alarm["zone"] = "A区" if pos_y < 500 else "C区"
        else:
            alarm["zone"] = "B区" if pos_y < 500 else "D区"

    for alarm in alarms:
        alarm["description"] = alarm.pop("image_description", None)
        alarm["description_status"] = alarm.pop("image_description_status", None)

    return jsonify({"alarms": alarms})


@app.route("/api/dashboard/alarm-trend")
def get_dashboard_alarm_trend():
    """Dashboard 报警趋势：今日/昨日每小时报警次数（全设备）"""
    auth_failed = require_auth()
    if auth_failed:
        return auth_failed

    trend = db.get_alarm_hourly_today_yesterday()
    return jsonify(trend)


@app.route("/api/device/<device_id>/alarm-sessions")
def get_device_alarm_sessions(device_id):
    auth_failed = require_auth()
    if auth_failed:
        return auth_failed

    limit = int(request.args.get("limit", 20))
    sessions = db.get_alarm_sessions(device_id, limit=limit)
    stats = db.get_alarm_duration_stats(device_id)
    active = db.get_active_alarm_session(device_id)

    current_duration = None
    if active:
        start_dt = datetime.strptime(active["start_time"], "%Y-%m-%d %H:%M:%S")
        current_duration = (datetime.now() - start_dt).total_seconds()

    return jsonify(
        {
            "device_id": device_id,
            "sessions": sessions,
            "stats": stats,
            "active_session": active,
            "current_duration_sec": round(current_duration, 1)
            if current_duration
            else None,
        }
    )

@app.route('/api/trend')
def trend():
    import random
    from flask import request, jsonify

    auth_failed = require_auth()
    if auth_failed:
        return auth_failed

    t = request.args.get('type', 'day')

    # ===== 时间轴 =====
    if t == 'day':
        labels = [f"{i}:00" for i in range(24)]
    elif t == 'week':
        labels = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']
    else:
        labels = [str(i+1) for i in range(30)]

    # ===== 模拟 publish_test 的报警逻辑 =====
    def gen():
        state = 0
        data = []
        for _ in labels:
            if state == 1:
                state = 1 if random.random() < 0.7 else 0
            else:
                state = 1 if random.random() < 0.15 else 0

            val = random.randint(1, 3) if state == 1 else random.randint(0, 1)
            data.append(val)
        return data

    return jsonify({
        "labels": labels,
        "fork1": gen(),
        "fork2": gen(),
        "fork3": gen()
    })


if __name__ == "__main__":
    log_event(
        "INFO", "system.app.starting", "ops", "app", "Flask + SocketIO app starting"
    )
    print("Starting Flask + SocketIO app on http://0.0.0.0:5000")
    socketio.run(app, host="0.0.0.0", port=5000, debug=False)
