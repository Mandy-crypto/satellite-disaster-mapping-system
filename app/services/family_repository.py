"""Storage for consent-based family sharing, isolated from project sensor data."""

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import RLock

from sqlalchemy import create_engine, text

from app.config import settings


_lock = RLock()
_engine = None
_initialized = False


def _get_engine():
    global _engine
    if _engine is None:
        database_url = str(settings.FAMILY_DATABASE_URL or os.getenv("FAMILY_DATABASE_URL", "")).strip()
        if database_url:
            if database_url.startswith("postgres://"):
                database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
            elif database_url.startswith("postgresql://"):
                database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
            _engine = create_engine(database_url, pool_pre_ping=True, pool_recycle=300)
        else:
            data_dir = Path(settings.DATA_DIR).resolve()
            data_dir.mkdir(parents=True, exist_ok=True)
            db_path = (data_dir / "family_safety.sqlite3").as_posix()
            _engine = create_engine(
                f"sqlite:///{db_path}",
                connect_args={"check_same_thread": False, "timeout": 15},
            )
    return _engine


def enabled() -> bool:
    value = os.getenv("FAMILY_SHARING_ENABLED")
    if value is not None:
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(settings.FAMILY_SHARING_ENABLED)


def has_durable_database() -> bool:
    return bool(settings.FAMILY_DATABASE_URL or os.getenv("FAMILY_DATABASE_URL", "").strip())


def initialize():
    global _initialized
    if _initialized:
        return
    with _lock:
        if _initialized:
            return
        engine = _get_engine()
        with engine.begin() as db:
            db.execute(text("""
                CREATE TABLE IF NOT EXISTS safety_groups (
                    group_id TEXT PRIMARY KEY,
                    group_name TEXT NOT NULL,
                    invite_hash TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL
                )
            """))
            db.execute(text("""
                CREATE TABLE IF NOT EXISTS safety_members (
                    member_id TEXT PRIMARY KEY,
                    group_id TEXT NOT NULL,
                    member_name TEXT NOT NULL,
                    token_hash TEXT NOT NULL UNIQUE,
                    role TEXT NOT NULL,
                    sharing_enabled INTEGER NOT NULL DEFAULT 0,
                    latitude REAL,
                    longitude REAL,
                    accuracy_m REAL,
                    location_updated_at TEXT,
                    created_at TEXT NOT NULL
                )
            """))
            db.execute(text("CREATE INDEX IF NOT EXISTS ix_safety_members_group ON safety_members(group_id)"))
            db.execute(text("""
                CREATE TABLE IF NOT EXISTS safety_alerts (
                    alert_id TEXT PRIMARY KEY,
                    group_id TEXT NOT NULL,
                    member_id TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    latitude REAL,
                    longitude REAL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """))
            db.execute(text("CREATE INDEX IF NOT EXISTS ix_safety_alerts_group ON safety_alerts(group_id, created_at)"))
        _initialized = True


def _mapping(row):
    return dict(row._mapping) if row else None


def create_group(group_id, name, invite_hash, member_id, member_name, token_hash, stamp):
    initialize()
    with _get_engine().begin() as db:
        db.execute(text("INSERT INTO safety_groups(group_id,group_name,invite_hash,created_at) VALUES(:id,:name,:invite,:stamp)"),
                   {"id": group_id, "name": name, "invite": invite_hash, "stamp": stamp})
        db.execute(text("INSERT INTO safety_members(member_id,group_id,member_name,token_hash,role,created_at) VALUES(:member,:group_id,:name,:token,'owner',:stamp)"),
                   {"member": member_id, "group_id": group_id, "name": member_name, "token": token_hash, "stamp": stamp})


def join_group(invite_hash, member_id, member_name, token_hash, stamp):
    initialize()
    with _get_engine().begin() as db:
        group = _mapping(db.execute(text("SELECT group_id,group_name FROM safety_groups WHERE invite_hash=:invite"), {"invite": invite_hash}).first())
        if not group:
            return None
        count = db.execute(text("SELECT COUNT(*) FROM safety_members WHERE group_id=:group_id"), group).scalar_one()
        if count >= 20:
            return {"error": "This family group has reached its 20-member limit."}
        db.execute(text("INSERT INTO safety_members(member_id,group_id,member_name,token_hash,role,created_at) VALUES(:member,:group_id,:name,:token,'member',:stamp)"),
                   {"member": member_id, "group_id": group["group_id"], "name": member_name, "token": token_hash, "stamp": stamp})
        return group


def member_for_token(group_id, token_hash):
    initialize()
    with _get_engine().connect() as db:
        row = db.execute(text("SELECT * FROM safety_members WHERE group_id=:group_id AND token_hash=:token"),
                         {"group_id": group_id, "token": token_hash}).first()
    return _mapping(row)


def group_details(group_id):
    initialize()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    with _get_engine().begin() as db:
        db.execute(text("""UPDATE safety_members SET sharing_enabled=0,latitude=NULL,longitude=NULL,accuracy_m=NULL,location_updated_at=NULL
            WHERE group_id=:id AND location_updated_at IS NOT NULL AND location_updated_at<:cutoff"""),
                   {"id": group_id, "cutoff": cutoff})
        db.execute(text("DELETE FROM safety_alerts WHERE group_id=:id AND created_at<:cutoff"),
                   {"id": group_id, "cutoff": cutoff})
    with _get_engine().connect() as db:
        group = _mapping(db.execute(text("SELECT group_id,group_name,created_at FROM safety_groups WHERE group_id=:id"), {"id": group_id}).first())
        members = [_mapping(row) for row in db.execute(text("""
            SELECT member_id, member_name, role, sharing_enabled, latitude, longitude, accuracy_m,
                   location_updated_at, created_at
            FROM safety_members WHERE group_id=:id ORDER BY created_at
        """), {"id": group_id}).fetchall()]
        alerts = [_mapping(row) for row in db.execute(text("""
            SELECT alert_id,member_id,alert_type,risk_level,message,latitude,longitude,metadata_json,created_at
            FROM safety_alerts WHERE group_id=:id ORDER BY created_at DESC LIMIT 50
        """), {"id": group_id}).fetchall()]
    for alert in alerts:
        alert["metadata"] = json.loads(alert.pop("metadata_json") or "{}")
    return group, members, alerts


def set_sharing(group_id, member_id, enabled):
    initialize()
    with _get_engine().begin() as db:
        db.execute(text("UPDATE safety_members SET sharing_enabled=:enabled WHERE group_id=:group_id AND member_id=:member_id"),
                   {"enabled": 1 if enabled else 0, "group_id": group_id, "member_id": member_id})


def save_location(group_id, member_id, latitude, longitude, accuracy, stamp):
    initialize()
    with _get_engine().begin() as db:
        result = db.execute(text("""
            UPDATE safety_members SET latitude=:lat,longitude=:lon,accuracy_m=:accuracy,location_updated_at=:stamp
            WHERE group_id=:group_id AND member_id=:member_id AND sharing_enabled=1
        """), {"lat": latitude, "lon": longitude, "accuracy": accuracy,
              "stamp": stamp, "group_id": group_id, "member_id": member_id})
        return result.rowcount == 1


def recent_auto_alert(group_id, member_id, zone_id, since):
    initialize()
    with _get_engine().connect() as db:
        rows = db.execute(text("""
            SELECT metadata_json FROM safety_alerts
            WHERE group_id=:group_id AND member_id=:member_id AND alert_type='RISK_ZONE' AND created_at>=:since
            ORDER BY created_at DESC LIMIT 50
        """), {"group_id": group_id, "member_id": member_id, "since": since}).fetchall()
    return any(json.loads(row[0] or "{}").get("zone_id") == zone_id for row in rows)


def add_alert(alert):
    initialize()
    with _get_engine().begin() as db:
        db.execute(text("""
            INSERT INTO safety_alerts(alert_id,group_id,member_id,alert_type,risk_level,message,latitude,longitude,metadata_json,created_at)
            VALUES(:alert_id,:group_id,:member_id,:alert_type,:risk_level,:message,:latitude,:longitude,:metadata,:created_at)
        """), {**alert, "metadata": json.dumps(alert.get("metadata", {}))})


def leave_group(group_id, member_id):
    initialize()
    with _get_engine().begin() as db:
        db.execute(text("DELETE FROM safety_members WHERE group_id=:group_id AND member_id=:member_id"),
                   {"group_id": group_id, "member_id": member_id})
        db.execute(text("DELETE FROM safety_alerts WHERE group_id=:group_id AND member_id=:member_id"),
                   {"group_id": group_id, "member_id": member_id})
