"""
Raster loader module for satellite imagery.

Handles loading of various image formats including GeoTIFF, JPEG, PNG, TIFF.
Supports multispectral and RGB imagery.
"""

import os
import numpy as np
from typing import Tuple, Optional, Dict, Any, List
from pathlib import Path
import logging
from PIL import Image
import rasterio
from rasterio.warp import reproject, Resampling
from rasterio.transform import from_origin
from rasterio.crs import CRS

logger = logging.getLogger(__name__)


class RasterLoader:
    """
    Load and validate satellite imagery from various formats.
    
    Supports:
    - GeoTIFF (with metadata)
    - JPEG, PNG, TIFF (RGB)
    - Multispectral imagery
    """
    
    SUPPORTED_FORMATS = ['.tif', '.tiff', '.jpg', '.jpeg', '.png', '.geotiff']
    
    def __init__(self, max_pixels: int = 4096 * 4096):
        """
        Initialize the raster loader.
        
        Args:
            max_pixels: Maximum number of pixels to load (resize if exceeded)
        """
        self.max_pixels = max_pixels
        self.metadata = {}
    
    def load_image(self, image_path: str) -> Dict[str, Any]:
        """
        Load satellite image from file path.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dictionary containing:
                - 'data': numpy array (height, width, bands)
                - 'metadata': dict with geospatial metadata
                - 'bands': list of band names
                - 'profile': rasterio profile if GeoTIFF
                
        Raises:
            FileNotFoundError: If image file doesn't exist
            ValueError: If image format is not supported
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        # Check file extension
        ext = Path(image_path).suffix.lower()
        if ext not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format: {ext}. Supported: {self.SUPPORTED_FORMATS}")
        
        try:
            # Try loading as GeoTIFF with rasterio
            if ext in ['.tif', '.tiff', '.geotiff']:
                return self._load_geotiff(image_path)
            else:
                # Load as RGB image with PIL
                return self._load_rgb(image_path)
        except Exception as e:
            logger.error(f"Error loading image {image_path}: {str(e)}")
            raise
    
    def _load_geotiff(self, image_path: str) -> Dict[str, Any]:
        """
        Load GeoTIFF image with geospatial metadata.
        """
        with rasterio.open(image_path) as src:
            # Read all bands
            data = src.read()
            
            # Ensure 3D array (bands, height, width)
            if len(data.shape) == 2:
                data = data[np.newaxis, :, :]
            
            # Get band descriptions if available
            bands = [src.descriptions[i] if src.descriptions[i] else f"band_{i+1}" 
                    for i in range(data.shape[0])]
            
            # Store metadata
            metadata = {
                'width': src.width,
                'height': src.height,
                'count': src.count,
                'crs': src.crs.to_string() if src.crs else None,
                'transform': src.transform,
                'bounds': src.bounds,
                'nodata': src.nodata,
                'dtype': str(data.dtype)
            }
            
            # Convert to float for processing
            data = data.astype(np.float32)
            
            # Handle nodata values
            if src.nodata is not None:
                data[data == src.nodata] = np.nan
            
            return {
                'data': data,
                'metadata': metadata,
                'bands': bands,
                'profile': src.profile.copy(),
                'crs': src.crs
            }
    
    def _load_rgb(self, image_path: str) -> Dict[str, Any]:
        """
        Load RGB image as 3-band array.
        """
        # Open image with PIL
        img = Image.open(image_path)
        
        # Convert to RGB if necessary
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Convert to numpy array
        data = np.array(img, dtype=np.float32)
        
        # Transpose to (bands, height, width) format
        if len(data.shape) == 3:
            data = np.transpose(data, (2, 0, 1))
        else:
            # Grayscale - duplicate to 3 bands
            data = np.stack([data, data, data], axis=0)
        
        # Store metadata
        metadata = {
            'width': img.width,
            'height': img.height,
            'count': data.shape[0],
            'crs': None,
            'transform': None,
            'bounds': None,
            'nodata': None,
            'dtype': str(data.dtype)
        }
        
        # Resize if too large
        if data.shape[1] * data.shape[2] > self.max_pixels:
            logger.warning(f"Image too large ({data.shape[1]}x{data.shape[2]}), resizing")
            data = self._resize_array(data, target_pixels=self.max_pixels)
            metadata['width'] = data.shape[2]
            metadata['height'] = data.shape[1]
        
        return {
            'data': data,
            'metadata': metadata,
            'bands': ['red', 'green', 'blue'],
            'profile': None,
            'crs': None
        }
    
    def _resize_array(self, data: np.ndarray, target_pixels: int) -> np.ndarray:
        """
        Resize array to reduce pixel count.
        
        Args:
            data: Input array (bands, height, width)
            target_pixels: Maximum number of pixels
            
        Returns:
            Resized array
        """
        import cv2
        
        height, width = data.shape[1], data.shape[2]
        current_pixels = height * width
        
        if current_pixels <= target_pixels:
            return data
        
        # Calculate scaling factor
        scale = np.sqrt(target_pixels / current_pixels)
        new_height = int(height * scale)
        new_width = int(width * scale)
        
        # Resize each band
        resized = []
        for band in data:
            resized_band = cv2.resize(
                band, 
                (new_width, new_height), 
                interpolation=cv2.INTER_AREA
            )
            resized.append(resized_band)
        
        return np.stack(resized, axis=0)
    
    def get_band(self, image_data: Dict[str, Any], band_name: str) -> np.ndarray:
        """
        Extract a specific band by name or index.
        
        Args:
            image_data: Dictionary from load_image()
            band_name: Band name or index (e.g., 'green', 'nir', 0)
            
        Returns:
            2D numpy array for the requested band
        """
        data = image_data['data']
        bands = image_data.get('bands', [])
        
        if isinstance(band_name, int):
            if band_name < 0 or band_name >= data.shape[0]:
                raise ValueError(f"Band index {band_name} out of range")
            return data[band_name]
        
        # Try to find band by name
        if band_name.lower() in [b.lower() for b in bands]:
            idx = [b.lower() for b in bands].index(band_name.lower())
            return data[idx]
        
        # Try common band naming conventions
        band_mapping = {
            'green': ['green', 'g', 'band_2', 'band2', 'b02'],
            'nir': ['nir', 'near_infrared', 'band_4', 'band4', 'b08'],
            'red': ['red', 'r', 'band_1', 'band1', 'b04'],
            'blue': ['blue', 'b', 'band_0', 'band0', 'b02']
        }
        
        for key, alternatives in band_mapping.items():
            if band_name.lower() in alternatives:
                for alt in alternatives:
                    if alt in [b.lower() for b in bands]:
                        idx = [b.lower() for b in bands].index(alt)
                        return data[idx]
        
        # If band not found, try to infer from position
        if len(bands) == 3 and band_name.lower() == 'green':
            # RGB order: red, green, blue
            return data[1]
        elif len(bands) == 3 and band_name.lower() == 'nir':
            # Try to simulate NIR from RGB
            logger.warning("No NIR band available, simulating from RGB")
            return self._simulate_nir(data[0], data[1], data[2])
        
        raise ValueError(f"Band '{band_name}' not found. Available bands: {bands}")
    
    def _simulate_nir(self, red: np.ndarray, green: np.ndarray, blue: np.ndarray) -> np.ndarray:
        """
        Simulate NIR band from RGB channels for testing purposes.
        
        This is a simplified approximation for demonstration.
        """
        # Simulate NIR as a combination of channels
        # In reality, this would use a more sophisticated approach
        nir = (0.5 * green + 0.3 * red + 0.2 * blue)
        
        # Normalize to similar range as other bands
        nir = np.clip(nir, 0, 255)
        
        return nir
    
    def get_geotransform(self, image_data: Dict[str, Any]) -> Optional[Tuple[float, float, float]]:
        """
        Extract geotransform from image data.
        
        Returns:
            Tuple of (x_resolution, y_resolution, pixel_area_km2)
            or None if no geospatial data available
        """
        if image_data.get('crs') is not None:
            # GeoTIFF with geospatial info
            transform = image_data['metadata'].get('transform')
            if transform:
                # Calculate pixel resolution
                x_res = abs(transform.a)
                y_res = abs(transform.e)
                
                # Calculate pixel area in km²
                pixel_area_km2 = (x_res * y_res) / 1e6  # Convert m² to km²
                
                return (x_res, y_res, pixel_area_km2)
        
        # Try to get from metadata
        if 'metadata' in image_data:
            meta = image_data['metadata']
            if 'resolution' in meta:
                res = meta['resolution']
                x_res = res
                y_res = res
                pixel_area_km2 = (res * res) / 1e6
                return (x_res, y_res, pixel_area_km2)
        
        # Default resolution if not available
        logger.warning("No geospatial metadata found, using default resolution")
        return (10.0, 10.0, 0.0001)  # 10m resolution, 0.0001 km² per pixel