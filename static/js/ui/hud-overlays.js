/**
 * ============================================================================
 * ASTRA-GEO // SATELLITE DISASTER INTELLIGENCE PLATFORM
 * MILITARY HUD OVERLAYS & COCKPIT THEME MANAGER
 * ============================================================================
 * Coordinates reticle crosshairs, Military Grid Reference System (MGRS),
 * CRT scanline toggles, visual audio indicators, and theme switches.
 */

(function (window) {
  'use strict';

  class HudOverlayManager {
    constructor() {
      this.currentTheme = 'dark-orbital';
      this.scanlinesEnabled = false;
      this.audioVisualizerInterval = null;
    }

    init() {
      this.setupThemeToggle();
      this.setupHudReticle();
      this.startAudioVisualizer();
    }

    setTheme(themeName) {
      this.currentTheme = themeName;
      document.body.setAttribute('data-theme', themeName);

      if (window.soundEngine) {
        window.soundEngine.playToggle();
      }

      if (window.telemetryFeed) {
        window.telemetryFeed.logEvent('SYSTEM', `UI Tactical Theme switched to [${themeName.toUpperCase()}]`, 'info');
      }
    }

    toggleScanlines() {
      this.scanlinesEnabled = !this.scanlinesEnabled;
      const root = document.getElementById('app-root');
      if (root) {
        if (this.scanlinesEnabled) {
          root.style.backgroundImage = 'var(--hud-scanlines)';
        } else {
          root.style.backgroundImage = 'none';
        }
      }
      return this.scanlinesEnabled;
    }

    setupHudReticle() {
      const stage = document.querySelector('.viewport-stage');
      if (!stage) return;

      stage.addEventListener('mousemove', (e) => {
        const rect = stage.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        const crosshair = document.querySelector('.hud-center-crosshair');
        if (crosshair) {
          crosshair.style.left = `${x}px`;
          crosshair.style.top = `${y}px`;
        }
      });
    }

    setupThemeToggle() {
      const themeSelect = document.getElementById('select-hud-theme');
      if (themeSelect) {
        themeSelect.addEventListener('change', (e) => {
          this.setTheme(e.target.value);
        });
      }
    }

    startAudioVisualizer() {
      const canvas = document.getElementById('footer-audio-visualizer');
      if (!canvas) return;
      const ctx = canvas.getContext('2d');
      const w = canvas.width = 60;
      const h = canvas.height = 14;

      const bars = 7;
      const render = () => {
        ctx.clearRect(0, 0, w, h);
        for (let i = 0; i < bars; i++) {
          const barH = Math.random() * (h - 2) + 2;
          ctx.fillStyle = '#00ff88';
          ctx.fillRect(i * 8 + 2, h - barH, 5, barH);
        }
      };

      this.audioVisualizerInterval = setInterval(render, 120);
    }
  }

  window.hudOverlayManager = new HudOverlayManager();

})(window);
