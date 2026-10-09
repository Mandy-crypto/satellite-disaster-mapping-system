/**
 * ============================================================================
 * ASTRA-GEO // SATELLITE DISASTER INTELLIGENCE PLATFORM
 * 4D TEMPORAL TIMELINE SCRUBBER & HISTORICAL PLAYBACK ENGINE
 * ============================================================================
 * Manages 4D disaster temporal state, keyframe navigation (T-72h to T+120h),
 * orbital imagery pass markers, playback rate acceleration, and viewport synchronization.
 */

(function (window) {
  'use strict';

  class TimelineScrubber {
    constructor() {
      this.isPlaying = false;
      this.playbackSpeed = 1; // 1x, 5x, 20x, 60x
      this.currentTimeOffsetHours = 0; // Relative to disaster T0 (-72 to +120)
      this.minOffsetHours = -72;
      this.maxOffsetHours = 120;
      this.playbackInterval = null;
      this.keyframeMarkers = [];
      this.timeDisplayElem = null;
      this.sliderElem = null;
    }

    init() {
      this.timeDisplayElem = document.getElementById('timeline-time-val');
      this.sliderElem = document.getElementById('timeline-scrubber-slider');

      if (this.sliderElem) {
        this.sliderElem.min = this.minOffsetHours;
        this.sliderElem.max = this.maxOffsetHours;
        this.sliderElem.value = this.currentTimeOffsetHours;

        this.sliderElem.addEventListener('input', (e) => {
          this.setTimeOffset(parseFloat(e.target.value), false);
        });
      }

      this.updateDisplay();
      this.renderKeyframePins();
    }

    setTimeOffset(hours, updateSlider = true) {
      this.currentTimeOffsetHours = Math.max(this.minOffsetHours, Math.min(this.maxOffsetHours, hours));
      if (updateSlider && this.sliderElem) {
        this.sliderElem.value = this.currentTimeOffsetHours;
      }
      this.updateDisplay();
    }

    updateDisplay() {
      if (!this.timeDisplayElem) return;
      const sign = this.currentTimeOffsetHours >= 0 ? '+' : '';
      const formatted = `T ${sign}${this.currentTimeOffsetHours.toFixed(1)} hrs`;
      this.timeDisplayElem.textContent = formatted;

      // Update active satellite positions
      if (window.globeEngine) {
        // Globe will automatically render satellites at propagated time
      }
    }

    play() {
      if (this.isPlaying) return;
      this.isPlaying = true;

      const playBtn = document.getElementById('btn-timeline-play');
      if (playBtn) playBtn.innerHTML = '⏸️ PAUSE';

      if (window.soundEngine) window.soundEngine.playToggle();

      const stepMs = 100;
      this.playbackInterval = setInterval(() => {
        // Increment time based on speed
        const deltaHours = (0.05 * this.playbackSpeed);
        let next = this.currentTimeOffsetHours + deltaHours;
        if (next > this.maxOffsetHours) {
          next = this.minOffsetHours; // Loop
        }
        this.setTimeOffset(next, true);
      }, stepMs);
    }

    pause() {
      if (!this.isPlaying) return;
      this.isPlaying = false;

      const playBtn = document.getElementById('btn-timeline-play');
      if (playBtn) playBtn.innerHTML = '▶ PLAY';

      if (this.playbackInterval) {
        clearInterval(this.playbackInterval);
        this.playbackInterval = null;
      }

      if (window.soundEngine) window.soundEngine.playClick();
    }

    togglePlayPause() {
      if (this.isPlaying) this.pause();
      else this.play();
    }

    setSpeed(speedMultiplier) {
      this.playbackSpeed = speedMultiplier;
      if (window.soundEngine) window.soundEngine.playClick();
    }

    stepBackward() {
      this.pause();
      this.setTimeOffset(this.currentTimeOffsetHours - 6, true);
    }

    stepForward() {
      this.pause();
      this.setTimeOffset(this.currentTimeOffsetHours + 6, true);
    }

    resetToT0() {
      this.pause();
      this.setTimeOffset(0, true);
    }

    renderKeyframePins() {
      const container = document.getElementById('timeline-keyframe-markers');
      if (!container) return;

      container.innerHTML = '';
      const range = this.maxOffsetHours - this.minOffsetHours;

      // Representative satellite acquisition passes
      const keyframes = [
        { hour: -48, label: 'Sentinel-2 Pre-Disaster Baseline', color: '#10b981' },
        { hour: 0, label: 'T0: Incident Emergence', color: '#ff3366' },
        { hour: 12, label: 'Sentinel-1A SAR Emergency Flood Pass', color: '#00f0ff' },
        { hour: 36, label: 'WorldView-3 High-Res Damage Pass', color: '#facc15' },
        { hour: 72, label: 'Landsat-9 Post-Event Recovery Pass', color: '#a855f7' }
      ];

      keyframes.forEach(kf => {
        const pct = ((kf.hour - this.minOffsetHours) / range) * 100;
        const pin = document.createElement('div');
        pin.className = 'timeline-keyframe-pin';
        pin.style.left = `${pct}%`;
        pin.style.backgroundColor = kf.color;
        pin.title = `${kf.label} (T${kf.hour >= 0 ? '+' : ''}${kf.hour}h)`;
        pin.addEventListener('click', () => {
          this.pause();
          this.setTimeOffset(kf.hour, true);
          if (window.soundEngine) window.soundEngine.playTargetLock();
        });
        container.appendChild(pin);
      });
    }
  }

  window.timelineScrubber = new TimelineScrubber();

})(window);
