"""Background processing jobs for uploaded satellite and sensor data."""

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.services import repository
from app.security import require_admin

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/process", tags=["Processing"])


class JobRequest(BaseModel):
    satellite_image_id: str | None = None
    sensor_file_id: str | None = None
    threshold: float = Field(0.2, ge=-1, le=1)


def _risk_level(score: float) -> str:
    return "CRITICAL" if score >= .8 else "HIGH" if score >= .6 else "MEDIUM" if score >= .3 else "LOW"


async def _run_job(job_id: str):
    job = repository.get_job(job_id)
    if not job or job["status"] == "CANCELLED":
        return
    request = job["request"]
    started = datetime.now(timezone.utc).isoformat()
    repository.update_job(job_id, "PROCESSING", started_at=started)
    result = {"satellite_result": None, "sensor_result": None, "fusion_result": None}
    try:
        if request.get("satellite_image_id"):
            image = repository.get_upload(request["satellite_image_id"], "satellite")
            if not image or not Path(image["path"]).is_file():
                raise ValueError("Satellite upload is missing")
            from app.pipeline.satellite.processor import SatelliteProcessor
            processor = SatelliteProcessor()
            output = await asyncio.to_thread(processor.process_image, image["path"], None,
                                             request.get("threshold"), image.get("location"))
            if output.get("status") != "success":
                output = await asyncio.to_thread(processor.process_rgb_image, image["path"],
                                                 request.get("threshold"), image.get("location"))
            if output.get("status") != "success":
                raise ValueError(output.get("error") or "Satellite processing failed")
            result["satellite_result"] = output

        if request.get("sensor_file_id"):
            upload = repository.get_upload(request["sensor_file_id"], "sensors")
            if not upload or not Path(upload["path"]).is_file():
                raise ValueError("Sensor upload is missing")
            _, readings = repository.list_readings(limit=1000)
            readings = [row for row in readings if row.get("source_file_id") == upload["id"]]
            if not readings:
                raise ValueError("Sensor upload contains no valid readings")
            scores = [float(row.get("risk_score", 0)) for row in readings]
            mean_score = sum(scores) / len(scores)
            result["sensor_result"] = {"reading_count": len(readings), "risk_score": round(mean_score, 4),
                                        "risk_level": _risk_level(mean_score), "max_risk_score": max(scores)}

        scores = []
        if result["satellite_result"]:
            scores.append(float(result["satellite_result"].get("flood_probability", 0)))
        if result["sensor_result"]:
            scores.append(float(result["sensor_result"]["risk_score"]))
        final_score = sum(scores) / len(scores) if scores else 0.0
        result["fusion_result"] = {"final_risk": round(final_score, 4), "risk_level": _risk_level(final_score),
                                    "confidence": round(min(1.0, 0.5 + 0.5 * len(scores)), 2),
                                    "sources": len(scores)}
        latest_job = repository.get_job(job_id)
        if not latest_job or latest_job["status"] == "CANCELLED":
            return
        repository.update_job(job_id, "COMPLETED", result=result)
    except Exception as exc:
        logger.exception("Processing job %s failed", job_id)
        repository.update_job(job_id, "FAILED", error=str(exc))


@router.post("/", status_code=202, dependencies=[Depends(require_admin)])
async def process_data(request: JobRequest, background_tasks: BackgroundTasks):
    if not request.satellite_image_id and not request.sensor_file_id:
        raise HTTPException(422, "Provide a satellite_image_id or sensor_file_id")
    if request.satellite_image_id and not repository.get_upload(request.satellite_image_id, "satellite"):
        raise HTTPException(404, "Satellite image not found")
    if request.sensor_file_id and not repository.get_upload(request.sensor_file_id, "sensors"):
        raise HTTPException(404, "Sensor file not found")
    job_id = f"JOB_{uuid4().hex[:12]}"
    repository.create_job(job_id, request.model_dump())
    background_tasks.add_task(_run_job, job_id)
    return {"status": "success", "job_id": job_id, "job_status": "QUEUED", "message": "Processing job created",
            "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/")
async def list_jobs(limit: int = Query(50, ge=1, le=100), status: str | None = None):
    if status and status not in {"QUEUED", "PROCESSING", "COMPLETED", "FAILED", "CANCELLED"}:
        raise HTTPException(422, "Unsupported job status")
    jobs = repository.list_jobs(limit, status)
    return {"status": "success", "count": len(jobs), "jobs": jobs, "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/{job_id}")
async def get_job_status(job_id: str):
    job = repository.get_job(job_id)
    if not job:
        raise HTTPException(404, "Processing job not found")
    return {"status": "success", **job}


@router.delete("/{job_id}", dependencies=[Depends(require_admin)])
async def cancel_job(job_id: str):
    job = repository.get_job(job_id)
    if not job:
        raise HTTPException(404, "Processing job not found")
    if job["status"] in ("COMPLETED", "FAILED", "CANCELLED"):
        raise HTTPException(409, f"Cannot cancel a {job['status'].lower()} job")
    repository.update_job(job_id, "CANCELLED")
    return {"status": "success", "job_id": job_id, "job_status": "CANCELLED"}
