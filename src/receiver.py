from datetime import datetime, timezone
from pathlib import Path
import csv

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="PHOTON Sensor Receiver")

DATA_DIR = Path("data/experiments")
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = DATA_DIR / "sensors.csv"


class SensorReading(BaseModel):
    device: str = "ESP32-C3"
    lux: float


@app.get("/")
def home():
    return {
        "project": "PHOTON",
        "status": "online",
        "endpoint": "POST /sensor",
    }


@app.post("/sensor")
def receive_sensor(reading: SensorReading):
    timestamp = datetime.now(timezone.utc).isoformat()
    file_exists = LOG_FILE.exists()

    with LOG_FILE.open("a", newline="") as f:
        writer = csv.writer(f)

        if not file_exists:
            writer.writerow(["timestamp", "device", "lux"])

        writer.writerow([timestamp, reading.device, reading.lux])

    print(f"[PHOTON] {reading.device}: {reading.lux:.2f} lux")

    return {
        "ok": True,
        "device": reading.device,
        "lux": reading.lux,
        "timestamp": timestamp,
    }
