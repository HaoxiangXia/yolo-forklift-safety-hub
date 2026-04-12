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
