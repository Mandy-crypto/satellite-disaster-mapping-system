"""
Spatial correlation module for sensor data.

Implements distance-based correlation using Gaussian and IDW-like functions.
"""

import numpy as np
from typing import Tuple, Dict, Any, List
from scipy.spatial.distance import cdist
import logging

logger = logging.getLogger(__name__)


class SpatialCorrelator:
    """
    Implements spatial correlation for sensor readings.
    
    Uses distance-weighted functions to correlate readings
    with distance from flood center.
    """
    
    def __init__(self, config: Any):
        """
        Initialize spatial correlator.
        
        Args:
            config: SensorConfig object
        """
        self.config = config
        self.flood_center = np.array([
            config.FLOOD_CENTER_LAT,
            config.FLOOD_CENTER_LON
        ])
        
    def calculate_distances(self, 
                           locations: np.ndarray) -> np.ndarray:
        """
        Calculate distances from flood center.
        
        Args:
            locations: Array of (lat, lon) coordinates
            
        Returns:
            Array of distances in kilometers
        """
        # Convert to radians for haversine calculation
        lat1, lon1 = np.radians(self.flood_center[0]), np.radians(self.flood_center[1])
        lat2, lon2 = np.radians(locations[:, 0]), np.radians(locations[:, 1])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
        c = 2 * np.arcsin(np.sqrt(a))
        r = 6371  # Earth's radius in km
        
        return r * c
    
    def gaussian_weight(self, 
                        distances: np.ndarray, 
                        sigma: float = 2.0) -> np.ndarray:
        """
        Calculate Gaussian weights based on distance.
        
        Args:
            distances: Array of distances in km
            sigma: Spread parameter (km)
            
        Returns:
            Array of weights (0-1)
        """
        return np.exp(-(distances ** 2) / (2 * sigma ** 2))
    
    def inverse_distance_weight(self, 
                               distances: np.ndarray, 
                               power: float = 2.0) -> np.ndarray:
        """
        Calculate inverse distance weights.
        
        Args:
            distances: Array of distances in km
            power: Power parameter
            
        Returns:
            Array of weights (0-1)
        """
        # Avoid division by zero
        distances_safe = np.maximum(distances, 0.01)
        weights = 1 / (distances_safe ** power)
        return weights / np.max(weights)
    
    def get_risk_level(self, distance: float) -> str:
        """
        Determine risk level based on distance from flood center.
        
        Args:
            distance: Distance in km
            
        Returns:
            Risk level string
        """
        if distance <= self.config.RISK_DISTANCES["CRITICAL"]:
            return "CRITICAL"
        elif distance <= self.config.RISK_DISTANCES["HIGH"]:
            return "HIGH"
        elif distance <= self.config.RISK_DISTANCES["MEDIUM"]:
            return "MEDIUM"
        else:
            return "LOW"
    
    def get_risk_score(self, distance: float) -> float:
        """
        Calculate risk score based on distance.
        
        Args:
            distance: Distance in km
            
        Returns:
            Risk score (0-1)
        """
        # Use inverse distance with decay
        max_distance = self.config.RISK_DISTANCES["MEDIUM"] * 2
        if distance <= 0:
            return 1.0
        elif distance >= max_distance:
            return 0.0
        
        # Decay function: 1 / (1 + (distance/3)^2)
        return 1 / (1 + (distance / 3) ** 2)
    
    def apply_correlation(self, 
                         locations: np.ndarray,
                         param_range: Tuple[float, float],
                         distance_effect: bool = True) -> np.ndarray:
        """
        Apply spatial correlation to parameter values.
        
        Args:
            locations: Array of (lat, lon) coordinates
            param_range: (min, max) range for parameter
            distance_effect: Whether to apply distance weighting
            
        Returns:
            Array of correlated values
        """
        # Calculate distances from flood center
        distances = self.calculate_distances(locations)
        
        # Base values (uniform random within range)
        base_values = np.random.uniform(
            param_range[0], 
            param_range[1], 
            len(locations)
        )
        
        if not distance_effect:
            return base_values
        
        # Calculate distance weights
        weights = self.gaussian_weight(distances, sigma=3.0)
        
        # Apply weight: closer to center -> higher values
        # Center values should be at the upper end of the range
        center_value = param_range[1]
        min_value = param_range[0]
        
        # Weighted blend: base_value * (1 - weight) + center_value * weight
        correlated = base_values * (1 - weights) + center_value * weights
        
        return correlated
    
    def get_parameter_range(self, scenario: str) -> Dict[str, Tuple[float, float]]:
        """
        Get parameter ranges for a scenario.
        
        Args:
            scenario: 'normal', 'warning', or 'critical'
            
        Returns:
            Dictionary of parameter ranges
        """
        from app.pipeline.sensors.config import Scenario
        scenario_enum = Scenario(scenario)
        return self.config.SCENARIO_RANGES[scenario_enum]
    
    def generate_spatially_correlated_readings(self,
                                               locations: np.ndarray,
                                               scenario: str) -> Dict[str, np.ndarray]:
        """
        Generate full set of spatially correlated readings.
        
        Args:
            locations: Array of (lat, lon) coordinates
            scenario: Operating scenario
            
        Returns:
            Dictionary with arrays for each parameter
        """
        ranges = self.get_parameter_range(scenario)
        
        # Generate correlated values for each parameter
        readings = {}
        
        for param_name, param_range in ranges.items():
            # Different parameters have different correlation strengths
            if param_name in ["rainfall_mm", "water_level_cm", "soil_moisture_percent"]:
                # Strong correlation with distance
                readings[param_name] = self.apply_correlation(
                    locations, param_range, distance_effect=True
                )
            else:
                # Weak or no correlation (temperature)
                readings[param_name] = self.apply_correlation(
                    locations, param_range, distance_effect=False
                )
        
        # Calculate risk scores
        distances = self.calculate_distances(locations)
        readings['risk_scores'] = np.array([self.get_risk_score(d) for d in distances])
        readings['risk_levels'] = np.array([self.get_risk_level(d) for d in distances])
        
        return readings