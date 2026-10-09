/**
 * ============================================================================
 * ASTRA-GEO // SATELLITE DISASTER INTELLIGENCE PLATFORM
 * HIGH-PERFORMANCE TACTICAL CANVAS & SVG CHARTING SUITE
 * ============================================================================
 * Lightweight, zero-dependency tactical charts for spectral reflectance curves,
 * seismograms, fire radiative power trends, and structural damage breakdowns.
 */

(function (window) {
  'use strict';

  class TacticalChartEngine {
    constructor() {}

    /**
     * Render Building Damage Breakdown Bar Chart in a target container
     * @param {HTMLElement} container 
     * @param {Object} damageData 
     */
    renderDamageBarChart(container, damageData) {
      if (!container || !damageData) return;

      const grades = [
        { label: 'G5: Collapsed', pct: damageData.percentages.grade5, color: '#7f1d1d' },
        { label: 'G4: Severe', pct: damageData.percentages.grade4, color: '#dc2626' },
        { label: 'G3: Heavy', pct: damageData.percentages.grade3, color: '#ea580c' },
        { label: 'G2: Moderate', pct: damageData.percentages.grade2, color: '#f59e0b' },
        { label: 'G1: Minor', pct: damageData.percentages.grade1, color: '#10b981' }
      ];

      let html = '<div style="display:flex; flex-direction:column; gap:6px; font-family:monospace; font-size:11px;">';
      grades.forEach(g => {
        html += `
          <div>
            <div style="display:flex; justify-content:space-between; margin-bottom:2px;">
              <span>${g.label}</span>
              <span style="font-weight:700; color:${g.color};">${g.pct}%</span>
            </div>
            <div style="width:100%; height:6px; background:rgba(255,255,255,0.06); border-radius:3px; overflow:hidden;">
              <div style="width:${g.pct}%; height:100%; background:${g.color}; border-radius:3px; transition:width 0.4s;"></div>
            </div>
          </div>
        `;
      });
      html += '</div>';

      container.innerHTML = html;
    }

    /**
     * Draw Real-time Seismogram Waveform on Canvas
     * @param {HTMLCanvasElement} canvas 
     */
    drawSeismogram(canvas) {
      if (!canvas || !window.seismicModel) return;
      const ctx = canvas.getContext('2d');
      const w = canvas.width = canvas.parentElement.clientWidth || 320;
      const h = canvas.height = 80;

      const trace = window.seismicModel.generateSyntheticSeismogram(w);

      ctx.clearRect(0, 0, w, h);
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.08)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(0, h / 2);
      ctx.lineTo(w, h / 2);
      ctx.stroke();

      // Waveform line
      ctx.strokeStyle = '#ffaa00';
      ctx.lineWidth = 1.2;
      ctx.beginPath();

      for (let x = 0; x < w; x++) {
        const val = trace[x];
        const y = h / 2 + val * (h * 0.42);
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();

      // P-Wave / S-Wave Markers
      ctx.font = '9px monospace';
      ctx.fillStyle = '#00f0ff';
      ctx.fillText('P-ARRIVAL', 60, 14);
      ctx.strokeStyle = '#00f0ff';
      ctx.setLineDash([2, 2]);
      ctx.beginPath(); ctx.moveTo(60, 16); ctx.lineTo(60, h); ctx.stroke();

      ctx.fillStyle = '#ff3366';
      ctx.fillText('S-ARRIVAL', 160, 14);
      ctx.strokeStyle = '#ff3366';
      ctx.beginPath(); ctx.moveTo(160, 16); ctx.lineTo(160, h); ctx.stroke();
      ctx.setLineDash([]);
    }

    /**
     * Draw Fire Radiative Power (MW) Temporal Trend Sparkline
     * @param {HTMLCanvasElement} canvas 
     */
    drawFRPTrend(canvas) {
      if (!canvas) return;
      const ctx = canvas.getContext('2d');
      const w = canvas.width = canvas.parentElement.clientWidth || 320;
      const h = canvas.height = 70;

      const dataPoints = [420, 680, 1250, 2400, 3850, 4850, 4100, 3200, 2600, 2100];
      const maxVal = 5000;

      ctx.clearRect(0, 0, w, h);

      // Area fill gradient
      const grad = ctx.createLinearGradient(0, 0, 0, h);
      grad.addColorStop(0, 'rgba(255, 87, 34, 0.4)');
      grad.addColorStop(1, 'transparent');

      ctx.beginPath();
      const stepX = w / (dataPoints.length - 1);
      ctx.moveTo(0, h);

      dataPoints.forEach((val, i) => {
        const x = i * stepX;
        const y = h - (val / maxVal) * (h * 0.85);
        ctx.lineTo(x, y);
      });

      ctx.lineTo(w, h);
      ctx.closePath();
      ctx.fillStyle = grad;
      ctx.fill();

      // Line
      ctx.strokeStyle = '#ff5722';
      ctx.lineWidth = 2;
      ctx.beginPath();
      dataPoints.forEach((val, i) => {
        const x = i * stepX;
        const y = h - (val / maxVal) * (h * 0.85);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.stroke();

      // Peak label
      ctx.fillStyle = '#ffaa00';
      ctx.font = 'bold 9px monospace';
      ctx.fillText('PEAK FRP: 4,850 MW', w * 0.4, 14);
    }
  }

  window.chartEngine = new TacticalChartEngine();

})(window);
