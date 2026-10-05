from fastapi import APIRouter, Query, HTTPException
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

from app.models.schemas import SensorReading, SensorType, RiskLevel, Alert, AlertType
from app.services.public_data_service import public_data_service
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/live",
    tags=["Live Data"]
)


@router.get("/weather")
async def get_current_weather(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    use_cache: bool = Query(True)
) -> Dict[str, Any]:
    """Get current weather data"""
    try:
        reading = await public_data_service.current_weather(lat, lon)
        return {"status": "success", "data": reading, "location": {"lat": lat, "lon": lon},
                "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error("Error getting public weather: %s", e)
        raise HTTPException(status_code=502, detail="Weather provider is temporarily unavailable") from e


@router.get("/forecast")
async def get_weather_forecast(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    days: int = Query(5, ge=1, le=5)
) -> Dict[str, Any]:
    """Get 5-day weather forecast"""
    try:
        forecasts = await public_data_service.weather_forecast(lat, lon, days)
        return {"status": "success", "location": {"lat": lat, "lon": lon}, "forecast": forecasts,
                "source": "Open-Meteo forecast model", "generated_at": datetime.now().isoformat()}
    except Exception as e:
        logger.error("Error getting public forecast: %s", e)
        raise HTTPException(status_code=502, detail="Forecast provider is temporarily unavailable") from e


@router.get("/earthquakes")
async def get_earthquakes(
    limit: int = Query(20, ge=1, le=100),
    min_magnitude: float = Query(2.5, ge=0, le=10)
) -> Dict[str, Any]:
    """Get recent earthquakes from USGS"""
    try:
        try:
            from app.services.usgs_service import get_usgs_service
            service = get_usgs_service()
            earthquakes = await service.fetch_earthquakes()
            
            filtered = [eq for eq in earthquakes if eq.magnitude >= min_magnitude]
            filtered = filtered[:limit]
            
            return {
                "status": "success",
                "count": len(filtered),
                "earthquakes": [
                    {
                        "alert_id": eq.alert_id,
                        "magnitude": eq.magnitude,
                        "place": eq.place,
                        "location": {"lat": eq.latitude, "lon": eq.longitude},
                        "depth_km": eq.depth_km,
                        "time": eq.time,
                        "alert_level": eq.alert_level,
                        "message": eq.message,
                        "tsunami": eq.tsunami,
                        "url": eq.url
                    }
                    for eq in filtered
                ],
                "timestamp": datetime.now().isoformat()
            }
        except ImportError:
            return {
                "status": "success",
                "count": 0,
                "earthquakes": [],
                "message": "USGS service not available",
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"Error getting earthquakes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/earthquakes/near")
async def get_earthquakes_near(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(100, ge=10, le=500),
    min_magnitude: float = Query(2.5, ge=0, le=10)
) -> Dict[str, Any]:
    """Get earthquakes near a location"""
    try:
        try:
            from app.services.usgs_service import get_usgs_service
            service = get_usgs_service()
            earthquakes = await service.fetch_earthquakes()
            
            near_earthquakes = []
            for eq in earthquakes:
                if eq.magnitude < min_magnitude:
                    continue
                dist = service._calculate_distance(lat, lon, eq.latitude, eq.longitude)
                if dist <= radius_km:
                    near_earthquakes.append({
                        "alert_id": eq.alert_id,
                        "magnitude": eq.magnitude,
                        "place": eq.place,
                        "location": {"lat": eq.latitude, "lon": eq.longitude},
                        "depth_km": eq.depth_km,
                        "time": eq.time,
                        "alert_level": eq.alert_level,
                        "message": eq.message,
                        "distance_km": round(dist, 1)
                    })
            
            return {
                "status": "success",
                "location": {"lat": lat, "lon": lon},
                "radius_km": radius_km,
                "count": len(near_earthquakes),
                "earthquakes": near_earthquakes,
                "timestamp": datetime.now().isoformat()
            }
        except ImportError:
            return {
                "status": "success",
                "location": {"lat": lat, "lon": lon},
                "radius_km": radius_km,
                "count": 0,
                "earthquakes": [],
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"Error getting nearby earthquakes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/water-levels")
async def get_water_levels(
    lat: Optional[float] = Query(None, ge=-90, le=90),
    lon: Optional[float] = Query(None, ge=-180, le=180),
    radius_km: float = Query(100, ge=10, le=500)
) -> Dict[str, Any]:
    """Get water levels from USGS"""
    try:
        try:
            from app.services.usgs_service import get_usgs_service
            service = get_usgs_service()
            readings = await service.fetch_water_levels(lat, lon, radius_km)
            
            return {
                "status": "success",
                "count": len(readings),
                "readings": [
                    {
                        "station_id": r.station_id,
                        "station_name": r.station_name,
                        "location": {"lat": r.latitude, "lon": r.longitude},
                        "water_level_cm": r.water_level_cm,
                        "flood_stage_m": r.flood_stage_m,
                        "action_stage_m": r.action_stage_m,
                        "stage_status": r.stage_status,
                        "risk_score": r.risk_score,
                        "risk_level": r.risk_level,
                        "timestamp": r.timestamp
                    }
                    for r in readings
                ],
                "timestamp": datetime.now().isoformat()
            }
        except ImportError:
            return {
                "status": "success",
                "count": 0,
                "readings": [],
                "message": "USGS water service not available",
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"Error getting water levels: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/river-levels")
async def get_public_river_levels(
    lat: float = Query(23.181, ge=-90, le=90),
    lon: float = Query(79.951, ge=-180, le=180),
    radius_km: float = Query(250, ge=10, le=1000),
):
    """Get nearby CWC Narmada basin station observations from NWIC."""
    try:
        return await public_data_service.cwc_river_levels(lat, lon, radius_km)
    except Exception as e:
        logger.exception("CWC/NWIC river data request failed")
        raise HTTPException(status_code=502, detail="NWIC river telemetry is temporarily unavailable") from e


@router.get("/india-stations")
async def get_india_weather_stations(state_id: int = Query(27, ge=1, le=36)):
    """Get IMD AWS/ARG station observations when an IMD API key is configured."""
    try:
        return await public_data_service.imd_stations(settings.IMD_API_KEY, state_id)
    except Exception as e:
        logger.exception("IMD AWS feed request failed")
        raise HTTPException(status_code=502, detail="IMD data unavailable; check API access and IMD_API_KEY") from e


@router.get("/india-warnings")
async def get_india_warnings():
    """Get official IMD district warnings when an IMD API key is configured."""
    try:
        return await public_data_service.imd_warnings(settings.IMD_API_KEY)
    except Exception as e:
        logger.exception("IMD warnings request failed")
        raise HTTPException(status_code=502, detail="IMD warnings unavailable; check API access and IMD_API_KEY") from e


@router.get("/combined-risk")
async def get_combined_risk(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180)
) -> Dict[str, Any]:
    """Get combined risk from multiple sources"""
    try:
        try:
            from app.services.usgs_service import get_usgs_service
            service = get_usgs_service()
            
            await service.fetch_earthquakes()
            await service.fetch_water_levels()
            
            combined = await service.calculate_combined_risk(lat, lon)
            
            return {
                "status": "success",
                "location": {"lat": lat, "lon": lon},
                "risk": {
                    "combined_risk": combined.combined_risk,
                    "risk_level": combined.risk_level,
                    "earthquake_risk": combined.earthquake_risk,
                    "water_risk": combined.water_risk
                },
                "alerts": combined.alerts,
                "timestamp": combined.timestamp
            }
        except ImportError:
            return {
                "status": "success",
                "location": {"lat": lat, "lon": lon},
                "risk": {
                    "combined_risk": 0.0,
                    "risk_level": "LOW",
                    "earthquake_risk": 0.0,
                    "water_risk": 0.0
                },
                "alerts": [],
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"Error calculating combined risk: {e}")
        raise HTTPException(status_code=500, detail=str(e))
