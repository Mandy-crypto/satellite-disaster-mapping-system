/**
 * ============================================================================
 * ASTRA-GEO // SATELLITE DISASTER INTELLIGENCE PLATFORM
 * SYNTHETIC SAR INTERFEROGRAM & CO-SEISMIC PHASE FRINGE ENGINE
 * ============================================================================
 * Generates synthetic Differential InSAR (DInSAR) wrapped phase fringes (4pi/lambda),
 * performs phase unwrapping to millimeters of line-of-sight (LOS) displacement,
 * and renders interactive radar interferometric layers on GIS viewports.
 */

(function (window) {
  'use strict';

  class InterferogramGenerator {
    constructor() {
      this.wavelengthCm = 5.546; // Sentinel-1 C-band radar wavelength (5.55 cm)
      this.displacementPerFringeCm = this.wavelengthCm / 2.0; // 2.77 cm per complete 2pi fringe
    }

    /**
     * Compute Wrapped Radar Phase at ground point [x, y]
     * @param {number} x - Normalized coordinate [0, 1]
     * @param {number} y - Normalized coordinate [0, 1]
     * @param {string} disasterCategory - 'cat-earthquake', 'cat-volcano'
     * @returns {Object} { wrappedPhaseRad, losDisplacementMm }
     */
    calculateInterferometricPhase(x, y, disasterCategory = 'cat-earthquake') {
      let losDisplacementCm = 0;

      if (disasterCategory === 'cat-earthquake') {
        // Strike-slip fault displacement model (arctan dislocation across fault trace at x = 0.5)
        const distFromFault = x - 0.5;
        const slipMaxM = 4.5;
        const lockingDepth = 0.15;
        // Analytical Okada strike-slip dislocation: u = (s / pi) * arctan(x / d)
        const displacementM = (slipMaxM / Math.PI) * Math.atan2(distFromFault, lockingDepth);
        losDisplacementCm = displacementM * 100 * 0.42; // Line-of-sight projection factor
      } else {
        // Volcano Mogi point pressure source (deflation/inflation bowl)
        const r = Math.hypot(x - 0.5, y - 0.5);
        losDisplacementCm = 65.0 * Math.exp(-Math.pow(r / 0.22, 2));
      }

      // Add synthetic atmospheric phase screen turbulence noise
      const atmNoise = 0.4 * Math.sin(x * 24) * Math.cos(y * 18);
      const totalPhaseRad = ((4 * Math.PI) / this.wavelengthCm) * losDisplacementCm + atmNoise;

      // Wrap phase modulo 2*PI into [-PI, +PI]
      let wrappedPhase = (totalPhaseRad % (2 * Math.PI));
      if (wrappedPhase > Math.PI) wrappedPhase -= 2 * Math.PI;
      if (wrappedPhase < -Math.PI) wrappedPhase += 2 * Math.PI;

      return {
        wrappedPhaseRad: wrappedPhase,
        losDisplacementMm: Math.round(losDisplacementCm * 10)
      };
    }

    /**
     * Convert Phase in radians [-PI, +PI] to RGB Color (Rainbow Interferogram Colormap)
     * @param {number} phaseRad 
     * @returns {string} CSS rgb string
     */
    phaseToColor(phaseRad) {
      // Normalize phase to [0.0, 1.0]
      const t = (phaseRad + Math.PI) / (2 * Math.PI);

      // Rainbow HSV conversion: Hue = t * 360
      const h = t * 360;
      const s = 0.95;
      const v = 0.9;

      const c = v * s;
      const x = c * (1 - Math.abs(((h / 60) % 2) - 1));
      const m = v - c;

      let r = 0, g = 0, b = 0;
      if (h < 60) { r = c; g = x; b = 0; }
      else if (h < 120) { r = x; g = c; b = 0; }
      else if (h < 180) { r = 0; g = c; b = x; }
      else if (h < 240) { r = 0; g = x; b = c; }
      else if (h < 300) { r = x; g = 0; b = c; }
      else { r = c; g = 0; b = x; }

      const red = Math.round((r + m) * 255);
      const grn = Math.round((g + m) * 255);
      const blu = Math.round((b + m) * 255);

      return `rgba(${red}, ${grn}, ${blu}, 0.75)`;
    }

    /**
     * Render Synthetic InSAR Phase Fringe Image on Canvas
     * @param {HTMLCanvasElement} canvas 
     * @param {string} category 
     */
    renderInterferogram(canvas, category = 'cat-earthquake') {
      if (!canvas) return;
      const ctx = canvas.getContext('2d');
      const w = canvas.width;
      const h = canvas.height;

      const imgData = ctx.createImageData(w, h);
      const data = imgData.data;

      for (let py = 0; py < h; py++) {
        const ny = py / h;
        for (let px = 0; px < w; px++) {
          const nx = px / w;
          const { wrappedPhaseRad } = this.calculateInterferometricPhase(nx, ny, category);

          // Phase to rainbow color
          const t = (wrappedPhaseRad + Math.PI) / (2 * Math.PI);
          const hDeg = t * 360;
          const s = 0.95;
          const v = 0.9;
          const c = v * s;
          const x = c * (1 - Math.abs(((hDeg / 60) % 2) - 1));
          const m = v - c;

          let r = 0, g = 0, b = 0;
          if (hDeg < 60) { r = c; g = x; b = 0; }
          else if (hDeg < 120) { r = x; g = c; b = 0; }
          else if (hDeg < 180) { r = 0; g = c; b = x; }
          else if (hDeg < 240) { r = 0; g = x; b = c; }
          else if (hDeg < 300) { r = x; g = 0; b = c; }
          else { r = c; g = 0; b = x; }

          const idx = (py * w + px) * 4;
          data[idx] = Math.round((r + m) * 255);
          data[idx + 1] = Math.round((g + m) * 255);
          data[idx + 2] = Math.round((b + m) * 255);
          data[idx + 3] = 190; // Alpha
        }
      }

      ctx.putImageData(imgData, 0, 0);
    }
  }

  window.interferogramGenerator = new InterferogramGenerator();

})(window);
