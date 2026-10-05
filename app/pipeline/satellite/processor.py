"""
Main satellite processor module.

Orchestrates the entire satellite processing pipeline.
"""

import os
import numpy as np
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import logging

from app.pipeline.satellite.raster_loader import RasterLoader
from app.pipeline.satellite.preprocessing import Preprocessor
from app.pipeline.satellite.indices import IndexCalculator
from app.pipeline.satellite.flood_detection import FloodDetector
from app.pipeline.satellite.change_detection import ChangeDetector
from app.pipeline.satellite.metrics import MetricsCalculator
from app.pipeline.satellite.visualization import Visualizer
from app.config import settings

logger = logging.getLogger(__name__)


class SatelliteProcessor:
    """
    Main satellite processing orchestrator.
    
    Coordinates all processing steps:
    1. Load image(s)
    2. Preprocess
    3. Calculate NDWI
    4. Detect flood
    5. Change detection (if before image provided)
    6. Calculate metrics
    7. Generate visualizations
    """
    
    def __init__(self):
        """Initialize satellite processor with all components."""
        self.loader = RasterLoader(max_pixels=settings.MAX_IMAGE_PIXELS)
        self.preprocessor = Preprocessor()
        self.index_calculator = IndexCalculator()
        self.flood_detector = FloodDetector(
            min_area_pixels=settings.MIN_FLOOD_AREA_PIXELS
        )
        self.change_detector = ChangeDetector()
        self.metrics_calculator = MetricsCalculator()
        self.visualizer = Visualizer(
            output_dir=settings.OUTPUT_DIR,
            save_plots=settings.SAVE_VISUALIZATIONS
        )
        
        # Store results
        self.last_result = None
        self.last_ndwi = None
        self.last_flood_mask = None
    
    def process_image(self,
                     image_path: str,
                     before_image_path: Optional[str] = None,
                     threshold: Optional[float] = None,
                     location: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """
        Process satellite image for flood detection.
        
        Args:
            image_path: Path to the satellite image
            before_image_path: Optional path to before image
            threshold: NDWI threshold for flood detection
            location: Optional location metadata
            
        Returns:
            Dictionary matching SatelliteProcessingResult schema
        """
        try:
            # Use configured threshold if not provided
            if threshold is None:
                threshold = settings.NDWI_THRESHOLD
            
            start_time = datetime.now()
            
            # Step 1: Load images
            logger.info(f"Loading image: {image_path}")
            image_data = self.loader.load_image(image_path)
            
            # Step 2: Preprocess
            logger.info("Preprocessing image")
            image_data = self.preprocessor.preprocess(image_data)
            
            # Step 3: Extract bands and calculate NDWI
            logger.info("Calculating NDWI")
            green = self.loader.get_band(image_data, 'green')
            nir = self.loader.get_band(image_data, 'nir')
            ndwi = self.index_calculator.calculate_ndwi(green, nir)
            
            # Step 4: Detect flood
            logger.info(f"Detecting flood with threshold: {threshold}")
            flood_mask = self.flood_detector.detect_flood(ndwi, threshold)
            
            # Step 5: Calculate metrics
            logger.info("Calculating metrics")
            pixel_area_km2 = self.loader.get_geotransform(image_data)[2]
            metrics = self.metrics_calculator.calculate_metrics(
                flood_mask, ndwi, pixel_area_km2
            )
            has_georeferenced_area = image_data.get('crs') is not None and bool(image_data.get('metadata', {}).get('transform'))
            
            # Step 6: Change detection (if before image provided)
            before_ndwi = None
            change_map = None
            before_metrics = None
            
            if before_image_path:
                logger.info(f"Processing before image: {before_image_path}")
                before_image = self.loader.load_image(before_image_path)
                before_image = self.preprocessor.preprocess(before_image)
                
                before_green = self.loader.get_band(before_image, 'green')
                before_nir = self.loader.get_band(before_image, 'nir')
                before_ndwi = self.index_calculator.calculate_ndwi(before_green, before_nir)
                before_flood_mask = self.flood_detector.detect_flood(before_ndwi, threshold)
                before_metrics = self.metrics_calculator.calculate_metrics(
                    before_flood_mask, before_ndwi, pixel_area_km2
                )
                
                # Detect changes
                change_results = self.change_detector.detect_changes(
                    before_ndwi, ndwi, threshold=0.05
                )
                change_map = change_results['change_map']
            
            # Step 7: Generate visualizations
            logger.info("Generating visualizations")
            visualization_data = self.visualizer.create_visualization_package(
                image_data, ndwi, flood_mask, before_ndwi, change_map
            )
            
            # Step 8: Prepare result
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Get location
            if location is None:
                location = {'lat': 0.0, 'lon': 0.0}
                if image_data.get('metadata', {}).get('bounds'):
                    bounds = image_data['metadata']['bounds']
                    location = {
                        'lat': (bounds[1] + bounds[3]) / 2,
                        'lon': (bounds[0] + bounds[2]) / 2
                    }
            
            # Prepare NDWI values and mask for schema
            ndwi_values = ndwi.tolist() if ndwi.size < 10000 else None
            mask = flood_mask.tolist() if flood_mask.size < 10000 else None
            
            # Create result matching canonical schema
            result = {
                "image_id": os.path.basename(image_path).split('.')[0],
                "location": location,
                "flood_probability": metrics.get('flood_probability', 0.0),
                "flood_area_km2": metrics.get('flood_area_km2') if has_georeferenced_area else None,
                "total_area_km2": metrics.get('total_area_km2') if has_georeferenced_area else None,
                "area_is_georeferenced": has_georeferenced_area,
                "flood_percentage": metrics.get('flood_percentage', 0.0),
                "ndwi_values": ndwi_values,
                "mask": mask,
                "status": "success",
                "error": None,
                "processed_at": datetime.now().isoformat()
            }
            
            # Add change detection metrics if available
            if before_metrics is not None:
                change_metrics = self.metrics_calculator.calculate_change_metrics(
                    before_flood_mask, flood_mask, pixel_area_km2
                )
                result['change_metrics'] = change_metrics
            
            # Store for later access
            self.last_result = result
            self.last_ndwi = ndwi
            self.last_flood_mask = flood_mask
            
            logger.info(f"Processing completed in {processing_time:.2f} seconds")
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing image: {str(e)}", exc_info=True)
            
            # Return error result matching schema
            return {
                "image_id": os.path.basename(image_path).split('.')[0] if image_path else "unknown",
                "location": location or {'lat': 0.0, 'lon': 0.0},
                "flood_probability": 0.0,
                "flood_area_km2": 0.0,
                "flood_percentage": 0.0,
                "ndwi_values": None,
                "mask": None,
                "status": "error",
                "error": str(e),
                "processed_at": datetime.now().isoformat()
            }
    
    def process_rgb_image(self,
                         image_path: str,
                         threshold: Optional[float] = None,
                         location: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """
        Process RGB image using color-based flood detection.
        
        Fallback for images without NIR band.
        
        Args:
            image_path: Path to RGB image
            threshold: Detection threshold
            location: Optional location metadata
            
        Returns:
            Result matching SatelliteProcessingResult schema
        """
        try:
            # Load and preprocess
            image_data = self.loader.load_image(image_path)
            image_data = self.preprocessor.preprocess(image_data)
            
            # Get RGB
            red = self.loader.get_band(image_data, 'red')
            green = self.loader.get_band(image_data, 'green')
            blue = self.loader.get_band(image_data, 'blue')
            
            # Calculate approximate NDWI from RGB
            ndwi = self.index_calculator.calculate_ndwi_from_rgb(red, green, blue)
            
            # Detect flood
            if threshold is None:
                threshold = settings.NDWI_THRESHOLD
            flood_mask = self.flood_detector.detect_flood(ndwi, threshold)
            
            # Calculate metrics
            pixel_area_km2 = self.loader.get_geotransform(image_data)[2]
            metrics = self.metrics_calculator.calculate_metrics(
                flood_mask, ndwi, pixel_area_km2
            )
            has_georeferenced_area = image_data.get('crs') is not None and bool(image_data.get('metadata', {}).get('transform'))
            
            # Get location
            if location is None:
                location = {'lat': 0.0, 'lon': 0.0}
            
            # Prepare result
            result = {
                "image_id": os.path.basename(image_path).split('.')[0],
                "location": location,
                "flood_probability": metrics.get('flood_probability', 0.0),
                "flood_area_km2": metrics.get('flood_area_km2') if has_georeferenced_area else None,
                "total_area_km2": metrics.get('total_area_km2') if has_georeferenced_area else None,
                "area_is_georeferenced": has_georeferenced_area,
                "flood_percentage": metrics.get('flood_percentage', 0.0),
                "ndwi_values": ndwi.tolist() if ndwi.size < 10000 else None,
                "mask": flood_mask.tolist() if flood_mask.size < 10000 else None,
                "status": "success",
                "error": None,
                "processed_at": datetime.now().isoformat()
            }
            
            self.last_result = result
            self.last_ndwi = ndwi
            self.last_flood_mask = flood_mask
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing RGB image: {str(e)}", exc_info=True)
            return {
                "image_id": os.path.basename(image_path).split('.')[0] if image_path else "unknown",
                "location": location or {'lat': 0.0, 'lon': 0.0},
                "flood_probability": 0.0,
                "flood_area_km2": 0.0,
                "flood_percentage": 0.0,
                "ndwi_values": None,
                "mask": None,
                "status": "error",
                "error": str(e),
                "processed_at": datetime.now().isoformat()
            }
    
    def get_last_result(self) -> Optional[Dict[str, Any]]:
        """Get the last processing result."""
        return self.last_result
    
    def get_ndwi(self) -> Optional[np.ndarray]:
        """Get the last NDWI array."""
        return self.last_ndwi
    
    def get_flood_mask(self) -> Optional[np.ndarray]:
        """Get the last flood mask."""
        return self.last_flood_mask


# Command line interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Satellite Flood Detection Pipeline")
    parser.add_argument("--image", required=True, help="Path to satellite image")
    parser.add_argument("--before", help="Path to before image for change detection")
    parser.add_argument("--threshold", type=float, default=0.2, help="NDWI threshold")
    parser.add_argument("--output", default="./output", help="Output directory")
    parser.add_argument("--visualize", action="store_true", help="Generate visualizations")
    
    args = parser.parse_args()
    
    # Configure settings
    settings.OUTPUT_DIR = args.output
    settings.SAVE_VISUALIZATIONS = args.visualize
    
    # Process image
    processor = SatelliteProcessor()
    result = processor.process_image(
        image_path=args.image,
        before_image_path=args.before,
        threshold=args.threshold
    )
    
    print("\nSatellite Processing Results")
    print("=" * 40)
    print(f"Image ID: {result['image_id']}")
    print(f"Status: {result['status']}")
    if result['status'] == 'success':
        print(f"Flood Probability: {result['flood_probability']:.2%}")
        print(f"Flood Area: {result['flood_area_km2']:.2f} km²")
        print(f"Flood Percentage: {result['flood_percentage']:.2f}%")
        print(f"Processed At: {result['processed_at']}")
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")
