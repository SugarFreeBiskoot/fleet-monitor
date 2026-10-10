from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
class DeviceCreate(BaseModel):
    id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")
    name: str = Field(min_length=1, max_length=128)

class Heartbeat(BaseModel):
    timestamp: datetime
    status: str = Field(min_length=1, max_length=32)
    cpu_usage: Optional[float] = Field(default=None, ge=0, le=100)
    signal_strength: Optional[float] = None

class DeviceOut(BaseModel):
    id: str
    name: str
    status: str
    last_heartbeat: Optional[datetime]
    last_seen: Optional[datetime]
    reported_status: Optional[str]
    cpu_usage: Optional[float]
    signal_strength: Optional[float]

class Summary(BaseModel):
    total: int
    online: int
    offline: int