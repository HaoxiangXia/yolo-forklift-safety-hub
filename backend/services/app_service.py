"""Business services for the FastAPI backend."""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import HTTPException, UploadFile

from config import ALLOWED_IMAGE_EXTENSIONS, HISTORY_LIMIT, MAX_IMAGE_SIZE_MB, TREND_LIMIT
from llm_client import analyze_alarm_image
from logger import get_logs_by_page, log_event
from backend.paths import ALARMS_IMAGE_DIR, ROOT_DIR
from backend.repositories import database as repo

DEVICE_IDS = ["FORK-001", "FORK-002", "FORK-003"]


def sanitize_device_id(device_id: str) -> str:
    cleaned = re.sub(r"[^\w\-]", "", device_id or "")
    if not cleaned:
        raise HTTPException(status_code=400, detail="无效的device_id")
    return cleaned


def allowed_image_file(filename: str) -> bool:
    if not filename or "." not in filename:
        return False
    return filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def decorate_alarm_records(alarms, devices=None):
    devices = devices or {d["device_id"]: d for d in repo.get_all_devices_with_positions()}
    for alarm in alarms:
        device = devices.get(alarm["device_id"], {})
        pos_x = device.get("pos_x", 0) or 0
        pos_y = device.get("pos_y", 0) or 0
        if pos_x < 600:
            alarm["zone"] = "A区" if pos_y < 500 else "C区"
        else:
            alarm["zone"] = "B区" if pos_y < 500 else "D区"
        alarm["description"] = alarm.pop("image_description", None)
        alarm["description_status"] = alarm.pop("image_description_status", None)
    return alarms


def get_latest_payload():
    return repo.get_latest_data_with_stats()


def get_logs_payload(page: int, page_size: int, level: str | None, device_id: str | None, category: str | None):
    return get_logs_by_page(page, page_size, level, device_id, category)


def get_device_history_payload(device_id: str):
    trend = repo.get_device_alarm_trend(device_id, limit=TREND_LIMIT)
    hourly = repo.get_device_alarm_hourly_today(device_id)
    raw_history = repo.get_device_history_raw(device_id, limit=HISTORY_LIMIT)
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
    return {
        "device_id": device_id,
        "labels": trend["labels"],
        "counts": trend["counts"],
        "hourly_labels": hourly["labels"],
        "hourly_counts": hourly["counts"],
        "history": history,
    }


def get_device_images_payload(device_id: str, limit: int):
    return {"device_id": device_id, "images": repo.get_device_images(device_id, limit=limit)}


def get_device_latest_image_payload(device_id: str):
    return repo.get_latest_image(device_id) or {}


def get_devices_payload():
    return {"devices": repo.get_all_devices_with_positions()}


def get_recent_alarms_payload(limit: int):
    alarms = repo.get_recent_alarms(limit=limit)
    devices = {d["device_id"]: d for d in repo.get_all_devices_with_positions()}
    return {"alarms": decorate_alarm_records(alarms, devices)}


def get_history_payload(limit: int):
    alarms = repo.get_recent_alarms(limit=limit)
    devices = {d["device_id"]: d for d in repo.get_all_devices_with_positions()}
    return {"items": decorate_alarm_records(alarms, devices)}


def get_dashboard_alarm_trend_payload():
    return repo.get_alarm_hourly_today_yesterday()


def get_device_alarm_sessions_payload(device_id: str, limit: int):
    sessions = repo.get_alarm_sessions(device_id, limit=limit)
    stats = repo.get_alarm_duration_stats(device_id)
    active = repo.get_active_alarm_session(device_id)
    current_duration = None
    if active:
        start_dt = datetime.strptime(active["start_time"], "%Y-%m-%d %H:%M:%S")
        current_duration = (datetime.now() - start_dt).total_seconds()
    return {
        "device_id": device_id,
        "sessions": sessions,
        "stats": stats,
        "active_session": active,
        "current_duration_sec": round(current_duration, 1) if current_duration else None,
    }


def get_trend_payload(range_type: str):
    trend_data = repo.get_alarm_trend_multi_device(range_type, DEVICE_IDS)
    labels = trend_data.get("labels", []) or []
    series = trend_data.get("series", {}) or {}
    return {
        "labels": labels,
        "fork1": series.get(DEVICE_IDS[0], []),
        "fork2": series.get(DEVICE_IDS[1], []),
        "fork3": series.get(DEVICE_IDS[2], []),
    }


async def save_uploaded_images(device_id: str, image_files: list[UploadFile], base_timestamp_raw: str, image_timestamps_raw: str):
    device_id = sanitize_device_id(device_id)
    if not image_files:
        raise HTTPException(status_code=400, detail="缺少images参数")
    timestamps = []
    try:
        if image_timestamps_raw:
            ts_list = json.loads(image_timestamps_raw)
            if not isinstance(ts_list, list):
                raise HTTPException(status_code=400, detail="image_timestamps必须是JSON数组")
            if len(ts_list) != len(image_files):
                raise HTTPException(status_code=400, detail="image_timestamps长度与图片数量不匹配")
            timestamps = [datetime.strptime(str(ts), "%Y-%m-%d %H:%M:%S") for ts in ts_list]
        else:
            base_dt = datetime.strptime(base_timestamp_raw, "%Y-%m-%d %H:%M:%S") if base_timestamp_raw else datetime.now()
            total = len(image_files)
            timestamps = [base_dt.replace() for _ in range(total)]
            for i in range(total):
                timestamps[i] = base_dt - timedelta(seconds=total - 1 - i)
    except ValueError:
        raise HTTPException(status_code=400, detail="时间格式错误，请使用 YYYY-MM-DD HH:MM:SS")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="image_timestamps JSON解析失败")

    image_urls = []
    max_size_bytes = MAX_IMAGE_SIZE_MB * 1024 * 1024
    for idx, image_file in enumerate(image_files):
        if not allowed_image_file(image_file.filename or ""):
            raise HTTPException(status_code=400, detail="不支持的图片格式")
        content = await image_file.read()
        if len(content) > max_size_bytes:
            raise HTTPException(status_code=400, detail=f"文件大小超过{MAX_IMAGE_SIZE_MB}MB限制")
        ts = timestamps[idx]
        ts_str = ts.strftime("%Y-%m-%d %H:%M:%S")
        safe_ts = ts.strftime("%Y-%m-%d_%H-%M-%S")
        ext = (image_file.filename or "jpg").rsplit(".", 1)[1].lower()
        filename = f"{device_id}_{safe_ts}_{idx}.{ext}"
        filepath = ALARMS_IMAGE_DIR / filename
        filepath.write_bytes(content)
        image_path = str(Path("images") / "alarms" / filename)
        repo.save_alarm_image(device_id, image_path, ts_str)
        log_event("INFO", "device.image.uploaded", "biz", "api", "Image uploaded via HTTP", device_id=device_id, extra={"image_path": image_path})
        image_urls.append(f"/images/alarms/{filename}")
    return {"image_urls": image_urls}


def resolve_local_image_path(image_path: str) -> Path | None:
    if not image_path:
        return None
    normalized = image_path[1:] if image_path.startswith("/") else image_path
    path = ROOT_DIR / normalized
    if repo.is_safe_image_path(str(path)):
        return path
    return None


def analyze_pending_images_batch(limit: int = 10):
    for item in repo.get_pending_alarm_images(limit=limit):
        image_path = item.get("image_path", "")
        image_id = item.get("id")
        device_id = item.get("device_id")
        local_path = resolve_local_image_path(image_path)
        if not local_path or not local_path.exists():
            repo.mark_alarm_image_failed(image_id, "Image not found", "filesystem")
            continue
        try:
            analysis = analyze_alarm_image(str(local_path))
            repo.mark_alarm_image_description(image_id, analysis, "llm")
            log_event("INFO", "llm.image.analysis.generated", "biz", "llm", f"AI分析：{analysis}", device_id=device_id, extra={"image_path": image_path})
        except Exception as exc:
            repo.mark_alarm_image_failed(image_id, str(exc), "llm")
            log_event("ERROR", "llm.image.analysis.failed", "ops", "llm", "Alarm image analysis failed", device_id=device_id, error=str(exc), extra={"image_path": image_path})


def process_mqtt_payload(topic: str, payload: dict):
    topic_parts = topic.split("/")
    device_id = topic_parts[2] if len(topic_parts) >= 3 else payload.get("device_id", "unknown")
    alarm = payload.get("alarm", 0)
    timestamp = payload.get("timestamp", "")
    changed = repo.update_device_data(device_id=device_id, alarm=alarm, mqtt_timestamp=timestamp)
    image_urls = payload.get("image_urls", [])
    if alarm == 1 and isinstance(image_urls, list):
        for image_url in image_urls:
            if not isinstance(image_url, str):
                continue
            image_path = image_url[1:] if image_url.startswith("/") else image_url
            repo.save_alarm_image(device_id, image_path, timestamp)
    elif alarm == 1 and payload.get("image_url"):
        image_url = str(payload["image_url"])
        image_path = image_url[1:] if image_url.startswith("/") else image_url
        repo.save_alarm_image(device_id, image_path, timestamp)
    log_event("INFO", "mqtt.message.processed", "biz", "mqtt", "MQTT message processed and DB updated", device_id=device_id, topic=topic, extra={"changed": changed})
