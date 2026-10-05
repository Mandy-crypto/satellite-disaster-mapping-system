"""
Canonical Data Schemas - Satellite-Assisted Disaster Mapping System
DO NOT MODIFY - This is the frozen data contract
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# ============================================
# ENUMS - All enums used across the system
# ============================================

class RiskLevel(str, Enum):
    """Risk level classification"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SensorType(str, Enum):
    """Types of sensors"""
    WEATHER = "weather"
    WATER_LEVEL = "water_level"
    SOIL = "soil"
    RAINFALL = "rainfall"
    SEISMIC = "seismic"
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"


class ProcessingStatus(str, Enum):
    """Processing job status"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class AlertType(str, Enum):
    """Alert types"""
    EARTHQUAKE = "earthquake"
    FLOOD = "flood"
    CYCLONE = "cyclone"
    WILDFIRE = "wildfire"
    LANDSLIDE = "landslide"
    WEATHER = "weather"
    WATER_LEVEL = "water_level"
    HEAVY_RAINFALL = "heavy_rainfall"
    HIGH_WIND = "high_wind"
    EXTREME_HEAT = "extreme_heat"
    FREEZING = "freezing"


class JobStatus(str, Enum):
    """Job status for async processing"""
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


# ============================================
# SCHEMAS A-J
# ============================================

# A. Satellite Image Input
class SatelliteImageInput(BaseModel):
    """Input schema for satellite image upload"""
    image_id: str
    image_path: str
    before_image_path: Optional[str] = None
    location: Dict[str, float]  # {"lat": float, "lon": float}
    acquisition_date: str
    bands: Optional[List[str]] = None
    threshold: Optional[float] = 0.2


# B. Satellite Processing Result
class SatelliteProcessingResult(BaseModel):
    """Output from satellite processing pipeline"""
    image_id: str
    location: Dict[str, float]
    flood_probability: float
    flood_area_km2: float
    flood_percentage: float
    ndwi_values: Optional[List[List[float]]] = None
    mask: Optional[List[List[int]]] = None
    status: str  # "success" or "error"
    error: Optional[str] = None
    processed_at: str


# C. Sensor Reading Input
class SensorReadingInput(BaseModel):
    """Input schema for sensor data"""
    sensor_id: str
    latitude: float
    longitude: float
    timestamp: str
    rainfall_mm: float
    water_level_cm: float
    soil_moisture_percent: float
    temperature_c: float


# D. Sensor Reading
class SensorReading(BaseModel):
    """Complete sensor reading with risk assessment"""
    sensor_id: str
    latitude: float
    longitude: float
    timestamp: str
    rainfall_mm: float
    water_level_cm: float
    soil_moisture_percent: float
    temperature_c: float
    sensor_type: Optional[SensorType] = SensorType.WEATHER
    risk_score: Optional[float] = None
    risk_level: Optional[RiskLevel] = None


# E. Sensor Processing Result
class SensorProcessingResult(BaseModel):
    """Output from sensor processing"""
    sensor_id: str
    location: Dict[str, float]
    risk_score: float
    risk_level: RiskLevel
    rainfall_score: float
    water_level_score: float
    soil_moisture_score: float
    confidence: float
    processed_at: str


# F. Processing Request
class ProcessingRequest(BaseModel):
    """Request to start processing"""
    job_id: str
    satellite_image_id: Optional[str] = None
    sensor_file_id: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None


# G. Processing Result
class ProcessingResult(BaseModel):
    """Complete processing result"""
    job_id: str
    status: ProcessingStatus
    satellite_result: Optional[SatelliteProcessingResult] = None
    sensor_result: Optional[SensorProcessingResult] = None
    fusion_result: Optional[Dict[str, Any]] = None
    started_at: str
    completed_at: Optional[str] = None
    error: Optional[str] = None


# H. Risk Zone
class RiskZone(BaseModel):
    """Individual risk zone in the grid"""
    zone_id: str
    grid_cell: str
    location: Dict[str, float]  # {"lat": float, "lon": float}
    risk_score: float
    risk_level: RiskLevel
    confidence: float
    satellite_contribution: float
    sensor_contribution: float
    explanation: str
    disagreement: bool


# I. Risk Statistics
class RiskStatistics(BaseModel):
    """Overall risk statistics"""
    total_area_km2: float
    affected_area_km2: float
    critical_zones: int
    high_zones: int
    medium_zones: int
    low_zones: int
    active_sensors: int
    avg_confidence: float
    last_updated: str


# J. Alert
class Alert(BaseModel):
    """Alert notification"""
    alert_id: str
    zone_id: str
    risk_level: RiskLevel
    alert_type: AlertType
    message: str
    generated_at: str
    acknowledged: bool = False
    metadata: Optional[Dict[str, Any]] = None


# K. Health Check
class HealthCheck(BaseModel):
    """Health check response"""
    status: str
    version: str
    timestamp: str
    services: Dict[str, bool]


# L. Earthquake Event (USGS)
class EarthquakeEvent(BaseModel):
    """Earthquake data from USGS"""
    alert_id: str
    event_id: str
    magnitude: float
    place: str
    latitude: float
    longitude: float
    depth_km: float
    time: str
    url: str
    status: str
    tsunami: int
    sig: int
    alert_level: RiskLevel
    message: str
    generated_at: str
    source: str = "usgs"


# M. Water Level Reading (USGS)
class WaterLevelReading(BaseModel):
    """Water level data from USGS"""
    station_id: str
    station_name: str
    latitude: float
    longitude: float
    water_level_m: float
    water_level_cm: float
    discharge_cfs: Optional[float] = None
    timestamp: str
    flood_stage_m: float
    action_stage_m: float
    stage_status: str  # NORMAL/ACTION/FLOOD/MAJOR_FLOOD
    risk_score: float
    risk_level: RiskLevel
    source: str = "usgs_waterdata"


# N. Combined Risk
class CombinedRisk(BaseModel):
    """Combined risk from multiple sources"""
    location_id: str
    latitude: float
    longitude: float
    earthquake_risk: float
    water_risk: float
    combined_risk: float
    risk_level: RiskLevel
    alerts: List[Dict[str, Any]]
    timestamp: str