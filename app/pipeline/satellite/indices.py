"""
Spectral index calculation module.

Calculates NDWI (Normalized Difference Water Index) and other indices.
"""

import numpy as np
from typing import Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class IndexCalculator:
    """
    Calculate spectral indices for satellite imagery.
    
    Primary indices:
    - NDWI: Normalized Difference Water Index
    - MNDWI: Modified NDWI
    - NDVI: Normalized Difference Vegetation Index
    """
    
    def __init__(self):
        """Initialize index calculator."""
        self.last_ndwi = None
        self.last_ndvi = None
    
    def calculate_ndwi(self, green: np.ndarray, nir: np.ndarray) -> np.ndarray:
        """
        Calculate Normalized Difference Water Index.
        
        Formula: NDWI = (Green - NIR) / (Green + NIR)
        
        Values range from -1 to 1, where:
        - > 0.2 indicates water presence
        - 0 to 0.2 indicates moderate water content
        - < 0 indicates non-water (land, vegetation)
        
        Args:
            green: Green band (2D array)
            nir: Near-Infrared band (2D array)
            
        Returns:
            NDWI array (2D, float32)
            
        Raises:
            ValueError: If arrays have different shapes or contain invalid values
        """
        if green.shape != nir.shape:
            raise ValueError(f"Green {green.shape} and NIR {nir.shape} shapes don't match")
        
        # Ensure arrays are float
        green = green.astype(np.float32)
        nir = nir.astype(np.float32)
        
        # Clip to valid range
        green = np.clip(green, 0, 1)
        nir = np.clip(nir, 0, 1)
        
        # Calculate NDWI with safe division
        denominator = green + nir
        ndwi = np.zeros_like(green, dtype=np.float32)
        
        # Only calculate where denominator > 0
        valid = denominator > 0
        ndwi[valid] = (green[valid] - nir[valid]) / denominator[valid]
        
        # Handle special cases (both zero)
        ndwi[~valid] = -1.0  # Treat as non-water
        
        # Clip to valid range
        ndwi = np.clip(ndwi, -1, 1)
        
        # Store for reference
        self.last_ndwi = ndwi
        
        logger.info(f"NDWI calculated: min={ndwi.min():.3f}, max={ndwi.max():.3f}, "
                   f"mean={ndwi.mean():.3f}")
        
        return ndwi
    
    def calculate_mndwi(self, green: np.ndarray, swir: np.ndarray) -> np.ndarray:
        """
        Calculate Modified Normalized Difference Water Index.
        
        Formula: MNDWI = (Green - SWIR) / (Green + SWIR)
        
        Better for urban water detection.
        
        Args:
            green: Green band (2D array)
            swir: Short-wave Infrared band (2D array)
            
        Returns:
            MNDWI array (2D, float32)
        """
        if green.shape != swir.shape:
            raise ValueError(f"Green {green.shape} and SWIR {swir.shape} shapes don't match")
        
        green = green.astype(np.float32)
        swir = swir.astype(np.float32)
        
        denominator = green + swir
        mndwi = np.zeros_like(green, dtype=np.float32)
        
        valid = denominator > 0
        mndwi[valid] = (green[valid] - swir[valid]) / denominator[valid]
        mndwi[~valid] = -1.0
        
        return np.clip(mndwi, -1, 1)
    
    def calculate_ndvi(self, nir: np.ndarray, red: np.ndarray) -> np.ndarray:
        """
        Calculate Normalized Difference Vegetation Index.
        
        Formula: NDVI = (NIR - Red) / (NIR + Red)
        
        Values range from -1 to 1:
        - > 0.3 indicates healthy vegetation
        - 0 to 0.3 indicates sparse vegetation
        - < 0 indicates non-vegetation
        
        Args:
            nir: Near-Infrared band (2D array)
            red: Red band (2D array)
            
        Returns:
            NDVI array (2D, float32)
        """
        if nir.shape != red.shape:
            raise ValueError(f"NIR {nir.shape} and Red {red.shape} shapes don't match")
        
        nir = nir.astype(np.float32)
        red = red.astype(np.float32)
        
        denominator = nir + red
        ndvi = np.zeros_like(nir, dtype=np.float32)
        
        valid = denominator > 0
        ndvi[valid] = (nir[valid] - red[valid]) / denominator[valid]
        ndvi[~valid] = -1.0
        
        self.last_ndvi = ndvi
        
        return np.clip(ndvi, -1, 1)
    
    def apply_threshold(self, index: np.ndarray, threshold: float = 0.2) -> np.ndarray:
        """
        Apply threshold to index to create binary mask.
        
        Args:
            index: Index array (NDWI, NDVI, etc.)
            threshold: Threshold value
            
        Returns:
            Binary mask (True where index > threshold)
        """
        return index > threshold
    
    def get_water_mask(self, ndwi: np.ndarray, threshold: float = 0.2) -> np.ndarray:
        """
        Get binary water mask from NDWI.
        
        Args:
            ndwi: NDWI array
            threshold: NDWI threshold for water detection
            
        Returns:
            Binary mask (1 for water, 0 for non-water)
        """
        return self.apply_threshold(ndwi, threshold).astype(np.uint8)
    
    def calculate_ndwi_from_rgb(self, 
                               red: np.ndarray, 
                               green: np.ndarray, 
                               blue: np.ndarray) -> np.ndarray:
        """
        Estimate NDWI from RGB bands when NIR is unavailable.
        
        This is a simplified approximation using RGB only.
        Not as accurate as true NIR but useful for testing.
        
        Args:
            red: Red band
            green: Green band
            blue: Blue band
            
        Returns:
            Estimated NDWI
        """
        # Simple approximation: use green and a simulated NIR
        # Simulate NIR as combination of RGB
        nir_sim = (0.4 * red + 0.3 * green + 0.3 * blue)
        
        # Normalize
        nir_sim = nir_sim / (nir_sim.max() + 1e-6)
        
        return self.calculate_ndwi(green, nir_sim)
    
    def analyze_ndwi_stats(self, ndwi: np.ndarray) -> Dict[str, Any]:
        """
        Analyze NDWI statistics.
        
        Args:
            ndwi: NDWI array
            
        Returns:
            Dictionary with statistics
        """
        # Remove NaN values
        valid = ~np.isnan(ndwi)
        ndwi_valid = ndwi[valid]
        
        if len(ndwi_valid) == 0:
            return {
                'min': None,
                'max': None,
                'mean': None,
                'std': None,
                'water_pixels': 0,
                'total_pixels': ndwi.size,
                'water_percentage': 0,
                'percentiles': {}
            }
        
        stats = {
            'min': float(np.min(ndwi_valid)),
            'max': float(np.max(ndwi_valid)),
            'mean': float(np.mean(ndwi_valid)),
            'std': float(np.std(ndwi_valid)),
            'water_pixels': int(np.sum(ndwi_valid > 0.2)),
            'total_pixels': int(ndwi.size),
            'water_percentage': float(np.sum(ndwi_valid > 0.2) / len(ndwi_valid) * 100),
            'percentiles': {
                '25%': float(np.percentile(ndwi_valid, 25)),
                '50%': float(np.percentile(ndwi_valid, 50)),
                '75%': float(np.percentile(ndwi_valid, 75)),
                '90%': float(np.percentile(ndwi_valid, 90))
            }
        }
        
        return stats