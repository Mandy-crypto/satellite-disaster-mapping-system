# Satellite-Assisted Disaster Mapping System

FastAPI backend for satellite flood analysis, ground sensor ingestion, live hazard feeds, risk dashboards, and WebSocket notifications. Uploaded files, readings, alerts, risk zones, and processing jobs are stored in SQLite and the local data directory by default.

## Features

- GeoTIFF and RGB image upload with flood detection, NDWI metrics, and saved visualizations.
- CSV and JSON sensor ingestion with row validation and per-reading risk scores.
- Durable background processing jobs with queue, status, result, failure, and cancellation states.
- Risk maps and statistics derived from imported readings, plus explicitly submitted risk zones.
- Public feeds: Open-Meteo forecast-model weather, USGS earthquakes, and NWIC/CWC Narmada-basin river gauge telemetry near Jabalpur.
- Optional official IMD automatic-weather-station readings and district warnings when an IMD-issued API credential is configured.
- Persistent alert creation and acknowledgment, MQTT ingestion, WebSocket updates, and satellite image processing.
- Interactive dashboard at `/static/dashboard.html` and OpenAPI documentation at `/docs`.

## Requirements and startup

Python 3.10 or newer is recommended (Python 3.11 or 3.12 is a good default; requirements allow newer compatible releases too). From this directory:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Using the virtual environment's `python.exe -m ...` form works in both Command Prompt and PowerShell and avoids PATH issues. If your system uses `python3` instead of `python`, replace `python` in the venv creation command with `python3`.

## Publish a public cloud website (Render)

This project includes a Dockerfile and Render Blueprint at `render.yaml`. Deploy it from a Git repository using Render's **New → Blueprint** flow. Render builds the backend and serves the dashboard and APIs together over HTTPS at a public `onrender.com` address. It uses a persistent disk at `/var/data` for SQLite, uploaded images, and processing output. The Blueprint uses a paid Starter web service because Render persistent disks are only available on paid services; check Render's current pricing before creating the service. The free web tier can sleep and has ephemeral storage, so it is not configured here for retaining uploads/database data.

To get the project into a repository, create a **private GitHub repository** and push this project folder, then connect that repository in Render and create a Blueprint from `render.yaml`. Keep `.env`, `.venv`, `data/`, uploads, and generated outputs out of Git (the ignore files already exclude them). Render will generate an `ADMIN_API_KEY`; keep it secret. Public dashboard users can view the site, while upload, processing, alert-writing, and risk-update endpoints require that key in the `X-Admin-API-Key` header. Add `IMD_API_KEY` in Render's Environment settings only if you have an IMD-issued credential. The deployment disables local MQTT by default; to receive MQTT telemetry in the cloud, configure a separate reachable broker and its `MQTT_HOST`, `MQTT_PORT`, and `MQTT_TOPIC` values.

I cannot finish the account-connected steps from this workspace yet: this folder is not a Git repository, GitHub CLI is not installed or authenticated, and no GitHub/Render connector is available in the current session. Once the code is pushed to your private repository and the Blueprint is created, Render gives you the public URL; your laptop can then be off.

After the server starts, open `http://127.0.0.1:8000/` for the dashboard, `http://127.0.0.1:8000/docs` for the API, or `http://127.0.0.1:8000/api/info` for service information. Do not open `static/dashboard.html` by double-clicking it: it needs to be served by FastAPI for API requests and live updates to work. The app creates `data/disaster_mapping.sqlite3`, `data/uploads/`, and the configured output directory as needed. Set `DATA_DIR`, `OUTPUT_DIR`, `MAX_UPLOAD_SIZE`, and `ALLOWED_ORIGINS` in the environment to customize storage, upload limits, and browser origins. `ALLOWED_ORIGINS` is a comma-separated list.

The default dashboard area is centered on Jabalpur, Madhya Pradesh, with a 250 km monitoring radius. Change `REGION_NAME`, `REGION_LAT`, `REGION_LON`, and `REGION_RADIUS_KM` in `.env` to use a different center/radius. The dashboard labels its public feed coverage; its CWC Narmada dataset may be old, and stale source timestamps remain visible. Satellite scene/flood areas are shown only after processing georeferenced imagery in the selected region. Risk-zone counts are shown as unavailable until there are regional sensor observations or saved risk zones; this prevents missing data from looking like a measured zero-risk result.

Weather uses the public Open-Meteo forecast API without an API key. Its “current” values come from weather forecast models, not direct observations from a nearby station. The CWC river feed is public NWIC telemetry for the Narmada basin in Madhya Pradesh, filtered by distance from the requested map center; timestamps identify when the source record was acquired. Old readings are marked stale after 24 hours. A CWC gauge level is an elevation relative to that station's gauge datum; it is not flood depth or a warning threshold. Do not infer flood danger from that number alone.

USGS earthquake data is fetched from the public feed. The USGS water-level endpoint requires configured site IDs and verified site-specific thresholds in `USGS_WATER_STATIONS`; without them it returns no readings. IMD AWS/ARG observations and district warnings are official station/warning feeds, but require an IMD-issued API credential. Register through the [IMD API portal](https://api.imd.gov.in/public/index.php), then put the issued token in `IMD_API_KEY` in `.env` and restart the server. Without a key `/api/live/india-stations` and `/api/live/india-warnings` explain that they are unconfigured. External feeds need internet access and can be temporarily unavailable. Provider data coverage and update frequency vary by location.

The dashboard combines several different kinds of information: MQTT or uploaded readings are sensor observations; Open-Meteo is model output; CWC values are government river gauge records; USGS values are earthquake records; and imported satellite images are analyzed from the uploaded file. The dashboard does not claim all map areas are covered by real-time government sensors. Where an external feed reports its source timestamp, use that timestamp to judge freshness. A provider outage is shown as unavailable rather than silently replaced with random readings.

## Main workflows

### Satellite processing

1. Upload a `.tif`, `.tiff`, `.png`, `.jpg`, or `.jpeg` image to `POST /api/satellite/upload` as multipart form data. Optional `lat` and `lon` query parameters attach its location.
2. Start analysis with `POST /api/process/` and JSON such as `{"satellite_image_id":"IMG_...","threshold":0.2}`.
3. Poll `GET /api/process/{job_id}`. A completed result includes satellite metrics and a fused risk summary. `GET /api/satellite/results/{image_id}` retrieves the corresponding result.

GeoTIFF multispectral scenes use the raster pipeline; regular RGB images use the RGB flood-detection fallback. The supported threshold range is -1 to 1.

### Sensor ingestion

Upload a CSV or JSON array to `POST /api/sensors/upload`. Each reading needs `sensor_id`, `latitude`, `longitude`, `timestamp`, `rainfall_mm`, `water_level_cm`, `soil_moisture_percent`, and `temperature_c`. Sensor files are validated before import. Query readings at `GET /api/sensors/`, or start a job with `sensor_file_id` to calculate a batch risk summary.

### Dashboard and live updates

- `GET /api/dashboard/risk-map` and `/api/dashboard/zones` return saved zones or zones derived from the latest sensor reading per sensor.
- `GET /api/dashboard/statistics` summarizes saved/imported sensor risk levels. Affected area is zero until satellite/risk-zone data supplies an area; confidence is blank where none was calculated.
- `GET /api/live/weather?lat=23.181&lon=79.951` and `/api/live/forecast?lat=23.181&lon=79.951` query Open-Meteo.
- `GET /api/live/river-levels?lat=23.181&lon=79.951&radius_km=250` returns nearby Narmada-basin CWC/NWIC stations.
- `GET /api/live/india-stations?state_id=27` and `/api/live/india-warnings` query IMD when `IMD_API_KEY` is configured.
- `GET /api/live/earthquakes` returns USGS earthquake feed entries.
- `POST /api/dashboard/alerts/push` stores an alert and broadcasts it; `PATCH /api/dashboard/alerts/{alert_id}/acknowledge` acknowledges it.
- WebSocket endpoints are exposed under `/ws`; live external feeds are under `/api/live`.

## Upload safety and persistence

Uploads are limited by `MAX_UPLOAD_SIZE` (50 MiB by default), filenames are normalized to their basename, and files are stored under the application data directory with generated names. SQLite uses WAL mode. Back up both the SQLite database and upload/output directories to preserve a complete installation.

Copy `.env.example` to `.env` for local configuration. Keep real API keys out of source control; `.env` and runtime databases are ignored by Git.

## Development

The main application is `app/main.py`. API routers live in `app/api/`, satellite processing in `app/pipeline/satellite/`, sensor simulation in `app/pipeline/sensors/`, and external integrations in `app/services/`. `run_demo.py` generates demo outputs; `sensor_simulator.py` publishes MQTT readings. Test scripts are included in the repository.
