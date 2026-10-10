
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

ONLINE = "ONLINE"
OFFLINE = "OFFLINE"
HEARTBEAT_TIMEOUT = timedelta(seconds=30)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DeviceAlreadyExists(Exception):
    pass


class DeviceNotFound(Exception):
    pass


@dataclass
class Device:
    id: str
    name: str
    last_heartbeat: Optional[datetime] = None  
    last_seen: Optional[datetime] = None       
    reported_status: Optional[str] = None      
    cpu_usage: Optional[float] = None
    signal_strength: Optional[float] = None


class DeviceStore:
    def __init__(self, clock: Callable[[], datetime] = utc_now,
                 timeout: timedelta = HEARTBEAT_TIMEOUT):
        self._devices: dict[str, Device] = {}
        self._lock = threading.Lock()  
        self._clock = clock            
        self._timeout = timeout

    def register(self, device_id: str, name: str) -> dict:
        with self._lock:
            if device_id in self._devices:
                raise DeviceAlreadyExists(device_id)
            device = Device(id=device_id, name=name)
            self._devices[device_id] = device
            return self._to_dict(device, self._clock())

    def heartbeat(self, device_id: str, timestamp: datetime, status: str,
                  cpu_usage: Optional[float] = None,
                  signal_strength: Optional[float] = None) -> dict:
        with self._lock:
            device = self._find(device_id)
            now = self._clock()
            device.last_heartbeat = timestamp
            device.last_seen = now
            device.reported_status = status
            device.cpu_usage = cpu_usage
            device.signal_strength = signal_strength
            return self._to_dict(device, now)

    def get(self, device_id: str) -> dict:
        with self._lock:
            return self._to_dict(self._find(device_id), self._clock())

    def list_devices(self) -> list[dict]:
        with self._lock:
            now = self._clock()
            return [self._to_dict(d, now) for d in self._devices.values()]

    def summary(self) -> dict:
        devices = self.list_devices()
        online = sum(1 for d in devices if d["status"] == ONLINE)
        return {"total": len(devices), "online": online, "offline": len(devices) - online}

    def _find(self, device_id: str) -> Device:
        device = self._devices.get(device_id)
        if device is None:
            raise DeviceNotFound(device_id)
        return device

    def _status(self, device: Device, now: datetime) -> str:
        if device.last_seen is None:
            return OFFLINE  
        if now - device.last_seen <= self._timeout:
            return ONLINE
        return OFFLINE

    def _to_dict(self, device: Device, now: datetime) -> dict:
        #asdict() makes a copy so that callers never touch shared data outside the lock
        return {**asdict(device), "status": self._status(device, now)}