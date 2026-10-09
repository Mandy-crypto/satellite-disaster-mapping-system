/**
 * ============================================================================
 * ASTRA-GEO // SATELLITE DISASTER INTELLIGENCE PLATFORM
 * SEISMIC RUPTURE & TSUNAMI PROPAGATION MECHANICS MODEL
 * ============================================================================
 * Implements Ground Motion Prediction Equations (GMPE) for Peak Ground
 * Acceleration (PGA), synthetic P/S-wave seismograms, shallow-water tsunami
 * wave speed (v = sqrt(g*d)), travel-time isochrones, and Omori aftershock decay.
 */

(function (window) {
  'use strict';

  class SeismicModel {
    constructor() {
      this.gravity = 9.80665; // m/s^2
      this.earthRadiusKm = 6371.0;
    }

    /**
     * Compute Peak Ground Acceleration (PGA in %g) using Boore-Atkinson GMPE approximation
     * ln(PGA) = c1 + c2*(M - 6) + c3*(M - 6)^2 - c4*ln(R_rup)
     * @param {number} magnitudeMw - Moment magnitude
     * @param {number} depthKm - Hypocenter depth
     * @param {number} distanceKm - Epicentral distance
     * @returns {Object} { pgaPercentG, mmiIntensity, damageExpectation }
     */
    calculatePGA(magnitudeMw = 7.8, depthKm = 15.0, distanceKm = 25.0) {
      const rRup = Math.sqrt(distanceKm * distanceKm + depthKm * depthKm);
      const mDelta = magnitudeMw - 6.0;

      // GMPE coefficients
      const lnPGA = 0.85 + 0.95 * mDelta - 0.12 * mDelta * mDelta - 1.25 * Math.log(Math.max(1, rRup));
      const pgaG = Math.exp(lnPGA);
      const pgaPercentG = Math.min(220, Math.max(1, pgaG * 100));

      // Compute Modified Mercalli Intensity (MMI) from Worden et al.
      let mmi = 1;
      if (pgaPercentG < 0.17) mmi = 1;
      else if (pgaPercentG < 1.4) mmi = 2 + (pgaPercentG / 1.4);
      else if (pgaPercentG < 3.9) mmi = 3 + ((pgaPercentG - 1.4) / 2.5);
      else if (pgaPercentG < 9.2) mmi = 4 + ((pgaPercentG - 3.9) / 5.3);
      else if (pgaPercentG < 18) mmi = 5 + ((pgaPercentG - 9.2) / 8.8);
      else if (pgaPercentG < 34) mmi = 6 + ((pgaPercentG - 18) / 16);
      else if (pgaPercentG < 65) mmi = 7 + ((pgaPercentG - 34) / 31);
      else if (pgaPercentG < 124) mmi = 8 + ((pgaPercentG - 65) / 59);
      else mmi = Math.min(10, 9 + ((pgaPercentG - 124) / 60));

      let romanMmi = 'I';
      const mmiInt = Math.round(mmi);
      const romans = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII'];
      romanMmi = romans[Math.max(0, Math.min(11, mmiInt - 1))];

      let damage = 'None';
      if (mmiInt >= 9) damage = 'Devastating Structural Collapse / Ground Rupture';
      else if (mmiInt >= 8) damage = 'Severe Damage in Ordinary Buildings / Partial Collapse';
      else if (mmiInt >= 7) damage = 'Moderate to Heavy Damage in Weak Structures';
      else if (mmiInt >= 6) damage = 'Felt by All, Slight Plaster Damage';
      else damage = 'Felt Mildly Indoors';

      return {
        pgaPercentG: parseFloat(pgaPercentG.toFixed(1)),
        mmiNumeric: parseFloat(mmi.toFixed(1)),
        mmiRoman: romanMmi,
        ruptureDistanceKm: parseFloat(rRup.toFixed(1)),
        damageExpectation: damage
      };
    }

    /**
     * Generate synthetic seismogram trace (P-wave, S-wave, surface wave coda)
     * @param {number} sampleCount 
     * @param {number} pWaveSampleIndex 
     * @param {number} sWaveSampleIndex 
     * @returns {Array<number>} Amplitude array [-1.0, 1.0]
     */
    generateSyntheticSeismogram(sampleCount = 600, pWaveSampleIndex = 80, sWaveSampleIndex = 180) {
      const trace = new Float32Array(sampleCount);

      for (let i = 0; i < sampleCount; i++) {
        // Pre-arrival background seismic noise
        let val = (Math.random() * 2 - 1) * 0.04;

        // P-wave arrival (high frequency, moderate amplitude)
        if (i >= pWaveSampleIndex) {
          const tP = i - pWaveSampleIndex;
          const pEnvelope = Math.exp(-tP / 45);
          const pOsc = Math.sin(tP * 0.42) + 0.5 * Math.sin(tP * 0.78);
          val += pOsc * pEnvelope * 0.35;
        }

        // S-wave & surface waves arrival (lower frequency, large amplitude)
        if (i >= sWaveSampleIndex) {
          const tS = i - sWaveSampleIndex;
          const sEnvelope = Math.exp(-tS / 95);
          const sOsc = Math.sin(tS * 0.18) + 0.8 * Math.sin(tS * 0.32) + 0.4 * Math.sin(tS * 0.08);
          val += sOsc * sEnvelope * 0.88;
        }

        trace[i] = Math.max(-1.0, Math.min(1.0, val));
      }

      return Array.from(trace);
    }

    /**
     * Compute Shallow-Water Tsunami Wave Velocity: v = sqrt(g * depth)
     * @param {number} oceanDepthMeters - Typical abyssal depth 4000m
     * @returns {Object} { velocityMS, velocityKmh }
     */
    calculateTsunamiSpeed(oceanDepthMeters = 4000) {
      const vMS = Math.sqrt(this.gravity * oceanDepthMeters);
      const vKmh = vMS * 3.6;
      return {
        velocityMS: parseFloat(vMS.toFixed(1)),
        velocityKmh: Math.round(vKmh)
      };
    }

    /**
     * Generate Tsunami Travel-Time Isochrone Rings (1-hr, 2-hr, 3-hr, 4-hr)
     * @param {number} epicenterLat 
     * @param {number} epicenterLon 
     * @param {number} maxHours 
     * @returns {Array<Object>} Isochrone contours with estimated arrival times
     */
    generateTsunamiIsochrones(epicenterLat, epicenterLon, maxHours = 5) {
      const { velocityKmh } = this.calculateTsunamiSpeed(4200); // ~730 km/h
      const isochrones = [];

      for (let h = 1; h <= maxHours; h++) {
        const radiusKm = velocityKmh * h;
        const points = [];
        const numPoints = 64;

        for (let i = 0; i < numPoints; i++) {
          const theta = (i * 2 * Math.PI) / numPoints;
          // Bathymetry modulation (waves slow down near continental shelves)
          const bathymetryFactor = 0.9 + 0.15 * Math.sin(theta * 2);
          const r = radiusKm * bathymetryFactor;

          const dLat = (r * Math.cos(theta)) / 111.32;
          const dLon = (r * Math.sin(theta)) / (111.32 * Math.cos((epicenterLat * Math.PI) / 180));

          points.push([epicenterLat + dLat, epicenterLon + dLon]);
        }
        points.push(points[0]);

        isochrones.push({
          hoursElapsed: h,
          travelTimeLabel: `T + ${h}h 00m`,
          radiusKm: Math.round(radiusKm),
          waveSpeedKmh: velocityKmh,
          coordinates: points
        });
      }

      return isochrones;
    }

    /**
     * Omori Law Aftershock Decay Rate: n(t) = K / (c + t)^p
     * @param {number} daysElapsed 
     * @param {number} K - Productivity parameter
     * @param {number} c - Time offset
     * @param {number} p - Decay exponent (~1.0)
     * @returns {number} Expected aftershocks per day
     */
    calculateAftershocksPerDay(daysElapsed = 1.0, K = 85, c = 0.05, p = 1.08) {
      return Math.round(K / Math.pow(c + daysElapsed, p));
    }
  }

  window.seismicModel = new SeismicModel();

})(window);
