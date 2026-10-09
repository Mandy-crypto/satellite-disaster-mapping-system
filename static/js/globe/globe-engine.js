/**
 * ============================================================================
 * ASTRA-GEO // SATELLITE DISASTER INTELLIGENCE PLATFORM
 * INTERACTIVE 3D PLANETARY DIGITAL EARTH GLOBE ENGINE
 * ============================================================================
 * High-performance WebGL & Canvas 3D Globe with day/night terminator, atmospheric
 * glow, satellite Keplerian orbits, sensor swath footprints, laser telemetry
 * downlinks, disaster shockwave rings, and orbital camera choreography.
 */

(function (window) {
  'use strict';

  class PlanetaryGlobeEngine {
    constructor() {
      this.container = null;
      this.canvas = null;
      this.ctx = null;
      this.animId = null;
      this.width = 600;
      this.height = 600;

      // Camera & Rotation State
      this.rotX = 22.0 * (Math.PI / 180);
      this.rotY = -35.0 * (Math.PI / 180);
      this.zoom = 1.0;
      this.autoRotate = true;
      this.autoRotateSpeed = 0.0018;

      // Mouse drag state
      this.isDragging = false;
      this.prevMouseX = 0;
      this.prevMouseY = 0;

      // Visual layers
      this.satellites = [];
      this.groundStations = [];
      this.disasters = [];
      this.selectedDisaster = null;
      this.selectedSatellite = null;

      // Hover state
      this.hoveredObject = null;
      this.hoverPos = { x: 0, y: 0 };
    }

    init(containerId = 'globe-canvas-container') {
      this.container = document.getElementById(containerId);
      if (!this.container) return;

      this.canvas = document.getElementById('globe-three-canvas');
      if (!this.canvas) {
        this.canvas = document.createElement('canvas');
        this.canvas.id = 'globe-three-canvas';
        this.container.appendChild(this.canvas);
      }

      this.ctx = this.canvas.getContext('2d');
      this.handleResize();
      window.addEventListener('resize', () => this.handleResize());

      this.setupInteraction();
      this.loadFleetData();

      // Listen for disaster manager selection changes
      if (window.disasterManager) {
        window.disasterManager.subscribe((type, data) => {
          if (type === 'DISASTER_SELECTED') {
            this.focusDisaster(data);
          }
        });
      }

      this.startRenderLoop();
    }

    handleResize() {
      if (!this.container || !this.canvas) return;
      const rect = this.container.getBoundingClientRect();
      this.width = rect.width || 600;
      this.height = rect.height || 600;
      this.canvas.width = this.width;
      this.canvas.height = this.height;
    }

    loadFleetData() {
      if (window.SatelliteCatalog) {
        this.satellites = window.SatelliteCatalog.satellites;
        this.groundStations = window.SatelliteCatalog.groundStations;
      }
      if (window.DisasterCatalog) {
        this.disasters = window.DisasterCatalog.getAll();
      }
    }

    setupInteraction() {
      if (!this.canvas) return;

      this.canvas.addEventListener('mousedown', (e) => {
        this.isDragging = true;
        this.prevMouseX = e.clientX;
        this.prevMouseY = e.clientY;
        this.autoRotate = false;
      });

      window.addEventListener('mouseup', () => {
        this.isDragging = false;
      });

      this.canvas.addEventListener('mousemove', (e) => {
        const rect = this.canvas.getBoundingClientRect();
        this.hoverPos.x = e.clientX - rect.left;
        this.hoverPos.y = e.clientY - rect.top;

        if (this.isDragging) {
          const deltaX = e.clientX - this.prevMouseX;
          const deltaY = e.clientY - this.prevMouseY;
          this.rotY += deltaX * 0.006;
          this.rotX = Math.max(-1.4, Math.min(1.4, this.rotX + deltaY * 0.006));
          this.prevMouseX = e.clientX;
          this.prevMouseY = e.clientY;
        } else {
          this.checkHover(this.hoverPos.x, this.hoverPos.y);
        }
      });

      this.canvas.addEventListener('wheel', (e) => {
        e.preventDefault();
        const zoomDelta = e.deltaY * -0.001;
        this.zoom = Math.max(0.65, Math.min(2.5, this.zoom + zoomDelta));
      }, { passive: false });

      this.canvas.addEventListener('click', (e) => {
        const rect = this.canvas.getBoundingClientRect();
        const clickX = e.clientX - rect.left;
        const clickY = e.clientY - rect.top;
        this.handleClick(clickX, clickY);
      });
    }

    /**
     * Convert spherical Geodetic coordinates (lat, lon, altKm) to 3D Cartesian coordinates
     */
    geoToCartesian(latDeg, lonDeg, radius) {
      const phi = (90 - latDeg) * (Math.PI / 180);
      const theta = (lonDeg + 180) * (Math.PI / 180);

      const x = -radius * Math.sin(phi) * Math.cos(theta);
      const z = radius * Math.sin(phi) * Math.sin(theta);
      const y = radius * Math.cos(phi);

      return { x, y, z };
    }

    /**
     * Rotate 3D point by camera Euler angles (rotX, rotY)
     */
    rotatePoint(p) {
      // Rotate around Y-axis
      const x1 = p.x * Math.cos(this.rotY) + p.z * Math.sin(this.rotY);
      const y1 = p.y;
      const z1 = -p.x * Math.sin(this.rotY) + p.z * Math.cos(this.rotY);

      // Rotate around X-axis
      const x2 = x1;
      const y2 = y1 * Math.cos(this.rotX) - z1 * Math.sin(this.rotX);
      const z2 = y1 * Math.sin(this.rotX) + z1 * Math.cos(this.rotX);

      return { x: x2, y: y2, z: z2 };
    }

    /**
     * Project 3D point onto 2D canvas screen coordinates
     */
    project(p3d, globeRadius) {
      const cx = this.width / 2;
      const cy = this.height / 2;
      const scale = this.zoom;

      // Perspective projection
      const cameraDistance = globeRadius * 3.8;
      const fov = cameraDistance / (cameraDistance - p3d.z);

      const screenX = cx + p3d.x * fov * scale;
      const screenY = cy - p3d.y * fov * scale;
      const isVisible = p3d.z > -globeRadius * 0.15; // Visible on front hemisphere

      return { x: screenX, y: screenY, z: p3d.z, isVisible, scale: fov * scale };
    }

    /**
     * Smoothly focus camera on a disaster location
     */
    focusDisaster(disaster) {
      if (!disaster || !disaster.location) return;
      this.selectedDisaster = disaster;
      this.autoRotate = false;

      // Calculate target camera angles to face the disaster coordinates
      const targetRotY = -disaster.location.lon * (Math.PI / 180) - Math.PI / 2;
      const targetRotX = disaster.location.lat * (Math.PI / 180);

      // Animate smoothly
      const startRotX = this.rotX;
      const startRotY = this.rotY;
      const startZoom = this.zoom;
      const targetZoom = 1.35;
      const durationMs = 1200;
      const startTime = performance.now();

      const anim = (now) => {
        const elapsed = now - startTime;
        const progress = Math.min(1.0, elapsed / durationMs);
        const ease = 0.5 - 0.5 * Math.cos(progress * Math.PI); // Smooth cosine easing

        this.rotX = startRotX + (targetRotX - startRotX) * ease;
        this.rotY = startRotY + (targetRotY - startRotY) * ease;
        this.zoom = startZoom + (targetZoom - startZoom) * ease;

        if (progress < 1.0) {
          requestAnimationFrame(anim);
        }
      };

      requestAnimationFrame(anim);
    }

    checkHover(mouseX, mouseY) {
      this.hoveredObject = null;
      const globeRadius = Math.min(this.width, this.height) * 0.28;

      // Check disaster pins
      for (const d of this.disasters) {
        const p3d = this.geoToCartesian(d.location.lat, d.location.lon, globeRadius);
        const rot = this.rotatePoint(p3d);
        if (rot.z > 0) {
          const proj = this.project(rot, globeRadius);
          const dist = Math.hypot(mouseX - proj.x, mouseY - proj.y);
          if (dist < 14) {
            this.hoveredObject = { type: 'disaster', data: d, x: proj.x, y: proj.y };
            return;
          }
        }
      }

      // Check satellites
      for (const sat of this.satellites) {
        const pos = window.orbitPropagator.propagate(sat, new Date());
        const satRadius = globeRadius * (1 + sat.altitudeKm / 6371.0 * 0.45);
        const p3d = this.geoToCartesian(pos.lat, pos.lon, satRadius);
        const rot = this.rotatePoint(p3d);
        if (rot.z > -globeRadius * 0.2) {
          const proj = this.project(rot, globeRadius);
          const dist = Math.hypot(mouseX - proj.x, mouseY - proj.y);
          if (dist < 12) {
            this.hoveredObject = { type: 'satellite', data: sat, telemetry: pos, x: proj.x, y: proj.y };
            return;
          }
        }
      }
    }

    handleClick(clickX, clickY) {
      if (this.hoveredObject) {
        if (this.hoveredObject.type === 'disaster') {
          if (window.disasterManager) {
            window.disasterManager.selectDisaster(this.hoveredObject.data.id);
          }
        } else if (this.hoveredObject.type === 'satellite') {
          this.selectedSatellite = this.hoveredObject.data;
          if (window.soundEngine) window.soundEngine.playSatTelemetryAcquired();
          if (window.telemetryFeed) {
            window.telemetryFeed.logEvent('ORBIT', `Selected Satellite: ${this.hoveredObject.data.name} (Alt: ${this.hoveredObject.telemetry.altKm}km)`, 'info');
          }
        }
      }
    }

    startRenderLoop() {
      let lastTime = performance.now();

      const render = (now) => {
        const dt = (now - lastTime) / 1000;
        lastTime = now;

        if (this.autoRotate) {
          this.rotY += this.autoRotateSpeed;
        }

        this.drawScene(now);
        this.animId = requestAnimationFrame(render);
      };

      this.animId = requestAnimationFrame(render);
    }

    drawScene(timeMs) {
      if (!this.ctx) return;
      const ctx = this.ctx;
      const w = this.width;
      const h = this.height;
      const cx = w / 2;
      const cy = h / 2;
      const globeRadius = Math.min(w, h) * 0.28 * this.zoom;

      // Clear Canvas
      ctx.clearRect(0, 0, w, h);

      // Deep space atmospheric glow
      const spaceGlow = ctx.createRadialGradient(cx, cy, globeRadius * 0.8, cx, cy, globeRadius * 1.6);
      spaceGlow.addColorStop(0, 'rgba(0, 240, 255, 0.12)');
      spaceGlow.addColorStop(0.5, 'rgba(16, 32, 64, 0.08)');
      spaceGlow.addColorStop(1, 'transparent');
      ctx.fillStyle = spaceGlow;
      ctx.beginPath();
      ctx.arc(cx, cy, globeRadius * 1.6, 0, Math.PI * 2);
      ctx.fill();

      // Earth Globe Sphere Background
      const earthGrad = ctx.createRadialGradient(cx - globeRadius * 0.35, cy - globeRadius * 0.35, globeRadius * 0.1, cx, cy, globeRadius);
      earthGrad.addColorStop(0, '#10223d');
      earthGrad.addColorStop(0.65, '#091324');
      earthGrad.addColorStop(1, '#040812');

      ctx.fillStyle = earthGrad;
      ctx.beginPath();
      ctx.arc(cx, cy, globeRadius, 0, Math.PI * 2);
      ctx.fill();

      // Draw Continents Geometry (Procedural Vectors)
      this.drawContinents(ctx, globeRadius);

      // Draw Lat/Lon Graticule Lines
      this.drawGraticule(ctx, globeRadius);

      // Draw Day / Night Terminator Line
      this.drawTerminator(ctx, globeRadius, timeMs);

      // Draw Ground Stations & Downlink Beams
      this.drawGroundStations(ctx, globeRadius, timeMs);

      // Draw Satellite Orbits & Constellations
      this.drawSatellites(ctx, globeRadius, timeMs);

      // Draw Disaster Hotspot Shockwaves & Pins
      this.drawDisasterPins(ctx, globeRadius, timeMs);

      // Draw Atmospheric Edge Glow Rim
      const rimGrad = ctx.createRadialGradient(cx, cy, globeRadius * 0.94, cx, cy, globeRadius);
      rimGrad.addColorStop(0, 'transparent');
      rimGrad.addColorStop(0.85, 'rgba(0, 240, 255, 0.25)');
      rimGrad.addColorStop(1, 'rgba(0, 240, 255, 0.55)');
      ctx.fillStyle = rimGrad;
      ctx.beginPath();
      ctx.arc(cx, cy, globeRadius, 0, Math.PI * 2);
      ctx.fill();

      // Draw Tooltip on Hover
      this.drawHoverTooltip(ctx);
    }

    drawGraticule(ctx, globeRadius) {
      ctx.strokeStyle = 'rgba(0, 240, 255, 0.08)';
      ctx.lineWidth = 1;

      // Parallels (Latitude lines)
      for (let lat = -60; lat <= 60; lat += 30) {
        ctx.beginPath();
        let started = false;
        for (let lon = -180; lon <= 180; lon += 6) {
          const p = this.geoToCartesian(lat, lon, globeRadius);
          const r = this.rotatePoint(p);
          if (r.z > 0) {
            const proj = this.project(r, globeRadius);
            if (!started) { ctx.moveTo(proj.x, proj.y); started = true; }
            else { ctx.lineTo(proj.x, proj.y); }
          } else {
            started = false;
          }
        }
        ctx.stroke();
      }

      // Meridians (Longitude lines)
      for (let lon = -180; lon < 180; lon += 45) {
        ctx.beginPath();
        let started = false;
        for (let lat = -85; lat <= 85; lat += 5) {
          const p = this.geoToCartesian(lat, lon, globeRadius);
          const r = this.rotatePoint(p);
          if (r.z > 0) {
            const proj = this.project(r, globeRadius);
            if (!started) { ctx.moveTo(proj.x, proj.y); started = true; }
            else { ctx.lineTo(proj.x, proj.y); }
          } else {
            started = false;
          }
        }
        ctx.stroke();
      }
    }

    drawContinents(ctx, globeRadius) {
      // Simplified continent polygon clusters
      const landClusters = [
        // North America
        [[70, -160], [72, -125], [60, -95], [55, -60], [45, -65], [30, -80], [25, -80], [20, -100], [30, -115], [48, -125], [60, -140], [70, -160]],
        // South America
        [[10, -75], [5, -52], [-10, -36], [-25, -45], [-50, -68], [-55, -72], [-35, -73], [-15, -75], [0, -80], [10, -75]],
        // Eurasia
        [[70, 30], [75, 80], [72, 140], [60, 160], [40, 140], [35, 120], [20, 110], [10, 100], [25, 70], [30, 50], [40, 30], [55, 10], [65, 15], [70, 30]],
        // Africa
        [[35, -5], [32, 32], [12, 45], [-5, 40], [-34, 20], [-32, 16], [-15, 12], [5, 2], [15, -17], [30, -10], [35, -5]],
        // Australia
        [[-15, 130], [-12, 142], [-25, 152], [-38, 145], [-35, 116], [-20, 115], [-15, 130]],
        // Antarctica
        [[-70, -160], [-72, -90], [-68, -20], [-67, 50], [-65, 120], [-70, 170], [-70, -160]]
      ];

      ctx.fillStyle = 'rgba(0, 240, 255, 0.09)';
      ctx.strokeStyle = 'rgba(0, 240, 255, 0.22)';
      ctx.lineWidth = 1;

      landClusters.forEach(cluster => {
        ctx.beginPath();
        let first = true;
        let anyVisible = false;

        cluster.forEach(pt => {
          const p = this.geoToCartesian(pt[0], pt[1], globeRadius);
          const r = this.rotatePoint(p);
          if (r.z > -globeRadius * 0.1) {
            anyVisible = true;
            const proj = this.project(r, globeRadius);
            if (first) { ctx.moveTo(proj.x, proj.y); first = false; }
            else { ctx.lineTo(proj.x, proj.y); }
          }
        });

        if (anyVisible) {
          ctx.closePath();
          ctx.fill();
          ctx.stroke();
        }
      });
    }

    drawTerminator(ctx, globeRadius, timeMs) {
      // Day/Night shadow arc
      const sunAngle = (timeMs * 0.00004) % (Math.PI * 2);
      ctx.save();
      ctx.beginPath();
      ctx.arc(this.width / 2, this.height / 2, globeRadius, 0, Math.PI * 2);
      ctx.clip();

      const shadow = ctx.createLinearGradient(
        this.width / 2 + Math.cos(sunAngle) * globeRadius,
        this.height / 2 + Math.sin(sunAngle) * globeRadius,
        this.width / 2 - Math.cos(sunAngle) * globeRadius,
        this.height / 2 - Math.sin(sunAngle) * globeRadius
      );
      shadow.addColorStop(0, 'transparent');
      shadow.addColorStop(0.5, 'rgba(0, 0, 0, 0.15)');
      shadow.addColorStop(1, 'rgba(0, 3, 10, 0.58)');

      ctx.fillStyle = shadow;
      ctx.fillRect(0, 0, this.width, this.height);
      ctx.restore();
    }

    drawGroundStations(ctx, globeRadius, timeMs) {
      this.groundStations.forEach(gs => {
        const p = this.geoToCartesian(gs.lat, gs.lon, globeRadius);
        const r = this.rotatePoint(p);
        if (r.z > 0) {
          const proj = this.project(r, globeRadius);

          // Draw Ground Station antenna dot
          ctx.fillStyle = '#facc15';
          ctx.beginPath();
          ctx.arc(proj.x, proj.y, 3, 0, Math.PI * 2);
          ctx.fill();

          // Pulsing radio wave ring
          const ringRad = 4 + (Math.sin(timeMs * 0.005 + gs.lat) + 1) * 4;
          ctx.strokeStyle = 'rgba(250, 204, 21, 0.4)';
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.arc(proj.x, proj.y, ringRad, 0, Math.PI * 2);
          ctx.stroke();
        }
      });
    }

    drawSatellites(ctx, globeRadius, timeMs) {
      const now = new Date();

      this.satellites.forEach(sat => {
        const pos = window.orbitPropagator.propagate(sat, now);
        const satAltitudeRatio = (sat.altitudeKm || 700) / 6371.0;
        const satRadius = globeRadius * (1 + satAltitudeRatio * 0.4);

        // 1. Draw 3D Orbit Ring
        ctx.strokeStyle = sat.color ? `${sat.color}33` : 'rgba(0, 240, 255, 0.2)';
        ctx.lineWidth = 1;
        ctx.beginPath();
        const steps = 60;
        let prevVis = false;

        for (let i = 0; i <= steps; i++) {
          const t = new Date(now.getTime() + (i / steps) * sat.periodMin * 60000);
          const pPos = window.orbitPropagator.propagate(sat, t);
          const p = this.geoToCartesian(pPos.lat, pPos.lon, satRadius);
          const r = this.rotatePoint(p);

          if (r.z > -globeRadius * 0.1) {
            const proj = this.project(r, globeRadius);
            if (!prevVis) { ctx.moveTo(proj.x, proj.y); prevVis = true; }
            else { ctx.lineTo(proj.x, proj.y); }
          } else {
            prevVis = false;
          }
        }
        ctx.stroke();

        // 2. Draw Satellite Body & Solar Arrays
        const satPoint = this.geoToCartesian(pos.lat, pos.lon, satRadius);
        const satRot = this.rotatePoint(satPoint);

        if (satRot.z > -globeRadius * 0.2) {
          const satProj = this.project(satRot, globeRadius);

          // Sub-satellite ground footprint circle
          const groundPoint = this.geoToCartesian(pos.lat, pos.lon, globeRadius);
          const groundRot = this.rotatePoint(groundPoint);
          if (groundRot.z > 0) {
            const gProj = this.project(groundRot, globeRadius);
            // Footprint swath cone
            ctx.fillStyle = sat.type.includes('SAR') ? 'rgba(0, 255, 136, 0.08)' : 'rgba(0, 240, 255, 0.08)';
            ctx.beginPath();
            ctx.arc(gProj.x, gProj.y, 14 * this.zoom, 0, Math.PI * 2);
            ctx.fill();

            // Slew line from sat to ground
            ctx.strokeStyle = 'rgba(255, 255, 255, 0.25)';
            ctx.setLineDash([2, 4]);
            ctx.beginPath();
            ctx.moveTo(satProj.x, satProj.y);
            ctx.lineTo(gProj.x, gProj.y);
            ctx.stroke();
            ctx.setLineDash([]);
          }

          // Satellite Core Cube & Panels
          ctx.fillStyle = sat.color || '#00f0ff';
          ctx.beginPath();
          ctx.arc(satProj.x, satProj.y, 4, 0, Math.PI * 2);
          ctx.fill();

          // Solar wings
          ctx.strokeStyle = '#38bdf8';
          ctx.lineWidth = 1.5;
          ctx.beginPath();
          ctx.moveTo(satProj.x - 7, satProj.y);
          ctx.lineTo(satProj.x + 7, satProj.y);
          ctx.stroke();

          // Satellite Label
          ctx.font = '9px monospace';
          ctx.fillStyle = '#e2e8f0';
          ctx.fillText(sat.name, satProj.x + 8, satProj.y - 3);

          // Telemetry Downlink Beam to Svalbard or active ground station
          if (sat.id === 'sentinel-2a' || sat.id === 'worldview-3') {
            const gs = this.groundStations[0]; // SKS
            const gsPoint = this.geoToCartesian(gs.lat, gs.lon, globeRadius);
            const gsRot = this.rotatePoint(gsPoint);
            if (gsRot.z > 0) {
              const gsProj = this.project(gsRot, globeRadius);
              ctx.strokeStyle = 'rgba(0, 255, 136, 0.6)';
              ctx.lineWidth = 1.2;
              ctx.beginPath();
              ctx.moveTo(satProj.x, satProj.y);
              ctx.lineTo(gsProj.x, gsProj.y);
              ctx.stroke();
            }
          }
        }
      });
    }

    drawDisasterPins(ctx, globeRadius, timeMs) {
      this.disasters.forEach(d => {
        const p = this.geoToCartesian(d.location.lat, d.location.lon, globeRadius);
        const r = this.rotatePoint(p);

        if (r.z > 0) {
          const proj = this.project(r, globeRadius);
          const isSelected = this.selectedDisaster && this.selectedDisaster.id === d.id;

          // Color by hazard type
          let pinColor = '#ff5722';
          if (d.type === 'Flood') pinColor = '#00f0ff';
          if (d.type === 'Earthquake') pinColor = '#ffaa00';
          if (d.type === 'Cyclone') pinColor = '#a855f7';
          if (d.type === 'Volcano') pinColor = '#ff3366';

          // Pulsing Shockwave Rings
          const wavePhase = (timeMs * 0.003) % 1;
          const waveRadius = 6 + wavePhase * 22;
          ctx.strokeStyle = pinColor;
          ctx.lineWidth = isSelected ? 2 : 1;
          ctx.globalAlpha = 1.0 - wavePhase;
          ctx.beginPath();
          ctx.arc(proj.x, proj.y, waveRadius, 0, Math.PI * 2);
          ctx.stroke();
          ctx.globalAlpha = 1.0;

          // Pin Core Dot
          ctx.fillStyle = pinColor;
          ctx.beginPath();
          ctx.arc(proj.x, proj.y, isSelected ? 6 : 4, 0, Math.PI * 2);
          ctx.fill();

          ctx.fillStyle = '#fff';
          ctx.beginPath();
          ctx.arc(proj.x, proj.y, 2, 0, Math.PI * 2);
          ctx.fill();

          // Title Tag
          if (isSelected) {
            ctx.font = 'bold 10px monospace';
            ctx.fillStyle = '#fff';
            ctx.fillText(d.title, proj.x + 10, proj.y - 4);
          }
        }
      });
    }

    drawHoverTooltip(ctx) {
      if (!this.hoveredObject) return;
      const h = this.hoveredObject;
      const x = Math.min(this.width - 220, Math.max(10, h.x + 12));
      const y = Math.min(this.height - 80, Math.max(10, h.y - 40));

      ctx.fillStyle = 'rgba(10, 14, 26, 0.92)';
      ctx.strokeStyle = 'rgba(0, 240, 255, 0.5)';
      ctx.lineWidth = 1;
      ctx.fillRect(x, y, 200, 55);
      ctx.strokeRect(x, y, 200, 55);

      ctx.fillStyle = '#fff';
      ctx.font = 'bold 11px monospace';

      if (h.type === 'disaster') {
        ctx.fillText(h.data.title, x + 8, y + 18);
        ctx.font = '10px monospace';
        ctx.fillStyle = '#00f0ff';
        ctx.fillText(`${h.data.type} | ${h.data.severity}`, x + 8, y + 33);
        ctx.fillStyle = '#94a3b8';
        ctx.fillText(h.data.location.name, x + 8, y + 47);
      } else if (h.type === 'satellite') {
        ctx.fillText(h.data.name, x + 8, y + 18);
        ctx.font = '10px monospace';
        ctx.fillStyle = '#00ff88';
        ctx.fillText(`${h.data.type}`, x + 8, y + 33);
        ctx.fillStyle = '#94a3b8';
        ctx.fillText(`Alt: ${h.telemetry.altKm.toFixed(0)} km | ${h.telemetry.velocityKmS} km/s`, x + 8, y + 47);
      }
    }
  }

  window.globeEngine = new PlanetaryGlobeEngine();

})(window);
