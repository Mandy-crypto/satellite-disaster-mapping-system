"""
Visualization module for sensor data.

Creates interactive maps and plots for sensor data visualization.
"""

import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from matplotlib.colors import LinearSegmentedColormap
import folium
from folium.plugins import HeatMap
from typing import Dict, Any, List, Optional
import pandas as pd
import logging
from datetime import datetime

from app.pipeline.sensors.scenario_generator import ScenarioData

logger = logging.getLogger(__name__)


class SensorVisualizer:
    """
    Visualize sensor data using various plotting methods.
    
    Creates:
    - Interactive maps (Folium)
    - Static plots (Matplotlib)
    - Heatmaps
    """
    
    def __init__(self, output_dir: str = "./sensor_output"):
        """
        Initialize visualizer.
        
        Args:
            output_dir: Output directory for visualizations
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Risk level colors
        self.risk_colors = {
            'LOW': '#00ff00',      # Green
            'MEDIUM': '#ffff00',    # Yellow
            'HIGH': '#ff8800',      # Orange
            'CRITICAL': '#ff0000'   # Red
        }
        
        # Create custom colormap for risk
        self.risk_cmap = LinearSegmentedColormap.from_list(
            'risk', 
            ['#00ff00', '#ffff00', '#ff8800', '#ff0000']
        )
    
    def create_risk_map(self, 
                        data: ScenarioData, 
                        filename: Optional[str] = None) -> str:
        """
        Create interactive map with sensor locations colored by risk.
        
        Args:
            data: ScenarioData object
            filename: Output filename (optional)
            
        Returns:
            Path to HTML file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"sensor_risk_map_{data.scenario.value}_{timestamp}.html"
        
        filepath = os.path.join(self.output_dir, filename)
        
        # Create base map
        center_lat = np.mean(data.locations[:, 0])
        center_lon = np.mean(data.locations[:, 1])
        
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=12,
            tiles='OpenStreetMap'
        )
        
        # Add flood center marker
        folium.Marker(
            [self.config.FLOOD_CENTER_LAT, self.config.FLOOD_CENTER_LON],
            popup='Flood Center',
            icon=folium.Icon(color='red', icon='warning-sign')
        ).add_to(m)
        
        # Add sensor markers
        readings = data.readings
        sensor_ids = data.sensor_ids
        locations = data.locations
        
        for i in range(len(locations)):
            risk_level = readings.get('risk_levels', ['LOW'])[i]
            risk_score = float(readings.get('risk_scores', [0])[i])
            color = self.risk_colors.get(risk_level, '#888888')
            
            # Create popup text
            popup_text = f"""
            <b>Sensor: {sensor_ids[i]}</b><br>
            Risk Level: <b>{risk_level}</b><br>
            Risk Score: {risk_score:.2f}<br>
            Rainfall: {readings.get('rainfall_mm', [0])[i]:.1f} mm<br>
            Water Level: {readings.get('water_level_cm', [0])[i]:.1f} cm<br>
            Soil Moisture: {readings.get('soil_moisture_percent', [0])[i]:.1f}%<br>
            Temperature: {readings.get('temperature_c', [0])[i]:.1f}°C
            """
            
            folium.CircleMarker(
                location=[locations[i, 0], locations[i, 1]],
                radius=8,
                popup=popup_text,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.8,
                weight=2
            ).add_to(m)
        
        # Add legend
        legend_html = '''
        <div style="position: fixed; bottom: 50px; right: 50px; width: 150px; height: 150px;
                    background-color: white; border: 2px solid grey; z-index: 1000;
                    padding: 10px; font-size: 14px;">
            <b>Risk Levels</b><br>
            <i style="background: #00ff00; width: 20px; height: 20px; display: inline-block;"></i> LOW<br>
            <i style="background: #ffff00; width: 20px; height: 20px; display: inline-block;"></i> MEDIUM<br>
            <i style="background: #ff8800; width: 20px; height: 20px; display: inline-block;"></i> HIGH<br>
            <i style="background: #ff0000; width: 20px; height: 20px; display: inline-block;"></i> CRITICAL
        </div>
        '''
        m.get_root().html.add_child(folium.Element(legend_html))
        
        # Save map
        m.save(filepath)
        logger.info(f"Created risk map: {filepath}")
        
        return filepath
    
    def create_heatmap(self, 
                      data: ScenarioData, 
                      parameter: str = 'rainfall_mm',
                      filename: Optional[str] = None) -> str:
        """
        Create heatmap for a specific parameter.
        
        Args:
            data: ScenarioData object
            parameter: Parameter to visualize
            filename: Output filename (optional)
            
        Returns:
            Path to HTML file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"sensor_{parameter}_{data.scenario.value}_{timestamp}.html"
        
        filepath = os.path.join(self.output_dir, filename)
        
        # Create base map
        center_lat = np.mean(data.locations[:, 0])
        center_lon = np.mean(data.locations[:, 1])
        
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=12,
            tiles='OpenStreetMap'
        )
        
        # Get parameter values
        readings = data.readings
        if parameter not in readings:
            logger.warning(f"Parameter {parameter} not found in readings")
            return filepath
        
        values = readings[parameter]
        locations = data.locations
        
        # Normalize values for heatmap
        if isinstance(values, np.ndarray):
            if len(values.shape) > 1:
                values = values[:, 0]  # First timestep
            values = values.astype(float)
            values_normalized = values / (np.max(values) + 1e-6)
            
            # Create heatmap data
            heat_data = []
            for i in range(len(locations)):
                heat_data.append([
                    locations[i, 0],
                    locations[i, 1],
                    float(values_normalized[i])
                ])
            
            # Add heatmap
            HeatMap(heat_data, radius=15, blur=10, max_zoom=1).add_to(m)
        
        # Add parameter-specific title
        param_title = parameter.replace('_', ' ').title()
        title_html = f'''
        <div style="position: fixed; top: 50px; left: 50px; width: 300px;
                    background-color: white; border: 2px solid grey; z-index: 1000;
                    padding: 10px; font-size: 16px; font-weight: bold;">
            {param_title} Heatmap
        </div>
        '''
        m.get_root().html.add_child(folium.Element(title_html))
        
        # Save map
        m.save(filepath)
        logger.info(f"Created heatmap: {filepath}")
        
        return filepath
    
    def create_static_plots(self, 
                           data: ScenarioData, 
                           filename: Optional[str] = None) -> Dict[str, str]:
        """
        Create static matplotlib plots.
        
        Args:
            data: ScenarioData object
            filename: Output filename (optional)
            
        Returns:
            Dictionary of plot file paths
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"sensor_plots_{data.scenario.value}_{timestamp}"
        
        filepaths = {}
        
        # Prepare DataFrame
        df = pd.DataFrame({
            'sensor_id': data.sensor_ids,
            'latitude': data.locations[:, 0],
            'longitude': data.locations[:, 1],
            'risk_score': data.readings.get('risk_scores', [0] * len(data.sensor_ids)),
            'risk_level': data.readings.get('risk_levels', ['LOW'] * len(data.sensor_ids))
        })
        
        for param in ['rainfall_mm', 'water_level_cm', 'soil_moisture_percent', 'temperature_c']:
            if param in data.readings:
                values = data.readings[param]
                if isinstance(values, np.ndarray) and len(values.shape) > 1:
                    values = values[:, 0]
                df[param] = values
        
        # Plot 1: Sensor locations with risk levels
        fig, ax = plt.subplots(figsize=(10, 8))
        risk_levels = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
        colors = ['green', 'yellow', 'orange', 'red']
        
        for risk, color in zip(risk_levels, colors):
            mask = df['risk_level'] == risk
            if mask.any():
                ax.scatter(
                    df.loc[mask, 'longitude'],
                    df.loc[mask, 'latitude'],
                    c=color,
                    label=risk,
                    s=50,
                    alpha=0.7
                )
        
        ax.set_xlabel('Longitude')
        ax.set_ylabel('Latitude')
        ax.set_title(f'Sensor Locations by Risk Level ({data.scenario.value})')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plot_file = os.path.join(self.output_dir, f"{filename}_locations.png")
        plt.savefig(plot_file, dpi=150, bbox_inches='tight')
        plt.close()
        filepaths['locations'] = plot_file
        
        # Plot 2: Parameter distributions
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        axes = axes.flatten()
        
        param_names = ['rainfall_mm', 'water_level_cm', 'soil_moisture_percent', 'temperature_c']
        param_titles = ['Rainfall (mm)', 'Water Level (cm)', 'Soil Moisture (%)', 'Temperature (°C)']
        
        for idx, (param, title) in enumerate(zip(param_names, param_titles)):
            if param in df.columns:
                ax = axes[idx]
                ax.hist(df[param], bins=20, alpha=0.7, color='blue', edgecolor='black')
                ax.set_xlabel(title)
                ax.set_ylabel('Frequency')
                ax.set_title(f'{title} Distribution')
                ax.grid(True, alpha=0.3)
        
        plot_file = os.path.join(self.output_dir, f"{filename}_distributions.png")
        plt.tight_layout()
        plt.savefig(plot_file, dpi=150, bbox_inches='tight')
        plt.close()
        filepaths['distributions'] = plot_file
        
        # Plot 3: Risk score distribution
        fig, ax = plt.subplots(figsize=(8, 6))
        
        if 'risk_score' in df.columns:
            ax.hist(df['risk_score'], bins=20, alpha=0.7, color='red', edgecolor='black')
            ax.set_xlabel('Risk Score')
            ax.set_ylabel('Frequency')
            ax.set_title(f'Risk Score Distribution ({data.scenario.value})')
            ax.grid(True, alpha=0.3)
            
            # Add vertical lines for thresholds
            for threshold in [0.3, 0.5, 0.7]:
                ax.axvline(x=threshold, color='gray', linestyle='--', alpha=0.5)
            ax.text(0.15, ax.get_ylim()[1]*0.9, 'LOW', ha='center')
            ax.text(0.4, ax.get_ylim()[1]*0.9, 'MEDIUM', ha='center')
            ax.text(0.6, ax.get_ylim()[1]*0.9, 'HIGH', ha='center')
            ax.text(0.85, ax.get_ylim()[1]*0.9, 'CRITICAL', ha='center')
            
            plot_file = os.path.join(self.output_dir, f"{filename}_risk_scores.png")
            plt.savefig(plot_file, dpi=150, bbox_inches='tight')
            plt.close()
            filepaths['risk_scores'] = plot_file
        
        # Plot 4: Distance vs Risk Score
        fig, ax = plt.subplots(figsize=(8, 6))
        
        from app.pipeline.sensors.spatial_correlation import SpatialCorrelator
        correlator = SpatialCorrelator(self.config)
        distances = correlator.calculate_distances(data.locations)
        
        if 'risk_score' in df.columns:
            ax.scatter(distances, df['risk_score'], alpha=0.6)
            ax.set_xlabel('Distance from Flood Center (km)')
            ax.set_ylabel('Risk Score')
            ax.set_title(f'Risk Score vs Distance ({data.scenario.value})')
            ax.grid(True, alpha=0.3)
            
            plot_file = os.path.join(self.output_dir, f"{filename}_risk_vs_distance.png")
            plt.savefig(plot_file, dpi=150, bbox_inches='tight')
            plt.close()
            filepaths['risk_vs_distance'] = plot_file
        
        logger.info(f"Created static plots in {self.output_dir}")
        return filepaths
    
    def create_all_visualizations(self, 
                                 data: ScenarioData,
                                 config: Any) -> Dict[str, str]:
        """
        Create all visualizations for sensor data.
        
        Args:
            data: ScenarioData object
            config: SensorConfig object
            
        Returns:
            Dictionary of all visualization file paths
        """
        self.config = config
        visualizations = {}
        
        # Create interactive risk map
        visualizations['risk_map'] = self.create_risk_map(data)
        
        # Create heatmaps for each parameter
        for param in ['rainfall_mm', 'water_level_cm', 'soil_moisture_percent']:
            if param in data.readings:
                visualizations[f'heatmap_{param}'] = self.create_heatmap(data, param)
        
        # Create static plots
        visualizations.update(self.create_static_plots(data))
        
        logger.info(f"Created {len(visualizations)} visualizations")
        return visualizations