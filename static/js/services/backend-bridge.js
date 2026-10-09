/**
 * ============================================================================
 * ASTRA-GEO // SATELLITE DISASTER INTELLIGENCE PLATFORM
 * FASTAPI BACKEND & WEBSOCKET REAL-TIME INTEGRATION BRIDGE
 * ============================================================================
 * Bridges the aerospace tactical dashboard to the FastAPI backend:
 * - Live WebSockets (/ws) with automatic reconnection & heartbeat
 * - Central Water Commission (CWC) live river gauge levels (/api/live/river-levels)
 * - USGS live seismic feeds (/api/live/earthquakes/near)
 * - IMD Indian disaster warnings & Open-Meteo weather (/api/live/weather)
 * - IoT water level sensor array (/api/live/sensors) & MQTT stream
 * - Risk assessment zones & statistics (/api/dashboard/statistics)
 */

(function (window) {
  'use strict';

  class FastAPIBackendBridge {
    constructor() {
      this.ws = null;
      this.wsConnected = false;
      this.reconnectTimer = null;
      this.pingInterval = null;
      this.apiBaseUrl = '';
      this.regionParams = {
        lat: 23.181,
        lon: 79.951,
        radiusKm: 250
      };
      this.liveSensorCount = 0;
      this.liveAlerts = [];
      this.riverGauges = [];
      this.earthquakes = [];
    }

    init() {
      // Determine API Base URL based on current protocol
      if (window.location.protocol === 'http:' || window.location.protocol === 'https:') {
        this.apiBaseUrl = window.location.origin;
        this.connectWebSocket();
        this.fetchInitialAPIData();
        // Periodic polling for REST updates
        setInterval(() => this.fetchInitialAPIData(), 15000);
      } else {
        console.log('ℹ️ Running in offline/file:// mode. Using simulated live telemetry feeds.');
        this.simulateLiveFeeds();
      }
    }

    connectWebSocket() {
      if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
        return;
      }

      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${wsProtocol}//${window.location.host}/ws`;

      try {
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
          this.wsConnected = true;
          this.updateConnectionStatus(true);
          console.log('✅ Real-time WebSocket connection established with FastAPI backend');
          if (window.telemetryFeed) {
            window.telemetryFeed.logEvent('WS_BRIDGE', 'Connected to FastAPI backend WebSocket stream (/ws)', 'success');
          }
          // Start ping heartbeat every 25 seconds
          this.startHeartbeat();
        };

        this.ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            this.handleWebSocketMessage(data);
          } catch (e) {
            // Text pong response
            if (event.data === 'pong') {
              // Heartbeat acknowledged
            }
          }
        };

        this.ws.onclose = () => {
          this.wsConnected = false;
          this.updateConnectionStatus(false);
          this.stopHeartbeat();
          // Schedule reconnect attempt in 4 seconds
          clearTimeout(this.reconnectTimer);
          this.reconnectTimer = setTimeout(() => this.connectWebSocket(), 4000);
        };

        this.ws.onerror = (err) => {
          this.wsConnected = false;
          this.updateConnectionStatus(false);
        };
      } catch (err) {
        console.warn('WebSocket connection not available:', err);
      }
    }

    startHeartbeat() {
      this.stopHeartbeat();
      this.pingInterval = setInterval(() => {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
          this.ws.send('ping');
        }
      }, 25000);
    }

    stopHeartbeat() {
      if (this.pingInterval) {
        clearInterval(this.pingInterval);
        this.pingInterval = null;
      }
    }

    updateConnectionStatus(connected) {
      const badge = document.getElementById('backend-ws-status-badge');
      if (badge) {
        badge.textContent = connected ? '● WS CONNECTED' : '○ WS STANDBY';
        badge.className = connected ? 'badge-emerald' : 'badge-amber';
      }
    }

    handleWebSocketMessage(payload) {
      if (!payload || !payload.type) return;

      switch (payload.type) {
        case 'connection_established':
          console.log('Backend Bridge:', payload.message);
          break;

        case 'sensor_update':
          this.handleLiveSensorUpdate(payload.data);
          break;

        case 'new_alert':
          this.handleLiveAlert(payload.data);
          break;

        case 'risk_update':
          this.handleRiskUpdate(payload.data);
          break;

        case 'initial_data':
          if (payload.data) {
            if (payload.data.sensors) this.updateSensorArray(payload.data.sensors);
            if (payload.data.alerts) this.updateAlertsList(payload.data.alerts);
          }
          break;

        default:
          break;
      }
    }

    handleLiveSensorUpdate(sensorData) {
      if (!sensorData) return;
      if (window.soundEngine) window.soundEngine.playToggle();
      if (window.telemetryFeed) {
        const id = sensorData.sensor_id || 'SENSOR';
        const val = sensorData.water_level_m !== undefined ? `${sensorData.water_level_m}m water level` : `${sensorData.value || ''}`;
        window.telemetryFeed.logEvent('MQTT_SENSOR', `Update from ${id}: ${val} (Risk: ${sensorData.risk_level || 'NORMAL'})`, 'info');
      }
    }

    handleLiveAlert(alert) {
      if (!alert) return;
      if (window.soundEngine) window.soundEngine.playEmergencyAlarm();
      if (window.telemetryFeed) {
        window.telemetryFeed.triggerCapAlert(`[${alert.risk_level || 'WARNING'}] ${alert.message}`, alert.risk_level || 'CRITICAL');
      }
    }

    handleRiskUpdate(riskData) {
      console.log('Risk update received:', riskData);
    }

    /**
     * Fetch Live REST APIs from FastAPI backend
     */
    async fetchInitialAPIData() {
      const q = `lat=${this.regionParams.lat}&lon=${this.regionParams.lon}&radius_km=${this.regionParams.radiusKm}`;

      try {
        // 1. Fetch Backend Statistics
        const statRes = await fetch(`${this.apiBaseUrl}/api/dashboard/statistics?${q}`);
        if (statRes.ok) {
          const stats = await statRes.json();
          this.applyBackendStats(stats);
        }

        // 2. Fetch Live Sensors
        const sensorRes = await fetch(`${this.apiBaseUrl}/api/live/sensors?${q}`);
        if (sensorRes.ok) {
          const sensors = await sensorRes.json();
          this.updateSensorArray(sensors);
        }

        // 3. Fetch Central Water Commission River Gauge Levels
        const riverRes = await fetch(`${this.apiBaseUrl}/api/live/river-levels?${q}`);
        if (riverRes.ok) {
          const rivers = await riverRes.json();
          this.riverGauges = rivers.gauges || rivers || [];
          this.renderRiverGaugesOnMap();
        }

        // 4. Fetch USGS Earthquakes
        const quakeRes = await fetch(`${this.apiBaseUrl}/api/live/earthquakes/near?${q}&min_magnitude=2.5`);
        if (quakeRes.ok) {
          const quakes = await quakeRes.json();
          this.earthquakes = quakes.earthquakes || quakes || [];
          this.renderEarthquakesOnMap();
        }

        // 5. Fetch India Disaster Warnings
        const warnRes = await fetch(`${this.apiBaseUrl}/api/live/india-warnings`);
        if (warnRes.ok) {
          const warnings = await warnRes.json();
          if (warnings.warnings && warnings.warnings.length > 0) {
            const topWarn = warnings.warnings[0];
            if (window.telemetryFeed) {
              window.telemetryFeed.logEvent('IMD_WARN', `${topWarn.title || topWarn.description || 'Severe Weather Warning'}`, 'warn');
            }
          }
        }
      } catch (err) {
        console.warn('Backend REST endpoint fetch error (running in fallback mode):', err);
      }
    }

    applyBackendStats(stats) {
      if (!stats) return;
      const popElem = document.getElementById('header-affected-pop');
      if (popElem && stats.total_population_affected) {
        popElem.textContent = parseInt(stats.total_population_affected).toLocaleString();
      }
    }

    updateSensorArray(sensors) {
      const list = Array.isArray(sensors) ? sensors : (sensors.sensors || []);
      this.liveSensorCount = list.length;
      const badge = document.getElementById('live-sensor-count-badge');
      if (badge) badge.textContent = `${this.liveSensorCount} IOT SENSORS`;

      // Add sensor pins to 2D Leaflet map
      if (window.mapEngine && window.mapEngine.map && window.L) {
        list.slice(0, 15).forEach(s => {
          if (!s.latitude || !s.longitude) return;
          const markerHtml = `
            <div style="background:rgba(10,14,26,0.9); border:1px solid #00f0ff; border-radius:50%; width:16px; height:16px; display:flex; align-items:center; justify-content:center; box-shadow:0 0 6px rgba(0,240,255,0.6);">
              <span style="width:6px; height:6px; border-radius:50%; background:${s.risk_level === 'CRITICAL' ? '#ff3366' : '#00f0ff'};"></span>
            </div>
          `;
          const icon = window.L.divIcon({ html: markerHtml, className: '', iconSize: [16, 16] });
          const m = window.L.marker([s.latitude, s.longitude], { icon });
          m.bindPopup(`
            <div style="font-family:monospace; font-size:11px;">
              <strong>${s.sensor_id || 'IoT Water Level Sensor'}</strong><br>
              Type: ${s.sensor_type || 'Ultrasonic Gauge'}<br>
              Water Level: ${s.water_level_m !== undefined ? s.water_level_m + ' m' : (s.value || 'N/A')}<br>
              Status: <span style="color:#00ff88;">ONLINE (MQTT)</span>
            </div>
          `);
          if (window.mapEngine.layerGroups.units) {
            window.mapEngine.layerGroups.units.addLayer(m);
          }
        });
      }
    }

    updateAlertsList(alerts) {
      const list = Array.isArray(alerts) ? alerts : (alerts.alerts || []);
      if (list.length > 0 && window.telemetryFeed) {
        const top = list[0];
        window.telemetryFeed.logEvent('ALERT_FEED', top.message || top.headline || 'Active Risk Advisory', 'alert');
      }
    }

    renderRiverGaugesOnMap() {
      if (!window.mapEngine || !window.mapEngine.map || !window.L || !this.riverGauges) return;
      this.riverGauges.slice(0, 10).forEach(g => {
        if (!g.latitude || !g.longitude) return;
        const iconHtml = `
          <div style="background:rgba(2,132,199,0.9); border:1px solid #38bdf8; border-radius:3px; padding:1px 4px; font-family:monospace; font-size:8px; color:#fff; white-space:nowrap;">
            🌊 ${g.station_name || 'CWC River Gauge'}: ${g.current_level_m || g.water_level_m || 24.5}m
          </div>
        `;
        const icon = window.L.divIcon({ html: iconHtml, className: '', iconSize: [100, 18] });
        const marker = window.L.marker([g.latitude, g.longitude], { icon });
        marker.bindPopup(`
          <div style="font-family:monospace; font-size:11px;">
            <strong>${g.station_name || 'Central Water Commission Gauge'}</strong><br>
            River: ${g.river_name || 'Narmada River'}<br>
            Water Level: ${g.current_level_m || 24.5} m (Danger: ${g.danger_level_m || 28.0} m)<br>
            Trend: ${g.trend || 'RISING'}
          </div>
        `);
        if (window.mapEngine.layerGroups.disasters) {
          window.mapEngine.layerGroups.disasters.addLayer(marker);
        }
      });
    }

    renderEarthquakesOnMap() {
      if (!window.mapEngine || !window.mapEngine.map || !window.L || !this.earthquakes) return;
      this.earthquakes.slice(0, 8).forEach(eq => {
        const coords = eq.geometry ? eq.geometry.coordinates : [eq.longitude, eq.latitude];
        if (!coords || coords.length < 2) return;
        const lon = coords[0], lat = coords[1];
        const mag = eq.properties ? eq.properties.mag : (eq.magnitude || 3.4);

        const iconHtml = `
          <div style="width:20px; height:20px; border-radius:50%; border:2px solid #ffaa00; background:rgba(255,170,0,0.3); display:flex; align-items:center; justify-content:center; font-family:monospace; font-size:8px; color:#fff; font-weight:700;">
            M${parseFloat(mag).toFixed(1)}
          </div>
        `;
        const icon = window.L.divIcon({ html: iconHtml, className: '', iconSize: [20, 20] });
        const marker = window.L.marker([lat, lon], { icon });
        marker.bindPopup(`
          <div style="font-family:monospace; font-size:11px;">
            <strong>USGS Live Earthquake: M${mag}</strong><br>
            Location: ${eq.properties ? eq.properties.place : (eq.place || 'Seismic Event')}<br>
            Depth: ${coords[2] || 10} km<br>
            Time: ${new Date(eq.properties ? eq.properties.time : Date.now()).toLocaleString()}
          </div>
        `);
        if (window.mapEngine.layerGroups.disasters) {
          window.mapEngine.layerGroups.disasters.addLayer(marker);
        }
      });
    }

    simulateLiveFeeds() {
      // Offline fallback telemetry simulation
      setInterval(() => {
        if (window.telemetryFeed) {
          const randLevel = (2.2 + Math.random() * 0.8).toFixed(2);
          window.telemetryFeed.logEvent('MQTT_SENSOR', `Narmada Gauge 04: Water level ${randLevel}m (Discharge: 1,840 m³/s)`, 'info');
        }
      }, 12000);
    }
  }

  window.backendBridge = new FastAPIBackendBridge();
  window.addEventListener('DOMContentLoaded', () => {
    if (window.backendBridge) window.backendBridge.init();
  });

})(window);
