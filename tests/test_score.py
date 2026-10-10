import threading
from datetime import datetime, timedelta, timezone
import pytest
from src.store import OFFLINE, ONLINE, DeviceAlreadyExists, DeviceNotFound
TS = datetime(2026, 9, 21, 10, 30, 0, tzinfo=timezone.utc)

def test_register_device(store):
    device = store.register("device-01", "Lab Device 01")
    assert device["id"] == "device-01"
    assert device["name"] == "Lab Device 01"

def test_register_duplicate_raises(store):
    store.register("device-01", "A")
    with pytest.raises(DeviceAlreadyExists):
        store.register("device-01", "B")

def test_get_unknown_device_raises(store):
    with pytest.raises(DeviceNotFound):
        store.get("ghost")

def test_heartbeat_unknown_device_raises(store):
    with pytest.raises(DeviceNotFound):
        store.heartbeat("ghost", TS, "OK")

def test_heartbeat_stores_latest_values(store):
    store.register("device-01", "A")
    device = store.heartbeat("device-01", TS, "OK", cpu_usage=42, signal_strength=-71)
    assert device["last_heartbeat"] == TS
    assert device["reported_status"] == "OK"
    assert device["cpu_usage"] == 42
    assert device["signal_strength"] == -71

def test_new_device_is_offline_until_first_heartbeat(store):
    store.register("device-01", "A")
    assert store.get("device-01")["status"] == OFFLINE
    store.heartbeat("device-01", TS, "OK")
    assert store.get("device-01")["status"] == ONLINE

def test_online_at_exactly_30_seconds(store, clock):
    store.register("device-01", "A")
    store.heartbeat("device-01", TS, "OK")
    clock.advance(30)
    assert store.get("device-01")["status"] == ONLINE

def test_offline_after_more_than_30_seconds(store, clock):
    store.register("device-01", "A")
    store.heartbeat("device-01", TS, "OK")
    clock.advance(31)
    assert store.get("device-01")["status"] == OFFLINE

def test_device_comes_back_online(store, clock):
    store.register("device-01", "A")
    store.heartbeat("device-01", TS, "OK")
    clock.advance(60)
    store.heartbeat("device-01", TS + timedelta(seconds=60), "OK")
    assert store.get("device-01")["status"] == ONLINE

def test_status_uses_server_time_not_device_timestamp(store):
    store.register("device-01", "A")
    store.heartbeat("device-01", TS - timedelta(hours=1), "OK")
    assert store.get("device-01")["status"] == ONLINE


def test_summary(store, clock):
    for device_id in ["d1", "d2", "d3"]:
        store.register(device_id, "x")
    store.heartbeat("d1", TS, "OK")
    store.heartbeat("d2", TS, "OK")
    assert store.summary() == {"total": 3, "online": 2, "offline": 1}
    clock.advance(31)
    assert store.summary() == {"total": 3, "online": 0, "offline": 3}


def test_concurrent_heartbeats(store):
    for i in range(10):
        store.register(f"d{i}", "x")

    def send_many(i):
        for _ in range(100):
            store.heartbeat(f"d{i}", TS, "OK")

    threads = [threading.Thread(target=send_many, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert store.summary() == {"total": 10, "online": 10, "offline": 0}