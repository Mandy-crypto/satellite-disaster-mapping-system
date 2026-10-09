/**
 * ============================================================================
 * ASTRA-GEO // SATELLITE DISASTER INTELLIGENCE PLATFORM
 * 2D TACTICAL GIS GEOSPATIAL MAP ENGINE
 * ============================================================================
 * High-performance Leaflet & Canvas tactical GIS engine with vector overlays,
 * animated active fire fronts, flood surge contours, hurricane wind radii,
 * first responder assets, satellite ground tracks, and geodesic tools.
 */

(function (window) {
  'use strict';

  class TacticalMapEngine {
    constructor() {
      this.map = null;
      this.vectorCanvas = null;
      this.vectorCtx = null;
      this.activeTileLayer = null;
      this.layerGroups = {
        disasters: null,
        satellites: null,
        units: null,
        shelters: null,
        evacuationRoutes: null
      };
      this.layerVisibility = {
        disasters: true,
        satellites: true,
        units: true,
        shelters: true,
        evacuationRoutes: true,
        radarSweep: true,
        mgrsGrid: false
      };
      this.currentDisaster = null;
      this.animFrameId = null;
    }

    init(containerId = 'leaflet-map-container') {
      const container = document.getElementById(containerId);
      if (!container) return;

      // Initialize Leaflet Map (fallback to custom canvas if Leaflet CDN is delayed)
      if (typeof window.L !== 'undefined') {
        this.map = window.L.map(containerId, {
          center: [39.4699, -0.3763], // Default Valencia
          zoom: 11,
          zoomControl: false,
          attributionControl: false
        });

        // Dark Matter Tactical Basemap
        this.activeTileLayer = window.L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
          maxZoom: 19,
          subdomains: 'abcd'
        }).addTo(this.map);

        // Initialize Layer Groups
        this.layerGroups.disasters = window.L.layerGroup().addTo(this.map);
        this.layerGroups.satellites = window.L.layerGroup().addTo(this.map);
        this.layerGroups.units = window.L.layerGroup().addTo(this.map);
        this.layerGroups.shelters = window.L.layerGroup().addTo(this.map);
        this.layerGroups.evacuationRoutes = window.L.layerGroup().addTo(this.map);

        this.setupMapEvents();
      }

      this.initVectorCanvas();
      this.loadInitialData();

      // Listen for disaster manager selection
      if (window.disasterManager) {
        window.disasterManager.subscribe((type, data) => {
          if (type === 'DISASTER_SELECTED') {
            this.focusDisaster(data);
          }
        });
      }

      this.startAnimationLoop();
    }

    initVectorCanvas() {
      this.vectorCanvas = document.getElementById('tactical-vector-canvas');
      if (this.vectorCanvas) {
        this.vectorCtx = this.vectorCanvas.getContext('2d');
        this.resizeVectorCanvas();
        window.addEventListener('resize', () => this.resizeVectorCanvas());
      }
    }

    resizeVectorCanvas() {
      if (!this.vectorCanvas) return;
      const rect = this.vectorCanvas.parentElement.getBoundingClientRect();
      this.vectorCanvas.width = rect.width;
      this.vectorCanvas.height = rect.height;
    }

    setupMapEvents() {
      if (!this.map) return;

      this.map.on('mousemove', (e) => {
        const hudLat = document.getElementById('hud-coord-lat');
        const hudLon = document.getElementById('hud-coord-lon');
        if (hudLat) hudLat.textContent = `${e.latlng.lat.toFixed(4)}° N`;
        if (hudLon) hudLon.textContent = `${e.latlng.lng.toFixed(4)}° E`;
      });

      this.map.on('move', () => {
        this.drawCanvasOverlays();
      });
      this.map.on('zoom', () => {
        this.drawCanvasOverlays();
      });
    }

    loadInitialData() {
      if (window.disasterManager) {
        const active = window.disasterManager.getSelected();
        if (active) this.focusDisaster(active);
      }
      this.renderSatellites();
      this.renderFirstResponders();
    }

    /**
     * Switch Basemap Style (Dark Matter, Satellite Imagery, Topographic)
     */
    setBaseLayer(style) {
      if (!this.map || !window.L) return;
      if (this.activeTileLayer) {
        this.map.removeLayer(this.activeTileLayer);
      }

      if (style === 'satellite') {
        this.activeTileLayer = window.L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
          maxZoom: 18
        });
      } else if (style === 'osm') {
        this.activeTileLayer = window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
          maxZoom: 19
        });
      } else {
        this.activeTileLayer = window.L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
          maxZoom: 19
        });
      }

      this.activeTileLayer.addTo(this.map);
    }

    toggleLayer(layerKey, isVisible) {
      this.layerVisibility[layerKey] = isVisible;
      if (this.layerGroups[layerKey] && this.map) {
        if (isVisible) {
          this.map.addLayer(this.layerGroups[layerKey]);
        } else {
          this.map.removeLayer(this.layerGroups[layerKey]);
        }
      }
      this.drawCanvasOverlays();
    }

    /**
     * Pan & Fly smoothly to Disaster coordinates and render hazard perimeters
     */
    focusDisaster(disaster) {
      if (!disaster || !this.map || !window.L) return;
      this.currentDisaster = disaster;

      const lat = disaster.location.lat;
      const lon = disaster.location.lon;
      const zoom = disaster.location.zoom || 11;

      this.map.flyTo([lat, lon], zoom, { duration: 1.5 });

      // Clear old disaster layers
      if (this.layerGroups.disasters) this.layerGroups.disasters.clearLayers();
      if (this.layerGroups.shelters) this.layerGroups.shelters.clearLayers();
      if (this.layerGroups.evacuationRoutes) this.layerGroups.evacuationRoutes.clearLayers();

      // 1. Render Disaster Center Marker
      const disasterPinHtml = `
        <div class="tactical-marker-pin" style="color: ${this.getHazardColor(disaster.type)};">
          <div class="pin-pulse"></div>
          <div class="pin-core" style="background: ${this.getHazardColor(disaster.type)};"></div>
        </div>
      `;
      const disasterIcon = window.L.divIcon({ html: disasterPinHtml, className: '', iconSize: [28, 28] });
      const mainMarker = window.L.marker([lat, lon], { icon: disasterIcon });
      mainMarker.bindPopup(`
        <div style="font-family: monospace; font-size: 11px;">
          <strong style="color: #00f0ff;">${disaster.title}</strong><br>
          Type: ${disaster.type} | ${disaster.severity}<br>
          Casualties: ${disaster.metrics.casualties || 0}<br>
          Affected: ${(disaster.metrics.affectedPopulation || 0).toLocaleString()}
        </div>
      `);
      this.layerGroups.disasters.addLayer(mainMarker);

      // 2. Render Hazard-Specific Polygons & Contours
      this.renderHazardSpecifics(disaster);

      // 3. Render Shelters
      (disaster.shelterLocations || []).forEach(s => {
        const shelterHtml = `
          <div style="background: rgba(16,22,38,0.9); border: 1px solid #00ff88; border-radius: 3px; padding: 2px 5px; font-family: monospace; font-size: 9px; color: #00ff88; white-space: nowrap; box-shadow: 0 0 6px rgba(0,255,136,0.4);">
            🏥 ${s.name} (${s.occupancy}/${s.capacity})
          </div>
        `;
        const shelterIcon = window.L.divIcon({ html: shelterHtml, className: '', iconSize: [120, 20] });
        const marker = window.L.marker([s.lat, s.lon], { icon: shelterIcon });
        this.layerGroups.shelters.addLayer(marker);
      });

      // 4. Render Evacuation Route
      if (window.routePlanner) {
        window.routePlanner.buildTacticalNetwork(lat, lon, disaster.evacuationCorridors || []);
        const route = window.routePlanner.findSafeEvacuationRoute(lat, lon);
        if (route && route.coordinates.length > 0) {
          const polyline = window.L.polyline(route.coordinates, {
            color: '#00f0ff',
            weight: 3.5,
            dashArray: '6, 6',
            opacity: 0.9
          });
          polyline.bindPopup(`<strong>RECOMMENDED EVACUATION CORRIDOR</strong><br>Distance: ${route.totalDistanceKm} km | ETA: ${route.estimatedMinutes} mins`);
          this.layerGroups.evacuationRoutes.addLayer(polyline);
        }
      }
    }

    renderHazardSpecifics(disaster) {
      if (!window.L || !this.map) return;
      const lat = disaster.location.lat;
      const lon = disaster.location.lon;

      if (disaster.category === 'cat-flood' && window.floodModel) {
        const contours = window.floodModel.generateFloodContours(lat, lon, 6.5, disaster.hazardTelemetry.floodSurgeHeightM || 2.8);
        contours.forEach(c => {
          const poly = window.L.polygon(c.coordinates, {
            color: c.color,
            fillColor: c.color,
            fillOpacity: 0.28,
            weight: 1.5
          });
          poly.bindPopup(`<strong>${c.tier}</strong><br>Depth: ${c.waterDepthM} meters`);
          this.layerGroups.disasters.addLayer(poly);
        });
      } else if (disaster.category === 'cat-wildfire' && window.wildfireModel) {
        const perimeters = window.wildfireModel.generateSpreadPerimeters(lat, lon, 55, 32, 4);
        perimeters.forEach((p, idx) => {
          const poly = window.L.polygon(p.coordinates, {
            color: idx === 0 ? '#ff3366' : '#ff9800',
            fillColor: '#ff5722',
            fillOpacity: 0.22,
            weight: 2
          });
          poly.bindPopup(`<strong>Active Fire Perimeter Hour ${p.hour}</strong><br>Area: ${p.areaSqKm} km² | Containment: ${p.containmentPct}%`);
          this.layerGroups.disasters.addLayer(poly);
        });
      } else if (disaster.category === 'cat-cyclone' && window.cycloneModel) {
        const windRings = window.cycloneModel.generateWindRadiiPolygons(lat, lon, 902, 22);
        windRings.forEach(ring => {
          const poly = window.L.polygon(ring.coordinates, {
            color: ring.color,
            fillColor: ring.color,
            fillOpacity: 0.15,
            weight: 1.5
          });
          poly.bindPopup(`<strong>${ring.name}</strong><br>Radius: ${ring.radiusKm} km`);
          this.layerGroups.disasters.addLayer(poly);
        });

        // Forecast track
        const ensemble = window.cycloneModel.generateEnsembleForecast(lat, lon, 42, 16, 48);
        const conePoly = window.L.polygon(ensemble.conePolygon, {
          color: 'rgba(0, 240, 255, 0.5)',
          fillColor: 'rgba(0, 240, 255, 0.12)',
          weight: 1.2
        });
        this.layerGroups.disasters.addLayer(conePoly);
      }
    }

    renderSatellites() {
      if (!this.map || !window.L || !window.SatelliteCatalog) return;
      if (this.layerGroups.satellites) this.layerGroups.satellites.clearLayers();

      const activeSats = window.SatelliteCatalog.getAllActive().slice(0, 6);
      const now = new Date();

      activeSats.forEach(sat => {
        const pos = window.orbitPropagator.propagate(sat, now);
        const satHtml = `
          <div class="satellite-map-marker">
            <div class="sat-icon" style="color:${sat.color}; border-color:${sat.color};">🛰️</div>
            <div class="sat-name">${sat.name}</div>
          </div>
        `;
        const icon = window.L.divIcon({ html: satHtml, className: '', iconSize: [50, 40], iconAnchor: [25, 20] });
        const marker = window.L.marker([pos.lat, pos.lon], { icon });
        marker.bindPopup(`
          <div style="font-family: monospace; font-size: 11px;">
            <strong>${sat.name}</strong> (${sat.agency})<br>
            Type: ${sat.type}<br>
            Altitude: ${pos.altKm.toFixed(0)} km | Speed: ${pos.velocityKmS} km/s<br>
            Swath: ${sat.swathWidthKm} km
          </div>
        `);
        this.layerGroups.satellites.addLayer(marker);

        // Ground track line
        const tracks = window.orbitPropagator.generateGroundTrack(sat, now, 45, 120);
        const polyline = window.L.polyline(tracks.futureTrack, {
          color: sat.color || '#00f0ff',
          weight: 1.5,
          opacity: 0.45,
          dashArray: '4, 4'
        });
        this.layerGroups.satellites.addLayer(polyline);
      });
    }

    renderFirstResponders() {
      if (!this.map || !window.L || !window.rescueDispatch) return;
      if (this.layerGroups.units) this.layerGroups.units.clearLayers();

      const units = window.rescueDispatch.getAllUnits();
      units.forEach(u => {
        const unitHtml = `
          <div style="background: rgba(10,14,26,0.9); border: 1px solid #00f0ff; border-radius: 4px; padding: 2px 6px; font-family: monospace; font-size: 9px; color: #fff; box-shadow: 0 0 8px rgba(0,240,255,0.4); display:flex; align-items:center; gap:4px;">
            <span style="display:inline-block; width:6px; height:6px; border-radius:50%; background:#00ff88;"></span>
            ${u.callsign}
          </div>
        `;
        const icon = window.L.divIcon({ html: unitHtml, className: '', iconSize: [140, 24] });
        const marker = window.L.marker([u.lat, u.lon], { icon });
        marker.bindPopup(`
          <div style="font-family: monospace; font-size: 11px;">
            <strong>${u.callsign}</strong><br>
            Type: ${u.type}<br>
            Status: ${u.status}<br>
            Personnel: ${u.personnel} | Fuel: ${u.fuelPct}%<br>
            Assigned: ${u.assignedSector}
          </div>
        `);
        this.layerGroups.units.addLayer(marker);
      });
    }

    drawCanvasOverlays() {
      if (!this.vectorCtx || !this.vectorCanvas || !this.map) return;
      const ctx = this.vectorCtx;
      const w = this.vectorCanvas.width;
      const h = this.vectorCanvas.height;

      ctx.clearRect(0, 0, w, h);

      // Draw Military Grid Reference System (MGRS) graticule if enabled
      if (this.layerVisibility.mgrsGrid) {
        ctx.strokeStyle = 'rgba(0, 240, 255, 0.12)';
        ctx.lineWidth = 1;
        const step = 80;
        for (let x = 0; x < w; x += step) {
          ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();
          ctx.fillStyle = 'rgba(0, 240, 255, 0.4)';
          ctx.font = '8px monospace';
          ctx.fillText(`30S ${Math.round(x * 12)}`, x + 4, 12);
        }
        for (let y = 0; y < h; y += step) {
          ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
          ctx.fillText(`YJ ${Math.round(y * 12)}`, 4, y - 4);
        }
      }
    }

    startAnimationLoop() {
      let frame = 0;
      const tick = () => {
        frame++;
        if (frame % 300 === 0) {
          this.renderSatellites();
        }
        this.animFrameId = requestAnimationFrame(tick);
      };
      this.animFrameId = requestAnimationFrame(tick);
    }

    getHazardColor(type) {
      if (type === 'Flood') return '#00f0ff';
      if (type === 'Earthquake') return '#ffaa00';
      if (type === 'Cyclone') return '#a855f7';
      if (type === 'Volcano') return '#ff3366';
      return '#ff5722';
    }

    zoomIn() { if (this.map) this.map.zoomIn(); }
    zoomOut() { if (this.map) this.map.zoomOut(); }
    resetView() {
      if (this.map && this.currentDisaster) {
        this.map.flyTo([this.currentDisaster.location.lat, this.currentDisaster.location.lon], this.currentDisaster.location.zoom || 11);
      }
    }
  }

  window.mapEngine = new TacticalMapEngine();

})(window);
