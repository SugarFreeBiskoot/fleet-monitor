# Mini Device Fleet Monitor

A small REST API that receives heartbeats from devices and reports whether each device is **ONLINE** or **OFFLINE**, plus a simulator that runs 5 devices against it.

- **ONLINE**: the last heartbeat arrived within the last 30 seconds
- **OFFLINE**: no heartbeat for more than 30 seconds, or no heartbeat yet

## Design

```text
simulator/simulate.py ──HTTP──▶ src/main.py    API routes; maps errors to 404 / 409
                                src/models.py  input validation (422 on bad input)
                                src/store.py   device data + ONLINE/OFFLINE rule
```

- **Status is computed when it is read, not stored.** The store keeps `last_seen`, the server time of each device's last heartbeat. Every read checks `now - last_seen <= 30s`. No background job is needed, and the status can never be out of date.
- **Server time decides the status**, not the device's `timestamp`, because device clocks can be wrong. The device's timestamp is still stored and returned as `last_heartbeat`.
- **Business logic is separate from HTTP.** `DeviceStore` contains no web code, so it can be tested directly. `main.py` only turns requests into store calls and store errors into status codes.
- **Injectable clock.** Tests pass a fake clock and move time forward 31 seconds instantly instead of waiting.
- **Thread-safe.** FastAPI handles requests on several threads, so a lock protects the device data.
- **In-memory storage** keeps the solution small.

| Code | Meaning |
|---|---|
| 201 | Device registered |
| 200 | Successful heartbeat or read |
| 404 | Device not registered |
| 409 | Device id already registered |
| 422 | Invalid input (missing field, bad timestamp, invalid id, `cpu_usage` outside 0–100, unknown status filter) |

- **Simple dashboard** (src/dashboard.html), served at /, uses plain HTML, CSS and a little JavaScript that polls /summary and /devices every 2 seconds. It reuses the existing API, so no extra backend logic was needed.

## Prerequisites

- Python 3.10 or newer
- Git

## Build

```bash
git clone <repo-url>
cd fleet-monitor
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Run the application

```bash
uvicorn src.main:app --port 8000
```

Interactive API documentation: http://localhost:8000/docs

Dashboard: open http://localhost:8000/ in a browser to see the fleet status update live every 2 seconds.

Optional: change the timeout with the `HEARTBEAT_TIMEOUT_SECONDS` environment variable (default 30), for example `HEARTBEAT_TIMEOUT_SECONDS=10 uvicorn src.main:app --port 8000`.

## Run the simulator

With the server running, open a second terminal, activate the virtual environment, and run:

```bash
python simulator/simulate.py
```

This registers `device-01` to `device-05`. Each sends a heartbeat every 5 seconds, and the fleet status is printed every 10 seconds.

To watch a device go OFFLINE:

```bash
python simulator/simulate.py --stop device-03 --stop-after 20
```

`device-03` stops sending after 20 seconds. About 30 seconds later the output shows:

```text
=== 5 devices | online: 4 | offline: 1 ['device-03']
```

Press Ctrl+C to stop. Other options: `--count`, `--interval`, `--url`.

## Run the tests

```bash
pytest -v
```

28 tests cover registration, heartbeats, device status, the 30-second rule (including exactly 30 s), filtering, validation and error codes, and concurrent heartbeats. A fake clock makes them run in under a second.

## Example API requests

```bash
# Register a device -> 201
curl -X POST http://localhost:8000/devices -H "Content-Type: application/json" \
  -d '{"id": "device-01", "name": "Lab Device 01"}'

# Send a heartbeat (cpu_usage and signal_strength are optional) -> 200
curl -X POST http://localhost:8000/devices/device-01/heartbeat -H "Content-Type: application/json" \
  -d '{"timestamp": "2026-09-21T10:30:00Z", "status": "OK", "cpu_usage": 42, "signal_strength": -71}'

# List devices, optionally filtered
curl http://localhost:8000/devices
curl "http://localhost:8000/devices?status=OFFLINE"

# One device
curl http://localhost:8000/devices/device-01

# Fleet summary -> {"total": 5, "online": 4, "offline": 1}
curl http://localhost:8000/summary
```

Example device response:

```json
{
  "id": "device-01",
  "name": "Lab Device 01",
  "status": "ONLINE",
  "last_heartbeat": "2026-09-21T10:30:00Z",
  "last_seen": "2026-09-21T10:30:00.120000Z",
  "reported_status": "OK",
  "cpu_usage": 42.0,
  "signal_strength": -71.0
}
```

## Assumptions

- A registered device with no heartbeat yet is OFFLINE.
- Exactly 30 seconds after the last heartbeat still counts as ONLINE; more than 30 seconds is OFFLINE.
- Status uses the time the server received the heartbeat, not the device's timestamp.
- The heartbeat `status` (e.g. "OK") is the device's own report, returned as `reported_status`. It is separate from ONLINE/OFFLINE.
- Heartbeats from unregistered devices are rejected with 404, not auto-registered.
- Device ids may only contain letters, digits, `.`, `_` and `-`, because they appear in URLs.

## Known limitations

- Data is kept in memory and lost when the server restarts.
- The lock only works within one server process; several instances would not share data.
- No authentication.
- Only the latest heartbeat is stored; there is no history.
- No pagination on `GET /devices`.

## With one more day

- Persistent storage (SQLite, then Redis/Postgres so several API instances can share data)
- API keys for devices and operators
- Log or alert when a device changes between ONLINE and OFFLINE
- Docker and docker-compose for the server and simulator
- Structured logging and a health-check endpoint

## AI Usage

- **Tool:** Claude (Anthropic).
- **Used for:** I used Cluade for breaking the task into steps, drafting the code from my logic and view,Writing Multiple tests and this README file
- **Changed / rejected:** Claude's wrote test cases that pass no matter what and also it gave 56 test cases which were reduced to 28 test cases which run .They come from 23 test functions. I Corrected that
.It Also was giving so much unnecessary long code which was shortened.
Also the spec says ONLINE “within 30 s” and OFFLINE at “more than 30 s”. So what is the status at exactly 30.0 s? Writing < instead of <= would wrongly mark the device OFFLINE.
My code: now - last_seen <= self._timeout treats exactly 30 s as ONLINE.
Test: test_online_at_exactly_30_seconds (and 31 s → OFFLINE).
The AI didnt take this edge case into consideration 
- **Verified myself:** I ran the simulator with `--stop device-03` and watched device-03 change to OFFLINE about 30 seconds after its last heartbeat, ran all 28 tests locally, and checked in the API docs page that a device turns OFFLINE after 30 seconds without heartbeats.