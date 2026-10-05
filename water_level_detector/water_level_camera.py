# =============================================
# CONFIGURATION
# =============================================

# Camera Settings
CAMERA_INDEX = 0  # 0 for USB webcam
USE_PICAMERA = False  # FALSE FOR WINDOWS! Set False for USB webcam
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FPS = 15
#!/usr/bin/env python3
"""
============================================
📸 WATER LEVEL DETECTION - RASPBERRY PI CAMERA
============================================

Features:
- Camera-based water level detection using OpenCV
- Water surface segmentation
- Real-time water level calculation
- Live video streaming (web interface)
- MQTT publishing

Requirements:
- Raspberry Pi with Camera Module (or USB webcam)
- OpenCV, picamera2, imutils
- Mosquitto MQTT broker

Installation:
pip install opencv-python picamera2 imutils paho-mqtt numpy
============================================
"""

import cv2
import numpy as np
import time
import json
import threading
import queue
from pathlib import Path
from datetime import datetime
import paho.mqtt.client as mqtt
# from picamera2 import Picamera2  # Only available on Raspberry Pi
import imutils
from flask import Flask, Response, render_template_string

# =============================================
# CONFIGURATION
# =============================================

# Load the editable installation profile, with safe defaults for first run.
CONFIG_PATH = Path(__file__).resolve().parent / "config" / "settings.json"
try:
    with CONFIG_PATH.open(encoding="utf-8") as config_file:
        APP_CONFIG = json.load(config_file)
except (OSError, json.JSONDecodeError):
    APP_CONFIG = {}

CAMERA_CONFIG = APP_CONFIG.get("camera", {})
DETECTION_CONFIG = APP_CONFIG.get("detection", {})
CALIBRATION_CONFIG = APP_CONFIG.get("calibration", {})
SENSOR_CONFIG = APP_CONFIG.get("sensor", {})
MQTT_CONFIG = APP_CONFIG.get("mqtt", {})
WEB_CONFIG = APP_CONFIG.get("web", {})

CAMERA_INDEX = int(CAMERA_CONFIG.get("index", 0))
USE_PICAMERA = bool(CAMERA_CONFIG.get("use_picamera", False))
FRAME_WIDTH = int(CAMERA_CONFIG.get("width", 640))
FRAME_HEIGHT = int(CAMERA_CONFIG.get("height", 480))
FPS = int(CAMERA_CONFIG.get("fps", 15))
MIN_AREA = int(DETECTION_CONFIG.get("minimum_contour_area", 1000))
REFERENCE_HEIGHT_CM = float(CALIBRATION_CONFIG.get("reference_height_cm", 100.0))
REFERENCE_PIXELS = float(CALIBRATION_CONFIG.get("reference_pixels", 200.0))
ZERO_OFFSET_CM = float(CALIBRATION_CONFIG.get("zero_offset_cm", 0.0))
CALIBRATION_INVERT = bool(CALIBRATION_CONFIG.get("invert", False))
MQTT_BROKER = MQTT_CONFIG.get("host", "localhost")
MQTT_PORT = int(MQTT_CONFIG.get("port", 1883))
MQTT_TOPIC = MQTT_CONFIG.get("topic", "sensor/data")
MQTT_CLIENT_ID = SENSOR_CONFIG.get("sensor_id", "RPI_WATER_001")
MQTT_ENABLED = bool(MQTT_CONFIG.get("enabled", True))
WEB_HOST = WEB_CONFIG.get("host", "127.0.0.1")
WEB_PORT = int(WEB_CONFIG.get("port", 5000))

# =============================================
# GLOBAL VARIABLES
# =============================================

water_level_cm = 0
latest_frame = None
frame_queue = queue.Queue(maxsize=10)
mqtt_client = None
is_running = True

# HSV range for water detection (blue/green water)
# You may need to adjust these based on your setup
WATER_LOWER = np.array(DETECTION_CONFIG.get("hsv_lower", [80, 50, 50]), dtype=np.uint8)
WATER_UPPER = np.array(DETECTION_CONFIG.get("hsv_upper", [140, 255, 255]), dtype=np.uint8)

# =============================================
# MQTT FUNCTIONS
# =============================================

def init_mqtt():
    """Initialize MQTT client"""
    global mqtt_client
    
    mqtt_client = mqtt.Client(
        client_id=MQTT_CLIENT_ID,
        callback_api_version=mqtt.CallbackAPIVersion.VERSION1
    )
    
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("✅ MQTT Connected")
        else:
            print(f"❌ MQTT Connection failed (rc: {rc})")
    
    mqtt_client.on_connect = on_connect
    
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_start()
        return True
    except Exception as e:
        print(f"❌ MQTT Connection error: {e}")
        return False

def publish_water_level(level_cm, frame=None):
    """Publish water level data via MQTT"""
    if mqtt_client is None or not MQTT_ENABLED:
        return
    
    data = {
        "sensor_id": MQTT_CLIENT_ID,
        "latitude": float(SENSOR_CONFIG.get("latitude", 23.181)),
        "longitude": float(SENSOR_CONFIG.get("longitude", 79.951)),
        "timestamp": datetime.now().isoformat(),
        "water_level_cm": round(level_cm, 2),
        "water_level_percent": round((level_cm / REFERENCE_HEIGHT_CM) * 100, 2),
        "source": "camera",
        "status": "active",
        "battery_percent": 100  # Not applicable for camera
    }
    
    try:
        payload = json.dumps(data)
        mqtt_client.publish(MQTT_TOPIC, payload)
        print(f"📤 Published: {level_cm:.2f} cm")
    except Exception as e:
        print(f"❌ Publish error: {e}")

# =============================================
# WATER DETECTION
# =============================================

def detect_water(frame):
    """
    Detect water surface using color segmentation
    Returns: processed frame, water mask, water level in pixels
    """
    # Convert to HSV for better color segmentation
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    
    # Create mask for water (blue/green range)
    mask = cv2.inRange(hsv, WATER_LOWER, WATER_UPPER)
    
    # Morphological operations to clean up the mask
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    
    # Find contours
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Draw detection on frame
    result = frame.copy()
    water_pixels = 0
    frame_height = frame.shape[0]
    
    if contours:
        # Find the largest contour (water surface)
        largest_contour = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest_contour)
        
        if area > MIN_AREA:
            # Get bounding rectangle
            x, y, w, h = cv2.boundingRect(largest_contour)
            
            # Calculate water level (from bottom of frame)
            water_pixels = frame_height - (y + h)
            
            # Draw bounding box
            cv2.rectangle(result, (x, y), (x + w, y + h), (0, 255, 0), 2)
            
            # Draw water surface line
            cv2.line(result, (0, y + h), (frame.shape[1], y + h), (0, 255, 255), 2)
            
            # Annotate level
            cv2.putText(result, f"Water Level: {water_pixels}px", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Draw contour
            cv2.drawContours(result, [largest_contour], -1, (255, 0, 0), 2)
    
    return result, mask, water_pixels

def calculate_level_pixels_to_cm(pixels):
    """Convert pixel measurement to centimeters"""
    if REFERENCE_PIXELS > 0:
        signed_pixels = -pixels if CALIBRATION_INVERT else pixels
        return max(0.0, ZERO_OFFSET_CM + (signed_pixels / REFERENCE_PIXELS) * REFERENCE_HEIGHT_CM)
    return 0

# =============================================
# CAMERA FUNCTIONS
# =============================================

def init_camera():
    """Initialize camera (Windows compatible)"""
    import sys
    if sys.platform == 'win32':
        print("💻 Windows detected - Using USB webcam")
        return init_usb_camera()
    
    # For Raspberry Pi
    if USE_PICAMERA:
        try:
            from picamera2 import Picamera2
            picam2 = Picamera2()
            config = picam2.create_preview_configuration(
                main={"size": (FRAME_WIDTH, FRAME_HEIGHT)}
            )
            picam2.configure(config)
            picam2.start()
            print("✅ Pi Camera initialized")
            return picam2
        except Exception as e:
            print(f"⚠️ Pi Camera error: {e}")
            print("Falling back to USB webcam...")
            return init_usb_camera()
    else:
        return init_usb_camera()

def init_usb_camera():
    """Initialize USB webcam"""
    cap = cv2.VideoCapture(CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, FPS)
    print("✅ USB Camera initialized")
    return cap

def capture_frame(camera):
    """Capture a frame from camera"""
    if USE_PICAMERA:
        return camera.capture_array()
    else:
        ret, frame = camera.read()
        return frame if ret else None

def camera_loop():
    """Main camera processing loop"""
    global water_level_cm, latest_frame, is_running
    
    camera = init_camera()
    if camera is None:
        print("❌ Failed to initialize camera")
        return
    
    print("📸 Starting camera loop...")
    fps_counter = 0
    fps_start = time.time()
    
    while is_running:
        try:
            # Capture frame
            frame = capture_frame(camera)
            if frame is None:
                print("⚠️ Failed to capture frame")
                time.sleep(0.1)
                continue
            
            # Process frame
            result, mask, water_pixels = detect_water(frame)
            
            # Calculate water level in cm
            water_level_cm = calculate_level_pixels_to_cm(water_pixels)
            
            # Store latest frame for streaming
            latest_frame = result.copy()
            
            # Publish every 5 seconds
            if water_pixels > 0:
                publish_water_level(water_level_cm, result)
            
            # FPS counter
            fps_counter += 1
            if time.time() - fps_start > 1:
                fps_start = time.time()
                fps_counter = 0
            
            # Add FPS overlay
            cv2.putText(result, f"FPS: {fps_counter}", 
                       (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Show level on frame
            cv2.putText(result, f"Level: {water_level_cm:.2f} cm", 
                       (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Display locally (optional - comment out for headless)
            cv2.imshow("Water Level Detection", result)
            cv2.imshow("Water Mask", mask)
            
            # Close on 'q' press
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            
            # Small delay
            time.sleep(0.05)
            
        except Exception as e:
            print(f"❌ Camera loop error: {e}")
            time.sleep(1)
    
    # Cleanup
    if USE_PICAMERA:
        camera.stop()
    else:
        camera.release()
    cv2.destroyAllWindows()
    print("✅ Camera loop stopped")

# =============================================
# WEB STREAMING SERVER
# =============================================

app = Flask(__name__)

HTML_TEMPLATE = """
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
        .status { padding: 10px; border-radius: 8px; margin: 10px 0; }
        .status.online { background: rgba(46,213,115,0.2); color: #2ed573; }
        .refresh { margin-top: 20px; color: rgba(255,255,255,0.5); }
    </style>
    <meta http-equiv="refresh" content="5">
</head>
<body>
    <div class="container">
        <h1>📸 Water Level Monitor</h1>
        <div class="status online">✅ Live Stream</div>
        <img src="/video_feed" alt="Camera Feed">
        <div class="data">
            <div class="level">{{ level }} cm</div>
            <div style="color:rgba(255,255,255,0.5);">
                Last Update: {{ time }}
            </div>
        </div>
        <div class="refresh">🔄 Auto-refresh every 5 seconds</div>
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    """Web interface"""
    global water_level_cm
    return render_template_string(
        HTML_TEMPLATE,
        level=round(water_level_cm, 2),
        time=datetime.now().strftime("%H:%M:%S")
    )

@app.route('/video_feed')
def video_feed():
    """Video streaming endpoint"""
    def generate_frames():
        global latest_frame
        while is_running:
            if latest_frame is not None:
                # Convert frame to JPEG
                ret, buffer = cv2.imencode('.jpg', latest_frame)
                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(0.05)
    
    return Response(generate_frames(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

def start_web_server():
    """Start the Flask web server in a separate thread"""
    app.run(host=WEB_HOST, port=WEB_PORT, debug=False, threaded=True)

# =============================================
# CALIBRATION TOOL
# =============================================

def calibrate():
    """
    Calibration helper - run this to set REFERENCE_PIXELS
    Place a ruler/marker at a known height and measure pixels
    """
    print("==========================================")
    print("📏 WATER LEVEL CALIBRATION")
    print("==========================================")
    print("1. Place a ruler or known-height object in the frame")
    print("2. Enter the height in cm (e.g., 100):")
    known_height = float(input("Height (cm): "))
    
    print("3. Press 'c' when ready to capture reference")
    camera = init_camera()
    
    while True:
        frame = capture_frame(camera)
        if frame is not None:
            cv2.imshow("Calibration - Press 'c' to capture", frame)
            key = cv2.waitKey(1)
            if key == ord('c'):
                print("4. Click on the top of the reference and press Enter")
                cv2.imshow("Calibration - Click top point", frame)
                cv2.setMouseCallback("Calibration - Click top point", get_click_position)
                break
            elif key == ord('q'):
                return
    
    if USE_PICAMERA:
        camera.stop()
    else:
        camera.release()
    cv2.destroyAllWindows()
    
    print(f"✅ Calibration complete. Set REFERENCE_PIXELS = {REFERENCE_PIXELS}")

click_points = []
def get_click_position(event, x, y, flags, param):
    global REFERENCE_PIXELS, click_points
    if event == cv2.EVENT_LBUTTONDOWN:
        click_points.append((x, y))
        print(f"Clicked: ({x}, {y})")
        if len(click_points) >= 2:
            REFERENCE_PIXELS = abs(click_points[1][1] - click_points[0][1])
            print(f"✅ Reference pixels: {REFERENCE_PIXELS}")

# =============================================
# MAIN
# =============================================

def main():
    """Main entry point"""
    global is_running
    
    print("==========================================")
    print("📸 WATER LEVEL DETECTION SYSTEM")
    print("==========================================")
    
    # Initialize MQTT
    init_mqtt()
    
    # Start camera loop in a separate thread
    camera_thread = threading.Thread(target=camera_loop, daemon=True)
    camera_thread.start()
    
    # Start web server in a separate thread
    web_thread = threading.Thread(target=start_web_server, daemon=True)
    web_thread.start()
    
    print(f"\n🌐 Web interface: http://localhost:{WEB_PORT}")
    print("📡 MQTT publishing to: " + MQTT_TOPIC)
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

# =============================================
# COMMAND LINE
# =============================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--calibrate":
        calibrate()
    else:
        main()
