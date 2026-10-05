"""Sensor data upload, validation and query endpoints."""

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import ValidationError

from app.config import settings
from app.models.schemas import SensorReadingInput
from app.services import repository
from app.security import require_admin

router = APIRouter(prefix="/api/sensors", tags=["Sensors"])


def _risk(reading):
    rain = min(max(reading.rainfall_mm, 0) / 100, .4)
    water = min(max(reading.water_level_cm, 0) / 200, .4)
    soil = min(max(reading.soil_moisture_percent - 50, 0) / 250, .2)
    score = min(1.0, rain + water + soil)
    level = "CRITICAL" if score >= .8 else "HIGH" if score >= .6 else "MEDIUM" if score >= .3 else "LOW"
    return round(score, 4), level


def _parse_sensor_file(path: Path, filename: str):
    if Path(filename).suffix.lower() == ".csv":
        with path.open(newline="", encoding="utf-8-sig") as source:
            return list(csv.DictReader(source))
    if Path(filename).suffix.lower() == ".json":
        with path.open(encoding="utf-8") as source:
            data = json.load(source)
        return data if isinstance(data, list) else data.get("readings", [data]) if isinstance(data, dict) else None
    return None


@router.post("/upload", status_code=201, dependencies=[Depends(require_admin)])
async def upload_sensor_data(file: UploadFile = File(...)):
    filename = Path(file.filename or "").name
    if Path(filename).suffix.lower() not in {".csv", ".json"}:
        raise HTTPException(415, "Sensor data must be a CSV or JSON file")
    upload_id = f"SENSORFILE_{uuid4().hex[:12]}"
    directory = Path(settings.DATA_DIR).resolve() / "uploads" / "sensors"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{upload_id}{Path(filename).suffix.lower()}"
    size = 0
    try:
        with path.open("wb") as destination:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > settings.MAX_UPLOAD_SIZE:
                    raise HTTPException(413, "Upload exceeds the configured size limit")
                destination.write(chunk)
        if not size:
            raise HTTPException(400, "Uploaded file is empty")
        raw_rows = _parse_sensor_file(path, filename)
        if raw_rows is None or not raw_rows:
            raise HTTPException(422, "Sensor file must contain at least one reading")
        if len(raw_rows) > 100_000:
            raise HTTPException(413, "A maximum of 100000 readings can be imported at once")
        validated = []
        errors = []
        for index, raw in enumerate(raw_rows, start=1):
            try:
                reading = SensorReadingInput.model_validate(raw).model_dump()
                score, level = _risk(SensorReadingInput.model_validate(reading))
                reading.update(risk_score=score, risk_level=level, source_file_id=upload_id)
                validated.append(reading)
            except (ValidationError, TypeError, ValueError) as exc:
                errors.append({"row": index, "error": str(exc)[:300]})
                if len(errors) >= 10:
                    break
        if errors:
            raise HTTPException(422, detail={"message": "Sensor file contains invalid rows", "errors": errors})
        repository.save_upload(upload_id, "sensors", filename, str(path))
        for reading in validated:
            repository.add_reading(reading)
        return {"status": "success", "sensor_file_id": upload_id, "filename": filename,
                "imported_count": len(validated), "timestamp": datetime.now(timezone.utc).isoformat()}
    except HTTPException:
        path.unlink(missing_ok=True)
        raise
    except (OSError, json.JSONDecodeError, csv.Error) as exc:
        path.unlink(missing_ok=True)
        raise HTTPException(422, f"Could not parse sensor data: {exc}") from exc
    finally:
        await file.close()


@router.get("/")
async def get_sensor_readings(limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0)):
    total, readings = repository.list_readings(limit, offset)
    return {"status": "success", "count": total, "limit": limit, "offset": offset,
            "readings": readings, "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/results/{sensor_id}")
async def get_sensor_results(sensor_id: str):
    total, readings = repository.list_readings(1000, 0, sensor_id)
    if not readings:
        raise HTTPException(404, "Sensor not found")
    scores = [r["risk_score"] for r in readings]
    average = sum(scores) / len(scores)
    level = "CRITICAL" if average >= .8 else "HIGH" if average >= .6 else "MEDIUM" if average >= .3 else "LOW"
    return {"status": "success", "sensor_id": sensor_id, "results": {"reading_count": total,
            "risk_score": round(average, 4), "risk_level": level, "latest": readings[0]},
            "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/{sensor_id}")
async def get_sensor_by_id(sensor_id: str):
    total, readings = repository.list_readings(1, 0, sensor_id)
    if not total:
        raise HTTPException(404, "Sensor not found")
    return {"status": "success", "sensor_id": sensor_id, "reading": readings[0]}


@router.post("/process/{sensor_id}", dependencies=[Depends(require_admin)])
async def process_sensor_data(sensor_id: str):
    total, readings = repository.list_readings(1000, 0, sensor_id)
    if not readings:
        raise HTTPException(404, "Sensor not found")
    scores = [r["risk_score"] for r in readings]
    score = sum(scores) / len(scores)
    level = "CRITICAL" if score >= .8 else "HIGH" if score >= .6 else "MEDIUM" if score >= .3 else "LOW"
    return {"status": "success", "sensor_id": sensor_id, "process_status": "COMPLETED",
            "result": {"reading_count": total, "risk_score": round(score, 4), "risk_level": level}}
