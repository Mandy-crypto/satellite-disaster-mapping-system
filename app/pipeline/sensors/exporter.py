"""
Export module for sensor data.

Exports sensor data to CSV, JSON, and GeoJSON formats.
"""

import os
import json
import csv
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from app.pipeline.sensors.scenario_generator import ScenarioData

logger = logging.getLogger(__name__)


class SensorExporter:
    """
    Export sensor data to various formats.
    
    Supports:
    - CSV
    - JSON
    - GeoJSON
    """
    
    def __init__(self, output_dir: str = "./sensor_output"):
        """
        Initialize exporter.
        
        Args:
            output_dir: Output directory for exported files
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def _prepare_dataframe(self, data: ScenarioData) -> pd.DataFrame:
        """
        Convert scenario data to pandas DataFrame.
        
        Args:
            data: ScenarioData object
            
        Returns:
            DataFrame with sensor readings
        """
        readings = data.readings
        locations = data.locations
        sensor_ids = data.sensor_ids
        timestamps = data.timestamps
        
        # Prepare data dictionary
        df_data = {
            'sensor_id': sensor_ids,
            'latitude': locations[:, 0],
            'longitude': locations[:, 1],
            'timestamp': timestamps,
            'risk_score': readings.get('risk_scores', [0] * len(sensor_ids)),
            'risk_level': readings.get('risk_levels', ['LOW'] * len(sensor_ids))
        }
        
        # Add parameter readings
        for param_name in ['rainfall_mm', 'water_level_cm', 'soil_moisture_percent', 'temperature_c']:
            if param_name in readings:
                values = readings[param_name]
                # If values is 2D (time series), take first timestep
                if len(values.shape) > 1:
                    values = values[:, 0]
                df_data[param_name] = values
        
        return pd.DataFrame(df_data)
    
    def export_csv(self, 
                  data: ScenarioData, 
                  filename: Optional[str] = None) -> str:
        """
        Export data to CSV file.
        
        Args:
            data: ScenarioData object
            filename: Output filename (optional)
            
        Returns:
            Path to created file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"sensor_data_{data.scenario.value}_{timestamp}.csv"
        
        filepath = os.path.join(self.output_dir, filename)
        
        # Prepare DataFrame
        df = self._prepare_dataframe(data)
        
        # Export to CSV
        df.to_csv(filepath, index=False)
        logger.info(f"Exported CSV: {filepath}")
        
        return filepath
    
    def export_json(self, 
                   data: ScenarioData, 
                   filename: Optional[str] = None) -> str:
        """
        Export data to JSON file.
        
        Args:
            data: ScenarioData object
            filename: Output filename (optional)
            
        Returns:
            Path to created file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"sensor_data_{data.scenario.value}_{timestamp}.json"
        
        filepath = os.path.join(self.output_dir, filename)
        
        # Prepare data
        df = self._prepare_dataframe(data)
        
        # Convert to JSON
        json_data = df.to_dict(orient='records')
        
        # Add metadata
        output = {
            'metadata': {
                'scenario': data.scenario.value,
                'num_sensors': len(data.sensor_ids),
                'exported_at': datetime.now().isoformat(),
                'version': '1.0'
            },
            'readings': json_data
        }
        
        # Write JSON
        with open(filepath, 'w') as f:
            json.dump(output, f, indent=2)
        
        logger.info(f"Exported JSON: {filepath}")
        return filepath
    
    def export_geojson(self, 
                      data: ScenarioData, 
                      filename: Optional[str] = None) -> str:
        """
        Export data to GeoJSON file.
        
        Args:
            data: ScenarioData object
            filename: Output filename (optional)
            
        Returns:
            Path to created file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"sensor_locations_{data.scenario.value}_{timestamp}.geojson"
        
        filepath = os.path.join(self.output_dir, filename)
        
        # Prepare features
        features = []
        readings = data.readings
        locations = data.locations
        sensor_ids = data.sensor_ids
        timestamps = data.timestamps
        
        for i in range(len(locations)):
            feature = {
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [
                        float(locations[i, 1]),  # longitude
                        float(locations[i, 0])   # latitude
                    ]
                },
                'properties': {
                    'sensor_id': sensor_ids[i],
                    'timestamp': timestamps[i],
                    'risk_level': readings.get('risk_levels', ['LOW'])[i],
                    'risk_score': float(readings.get('risk_scores', [0])[i]),
                    'rainfall_mm': float(readings.get('rainfall_mm', [0])[i]),
                    'water_level_cm': float(readings.get('water_level_cm', [0])[i]),
                    'soil_moisture_percent': float(readings.get('soil_moisture_percent', [0])[i]),
                    'temperature_c': float(readings.get('temperature_c', [0])[i])
                }
            }
            features.append(feature)
        
        # Create GeoJSON
        geojson = {
            'type': 'FeatureCollection',
            'metadata': {
                'scenario': data.scenario.value,
                'num_sensors': len(sensor_ids),
                'exported_at': datetime.now().isoformat()
            },
            'features': features
        }
        
        # Write GeoJSON
        with open(filepath, 'w') as f:
            json.dump(geojson, f, indent=2)
        
        logger.info(f"Exported GeoJSON: {filepath}")
        return filepath
    
    def export_all(self, 
                  data: ScenarioData, 
                  prefix: Optional[str] = None) -> Dict[str, str]:
        """
        Export data to all supported formats.
        
        Args:
            data: ScenarioData object
            prefix: Filename prefix (optional)
            
        Returns:
            Dictionary with file paths
        """
        if prefix is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            prefix = f"sensor_{data.scenario.value}_{timestamp}"
        
        files = {
            'csv': self.export_csv(data, f"{prefix}.csv"),
            'json': self.export_json(data, f"{prefix}.json"),
            'geojson': self.export_geojson(data, f"{prefix}.geojson")
        }
        
        logger.info(f"Exported all formats to {self.output_dir}")
        return files
    
    def export_timeseries(self, 
                         data: ScenarioData, 
                         filename: Optional[str] = None) -> str:
        """
        Export time series data to CSV.
        
        Args:
            data: ScenarioData object with temporal data
            filename: Output filename (optional)
            
        Returns:
            Path to created file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"sensor_timeseries_{data.scenario.value}_{timestamp}.csv"
        
        filepath = os.path.join(self.output_dir, filename)
        
        readings = data.readings
        locations = data.locations
        sensor_ids = data.sensor_ids
        
        # Check if we have temporal data
        param_name = 'rainfall_mm'
        if param_name in readings and len(readings[param_name].shape) > 1:
            # Time series data
            time_steps = readings[param_name].shape[1]
            
            # Prepare data
            rows = []
            for i in range(len(sensor_ids)):
                for t in range(time_steps):
                    row = {
                        'sensor_id': sensor_ids[i],
                        'latitude': locations[i, 0],
                        'longitude': locations[i, 1],
                        'timestamp': data.timestamps[i] if i < len(data.timestamps) else f"2026-08-29T{12+t:02d}:00:00",
                        'timestep': t
                    }
                    
                    # Add parameters
                    for param in ['rainfall_mm', 'water_level_cm', 'soil_moisture_percent', 'temperature_c']:
                        if param in readings and len(readings[param].shape) > 1:
                            row[param] = readings[param][i, t]
                        elif param in readings:
                            row[param] = readings[param][i]
                        else:
                            row[param] = 0
                    
                    rows.append(row)
            
            # Write CSV
            with open(filepath, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            
            logger.info(f"Exported time series: {filepath}")
        
        return filepath