/**
 * ============================================================================
 * ASTRA-GEO // SATELLITE DISASTER INTELLIGENCE PLATFORM
 * REAL-TIME TELEMETRY STREAM & CAP ALERT TICKER
 * ============================================================================
 * Simulates streaming downlink telemetry packets, CCSDS frame sync headers,
 * spacecraft health telemetry, and Common Alerting Protocol (CAP) broadcasts.
 */

(function (window) {
  'use strict';

  class TelemetryFeedManager {
    constructor() {
      this.logContainer = null;
      this.alertBannerText = null;
      this.maxLogEntries = 120;
      this.streamInterval = null;
    }

    init() {
      this.logContainer = document.getElementById('telemetry-log-entries');
      this.alertBannerText = document.getElementById('cap-alert-text');

      this.logEvent('SYSTEM', 'ASTRA-GEO ORBITAL C2 CORE ONLINE // SECURE TELEMETRY LINK ESTABLISHED', 'success');
      this.logEvent('ORBITAL', 'Propagating constellations: Copernicus Sentinel (S1/S2), Landsat-9, WorldView-3, ICEYE-X24', 'info');

      this.startSimulatedDownlinkStream();
    }

    logEvent(source, msg, type = 'info') {
      if (!this.logContainer) {
        this.logContainer = document.getElementById('telemetry-log-entries');
      }
      if (!this.logContainer) return;

      const timeStr = new Date().toISOString().substring(11, 19);
      const row = document.createElement('div');
      row.className = `log-entry ${type}`;
      row.innerHTML = `
        <span class="log-time">[${timeStr}]</span>
        <span class="log-source">&lt;${source}&gt;</span>
        <span class="log-msg">${msg}</span>
      `;

      this.logContainer.prepend(row);

      // Trim old entries
      while (this.logContainer.children.length > this.maxLogEntries) {
        this.logContainer.removeChild(this.logContainer.lastChild);
      }
    }

    triggerCapAlert(alertTitle, severity = 'WARNING') {
      if (this.alertBannerText) {
        this.alertBannerText.textContent = `[${severity}] ${alertTitle}`;
      }

      if (window.soundEngine) {
        window.soundEngine.playEmergencyAlarm();
      }

      this.logEvent('CAP_ALERT', alertTitle, 'alert');
    }

    startSimulatedDownlinkStream() {
      const simulatedTelemetryEvents = [
        { src: 'SKS_GROUND', msg: 'CCSDS Telemetry Frame Sync 0x1ACFFC1D received from Sentinel-2A. 1.2 Gbps lock.', type: 'info' },
        { src: 'WORLDVIEW-3', msg: 'Attitude control reaction wheels nominal at 2,450 RPM. Optical gyro drift < 0.002°/hr.', type: 'info' },
        { src: 'COPERNICUS', msg: 'Sentinel-1A SAR raw interferogram granule downlinked. InSAR coherence generation initiated.', type: 'success' },
        { src: 'USGS_EROS', msg: 'Landsat-9 OLI-2 Band 7 Shortwave Infrared orthorectification completed.', type: 'info' },
        { src: 'NOAA_NHC', msg: 'GOES-16 ABI 1-min mesoscale rapid eye scan refreshed. Central pressure 897 mb.', type: 'warn' },
        { src: 'ICEYE_OPS', msg: 'ICEYE-X24 X-Band radar high-resolution spotlight pass executed over coastal zone.', type: 'success' },
        { src: 'PWR_BUS', msg: 'Battery depth of discharge nominal at 4.2%. Solar array sun-tracking angle 18.4°.', type: 'info' }
      ];

      this.streamInterval = setInterval(() => {
        const randEvent = simulatedTelemetryEvents[Math.floor(Math.random() * simulatedTelemetryEvents.length)];
        this.logEvent(randEvent.src, randEvent.msg, randEvent.type);
      }, 7000);
    }
  }

  window.telemetryFeed = new TelemetryFeedManager();

})(window);
