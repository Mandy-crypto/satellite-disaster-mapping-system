"""
API Routers - Export all routers
"""

from .satellite import router as satellite_router
from .sensors import router as sensors_router
from .process import router as process_router
from .dashboard import router as dashboard_router
from .live import router as live_router
from .websocket import router as websocket_router
from .safety import router as safety_router

__all__ = [
    "satellite_router",
    "sensors_router",
    "process_router",
    "dashboard_router",
    "live_router",
    "websocket_router",
    "safety_router"
]
