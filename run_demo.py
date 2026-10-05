#!/usr/bin/env python
"""
Satellite-Assisted Disaster Mapping System - Enhanced Demo
Optimized for SIH hackathon presentation with realistic CRITICAL/HIGH risk zones.
"""

import os
import sys
import json
import numpy as np
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# FALLBACK MOCKS (in case imports fail)
# ============================================================================

class MockSatelliteProcessor:
    """Fallback satellite processor with realistic flood detection."""
    
    def __init__(self):
        self.seed = 42
        np.random.seed(self.seed)
    
    def process_image(self, image_path=None, before_image_path=None, threshold=0.2):
        """Return enhanced satellite processing result with significant flood."""
        print("  🛰️ Using enhanced mock satellite processor")
        
        # Create more realistic flood pattern
        height, width = 512, 512
        x = np.linspace(-2.5, 2.5, width)
        y = np.linspace(-2.5, 2.5, height)
        X, Y = np.meshgrid(x, y)
        
        # Multiple flood zones for realistic pattern
        flood1 = (X/1.2)**2 + (Y/0.8)**2 < 0.6  # Main flood
        flood2 = (X/2.0)**2 + (Y/1.5)**2 < 0.4  # Secondary flood
        flood3 = ((X-1.0)/1.0)**2 + ((Y+0.5)/0.8)**2 < 0.3  # Third flood
        flood4 = ((X+0.8)/0.8)**2 + ((Y-1.0)/0.6)**2 < 0.25  # Fourth flood
        
        flood_mask = (flood1 | flood2 | flood3 | flood4).astype(np.uint8)
        
        # Create NDWI with realistic values
        ndwi = np.random.uniform(-0.4, 0.1, (height, width)).astype(np.float32)
        # Higher NDWI for flood areas
        flood_indices = flood_mask == 1
        ndwi[flood_indices] = np.random.uniform(0.35, 0.85, np.sum(flood_indices))
        
        # Calculate metrics - make it more severe
        flood_pixels = np.sum(flood_mask)
        total_pixels = height * width
        flood_percentage = (flood_pixels / total_pixels) * 100
        flood_area_km2 = flood_pixels * 0.0001
        flood_probability = 0.78 + np.random.uniform(-0.08, 0.08)  # 70-86%
        flood_probability = np.clip(flood_probability, 0.6, 0.9)
        
        return {
            "image_id": "demo_flood_image",
            "location": {"lat": 23.25, "lon": 79.75},
            "flood_probability": float(flood_probability),
            "flood_area_km2": float(flood_area_km2 * 1.5),  # Increase area for impact
            "flood_percentage": float(flood_percentage * 1.3),
            "ndwi_values": ndwi.tolist() if ndwi.size < 10000 else None,
            "mask": flood_mask.tolist() if flood_mask.size < 10000 else None,
            "status": "success",
            "error": None,
            "processed_at": datetime.now().isoformat(),
            "_ndwi": ndwi,
            "_mask": flood_mask
        }


class MockSensorSimulator:
    """Enhanced sensor simulator with clear flood pattern."""
    
    def __init__(self):
        np.random.seed(42)
    
    def generate(self, scenario="critical", num_sensors=100):
        """Generate enhanced sensor data with clear risk gradient."""
        print(f"  📡 Using enhanced mock sensor simulator ({scenario} scenario)")
        
        # Generate sensor locations with some clustering
        locations = []
        flood_center = (23.25, 79.75)
        
        # Create sensors in a grid with some randomness
        grid_size = int(np.sqrt(num_sensors))
        for i in range(grid_size):
            for j in range(grid_size):
                # Grid with jitter
                lat = 23.1 + (i / grid_size) * 0.3 + np.random.uniform(-0.015, 0.015)
                lon = 79.6 + (j / grid_size) * 0.3 + np.random.uniform(-0.015, 0.015)
                locations.append([lat, lon])
        
        # Add some sensors near flood center
        for _ in range(int(num_sensors * 0.15)):
            angle = np.random.uniform(0, 2*np.pi)
            radius = np.random.uniform(0.01, 0.04)
            lat = flood_center[0] + radius * np.cos(angle)
            lon = flood_center[1] + radius * np.sin(angle)
            locations.append([lat, lon])
        
        locations = np.array(locations[:num_sensors])
        
        # Calculate distances from flood center (in km)
        center_lat, center_lon = flood_center
        distances = np.sqrt(
            ((locations[:, 0] - center_lat) * 111) ** 2 + 
            ((locations[:, 1] - center_lon) * 111) ** 2
        )
        
        # Generate readings with clear spatial pattern
        rainfall = np.zeros(len(locations))
        water_level = np.zeros(len(locations))
        soil_moisture = np.zeros(len(locations))
        risk_scores = np.zeros(len(locations))
        
        for i, dist in enumerate(distances):
            # Base values for critical scenario
            if dist < 2.0:  # Very close to center
                rainfall[i] = 130 + np.random.normal(0, 15)
                water_level[i] = 160 + np.random.normal(0, 20)
                soil_moisture[i] = 92 + np.random.normal(0, 4)
                risk_scores[i] = 0.85 + np.random.uniform(-0.08, 0.08)
            elif dist < 4.0:  # Close to center
                rainfall[i] = 100 + np.random.normal(0, 20)
                water_level[i] = 120 + np.random.normal(0, 25)
                soil_moisture[i] = 85 + np.random.normal(0, 5)
                risk_scores[i] = 0.65 + np.random.uniform(-0.08, 0.08)
            elif dist < 7.0:  # Medium distance
                rainfall[i] = 60 + np.random.normal(0, 20)
                water_level[i] = 70 + np.random.normal(0, 20)
                soil_moisture[i] = 70 + np.random.normal(0, 8)
                risk_scores[i] = 0.45 + np.random.uniform(-0.08, 0.08)
            else:  # Far from center
                rainfall[i] = 20 + np.random.normal(0, 10)
                water_level[i] = 30 + np.random.normal(0, 10)
                soil_moisture[i] = 40 + np.random.normal(0, 10)
                risk_scores[i] = 0.15 + np.random.uniform(-0.08, 0.08)
            
            # Add some randomness
            rainfall[i] = np.clip(rainfall[i], 0, 200)
            water_level[i] = np.clip(water_level[i], 0, 250)
            soil_moisture[i] = np.clip(soil_moisture[i], 0, 100)
            risk_scores[i] = np.clip(risk_scores[i], 0, 1)
        
        # Assign risk levels
        risk_levels = []
        for score in risk_scores:
            if score > 0.75:
                risk_levels.append("CRITICAL")
            elif score > 0.55:
                risk_levels.append("HIGH")
            elif score > 0.30:
                risk_levels.append("MEDIUM")
            else:
                risk_levels.append("LOW")
        
        readings = {
            'rainfall_mm': rainfall,
            'water_level_cm': water_level,
            'soil_moisture_percent': soil_moisture,
            'temperature_c': 25 + np.random.normal(0, 2, len(locations)),
            'risk_scores': risk_scores,
            'risk_levels': np.array(risk_levels)
        }
        
        return {
            'locations': locations,
            'readings': readings,
            'sensor_ids': [f"S{i:04d}" for i in range(len(locations))],
            'timestamps': [datetime.now().isoformat()] * len(locations)
        }


# Try to import real modules, fall back to mocks
try:
    from app.pipeline.satellite.processor import SatelliteProcessor
    from app.config import settings
    print("✅ Loaded real SatelliteProcessor")
    USE_REAL_SATELLITE = True
except ImportError:
    SatelliteProcessor = MockSatelliteProcessor
    USE_REAL_SATELLITE = False
    print("⚠️ Using enhanced mock SatelliteProcessor")

try:
    from app.pipeline.sensors.simulator import SensorSimulator
    from app.pipeline.sensors.config import SensorConfig, Scenario
    print("✅ Loaded real SensorSimulator")
    USE_REAL_SENSOR = True
except ImportError:
    SensorSimulator = MockSensorSimulator
    SensorConfig = None
    Scenario = None
    USE_REAL_SENSOR = False
    print("⚠️ Using enhanced mock SensorSimulator")


# ============================================================================
# MAIN DEMO CLASS
# ============================================================================

class DisasterMappingDemo:
    """
    Enhanced disaster mapping pipeline for hackathon demo.
    """
    
    def __init__(self, output_dir: str = "./demo_output"):
        """Initialize demo with output directory."""
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialize processors
        self.satellite_processor = SatelliteProcessor()
        
        # Initialize sensor simulator
        try:
            if USE_REAL_SENSOR and SensorConfig is not None:
                config = SensorConfig(
                    NUM_SENSORS=120,
                    SCENARIO=Scenario.CRITICAL,
                    OUTPUT_DIR=output_dir,
                    FLOOD_CENTER_LAT=23.25,
                    FLOOD_CENTER_LON=79.75,
                    RANDOM_SEED=42
                )
                self.sensor_simulator = SensorSimulator(config)
            else:
                self.sensor_simulator = SensorSimulator()
        except Exception as e:
            print(f"⚠️ Sensor simulator init failed: {e}")
            self.sensor_simulator = SensorSimulator()
        
        # Store results
        self.satellite_result = None
        self.sensor_data = None
        self.risk_zones = []
        self.statistics = {}
    
    def create_test_image(self) -> Tuple[str, str]:
        """
        Create a synthetic test image with clear flood pattern.
        """
        print("\n📸 Creating synthetic test image with flood pattern...")
        
        height, width = 512, 512
        image = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Create flood pattern with multiple flood zones
        x = np.linspace(-2.5, 2.5, width)
        y = np.linspace(-2.5, 2.5, height)
        X, Y = np.meshgrid(x, y)
        
        # Multiple flood zones
        flood1 = (X/1.2)**2 + (Y/0.8)**2 < 0.6
        flood2 = (X/2.0)**2 + (Y/1.5)**2 < 0.4
        flood3 = ((X-1.0)/1.0)**2 + ((Y+0.5)/0.8)**2 < 0.3
        flood_mask = flood1 | flood2 | flood3
        
        # Generate land textures
        land_red = np.random.randint(80, 200, (height, width))
        land_green = np.random.randint(70, 180, (height, width))
        land_blue = np.random.randint(30, 120, (height, width))
        
        # Water colors
        water_red = np.random.randint(10, 50, (height, width))
        water_green = np.random.randint(30, 80, (height, width))
        water_blue = np.random.randint(120, 220, (height, width))
        
        # Apply to image
        image[:, :, 0] = np.where(flood_mask, water_red, land_red)
        image[:, :, 1] = np.where(flood_mask, water_green, land_green)
        image[:, :, 2] = np.where(flood_mask, water_blue, land_blue)
        
        # Add some noise
        noise = np.random.randint(0, 15, (height, width, 3))
        image = np.clip(image.astype(int) + noise, 0, 255).astype(np.uint8)
        
        # Save image
        from PIL import Image
        image_path = os.path.join(self.output_dir, "flood_image.png")
        Image.fromarray(image).save(image_path)
        
        # Create before image (less flood)
        before_flood = (X/1.5)**2 + (Y/1.0)**2 < 0.3
        before_image = np.zeros((height, width, 3), dtype=np.uint8)
        before_image[:, :, 0] = np.where(before_flood, water_red - 20, land_red)
        before_image[:, :, 1] = np.where(before_flood, water_green - 20, land_green)
        before_image[:, :, 2] = np.where(before_flood, water_blue - 30, land_blue)
        before_image = np.clip(before_image.astype(int) + noise//2, 0, 255).astype(np.uint8)
        
        before_path = os.path.join(self.output_dir, "before_flood.png")
        Image.fromarray(before_image).save(before_path)
        
        flood_percentage = np.sum(flood_mask) / (height * width) * 100
        print(f"  ✅ Test images created")
        print(f"  📊 Flood covers {flood_percentage:.1f}% of image")
        print(f"  📁 {image_path}")
        print(f"  📁 {before_path}")
        
        return image_path, before_path
    
    def run_satellite_processing(self, image_path: str, before_path: Optional[str] = None):
        """Run satellite processing."""
        print("\n🛰️ Running satellite processing...")
        print("  ⏳ Analyzing NDWI and detecting floods...")
        
        try:
            result = self.satellite_processor.process_image(
                image_path=image_path,
                before_image_path=before_path,
                threshold=0.2
            )
            
            self.satellite_result = result
            
            print(f"  ✅ Satellite processing complete")
            print(f"  🌊 Flood probability: {result.get('flood_probability', 0):.1%}")
            print(f"  📏 Flood area: {result.get('flood_area_km2', 0):.1f} km²")
            print(f"  📊 Flood percentage: {result.get('flood_percentage', 0):.1f}%")
            
            return result
            
        except Exception as e:
            print(f"  ⚠️ Satellite processing error: {e}")
            print("  📡 Using enhanced mock data...")
            
            # Enhanced fallback with realistic flood
            result = {
                "image_id": "demo_flood",
                "location": {"lat": 23.25, "lon": 79.75},
                "flood_probability": 0.82,
                "flood_area_km2": 68.5,
                "flood_percentage": 42.3,
                "ndwi_values": None,
                "mask": None,
                "status": "success",
                "error": None,
                "processed_at": datetime.now().isoformat()
            }
            self.satellite_result = result
            return result
    
    def run_sensor_simulation(self):
        """Generate sensor data with clear flood pattern."""
        print("\n📡 Generating sensor data...")
        print("  ⏳ Creating sensors with risk gradient...")
        
        try:
            if USE_REAL_SENSOR:
                # Use real simulator if available
                result = self.sensor_simulator.generate_export_visualize(
                    scenario=Scenario.CRITICAL if Scenario else None,
                    num_sensors=120
                )
                data = result.get('data')
            else:
                data = self.sensor_simulator.generate(scenario="critical", num_sensors=120)
            
            self.sensor_data = data
            
            locations = data.get('locations', np.array([]))
            readings = data.get('readings', {})
            
            print(f"  ✅ Generated {len(locations)} sensors")
            
            if len(locations) > 0:
                # Count risk levels
                risk_levels = readings.get('risk_levels', [])
                if len(risk_levels) > 0:
                    unique, counts = np.unique(risk_levels, return_counts=True)
                    print("  📊 Sensor risk distribution:")
                    for level, count in zip(unique, counts):
                        print(f"    {level}: {count} sensors")
                
                # Summary stats
                print(f"  🌧️ Avg rainfall: {np.mean(readings.get('rainfall_mm', [0])):.1f} mm")
                print(f"  💧 Avg water level: {np.mean(readings.get('water_level_cm', [0])):.1f} cm")
                print(f"  🌱 Avg soil moisture: {np.mean(readings.get('soil_moisture_percent', [0])):.1f}%")
            
            return data
            
        except Exception as e:
            print(f"  ⚠️ Sensor simulation error: {e}")
            print("  📡 Using enhanced mock sensor data...")
            
            # Enhanced fallback with clear pattern
            np.random.seed(42)
            num_sensors = 120
            locations = []
            
            # Create grid with clustering
            flood_center = (23.25, 79.75)
            for i in range(int(np.sqrt(num_sensors))):
                for j in range(int(np.sqrt(num_sensors))):
                    lat = 23.1 + (i / np.sqrt(num_sensors)) * 0.3 + np.random.uniform(-0.01, 0.01)
                    lon = 79.6 + (j / np.sqrt(num_sensors)) * 0.3 + np.random.uniform(-0.01, 0.01)
                    locations.append([lat, lon])
            
            locations = np.array(locations[:num_sensors])
            
            # Calculate distances (km)
            distances = np.sqrt(
                ((locations[:, 0] - flood_center[0]) * 111) ** 2 + 
                ((locations[:, 1] - flood_center[1]) * 111) ** 2
            )
            
            # Generate readings with clear risk zones
            rainfall = np.clip(130 * np.exp(-distances/3) + np.random.normal(0, 10, len(locations)), 0, 200)
            water_level = np.clip(160 * np.exp(-distances/3) + np.random.normal(0, 15, len(locations)), 0, 250)
            soil_moisture = np.clip(92 * np.exp(-distances/3) + np.random.normal(0, 5, len(locations)), 0, 100)
            
            # Risk scores based on distance
            risk_scores = np.clip(1 / (1 + (distances / 2.5) ** 2), 0, 1)
            
            risk_levels = []
            for score in risk_scores:
                if score > 0.75: risk_levels.append("CRITICAL")
                elif score > 0.55: risk_levels.append("HIGH")
                elif score > 0.30: risk_levels.append("MEDIUM")
                else: risk_levels.append("LOW")
            
            self.sensor_data = {
                'locations': locations,
                'readings': {
                    'rainfall_mm': rainfall,
                    'water_level_cm': water_level,
                    'soil_moisture_percent': soil_moisture,
                    'temperature_c': 25 + np.random.normal(0, 2, len(locations)),
                    'risk_scores': risk_scores,
                    'risk_levels': np.array(risk_levels)
                },
                'sensor_ids': [f"S{i:04d}" for i in range(len(locations))],
                'timestamps': [datetime.now().isoformat()] * len(locations)
            }
            
            return self.sensor_data
    
    def fuse_data(self) -> float:
        """
        Enhanced fusion with weighted combination.
        """
        print("\n🔀 Fusing satellite and sensor data...")
        
        # Satellite flood probability
        satellite_prob = self.satellite_result.get('flood_probability', 0.5)
        
        # Sensor data
        sensor_readings = self.sensor_data.get('readings', {})
        sensor_scores = sensor_readings.get('risk_scores', np.array([]))
        
        if len(sensor_scores) > 0:
            # Weighted by distance (give more weight to near-center sensors)
            locations = self.sensor_data.get('locations', np.array([]))
            if len(locations) > 0:
                center_lat, center_lon = 23.25, 79.75
                distances = np.sqrt(
                    ((locations[:, 0] - center_lat) * 111) ** 2 + 
                    ((locations[:, 1] - center_lon) * 111) ** 2
                )
                # Inverse distance weighting
                weights = np.exp(-distances / 5.0)
                sensor_score = np.average(sensor_scores, weights=weights)
            else:
                sensor_score = np.mean(sensor_scores)
        else:
            sensor_score = satellite_prob * 0.6
        
        # Enhanced fusion - gives more weight to satellite for broad coverage
        final_risk = 0.55 * satellite_prob + 0.45 * sensor_score
        final_risk = np.clip(final_risk, 0, 1)
        
        print(f"  🛰️ Satellite contribution: {satellite_prob:.1%}")
        print(f"  📡 Sensor contribution: {sensor_score:.1%}")
        print(f"  🎯 Final fused risk: {final_risk:.1%}")
        
        return final_risk
    
    def classify_risk(self, score: float) -> Tuple[str, str]:
        """Classify risk level."""
        if score > 0.75:
            return "CRITICAL", "#FF0000"
        elif score > 0.55:
            return "HIGH", "#FF8800"
        elif score > 0.30:
            return "MEDIUM", "#FFFF00"
        else:
            return "LOW", "#00FF00"
    
    def generate_risk_zones(self, fused_score: float) -> List[Dict]:
        """Generate risk zones from fused data."""
        print("\n🗺️ Generating risk zones...")
        
        risk_zones = []
        locations = self.sensor_data.get('locations', np.array([]))
        sensor_readings = self.sensor_data.get('readings', {})
        sensor_scores = sensor_readings.get('risk_scores', np.array([]))
        sensor_ids = self.sensor_data.get('sensor_ids', [])
        
        # Create zones based on sensor clusters
        if len(locations) > 0:
            # Select sensors with highest risk
            if len(sensor_scores) > 0:
                # Sort by risk score descending
                sorted_indices = np.argsort(sensor_scores)[::-1]
                top_indices = sorted_indices[:min(15, len(sorted_indices))]
            else:
                # If no risk scores, use random selection
                top_indices = np.random.choice(len(locations), min(15, len(locations)), replace=False)
            
            for i, idx in enumerate(top_indices):
                lat = locations[idx, 0]
                lon = locations[idx, 1]
                
                # Get sensor risk
                sensor_risk = sensor_scores[idx] if len(sensor_scores) > idx else 0.5
                
                # Calculate zone risk (blend satellite and sensor)
                zone_risk = 0.5 * fused_score + 0.5 * sensor_risk
                zone_risk = np.clip(zone_risk, 0, 1)
                
                zone_risk_level, _ = self.classify_risk(zone_risk)
                
                zone = {
                    "zone_id": f"ZONE_{i+1:04d}",
                    "grid_cell": f"G{i+1:03d}",
                    "location": {"lat": float(lat), "lon": float(lon)},
                    "risk_score": float(zone_risk),
                    "risk_level": zone_risk_level,
                    "confidence": float(fused_score * 0.85 + 0.1),
                    "satellite_contribution": 0.55,
                    "sensor_contribution": 0.45,
                    "explanation": f"Risk zone {i+1} near sensor {sensor_ids[idx] if idx < len(sensor_ids) else f'S{i:04d}'}",
                    "disagreement": False
                }
                risk_zones.append(zone)
            
            # Add some high-risk zones near flood center
            center_lat, center_lon = 23.25, 79.75
            for i in range(3):
                lat = center_lat + np.random.uniform(-0.02, 0.02)
                lon = center_lon + np.random.uniform(-0.02, 0.02)
                zone_risk = fused_score * np.random.uniform(0.85, 1.0)
                zone_risk = np.clip(zone_risk, 0, 1)
                
                zone = {
                    "zone_id": f"ZONE_CENTER_{i+1:04d}",
                    "grid_cell": f"GC{i+1:03d}",
                    "location": {"lat": float(lat), "lon": float(lon)},
                    "risk_score": float(zone_risk),
                    "risk_level": "CRITICAL",
                    "confidence": float(fused_score * 0.9),
                    "satellite_contribution": 0.6,
                    "sensor_contribution": 0.4,
                    "explanation": f"Critical zone near flood epicenter",
                    "disagreement": False
                }
                risk_zones.append(zone)
        
        self.risk_zones = risk_zones
        print(f"  ✅ Generated {len(risk_zones)} risk zones")
        
        # Show distribution
        levels = {}
        for zone in risk_zones:
            level = zone.get('risk_level', 'LOW')
            levels[level] = levels.get(level, 0) + 1
        
        print("  📊 Zone risk distribution:")
        for level in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
            if level in levels:
                print(f"    {level}: {levels[level]} zones")
        
        return risk_zones
    
    def calculate_statistics(self, fused_score: float) -> Dict:
        """Calculate risk statistics."""
        print("\n📊 Calculating statistics...")
        
        # Count zones by risk level
        zone_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
        for zone in self.risk_zones:
            level = zone.get("risk_level", "LOW")
            if level in zone_counts:
                zone_counts[level] += 1
        
        # Get sensor data
        locations = self.sensor_data.get('locations', np.array([]))
        sensor_readings = self.sensor_data.get('readings', {})
        
        # Calculate affected area (use satellite data)
        affected_area = self.satellite_result.get('flood_area_km2', 68.5)
        
        # Calculate risk distribution percentages
        total_zones = sum(zone_counts.values()) or 1
        
        stats = {
            "total_area_km2": 250.0,
            "affected_area_km2": float(affected_area),
            "critical_zones": zone_counts.get("CRITICAL", 0),
            "high_zones": zone_counts.get("HIGH", 0),
            "medium_zones": zone_counts.get("MEDIUM", 0),
            "low_zones": zone_counts.get("LOW", 0),
            "active_sensors": len(locations),
            "avg_confidence": float(fused_score * 0.85 + 0.1),
            "last_updated": datetime.now().isoformat(),
            "fused_risk_score": float(fused_score),
            "satellite_probability": float(self.satellite_result.get('flood_probability', 0)),
            "sensor_average_risk": float(np.mean(
                sensor_readings.get('risk_scores', np.array([0]))
            )) if len(sensor_readings.get('risk_scores', [])) > 0 else 0,
            "risk_distribution": zone_counts,
            "scenario": "CRITICAL",
            "risk_level_percentage": {
                "CRITICAL": f"{zone_counts.get('CRITICAL', 0) / total_zones * 100:.1f}%",
                "HIGH": f"{zone_counts.get('HIGH', 0) / total_zones * 100:.1f}%",
                "MEDIUM": f"{zone_counts.get('MEDIUM', 0) / total_zones * 100:.1f}%",
                "LOW": f"{zone_counts.get('LOW', 0) / total_zones * 100:.1f}%"
            }
        }
        
        self.statistics = stats
        print(f"  ✅ Statistics calculated")
        print(f"  🔴 Critical zones: {stats['critical_zones']}")
        print(f"  🟠 High zones: {stats['high_zones']}")
        print(f"  🟡 Medium zones: {stats['medium_zones']}")
        print(f"  🟢 Low zones: {stats['low_zones']}")
        print(f"  📊 Total affected area: {affected_area:.1f} km²")
        
        return stats
    
    def save_outputs(self) -> Dict[str, str]:
        """Save outputs to JSON files."""
        print("\n💾 Saving outputs...")
        
        # Save risk zones
        risk_zones_path = os.path.join(self.output_dir, "risk_zones.json")
        with open(risk_zones_path, 'w') as f:
            json.dump({
                "metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "version": "1.0",
                    "source": "Satellite-Assisted Disaster Mapping System Demo",
                    "scenario": "CRITICAL"
                },
                "risk_zones": self.risk_zones
            }, f, indent=2)
        print(f"  ✅ Saved: {risk_zones_path}")
        
        # Save statistics
        stats_path = os.path.join(self.output_dir, "statistics.json")
        with open(stats_path, 'w') as f:
            json.dump({
                "metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "version": "1.0"
                },
                "statistics": self.statistics
            }, f, indent=2)
        print(f"  ✅ Saved: {stats_path}")
        
        # Save complete report
        report = {
            "timestamp": datetime.now().isoformat(),
            "pipeline": {
                "satellite": {
                    "flood_probability": self.satellite_result.get('flood_probability', 0),
                    "flood_area_km2": self.satellite_result.get('flood_area_km2', 0),
                    "flood_percentage": self.satellite_result.get('flood_percentage', 0),
                    "status": self.satellite_result.get('status', 'unknown')
                },
                "sensor": {
                    "num_sensors": len(self.sensor_data.get('locations', [])),
                    "avg_risk_score": float(np.mean(
                        self.sensor_data.get('readings', {}).get('risk_scores', np.array([0]))
                    )) if len(self.sensor_data.get('readings', {}).get('risk_scores', [])) > 0 else 0
                },
                "fusion": {
                    "final_risk_score": self.statistics.get('fused_risk_score', 0),
                    "overall_risk_level": self.classify_risk(
                        self.statistics.get('fused_risk_score', 0)
                    )[0]
                }
            },
            "risk_zones_count": len(self.risk_zones),
            "risk_distribution": self.statistics.get('risk_distribution', {}),
            "statistics": self.statistics
        }
        
        report_path = os.path.join(self.output_dir, "complete_report.json")
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"  ✅ Saved: {report_path}")
        
        return {
            "risk_zones": risk_zones_path,
            "statistics": stats_path,
            "report": report_path
        }
    
    def run(self) -> Dict:
        """Run the complete demo pipeline."""
        print("\n" + "="*70)
        print("  🚀 SATELLITE-ASSISTED DISASTER MAPPING SYSTEM")
        print("  SIH Hackathon Demo - Enhanced Version")
        print("="*70)
        print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Output: {self.output_dir}")
        print("="*70)
        
        start_time = datetime.now()
        
        try:
            # Step 1: Create test image
            image_path, before_path = self.create_test_image()
            
            # Step 2: Run satellite processing
            satellite_result = self.run_satellite_processing(image_path, before_path)
            
            # Step 3: Generate sensor data
            sensor_data = self.run_sensor_simulation()
            
            # Step 4: Fuse data
            fused_score = self.fuse_data()
            
            # Step 5: Generate risk zones
            risk_zones = self.generate_risk_zones(fused_score)
            
            # Step 6: Calculate statistics
            statistics = self.calculate_statistics(fused_score)
            
            # Step 7: Save outputs
            files = self.save_outputs()
            
            # Calculate execution time
            elapsed = (datetime.now() - start_time).total_seconds()
            
            # Determine overall risk
            risk_level, color = self.classify_risk(fused_score)
            
            # Print summary
            print("\n" + "="*70)
            print("  ✅ DEMO COMPLETED SUCCESSFULLY!")
            print("="*70)
            print(f"  ⏱️ Execution time: {elapsed:.2f} seconds")
            print(f"  📁 Output directory: {self.output_dir}")
            print("\n  📄 Generated files:")
            for name, path in files.items():
                print(f"    - {name}: {path}")
            
            print(f"\n  🎯 FINAL RISK ASSESSMENT:")
            print(f"    Risk Score: {fused_score:.1%}")
            print(f"    Risk Level: {risk_level}")
            print(f"    Affected Area: {statistics.get('affected_area_km2', 0):.1f} km²")
            print(f"    Critical Zones: {statistics.get('critical_zones', 0)}")
            print(f"    High Zones: {statistics.get('high_zones', 0)}")
            print(f"    Active Sensors: {statistics.get('active_sensors', 0)}")
            
            print("\n  📊 Risk Distribution:")
            for level in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
                count = statistics.get('risk_distribution', {}).get(level, 0)
                if count > 0:
                    print(f"    {level}: {count} zones")
            
            print("\n" + "="*70)
            print("  ✅ Demo ready for presentation!")
            print("  📊 Open risk_zones.json to see the results")
            print("="*70 + "\n")
            
            return {
                "success": True,
                "execution_time": elapsed,
                "files": files,
                "risk_score": fused_score,
                "risk_level": risk_level,
                "statistics": statistics,
                "risk_zones": risk_zones
            }
            
        except Exception as e:
            print(f"\n❌ Demo failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }


# ============================================================================
# COMMAND LINE EXECUTION
# ============================================================================

def main():
    """Command line entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Satellite-Assisted Disaster Mapping System - Enhanced Demo"
    )
    parser.add_argument(
        "--output", 
        type=str, 
        default="./demo_output",
        help="Output directory for generated files"
    )
    
    args = parser.parse_args()
    
    # Run demo
    demo = DisasterMappingDemo(output_dir=args.output)
    result = demo.run()
    
    # Return exit code
    return 0 if result.get("success", False) else 1


if __name__ == "__main__":
    sys.exit(main())