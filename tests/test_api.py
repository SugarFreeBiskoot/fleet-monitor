import pytest

HEARTBEAT = {"timestamp": "2026-09-21T10:30:00Z", "status": "OK"}

def register(client, device_id="device-01"):
    return client.post("/devices", json={"id": device_id, "name": "Lab Device"})

def test_register_device(client):
    resp = register(client)
    assert resp.status_code == 201
    assert resp.json()["id"] == "device-01"
    assert resp.json()["status"] == "OFFLINE"

def test_register_duplicate_returns_409(client):
    register(client)
    assert register(client).status_code == 409

@pytest.mark.parametrize("body", [
    {},                               
    {"id": "device-01"},             
    {"id": "", "name": "x"},         
    {"id": "bad/id", "name": "x"},   
])
def test_register_invalid_input_returns_422(client, body):
    assert client.post("/devices", json=body).status_code == 422

def test_heartbeat_makes_device_online(client):
    register(client)
    resp = client.post("/devices/device-01/heartbeat", json=HEARTBEAT)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ONLINE"
    assert resp.json()["last_heartbeat"] == "2026-09-21T10:30:00Z"

def test_heartbeat_unknown_device_returns_404(client):
    assert client.post("/devices/ghost/heartbeat", json=HEARTBEAT).status_code == 404

@pytest.mark.parametrize("body", [
    {"status": "OK"},                                  
    {"timestamp": "yesterday", "status": "OK"},       
    {**HEARTBEAT, "cpu_usage": 150},                   
])
def test_heartbeat_invalid_input_returns_422(client, body):
    register(client)
    assert client.post("/devices/device-01/heartbeat", json=body).status_code == 422

def test_get_device(client):
    register(client)
    assert client.get("/devices/device-01").status_code == 200
    assert client.get("/devices/unknown").status_code == 404

def test_list_devices(client):
    register(client, "d1")
    register(client, "d2")
    ids = [d["id"] for d in client.get("/devices").json()]
    assert ids == ["d1", "d2"]

def test_filter_devices_by_status(client):
    register(client, "d1")
    register(client, "d2")
    client.post("/devices/d1/heartbeat", json=HEARTBEAT)
    online = client.get("/devices", params={"status": "ONLINE"}).json()
    offline = client.get("/devices", params={"status": "OFFLINE"}).json()
    assert [d["id"] for d in online] == ["d1"]
    assert [d["id"] for d in offline] == ["d2"]
    assert client.get("/devices", params={"status": "SLEEPING"}).status_code == 422

def test_device_goes_offline_after_30_seconds(client, clock):
    register(client)
    client.post("/devices/device-01/heartbeat", json=HEARTBEAT)
    clock.advance(30)
    assert client.get("/devices/device-01").json()["status"] == "ONLINE"
    clock.advance(1)
    assert client.get("/devices/device-01").json()["status"] == "OFFLINE"

def test_summary(client):
    register(client, "d1")
    register(client, "d2")
    client.post("/devices/d1/heartbeat", json=HEARTBEAT)
    assert client.get("/summary").json() == {"total": 2, "online": 1, "offline": 1}

def test_dashboard_page(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Fleet Monitor" in resp.text