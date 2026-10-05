"""
Dashboard API Router - Risk Maps, Statistics, Alerts with WebSocket support
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List, Dict, Any
from pydantic import ValidationError
from datetime import datetime
import logging
from uuid import uuid4
from app.services import repository
from app.config import settings
from app.security import require_admin

from app.models.schemas import RiskZone, Alert
from app.api.websocket import manager, push_alert

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/dashboard",
    tags=["Dashboard"]
)


@router.get("/risk-map")
async def get_risk_map(
    lat: Optional[float] = Query(None, ge=-90, le=90),
    lon: Optional[float] = Query(None, ge=-180, le=180),
    radius_km: float = Query(100, ge=10, le=500)
) -> dict:
    """Get risk map data"""
    zones = repository.list_risk_zones(500)
    if not zones:
        _, readings = repository.list_readings(1000, 0)
        latest = {}
        for reading in readings:
            latest.setdefault(reading["sensor_id"], reading)
        zones = [{"zone_id": f"SENSOR_{r['sensor_id']}", "grid_cell": r["sensor_id"],
                  "location": {"lat": r["latitude"], "lon": r["longitude"]}, "risk_score": r.get("risk_score", 0),
                  "risk_level": r.get("risk_level", "LOW"), "confidence": None,
                  "satellite_contribution": 0.0, "sensor_contribution": r.get("risk_score", 0),
                  "explanation": "Derived from the latest sensor reading", "disagreement": False}
                 for r in latest.values()]
    if lat is not None and lon is not None:
        from math import radians, sin, cos, asin, sqrt
        def distance(zone):
            zlat, zlon = zone["location"]["lat"], zone["location"]["lon"]
            dlat, dlon = radians(zlat - lat), radians(zlon - lon)
            return 2 * 6371 * asin(sqrt(sin(dlat / 2) ** 2 + cos(radians(lat)) * cos(radians(zlat)) * sin(dlon / 2) ** 2))
        zones = [zone for zone in zones if distance(zone) <= radius_km]
    return {
        "status": "success",
        "zones": zones,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/zones")
async def get_risk_zones(
    risk_level: Optional[str] = Query(None, regex="^(LOW|MEDIUM|HIGH|CRITICAL)$"),
    limit: int = Query(100, ge=1, le=500)
) -> dict:
    """Get all risk zones"""
    zones = (await get_risk_map())["zones"]
    if risk_level:
        zones = [zone for zone in zones if zone["risk_level"] == risk_level]
    zones = zones[:limit]
    return {
        "status": "success",
        "count": len(zones),
        "zones": zones,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/statistics")
async def get_statistics(
    lat: float = Query(settings.REGION_LAT, ge=-90, le=90),
    lon: float = Query(settings.REGION_LON, ge=-180, le=180),
    radius_km: float = Query(settings.REGION_RADIUS_KM, ge=10, le=1000),
) -> dict:
    """Summarize assessed data within the configured dashboard region."""
    zones = await get_risk_map(lat=lat, lon=lon, radius_km=radius_km)
    zone_list = zones["zones"]
    _, all_readings = repository.list_readings(10000, 0)
    from math import radians, sin, cos, asin, sqrt

    def is_in_region(record):
        try:
            rlat, rlon = float(record["latitude"]), float(record["longitude"])
            dlat, dlon = radians(rlat - lat), radians(rlon - lon)
            distance = 2 * 6371.0088 * asin(sqrt(sin(dlat / 2) ** 2 + cos(radians(lat)) * cos(radians(rlat)) * sin(dlon / 2) ** 2))
            return distance <= radius_km
        except (KeyError, TypeError, ValueError):
            return False

    readings = [r for r in all_readings if is_in_region(r)]
    levels = [z["risk_level"] for z in zone_list]
    scores = [z["confidence"] for z in zone_list if isinstance(z.get("confidence"), (int, float))]

    # Read area only from the latest completed, georeferenced satellite result
    # inside this region. No uploaded scene means area is genuinely unknown.
    satellite = None
    for job in repository.list_jobs(200, "COMPLETED"):
        if job.get("result") and job.get("result", {}).get("satellite_result"):
            candidate = job["result"]["satellite_result"]
            location = candidate.get("location") or {}
            image_lat = location.get("lat")
            image_lon = location.get("lon")
            if image_lat is None or image_lon is None:
                image = repository.get_upload(job["request"].get("satellite_image_id", ""), "satellite")
                location = image.get("location") if image else None
                image_lat = (location or {}).get("lat")
                image_lon = (location or {}).get("lon")
            if image_lat is None or image_lon is None or not is_in_region({"latitude": image_lat, "longitude": image_lon}):
                continue
            satellite = candidate
            break

    sensor_ids = {r["sensor_id"] for r in readings}
    assessed = bool(zone_list or readings)
    return {
        "status": "success",
        "region": {"name": settings.REGION_NAME, "latitude": lat, "longitude": lon,
                   "radius_km": radius_km, "scope": f"within {radius_km:g} km of {settings.REGION_NAME}"},
        "statistics": {
            "total_area_km2": satellite.get("total_area_km2") if satellite else None,
            "affected_area_km2": satellite.get("flood_area_km2") if satellite else None,
            "critical_zones": levels.count("CRITICAL") if assessed else None,
            "high_zones": levels.count("HIGH") if assessed else None,
            "medium_zones": levels.count("MEDIUM") if assessed else None,
            "low_zones": levels.count("LOW") if assessed else None,
            "active_sensors": len(sensor_ids),
            "sensor_readings": len(readings),
            "avg_confidence": round(sum(scores) / len(scores), 3) if scores else None,
            "assessment_status": "available" if assessed or satellite else "no_assessment",
            "satellite_status": "available" if satellite else "no_georeferenced_scene",
            "satellite_processed_at": satellite.get("processed_at") if satellite else None,
            "last_updated": datetime.now().isoformat()
        },
        "timestamp": datetime.now().isoformat()
    }


@router.get("/alerts")
async def get_alerts(
    acknowledged: Optional[bool] = None,
    limit: int = Query(50, ge=1, le=100)
) -> dict:
    """Get active alerts"""
    alerts = repository.list_alerts(limit)
    if acknowledged is not None:
        alerts = [alert for alert in alerts if alert.get("acknowledged", False) == acknowledged]
    
    return {
        "status": "success",
        "count": len(alerts),
        "alerts": alerts,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/health")
async def health_check() -> dict:
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "2.1.0",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "api": True,
            "websocket": True
        }
    }


# =============================================
# WEBSOCKET-ENABLED ENDPOINTS
# =============================================

@router.post("/alerts/push", dependencies=[Depends(require_admin)])
async def create_alert(alert_data: Dict[str, Any]):
    """Create and push a new alert to WebSocket clients"""
    new_alert = {
        "alert_id": f"ALT_{uuid4().hex[:12]}",
        "zone_id": alert_data.get("zone_id", "UNKNOWN"),
        "risk_level": alert_data.get("risk_level", "HIGH"),
        "alert_type": alert_data.get("alert_type", "flood"),
        "message": alert_data.get("message", "Alert triggered"),
        "generated_at": datetime.now().isoformat(),
        "acknowledged": False,
        "metadata": alert_data.get("metadata", {})
    }
    try:
        new_alert = Alert.model_validate(new_alert).model_dump(mode="json")
    except ValidationError as exc:
        raise HTTPException(422, detail=exc.errors()) from exc
    repository.save_alert(new_alert)
    
    # Push to WebSocket clients
    await push_alert(new_alert)
    
    return {
        "status": "success",
        "alert": new_alert,
        "timestamp": datetime.now().isoformat()
    }


@router.patch("/alerts/{alert_id}/acknowledge", dependencies=[Depends(require_admin)])
async def acknowledge_alert(alert_id: str):
    alerts = repository.list_alerts(500)
    alert = next((item for item in alerts if item["alert_id"] == alert_id), None)
    if not alert:
        raise HTTPException(404, "Alert not found")
    alert["acknowledged"] = True
    repository.save_alert(alert)
    return {"status": "success", "alert": alert, "timestamp": datetime.now().isoformat()}


@router.post("/risk/update", dependencies=[Depends(require_admin)])
async def update_risk_zones(risk_data: Dict[str, Any]):
    """Update risk zones and push to WebSocket"""
    zones = risk_data.get("zones", [])
    if not isinstance(zones, list):
        raise HTTPException(422, "zones must be a list")
    try:
        zones = [RiskZone.model_validate(zone).model_dump(mode="json") for zone in zones]
    except ValidationError as exc:
        raise HTTPException(422, detail=exc.errors()) from exc
    repository.save_risk_zones(zones)
    await manager.broadcast_to_room("risk", {
        "type": "risk_update",
        "data": risk_data,
        "timestamp": datetime.now().isoformat()
    })
    
    return {
        "status": "success",
        "message": "Risk zones updated",
        "timestamp": datetime.now().isoformat()
    }


@router.post("/sensor/update", dependencies=[Depends(require_admin)])
async def update_sensor_data(sensor_data: Dict[str, Any]):
    """Update sensor data and push to WebSocket"""
    await manager.broadcast_to_room("sensors", {
        "type": "sensor_update",
        "data": sensor_data,
        "timestamp": datetime.now().isoformat()
    })
    
    return {
        "status": "success",
        "message": "Sensor data updated",
        "timestamp": datetime.now().isoformat()
    }
