"""Upload and inspect satellite scenes."""

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from app.config import settings
from app.services import repository
from app.security import require_admin

router = APIRouter(prefix="/api/satellite", tags=["Satellite"])
_ALLOWED = {".tif", ".tiff", ".png", ".jpg", ".jpeg"}


async def _save_upload(file: UploadFile, kind: str, location=None):
    filename = Path(file.filename or "upload").name
    suffix = Path(filename).suffix.lower()
    if suffix not in _ALLOWED:
        raise HTTPException(415, "Upload a GeoTIFF, TIFF, PNG, or JPEG image")
    upload_id = f"IMG_{uuid4().hex[:12]}"
    directory = Path(settings.DATA_DIR).resolve() / "uploads" / kind
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{upload_id}{suffix}"
    size = 0
    try:
        with target.open("wb") as destination:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > settings.MAX_UPLOAD_SIZE:
                    raise HTTPException(413, "Upload exceeds the configured size limit")
                destination.write(chunk)
        if size == 0:
            raise HTTPException(400, "Uploaded file is empty")
        record = repository.save_upload(upload_id, kind, filename, str(target), location)
        return record
    except Exception:
        target.unlink(missing_ok=True)
        raise
    finally:
        await file.close()


@router.post("/upload", status_code=201, dependencies=[Depends(require_admin)])
async def upload_satellite_image(
    file: UploadFile = File(...),
    lat: float = Query(23.181, ge=-90, le=90),
    lon: float = Query(79.951, ge=-180, le=180),
):
    record = await _save_upload(file, "satellite", {"lat": lat, "lon": lon})
    return {"status": "success", "message": "Satellite image uploaded", "image_id": record["id"],
            "filename": record["filename"], "location": record["location"],
            "timestamp": record["created_at"]}


@router.get("/request/{image_id}")
async def get_satellite_request(image_id: str):
    image = repository.get_upload(image_id, "satellite")
    if not image:
        raise HTTPException(404, "Satellite image not found")
    jobs = [job for job in repository.list_jobs(100) if job["request"].get("satellite_image_id") == image_id]
    job = jobs[0] if jobs else None
    return {"status": "success", "image_id": image_id,
            "request_status": job["status"] if job else "UPLOADED", "job_id": job["id"] if job else None,
            "timestamp": image["created_at"]}


@router.get("/results/{image_id}")
async def get_satellite_results(image_id: str):
    image = repository.get_upload(image_id, "satellite")
    if not image:
        raise HTTPException(404, "Satellite image not found")
    jobs = [job for job in repository.list_jobs(100) if job["request"].get("satellite_image_id") == image_id]
    completed = next((job for job in jobs if job["result"]), None)
    result = (completed["result"].get("satellite_result") or completed["result"]) if completed else None
    return {"status": "success", "image_id": image_id, "result": result,
            "request_status": completed["status"] if completed else (jobs[0]["status"] if jobs else "UPLOADED"),
            "timestamp": datetime.now(timezone.utc).isoformat()}
