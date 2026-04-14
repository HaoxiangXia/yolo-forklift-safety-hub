"""Background workers for MQTT and periodic jobs."""

from __future__ import annotations

import asyncio
import json
import random
import threading
import time

import paho.mqtt.client as mqtt

from config import (
    LLM_ENABLED,
    LLM_POLL_INTERVAL_SEC,
    MQTT_BROKER,
    MQTT_PORT,
    MQTT_REQUIRED,
    MQTT_TOPIC,
    OFFLINE_CHECK_INTERVAL_SEC,
    OFFLINE_TIMEOUT_SEC,
    POSITION_MOVE_RANGE,
    POSITION_UPDATE_INTERVAL_SEC,
)
from logger import log_event
from backend.repositories import database as repo
from backend.services import app_service


class WorkerManager:
    def __init__(self, sio):
        self.sio = sio
        self.stop_event = asyncio.Event()
        self.loop = None
        self.tasks = []
        self.mqtt_client = None
        self.mqtt_thread = None

    async def start(self):
        repo.init_db()
        repo.init_device_positions()
        self.loop = asyncio.get_running_loop()
        self.tasks = [
            asyncio.create_task(self._offline_check_loop(), name="offline-check"),
            asyncio.create_task(self._position_broadcast_loop(), name="position-broadcast"),
        ]
        if LLM_ENABLED:
            self.tasks.append(asyncio.create_task(self._llm_analysis_loop(), name="llm-analysis"))
        self._start_mqtt()

    async def stop(self):
        self.stop_event.set()
        if self.mqtt_client is not None:
            try:
                self.mqtt_client.disconnect()
                self.mqtt_client.loop_stop()
            except Exception:
                pass
        if self.mqtt_thread and self.mqtt_thread.is_alive():
            self.mqtt_thread.join(timeout=5)
        for task in self.tasks:
            task.cancel()
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)

    def _emit_threadsafe(self, event, payload):
        if self.loop is None:
            return
        asyncio.run_coroutine_threadsafe(self.sio.emit(event, payload), self.loop)

    def _start_mqtt(self):
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.mqtt_client = client

        def on_connect(client, userdata, flags, reason_code, properties=None):
            if int(reason_code) == 0:
                client.subscribe(MQTT_TOPIC)
                log_event("INFO", "mqtt.client.connected", "ops", "mqtt", "Connected to MQTT broker successfully", topic=MQTT_TOPIC)
            else:
                log_event("ERROR", "mqtt.client.connect_failed", "ops", "mqtt", f"Failed to connect to MQTT broker, return code {reason_code}", topic=MQTT_TOPIC)

        def on_message(client, userdata, msg):
            try:
                payload = json.loads(msg.payload.decode())
                app_service.process_mqtt_payload(msg.topic, payload)
                self._emit_threadsafe("device_update", app_service.get_latest_payload())
            except Exception as exc:
                log_event("ERROR", "mqtt.message.parse_failed", "ops", "mqtt", "Failed to process MQTT message", topic=msg.topic, error=str(exc))

        client.on_connect = on_connect
        client.on_message = on_message

        def mqtt_runner():
            try:
                client.connect(MQTT_BROKER, MQTT_PORT, 60)
                client.loop_forever()
            except Exception as exc:
                level = "CRITICAL" if MQTT_REQUIRED else "WARNING"
                log_event(level, "mqtt.client.start_failed", "ops", "mqtt", "MQTT client failed to start", extra={"broker": MQTT_BROKER, "port": MQTT_PORT, "required": MQTT_REQUIRED}, error=str(exc))

        self.mqtt_thread = threading.Thread(target=mqtt_runner, name="mqtt-worker", daemon=True)
        self.mqtt_thread.start()

    async def _offline_check_loop(self):
        while not self.stop_event.is_set():
            try:
                await asyncio.sleep(OFFLINE_CHECK_INTERVAL_SEC)
                devices = repo.get_all_devices()
                now = time.time()
                changed = False
                for dev in devices:
                    last_seen = dev.get("last_seen")
                    if dev.get("online_status") != 1 or not last_seen:
                        continue
                    last_seen_ts = time.mktime(time.strptime(last_seen, "%Y-%m-%d %H:%M:%S"))
                    if now - last_seen_ts > OFFLINE_TIMEOUT_SEC:
                        repo.set_device_offline(dev["device_id"])
                        changed = True
                        log_event("WARNING", "device.status.offline_marked", "biz", "worker", "Device marked offline", device_id=dev["device_id"], extra={"offline_seconds": now - last_seen_ts})
                if changed:
                    await self.sio.emit("device_update", app_service.get_latest_payload())
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                log_event("ERROR", "system.background.offline_check_failed", "ops", "worker", "Offline check loop error", error=str(exc))

    async def _position_broadcast_loop(self):
        while not self.stop_event.is_set():
            try:
                await asyncio.sleep(POSITION_UPDATE_INTERVAL_SEC)
                devices = repo.get_all_devices_with_positions()
                if POSITION_MOVE_RANGE <= 0:
                    await self.sio.emit("position_update", devices)
                    continue
                for dev in devices:
                    if dev.get("online_status") != 1:
                        continue
                    pos_x = max(0, min(1920, (dev.get("pos_x") or 0) + random.uniform(-POSITION_MOVE_RANGE, POSITION_MOVE_RANGE)))
                    pos_y = max(0, min(1080, (dev.get("pos_y") or 0) + random.uniform(-POSITION_MOVE_RANGE, POSITION_MOVE_RANGE)))
                    repo.update_device_position(dev["device_id"], pos_x, pos_y)
                await self.sio.emit("position_update", repo.get_all_devices_with_positions())
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                log_event("ERROR", "system.background.position_broadcast_failed", "ops", "worker", "Position broadcast loop error", error=str(exc))

    async def _llm_analysis_loop(self):
        while not self.stop_event.is_set():
            try:
                await asyncio.sleep(LLM_POLL_INTERVAL_SEC)
                await asyncio.to_thread(app_service.analyze_pending_images_batch)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                log_event("ERROR", "llm.image.analysis.loop_failed", "ops", "worker", "LLM analysis loop error", error=str(exc))
