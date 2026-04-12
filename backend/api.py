"""FastAPI routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from backend.paths import FRONTEND_ASSETS_DIR, FRONTEND_DIST_DIR, ROOT_DIR, STATIC_DIR
from backend.services import app_service

router = APIRouter()
SPA_ROUTES = ["/", "/devices", "/logs", "/history", "/trend"]


def _index_response():
    index_file = FRONTEND_DIST_DIR / "index.html"
    if not index_file.is_file():
        raise HTTPException(status_code=404, detail="Frontend build not found")
    return FileResponse(index_file)


@router.get("/api/latest")
async def api_latest():
    return JSONResponse(app_service.get_latest_payload())


@router.get("/api/logs")
async def api_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    level: str | None = None,
    device_id: str | None = None,
    category: str | None = None,
):
    return JSONResponse(app_service.get_logs_payload(page, page_size, level, device_id, category))


@router.get("/api/biz_logs")
async def api_biz_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    level: str | None = None,
    device_id: str | None = None,
):
    return JSONResponse(app_service.get_logs_payload(page, page_size, level, device_id, "biz"))


@router.get("/api/device/{device_id}/history")
async def api_device_history(device_id: str):
    return JSONResponse(app_service.get_device_history_payload(device_id))


@router.get("/api/device/{device_id}/images")
async def api_device_images(device_id: str, limit: int = Query(20, ge=1, le=200)):
    return JSONResponse(app_service.get_device_images_payload(device_id, limit))


@router.get("/api/device/{device_id}/latest-image")
async def api_device_latest_image(device_id: str):
    return JSONResponse(app_service.get_device_latest_image_payload(device_id))


@router.post("/api/upload-image-legacy")
async def api_upload_image_legacy():
    return JSONResponse({"error": "单图上传已废弃，请使用 /api/upload-image 批量上传"}, status_code=410)


@router.post("/api/upload-image")
async def api_upload_image(
    device_id: str = Form(...),
    base_timestamp: str = Form(""),
    image_timestamps: str = Form(""),
    images: list[UploadFile] = File(...),
):
    payload = await app_service.save_uploaded_images(device_id, images, base_timestamp.strip(), image_timestamps.strip())
    return JSONResponse(payload)


@router.get("/api/devices")
async def api_devices():
    return JSONResponse(app_service.get_devices_payload())


@router.get("/api/recent-alarms")
async def api_recent_alarms(limit: int = Query(10, ge=1, le=200)):
    return JSONResponse(app_service.get_recent_alarms_payload(limit))


@router.get("/api/history")
async def api_history(limit: int = Query(50, ge=1, le=500)):
    return JSONResponse(app_service.get_history_payload(limit))


@router.get("/api/dashboard/alarm-trend")
async def api_dashboard_alarm_trend():
    return JSONResponse(app_service.get_dashboard_alarm_trend_payload())


@router.get("/api/device/{device_id}/alarm-sessions")
async def api_device_alarm_sessions(device_id: str, limit: int = Query(20, ge=1, le=200)):
    return JSONResponse(app_service.get_device_alarm_sessions_payload(device_id, limit))


@router.get("/api/trend")
async def api_trend(type: str = Query("day")):
    return JSONResponse(app_service.get_trend_payload(type))


@router.get("/images/{file_path:path}")
async def serve_image(file_path: str):
    file = ROOT_DIR / "images" / file_path
    if not file.is_file():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(file)


@router.get("/Dashboard.png")
async def serve_dashboard_png():
    return FileResponse(ROOT_DIR / "map.jpg")


@router.get("/map.jpg")
async def serve_map_jpg():
    return FileResponse(ROOT_DIR / "map.jpg")


@router.get("/vite.svg")
async def serve_vite_svg():
    dist_svg = FRONTEND_DIST_DIR / "vite.svg"
    if dist_svg.is_file():
        return FileResponse(dist_svg)
    fallback = STATIC_DIR / "vite.svg"
    if fallback.is_file():
        return FileResponse(fallback)
    raise HTTPException(status_code=404, detail="vite.svg not found")


@router.get("/assets/{asset_path:path}")
async def serve_asset(asset_path: str):
    file = FRONTEND_ASSETS_DIR / asset_path
    if not file.is_file():
        raise HTTPException(status_code=404, detail="Asset not found")
    return FileResponse(file)


def register_routes(app: FastAPI):
    app.include_router(router)
    for route in SPA_ROUTES:
        app.add_api_route(route, _index_response, methods=["GET"], include_in_schema=False)
