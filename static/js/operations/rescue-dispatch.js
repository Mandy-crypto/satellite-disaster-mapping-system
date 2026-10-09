/**
 * ============================================================================
 * ASTRA-GEO // SATELLITE DISASTER INTELLIGENCE PLATFORM
 * EMERGENCY RESPONSE UNIT DISPATCH & SYNTHETIC UAV DRONE STREAM ENGINE
 * ============================================================================
 * Tracks search & rescue (SAR) units, dispatches emergency teams, and renders
 * a real-time synthetic FLIR thermal & optical UAV drone video feed on canvas.
 */

(function (window) {
  'use strict';

  const DEFAULT_UNITS = [
    {
      id: 'SAR-ALPHA',
      callsign: 'Paiporta USAR Task Force 1',
      type: 'Heavy Urban Search & Rescue',
      lat: 39.428,
      lon: -0.418,
      status: 'ON_SCENE',
      personnel: 38,
      fuelPct: 82,
      assignedSector: 'Sector Bravo - Collapsed Basements',
      etaMinutes: 0
    },
    {
      id: 'SAR-BRAVO',
      callsign: 'Swiftwater Rescue Boat Unit 4',
      type: 'Amphibious Swiftwater Inundation',
      lat: 39.412,
      lon: -0.385,
      status: 'DISPATCHED',
      personnel: 14,
      fuelPct: 65,
      assignedSector: 'Sedaví Industrial Park Submerged Vehicles',
      etaMinutes: 12
    },
    {
      id: 'HELO-RESCUE-9',
      callsign: 'Air-Rescue Skycrane Heavy 9',
      type: 'Air-Rescue Extraction Helicopter',
      lat: 39.485,
      lon: -0.360,
      status: 'AIRBORNE',
      personnel: 6,
      fuelPct: 74,
      assignedSector: 'Rooftop Winch Evacuations Alfafar',
      etaMinutes: 6
    },
    {
      id: 'UAV-RECON-3',
      callsign: 'High-Altitude Thermal Drone Recon 3',
      type: 'Autonomous Long-Endurance UAV',
      lat: 39.435,
      lon: -0.395,
      status: 'LOITERING',
      altitudeMeters: 450,
      sensorMode: 'FLIR Thermal LWIR 640x512',
      batteryPct: 88,
      assignedSector: 'Live Thermal Survivor Scour Sector Charlie',
      etaMinutes: 0
    }
  ];

  class RescueDispatchSystem {
    constructor() {
      this.units = JSON.parse(JSON.stringify(DEFAULT_UNITS));
      this.droneCanvas = null;
      this.droneCtx = null;
      this.droneAnimId = null;
      this.droneTelemetry = {
        altitudeM: 450,
        speedKts: 34,
        headingDeg: 128,
        batteryPct: 88,
        gimbalPitchDeg: -45,
        targetLocked: true,
        thermalPalette: 'white-hot'
      };
    }

    getAllUnits() {
      return this.units;
    }

    getUnitById(id) {
      return this.units.find(u => u.id === id);
    }

    dispatchUnit(unitId, targetLat, targetLon, sectorName) {
      const unit = this.getUnitById(unitId);
      if (!unit) return null;

      unit.status = 'DISPATCHED';
      unit.lat = targetLat;
      unit.lon = targetLon;
      unit.assignedSector = sectorName || `Target Coordinates [${targetLat.toFixed(3)}, ${targetLon.toFixed(3)}]`;
      unit.etaMinutes = Math.floor(Math.random() * 15) + 5;

      if (window.soundEngine) {
        window.soundEngine.playRadioStatic();
      }

      if (window.telemetryFeed) {
        window.telemetryFeed.logEvent(
          'DISPATCH_C2',
          `FIRST RESPONDER DISPATCHED: ${unit.callsign} rerouted to ${unit.assignedSector} (ETA ${unit.etaMinutes}m)`,
          'warn'
        );
      }

      return unit;
    }

    /**
     * Initialize Synthetic UAV Drone Video Stream Canvas
     * @param {HTMLCanvasElement} canvas 
     */
    initDroneStream(canvas) {
      if (!canvas) return;
      this.droneCanvas = canvas;
      this.droneCtx = canvas.getContext('2d');
      this.startDroneLoop();
    }

    stopDroneStream() {
      if (this.droneAnimId) {
        cancelAnimationFrame(this.droneAnimId);
        this.droneAnimId = null;
      }
    }

    startDroneLoop() {
      if (!this.droneCanvas || !this.droneCtx) return;
      let frame = 0;

      const render = () => {
        frame++;
        const ctx = this.droneCtx;
        const w = this.droneCanvas.width;
        const h = this.droneCanvas.height;

        // Render synthetic terrain & thermal hotspots
        ctx.fillStyle = '#080c14';
        ctx.fillRect(0, 0, w, h);

        // Draw scanlines & sensor noise
        ctx.strokeStyle = 'rgba(0, 255, 136, 0.05)';
        ctx.lineWidth = 1;
        for (let y = 0; y < h; y += 4) {
          ctx.beginPath();
          ctx.moveTo(0, y);
          ctx.lineTo(w, y);
          ctx.stroke();
        }

        // Draw synthetic landscape features (roads, river, flooded basins)
        ctx.strokeStyle = 'rgba(0, 240, 255, 0.35)';
        ctx.lineWidth = 3;
        ctx.beginPath();
        const roadCurve = Math.sin(frame * 0.01) * 30;
        ctx.moveTo(w * 0.2 + roadCurve, 0);
        ctx.lineTo(w * 0.4 - roadCurve, h);
        ctx.stroke();

        // Draw simulated buildings (rectangles in FLIR view)
        const buildingCount = 8;
        for (let i = 0; i < buildingCount; i++) {
          const bx = (w * 0.3 + i * 45 + Math.sin(frame * 0.01 + i) * 10) % (w * 0.8);
          const by = (h * 0.2 + (i % 3) * 80 + Math.cos(frame * 0.01 + i) * 10) % (h * 0.7);

          ctx.fillStyle = (i === 3 || i === 5) ? 'rgba(255, 100, 50, 0.55)' : 'rgba(30, 45, 70, 0.6)';
          ctx.fillRect(bx, by, 38, 32);
          ctx.strokeStyle = (i === 3 || i === 5) ? '#ff5722' : 'rgba(0, 240, 255, 0.4)';
          ctx.lineWidth = 1;
          ctx.strokeRect(bx, by, 38, 32);

          // Heat signature label
          if (i === 3 || i === 5) {
            ctx.fillStyle = '#ffaa00';
            ctx.font = '9px monospace';
            ctx.fillText('HEAT ANOMALY 37.4°C', bx - 10, by - 5);
          }
        }

        // Draw center crosshair and target tracking box
        const cx = w / 2;
        const cy = h / 2;

        ctx.strokeStyle = '#00ff88';
        ctx.lineWidth = 1.5;

        // Bounding reticle
        const retSize = 40;
        ctx.beginPath();
        ctx.moveTo(cx - retSize, cy - retSize + 10);
        ctx.lineTo(cx - retSize, cy - retSize);
        ctx.lineTo(cx - retSize + 10, cy - retSize);

        ctx.moveTo(cx + retSize - 10, cy - retSize);
        ctx.lineTo(cx + retSize, cy - retSize);
        ctx.lineTo(cx + retSize, cy - retSize + 10);

        ctx.moveTo(cx - retSize, cy + retSize - 10);
        ctx.lineTo(cx - retSize, cy + retSize);
        ctx.lineTo(cx - retSize + 10, cy + retSize);

        ctx.moveTo(cx + retSize - 10, cy + retSize);
        ctx.lineTo(cx + retSize, cy + retSize);
        ctx.lineTo(cx + retSize, cy + retSize - 10);
        ctx.stroke();

        // Crosshairs
        ctx.beginPath();
        ctx.moveTo(cx - 15, cy); ctx.lineTo(cx + 15, cy);
        ctx.moveTo(cx, cy - 15); ctx.lineTo(cx, cy + 15);
        ctx.stroke();

        // Center dot
        ctx.fillStyle = '#00ff88';
        ctx.fillRect(cx - 1.5, cy - 1.5, 3, 3);

        // Compass heading indicator at top
        const headingOffset = (frame * 0.5) % 360;
        ctx.font = '10px monospace';
        ctx.fillStyle = '#00ff88';
        ctx.textAlign = 'center';
        ctx.fillText(`HDG: ${Math.round(headingOffset)}° MAG | PITCH: -45.2° | ROLL: +0.4°`, cx, 24);

        // Pitch ladder
        for (let p = -2; p <= 2; p++) {
          if (p === 0) continue;
          const py = cy + p * 30;
          ctx.beginPath();
          ctx.moveTo(cx - 30, py);
          ctx.lineTo(cx - 10, py);
          ctx.moveTo(cx + 10, py);
          ctx.lineTo(cx + 30, py);
          ctx.stroke();
          ctx.fillText(`${-p * 10}`, cx + 38, py + 3);
        }

        // Loop animation
        this.droneAnimId = requestAnimationFrame(render);
      };

      this.droneAnimId = requestAnimationFrame(render);
    }
  }

  window.rescueDispatch = new RescueDispatchSystem();

})(window);
