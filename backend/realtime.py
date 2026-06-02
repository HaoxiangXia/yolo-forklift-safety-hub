"""Realtime Socket.IO server helpers."""

from __future__ import annotations

import socketio

from logger import log_event

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")


@sio.event
async def connect(sid, environ, auth):
    log_event("INFO", "socket.client.connected", "ops", "socketio", "SocketIO client connected", sid=sid)


@sio.event
async def disconnect(sid):
    log_event("INFO", "socket.client.disconnected", "ops", "socketio", "SocketIO client disconnected", sid=sid)


@sio.event
async def edge_node_update(sid, payload):
    """Accept demo edge-node updates and fan out dashboard refresh events."""
    from backend.services import app_service

    payload = payload if isinstance(payload, dict) else {}
    devices = payload.get("devices")
    status_changed = bool(payload.get("status_changed"))

    if not isinstance(devices, list):
        devices = app_service.get_latest_payload().get("devices", [])
    await sio.emit("position_update", devices)

    if status_changed:
        await sio.emit("device_update", app_service.get_latest_payload())
        log_event(
            "INFO",
            "socket.edge_node_status_changed",
            "ops",
            "socketio",
            "Edge node status change broadcast",
            sid=sid,
            extra={
                "mode": payload.get("mode"),
                "image_url": payload.get("image_url"),
                "devices": [
                    {
                        "device_id": item.get("device_id"),
                        "alarm_status": item.get("alarm_status"),
                    }
                    for item in devices
                    if isinstance(item, dict)
                ],
            },
        )
