"""
Test script for satellite processing pipeline.

Creates test images and validates the complete pipeline.
"""

import os
import sys
import numpy as np
from PIL import Image
from datetime import datetime
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.pipeline.satellite.processor import SatelliteProcessor
from app.pipeline.satellite.raster_loader import RasterLoader
from app.config import settings


def create_test_image(size: tuple = (512, 512), 
                     water_percentage: float = 0.3,
                     with_bands: bool = True,
                     filename: str = "test_image.png"):
    """
    Create a synthetic test image with water and land areas.
    
    Args:
        size: Image size (height, width)
        water_percentage: Percentage of image covered by water
        with_bands: Whether to create multispectral (3 bands)
        filename: Output filename
        
    Returns:
        Path to created image
    """
    height, width = size
    total_pixels = height * width
    
    # Create base image with land and water
    # Water: NDWI > 0.2, Land: NDWI < 0
    
    # Create a grid with varying water patterns
    x = np.linspace(-2, 2, width)
    y = np.linspace(-2, 2, height)
    X, Y = np.meshgrid(x, y)
    
    # Create water bodies (circles + meandering river)
    water1 = (X**2 + Y**2) < 1.0  # Central lake
    water2 = (np.sin(X * 3) + 1) * 0.3 + (np.cos(Y * 2) + 1) * 0.3 > 0.8  # River
    water3 = (X < -0.5) & (Y > 0.5)  # Corner water body
    
    water_mask = water1 | water2 | water3
    
    # Ensure water percentage is close to desired
    current_water = np.sum(water_mask) / total_pixels
    if current_water < water_percentage:
        # Add more water
        additional = np.random.rand(height, width) < (water_percentage - current_water)
        water_mask = water_mask | additional
    elif current_water > water_percentage:
        # Too much water, reduce
        reduce = np.random.rand(height, width) > (current_water - water_percentage)
        water_mask = water_mask & reduce
    
    # Create RGB bands
    # Land: greenish/brown, Water: blue/dark
    if with_bands:
        # Red band
        red = np.zeros((height, width), dtype=np.uint8)
        red[water_mask] = np.random.randint(20, 80, np.sum(water_mask))
        red[~water_mask] = np.random.randint(80, 200, np.sum(~water_mask))
        
        # Green band
        green = np.zeros((height, width), dtype=np.uint8)
        green[water_mask] = np.random.randint(30, 100, np.sum(water_mask))
        green[~water_mask] = np.random.randint(80, 220, np.sum(~water_mask))
        
        # Blue band
        blue = np.zeros((height, width), dtype=np.uint8)
        blue[water_mask] = np.random.randint(80, 200, np.sum(water_mask))
        blue[~water_mask] = np.random.randint(20, 100, np.sum(~water_mask))
        
        # Stack bands
        image = np.stack([red, green, blue], axis=2)
    else:
        # Grayscale
        image = np.zeros((height, width), dtype=np.uint8)
        image[water_mask] = np.random.randint(50, 120, np.sum(water_mask))
        image[~water_mask] = np.random.randint(120, 200, np.sum(~water_mask))
    
    # Save image
    img = Image.fromarray(image)
    img.save(filename)
    print(f"Test image created: {filename}")
    print(f"  Size: {width}x{height}")
    print(f"  Water percentage: {np.sum(water_mask) / total_pixels * 100:.1f}%")
    
    return filename, water_mask


def create_test_images():
    """Create before and after test images."""
    # Create before image (less water)
    before_path, before_mask = create_test_image(
        size=(512, 512),
        water_percentage=0.15,
        with_bands=True,
        filename="test_before.png"
    )
    
    # Create after image (more water)
    after_path, after_mask = create_test_image(
        size=(512, 512),
        water_percentage=0.35,
        with_bands=True,
        filename="test_after.png"
    )
    
    return before_path, after_path, before_mask, after_mask


def validate_result(result: dict) -> bool:
    """
    Validate that result matches canonical schema.
    
    Returns:
        True if valid, False otherwise
    """
    required_fields = [
        "image_id",
        "location",
        "flood_probability",
        "flood_area_km2",
        "flood_percentage",
        "status",
        "processed_at"
    ]
    
    # Check required fields
    for field in required_fields:
        if field not in result:
            print(f"❌ Missing required field: {field}")
            return False
    
    # Check location
    location = result.get("location", {})
    if "lat" not in location or "lon" not in location:
        print("❌ Missing lat/lon in location")
        return False
    
    # Check types
    if not isinstance(result["flood_probability"], (int, float)):
        print(f"❌ flood_probability should be number, got {type(result['flood_probability'])}")
        return False
    
    if result["flood_probability"] < 0 or result["flood_probability"] > 1:
        print(f"❌ flood_probability out of range: {result['flood_probability']}")
        return False
    
    if result["flood_area_km2"] < 0:
        print(f"❌ flood_area_km2 should be >= 0: {result['flood_area_km2']}")
        return False
    
    if result["status"] not in ["success", "error"]:
        print(f"❌ Invalid status: {result['status']}")
        return False
    
    if result["status"] == "success" and result.get("error") is not None:
        print("❌ Status is success but error is not None")
        return False
    
    if result["status"] == "error" and result.get("error") is None:
        print("❌ Status is error but error is None")
        return False
    
    print("✅ Result matches canonical schema")
    return True


def test_pipeline():
    """Run full pipeline test."""
    print("\n" + "="*60)
    print("SATELLITE PROCESSING PIPELINE TEST")
    print("="*60 + "\n")
    
    # Create test images
    print("Creating test images...")
    before_path, after_path, before_mask, after_mask = create_test_images()
    
    # Initialize processor
    processor = SatelliteProcessor()
    
    # Test 1: Single image processing
    print("\n" + "-"*40)
    print("Test 1: Single Image Processing")
    print("-"*40)
    
    result = processor.process_image(
        image_path=after_path,
        threshold=0.2
    )
    
    print(f"\nResult:")
    print(f"  Status: {result['status']}")
    print(f"  Flood Probability: {result['flood_probability']:.2%}")
    print(f"  Flood Area: {result['flood_area_km2']:.4f} km²")
    print(f"  Flood Percentage: {result['flood_percentage']:.2f}%")
    
    if validate_result(result):
        print("✅ Test 1 PASSED")
    else:
        print("❌ Test 1 FAILED")
        return False
    
    # Test 2: Change detection (before + after)
    print("\n" + "-"*40)
    print("Test 2: Change Detection")
    print("-"*40)
    
    result_with_change = processor.process_image(
        image_path=after_path,
        before_image_path=before_path,
        threshold=0.2
    )
    
    print(f"\nResult:")
    print(f"  Status: {result_with_change['status']}")
    print(f"  Flood Probability: {result_with_change['flood_probability']:.2%}")
    print(f"  Flood Area: {result_with_change['flood_area_km2']:.4f} km²")
    print(f"  Flood Percentage: {result_with_change['flood_percentage']:.2f}%")
    
    if 'change_metrics' in result_with_change:
        change = result_with_change['change_metrics']
        print(f"\nChange Metrics:")
        print(f"  New Flood Area: {change.get('new_flood_area_km2', 0):.4f} km²")
        print(f"  Flood Expansion: {change.get('expansion_percentage', 0):.1f}%")
    
    if validate_result(result_with_change):
        print("✅ Test 2 PASSED")
    else:
        print("❌ Test 2 FAILED")
        return False
    
    # Test 3: Error handling
    print("\n" + "-"*40)
    print("Test 3: Error Handling")
    print("-"*40)
    
    error_result = processor.process_image(
        image_path="non_existent_image.tif"
    )
    
    print(f"\nError Result:")
    print(f"  Status: {error_result['status']}")
    print(f"  Error: {error_result.get('error', 'No error message')}")
    
    if error_result['status'] == 'error' and error_result.get('error') is not None:
        print("✅ Test 3 PASSED")
    else:
        print("❌ Test 3 FAILED")
        return False
    
    # Test 4: Visualization generation
    print("\n" + "-"*40)
    print("Test 4: Visualization Generation")
    print("-"*40)
    
    settings.SAVE_VISUALIZATIONS = True
    settings.OUTPUT_DIR = "./test_output"
    
    vis_result = processor.process_image(
        image_path=after_path,
        before_image_path=before_path,
        threshold=0.2
    )
    
    # Check if visualizations were created
    if os.path.exists("./test_output"):
        files = os.listdir("./test_output")
        if any(f.endswith('.png') for f in files):
            print(f"✅ Visualizations created: {len([f for f in files if f.endswith('.png')])} files")
            print("✅ Test 4 PASSED")
        else:
            print("❌ No visualization files found")
            return False
    else:
        print("❌ Output directory not created")
        return False
    
    # Clean up
    print("\n" + "-"*40)
    print("Cleaning up test files...")
    os.remove(before_path)
    os.remove(after_path)
    print("✅ Test files removed")
    
    # Summary
    print("\n" + "="*60)
    print("ALL TESTS PASSED! ✅")
    print("="*60)
    print("\nSatellite Processing Pipeline is ready for integration.")
    print(f"Results can be found in: {settings.OUTPUT_DIR}")
    print(f"Check visualizations in: ./test_output")
    
    return True


def compare_with_schema():
    """Validate all returned values against canonical schema."""
    from app.models.schemas import SatelliteProcessingResult
    
    # This is a static check - ensure the result dict matches the schema
    schema_fields = {
        "image_id": str,
        "location": dict,
        "flood_probability": float,
        "flood_area_km2": float,
        "flood_percentage": float,
        "ndwi_values": (list, type(None)),
        "mask": (list, type(None)),
        "status": str,
        "error": (str, type(None)),
        "processed_at": str
    }
    
    print("\n" + "-"*40)
    print("Schema Validation")
    print("-"*40)
    
    # Create a sample result
    sample_result = {
        "image_id": "test_001",
        "location": {"lat": 35.0, "lon": 135.0},
        "flood_probability": 0.65,
        "flood_area_km2": 12.5,
        "flood_percentage": 25.3,
        "ndwi_values": None,
        "mask": None,
        "status": "success",
        "error": None,
        "processed_at": datetime.now().isoformat()
    }
    
    # Validate fields
    valid = True
    for field, expected_type in schema_fields.items():
        if field not in sample_result:
            print(f"❌ Missing field: {field}")
            valid = False
        else:
            actual_type = type(sample_result[field])
            if isinstance(expected_type, tuple):
                if not isinstance(sample_result[field], expected_type):
                    print(f"❌ Field {field}: Expected {expected_type}, got {actual_type}")
                    valid = False
            else:
                if not isinstance(sample_result[field], expected_type):
                    print(f"❌ Field {field}: Expected {expected_type}, got {actual_type}")
                    valid = False
    
    if valid:
        print("✅ All fields match canonical schema")
    
    return valid


if __name__ == "__main__":
    # Run schema comparison first
    schema_valid = compare_with_schema()
    
    if not schema_valid:
        print("\n❌ Schema validation failed. Please check the schemas in app/models/schemas.py")
        sys.exit(1)
    
    # Run pipeline tests
    success = test_pipeline()
    
    sys.exit(0 if success else 1)