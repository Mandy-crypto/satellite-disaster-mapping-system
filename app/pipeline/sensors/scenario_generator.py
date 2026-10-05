"""
Scenario generator for sensor simulation.

Creates different scenarios (NORMAL, WARNING, CRITICAL) with appropriate
parameter distributions.
"""

import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
import logging

from app.pipeline.sensors.config import Scenario, SensorConfig
from app.pipeline.sensors.spatial_correlation import SpatialCorrelator
from app.pipeline.sensors.noise_generator import NoiseGenerator

logger = logging.getLogger(__name__)


@dataclass
class ScenarioData:
    """Container for scenario data."""
    scenario: Scenario
    readings: Dict[str, np.ndarray]
    locations: np.ndarray
    sensor_ids: List[str]
    timestamps: List[str]


class ScenarioGenerator:
    """
    Generate sensor data for different scenarios.
    
    Creates spatially correlated sensor readings for NORMAL,
    WARNING, and CRITICAL scenarios.
    """
    
    def __init__(self, config: SensorConfig):
        """
        Initialize scenario generator.
        
        Args:
            config: SensorConfig object
        """
        self.config = config
        self.correlator = SpatialCorrelator(config)
        self.noise_generator = NoiseGenerator(
            noise_amount=config.NOISE_AMOUNT,
            random_seed=config.RANDOM_SEED
        )
        
        # Set random seed
        np.random.seed(config.RANDOM_SEED)
    
    def generate_sensor_locations(self) -> np.ndarray:
        """
        Generate sensor locations distributed across the region.
        
        Returns:
            Array of (lat, lon) coordinates
        """
        n_sensors = self.config.NUM_SENSORS
        
        # Generate base grid with some randomness
        # Use Poisson disk sampling for even distribution
        locations = []
        
        # Create grid points
        lat_range = self.config.LAT_MAX - self.config.LAT_MIN
        lon_range = self.config.LON_MAX - self.config.LON_MIN
        
        # Number of points in each dimension
        n_lat = int(np.sqrt(n_sensors * (lat_range / lon_range)))
        n_lon = int(n_sensors / n_lat)
        
        # Generate grid with jitter
        for i in range(n_lat):
            for j in range(n_lon):
                lat = self.config.LAT_MIN + (i + 0.5) * (lat_range / n_lat)
                lon = self.config.LON_MIN + (j + 0.5) * (lon_range / n_lon)
                
                # Add random jitter (spacing / 3)
                lat_jitter = np.random.uniform(-0.5, 0.5) * (lat_range / n_lat) * 0.5
                lon_jitter = np.random.uniform(-0.5, 0.5) * (lon_range / n_lon) * 0.5
                
                lat = np.clip(lat + lat_jitter, self.config.LAT_MIN, self.config.LAT_MAX)
                lon = np.clip(lon + lon_jitter, self.config.LON_MIN, self.config.LON_MAX)
                
                locations.append([lat, lon])
        
        # If we have more locations than needed, randomly sample
        if len(locations) > n_sensors:
            indices = np.random.choice(len(locations), n_sensors, replace=False)
            locations = [locations[i] for i in indices]
        
        # If we have fewer, add random points
        while len(locations) < n_sensors:
            lat = np.random.uniform(self.config.LAT_MIN, self.config.LAT_MAX)
            lon = np.random.uniform(self.config.LON_MIN, self.config.LON_MAX)
            locations.append([lat, lon])
        
        # Add some clustering around flood center
        n_cluster = int(n_sensors * 0.15)  # 15% clustered
        if n_cluster > 0:
            cluster_indices = np.random.choice(len(locations), n_cluster, replace=False)
            for idx in cluster_indices:
                # Move closer to flood center
                center_lat = self.config.FLOOD_CENTER_LAT
                center_lon = self.config.FLOOD_CENTER_LON
                radius = np.random.uniform(0.01, 0.03)  # ~1-3 km
                angle = np.random.uniform(0, 2 * np.pi)
                locations[idx][0] = center_lat + radius * np.cos(angle)
                locations[idx][1] = center_lon + radius * np.sin(angle)
        
        return np.array(locations)
    
    def generate_sensor_ids(self, n_sensors: int) -> List[str]:
        """
        Generate unique sensor IDs.
        
        Args:
            n_sensors: Number of sensors
            
        Returns:
            List of sensor IDs
        """
        prefix = self.config.SENSOR_ID_PREFIX
        return [f"{prefix}{i:04d}" for i in range(1, n_sensors + 1)]
    
    def generate_timestamps(self, n_sensors: int) -> List[str]:
        """
        Generate timestamps for sensor readings.
        
        Args:
            n_sensors: Number of sensors
            
        Returns:
            List of ISO format timestamps
        """
        from datetime import datetime, timedelta
        
        # Current time
        now = datetime.now()
        
        # Generate timestamps with some spread
        timestamps = []
        for i in range(n_sensors):
            # Random offset within last hour
            offset_seconds = np.random.uniform(0, 3600)
            timestamp = now - timedelta(seconds=offset_seconds)
            timestamps.append(timestamp.isoformat())
        
        return timestamps
    
    def generate_scenario(self, 
                         scenario: Scenario = None) -> ScenarioData:
        """
        Generate complete scenario data.
        
        Args:
            scenario: Scenario to generate (defaults to config.SCENARIO)
            
        Returns:
            ScenarioData object containing all readings
        """
        if scenario is None:
            scenario = self.config.SCENARIO
        
        logger.info(f"Generating {scenario.value} scenario with {self.config.NUM_SENSORS} sensors")
        
        # Generate locations
        locations = self.generate_sensor_locations()
        
        # Generate spatially correlated readings
        readings = self.correlator.generate_spatially_correlated_readings(
            locations, 
            scenario.value
        )
        
        # Add noise
        readings = self.noise_generator.add_complete_noise(
            readings,
            add_outliers=True,
            add_temporal=False
        )
        
        # Generate sensor IDs
        sensor_ids = self.generate_sensor_ids(len(locations))
        
        # Generate timestamps
        timestamps = self.generate_timestamps(len(locations))
        
        return ScenarioData(
            scenario=scenario,
            readings=readings,
            locations=locations,
            sensor_ids=sensor_ids,
            timestamps=timestamps
        )
    
    def generate_all_scenarios(self) -> Dict[Scenario, ScenarioData]:
        """
        Generate data for all three scenarios.
        
        Returns:
            Dictionary mapping scenarios to ScenarioData
        """
        scenarios = {}
        for scenario in [Scenario.NORMAL, Scenario.WARNING, Scenario.CRITICAL]:
            scenarios[scenario] = self.generate_scenario(scenario)
        
        return scenarios
    
    def get_summary_statistics(self, 
                              data: ScenarioData) -> Dict[str, Any]:
        """
        Get summary statistics for generated data.
        
        Args:
            data: ScenarioData object
            
        Returns:
            Dictionary with summary statistics
        """
        readings = data.readings
        locations = data.locations
        
        # Calculate distances from flood center
        distances = self.correlator.calculate_distances(locations)
        
        stats = {
            'scenario': data.scenario.value,
            'num_sensors': len(locations),
            'sensor_distribution': {
                'min_distance_km': float(np.min(distances)),
                'max_distance_km': float(np.max(distances)),
                'mean_distance_km': float(np.mean(distances)),
                'std_distance_km': float(np.std(distances))
            },
            'parameter_statistics': {}
        }
        
        # Statistics for each parameter
        for param_name, values in readings.items():
            if param_name in ['risk_scores', 'risk_levels']:
                continue
            if isinstance(values, np.ndarray):
                stats['parameter_statistics'][param_name] = {
                    'min': float(np.min(values)),
                    'max': float(np.max(values)),
                    'mean': float(np.mean(values)),
                    'std': float(np.std(values))
                }
        
        # Risk level distribution
        risk_levels = readings.get('risk_levels', [])
        risk_counts = {}
        for level in ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']:
            risk_counts[level] = int(np.sum(risk_levels == level))
        stats['risk_distribution'] = risk_counts
        
        return stats