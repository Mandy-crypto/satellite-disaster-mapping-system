"""
WebSocket Handler for Real-time Updates
Supports: Sensor data, Alerts, Risk zones
"""

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from typing import List, Dict, Any, Set
import logging
import json
from datetime import datetime
import asyncio

from app.services.mqtt_service import get_mqtt_service
from app.security import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ws",
    tags=["WebSocket"]
)


class ConnectionManager:
    """Manage WebSocket connections with room support"""
    
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {
            "sensors": set(),
            "alerts": set(),
            "risk": set(),
            "all": set()
        }
        self.connection_data: Dict[WebSocket, Dict] = {}
    
    async def connect(self, websocket: WebSocket, room: str = "all"):
        """Accept new WebSocket connection"""
        await websocket.accept()
        self.active_connections[room].add(websocket)
        self.connection_data[websocket] = {
            "room": room,
            "connected_at": datetime.now().isoformat(),
            "messages_sent": 0,
            "last_ping": datetime.now().isoformat()
        }
        logger.info(f"🔌 WebSocket connected to {room} (total: {self.get_total_connections()})")
    
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        for room, connections in self.active_connections.items():
            if websocket in connections:
                connections.remove(websocket)
                break
        if websocket in self.connection_data:
            del self.connection_data[websocket]
        logger.info(f"🔌 WebSocket disconnected (total: {self.get_total_connections()})")
    
    async def send_json(self, websocket: WebSocket, data: Dict[str, Any]):
        """Send JSON to a specific connection"""
        try:
            await websocket.send_json(data)
            if websocket in self.connection_data:
                self.connection_data[websocket]["messages_sent"] += 1
        except Exception as e:
            logger.error(f"❌ Error sending: {e}")
            self.disconnect(websocket)
    
    async def broadcast_to_room(self, room: str, data: Dict[str, Any]):
        """Broadcast to all connections in a room"""
        disconnected = []
        for websocket in self.active_connections.get(room, []):
            try:
                await websocket.send_json(data)
                if websocket in self.connection_data:
                    self.connection_data[websocket]["messages_sent"] += 1
            except Exception:
                disconnected.append(websocket)
        
        for websocket in disconnected:
            self.disconnect(websocket)
    
    async def broadcast(self, data: Dict[str, Any]):
        """Broadcast to all connections"""
        await self.broadcast_to_room("all", data)
        room = data.get("room")
        if room and room in self.active_connections:
            await self.broadcast_to_room(room, data)
    
    def get_total_connections(self) -> int:
        """Get total active connections"""
        return sum(len(conns) for conns in self.active_connections.values())
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        return {
            "total": self.get_total_connections(),
            "rooms": {
                room: len(conns) 
                for room, conns in self.active_connections.items()
            },
            "connections": [
                {
                    "room": data.get("room", "unknown"),
                    "connected_at": data.get("connected_at"),
                    "messages_sent": data.get("messages_sent", 0)
                }
                for data in self.connection_data.values()
            ]
        }


# Global connection manager
manager = ConnectionManager()


# =============================================
# WEBSOCKET ENDPOINTS
# =============================================

@router.websocket("/sensors")
async def websocket_sensors(websocket: WebSocket):
    """
    WebSocket for real-time sensor data
    """
    await manager.connect(websocket, "sensors")
    
    mqtt_service = get_mqtt_service()
    
    def mqtt_callback(data):
        import asyncio
        asyncio.create_task(manager.broadcast_to_room("sensors", {
            "type": "sensor_update",
            "data": data,
            "timestamp": datetime.now().isoformat()
        }))
    
    mqtt_service.add_websocket_subscriber(mqtt_callback)
    
    try:
        await manager.send_json(websocket, {
            "type": "connection_established",
            "room": "sensors",
            "message": "Connected to sensor WebSocket",
            "timestamp": datetime.now().isoformat()
        })
        
        await manager.send_json(websocket, {
            "type": "sensor_status",
            "data": mqtt_service.get_sensor_status(),
            "timestamp": datetime.now().isoformat()
        })
        
        while True:
            try:
                data = await websocket.receive_text()
                if data == "ping":
                    await manager.send_json(websocket, {
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    })
                else:
                    await manager.send_json(websocket, {
                        "type": "echo",
                        "message": f"Received: {data}",
                        "timestamp": datetime.now().isoformat()
                    })
            except Exception as e:
                logger.error(f"❌ WebSocket error: {e}")
                break
    
    except WebSocketDisconnect:
        pass
    
    finally:
        mqtt_service.remove_websocket_subscriber(mqtt_callback)
        manager.disconnect(websocket)


@router.websocket("/alerts")
async def websocket_alerts(websocket: WebSocket):
    """
    WebSocket for real-time alerts
    """
    await manager.connect(websocket, "alerts")
    
    try:
        await manager.send_json(websocket, {
            "type": "connection_established",
            "room": "alerts",
            "message": "Connected to alerts WebSocket",
            "timestamp": datetime.now().isoformat()
        })
        
        try:
            from app.api.dashboard import get_alerts
            alerts_data = await get_alerts()
            await manager.send_json(websocket, {
                "type": "alerts_initial",
                "data": alerts_data,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"❌ Error loading alerts: {e}")
        
        while True:
            try:
                data = await websocket.receive_text()
                if data == "ping":
                    await manager.send_json(websocket, {
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    })
            except Exception:
                break
    
    except WebSocketDisconnect:
        pass
    
    finally:
        manager.disconnect(websocket)


@router.websocket("/risk")
async def websocket_risk(websocket: WebSocket):
    """
    WebSocket for real-time risk zone updates
    """
    await manager.connect(websocket, "risk")
    
    try:
        await manager.send_json(websocket, {
            "type": "connection_established",
            "room": "risk",
            "message": "Connected to risk WebSocket",
            "timestamp": datetime.now().isoformat()
        })
        
        try:
            from app.api.dashboard import get_risk_map
            risk_data = await get_risk_map()
            await manager.send_json(websocket, {
                "type": "risk_initial",
                "data": risk_data,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"❌ Error loading risk data: {e}")
        
        while True:
            try:
                data = await websocket.receive_text()
                if data == "ping":
                    await manager.send_json(websocket, {
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    })
                elif data == "refresh":
                    from app.api.dashboard import get_risk_map
                    risk_data = await get_risk_map()
                    await manager.send_json(websocket, {
                        "type": "risk_update",
                        "data": risk_data,
                        "timestamp": datetime.now().isoformat()
                    })
            except Exception:
                break
    
    except WebSocketDisconnect:
        pass
    
    finally:
        manager.disconnect(websocket)


@router.websocket("/all")
async def websocket_all(websocket: WebSocket):
    """
    WebSocket for all updates (sensors + alerts + risk)
    """
    await manager.connect(websocket, "all")
    
    mqtt_service = get_mqtt_service()
    
    def mqtt_callback(data):
        import asyncio
        asyncio.create_task(manager.send_json(websocket, {
            "type": "sensor_update",
            "data": data,
            "timestamp": datetime.now().isoformat()
        }))
    
    mqtt_service.add_websocket_subscriber(mqtt_callback)
    
    try:
        await manager.send_json(websocket, {
            "type": "connection_established",
            "room": "all",
            "message": "Connected to all updates WebSocket",
            "timestamp": datetime.now().isoformat()
        })
        
        try:
            from app.api.dashboard import get_risk_map, get_alerts
            risk_data = await get_risk_map()
            alerts_data = await get_alerts()
            sensor_status = mqtt_service.get_sensor_status()
            
            await manager.send_json(websocket, {
                "type": "initial_data",
                "data": {
                    "risk": risk_data,
                    "alerts": alerts_data,
                    "sensors": sensor_status
                },
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"❌ Error loading initial data: {e}")
        
        while True:
            try:
                data = await websocket.receive_text()
                if data == "ping":
                    await manager.send_json(websocket, {
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    })
                elif data == "refresh":
                    from app.api.dashboard import get_risk_map, get_alerts
                    risk_data = await get_risk_map()
                    alerts_data = await get_alerts()
                    
                    await manager.send_json(websocket, {
                        "type": "refresh_data",
                        "data": {
                            "risk": risk_data,
                            "alerts": alerts_data
                        },
                        "timestamp": datetime.now().isoformat()
                    })
            except Exception:
                break
    
    except WebSocketDisconnect:
        pass
    
    finally:
        mqtt_service.remove_websocket_subscriber(mqtt_callback)
        manager.disconnect(websocket)


# =============================================
# WEBSOCKET STATUS ENDPOINT
# =============================================

@router.get("/status")
async def get_websocket_status():
    """Get WebSocket connection status"""
    return {
        "status": "success",
        "connections": manager.get_stats(),
        "timestamp": datetime.now().isoformat()
    }


@router.post("/broadcast", dependencies=[Depends(require_admin)])
async def broadcast_message(data: Dict[str, Any]):
    """Broadcast a message to all WebSocket connections"""
    room = data.get("room", "all")
    message = data.get("message", {})
    
    if room == "all":
        await manager.broadcast(message)
    else:
        await manager.broadcast_to_room(room, message)
    
    return {
        "status": "success",
        "message": f"Broadcasted to {room}",
        "timestamp": datetime.now().isoformat()
    }


# =============================================
# ALERT PUSH FUNCTION
# =============================================

async def push_alert(alert_data: Dict[str, Any]):
    """Push an alert to all WebSocket clients"""
    await manager.broadcast_to_room("alerts", {
        "type": "new_alert",
        "data": alert_data,
        "timestamp": datetime.now().isoformat()
    })
    await manager.broadcast({
        "type": "new_alert",
        "data": alert_data,
        "timestamp": datetime.now().isoformat()
    })
    logger.info(f"🔔 Alert pushed: {alert_data.get('message', '')}")
