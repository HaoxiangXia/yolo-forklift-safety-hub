"""FastAPI + Socket.IO application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import register_routes
from backend.realtime import sio
from backend.workers import WorkerManager

worker_manager = WorkerManager(sio)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await worker_manager.start()
    try:
        yield
    finally:
        await worker_manager.stop()


fastapi_app = FastAPI(title="Forklift Safety Hub API", lifespan=lifespan)
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
register_routes(fastapi_app)
app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)
