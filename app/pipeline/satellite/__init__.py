"""
Satellite processing pipeline module.

This module handles satellite image processing for flood detection
including NDWI calculation, flood detection, change detection,
and metrics calculation.
"""

from app.pipeline.satellite.processor import SatelliteProcessor

__all__ = ["SatelliteProcessor"]