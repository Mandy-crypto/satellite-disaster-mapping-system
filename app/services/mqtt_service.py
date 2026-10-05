"""
MQTT Service - Real hardware sensor integration
"""

import json
import logging
import threading
import time
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict

import paho.mqtt.client as mqtt
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class MQTTSensorReading:
    sensor_id: str
    latitude: float
    longitude: float
    timestamp: str
    rainfall_mm: float
    water_level_cm: float
    soil_moisture_percent: float
    temperature_c: float
    battery_percent: Optional[float] = None
    signal_strength: Optional[int] = None
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    received_at: str = None
    
    def __post_init__(self):
        if self.received_at is None:
            self.received_at = datetime.now().isoformat()


class MQTTService:
    def __init__(
        self,
        broker_host: str = "localhost",
        broker_port: int = 1883,
        topic: str = "sensor/data",
        client_id: str = "disaster_mapping"
    ):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.topic = topic
        self.client_id = client_id
        
        self.sensor_data: Dict[str, List[MQTTSensorReading]] = {}
        self.latest_readings: Dict[str, MQTTSensorReading] = {}
        self.total_messages = 0
        self.last_message_time: Optional[datetime] = None
        
        self.connected = False
        self.connecting = False
        self._stop_flag = False
        
        self.client = None
        self._reconnect_thread = None
        self.ws_subscribers = []
        
        # Create and connect client immediately
        self._setup_client()
        
        logger.info(f"📡 MQTT Service initialized: {broker_host}:{broker_port}")
    
    def _setup_client(self):
        """Setup MQTT client with callbacks"""
        self.client = mqtt.Client(
            client_id=self.client_id, 
            clean_session=True,
            callback_api_version=mqtt.CallbackAPIVersion.VERSION1
        )
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
    
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            self.connecting = False
            logger.info(f"✅ Connected to MQTT broker")
            # Subscribe to topics
            client.subscribe(self.topic)
            logger.info(f"📡 Subscribed to: {self.topic}")
            client.subscribe("sensor/status")
            logger.info(f"📡 Subscribed to: sensor/status")
        else:
            self.connected = False
            logger.error(f"❌ Failed to connect (rc: {rc})")
    
    def _on_disconnect(self, client, userdata, rc):
        self.connected = False
        logger.warning(f"⚠️ Disconnected from MQTT broker")
        if not self._stop_flag:
            self._schedule_reconnect()
    
    def _on_message(self, client, userdata, msg):
        try:
            self.total_messages += 1
            self.last_message_time = datetime.now()
            
            payload = msg.payload.decode('utf-8')
            logger.info(f"📨 Received on {msg.topic}: {payload[:100]}...")
            
            try:
                data = json.loads(payload)
            except json.JSONDecodeError as e:
                logger.error(f"❌ Invalid JSON: {e}")
                logger.error(f"   Payload: {payload}")
                return
            
            if msg.topic == self.topic:
                self._process_sensor_data(data)
                
        except Exception as e:
            logger.error(f"❌ Error processing MQTT message: {e}")
    
    def _process_sensor_data(self, data: Dict[str, Any]):
        try:
            required = ["sensor_id", "latitude", "longitude", "timestamp"]
            if not all(k in data for k in required):
                logger.warning(f"⚠️ Missing required fields: {list(data.keys())}")
                return
            
            reading = MQTTSensorReading(
                sensor_id=data["sensor_id"],
                latitude=data["latitude"],
                longitude=data["longitude"],
                timestamp=data["timestamp"],
                rainfall_mm=float(data.get("rainfall_mm", 0.0)),
                water_level_cm=float(data.get("water_level_cm", 0.0)),
                soil_moisture_percent=float(data.get("soil_moisture_percent", 0.0)),
                temperature_c=float(data.get("temperature_c", 0.0)),
                battery_percent=data.get("battery_percent"),
                signal_strength=data.get("signal_strength"),
                received_at=datetime.now().isoformat()
            )
            
            reading.risk_score = self._calculate_risk_score(reading)
            reading.risk_level = self._get_risk_level(reading.risk_score)
            
            sensor_id = reading.sensor_id
            if sensor_id not in self.sensor_data:
                self.sensor_data[sensor_id] = []
            
            self.sensor_data[sensor_id].append(reading)
            
            if len(self.sensor_data[sensor_id]) > 100:
                self.sensor_data[sensor_id] = self.sensor_data[sensor_id][-100:]
            
            self.latest_readings[sensor_id] = reading

            # Preserve live telemetry so dashboards and risk summaries can
            # recover it after a service restart (MQTT's in-memory history is
            # still kept as a short hot cache).
            try:
                from app.services.repository import add_reading
                stored = asdict(reading)
                stored["source"] = "mqtt"
                add_reading(stored)
            except Exception:
                logger.exception("Could not persist MQTT reading from %s", sensor_id)
            
            self._notify_subscribers(reading)
            
            logger.info(f"✅ Sensor {sensor_id}: {reading.temperature_c}°C, Risk={reading.risk_level}")
            
        except Exception as e:
            logger.error(f"❌ Error processing sensor data: {e}")
    
    def _calculate_risk_score(self, reading: MQTTSensorReading) -> float:
        risk = 0.0
        if reading.rainfall_mm > 0:
            risk += min(reading.rainfall_mm / 100, 0.4)
        if reading.water_level_cm > 0:
            risk += min(reading.water_level_cm / 200, 0.4)
        if reading.soil_moisture_percent > 50:
            risk += min((reading.soil_moisture_percent - 50) / 50, 0.2)
        return min(risk, 1.0)
    
    def _get_risk_level(self, risk_score: float) -> str:
        if risk_score >= 0.8:
            return "CRITICAL"
        elif risk_score >= 0.6:
            return "HIGH"
        elif risk_score >= 0.3:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _schedule_reconnect(self):
        if self._reconnect_thread is None or not self._reconnect_thread.is_alive():
            self._reconnect_thread = threading.Thread(target=self._reconnect_loop, daemon=True)
            self._reconnect_thread.start()
    
    def _reconnect_loop(self):
        while not self._stop_flag and not self.connected:
            try:
                logger.info("🔄 Attempting to reconnect...")
                self.connect()
                break
            except Exception as e:
                logger.error(f"❌ Reconnection failed: {e}")
                time.sleep(5)
    
    def add_websocket_subscriber(self, callback):
        self.ws_subscribers.append(callback)
    
    def remove_websocket_subscriber(self, callback):
        if callback in self.ws_subscribers:
            self.ws_subscribers.remove(callback)
    
    def _notify_subscribers(self, reading: MQTTSensorReading):
        if self.ws_subscribers:
            data = {
                "type": "sensor_update",
                "data": asdict(reading),
                "timestamp": datetime.now().isoformat()
            }
            for callback in self.ws_subscribers:
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"❌ Error notifying subscriber: {e}")
    
    def connect(self):
        if self.connecting:
            return
        
        self.connecting = True
        
        try:
            self.client.connect(self.broker_host, self.broker_port, 60)
            self.client.loop_start()
            
        except Exception as e:
            self.connected = False
            self.connecting = False
            logger.error(f"❌ Failed to connect: {e}")
            raise
    
    def disconnect(self):
        self._stop_flag = True
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
        self.connected = False
        logger.info("🛑 Disconnected from MQTT broker")
    
    def get_all_sensors(self) -> List[str]:
        return list(self.latest_readings.keys())
    
    def get_sensor_data(self, sensor_id: str, limit: int = 20) -> List[MQTTSensorReading]:
        if sensor_id not in self.sensor_data:
            return []
        return self.sensor_data[sensor_id][-limit:]
    
    def get_latest_readings(self) -> List[MQTTSensorReading]:
        return list(self.latest_readings.values())

    def get_sensor_records(self) -> List[Dict[str, Any]]:
        return [asdict(reading) for reading in self.latest_readings.values()]
    
    def get_sensor_status(self) -> Dict[str, Any]:
        return {
            "connected": self.connected,
            "total_messages": self.total_messages,
            "active_sensors": len(self.latest_readings),
            "total_readings": sum(len(v) for v in self.sensor_data.values()),
            "last_message": self.last_message_time.isoformat() if self.last_message_time else None
        }
    
    def get_risk_summary(self) -> Dict[str, int]:
        summary = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for reading in self.latest_readings.values():
            level = reading.risk_level or "LOW"
            if level in summary:
                summary[level] += 1
        return summary


_mqtt_service: Optional[MQTTService] = None


def get_mqtt_service() -> MQTTService:
    global _mqtt_service
    if _mqtt_service is None:
        _mqtt_service = MQTTService(
            broker_host=settings.MQTT_HOST,
            broker_port=settings.MQTT_PORT,
            topic=settings.MQTT_TOPIC,
        )
    return _mqtt_service
