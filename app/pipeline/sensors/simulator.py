"""
Main sensor simulator module.

Orchestrates the entire sensor data simulation pipeline.
"""

import os
import json
import yaml
import argparse
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

from app.pipeline.sensors.config import SensorConfig, Scenario
from app.pipeline.sensors.scenario_generator import ScenarioGenerator
from app.pipeline.sensors.exporter import SensorExporter
from app.pipeline.sensors.visualizer import SensorVisualizer

logger = logging.getLogger(__name__)


class SensorSimulator:
    """
    Main sensor simulator orchestrator.
    
    Coordinates all simulation components:
    1. Configuration
    2. Scenario generation
    3. Export
    4. Visualization
    """
    
    def __init__(self, config: Optional[SensorConfig] = None):
        """
        Initialize sensor simulator.
        
        Args:
            config: SensorConfig object (uses defaults if None)
        """
        self.config = config or SensorConfig()
        
        # Initialize components
        self.generator = ScenarioGenerator(self.config)
        self.exporter = SensorExporter(self.config.OUTPUT_DIR)
        self.visualizer = SensorVisualizer(self.config.OUTPUT_DIR)
        
        # Store generated data
        self.generated_data = {}
    
    def generate(self, 
                scenario: Optional[Scenario] = None,
                num_sensors: Optional[int] = None) -> Dict[str, Any]:
        """
        Generate sensor data for a scenario.
        
        Args:
            scenario: Scenario to generate (default: from config)
            num_sensors: Number of sensors (default: from config)
            
        Returns:
            Dictionary with generated data
        """
        # Update config if parameters provided
        if scenario is not None:
            self.config.SCENARIO = scenario
        if num_sensors is not None:
            self.config.NUM_SENSORS = num_sensors
        
        # Generate data
        data = self.generator.generate_scenario()
        
        # Store data
        self.generated_data[self.config.SCENARIO.value] = data
        
        # Get summary statistics
        stats = self.generator.get_summary_statistics(data)
        
        logger.info(f"Generated {self.config.NUM_SENSORS} sensors for {self.config.SCENARIO.value} scenario")
        
        return {
            'data': data,
            'stats': stats,
            'config': self.config.to_dict()
        }
    
    def export(self, 
              data: Optional[ScenarioData] = None,
              formats: Optional[List[str]] = None) -> Dict[str, str]:
        """
        Export generated data to files.
        
        Args:
            data: ScenarioData object (uses last generated if None)
            formats: List of formats to export ('csv', 'json', 'geojson')
            
        Returns:
            Dictionary of file paths
        """
        if data is None:
            if not self.generated_data:
                raise ValueError("No data generated. Call generate() first.")
            data = list(self.generated_data.values())[-1]
        
        if formats is None:
            formats = ['csv', 'json', 'geojson']
        
        files = {}
        
        # Export each format
        if 'csv' in formats:
            files['csv'] = self.exporter.export_csv(data)
        if 'json' in formats:
            files['json'] = self.exporter.export_json(data)
        if 'geojson' in formats:
            files['geojson'] = self.exporter.export_geojson(data)
        
        # Export time series if available
        if 'rainfall_mm' in data.readings and len(data.readings['rainfall_mm'].shape) > 1:
            files['timeseries'] = self.exporter.export_timeseries(data)
        
        return files
    
    def visualize(self, 
                 data: Optional[ScenarioData] = None) -> Dict[str, str]:
        """
        Create visualizations for generated data.
        
        Args:
            data: ScenarioData object (uses last generated if None)
            
        Returns:
            Dictionary of visualization file paths
        """
        if data is None:
            if not self.generated_data:
                raise ValueError("No data generated. Call generate() first.")
            data = list(self.generated_data.values())[-1]
        
        return self.visualizer.create_all_visualizations(data, self.config)
    
    def generate_export_visualize(self,
                                 scenario: Optional[Scenario] = None,
                                 num_sensors: Optional[int] = None) -> Dict[str, Any]:
        """
        Full pipeline: generate, export, and visualize.
        
        Args:
            scenario: Scenario to generate
            num_sensors: Number of sensors
            
        Returns:
            Dictionary with all results
        """
        # Generate
        result = self.generate(scenario, num_sensors)
        data = result['data']
        
        # Export
        files = self.export(data)
        
        # Visualize
        visualizations = self.visualize(data)
        
        return {
            'data': data,
            'stats': result['stats'],
            'files': files,
            'visualizations': visualizations,
            'config': self.config.to_dict()
        }
    
    def generate_all_scenarios(self) -> Dict[str, Dict[str, Any]]:
        """
        Generate data for all three scenarios.
        
        Returns:
            Dictionary with results for each scenario
        """
        results = {}
        
        for scenario in [Scenario.NORMAL, Scenario.WARNING, Scenario.CRITICAL]:
            logger.info(f"Generating {scenario.value} scenario")
            result = self.generate_export_visualize(scenario)
            results[scenario.value] = result
        
        return results
    
    def save_config(self, filename: str = "sensor_config.json"):
        """
        Save current configuration to file.
        
        Args:
            filename: Output filename
        """
        config_path = os.path.join(self.config.OUTPUT_DIR, filename)
        with open(config_path, 'w') as f:
            json.dump(self.config.to_dict(), f, indent=2)
        logger.info(f"Saved config to {config_path}")
    
    def save_summary_report(self, results: Dict[str, Any]) -> str:
        """
        Generate and save summary report.
        
        Args:
            results: Results from generate_export_visualize()
            
        Returns:
            Path to report file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(
            self.config.OUTPUT_DIR, 
            f"summary_report_{timestamp}.txt"
        )
        
        with open(report_path, 'w') as f:
            f.write("=" * 60 + "\n")
            f.write("SENSOR SIMULATION SUMMARY REPORT\n")
            f.write("=" * 60 + "\n\n")
            
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write(f"Scenario: {results.get('stats', {}).get('scenario', 'N/A')}\n")
            f.write(f"Number of Sensors: {len(results.get('data', {}).sensor_ids) if results.get('data') else 0}\n\n")
            
            # Statistics
            stats = results.get('stats', {})
            f.write("STATISTICS\n")
            f.write("-" * 40 + "\n")
            
            for key, value in stats.items():
                if key != 'parameter_statistics' and key != 'risk_distribution':
                    f.write(f"{key}: {value}\n")
            
            # Parameter statistics
            f.write("\nPARAMETER STATISTICS\n")
            f.write("-" * 40 + "\n")
            for param, stat in stats.get('parameter_statistics', {}).items():
                f.write(f"\n{param}:\n")
                for stat_key, stat_value in stat.items():
                    f.write(f"  {stat_key}: {stat_value:.2f}\n")
            
            # Risk distribution
            f.write("\nRISK DISTRIBUTION\n")
            f.write("-" * 40 + "\n")
            for level, count in stats.get('risk_distribution', {}).items():
                f.write(f"{level}: {count} sensors\n")
            
            # Files
            f.write("\nGENERATED FILES\n")
            f.write("-" * 40 + "\n")
            for file_type, file_path in results.get('files', {}).items():
                f.write(f"{file_type}: {file_path}\n")
            
            # Visualizations
            f.write("\nVISUALIZATIONS\n")
            f.write("-" * 40 + "\n")
            for viz_type, viz_path in results.get('visualizations', {}).items():
                f.write(f"{viz_type}: {viz_path}\n")
        
        logger.info(f"Summary report saved to {report_path}")
        return report_path


# Command line interface
def main():
    """Command line interface for sensor simulator."""
    parser = argparse.ArgumentParser(
        description="Sensor Data Simulator for Disaster Mapping"
    )
    parser.add_argument(
        "--scenario", 
        type=str, 
        choices=['normal', 'warning', 'critical'],
        default='normal',
        help="Operating scenario"
    )
    parser.add_argument(
        "--num-sensors", 
        type=int, 
        default=100,
        help="Number of sensors to generate"
    )
    parser.add_argument(
        "--output-dir", 
        type=str, 
        default="./sensor_output",
        help="Output directory for files"
    )
    parser.add_argument(
        "--flood-center", 
        type=str, 
        default="23.25,79.75",
        help="Flood center as 'lat,lon'"
    )
    parser.add_argument(
        "--all-scenarios", 
        action="store_true",
        help="Generate all three scenarios"
    )
    parser.add_argument(
        "--no-visualize", 
        action="store_true",
        help="Skip visualization generation"
    )
    parser.add_argument(
        "--config", 
        type=str,
        help="Configuration YAML file"
    )
    parser.add_argument(
        "--random-seed", 
        type=int, 
        default=42,
        help="Random seed for reproducibility"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Parse flood center
    flood_center = args.flood_center.split(',')
    flood_center_lat = float(flood_center[0].strip())
    flood_center_lon = float(flood_center[1].strip())
    
    # Create config
    config = SensorConfig(
        NUM_SENSORS=args.num_sensors,
        SCENARIO=Scenario(args.scenario),
        OUTPUT_DIR=args.output_dir,
        FLOOD_CENTER_LAT=flood_center_lat,
        FLOOD_CENTER_LON=flood_center_lon,
        RANDOM_SEED=args.random_seed,
        VISUALIZE=not args.no_visualize
    )
    
    # Initialize simulator
    simulator = SensorSimulator(config)
    
    if args.all_scenarios:
        # Generate all scenarios
        results = simulator.generate_all_scenarios()
        
        # Save summary reports
        for scenario, result in results.items():
            simulator.save_summary_report(result)
        
        print(f"\n✅ Generated all scenarios in {args.output_dir}")
        
    else:
        # Generate single scenario
        result = simulator.generate_export_visualize()
        
        # Save summary report
        simulator.save_summary_report(result)
        
        print(f"\n✅ Generated {args.scenario} scenario in {args.output_dir}")
        print(f"   Sensors: {args.num_sensors}")
        print(f"   Flood Center: ({flood_center_lat}, {flood_center_lon})")
        
        # Print file locations
        print("\n📁 Generated Files:")
        for file_type, file_path in result.get('files', {}).items():
            print(f"   {file_type}: {file_path}")
        
        if not args.no_visualize:
            print("\n📊 Visualizations:")
            for viz_type, viz_path in result.get('visualizations', {}).items():
                print(f"   {viz_type}: {viz_path}")


if __name__ == "__main__":
    main()