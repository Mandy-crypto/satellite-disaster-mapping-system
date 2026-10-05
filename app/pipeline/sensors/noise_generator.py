"""
Noise generation module for sensor data.

Adds realistic noise to sensor readings.
"""

import numpy as np
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class NoiseGenerator:
    """
    Generate realistic noise for sensor readings.
    
    Supports:
    - Gaussian noise
    - Uniform noise
    - Sensor-specific noise profiles
    """
    
    def __init__(self, noise_amount: float = 0.15, random_seed: Optional[int] = None):
        """
        Initialize noise generator.
        
        Args:
            noise_amount: Noise level (0-1)
            random_seed: Random seed for reproducibility
        """
        self.noise_amount = noise_amount
        if random_seed is not None:
            np.random.seed(random_seed)
        
        # Sensor-specific noise profiles
        self.sensor_noise_profiles = {
            'rainfall_mm': {'type': 'gaussian', 'std_scale': 0.15},
            'water_level_cm': {'type': 'gaussian', 'std_scale': 0.12},
            'soil_moisture_percent': {'type': 'gaussian', 'std_scale': 0.10},
            'temperature_c': {'type': 'gaussian', 'std_scale': 0.05},
        }
    
    def add_gaussian_noise(self, 
                          values: np.ndarray, 
                          std_scale: float = 0.1) -> np.ndarray:
        """
        Add Gaussian noise to values.
        
        Args:
            values: Input array
            std_scale: Standard deviation scale relative to value
            
        Returns:
            Array with added noise
        """
        # Calculate standard deviation based on value magnitude
        std = np.abs(values) * std_scale * self.noise_amount
        
        # Add noise
        noise = np.random.normal(0, std)
        noisy_values = values + noise
        
        # Ensure values stay within reasonable bounds
        # Use the noise amount as a bound
        max_deviation = np.abs(values) * self.noise_amount * 0.5
        noisy_values = np.clip(
            noisy_values, 
            values - max_deviation, 
            values + max_deviation
        )
        
        return noisy_values
    
    def add_uniform_noise(self, 
                         values: np.ndarray, 
                         range_scale: float = 0.1) -> np.ndarray:
        """
        Add uniform noise to values.
        
        Args:
            values: Input array
            range_scale: Range scale relative to value
            
        Returns:
            Array with added noise
        """
        half_range = np.abs(values) * range_scale * self.noise_amount
        noise = np.random.uniform(-half_range, half_range)
        noisy_values = values + noise
        
        return noisy_values
    
    def add_sensor_specific_noise(self, 
                                 readings: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        """
        Add sensor-specific noise to readings.
        
        Args:
            readings: Dictionary of parameter arrays
            
        Returns:
            Dictionary with noise added to each parameter
        """
        noisy_readings = {}
        
        for param_name, values in readings.items():
            if param_name in self.sensor_noise_profiles:
                profile = self.sensor_noise_profiles[param_name]
                noise_type = profile.get('type', 'gaussian')
                std_scale = profile.get('std_scale', 0.1)
                
                if noise_type == 'gaussian':
                    noisy_readings[param_name] = self.add_gaussian_noise(values, std_scale)
                elif noise_type == 'uniform':
                    noisy_readings[param_name] = self.add_uniform_noise(values, std_scale)
                else:
                    noisy_readings[param_name] = values
            else:
                # Default: add small gaussian noise
                noisy_readings[param_name] = self.add_gaussian_noise(values, 0.05)
        
        return noisy_readings
    
    def add_temporal_noise(self, 
                          readings: Dict[str, np.ndarray],
                          temporal_correlation: float = 0.8) -> Dict[str, np.ndarray]:
        """
        Add temporal correlation to readings (simulating time series).
        
        Args:
            readings: Dictionary of parameter arrays
            temporal_correlation: Correlation between consecutive readings
            
        Returns:
            Dictionary with temporal noise added
        """
        # This simulates multiple timestamps (e.g., 24 hours of data)
        # For simplicity, we'll just add small variations
        time_steps = 24  # 24 hours
        
        noisy_readings = {}
        for param_name, base_values in readings.items():
            # Expand to time series
            n_sensors = len(base_values)
            time_series = np.zeros((n_sensors, time_steps))
            
            for i in range(n_sensors):
                # Start with base value
                current = base_values[i]
                for t in range(time_steps):
                    # Add random walk with correlation
                    noise = np.random.normal(0, current * 0.02)
                    current = current * temporal_correlation + noise * (1 - temporal_correlation)
                    time_series[i, t] = current
            
            noisy_readings[param_name] = time_series
        
        return noisy_readings
    
    def add_outliers(self, 
                    values: np.ndarray, 
                    outlier_fraction: float = 0.02) -> np.ndarray:
        """
        Add occasional outlier values to simulate sensor errors.
        
        Args:
            values: Input array
            outlier_fraction: Fraction of values to make outliers
            
        Returns:
            Array with outliers
        """
        outlier_values = values.copy()
        n_outliers = int(len(values) * outlier_fraction)
        
        if n_outliers > 0:
            # Randomly select outlier indices
            indices = np.random.choice(len(values), n_outliers, replace=False)
            
            # Generate outliers (2-5x normal range)
            for idx in indices:
                factor = np.random.choice([-1, 1]) * np.random.uniform(2, 5)
                outlier_values[idx] = values[idx] * (1 + factor * self.noise_amount)
        
        return outlier_values
    
    def add_complete_noise(self, 
                          readings: Dict[str, np.ndarray],
                          add_outliers: bool = True,
                          add_temporal: bool = True) -> Dict[str, np.ndarray]:
        """
        Add complete noise profile to readings.
        
        Args:
            readings: Dictionary of parameter arrays
            add_outliers: Whether to add outliers
            add_temporal: Whether to add temporal noise
            
        Returns:
            Dictionary with comprehensive noise added
        """
        # Step 1: Add sensor-specific noise
        noisy = self.add_sensor_specific_noise(readings)
        
        # Step 2: Add outliers
        if add_outliers:
            for param_name in noisy.keys():
                if param_name not in ['risk_scores', 'risk_levels']:
                    noisy[param_name] = self.add_outliers(
                        noisy[param_name], 
                        outlier_fraction=0.02
                    )
        
        # Step 3: Add temporal noise (if requested)
        if add_temporal:
            noisy = self.add_temporal_noise(noisy)
        
        return noisy