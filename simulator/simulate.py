import argparse
import random
import threading
import time
from datetime import datetime, timezone
import requests

def register(url, device_id):
    resp = requests.post(f"{url}/devices", json={"id": device_id, "name": f"Simulated {device_id}"},
                         timeout=3)
    if resp.status_code not in (201, 409):
        resp.raise_for_status()

def run_device(url, device_id, interval, stop_after):
    started = time.monotonic()
    while True:
        if stop_after is not None and time.monotonic() - started >= stop_after:
            print(f"[{device_id}] stopped sending heartbeats")
            return
        heartbeat = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "OK",
            "cpu_usage": random.randint(5, 95),
            "signal_strength": random.randint(-95, -50),
        }
        try:
            resp = requests.post(f"{url}/devices/{device_id}/heartbeat", json=heartbeat, timeout=3)
            print(f"[{device_id}] heartbeat -> {resp.status_code}")
        except requests.RequestException as exc:
            print(f"[{device_id}] heartbeat failed: {exc}")
        time.sleep(interval)

def print_fleet(url):
    try:
        devices = requests.get(f"{url}/devices", timeout=3).json()
        offline = [d["id"] for d in devices if d["status"] == "OFFLINE"]
        print(f"=== {len(devices)} devices | online: {len(devices) - len(offline)} "
              f"| offline: {len(offline)} {offline}")
    except requests.RequestException as exc:
        print(f"=== could not get fleet status: {exc}")

def main():
    parser = argparse.ArgumentParser(description="Simulate devices sending heartbeats")
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--count", type=int, default=5, help="number of devices")
    parser.add_argument("--interval", type=float, default=5, help="seconds between heartbeats")
    parser.add_argument("--stop", help="id of a device that stops sending, e.g. device-03")
    parser.add_argument("--stop-after", type=float, default=20, help="seconds before it stops")
    args = parser.parse_args()

    device_ids = [f"device-{i:02d}" for i in range(1, args.count + 1)]
    try:
        for device_id in device_ids:
            register(args.url, device_id)
    except requests.ConnectionError:
        raise SystemExit(f"Cannot reach {args.url}. Start the server first.")

    for device_id in device_ids:
        stop_after = args.stop_after if device_id == args.stop else None
        print(f"{device_id} -> heartbeat every {args.interval:g} seconds")
        threading.Thread(target=run_device, args=(args.url, device_id, args.interval, stop_after),
                         daemon=True).start()

    try:
        while True:
            time.sleep(10)
            print_fleet(args.url)
    except KeyboardInterrupt:
        print("Simulator stopped")

if __name__ == "__main__":
    main()