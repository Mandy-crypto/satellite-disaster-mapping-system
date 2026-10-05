"""
Flood detection module.

Detects flooded areas using NDWI thresholding and morphological operations.
"""

import numpy as np
from typing import Dict, Any, Tuple, Optional
import logging
from scipy import ndimage
from skimage import morphology, measure

logger = logging.getLogger(__name__)


class FloodDetector:
    """
    Detect flooded areas from satellite imagery.
    
    Uses NDWI thresholding with morphological operations to
    identify and clean flood masks.
    """
    
    def __init__(self, min_area_pixels: int = 100):
        """
        Initialize flood detector.
        
        Args:
            min_area_pixels: Minimum area in pixels to consider as flood
        """
        self.min_area_pixels = min_area_pixels
        self.last_mask = None
        self.last_contours = None
    
    def detect_flood(self, ndwi: np.ndarray, threshold: float = 0.2) -> np.ndarray:
        """
        Detect flooded areas from NDWI.
        
        Args:
            ndwi: NDWI array (2D)
            threshold: NDWI threshold for water detection
            
        Returns:
            Binary flood mask (2D, uint8)
        """
        # Initial water mask
        mask = (ndwi > threshold).astype(np.uint8)
        
        # Clean mask with morphological operations
        mask = self._clean_mask(mask)
        
        # Filter by area
        mask = self._filter_by_area(mask)
        
        self.last_mask = mask
        
        logger.info(f"Flood detection completed: {np.sum(mask)} water pixels")
        
        return mask
    
    def detect_flood_from_rgb(self, 
                             image: np.ndarray,
                             threshold: float = 0.2) -> np.ndarray:
        """
        Detect flood from RGB image directly.
        
        Uses color-based water detection as fallback.
        
        Args:
            image: RGB image (height, width, 3)
            threshold: Detection threshold
            
        Returns:
            Binary flood mask
        """
        # Convert to HSV for color-based water detection
        import cv2
        hsv = cv2.cvtColor((image * 255).astype(np.uint8), cv2.COLOR_RGB2HSV)
        hsv = hsv.astype(np.float32) / 255.0
        
        # Water typically has low saturation and specific hue ranges
        hue = hsv[:, :, 0]
        saturation = hsv[:, :, 1]
        
        # Simple water detection: low saturation and specific hue
        mask = (saturation < 0.3) & (hue < 0.6) & (hue > 0.4)
        
        # Clean mask
        mask = self._clean_mask(mask.astype(np.uint8))
        mask = self._filter_by_area(mask)
        
        self.last_mask = mask
        
        return mask
    
    def _clean_mask(self, mask: np.ndarray) -> np.ndarray:
        """
        Apply morphological operations to clean mask.
        
        Operations:
        - Remove small holes
        - Remove isolated pixels
        - Smooth boundaries
        """
        # Convert to boolean
        bool_mask = mask.astype(bool)
        
        # Remove small holes
        bool_mask = morphology.remove_small_holes(bool_mask, 
                                                  area_threshold=50)
        
        # Remove small objects
        bool_mask = morphology.remove_small_objects(bool_mask, 
                                                    min_size=self.min_area_pixels)
        
        # Apply binary closing to fill small gaps
        struct_elem = morphology.disk(2)
        bool_mask = morphology.binary_closing(bool_mask, struct_elem)
        
        # Apply binary opening to remove small noise
        bool_mask = morphology.binary_opening(bool_mask, struct_elem)
        
        return bool_mask.astype(np.uint8)
    
    def _filter_by_area(self, mask: np.ndarray) -> np.ndarray:
        """
        Filter connected components by area.
        
        Removes components smaller than min_area_pixels.
        """
        # Label connected components
        labeled = measure.label(mask)
        
        # Get properties
        props = measure.regionprops(labeled)
        
        # Create filtered mask
        filtered = np.zeros_like(mask)
        
        for prop in props:
            if prop.area >= self.min_area_pixels:
                filtered[labeled == prop.label] = 1
        
        return filtered
    
    def get_flood_contours(self, mask: np.ndarray) -> list:
        """
        Extract contours from flood mask.
        
        Args:
            mask: Binary flood mask
            
        Returns:
            List of contour coordinates
        """
        import cv2
        
        contours, _ = cv2.findContours(
            mask.astype(np.uint8),
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )
        
        self.last_contours = contours
        
        return contours
    
    def get_flood_regions(self, mask: np.ndarray) -> Dict[str, Any]:
        """
        Get detailed information about flood regions.
        
        Args:
            mask: Binary flood mask
            
        Returns:
            Dictionary with region information
        """
        labeled = measure.label(mask)
        props = measure.regionprops(labeled)
        
        regions = []
        for prop in props:
            regions.append({
                'id': prop.label,
                'area_pixels': prop.area,
                'bbox': prop.bbox,
                'centroid': prop.centroid,
                'perimeter': prop.perimeter,
                'eccentricity': prop.eccentricity
            })
        
        return {
            'num_regions': len(regions),
            'total_area_pixels': int(np.sum(mask)),
            'regions': regions
        }
    
    def calculate_probability(self, ndwi: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """
        Calculate flood probability map.
        
        Args:
            ndwi: NDWI array
            mask: Binary flood mask
            
        Returns:
            Probability map (0-1)
        """
        # Use NDWI values within mask as probability
        probability = np.zeros_like(ndwi)
        probability[mask == 1] = (ndwi[mask == 1] - 0.2) / 0.8
        probability = np.clip(probability, 0, 1)
        
        return probability