/**
 * ============================================================================
 * ASTRA-GEO // SATELLITE DISASTER INTELLIGENCE PLATFORM
 * HYDROLOGICAL RUNOFF DISCHARGE & DAM BREACH HYDRODYNAMICS ENGINE
 * ============================================================================
 * Implements Froehlich (1995) dam breach peak discharge equations, SCS dimensionless
 * unit hydrographs, Manning's open-channel hydraulics, and flood hydrograph charting.
 */

(function (window) {
  'use strict';

  class HydrologicalDischargeEngine {
    constructor() {
      this.gravity = 9.80665; // m/s^2
    }

    /**
     * Froehlich (1995) Empirical Dam Breach Peak Discharge
     * Q_p = 0.607 * V_w^0.295 * h_w^1.24
     * @param {number} reservoirVolumeM3 - Total stored reservoir volume in m^3
     * @param {number} breachWaterDepthM - Depth of water above breach invert in meters
     * @returns {Object} { peakDischargeM3S, breachTimeHours, downstreamSurgeKmh }
     */
    calculateDamBreachPeak(reservoirVolumeM3 = 30000000, breachWaterDepthM = 28.0) {
      // Q_p in m3/s
      const qp = 0.607 * Math.pow(reservoirVolumeM3, 0.295) * Math.pow(breachWaterDepthM, 1.24);

      // Average breach formation time (Froehlich 2008): t_f = 0.0179 * V_w^0.364 * h_w^-0.564 (hours)
      const breachFormationHours = 0.0179 * Math.pow(reservoirVolumeM3, 0.364) * Math.pow(breachWaterDepthM, -0.564);

      // Dam breach wave front celerity: c = sqrt(g * h)
      const waveVelocityMs = Math.sqrt(this.gravity * breachWaterDepthM);
      const waveSpeedKmh = waveVelocityMs * 3.6;

      return {
        peakDischargeM3S: Math.round(qp),
        breachFormationHours: parseFloat(breachFormationHours.toFixed(2)),
        breachFormationMinutes: Math.round(breachFormationHours * 60),
        waveSpeedKmh: Math.round(waveSpeedKmh),
        totalWaterVolumeReleasedM3: reservoirVolumeM3
      };
    }

    /**
     * Generate SCS Dimensionless Unit Hydrograph Curve (Discharge Q(t) vs. Time)
     * Q / Q_p = (t / T_p) * exp(1 - t / T_p)^m
     * @param {number} peakDischargeM3S 
     * @param {number} timeToPeakHours 
     * @param {number} totalDurationHours 
     * @returns {Array<Object>} [{ hour, dischargeM3S }]
     */
    generateHydrographSeries(peakDischargeM3S = 2280, timeToPeakHours = 4.0, totalDurationHours = 24.0) {
      const series = [];
      const steps = 48;
      const stepSize = totalDurationHours / steps;

      for (let i = 0; i <= steps; i++) {
        const t = i * stepSize;
        if (t === 0) {
          series.push({ hour: 0, dischargeM3S: 45 }); // Baseflow
          continue;
        }

        const tRatio = t / timeToPeakHours;
        // Gamma distribution hydrograph shape
        const qRatio = Math.pow(tRatio, 2.5) * Math.exp(2.5 * (1 - tRatio));
        const q = Math.max(45, Math.round(peakDischargeM3S * qRatio));

        series.push({
          hour: parseFloat(t.toFixed(1)),
          dischargeM3S: q
        });
      }

      return series;
    }

    /**
     * Render Hydrograph Discharge Curve onto Canvas
     * @param {HTMLCanvasElement} canvas 
     * @param {Array<Object>} hydrographData 
     */
    renderHydrographChart(canvas, hydrographData) {
      if (!canvas || !hydrographData || hydrographData.length === 0) return;
      const ctx = canvas.getContext('2d');
      const w = canvas.width = canvas.parentElement.clientWidth || 360;
      const h = canvas.height = 100;

      const maxQ = Math.max(...hydrographData.map(d => d.dischargeM3S)) * 1.15;

      ctx.clearRect(0, 0, w, h);

      // Gradient area fill
      const grad = ctx.createLinearGradient(0, 0, 0, h);
      grad.addColorStop(0, 'rgba(0, 240, 255, 0.45)');
      grad.addColorStop(1, 'transparent');

      ctx.beginPath();
      const stepX = w / (hydrographData.length - 1);
      ctx.moveTo(0, h);

      hydrographData.forEach((pt, i) => {
        const x = i * stepX;
        const y = h - (pt.dischargeM3S / maxQ) * (h * 0.85);
        ctx.lineTo(x, y);
      });

      ctx.lineTo(w, h);
      ctx.closePath();
      ctx.fillStyle = grad;
      ctx.fill();

      // Line outline
      ctx.strokeStyle = '#00f0ff';
      ctx.lineWidth = 2;
      ctx.beginPath();
      hydrographData.forEach((pt, i) => {
        const x = i * stepX;
        const y = h - (pt.dischargeM3S / maxQ) * (h * 0.85);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.stroke();

      // Peak discharge marker
      const peakPt = hydrographData.reduce((prev, curr) => curr.dischargeM3S > prev.dischargeM3S ? curr : prev);
      const peakIdx = hydrographData.indexOf(peakPt);
      const peakX = peakIdx * stepX;
      const peakY = h - (peakPt.dischargeM3S / maxQ) * (h * 0.85);

      ctx.fillStyle = '#ff3366';
      ctx.beginPath();
      ctx.arc(peakX, peakY, 4, 0, Math.PI * 2);
      ctx.fill();

      ctx.font = 'bold 9px monospace';
      ctx.fillStyle = '#fff';
      ctx.fillText(`PEAK: ${peakPt.dischargeM3S.toLocaleString()} m³/s (T+${peakPt.hour}h)`, Math.max(10, peakX - 60), Math.max(14, peakY - 8));
    }
  }

  window.hydrologicalEngine = new HydrologicalDischargeEngine();

})(window);
