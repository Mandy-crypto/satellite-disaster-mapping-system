"""Adapters for openly accessible government observation feeds."""

import asyncio
import json
import logging
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

logger = logging.getLogger(__name__)

NWIC_API = "https://nwdp.nwic.gov.in/api/3/action"
# NWIC CWC Narmada basin, 2026-2030 telemetry resource. It publishes station
# metadata and timestamped gauge-level observations through CKAN DataStore.
NWIC_NARMADA_RESOURCE = "a2e056f6-ed8a-45bf-9142-01dc1904405a"
IMD_API = "https://api.imd.gov.in/api/v1"


class PublicDataService:
    def __init__(self):
        self._client: httpx.AsyncClient | None = None
        self._river_cache: list[dict[str, Any]] = []
        self._river_cache_at: datetime | None = None
        self._river_lock = asyncio.Lock()

    async def _get_client(self):
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(30, connect=10),
                                              headers={"User-Agent": "disaster-mapping-dashboard/2.1"},
                                              follow_redirects=True)
        return self._client

    async def current_weather(self, lat: float, lon: float) -> dict[str, Any]:
        client = await self._get_client()
        response = await client.get("https://api.open-meteo.com/v1/forecast", params={
            "latitude": lat, "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,weather_code",
            "hourly": "precipitation", "forecast_days": 1, "timezone": "auto",
        })
        response.raise_for_status()
        payload = response.json()
        current = payload.get("current", {})
        hourly = payload.get("hourly", {})
        rainfall = 0.0
        times = hourly.get("time", [])
        precipitation = hourly.get("precipitation", [])
        if current.get("time") in times:
            rainfall = float(precipitation[times.index(current["time"])] or 0)
        return {
            "temperature_c": current.get("temperature_2m"),
            "humidity": current.get("relative_humidity_2m"),
            "pressure_hpa": None,
            "wind_speed_mps": round(float(current["wind_speed_10m"]) / 3.6, 2) if current.get("wind_speed_10m") is not None else None,
            "rainfall_mm": current.get("precipitation", rainfall),
            "weather_condition": _weather_code(current.get("weather_code")),
            "weather_icon": None,
            "source": "Open-Meteo (model-based, not a local station observation)",
            "source_url": "https://open-meteo.com/en/docs",
            "observed_at": current.get("time"),
            "timezone": payload.get("timezone"),
            "elevation_m": payload.get("elevation"),
            "risk_score": None,
            "risk_level": None,
        }

    async def weather_forecast(self, lat: float, lon: float, days: int = 5) -> list[dict[str, Any]]:
        client = await self._get_client()
        response = await client.get("https://api.open-meteo.com/v1/forecast", params={
            "latitude": lat, "longitude": lon,
            "daily": "temperature_2m_min,temperature_2m_max,precipitation_sum,precipitation_probability_max,wind_speed_10m_max",
            "forecast_days": days, "timezone": "auto",
        })
        response.raise_for_status()
        daily = response.json().get("daily", {})
        return [{
            "date": date,
            "temperature_min": _at(daily, "temperature_2m_min", index),
            "temperature_max": _at(daily, "temperature_2m_max", index),
            "rainfall_mm": _at(daily, "precipitation_sum", index),
            "precipitation_probability_percent": _at(daily, "precipitation_probability_max", index),
            "humidity": None,
            "wind_speed_mps": round(_at(daily, "wind_speed_10m_max", index) / 3.6, 2) if _at(daily, "wind_speed_10m_max", index) is not None else None,
            "weather_condition": "Forecast",
            "source": "Open-Meteo forecast model",
        } for index, date in enumerate(daily.get("time", []))]

    async def cwc_river_levels(self, lat: float, lon: float, radius_km: float = 250) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        async with self._river_lock:
            if self._river_cache_at and now - self._river_cache_at < timedelta(minutes=30):
                records = self._river_cache
            else:
                client = await self._get_client()
                response = await client.get(f"{NWIC_API}/datastore_search", params={
                    "resource_id": NWIC_NARMADA_RESOURCE,
                    "filters": json.dumps({"State": "Madhya Pradesh"}),
                    # The resource contains thousands of hourly rows for only a
                    # handful of stations. Fetch the most recent page instead of
                    # transferring the full history on every dashboard refresh.
                    "sort": "Data Acquisition Time desc",
                    "limit": 1000,
                })
                response.raise_for_status()
                payload = response.json()
                if not payload.get("success"):
                    raise RuntimeError("NWIC CWC telemetry query failed")
                records = _latest_station_rows(payload.get("result", {}).get("records", []))
                self._river_cache = records
                self._river_cache_at = now

        stations = []
        for record in records:
            try:
                station_lat = float(record["Latitude"])
                station_lon = float(record["Longitude"])
                distance = _distance_km(lat, lon, station_lat, station_lon)
                if distance > radius_km:
                    continue
                stations.append({
                    "station_id": str(record.get("Station", "")).strip(),
                    "station_name": str(record.get("Station", "")).strip(),
                    "river": str(record.get("River", "Narmada")).strip(),
                    "basin": str(record.get("Basin", "Narmada")).strip(),
                    "state": str(record.get("State", "Madhya Pradesh")).strip(),
                    "district": str(record.get("District", "")).strip(),
                    "latitude": station_lat,
                    "longitude": station_lon,
                    # CWC reports gauge elevation in metres relative to the
                    # station datum; it is not water depth or flood-stage status.
                    "gauge_level_m": float(record["River Water Level Telemetry Hourly (meter)"]),
                    "gauge_zero_elevation_m": _optional_float(record.get("RL_of_zeroGauge")),
                    "timestamp": _parse_cwc_time(record.get("Data Acquisition Time")),
                    "stale": _is_stale(_parse_cwc_time(record.get("Data Acquisition Time")), now),
                    "distance_km": round(distance, 1),
                    "source": "Central Water Commission via NWIC",
                    "source_url": "https://www.nwdp.nwic.gov.in/en/dataset/river-water-level-telemetry-hourly-central-water-commission-cwc",
                    "risk_level": None,
                })
            except (KeyError, TypeError, ValueError):
                continue
        stations.sort(key=lambda station: station["distance_km"])
        return {"status": "success", "count": len(stations), "stations": stations,
                "basin": "Narmada", "coverage": "Narmada basin stations in Madhya Pradesh",
                "requested_radius_km": radius_km, "retrieved_at": now.isoformat(),
                "note": "Gauge elevation is not flood depth. Compare only with station-specific CWC warning levels; data timestamps show the source observation time."}

    async def imd_stations(self, api_key: str, state_id: int = 27) -> dict[str, Any]:
        """Retrieve IMD AWS/ARG observations for a state using an IMD-issued key."""
        if not api_key:
            return {"status": "unconfigured", "source": "India Meteorological Department",
                    "message": "IMD_API_KEY is not configured. Register with IMD API Management to obtain access.", "stations": []}
        client = await self._get_client()
        response = await client.get(f"{IMD_API}/aws_data", params={"sid": state_id},
                                    headers={"Authorization": f"Bearer {api_key}", "x-api-key": api_key})
        response.raise_for_status()
        payload = response.json()
        records = payload if isinstance(payload, list) else payload.get("data", payload.get("stations", []))
        if isinstance(records, dict):
            records = list(records.values())
        stations = []
        for row in records if isinstance(records, list) else []:
            if not isinstance(row, dict):
                continue
            try:
                stations.append({
                    "station_id": row.get("ID") or row.get("CALL_SIGN"),
                    "station_name": row.get("STATION") or row.get("Station"),
                    "district": row.get("DISTRICT") or row.get("District"),
                    "state": row.get("STATE") or row.get("State"),
                    "latitude": float(row.get("Latitude", row.get("LATITUDE"))),
                    "longitude": float(row.get("Longitude", row.get("LONGITUDE"))),
                    "temperature_c": _optional_float(row.get("CURR_TEMP", row.get("Temperature"))),
                    "humidity_percent": _optional_float(row.get("RH", row.get("Humidity"))),
                    "rainfall_24h_mm": _optional_float(row.get("RAINFALL", row.get("Last 24 hrs Rainfall"))),
                    "wind_speed_kmh": _optional_float(row.get("WIND_SPEED", row.get("Wind Speed"))),
                    "observed_at": " ".join(str(row.get(k, "")).strip() for k in ("DATE", "TIME") if row.get(k)) or row.get("Date of Observation"),
                    "source": "India Meteorological Department AWS/ARG",
                })
            except (TypeError, ValueError):
                continue
        return {"status": "success", "count": len(stations), "stations": stations,
                "source": "India Meteorological Department AWS/ARG",
                "source_url": "https://api.imd.gov.in/public/api_reference.html"}

    async def imd_warnings(self, api_key: str) -> dict[str, Any]:
        if not api_key:
            return {"status": "unconfigured", "source": "India Meteorological Department",
                    "message": "IMD_API_KEY is not configured. Register with IMD API Management to obtain access.", "warnings": []}
        client = await self._get_client()
        response = await client.get(f"{IMD_API}/districtwarning", headers={"Authorization": f"Bearer {api_key}", "x-api-key": api_key})
        response.raise_for_status()
        payload = response.json()
        warnings = payload if isinstance(payload, list) else payload.get("data", payload.get("warnings", []))
        if isinstance(warnings, dict):
            warnings = list(warnings.values())
        return {"status": "success", "count": len(warnings) if isinstance(warnings, list) else 0,
                "warnings": warnings if isinstance(warnings, list) else [],
                "source": "India Meteorological Department district warnings",
                "source_url": "https://api.imd.gov.in/public/api_reference.html"}


def _latest_station_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latest = {}
    for row in records:
        station = str(row.get("Station", "")).strip()
        stamp = _parse_cwc_time(row.get("Data Acquisition Time"))
        if not station or not stamp:
            continue
        if station not in latest or stamp > latest[station][0]:
            latest[station] = (stamp, row)
    return [row for _, row in latest.values()]


def _parse_cwc_time(value: Any) -> str | None:
    if not value:
        return None
    try:
        parsed = datetime.strptime(str(value).strip(), "%d-%m-%Y %H:%M")
        return parsed.replace(tzinfo=ZoneInfo("Asia/Kolkata")).isoformat()
    except ValueError:
        try:
            return datetime.fromisoformat(str(value).strip()).isoformat()
        except ValueError:
            return None


def _is_stale(timestamp: str | None, now: datetime) -> bool:
    if not timestamp:
        return True
    parsed = datetime.fromisoformat(timestamp)
    return now - parsed.astimezone(timezone.utc) > timedelta(hours=24)


def _optional_float(value: Any):
    try:
        return float(value) if value not in (None, "", "-", "NA", "N/A") else None
    except (ValueError, TypeError):
        return None


def _at(payload: dict, key: str, index: int):
    values = payload.get(key, [])
    return values[index] if index < len(values) else None


def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float):
    from math import asin, cos, radians, sin, sqrt
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
    arc = 2 * asin(sqrt(sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2))
    return 6371.0088 * arc


def _weather_code(code: Any):
    if code is None:
        return "Unknown"
    code = int(code)
    if code == 0: return "Clear sky"
    if code in (1, 2, 3): return "Partly cloudy"
    if code in (45, 48): return "Fog"
    if code in (51, 53, 55, 56, 57): return "Drizzle"
    if code in (61, 63, 65, 66, 67): return "Rain"
    if code in (71, 73, 75, 77): return "Snow"
    if code in (80, 81, 82): return "Rain showers"
    if code in (85, 86): return "Snow showers"
    if code in (95, 96, 99): return "Thunderstorm"
    return "Unknown"


public_data_service = PublicDataService()
