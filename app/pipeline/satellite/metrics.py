"""
Metrics calculation module.

Calculates flood metrics including area, percentage, and probability.
"""

import numpy as np
from typing import Dict, Any, Tuple, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class MetricsCalculator:
    """
    Calculate flood metrics from processed data.
    
    Metrics:
    - Flood percentage
    - Flood area in km²
    - Flood probability
    - Pixel statistics
    """
    
    def __init__(self):
        """Initialize metrics calculator."""
        self.last_metrics = {}
    
    def calculate_metrics(self, 
                         flood_mask: np.ndarray,
                         ndwi: np.ndarray,
                         pixel_area_km2: float = 0.0001,
                         total_area_km2: Optional[float] = None) -> Dict[str, Any]:
        """
        Calculate comprehensive flood metrics.
        
        Args:
            flood_mask: Binary flood mask (2D)
            ndwi: NDWI array (2D)
            pixel_area_km2: Area of each pixel in km²
            total_area_km2: Total area of image in km² (optional)
            
        Returns:
            Dictionary with calculated metrics
        """
        # Basic pixel counts
        total_pixels = flood_mask.size
        flood_pixels = np.sum(flood_mask)
        
        # Area calculations
        flood_area_km2 = flood_pixels * pixel_area_km2
        
        # Calculate total area if not provided
        if total_area_km2 is None:
            total_area_km2 = total_pixels * pixel_area_km2
        
        # Calculate percentages
        flood_percentage = (flood_pixels / total_pixels) * 100 if total_pixels > 0 else 0
        
        # Flood probability (average NDWI in flood areas)
        flood_probability = 0.5  # Default
        if flood_pixels > 0:
            flood_ndwi = ndwi[flood_mask == 1]
            if len(flood_ndwi) > 0:
                # Probability based on NDWI values (0.2-1.0 mapped to 0.5-1.0)
                avg_ndwi = np.mean(flood_ndwi)
                flood_probability = 0.5 + 0.5 * (avg_ndwi - 0.2) / 0.8
                flood_probability = np.clip(flood_probability, 0.5, 0.99)
        
        # Calculate additional metrics
        metrics = {
            'flood_pixels': int(flood_pixels),
            'total_pixels': int(total_pixels),
            'flood_area_km2': float(flood_area_km2),
            'total_area_km2': float(total_area_km2),
            'flood_percentage': float(flood_percentage),
            'flood_probability': float(flood_probability),
            'pixel_area_km2': float(pixel_area_km2)
        }
        
        # Add NDWI statistics
        valid_ndwi = ndwi[~np.isnan(ndwi)]
        if len(valid_ndwi) > 0:
            metrics.update({
                'ndwi_min': float(np.min(valid_ndwi)),
                'ndwi_max': float(np.max(valid_ndwi)),
                'ndwi_mean': float(np.mean(valid_ndwi)),
                'ndwi_std': float(np.std(valid_ndwi))
            })
        
        # Add flood region metrics
        flood_regions = self._calculate_flood_regions(flood_mask)
        metrics.update(flood_regions)
        
        self.last_metrics = metrics
        
        return metrics
    
    def _calculate_flood_regions(self, mask: np.ndarray) -> Dict[str, Any]:
        """
        Calculate metrics for individual flood regions.
        """
        from skimage import measure
        
        labeled = measure.label(mask)
        props = measure.regionprops(labeled)
        
        if not props:
            return {
                'num_flood_regions': 0,
                'largest_region_pixels': 0,
                'avg_region_pixels': 0,
                'region_std_pixels': 0
            }
        
        areas = [prop.area for prop in props]
        
        return {
            'num_flood_regions': len(props),
            'largest_region_pixels': int(max(areas)),
            'avg_region_pixels': float(np.mean(areas)),
            'region_std_pixels': float(np.std(areas))
        }
    
    def calculate_change_metrics(self,
                                 mask_before: np.ndarray,
                                 mask_after: np.ndarray,
                                 pixel_area_km2: float = 0.0001) -> Dict[str, Any]:
        """
        Calculate metrics for change detection.
        
        Args:
            mask_before: Flood mask from before image
            mask_after: Flood mask from after image
            pixel_area_km2: Area of each pixel in km²
            
        Returns:
            Dictionary with change metrics
        """
        # Calculate areas
        area_before = np.sum(mask_before) * pixel_area_km2
        area_after = np.sum(mask_after) * pixel_area_km2
        
        # Calculate changes
        new_flood = mask_after & ~mask_before
        new_area = np.sum(new_flood) * pixel_area_km2
        
        persistent = mask_before & mask_after
        persistent_area = np.sum(persistent) * pixel_area_km2
        
        recession = mask_before & ~mask_after
        recession_area = np.sum(recession) * pixel_area_km2
        
        # Calculate percentages
        expansion_percentage = (new_area / area_before * 100) if area_before > 0 else 0
        
        return {
            'area_before_km2': float(area_before),
            'area_after_km2': float(area_after),
            'area_change_km2': float(area_after - area_before),
            'new_flood_area_km2': float(new_area),
            'persistent_flood_area_km2': float(persistent_area),
            'recession_area_km2': float(recession_area),
            'expansion_percentage': float(expansion_percentage),
            'has_flood_expansion': bool(new_area > 0.01),
            'new_flood_regions': int(self._count_regions(new_flood))
        }
    
    def _count_regions(self, mask: np.ndarray) -> int:
        """
        Count connected regions in mask.
        """
        from skimage import measure
        return len(measure.regionprops(measure.label(mask)))
    
    def calculate_probability_map(self,
                                 ndwi: np.ndarray,
                                 flood_mask: np.ndarray) -> np.ndarray:
        """
        Calculate flood probability map.
        
        Args:
            ndwi: NDWI array
            flood_mask: Binary flood mask
            
        Returns:
            Probability map (0-1)
        """
        # Create probability map based on NDWI values
        prob = np.zeros_like(ndwi)
        
        # For flood areas, use NDWI as probability
        prob[flood_mask == 1] = (ndwi[flood_mask == 1] - 0.2) / 0.8
        prob = np.clip(prob, 0, 1)
        
        # For non-flood areas, low probability
        prob[flood_mask == 0] = 0.01
        
        return prob
    
    def calculate_risk_metrics(self,
                              flood_mask: np.ndarray,
                              ndwi: np.ndarray,
                              latitude: float,
                              longitude: float,
                              pixel_area_km2: float = 0.0001) -> Dict[str, Any]:
        """
        Calculate risk metrics for the flooded area.
        
        Args:
            flood_mask: Binary flood mask
            ndwi: NDWI array
            latitude: Center latitude
            longitude: Center longitude
            pixel_area_km2: Area of each pixel
            
        Returns:
            Dictionary with risk metrics
        """
        metrics = self.calculate_metrics(flood_mask, ndwi, pixel_area_km2)
        
        # Determine risk level based on flood probability and area
        risk_levels = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
        probabilities = [0.3, 0.5, 0.7, 0.9]
        
        probability = metrics['flood_probability']
        
        # Determine risk level
        risk_level = 'LOW'
        for i, threshold in enumerate(probabilities):
            if probability >= threshold:
                risk_level = risk_levels[i]
        
        # Determine confidence based on NDWI variance
        ndwi_std = metrics.get('ndwi_std', 0.1)
        confidence = 0.7 + 0.3 * (1 - min(ndwi_std / 0.3, 1))
        
        return {
            'location': {'lat': latitude, 'lon': longitude},
            'flood_probability': metrics['flood_probability'],
            'flood_area_km2': metrics['flood_area_km2'],
            'flood_percentage': metrics['flood_percentage'],
            'risk_level': risk_level,
            'confidence': float(confidence),
            'timestamp': datetime.now().isoformat()
        }