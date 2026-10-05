"""
Satellite-Assisted Disaster Mapping System - Main Application
SIH 2026 - Multi-Disaster Risk Assessment Platform with MQTT, WebSocket Support
"""

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
from datetime import datetime
import logging
from app.config import settings

# =============================================
# LOGGING
# =============================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================
# CREATE APP
# =============================================

app = FastAPI(
    title="Satellite-Assisted Disaster Mapping System",
    description="SIH 2026 - Multi-Disaster Risk Assessment Platform with MQTT & WebSocket",
    version="2.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000,http://127.0.0.1:3000,http://127.0.0.1:8000").split(",") if origin.strip()],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================
# STATIC FILES
# =============================================

static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# =============================================
# IMPORT ROUTERS
# =============================================

from app.api import (
    satellite_router,
    sensors_router,
    process_router,
    dashboard_router,
    live_router,
    websocket_router
)

app.include_router(satellite_router)
app.include_router(sensors_router)
app.include_router(process_router)
app.include_router(dashboard_router)
app.include_router(live_router)
app.include_router(websocket_router)

# =============================================
# BASIC ROUTES
# =============================================

@app.get("/")
async def root():
    """Open the dashboard when visiting the server root."""
    return FileResponse(os.path.join(static_dir, "dashboard.html"))


@app.get("/api/info")
async def api_info():
    return {
        "message": "Satellite-Assisted Disaster Mapping System",
        "version": app.version,
        "status": "running",
        "dashboard": "/static/dashboard.html",
        "openapi": "/docs",
        "features": [
            "Satellite Processing",
            "Sensor Data (MQTT)",
            "Live Weather",
            "Earthquake Monitoring",
            "WebSocket Updates"
        ]
    }


@app.get("/api/health")
async def health_check():
    """Health check with MQTT & WebSocket status"""
    try:
        from app.services.mqtt_service import get_mqtt_service
        mqtt = get_mqtt_service()
        mqtt_status = mqtt.connected
        mqtt_messages = mqtt.total_messages
        active_sensors = len(mqtt.latest_readings)
    except:
        mqtt_status = False
        mqtt_messages = 0
        active_sensors = 0
    
    # WebSocket status
    from app.api.websocket import manager
    ws_stats = manager.get_stats()
    from app.services.repository import health_check as database_health
    storage_status = database_health()
    
    return {
        "status": "healthy" if storage_status else "degraded",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "api": True,
            "static": os.path.exists(static_dir),
            "storage": storage_status,
            "mqtt": mqtt_status,
            "mqtt_messages": mqtt_messages,
            "active_sensors": active_sensors,
            "websocket_connections": ws_stats.get("total", 0)
        }
    }


# =============================================
# MQTT SENSOR ENDPOINTS
# =============================================

@app.get("/api/mqtt/status")
async def get_mqtt_status():
    """Get MQTT connection status"""
    try:
        from app.services.mqtt_service import get_mqtt_service
        mqtt = get_mqtt_service()
        
        return {
            "status": "success",
            "mqtt": mqtt.get_sensor_status(),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }


@app.get("/api/live/sensors")
async def get_all_sensors(
    lat: float = Query(settings.REGION_LAT, ge=-90, le=90),
    lon: float = Query(settings.REGION_LON, ge=-180, le=180),
    radius_km: float = Query(settings.REGION_RADIUS_KM, ge=10, le=1000),
):
    """Get latest known MQTT or imported sensor readings in the selected region."""
    try:
        from app.services.mqtt_service import get_mqtt_service
        from app.services import repository
        from math import radians, sin, cos, asin, sqrt
        mqtt = get_mqtt_service()

        # The DB retains uploaded/MQTT observations across restarts; overlay
        # in-memory MQTT values so the newest live message always wins.
        _, records = repository.list_readings(10000, 0)
        latest = {}
        for record in records:
            latest.setdefault(record["sensor_id"], record)
        for record in mqtt.get_sensor_records():
            latest[record["sensor_id"]] = record

        readings = []
        for record in latest.values():
            try:
                rlat, rlon = float(record["latitude"]), float(record["longitude"])
                dlat, dlon = radians(rlat - lat), radians(rlon - lon)
                distance = 2 * 6371.0088 * asin(sqrt(sin(dlat / 2) ** 2 + cos(radians(lat)) * cos(radians(rlat)) * sin(dlon / 2) ** 2))
                if distance <= radius_km:
                    readings.append({**record, "distance_km": round(distance, 1)})
            except (KeyError, TypeError, ValueError):
                continue
        risk_summary = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for reading in readings:
            level = reading.get("risk_level")
            if level in risk_summary:
                risk_summary[level] += 1
        return {
            "status": "success",
            "count": len(readings),
            "sensors": [reading["sensor_id"] for reading in readings],
            "readings": readings,
            "risk_summary": risk_summary,
            "region": {"name": settings.REGION_NAME, "latitude": lat, "longitude": lon, "radius_km": radius_km},
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }


@app.get("/api/live/sensors/{sensor_id}")
async def get_sensor_data(sensor_id: str, limit: int = 20):
    """Get historical data for a specific sensor"""
    try:
        from app.services.mqtt_service import get_mqtt_service
        mqtt = get_mqtt_service()

        if sensor_id == "latest":
            readings = mqtt.get_latest_readings()
            return {"status": "success", "count": len(readings),
                    "readings": [r.__dict__ for r in readings], "timestamp": datetime.now().isoformat()}
        
        readings = mqtt.get_sensor_data(sensor_id, limit)
        
        return {
            "status": "success",
            "sensor_id": sensor_id,
            "count": len(readings),
            "readings": [r.__dict__ for r in readings],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }


@app.get("/api/live/sensors/latest")
async def get_latest_readings():
    """Get latest reading from all sensors"""
    try:
        from app.services.mqtt_service import get_mqtt_service
        mqtt = get_mqtt_service()
        
        readings = mqtt.get_latest_readings()
        
        return {
            "status": "success",
            "count": len(readings),
            "readings": [r.__dict__ for r in readings],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }


# =============================================
# STARTUP / SHUTDOWN
# =============================================

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("🚀 Starting Disaster Mapping System with MQTT & WebSocket Support...")

    from app.services.repository import initialize
    initialize()
    
    # Initialize MQTT service
    if settings.MQTT_ENABLED:
        try:
            from app.services.mqtt_service import get_mqtt_service
            mqtt = get_mqtt_service()
            mqtt.connect()
            logger.info("📡 MQTT service initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize MQTT service: {e}")
    else:
        logger.info("📡 MQTT ingestion disabled by MQTT_ENABLED")
    
    # Log WebSocket status
    from app.api.websocket import manager
    logger.info(f"🔌 WebSocket manager ready: {manager.get_stats()}")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown"""
    logger.info("🛑 Shutting down...")
    
    # Disconnect MQTT
    try:
        from app.services.mqtt_service import get_mqtt_service
        mqtt = get_mqtt_service()
        if settings.MQTT_ENABLED:
            mqtt.disconnect()
        logger.info("📡 MQTT disconnected")
    except Exception as e:
        logger.error(f"❌ Error disconnecting MQTT: {e}")
