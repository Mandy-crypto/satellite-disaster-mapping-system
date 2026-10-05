# Sensor Simulation Module

Generates realistic synthetic sensor data for disaster mapping scenarios.

## Overview

This module simulates field sensor data for the Satellite-Assisted Disaster Mapping System. It generates spatially correlated sensor readings for three scenarios: NORMAL, WARNING, and CRITICAL.

## Features

- **Realistic Data Generation**: Spatially correlated readings with realistic noise
- **Three Scenarios**: NORMAL, WARNING, and CRITICAL flood conditions
- **Multiple Export Formats**: CSV, JSON, GeoJSON
- **Interactive Visualizations**: Folium maps, heatmaps, static plots
- **Configurable**: Geographic bounds, sensor count, flood center, noise levels
- **Reproducible**: Set random seed for consistent results

## Installation

```bash
pip install -r requirements.txt