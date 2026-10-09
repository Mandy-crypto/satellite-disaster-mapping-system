/**
 * ============================================================================
 * ASTRA-GEO // SATELLITE DISASTER INTELLIGENCE PLATFORM
 * DOPPLER WEATHER RADAR & PRECIPITATION REFLECTIVITY ENGINE
 * ============================================================================
 * Renders real-time simulated Doppler radar base reflectivity echoes (dBZ),
 * NWS 16-color radar palette sweeps, and convective precipitation advection.
 */

(function (window) {
  'use strict';

  // National Weather Service (NWS) 16-Color Doppler Reflectivity Palette (dBZ)
  const NWS_RADAR_PALETTE = [
    { dbz: 5, color: [4, 233, 231, 140] },    // Light cyan
    { dbz: 10, color: [1, 159, 244, 160] },   // Cyan-blue
    { dbz: 15, color: [3, 0, 244, 180] },     // Blue
    { dbz: 20, color: [2, 253, 2, 190] },     // Light green
    { dbz: 25, color: [1, 197, 1, 200] },     // Green
    { dbz: 30, color: [0, 142, 0, 210] },     // Dark green
    { dbz: 35, color: [253, 248, 2, 220] },   // Yellow
    { dbz: 40, color: [229, 188, 0, 220] },   // Dark yellow
    { dbz: 45, color: [253, 149, 0, 230] },   // Orange
    { dbz: 50, color: [253, 0, 0, 240] },     // Red
    { dbz: 55, color: [212, 0, 0, 240] },     // Dark red
    { dbz: 60, color: [188, 0, 0, 250] },     // Crimson
    { dbz: 65, color: [248, 0, 253, 250] },   // Magenta (Hail core)
    { dbz: 70, color: [153, 85, 201, 255] }   // Purple (Severe hail / tornado)
  ];

  class WeatherRadarEngine {
    constructor() {
      this.enabled = true;
      this.radarCanvas = null;
      this.radarCtx = null;
      this.sweepAngleRad = 0;
      this.animId = null;
      this.frame = 0;
    }

    init() {
      // Create dedicated weather radar overlay canvas above Leaflet
      const mapContainer = document.getElementById('leaflet-map-container');
      if (!mapContainer) return;

      this.radarCanvas = document.createElement('canvas');
      this.radarCanvas.id = 'weather-radar-canvas';
      this.radarCanvas.style.cssText = `
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
        z-index: 15;
      `;
      mapContainer.appendChild(this.radarCanvas);
      this.radarCtx = this.radarCanvas.getContext('2d');

      this.handleResize();
      window.addEventListener('resize', () => this.handleResize());

      this.startSweepAnimation();
    }

    handleResize() {
      if (!this.radarCanvas) return;
      const rect = this.radarCanvas.parentElement.getBoundingClientRect();
      this.radarCanvas.width = rect.width;
      this.radarCanvas.height = rect.height;
    }

    toggleRadar(enable) {
      this.enabled = enable !== undefined ? enable : !this.enabled;
      if (this.radarCanvas) {
        this.radarCanvas.style.display = this.enabled ? 'block' : 'none';
      }
      return this.enabled;
    }

    startSweepAnimation() {
      const render = () => {
        this.frame++;
        this.sweepAngleRad = (this.frame * 0.025) % (Math.PI * 2);

        if (this.enabled) {
          this.drawRadarEchoes();
        }

        this.animId = requestAnimationFrame(render);
      };

      this.animId = requestAnimationFrame(render);
    }

    drawRadarEchoes() {
      if (!this.radarCtx || !this.radarCanvas) return;
      const ctx = this.radarCtx;
      const w = this.radarCanvas.width;
      const h = this.radarCanvas.height;
      const cx = w / 2;
      const cy = h / 2;

      ctx.clearRect(0, 0, w, h);

      // Draw Rotating Antenna Sweep Beam
      const sweepRadius = Math.min(w, h) * 0.45;
      const sweepGradient = ctx.createRadialGradient(cx, cy, 10, cx, cy, sweepRadius);
      sweepGradient.addColorStop(0, 'rgba(0, 255, 136, 0.25)');
      sweepGradient.addColorStop(1, 'transparent');

      ctx.save();
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.arc(cx, cy, sweepRadius, this.sweepAngleRad - 0.4, this.sweepAngleRad);
      ctx.closePath();
      ctx.fillStyle = sweepGradient;
      ctx.fill();
      ctx.restore();

      // Render Organic Convective Precipitation Echo Cells (dBZ)
      const cellCount = 5;
      for (let i = 0; i < cellCount; i++) {
        const angle = i * 1.35 + this.frame * 0.003;
        const dist = 60 + i * 40 + Math.sin(this.frame * 0.02 + i) * 15;
        const cellX = cx + Math.cos(angle) * dist;
        const cellY = cy + Math.sin(angle) * dist;

        // Multi-tier reflectivity concentric rings (dBZ)
        const maxDbzTier = (i % 2 === 0) ? 10 : 7; // Severe storms reach purple/red
        for (let t = 0; t <= maxDbzTier; t++) {
          const tier = NWS_RADAR_PALETTE[t];
          const radius = Math.max(4, (maxDbzTier - t) * 6 + Math.sin(this.frame * 0.05 + t) * 3);

          ctx.fillStyle = `rgba(${tier.color[0]}, ${tier.color[1]}, ${tier.color[2]}, 0.45)`;
          ctx.beginPath();
          ctx.arc(cellX, cellY, radius, 0, Math.PI * 2);
          ctx.fill();
        }
      }
    }
  }

  window.weatherRadar = new WeatherRadarEngine();
  window.addEventListener('DOMContentLoaded', () => {
    if (window.weatherRadar) window.weatherRadar.init();
  });

})(window);
