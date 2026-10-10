import os
from datetime import timedelta
from pathlib import Path
from typing import Literal, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from src.models import DeviceCreate, DeviceOut, Heartbeat, Summary
from src.store import DeviceAlreadyExists, DeviceNotFound, DeviceStore

DASHBOARD_FILE = Path(__file__).parent / "dashboard.html"

def create_app(store: DeviceStore | None = None) -> FastAPI:
    if store is None:
        timeout_seconds = float(os.getenv("HEARTBEAT_TIMEOUT_SECONDS", "30"))
        store = DeviceStore(timeout=timedelta(seconds=timeout_seconds))
    app = FastAPI(title="Mini Device Fleet Monitor")

    @app.post("/devices", response_model=DeviceOut, status_code=201)
    def register_device(body: DeviceCreate):
        try:
            return store.register(body.id, body.name)
        except DeviceAlreadyExists:
            raise HTTPException(status_code=409, detail=f"Device '{body.id}' is already registered")

    @app.post("/devices/{device_id}/heartbeat", response_model=DeviceOut)
    def receive_heartbeat(device_id: str, body: Heartbeat):
        try:
            return store.heartbeat(device_id, body.timestamp, body.status,
                                   body.cpu_usage, body.signal_strength)
        except DeviceNotFound:
            raise HTTPException(status_code=404, detail=f"Device '{device_id}' not found")

    @app.get("/devices", response_model=list[DeviceOut])
    def list_devices(status: Optional[Literal["ONLINE", "OFFLINE"]] = None):
        devices = store.list_devices()
        if status is not None:  
            devices = [d for d in devices if d["status"] == status]
        return devices

    @app.get("/devices/{device_id}", response_model=DeviceOut)
    def get_device(device_id: str):
        try:
            return store.get(device_id)
        except DeviceNotFound:
            raise HTTPException(status_code=404, detail=f"Device '{device_id}' not found")

    @app.get("/summary", response_model=Summary)
    def get_summary():
        return store.summary()

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def dashboard():
        return DASHBOARD_FILE.read_text(encoding="utf-8")

    return app

app = create_app()