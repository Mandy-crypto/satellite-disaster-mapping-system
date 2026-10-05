#!/usr/bin/env python3
"""
============================================
WATER LEVEL DETECTION - WINDOWS VERSION
============================================
"""

import cv2
import numpy as np
import time
import json
import threading
from datetime import datetime
import paho.mqtt.client as mqtt
import imutils
from flask import Flask, Response, render_template_string

# =============================================
# CONFIGURATION
# =============================================

CAMERA_INDEX = 0
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FPS = 15

# MQTT Settings
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "sensor/data"
MQTT_CLIENT_ID = "RPI_WATER_001"

# Web Server
WEB_PORT = 5000

# HSV for water detection (blue/green)
WATER_LOWER = np.array([80, 50, 50])
WATER_UPPER = np.array([140, 255, 255])
MIN_AREA = 1000
REFERENCE_HEIGHT_CM = 100
REFERENCE_PIXELS = 200

# =============================================
# GLOBAL VARIABLES
# =============================================

water_level_cm = 0
latest_frame = None
is_running = True
mqtt_client = None

# =============================================
# MQTT
# =============================================

def init_mqtt():
    global mqtt_client
    mqtt_client = mqtt.Client(
        client_id=MQTT_CLIENT_ID,
        callback_api_version=mqtt.CallbackAPIVersion.VERSION1
    )
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_start()
        print("✅ MQTT Connected")
        return True
    except Exception as e:
        print(f"❌ MQTT Error: {e}")
        return False

def publish_water_level(level_cm):
    if mqtt_client is None:
        return
    data = {
        "sensor_id": MQTT_CLIENT_ID,
        "latitude": 23.181,
        "longitude": 79.951,
        "timestamp": datetime.now().isoformat(),
        "water_level_cm": round(level_cm, 2),
        "source": "camera",
        "status": "active"
    }
    try:
        mqtt_client.publish(MQTT_TOPIC, json.dumps(data))
        print(f"📤 Published: {level_cm:.2f} cm")
    except Exception as e:
        print(f"❌ Publish error: {e}")

# =============================================
# WATER DETECTION
# =============================================

def detect_water(frame):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, WATER_LOWER, WATER_UPPER)
    
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    result = frame.copy()
    water_pixels = 0
    frame_height = frame.shape[0]
    
    if contours:
        largest = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest)
        if area > MIN_AREA:
            x, y, w, h = cv2.boundingRect(largest)
            water_pixels = frame_height - (y + h)
            cv2.rectangle(result, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.line(result, (0, y + h), (frame.shape[1], y + h), (0, 255, 255), 2)
            cv2.putText(result, f"Level: {water_pixels}px", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    return result, mask, water_pixels

def calculate_level(water_pixels):
    if REFERENCE_PIXELS > 0:
        return (water_pixels / REFERENCE_PIXELS) * REFERENCE_HEIGHT_CM
    return 0

# =============================================
# CAMERA
# =============================================

def init_camera():
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print("❌ No camera found!")
        return None
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    print("✅ USB Camera initialized")
    return cap

# =============================================
# MAIN LOOP
# =============================================

def camera_loop():
    global water_level_cm, latest_frame, is_running
    
    camera = init_camera()
    if camera is None:
        print("❌ Using test image mode...")
        is_running = False
        return
    
    print("📸 Starting camera loop...")
    
    while is_running:
        ret, frame = camera.read()
        if not ret:
            time.sleep(0.1)
            continue
        
        result, mask, water_pixels = detect_water(frame)
        water_level_cm = calculate_level(water_pixels)
        latest_frame = result
        
        if water_pixels > 0:
            publish_water_level(water_level_cm)
        
        # Display
        cv2.putText(result, f"Level: {water_level_cm:.2f} cm", (10, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.imshow("Water Level Detection", result)
        cv2.imshow("Water Mask", mask)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        
        time.sleep(0.05)
    
    camera.release()
    cv2.destroyAllWindows()
    print("✅ Camera loop stopped")

# =============================================
# WEB SERVER
# =============================================

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Water Level Monitor</title>
    <style>
        body { font-family: Arial; background: #0a0e27; color: white; text-align: center; padding: 20px; }
        h1 { color: #7c5cfc; }
        .container { max-width: 800px; margin: 0 auto; }
        img { width: 100%; border-radius: 12px; border: 2px solid rgba(255,255,255,0.1); }
        .data { margin: 20px 0; padding: 20px; background: rgba(255,255,255,0.05); border-radius: 12px; }
        .level { font-size: 48px; font-weight: bold; color: #2ed573; }
        .status { padding: 10px; border-radius: 8px; margin: 10px 0; background: rgba(46,213,115,0.2); color: #2ed573; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📸 Water Level Monitor</h1>
        <div class="status">✅ Live Stream</div>
        <img src="/video_feed">
        <div class="data">
            <div class="level">{{ level }} cm</div>
            <div style="color:rgba(255,255,255,0.5);">Last Update: {{ time }}</div>
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    global water_level_cm
    return render_template_string(HTML, level=round(water_level_cm, 2), time=datetime.now().strftime("%H:%M:%S"))

@app.route('/video_feed')
def video_feed():
    def generate():
        global latest_frame
        while is_running:
            if latest_frame is not None:
                ret, buffer = cv2.imencode('.jpg', latest_frame)
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            time.sleep(0.05)
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

# =============================================
# MAIN
# =============================================

def main():
    global is_running
    print("==========================================")
    print("📸 WATER LEVEL DETECTION - WINDOWS")
    print("==========================================")
    
    init_mqtt()
    
    camera_thread = threading.Thread(target=camera_loop, daemon=True)
    camera_thread.start()
    
    web_thread = threading.Thread(target=app.run, kwargs={'host': '0.0.0.0', 'port': WEB_PORT, 'debug': False, 'threaded': True}, daemon=True)
    web_thread.start()
    
    print(f"\n🌐 Web: http://localhost:{WEB_PORT}")
    print("📡 MQTT: " + MQTT_TOPIC)
    print("Press Ctrl+C to stop\n")
    
    try:
        while is_running:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping...")
        is_running = False
        if mqtt_client:
            mqtt_client.disconnect()
        print("✅ Stopped")

if __name__ == "__main__":
    main()