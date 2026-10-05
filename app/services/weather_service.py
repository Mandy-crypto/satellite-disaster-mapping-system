"""
Weather Service - Fetches real-time weather data from OpenWeatherMap API
Replaces mock sensor data with live weather data
"""

import asyncio
import httpx
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
import json
import logging
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class WeatherReading:
    """Weather data matching SensorReading schema"""
    sensor_id: str
    latitude: float
    longitude: float
    timestamp: str
    rainfall_mm: float
    temperature_c: float
    humidity: float
    pressure_hpa: float
    wind_speed_mps: float
    weather_condition: str
    weather_icon: str
    source: str = "openweathermap"
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None


@dataclass
class WeatherForecast:
    """5-day weather forecast"""
    date: str
    temperature_min: float
    temperature_max: float
    rainfall_mm: float
    humidity: float
    wind_speed_mps: float
    weather_condition: str
    weather_icon: str


class WeatherService:
    """
    Service for fetching weather data from OpenWeatherMap API
    """
    
    def __init__(self):
        self.api_key = settings.OPENWEATHER_API_KEY
        self.base_url = "https://api.openweathermap.org/data/2.5"
        self.cache: Dict[str, List[WeatherReading]] = {}
        self.forecast_cache: Dict[str, List[WeatherForecast]] = {}
        self.last_update: Dict[str, datetime] = {}
        self._client: Optional[httpx.AsyncClient] = None
        self.is_running = False
        
        if not self.api_key:
            logger.warning("OPENWEATHER_API_KEY not set. Using mock data fallback.")
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=20)
            )
        return self._client
    
    async def fetch_current_weather(
        self, 
        lat: float, 
        lon: float, 
        sensor_id: str = "WEATHER_001"
    ) -> WeatherReading:
        """
        Fetch current weather for a location
        
        Args:
            lat: Latitude
            lon: Longitude
            sensor_id: Optional sensor ID
            
        Returns:
            WeatherReading object with current weather data
        """
        try:
            if not self.api_key:
                logger.warning("No API key, using mock data")
                return self._generate_mock_weather(lat, lon, sensor_id)
            
            client = await self._get_client()
            
            # Current weather endpoint
            url = f"{self.base_url}/weather"
            params = {
                "lat": lat,
                "lon": lon,
                "appid": self.api_key,
                "units": "metric"  # Celsius
            }
            
            response = await client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract data
            reading = WeatherReading(
                sensor_id=sensor_id,
                latitude=lat,
                longitude=lon,
                timestamp=datetime.now().isoformat(),
                rainfall_mm=data.get("rain", {}).get("1h", 0.0),
                temperature_c=data["main"]["temp"],
                humidity=data["main"]["humidity"],
                pressure_hpa=data["main"]["pressure"],
                wind_speed_mps=data["wind"]["speed"],
                weather_condition=data["weather"][0]["description"],
                weather_icon=data["weather"][0]["icon"],
                source="openweathermap"
            )
            
            # Calculate risk score based on weather
            reading.risk_score = self._calculate_risk_score(reading)
            reading.risk_level = self._get_risk_level(reading.risk_score)
            
            # Cache the reading
            cache_key = f"{lat:.4f},{lon:.4f}"
            if cache_key not in self.cache:
                self.cache[cache_key] = []
            self.cache[cache_key].append(reading)
            self.last_update[cache_key] = datetime.now()
            
            # Keep only last 100 readings per location
            if len(self.cache[cache_key]) > 100:
                self.cache[cache_key] = self.cache[cache_key][-100:]
            
            logger.info(f"✅ Fetched weather for ({lat}, {lon}): {reading.temperature_c}°C, {reading.rainfall_mm}mm")
            return reading
            
        except httpx.HTTPStatusError as e:
            logger.error(f"API error: {e.response.status_code} - {e.response.text}")
            return self._generate_mock_weather(lat, lon, sensor_id, error="api_error")
        except Exception as e:
            logger.error(f"Error fetching weather: {e}")
            return self._generate_mock_weather(lat, lon, sensor_id, error=str(e))
    
    async def fetch_forecast(
        self, 
        lat: float, 
        lon: float
    ) -> List[WeatherForecast]:
        """
        Fetch 5-day weather forecast
        
        Args:
            lat: Latitude
            lon: Longitude
            
        Returns:
            List of WeatherForecast objects
        """
        try:
            if not self.api_key:
                return self._generate_mock_forecast(lat, lon)
            
            client = await self._get_client()
            
            # Forecast endpoint (5 days, 3-hour intervals)
            url = f"{self.base_url}/forecast"
            params = {
                "lat": lat,
                "lon": lon,
                "appid": self.api_key,
                "units": "metric",
                "cnt": 40  # 5 days * 8 intervals
            }
            
            response = await client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # Process forecast data - get daily aggregates
            daily_data: Dict[str, List[Dict]] = {}
            
            for item in data["list"]:
                date = item["dt_txt"].split(" ")[0]  # YYYY-MM-DD
                if date not in daily_data:
                    daily_data[date] = []
                daily_data[date].append(item)
            
            forecasts = []
            for date, items in list(daily_data.items())[:5]:  # First 5 days
                temps = [i["main"]["temp"] for i in items]
                rainfalls = [i.get("rain", {}).get("3h", 0.0) for i in items]
                
                forecast = WeatherForecast(
                    date=date,
                    temperature_min=min(temps),
                    temperature_max=max(temps),
                    rainfall_mm=sum(rainfalls),
                    humidity=sum(i["main"]["humidity"] for i in items) / len(items),
                    wind_speed_mps=sum(i["wind"]["speed"] for i in items) / len(items),
                    weather_condition=items[0]["weather"][0]["description"],
                    weather_icon=items[0]["weather"][0]["icon"]
                )
                forecasts.append(forecast)
            
            # Cache forecast
            cache_key = f"{lat:.4f},{lon:.4f}"
            self.forecast_cache[cache_key] = forecasts
            
            logger.info(f"✅ Fetched forecast for ({lat}, {lon}): {len(forecasts)} days")
            return forecasts
            
        except Exception as e:
            logger.error(f"Error fetching forecast: {e}")
            return self._generate_mock_forecast(lat, lon)
    
    def _calculate_risk_score(self, reading: WeatherReading) -> float:
        """
        Calculate risk score based on weather conditions
        
        Factors:
        - Heavy rainfall (>50mm): high risk
        - High wind speed (>20m/s): high risk
        - Extreme temperatures: moderate risk
        """
        risk = 0.0
        
        # Rainfall risk (0-0.5)
        if reading.rainfall_mm > 0:
            risk += min(reading.rainfall_mm / 100, 0.5)
        
        # Wind risk (0-0.3)
        if reading.wind_speed_mps > 10:
            risk += min((reading.wind_speed_mps - 10) / 40, 0.3)
        
        # Temperature risk (0-0.2)
        if reading.temperature_c > 35:
            risk += min((reading.temperature_c - 35) / 15, 0.2)
        elif reading.temperature_c < 0:
            risk += min((0 - reading.temperature_c) / 10, 0.2)
        
        return min(risk, 1.0)
    
    def _get_risk_level(self, risk_score: float) -> str:
        """Convert risk score to risk level"""
        if risk_score >= 0.8:
            return "CRITICAL"
        elif risk_score >= 0.6:
            return "HIGH"
        elif risk_score >= 0.3:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _generate_mock_weather(
        self, 
        lat: float, 
        lon: float, 
        sensor_id: str,
        error: Optional[str] = None
    ) -> WeatherReading:
        """Generate mock weather data as fallback"""
        import random
        
        # Simulate realistic weather patterns
        temp = random.uniform(20, 35)
        humidity = random.uniform(40, 85)
        rainfall = random.uniform(0, 20) if random.random() > 0.7 else 0
        
        conditions = ["clear sky", "few clouds", "scattered clouds", "broken clouds", 
                      "light rain", "moderate rain", "overcast clouds"]
        
        reading = WeatherReading(
            sensor_id=sensor_id,
            latitude=lat,
            longitude=lon,
            timestamp=datetime.now().isoformat(),
            rainfall_mm=rainfall,
            temperature_c=temp,
            humidity=humidity,
            pressure_hpa=random.uniform(1000, 1025),
            wind_speed_mps=random.uniform(0, 15),
            weather_condition=random.choice(conditions),
            weather_icon="01d",
            source="mock_fallback" if error else "mock"
        )
        
        reading.risk_score = self._calculate_risk_score(reading)
        reading.risk_level = self._get_risk_level(reading.risk_score)
        
        return reading
    
    def _generate_mock_forecast(self, lat: float, lon: float) -> List[WeatherForecast]:
        """Generate mock forecast data"""
        import random
        
        forecasts = []
        for i in range(5):
            date = (datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d")
            forecasts.append(
                WeatherForecast(
                    date=date,
                    temperature_min=random.uniform(18, 25),
                    temperature_max=random.uniform(28, 38),
                    rainfall_mm=random.uniform(0, 15) if random.random() > 0.6 else 0,
                    humidity=random.uniform(40, 80),
                    wind_speed_mps=random.uniform(2, 12),
                    weather_condition=random.choice(["sunny", "partly cloudy", "cloudy", "light rain"]),
                    weather_icon="01d"
                )
            )
        return forecasts
    
    async def get_weather(
        self, 
        lat: float, 
        lon: float,
        use_cache: bool = True
    ) -> WeatherReading:
        """
        Get weather data (with caching)
        
        Args:
            lat: Latitude
            lon: Longitude
            use_cache: Whether to use cached data if available
            
        Returns:
            WeatherReading object
        """
        cache_key = f"{lat:.4f},{lon:.4f}"
        
        # Check cache (5 minute TTL)
        if use_cache and cache_key in self.cache and self.cache[cache_key]:
            last = self.last_update.get(cache_key)
            if last and (datetime.now() - last).seconds < 300:  # 5 minutes
                return self.cache[cache_key][-1]
        
        # Fetch fresh data
        return await self.fetch_current_weather(lat, lon)
    
    async def start_background_updates(
        self, 
        locations: List[tuple],
        interval_minutes: int = 5
    ):
        """
        Start background task to update weather data periodically
        
        Args:
            locations: List of (lat, lon) tuples
            interval_minutes: Update interval in minutes
        """
        if self.is_running:
            logger.warning("Background updates already running")
            return
        
        self.is_running = True
        logger.info(f"🚀 Starting background weather updates every {interval_minutes} minutes")
        
        while self.is_running:
            try:
                for lat, lon in locations:
                    await self.fetch_current_weather(lat, lon)
                logger.info(f"✅ Updated weather for {len(locations)} locations")
            except Exception as e:
                logger.error(f"Background update failed: {e}")
            
            await asyncio.sleep(interval_minutes * 60)
    
    def stop_background_updates(self):
        """Stop background updates"""
        self.is_running = False
        logger.info("🛑 Stopped background weather updates")
    
    async def close(self):
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def check_alerts(self, reading: WeatherReading) -> Optional[Dict[str, Any]]:
        """
        Check if weather conditions trigger alerts
        
        Returns:
            Alert dict if conditions are severe, None otherwise
        """
        alerts = []
        
        # Heavy rainfall alert (>50mm)
        if reading.rainfall_mm > 50:
            alerts.append({
                "type": "HEAVY_RAINFALL",
                "severity": "CRITICAL" if reading.rainfall_mm > 100 else "HIGH",
                "message": f"⚠️ Heavy rainfall detected: {reading.rainfall_mm:.1f}mm in last hour",
                "value": reading.rainfall_mm,
                "threshold": 50
            })
        
        # High wind alert (>20m/s)
        if reading.wind_speed_mps > 20:
            alerts.append({
                "type": "HIGH_WIND",
                "severity": "CRITICAL" if reading.wind_speed_mps > 30 else "HIGH",
                "message": f"💨 High wind speed: {reading.wind_speed_mps:.1f} m/s",
                "value": reading.wind_speed_mps,
                "threshold": 20
            })
        
        # Extreme temperature alert
        if reading.temperature_c > 40:
            alerts.append({
                "type": "EXTREME_HEAT",
                "severity": "HIGH",
                "message": f"🌡️ Extreme heat: {reading.temperature_c:.1f}°C",
                "value": reading.temperature_c,
                "threshold": 40
            })
        elif reading.temperature_c < 0:
            alerts.append({
                "type": "FREEZING",
                "severity": "HIGH",
                "message": f"❄️ Freezing temperature: {reading.temperature_c:.1f}°C",
                "value": reading.temperature_c,
                "threshold": 0
            })
        
        if alerts:
            return {
                "location": {"lat": reading.latitude, "lon": reading.longitude},
                "timestamp": reading.timestamp,
                "alerts": alerts,
                "total_severity": max(a["severity"] for a in alerts)
            }
        
        return None


# ============================================
# SINGLETON INSTANCE
# ============================================
_weather_service: Optional[WeatherService] = None


def get_weather_service() -> WeatherService:
    """Get or create weather service singleton"""
    global _weather_service
    if _weather_service is None:
        _weather_service = WeatherService()
    return _weather_service
