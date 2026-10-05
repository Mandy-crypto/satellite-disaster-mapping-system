"""Compatibility facade around the real satellite and sensor processors."""

from datetime import datetime, timezone
from time import perf_counter
from typing import Any
import logging

logger = logging.getLogger(__name__)


class DataProcessor:
    """Legacy service facade that delegates work to project pipelines."""

    def __init__(self):
        self.processing_times: dict[str, float] = {}
        self.error_count = 0

    def process_satellite_data(self, image_data: dict[str, Any]) -> dict[str, Any]:
        image_path = image_data.get("image_path") or image_data.get("path")
        if not image_path:
            return {"status": "failed", "error": "image_path is required", "processed_at": _now()}
        started = perf_counter()
        try:
            from app.pipeline.satellite.processor import SatelliteProcessor
            result = SatelliteProcessor().process_image(
                image_path,
                image_data.get("before_image_path"),
                image_data.get("threshold"),
                image_data.get("location"),
            )
            if result.get("status") != "success":
                self.error_count += 1
            self.processing_times[str(image_data.get("image_id") or image_path)] = perf_counter() - started
            return result
        except Exception as exc:
            self.error_count += 1
            logger.exception("Satellite processing failed")
            return {"status": "failed", "error": str(exc), "processed_at": _now()}

    def process_sensor_data(self, sensor_data: list[dict[str, Any]]) -> dict[str, Any]:
        started = perf_counter()
        anomalies = []
        totals = {"rainfall_mm": 0.0, "water_level_cm": 0.0, "soil_moisture_percent": 0.0}
        for reading in sensor_data:
            values = reading.get("readings", reading)
            for key in totals:
                try:
                    totals[key] += float(values.get(key, 0) or 0)
                except (TypeError, ValueError):
                    continue
            try:
                temperature = float(values.get("temperature_c", values.get("temperature", 0)) or 0)
            except (TypeError, ValueError):
                temperature = 0.0
            try:
                water_level = float(values.get("water_level_cm", 0) or 0)
            except (TypeError, ValueError):
                water_level = 0.0
            if temperature > 40:
                anomalies.append({"sensor_id": reading.get("sensor_id"), "type": "temperature_spike",
                                  "value": values.get("temperature_c", values.get("temperature")),
                                  "timestamp": reading.get("timestamp")})
            if water_level >= 150:
                anomalies.append({"sensor_id": reading.get("sensor_id"), "type": "high_water_level",
                                  "value": values.get("water_level_cm"), "timestamp": reading.get("timestamp")})
        self.processing_times["sensor_batch"] = perf_counter() - started
        count = len(sensor_data)
        return {"status": "completed", "processed_at": _now(), "anomalies_detected": anomalies,
                "data_summary": {"total_readings": count, "anomalies_found": len(anomalies),
                                 "averages": {key: value / count for key, value in totals.items()} if count else {}}}

    def get_statistics(self) -> dict[str, Any]:
        durations = list(self.processing_times.values())
        return {"total_processes": len(durations),
                "average_processing_time_seconds": sum(durations) / len(durations) if durations else 0.0,
                "max_processing_time_seconds": max(durations) if durations else 0.0,
                "error_count": self.error_count}


def _now():
    return datetime.now(timezone.utc).isoformat()


processor = DataProcessor()
process_image = processor.process_satellite_data
process_sensor_readings = processor.process_sensor_data
get_processor_stats = processor.get_statistics

__all__ = ["DataProcessor", "processor", "process_image", "process_sensor_readings", "get_processor_stats"]
