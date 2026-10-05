"""
MQTT Sensor Simulator - Sends fake sensor data to FastAPI
No hardware needed! Runs on your computer.
"""

import json
import time
import random
from datetime import datetime
import paho.mqtt.client as mqtt

# =============================================
# CONFIGURATION
# =============================================

BROKER = "localhost"  # Mosquitto is running on your PC
PORT = 1883
TOPIC = "sensor/data"
CLIENT_ID = "SIMULATOR_001"

# =============================================
# SENSOR SIMULATOR
# =============================================

def generate_sensor_data(sensor_id, lat, lon):
    """Generate realistic fake sensor data"""
    
    # Create different risk scenarios
    risk_scenario = random.choice(["normal", "warning", "flood"])
    
    if risk_scenario == "normal":
        rainfall = round(random.uniform(0, 10), 2)
        water_level = round(random.uniform(10, 40), 2)
        soil_moisture = round(random.uniform(30, 50), 2)
    elif risk_scenario == "warning":
        rainfall = round(random.uniform(30, 60), 2)
        water_level = round(random.uniform(60, 90), 2)
        soil_moisture = round(random.uniform(60, 80), 2)
    else:  # flood
        rainfall = round(random.uniform(80, 150), 2)
        water_level = round(random.uniform(100, 180), 2)
        soil_moisture = round(random.uniform(85, 98), 2)
    
    return {
        "sensor_id": sensor_id,
        "latitude": lat + random.uniform(-0.005, 0.005),
        "longitude": lon + random.uniform(-0.005, 0.005),
        "timestamp": datetime.now().isoformat(),
        "temperature_c": round(random.uniform(20, 35), 2),
        "humidity": round(random.uniform(40, 85), 2),
        "rainfall_mm": rainfall,
        "water_level_cm": water_level,
        "soil_moisture_percent": soil_moisture,
        "battery_percent": round(random.uniform(60, 100), 2),
        "signal_strength": random.randint(3, 5),
        "risk_scenario": risk_scenario
    }

def publish_sensor_data():
    """Publish data for 5 simulated sensors continuously"""
    
    # Define sensors with different locations
    sensors = [
        {"id": "SENSOR_001", "lat": 23.181, "lon": 79.951},
        {"id": "SENSOR_002", "lat": 23.195, "lon": 79.940},
        {"id": "SENSOR_003", "lat": 23.215, "lon": 79.920},
        {"id": "SENSOR_004", "lat": 23.170, "lon": 79.960},
        {"id": "SENSOR_005", "lat": 23.200, "lon": 79.945},
    ]
    
    print("=" * 50)
    print("📡 MQTT SENSOR SIMULATOR STARTED")
    print("=" * 50)
    print(f"📤 Publishing to: {BROKER}:{PORT}/{TOPIC}")
    print(f"📡 Number of sensors: {len(sensors)}")
    print("Press Ctrl+C to stop\n")
    
    # Create MQTT client with proper callback API version
    client = mqtt.Client(
        client_id=CLIENT_ID, 
        callback_api_version=mqtt.CallbackAPIVersion.VERSION1
    )
    client.connect(BROKER, PORT, 60)
    client.loop_start()
    
    message_count = 0
    
    try:
        while True:
            for sensor in sensors:
                # Generate data
                data = generate_sensor_data(sensor["id"], sensor["lat"], sensor["lon"])
                payload = json.dumps(data)
                
                # Publish
                client.publish(TOPIC, payload)
                message_count += 1
                
                # Print summary
                risk_emoji = "🟢" if data["risk_scenario"] == "normal" else "🟡" if data["risk_scenario"] == "warning" else "🔴"
                print(f"{risk_emoji} [{message_count}] {sensor['id']}: {data['temperature_c']}°C, "
                      f"🌧️{data['rainfall_mm']}mm, 💧{data['water_level_cm']}cm, "
                      f"🌱{data['soil_moisture_percent']}%")
                
                # Random delay between sensors (1-3 seconds)
                time.sleep(random.uniform(1, 3))
            
            print("-" * 40)
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping simulator...")
        client.disconnect()
        print("✅ Simulator stopped")

# =============================================
# RUN THE SIMULATOR
# =============================================

if __name__ == "__main__":
    publish_sensor_data()