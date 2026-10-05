"""
USGS Service - Fetches real-time earthquake and water data from USGS APIs
Integrates with existing disaster mapping system
"""

import os
import asyncio
import httpx
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, asdict
import json
import logging
import math
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class EarthquakeEvent:
    """Earthquake data matching Alert schema"""
    alert_id: str
    event_id: str
    magnitude: float
    place: str
    latitude: float
    longitude: float
    depth_km: float
    time: str
    url: str
    status: str
    tsunami: int
    sig: int
    alert_level: str  # CRITICAL/HIGH/MEDIUM/LOW based on magnitude
    message: str
    generated_at: str
    source: str = "usgs"


@dataclass
class WaterLevelReading:
    """Water level data for river/stations"""
    station_id: str
    station_name: str
    latitude: float
    longitude: float
    water_level_m: float
    water_level_cm: float
    discharge_cfs: Optional[float]
    timestamp: str
    flood_stage_m: float
    action_stage_m: float
    stage_status: str  # NORMAL/ACTION/FLOOD/MAJOR_FLOOD
    risk_score: float
    risk_level: str
    source: str = "usgs_waterdata"


@dataclass
class CombinedRisk:
    """Combined risk from earthquake + water data"""
    location_id: str
    latitude: float
    longitude: float
    earthquake_risk: float
    water_risk: float
    combined_risk: float
    risk_level: str
    alerts: List[Dict[str, Any]]
    timestamp: str


class USGSService:
    """
    Service for fetching USGS earthquake and water data
    """
    
    def __init__(self):
        self.earthquake_url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson"
        self.water_url = "https://waterservices.usgs.gov/nwis/iv/"
        # Optional JSON object keyed by USGS site ID. Each value may define
        # action_stage_m and flood_stage_m for locally calibrated warnings.
        try:
            configured_stations = settings.USGS_WATER_STATIONS
            self.water_station_config = json.loads(configured_stations)
        except json.JSONDecodeError:
            logger.error("USGS_WATER_STATIONS must be valid JSON; water feed disabled")
            self.water_station_config = {}
        self._client: Optional[httpx.AsyncClient] = None
        
        # Cache
        self.earthquake_cache: List[EarthquakeEvent] = []
        self.water_cache: List[WaterLevelReading] = []
        self.combined_risk_cache: List[CombinedRisk] = []
        self.last_earthquake_update: Optional[datetime] = None
        self.last_water_update: Optional[datetime] = None
        
        # Background task flags
        self.is_earthquake_running = False
        self.is_water_running = False
        
        # Default locations to monitor
        self.monitored_locations = [
            {"lat": 23.181, "lon": 79.951, "name": "Bhopal"},
            {"lat": 28.6139, "lon": 77.2090, "name": "Delhi"},
            {"lat": 19.0760, "lon": 72.8777, "name": "Mumbai"},
        ]
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=30)
            )
        return self._client
    
    # ============================================
    # EARTHQUAKE METHODS
    # ============================================
    
    async def fetch_earthquakes(self) -> List[EarthquakeEvent]:
        """
        Fetch earthquakes from USGS API
        Filters: magnitude > 2.5
        """
        try:
            client = await self._get_client()
            response = await client.get(self.earthquake_url)
            response.raise_for_status()
            
            data = response.json()
            features = data.get("features", [])
            
            earthquakes = []
            for feature in features:
                props = feature.get("properties", {})
                geometry = feature.get("geometry", {})
                coords = geometry.get("coordinates", [0, 0, 0])
                
                mag = props.get("mag", 0)
                
                # Filter: magnitude > 2.5 (already filtered by USGS endpoint)
                if mag >= 2.5:
                    # Determine alert level based on magnitude
                    if mag >= 7.0:
                        alert_level = "CRITICAL"
                    elif mag >= 6.0:
                        alert_level = "HIGH"
                    elif mag >= 5.0:
                        alert_level = "MEDIUM"
                    else:
                        alert_level = "LOW"
                    
                    event = EarthquakeEvent(
                        alert_id=f"EQ_{props.get('code', 'unknown')}",
                        event_id=feature.get("id", "unknown"),
                        magnitude=mag,
                        place=props.get("place", "Unknown location"),
                        latitude=coords[1],
                        longitude=coords[0],
                        depth_km=coords[2] if len(coords) > 2 else 0,
                        time=datetime.fromtimestamp(props.get("time", 0) / 1000).isoformat(),
                        url=props.get("url", ""),
                        status=props.get("status", "unknown"),
                        tsunami=props.get("tsunami", 0),
                        sig=props.get("sig", 0),
                        alert_level=alert_level,
                        message=self._generate_earthquake_message(props),
                        generated_at=datetime.now().isoformat(),
                        source="usgs"
                    )
                    earthquakes.append(event)
            
            # Sort by magnitude (highest first)
            earthquakes.sort(key=lambda x: x.magnitude, reverse=True)
            
            # Update cache
            self.earthquake_cache = earthquakes
            self.last_earthquake_update = datetime.now()
            
            logger.info(f"✅ Fetched {len(earthquakes)} earthquakes from USGS")
            return earthquakes
            
        except httpx.HTTPStatusError as e:
            logger.error(f"USGS API error: {e.response.status_code}")
            return self.earthquake_cache  # Return cached data
        except Exception as e:
            logger.error(f"Error fetching earthquakes: {e}")
            return self.earthquake_cache
    
    def _generate_earthquake_message(self, props: Dict[str, Any]) -> str:
        """Generate alert message from earthquake data"""
        mag = props.get("mag", 0)
        place = props.get("place", "Unknown location")
        
        if mag >= 7.0:
            return f"⚠️ MAJOR EARTHQUAKE: M{mag:.1f} near {place}. Severe damage expected. Immediate evacuation recommended."
        elif mag >= 6.0:
            return f"🔴 STRONG EARTHQUAKE: M{mag:.1f} near {place}. Possible damage. Prepare for aftershocks."
        elif mag >= 5.0:
            return f"🟠 MODERATE EARTHQUAKE: M{mag:.1f} near {place}. Some damage possible. Monitor for updates."
        else:
            return f"🟡 MINOR EARTHQUAKE: M{mag:.1f} near {place}. Minor shaking reported. No damage expected."
    
    # ============================================
    # WATER DATA METHODS
    # ============================================
    
    async def fetch_water_levels(
        self, 
        lat: Optional[float] = None, 
        lon: Optional[float] = None,
        radius_km: float = 100
    ) -> List[WaterLevelReading]:
        """Fetch configured USGS gage sites; never fabricate observations."""
        sites = self.water_station_config
        if not isinstance(sites, dict) or not sites:
            logger.info("USGS water feed disabled: configure USGS_WATER_STATIONS with site IDs")
            return self.water_cache
        try:
            client = await self._get_client()
            response = await client.get(self.water_url, params={
                "format": "json", "sites": ",".join(sites.keys()),
                "parameterCd": "00060,00065", "period": "P1D", "siteStatus": "active",
            })
            response.raise_for_status()
            series = response.json().get("value", {}).get("timeSeries", [])
            by_site = {}
            for item in series:
                source = item.get("sourceInfo", {})
                site_code = str((source.get("siteCode") or [{}])[0].get("value", ""))
                variable = str((item.get("variable", {}).get("variableCode") or [{}])[0].get("value", ""))
                values = item.get("values", [{}])[0].get("value", [])
                if site_code and variable in {"00060", "00065"} and values:
                    by_site.setdefault(site_code, {})[variable] = (item, values[-1])

            readings = []
            for site_code, variables in by_site.items():
                stage_record = variables.get("00065")
                if not stage_record:
                    continue
                item, observation = stage_record
                source = item.get("sourceInfo", {})
                geo = source.get("geoLocation", {}).get("geogLocation", {})
                latitude, longitude = float(geo.get("latitude", 0)), float(geo.get("longitude", 0))
                if lat is not None and lon is not None and self._calculate_distance(lat, lon, latitude, longitude) > radius_km:
                    continue
                stage_m = float(observation.get("value", 0))
                if str(item.get("variable", {}).get("unit", {}).get("unitCode", "")).lower() in {"ft", "feet"}:
                    stage_m *= 0.3048
                station = sites.get(site_code, {}) if isinstance(sites.get(site_code), dict) else {}
                action = float(station.get("action_stage_m", 0) or 0)
                flood = float(station.get("flood_stage_m", 0) or 0)
                if flood > 0 and stage_m >= flood:
                    status, score = "MAJOR_FLOOD", 0.9
                elif action > 0 and stage_m >= action:
                    status, score = "FLOOD", 0.7
                elif action > 0 and stage_m >= action * 0.7:
                    status, score = "ACTION", 0.4
                else:
                    status, score = ("NORMAL", 0.1) if action > 0 else ("UNKNOWN", 0.0)
                discharge = None
                if "00060" in variables:
                    discharge = float(variables["00060"][1].get("value", 0))
                level = "CRITICAL" if score >= .8 else "HIGH" if score >= .6 else "MEDIUM" if score >= .3 else "LOW"
                readings.append(WaterLevelReading(
                    station_id=site_code, station_name=source.get("siteName", site_code),
                    latitude=latitude, longitude=longitude, water_level_m=round(stage_m, 3),
                    water_level_cm=round(stage_m * 100, 1), discharge_cfs=discharge,
                    timestamp=observation.get("dateTime", datetime.now().isoformat()),
                    flood_stage_m=flood, action_stage_m=action, stage_status=status,
                    risk_score=score, risk_level=level,
                ))
            self.water_cache = readings
            self.last_water_update = datetime.now()
            logger.info("Fetched %s configured USGS gage readings", len(readings))
            return readings
        except httpx.HTTPStatusError as e:
            logger.error("USGS water API error: %s", e.response.status_code)
            return self.water_cache
        except Exception as e:
            logger.error(f"Error fetching water data: {e}")
            return self.water_cache
    
    # ALERT CHECKING
    # ============================================
    
    async def check_earthquake_alerts(self, lat: float, lon: float, radius_km: float = 100) -> List[Dict[str, Any]]:
        """
        Check for earthquakes near a specific location
        """
        alerts = []
        
        for eq in self.earthquake_cache:
            # Calculate distance
            dist = self._calculate_distance(lat, lon, eq.latitude, eq.longitude)
            
            if dist <= radius_km and eq.magnitude >= 4.0:
                alerts.append({
                    "alert_id": eq.alert_id,
                    "type": "EARTHQUAKE",
                    "severity": eq.alert_level,
                    "message": eq.message,
                    "magnitude": eq.magnitude,
                    "distance_km": round(dist, 1),
                    "location": {"lat": eq.latitude, "lon": eq.longitude},
                    "timestamp": eq.time
                })
        
        return alerts
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance in km between two points"""
        R = 6371  # Earth's radius in km
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c
    
    # ============================================
    # COMBINED RISK
    # ============================================
    
    async def calculate_combined_risk(self, lat: float, lon: float) -> CombinedRisk:
        """
        Calculate combined risk from earthquake + water data
        """
        # Get earthquake risk near location
        earthquake_alerts = await self.check_earthquake_alerts(lat, lon)
        earthquake_risk = 0.0
        if earthquake_alerts:
            # Highest magnitude within radius
            max_mag = max([a.get("magnitude", 0) for a in earthquake_alerts])
            earthquake_risk = min(max_mag / 10.0, 1.0)  # Normalize to 0-1
        
        # Get water risk near location
        water_alerts = []
        for water in self.water_cache:
            dist = self._calculate_distance(lat, lon, water.latitude, water.longitude)
            if dist <= 50:  # 50km radius
                water_alerts.append(water)
        
        water_risk = 0.0
        for w in water_alerts:
            water_risk = max(water_risk, w.risk_score)
        
        # Combined risk (weighted average)
        combined_risk = (earthquake_risk * 0.4 + water_risk * 0.6)
        
        # Determine risk level
        if combined_risk >= 0.8:
            risk_level = "CRITICAL"
        elif combined_risk >= 0.6:
            risk_level = "HIGH"
        elif combined_risk >= 0.3:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        # Combine all alerts
        all_alerts = earthquake_alerts + [
            {
                "alert_id": f"WATER_{w.station_id}",
                "type": "WATER_LEVEL",
                "severity": w.risk_level,
                "message": f"⚠️ {w.station_name}: Water level at {w.water_level_cm}cm ({w.stage_status})",
                "water_level_cm": w.water_level_cm,
                "stage_status": w.stage_status,
                "location": {"lat": w.latitude, "lon": w.longitude},
                "timestamp": w.timestamp
            }
            for w in water_alerts if w.risk_score > 0.3
        ]
        
        # Create combined risk object
        combined = CombinedRisk(
            location_id=f"RISK_{lat:.4f}_{lon:.4f}",
            latitude=lat,
            longitude=lon,
            earthquake_risk=round(earthquake_risk, 2),
            water_risk=round(water_risk, 2),
            combined_risk=round(combined_risk, 2),
            risk_level=risk_level,
            alerts=all_alerts,
            timestamp=datetime.now().isoformat()
        )
        
        # Cache
        self.combined_risk_cache.append(combined)
        if len(self.combined_risk_cache) > 100:
            self.combined_risk_cache = self.combined_risk_cache[-100:]
        
        return combined
    
    # ============================================
    # BACKGROUND TASKS
    # ============================================
    
    async def start_earthquake_updates(self, interval_minutes: int = 10):
        """Start background earthquake updates"""
        if self.is_earthquake_running:
            logger.warning("Earthquake updates already running")
            return
        
        self.is_earthquake_running = True
        logger.info(f"🚀 Starting earthquake updates every {interval_minutes} minutes")
        
        while self.is_earthquake_running:
            try:
                await self.fetch_earthquakes()
                logger.info(f"✅ Earthquake update complete: {len(self.earthquake_cache)} events")
            except Exception as e:
                logger.error(f"Earthquake update failed: {e}")
            
            await asyncio.sleep(interval_minutes * 60)
    
    async def start_water_updates(self, interval_minutes: int = 15):
        """Start background water level updates"""
        if self.is_water_running:
            logger.warning("Water updates already running")
            return
        
        self.is_water_running = True
        logger.info(f"🚀 Starting water level updates every {interval_minutes} minutes")
        
        while self.is_water_running:
            try:
                await self.fetch_water_levels()
                logger.info(f"✅ Water update complete: {len(self.water_cache)} readings")
            except Exception as e:
                logger.error(f"Water update failed: {e}")
            
            await asyncio.sleep(interval_minutes * 60)
    
    def stop_earthquake_updates(self):
        """Stop earthquake background updates"""
        self.is_earthquake_running = False
        logger.info("🛑 Stopped earthquake updates")
    
    def stop_water_updates(self):
        """Stop water background updates"""
        self.is_water_running = False
        logger.info("🛑 Stopped water updates")
    
    async def close(self):
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None


# ============================================
# SINGLETON INSTANCE
# ============================================
_usgs_service: Optional[USGSService] = None


def get_usgs_service() -> USGSService:
    """Get or create USGS service singleton"""
    global _usgs_service
    if _usgs_service is None:
        _usgs_service = USGSService()
    return _usgs_service
