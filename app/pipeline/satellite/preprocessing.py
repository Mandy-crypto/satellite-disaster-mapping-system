"""
Preprocessing module for satellite imagery.

Handles image normalization, denoising, and preparation for analysis.
"""

import numpy as np
from typing import Dict, Any, Tuple, Optional
import logging
from scipy import ndimage
import cv2

logger = logging.getLogger(__name__)


class Preprocessor:
    """
    Preprocess satellite images for analysis.
    
    Operations:
    - Normalization to 0-1 range
    - Noise reduction
    - Cloud masking (placeholder)
    - Pixel clipping
    """
    
    def __init__(self):
        """Initialize preprocessor with default settings."""
        self.stats = {}
    
    def preprocess(self, image_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply full preprocessing pipeline.
        
        Args:
            image_data: Dictionary from RasterLoader.load_image()
            
        Returns:
            Preprocessed image data with normalized array
        """
        data = image_data['data'].copy()
        
        # Step 1: Normalize
        data = self.normalize(data)
        
        # Step 2: Remove NaN/Inf
        data = self.clean_values(data)
        
        # Step 3: Apply noise reduction
        data = self.denoise(data)
        
        # Step 4: Apply clipping
        data = self.clip_values(data)
        
        # Store preprocessing stats
        self.stats = {
            'min': float(np.nanmin(data)),
            'max': float(np.nanmax(data)),
            'mean': float(np.nanmean(data)),
            'std': float(np.nanstd(data)),
            'nan_count': int(np.isnan(data).sum())
        }
        
        image_data['data'] = data
        image_data['preprocessing_stats'] = self.stats
        
        return image_data
    
    def normalize(self, data: np.ndarray, method: str = 'minmax') -> np.ndarray:
        """
        Normalize image data to 0-1 range.
        
        Args:
            data: Input array
            method: Normalization method ('minmax', 'standard', 'percentile')
            
        Returns:
            Normalized array
        """
        # Handle NaN values
        data = np.nan_to_num(data, nan=0.0)
        
        if method == 'minmax':
            # Min-max normalization
            min_val = np.min(data)
            max_val = np.max(data)
            if max_val > min_val:
                data = (data - min_val) / (max_val - min_val)
            else:
                logger.warning("Data has no variation, skipping normalization")
        
        elif method == 'standard':
            # Standardization (z-score)
            mean = np.mean(data)
            std = np.std(data)
            if std > 0:
                data = (data - mean) / std
                # Clip to 3 standard deviations
                data = np.clip(data, -3, 3)
                # Map to 0-1
                data = (data + 3) / 6
        
        elif method == 'percentile':
            # Percentile-based clipping (robust to outliers)
            p2 = np.percentile(data, 2)
            p98 = np.percentile(data, 98)
            data = np.clip(data, p2, p98)
            if p98 > p2:
                data = (data - p2) / (p98 - p2)
        
        return data
    
    def clean_values(self, data: np.ndarray) -> np.ndarray:
        """
        Clean invalid values from array.
        
        Replaces NaN, Inf with 0 or interpolated values.
        """
        # Replace NaN and Inf with 0
        data = np.nan_to_num(data, nan=0.0, posinf=0.0, neginf=0.0)
        
        # Clip extreme values
        data = np.clip(data, -1000, 1000)
        
        return data
    
    def denoise(self, data: np.ndarray, method: str = 'gaussian') -> np.ndarray:
        """
        Apply noise reduction to image.
        
        Args:
            data: Input array (bands, height, width)
            method: Denoising method ('gaussian', 'median', 'bilateral')
            
        Returns:
            Denoised array
        """
        if method == 'gaussian':
            # Gaussian blur
            sigma = 1.0
            if len(data.shape) == 3:
                result = []
                for band in data:
                    band_smooth = ndimage.gaussian_filter(band, sigma=sigma)
                    result.append(band_smooth)
                return np.stack(result, axis=0)
            else:
                return ndimage.gaussian_filter(data, sigma=sigma)
        
        elif method == 'median':
            # Median filter
            if len(data.shape) == 3:
                result = []
                for band in data:
                    band_smooth = ndimage.median_filter(band, size=3)
                    result.append(band_smooth)
                return np.stack(result, axis=0)
            else:
                return ndimage.median_filter(data, size=3)
        
        elif method == 'bilateral':
            # Bilateral filter (preserves edges)
            if len(data.shape) == 3:
                result = []
                for band in data:
                    band_uint8 = (band * 255).astype(np.uint8)
                    filtered = cv2.bilateralFilter(band_uint8, 9, 75, 75)
                    result.append(filtered.astype(np.float32) / 255.0)
                return np.stack(result, axis=0)
        
        return data
    
    def clip_values(self, data: np.ndarray, min_val: float = 0.0, max_val: float = 1.0) -> np.ndarray:
        """
        Clip values to specified range.
        
        Args:
            data: Input array
            min_val: Minimum value
            max_val: Maximum value
            
        Returns:
            Clipped array
        """
        return np.clip(data, min_val, max_val)
    
    def extract_bands(self, image_data: Dict[str, Any], 
                     bands: Dict[str, str]) -> Dict[str, np.ndarray]:
        """
        Extract specific bands for processing.
        
        Args:
            image_data: Dictionary from RasterLoader
            bands: Dictionary mapping band names to band identifiers
            
        Returns:
            Dictionary with extracted bands as numpy arrays
        """
        extracted = {}
        data = image_data['data']
        band_names = image_data.get('bands', [])
        
        for target_name, source_band in bands.items():
            if isinstance(source_band, int):
                # Index-based extraction
                if source_band < data.shape[0]:
                    extracted[target_name] = data[source_band]
                else:
                    raise ValueError(f"Band index {source_band} out of range")
            
            elif isinstance(source_band, str):
                # Name-based extraction
                if source_band in band_names:
                    idx = band_names.index(source_band)
                    extracted[target_name] = data[idx]
                else:
                    # Try case-insensitive matching
                    matched = False
                    for i, name in enumerate(band_names):
                        if name.lower() == source_band.lower():
                            extracted[target_name] = data[i]
                            matched = True
                            break
                    if not matched:
                        raise ValueError(f"Band '{source_band}' not found")
            
            else:
                raise ValueError(f"Invalid band specification: {source_band}")
        
        return extracted