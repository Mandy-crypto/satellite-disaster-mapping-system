/**
 * ============================================================================
 * ASTRA-GEO // SATELLITE DISASTER INTELLIGENCE PLATFORM
 * MULTISPECTRAL & RADAR REMOTE SENSING ANALYSIS WORKBENCH
 * ============================================================================
 * Implements satellite band combinations (True Color, False Color NIR, SWIR,
 * NDVI, NDWI, NBR, SAR Coherence), radiometric histograms, pixel inspection,
 * and the interactive swipe curtain before/after comparison lens.
 */

(function (window) {
  'use strict';

  class SpectralAnalysisEngine {
    constructor() {
      this.currentMode = 'TRUE_COLOR';
      this.histogramCanvas = null;
      this.histogramCtx = null;
      this.swipeActive = false;
      this.swipeSplitPct = 50;
      this.selectedPixelData = null;
    }

    init() {
      this.histogramCanvas = document.getElementById('spectral-histogram-canvas');
      if (this.histogramCanvas) {
        this.histogramCtx = this.histogramCanvas.getContext('2d');
        this.drawHistogram();
      }

      this.setupSwipeCurtain();
    }

    /**
     * Switch Active Spectral Band Preset
     * @param {string} modeKey - 'TRUE_COLOR', 'FALSE_COLOR_NIR', 'SWIR', 'NDVI', 'NDWI', 'NBR', 'SAR_COHERENCE'
     */
    setBandMode(modeKey) {
      this.currentMode = modeKey;

      if (window.soundEngine) {
        window.soundEngine.playToggle();
      }

      if (window.telemetryFeed) {
        window.telemetryFeed.logEvent('SPECTRAL', `Band Preset Changed: ${modeKey}`, 'info');
      }

      this.drawHistogram();
    }

    /**
     * Setup Swipe Comparison Slider Handle
     */
    setupSwipeCurtain() {
      const container = document.getElementById('swipe-curtain-container');
      const handle = document.getElementById('swipe-curtain-handle');
      const curtain = document.getElementById('swipe-curtain-layer');
      if (!container || !handle || !curtain) return;

      let isDragging = false;

      const updatePos = (clientX) => {
        const rect = container.getBoundingClientRect();
        const offsetX = Math.max(0, Math.min(rect.width, clientX - rect.left));
        this.swipeSplitPct = (offsetX / rect.width) * 100;
        curtain.style.width = `${this.swipeSplitPct}%`;
      };

      handle.addEventListener('mousedown', (e) => {
        isDragging = true;
        e.stopPropagation();
      });

      window.addEventListener('mouseup', () => {
        isDragging = false;
      });

      window.addEventListener('mousemove', (e) => {
        if (isDragging) {
          updatePos(e.clientX);
        }
      });
    }

    toggleSwipeLens(enable) {
      this.swipeActive = enable !== undefined ? enable : !this.swipeActive;
      const container = document.getElementById('swipe-curtain-container');
      if (container) {
        if (this.swipeActive) container.classList.add('active');
        else container.classList.remove('active');
      }
      return this.swipeActive;
    }

    /**
     * Draw Radiometric Pixel Intensity Histogram Curves
     */
    drawHistogram() {
      if (!this.histogramCanvas || !this.histogramCtx) return;
      const ctx = this.histogramCtx;
      const w = this.histogramCanvas.width = this.histogramCanvas.parentElement.clientWidth || 360;
      const h = this.histogramCanvas.height = 70;

      ctx.clearRect(0, 0, w, h);

      // Draw background grid lines
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
      ctx.lineWidth = 1;
      for (let x = 0; x < w; x += 40) {
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();
      }

      // Draw Gaussian Curves for Spectral Channels (Red, Green, Blue, NIR, SWIR)
      const bands = [
        { color: 'rgba(255, 51, 102, 0.7)', mean: w * 0.42, std: 32 }, // Red
        { color: 'rgba(0, 255, 136, 0.7)', mean: w * 0.52, std: 28 },  // Green
        { color: 'rgba(0, 240, 255, 0.7)', mean: w * 0.35, std: 36 },  // Blue
        { color: 'rgba(168, 85, 247, 0.8)', mean: w * 0.68, std: 38 }  // NIR
      ];

      bands.forEach(b => {
        ctx.strokeStyle = b.color;
        ctx.lineWidth = 1.5;
        ctx.beginPath();

        for (let x = 0; x < w; x += 3) {
          const norm = (x - b.mean) / b.std;
          const yVal = Math.exp(-0.5 * norm * norm);
          const y = h - (yVal * (h * 0.85)) - 4;
          if (x === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.stroke();
      });

      // Axis legend labels
      ctx.font = '8px monospace';
      ctx.fillStyle = '#64748b';
      ctx.fillText('DN 0 (DARK)', 4, h - 3);
      ctx.fillText('DN 10000 (BRIGHT)', w - 85, h - 3);
    }

    /**
     * Inspect Pixel Spectral Signature
     * @param {number} x 
     * @param {number} y 
     */
    inspectPixel(x, y) {
      // Simulate reflectance profile across 8 spectral bands
      const profile = [
        { band: 'B02 Blue', val: 0.082 },
        { band: 'B03 Green', val: 0.114 },
        { band: 'B04 Red', val: 0.095 },
        { band: 'B05 RE1', val: 0.185 },
        { band: 'B08 NIR', val: 0.442 },
        { band: 'B11 SWIR1', val: 0.215 },
        { band: 'B12 SWIR2', val: 0.118 }
      ];

      const ndvi = (0.442 - 0.095) / (0.442 + 0.095);
      const ndwi = (0.114 - 0.442) / (0.114 + 0.442);
      const nbr = (0.442 - 0.215) / (0.442 + 0.215);

      this.selectedPixelData = {
        pixelX: x,
        pixelY: y,
        profile,
        indices: {
          ndvi: parseFloat(ndvi.toFixed(3)),
          ndwi: parseFloat(ndwi.toFixed(3)),
          nbr: parseFloat(nbr.toFixed(3))
        }
      };

      return this.selectedPixelData;
    }
  }

  window.spectralAnalysis = new SpectralAnalysisEngine();

})(window);
