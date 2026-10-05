"""
Change detection module.

Detects changes between before and after satellite images.
"""

import numpy as np
from typing import Dict, Any, Tuple, Optional
import logging
from scipy import ndimage

logger = logging.getLogger(__name__)


class ChangeDetector:
    """
    Detect changes between before and after satellite images.
    
    Compares NDWI of before and after images to identify
    areas where water has increased (potential flooding).
    """
    
    def __init__(self, min_change_pixels: int = 50):
        """
        Initialize change detector.
        
        Args:
            min_change_pixels: Minimum pixels for change detection
        """
        self.min_change_pixels = min_change_pixels
        self.last_change_map = None
        self.last_stats = None
    
    def detect_changes(self, 
                      ndwi_before: np.ndarray, 
                      ndwi_after: np.ndarray,
                      threshold: float = 0.1) -> Dict[str, np.ndarray]:
        """
        Detect changes between before and after NDWI.
        
        Args:
            ndwi_before: NDWI from before image
            ndwi_after: NDWI from after image
            threshold: Change detection threshold
            
        Returns:
            Dictionary containing:
                - 'change_map': Binary change map
                - 'increase_map': Areas where water increased
                - 'decrease_map': Areas where water decreased
                - 'difference': Raw difference
        """
        if ndwi_before.shape != ndwi_after.shape:
            raise ValueError("Before and after NDWI shapes don't match")
        
        # Calculate difference
        diff = ndwi_after - ndwi_before
        
        # Identify significant changes
        increase = diff > threshold
        decrease = diff < -threshold
        
        # Clean change maps
        increase = self._clean_change_map(increase)
        decrease = self._clean_change_map(decrease)
        
        # Combined change
        change = increase | decrease
        
        # Store results
        self.last_change_map = change
        self.last_stats = self._calculate_stats(ndwi_before, ndwi_after, diff)
        
        return {
            'change_map': change.astype(np.uint8),
            'increase_map': increase.astype(np.uint8),
            'decrease_map': decrease.astype(np.uint8),
            'difference': diff,
            'stats': self.last_stats
        }
    
    def _clean_change_map(self, change_map: np.ndarray) -> np.ndarray:
        """
        Clean change map with morphological operations.
        """
        from skimage import morphology
        
        # Convert to boolean
        bool_map = change_map.astype(bool)
        
        # Remove small objects
        bool_map = morphology.remove_small_objects(
            bool_map, 
            min_size=self.min_change_pixels
        )
        
        # Apply binary closing
        struct_elem = morphology.disk(1)
        bool_map = morphology.binary_closing(bool_map, struct_elem)
        
        return bool_map.astype(np.uint8)
    
    def _calculate_stats(self, 
                        ndwi_before: np.ndarray, 
                        ndwi_after: np.ndarray,
                        diff: np.ndarray) -> Dict[str, Any]:
        """
        Calculate change statistics.
        """
        # Remove NaN
        valid = ~np.isnan(diff)
        diff_valid = diff[valid]
        
        if len(diff_valid) == 0:
            return {
                'mean_change': 0,
                'max_increase': 0,
                'max_decrease': 0,
                'total_change_pixels': 0,
                'change_percentage': 0
            }
        
        stats = {
            'mean_change': float(np.mean(diff_valid)),
            'std_change': float(np.std(diff_valid)),
            'max_increase': float(np.max(diff_valid)),
            'max_decrease': float(np.min(diff_valid)),
            'total_change_pixels': int(np.sum(np.abs(diff_valid) > 0.1)),
            'change_percentage': float(np.sum(np.abs(diff_valid) > 0.1) / len(diff_valid) * 100)
        }
        
        return stats
    
    def get_flood_expansion(self, 
                           flood_mask_before: np.ndarray,
                           flood_mask_after: np.ndarray) -> Dict[str, Any]:
        """
        Analyze flood expansion from before to after.
        
        Args:
            flood_mask_before: Flood mask from before image
            flood_mask_after: Flood mask from after image
            
        Returns:
            Dictionary with expansion metrics
        """
        # Calculate areas
        area_before = np.sum(flood_mask_before)
        area_after = np.sum(flood_mask_after)
        
        # Calculate new flooding (after but not before)
        new_flood = flood_mask_after & ~flood_mask_before
        new_area = np.sum(new_flood)
        
        # Calculate persistent flooding (both before and after)
        persistent = flood_mask_before & flood_mask_after
        persistent_area = np.sum(persistent)
        
        # Calculate recession (before but not after)
        recession = flood_mask_before & ~flood_mask_after
        recession_area = np.sum(recession)
        
        return {
            'area_before_pixels': int(area_before),
            'area_after_pixels': int(area_after),
            'new_flood_pixels': int(new_area),
            'persistent_flood_pixels': int(persistent_area),
            'recession_pixels': int(recession_area),
            'expansion_percentage': float(
                new_area / area_before * 100 if area_before > 0 else 0
            ),
            'new_flood_percentage': float(
                new_area / area_after * 100 if area_after > 0 else 0
            )
        }
    
    def detect_water_increase(self, 
                            ndwi_before: np.ndarray,
                            ndwi_after: np.ndarray,
                            threshold: float = 0.05) -> np.ndarray:
        """
        Specifically detect areas where water increased.
        
        Args:
            ndwi_before: NDWI from before
            ndwi_after: NDWI from after
            threshold: Minimum increase threshold
            
        Returns:
            Binary map of water increase areas
        """
        diff = ndwi_after - ndwi_before
        increase = diff > threshold
        
        # Also require that after NDWI is positive (actual water)
        increase = increase & (ndwi_after > 0.1)
        
        return self._clean_change_map(increase)