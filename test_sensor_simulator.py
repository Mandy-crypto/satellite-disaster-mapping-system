"""
Test script for sensor simulator.

Tests all aspects of the sensor simulation pipeline.
"""

import os
import sys
import json
import unittest
import numpy as np
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.pipeline.sensors.config import SensorConfig, Scenario
from app.pipeline.sensors.simulator import SensorSimulator
from app.pipeline.sensors.scenario_generator import ScenarioGenerator
from app.pipeline.sensors.spatial_correlation import SpatialCorrelator
from app.pipeline.sensors.noise_generator import NoiseGenerator
from app.pipeline.sensors.exporter import SensorExporter
from app.pipeline.sensors.visualizer import SensorVisualizer


class TestSensorSimulator(unittest.TestCase):
    """Test cases for sensor simulator."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_output_dir = "./test_sensor_output"
        self.config = SensorConfig(
            NUM_SENSORS=50,
            SCENARIO=Scenario.NORMAL,
            OUTPUT_DIR=self.test_output_dir,
            RANDOM_SEED=42,
            VISUALIZE=False
        )
        self.simulator = SensorSimulator(self.config)
    
    def tearDown(self):
        """Clean up test files."""
        import shutil
        if os.path.exists(self.test_output_dir):
            shutil.rmtree(self.test_output_dir)
    
    def test_config_validation(self):
        """Test configuration validation."""
        # Valid config
        config = SensorConfig()
        self.assertIsNotNone(config)
        
        # Invalid config
        with self.assertRaises(ValueError):
            SensorConfig(NUM_SENSORS=5)  # Too few sensors
        
        with self.assertRaises(ValueError):
            SensorConfig(NOISE_AMOUNT=0.6)  # Too much noise
        
        with self.assertRaises(ValueError):
            SensorConfig(LAT_MIN=23.5, LAT_MAX=23.0)  # Invalid bounds
    
    def test_spatial_correlation(self):
        """Test spatial correlation functions."""
        correlator = SpatialCorrelator(self.config)
        
        # Test distance calculation
        locations = np.array([
            [23.25, 79.75],  # At center
            [23.30, 79.80],  # 5km away
            [23.40, 79.90]   # 15km away
        ])
        distances = correlator.calculate_distances(locations)
        self.assertEqual(len(distances), 3)
        self.assertAlmostEqual(distances[0], 0.0, places=1)
        
        # Test risk level
        self.assertEqual(correlator.get_risk_level(0.5), "CRITICAL")
        self.assertEqual(correlator.get_risk_level(2.0), "HIGH")
        self.assertEqual(correlator.get_risk_level(4.0), "MEDIUM")
        self.assertEqual(correlator.get_risk_level(8.0), "LOW")
        
        # Test risk score
        self.assertAlmostEqual(correlator.get_risk_score(0), 1.0)
        self.assertAlmostEqual(correlator.get_risk_score(10), 0.0, places=1)
        
        # Test Gaussian weights
        weights = correlator.gaussian_weight(np.array([0, 1, 2, 3]), sigma=2.0)
        self.assertEqual(len(weights), 4)
        self.assertAlmostEqual(weights[0], 1.0)
        self.assertLess(weights[1], 1.0)
    
    def test_noise_generator(self):
        """Test noise generation."""
        noise_gen = NoiseGenerator(noise_amount=0.1, random_seed=42)
        
        # Test Gaussian noise
        values = np.array([10.0, 20.0, 30.0, 40.0])
        noisy = noise_gen.add_gaussian_noise(values, std_scale=0.1)
        self.assertEqual(len(noisy), 4)
        self.assertFalse(np.array_equal(noisy, values))
        
        # Test sensor-specific noise
        readings = {
            'rainfall_mm': np.array([50, 60, 70]),
            'temperature_c': np.array([25, 26, 27])
        }
        noisy_readings = noise_gen.add_sensor_specific_noise(readings)
        self.assertIn('rainfall_mm', noisy_readings)
        self.assertIn('temperature_c', noisy_readings)
        
        # Test outliers
        values = np.ones(100) * 50
        outlier_values = noise_gen.add_outliers(values, outlier_fraction=0.02)
        self.assertNotEqual(np.sum(outlier_values), np.sum(values))
    
    def test_scenario_generator(self):
        """Test scenario generation."""
        generator = ScenarioGenerator(self.config)
        
        # Test location generation
        locations = generator.generate_sensor_locations()
        self.assertEqual(len(locations), self.config.NUM_SENSORS)
        self.assertTrue(np.all(locations[:, 0] >= self.config.LAT_MIN))
        self.assertTrue(np.all(locations[:, 0] <= self.config.LAT_MAX))
        self.assertTrue(np.all(locations[:, 1] >= self.config.LON_MIN))
        self.assertTrue(np.all(locations[:, 1] <= self.config.LON_MAX))
        
        # Test sensor IDs
        sensor_ids = generator.generate_sensor_ids(10)
        self.assertEqual(len(sensor_ids), 10)
        self.assertTrue(all(id.startswith(self.config.SENSOR_ID_PREFIX) for id in sensor_ids))
        
        # Test scenario generation
        data = generator.generate_scenario(Scenario.NORMAL)
        self.assertEqual(len(data.sensor_ids), self.config.NUM_SENSORS)
        self.assertIn('rainfall_mm', data.readings)
        self.assertIn('risk_scores', data.readings)
        self.assertIn('risk_levels', data.readings)
        
        # Test all scenarios
        scenarios = generator.generate_all_scenarios()
        self.assertIn(Scenario.NORMAL, scenarios)
        self.assertIn(Scenario.WARNING, scenarios)
        self.assertIn(Scenario.CRITICAL, scenarios)
    
    def test_exporter(self):
        """Test data export."""
        # Generate test data
        generator = ScenarioGenerator(self.config)
        data = generator.generate_scenario(Scenario.NORMAL)
        
        # Test exporter
        exporter = SensorExporter(self.test_output_dir)
        
        # Test CSV export
        csv_path = exporter.export_csv(data)
        self.assertTrue(os.path.exists(csv_path))
        self.assertTrue(csv_path.endswith('.csv'))
        
        # Test JSON export
        json_path = exporter.export_json(data)
        self.assertTrue(os.path.exists(json_path))
        self.assertTrue(json_path.endswith('.json'))
        
        # Test GeoJSON export
        geojson_path = exporter.export_geojson(data)
        self.assertTrue(os.path.exists(geojson_path))
        self.assertTrue(geojson_path.endswith('.geojson'))
        
        # Test all exports
        files = exporter.export_all(data)
        self.assertIn('csv', files)
        self.assertIn('json', files)
        self.assertIn('geojson', files)
    
    def test_simulator_full_pipeline(self):
        """Test full simulator pipeline."""
        # Generate, export, visualize
        result = self.simulator.generate_export_visualize()
        
        # Check results
        self.assertIn('data', result)
        self.assertIn('stats', result)
        self.assertIn('files', result)
        self.assertIn('config', result)
        
        # Check files
        self.assertTrue(os.path.exists(self.test_output_dir))
        self.assertTrue(len(result['files']) > 0)
    
    def test_schema_compliance(self):
        """Test that generated data matches canonical schemas."""
        # Generate data
        result = self.simulator.generate()
        data = result['data']
        
        # Get first reading
        first_idx = 0
        reading = {
            'sensor_id': data.sensor_ids[first_idx],
            'latitude': float(data.locations[first_idx, 0]),
            'longitude': float(data.locations[first_idx, 1]),
            'timestamp': data.timestamps[first_idx],
            'rainfall_mm': float(data.readings['rainfall_mm'][first_idx]),
            'water_level_cm': float(data.readings['water_level_cm'][first_idx]),
            'soil_moisture_percent': float(data.readings['soil_moisture_percent'][first_idx]),
            'temperature_c': float(data.readings['temperature_c'][first_idx])
        }
        
        # Check required fields
        required_fields = [
            'sensor_id', 'latitude', 'longitude', 'timestamp',
            'rainfall_mm', 'water_level_cm', 'soil_moisture_percent', 'temperature_c'
        ]
        for field in required_fields:
            self.assertIn(field, reading)
        
        # Check types
        self.assertIsInstance(reading['sensor_id'], str)
        self.assertIsInstance(reading['latitude'], float)
        self.assertIsInstance(reading['longitude'], float)
        self.assertIsInstance(reading['timestamp'], str)
        self.assertIsInstance(reading['rainfall_mm'], float)
        self.assertIsInstance(reading['water_level_cm'], float)
        self.assertIsInstance(reading['soil_moisture_percent'], float)
        self.assertIsInstance(reading['temperature_c'], float)
        
        # Check value ranges
        self.assertGreaterEqual(reading['rainfall_mm'], 0)
        self.assertGreaterEqual(reading['water_level_cm'], 0)
        self.assertBetween(reading['soil_moisture_percent'], 0, 100)
        self.assertGreaterEqual(reading['temperature_c'], 0)
    
    def assertBetween(self, value, min_val, max_val):
        """Assert that value is between min_val and max_val."""
        self.assertGreaterEqual(value, min_val)
        self.assertLessEqual(value, max_val)
    
    def test_all_scenarios_generation(self):
        """Test generation of all scenarios."""
        results = self.simulator.generate_all_scenarios()
        
        self.assertIn('normal', results)
        self.assertIn('warning', results)
        self.assertIn('critical', results)
        
        # Check that each scenario has different statistics
        normal_stats = results['normal']['stats']
        critical_stats = results['critical']['stats']
        
        # Critical should have higher rainfall
        self.assertLess(
            normal_stats['parameter_statistics']['rainfall_mm']['mean'],
            critical_stats['parameter_statistics']['rainfall_mm']['mean']
        )
    
    def test_visualizer(self):
        """Test visualization generation."""
        # Generate data
        generator = ScenarioGenerator(self.config)
        data = generator.generate_scenario(Scenario.NORMAL)
        
        # Create visualizer
        visualizer = SensorVisualizer(self.test_output_dir)
        
        # Create risk map
        map_path = visualizer.create_risk_map(data)
        self.assertTrue(os.path.exists(map_path))
        self.assertTrue(map_path.endswith('.html'))
        
        # Create heatmap
        heatmap_path = visualizer.create_heatmap(data, 'rainfall_mm')
        self.assertTrue(os.path.exists(heatmap_path))
        
        # Create static plots
        plots = visualizer.create_static_plots(data)
        self.assertTrue(len(plots) > 0)
        for plot_path in plots.values():
            self.assertTrue(os.path.exists(plot_path))


def run_tests():
    """Run all tests."""
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSensorSimulator)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n✅ ALL TESTS PASSED!")
    else:
        print("\n❌ SOME TESTS FAILED")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)