"""
Configuration for sensor simulation.

Defines geographic bounds, scenario parameters, and simulation settings.
"""

from dataclasses import dataclass, field
from typing import Tuple, Optional, Dict, Any
from enum import Enum


class Scenario(str, Enum):
    """Operating scenarios for sensor simulation."""
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class SensorConfig:
    """Configuration for sensor simulation."""
    
    # Geographic bounds (latitude, longitude)
    LAT_MIN: float = 23.0
    LAT_MAX: float = 23.5
    LON_MIN: float = 79.5
    LON_MAX: float = 80.0
    
    # Flood center (epicenter)
    FLOOD_CENTER_LAT: float = 23.25
    FLOOD_CENTER_LON: float = 79.75
    
    # Number of sensors
    NUM_SENSORS: int = 100
    
    # Scenario
    SCENARIO: Scenario = Scenario.NORMAL
    
    # Random seed for reproducibility
    RANDOM_SEED: int = 42
    
    # Noise levels
    NOISE_AMOUNT: float = 0.15  # 15% noise
    
    # Sensor ID prefix
    SENSOR_ID_PREFIX: str = "S"
    
    # Output directory
    OUTPUT_DIR: str = "./sensor_output"
    
    # Visualization settings
    VISUALIZE: bool = True
    VISUALIZATION_FORMAT: str = "html"
    
    # Export formats
    EXPORT_CSV: bool = True
    EXPORT_JSON: bool = True
    EXPORT_GEOJSON: bool = True
    
    # Scenario-specific parameter ranges
    SCENARIO_RANGES: Dict[Scenario, Dict[str, Tuple[float, float]]] = field(default_factory=lambda: {
        Scenario.NORMAL: {
            "rainfall_mm": (0.0, 20.0),
            "water_level_cm": (20.0, 40.0),
            "soil_moisture_percent": (30.0, 50.0),
            "temperature_c": (25.0, 30.0)
        },
        Scenario.WARNING: {
            "rainfall_mm": (40.0, 70.0),
            "water_level_cm": (60.0, 90.0),
            "soil_moisture_percent": (55.0, 75.0),
            "temperature_c": (24.0, 28.0)
        },
        Scenario.CRITICAL: {
            "rainfall_mm": (80.0, 150.0),
            "water_level_cm": (100.0, 180.0),
            "soil_moisture_percent": (80.0, 95.0),
            "temperature_c": (22.0, 27.0)
        }
    })
    
    # Risk level thresholds
    RISK_THRESHOLDS: Dict[str, Tuple[float, float]] = field(default_factory=lambda: {
        "LOW": (0.0, 0.3),
        "MEDIUM": (0.3, 0.5),
        "HIGH": (0.5, 0.7),
        "CRITICAL": (0.7, 1.0)
    })
    
    # Distance thresholds for risk levels (km)
    RISK_DISTANCES: Dict[str, float] = field(default_factory=lambda: {
        "CRITICAL": 1.0,
        "HIGH": 3.0,
        "MEDIUM": 6.0
    })
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.LAT_MIN >= self.LAT_MAX:
            raise ValueError("LAT_MIN must be less than LAT_MAX")
        if self.LON_MIN >= self.LON_MAX:
            raise ValueError("LON_MIN must be less than LON_MAX")
        if self.NUM_SENSORS < 10:
            raise ValueError("NUM_SENSORS must be at least 10")
        if self.NOISE_AMOUNT < 0 or self.NOISE_AMOUNT > 0.5:
            raise ValueError("NOISE_AMOUNT must be between 0 and 0.5")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "geographic_bounds": {
                "lat_min": self.LAT_MIN,
                "lat_max": self.LAT_MAX,
                "lon_min": self.LON_MIN,
                "lon_max": self.LON_MAX
            },
            "flood_center": {
                "lat": self.FLOOD_CENTER_LAT,
                "lon": self.FLOOD_CENTER_LON
            },
            "num_sensors": self.NUM_SENSORS,
            "scenario": self.SCENARIO.value,
            "random_seed": self.RANDOM_SEED,
            "noise_amount": self.NOISE_AMOUNT
        }