"""Small durable SQLite repository for uploaded data and processing state."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any, Optional

from app.config import settings


_lock = RLock()
_db_path = Path(settings.DATA_DIR).resolve() / "disaster_mapping.sqlite3"
_db_path.parent.mkdir(parents=True, exist_ok=True)


def _connect():
    connection = sqlite3.connect(_db_path, timeout=15)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def initialize():
    with _lock, _connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS uploads (
            id TEXT PRIMARY KEY, kind TEXT NOT NULL, filename TEXT NOT NULL,
            path TEXT NOT NULL, location_json TEXT, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sensor_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT, sensor_id TEXT NOT NULL,
            latitude REAL NOT NULL, longitude REAL NOT NULL, timestamp TEXT NOT NULL,
            payload_json TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS ix_sensor_timestamp ON sensor_readings(sensor_id, timestamp DESC);
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY, status TEXT NOT NULL, request_json TEXT NOT NULL,
            result_json TEXT, error TEXT, created_at TEXT NOT NULL,
            started_at TEXT, completed_at TEXT
        );
        CREATE TABLE IF NOT EXISTS alerts (
            id TEXT PRIMARY KEY, payload_json TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS risk_zones (
            id TEXT PRIMARY KEY, payload_json TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        """)


# Ensure CLI tools and workers can use the repository before ASGI startup hooks run.
initialize()


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def health_check() -> bool:
    try:
        with _lock, _connect() as db:
            db.execute("SELECT 1").fetchone()
        return True
    except sqlite3.Error:
        return False


def _dict(row):
    return dict(row) if row else None


def save_upload(upload_id: str, kind: str, filename: str, path: str, location=None):
    with _lock, _connect() as db:
        db.execute("INSERT INTO uploads VALUES (?, ?, ?, ?, ?, ?)",
                   (upload_id, kind, filename, path, json.dumps(location) if location else None, now_iso()))
        row = db.execute("SELECT * FROM uploads WHERE id=?", (upload_id,)).fetchone()
    result = _dict(row)
    result["location"] = json.loads(result.pop("location_json")) if result["location_json"] else None
    return result


def get_upload(upload_id: str, kind: Optional[str] = None):
    with _lock, _connect() as db:
        row = db.execute("SELECT * FROM uploads WHERE id=?" + (" AND kind=?" if kind else ""),
                         (upload_id, kind) if kind else (upload_id,)).fetchone()
    result = _dict(row)
    if result:
        result["location"] = json.loads(result.pop("location_json")) if result["location_json"] else None
    return result


def add_reading(reading: dict):
    with _lock, _connect() as db:
        db.execute("INSERT INTO sensor_readings(sensor_id, latitude, longitude, timestamp, payload_json) VALUES (?, ?, ?, ?, ?)",
                   (reading["sensor_id"], reading["latitude"], reading["longitude"], reading["timestamp"], json.dumps(reading)))


def list_readings(limit=100, offset=0, sensor_id=None):
    where, args = (" WHERE sensor_id=?", [sensor_id]) if sensor_id else ("", [])
    with _lock, _connect() as db:
        total = db.execute("SELECT COUNT(*) FROM sensor_readings" + where, args).fetchone()[0]
        rows = db.execute("SELECT payload_json FROM sensor_readings" + where + " ORDER BY timestamp DESC, id DESC LIMIT ? OFFSET ?",
                          [*args, limit, offset]).fetchall()
    return total, [json.loads(row[0]) for row in rows]


def create_job(job_id: str, request: dict):
    with _lock, _connect() as db:
        db.execute("INSERT INTO jobs(id,status,request_json,created_at) VALUES (?, 'QUEUED', ?, ?)",
                   (job_id, json.dumps(request), now_iso()))
    return get_job(job_id)


def update_job(job_id: str, status: str, result=None, error=None, started_at=None):
    with _lock, _connect() as db:
        db.execute("UPDATE jobs SET status=?, result_json=COALESCE(?,result_json), error=?, started_at=COALESCE(?,started_at), completed_at=? WHERE id=?",
                   (status, json.dumps(result) if result is not None else None, error, started_at,
                    now_iso() if status in ("COMPLETED", "FAILED", "CANCELLED") else None, job_id))
    return get_job(job_id)


def get_job(job_id: str):
    with _lock, _connect() as db:
        row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    result = _dict(row)
    if result:
        result["request"] = json.loads(result.pop("request_json"))
        result["result"] = json.loads(result.pop("result_json")) if result["result_json"] else None
    return result


def list_jobs(limit=50, status=None):
    where, args = (" WHERE status=?", [status]) if status else ("", [])
    with _lock, _connect() as db:
        rows = db.execute("SELECT id FROM jobs" + where + " ORDER BY created_at DESC LIMIT ?", [*args, limit]).fetchall()
    return [get_job(row[0]) for row in rows]


def save_alert(alert: dict):
    with _lock, _connect() as db:
        db.execute("INSERT OR REPLACE INTO alerts VALUES (?, ?, ?)", (alert["alert_id"], json.dumps(alert), alert["generated_at"]))


def list_alerts(limit=50):
    with _lock, _connect() as db:
        rows = db.execute("SELECT payload_json FROM alerts ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    return [json.loads(row[0]) for row in rows]


def save_risk_zones(zones: list[dict]):
    with _lock, _connect() as db:
        db.execute("DELETE FROM risk_zones")
        stamp = now_iso()
        db.executemany("INSERT INTO risk_zones VALUES (?, ?, ?)", [(z["zone_id"], json.dumps(z), stamp) for z in zones])


def list_risk_zones(limit=500):
    with _lock, _connect() as db:
        rows = db.execute("SELECT payload_json FROM risk_zones ORDER BY updated_at DESC LIMIT ?", (limit,)).fetchall()
    return [json.loads(row[0]) for row in rows]
