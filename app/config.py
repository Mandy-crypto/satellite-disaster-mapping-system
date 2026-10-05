"""
Configuration settings for the application.

Uses Pydantic Settings for environment variable management.
"""

from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    """Application settings."""
    
    # Application settings
    APP_NAME: str = "Satellite-Assisted Disaster Mapping System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Database settings
    DATABASE_URL: str = "sqlite:///./disaster.db"
    DATA_DIR: str = "./data"
    OPENWEATHER_API_KEY: str = ""
    IMD_API_KEY: str = ""
    USGS_WATER_STATIONS: str = "{}"

    # Region shown on the dashboard by default. Coordinates currently center
    # the project on Jabalpur, Madhya Pradesh; the public-feed radius is in km.
    REGION_NAME: str = "Jabalpur, Madhya Pradesh"
    REGION_LAT: float = 23.181
    REGION_LON: float = 79.951
    REGION_RADIUS_KM: float = 250.0
    MQTT_ENABLED: bool = True
    MQTT_HOST: str = "localhost"
    MQTT_PORT: int = 1883
    MQTT_TOPIC: str = "sensor/data"
    ADMIN_API_KEY: str = ""
    
    # CORS settings
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000"
    ]
    
    # File upload settings
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50 MB
    ALLOWED_IMAGE_TYPES: List[str] = [
        "image/jpeg",
        "image/png",
        "image/tiff",
        "image/geotiff"
    ]
    
    # Processing settings
    MAX_PROCESSING_JOBS: int = 100
    
    # ============ SATELLITE PROCESSING CONFIGURATION ============
    
    # NDWI threshold for flood detection (default: 0.2)
    NDWI_THRESHOLD: float = 0.2
    
    # Minimum flood area in pixels to consider as flood (avoid noise)
    MIN_FLOOD_AREA_PIXELS: int = 100
    
    # Minimum flood area in km² to report
    MIN_FLOOD_AREA_KM2: float = 0.01
    
    # Image resolution in meters per pixel (for area calculation)
    IMAGE_RESOLUTION_M: float = 10.0  # Sentinel-2 default
    
    # Output directory for visualizations
    OUTPUT_DIR: str = "./output"
    
    # Whether to save intermediate visualizations
    SAVE_VISUALIZATIONS: bool = True
    
    # Visualization output formats
    VISUALIZATION_FORMATS: List[str] = ["png", "jpg"]
    
    # Maximum image size for processing (resize if larger)
    MAX_IMAGE_PIXELS: int = 4096 * 4096
    
    # Default bands for multispectral images
    GREEN_BAND: str = "green"
    NIR_BAND: str = "nir"
    RED_BAND: str = "red"
    
    # Fallback band indices for common satellite sensors
    BAND_MAPPING: dict = {
        "sentinel2": {"green": 3, "nir": 8, "red": 4},
        "landsat8": {"green": 3, "nir": 5, "red": 4},
        "modis": {"green": 4, "nir": 2, "red": 1}
    }
    
    # Whether to use parallel processing
    USE_PARALLEL: bool = False
    
    # Number of worker threads for parallel processing
    NUM_WORKERS: int = 4
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


settings = Settings()

# Create output directory if it doesn't exist
if settings.SAVE_VISUALIZATIONS:
    os.makedirs(settings.OUTPUT_DIR, exist_ok=True)
