# Camera Water Level Detector

OpenCV utility that estimates a water level from a fixed camera view, streams annotated frames in a small Flask page, and can publish readings over MQTT.

## Setup

Install `requirements_windows.txt` on Windows, or `requirements.txt` on a Raspberry Pi. Pi camera support is optional; a USB webcam is used by default. Run from this folder:

```bash
python water_level_camera.py
```

The preview is served at `http://127.0.0.1:5000` by default. The primary `water_level_camera.py` reads camera, sensor location, broker, HSV bounds, and capture resolution from `config/settings.json`. Set `web.host` to `0.0.0.0` when the stream must be reachable from another device on the local network.

## Calibration

Measure a known vertical distance in the camera image, then save the corresponding pixel span:

```bash
python utills/calibration.py --height-cm 100 --pixels 200
```

This writes `reference_height_cm` and `reference_pixels` in `config/settings.json`. The conversion is `measured pixels * reference_height_cm / reference_pixels`; keep the camera fixed after calibration and repeat calibration whenever the camera position or zoom changes. `--zero-offset-cm` and `--invert` adjust the baseline and direction.

## MQTT

The default topic is `sensor/data`, which matches the backend MQTT subscriber. Configure the broker and site coordinates before deployment. For real measurements, use a fixed camera and a visible gauge or controlled channel; color-only water segmentation is sensitive to lighting, reflections, and background color.
