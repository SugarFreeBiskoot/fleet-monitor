from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from src.main import create_app
from src.store import DeviceStore

class FakeClock:
    def __init__(self):
        self.now = datetime(2026, 9, 21, 10, 30, 0, tzinfo=timezone.utc)

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += timedelta(seconds=seconds)

@pytest.fixture
def clock():
    return FakeClock()

@pytest.fixture
def store(clock):
    return DeviceStore(clock=clock)

@pytest.fixture
def client(store):
    return TestClient(create_app(store))