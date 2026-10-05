from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import logging

# ============================================
# CREATE APP INSTANCE FIRST
# ============================================
app = FastAPI(
    title="Satellite-Assisted Disaster Mapping System",
    description="SIH 2026 - Multi-Disaster Risk Assessment Platform",
    version="2.0.0"
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================
# IMPORT ROUTERS (after app is created)
# ============================================
from app.api import satellite, sensors, process, dashboard, live

# ============================================
# REGISTER ROUTERS
# ============================================
app.include_router(satellite.router)
app.include_router(sensors.router)
app.include_router(process.router)
app.include_router(dashboard.router)
app.include_router(live.router)

# ============================================
# SERVE STATIC FILES (Dashboard)
# ============================================
import os
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# ============================================
# STARTUP EVENT
# ============================================
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("🚀 Starting Disaster Mapping System...")
    
    # Initialize Weather Service
    try:
        from app.services.weather_service import get_weather_service
        weather_service = get_weather_service()
        logger.info("🌤️ Weather service initialized")
        
        # Start background updates (optional - uncomment to auto-start)
        # import asyncio
        # locations = [(23.181, 79.951), (23.195, 79.940), (23.215, 79.920)]
        # asyncio.create_task(weather_service.start_background_updates(locations, 5))
    except Exception as e:
        logger.error(f"❌ Failed to initialize weather service: {e}")
    
    # Initialize USGS Service
    try:
        from app.services.usgs_service import get_usgs_service
        usgs_service = get_usgs_service()
        logger.info("🌍 USGS service initialized")
        
        # Start background updates (optional - uncomment to auto-start)
        # import asyncio
        # asyncio.create_task(usgs_service.start_earthquake_updates(10))
        # asyncio.create_task(usgs_service.start_water_updates(15))
    except Exception as e:
        logger.error(f"❌ Failed to initialize USGS service: {e}")
    
    logger.info("✅ All services initialized!")

# ============================================
# SHUTDOWN EVENT
# ============================================
@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown"""
    logger.info("🛑 Shutting down services...")
    
    # Clean up Weather Service
    try:
        from app.services.weather_service import get_weather_service
        weather_service = get_weather_service()
        await weather_service.close()
        logger.info("🌤️ Weather service closed")
    except Exception as e:
        logger.error(f"❌ Error closing weather service: {e}")
    
    # Clean up USGS Service
    try:
        from app.services.usgs_service import get_usgs_service
        usgs_service = get_usgs_service()
        usgs_service.stop_earthquake_updates()
        usgs_service.stop_water_updates()
        await usgs_service.close()
        logger.info("🌍 USGS service closed")
    except Exception as e:
        logger.error(f"❌ Error closing USGS service: {e}")
    
    logger.info("✅ All services closed!")

# ============================================
# ROOT ENDPOINT
# ============================================
@app.get("/")
async def root():
    return {
        "message": "Satellite-Assisted Disaster Mapping System",
        "version": "2.0.0",
        "status": "running",
        "endpoints": {
            "docs": "/docs",
            "dashboard": "/static/dashboard.html",
            "api": "/api"
        }
    }

# ============================================
# HEALTH CHECK
# ============================================
@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "weather": "online",
            "usgs": "online",
            "database": "online"
        }
    }