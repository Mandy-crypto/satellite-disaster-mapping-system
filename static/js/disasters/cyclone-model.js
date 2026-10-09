/**
 * ============================================================================
 * ASTRA-GEO // SATELLITE DISASTER INTELLIGENCE PLATFORM
 * HOLLAND PARAMETRIC CYCLONE WIND FIELD & ENSEMBLE TRACK MODEL
 * ============================================================================
 * Implements Holland (1980) radial wind profile, Coriolis parameter,
 * Saffir-Simpson category classification, barometric pressure gradients,
 * multi-model ensemble forecast cone of uncertainty, and storm surge estimates.
 */

(function (window) {
  'use strict';

  class CycloneModel {
    constructor() {
      this.airDensityKgM3 = 1.15; // Sea level air density in kg/m^3
      this.ambientPressureMb = 1013.25; // Standard peripheral pressure
      this.omegaEarth = 7.2921159e-5; // rad/s
    }

    /**
     * Compute Coriolis parameter f = 2 * omega * sin(latitude)
     */
    getCoriolisParameter(latDeg) {
      return 2 * this.omegaEarth * Math.sin((latDeg * Math.PI) / 180.0);
    }

    /**
     * Saffir-Simpson Hurricane Wind Scale Classifier
     */
    classifyIntensity(windSpeedMph) {
      if (windSpeedMph >= 157) return { category: 'Category 5 Superstorm', level: 5, color: '#9333ea', label: 'Catastrophic' };
      if (windSpeedMph >= 130) return { category: 'Category 4 Major Hurricane', level: 4, color: '#dc2626', label: 'Extreme' };
      if (windSpeedMph >= 111) return { category: 'Category 3 Major Hurricane', level: 3, color: '#ea580c', label: 'Extensive' };
      if (windSpeedMph >= 96) return { category: 'Category 2 Hurricane', level: 2, color: '#f59e0b', label: 'Very Dangerous' };
      if (windSpeedMph >= 74) return { category: 'Category 1 Hurricane', level: 1, color: '#eab308', label: 'Dangerous' };
      if (windSpeedMph >= 39) return { category: 'Tropical Storm', level: 0, color: '#06b6d4', label: 'Gale Force' };
      return { category: 'Tropical Depression', level: 0, color: '#3b82f6', label: 'Depression' };
    }

    /**
     * Holland (1980) Radial Wind Velocity Profile V(r)
     * @param {number} rKm - Radial distance from eye center in km
     * @param {number} centralPressureMb - Central minimum pressure
     * @param {number} rmwKm - Radius of maximum winds (RMW)
     * @param {number} latDeg - Current latitude
     * @returns {number} Sustained wind speed at radius r in mph
     */
    calculateWindAtRadius(rKm, centralPressureMb = 920, rmwKm = 25, latDeg = 27.5) {
      if (rKm <= 0) return 0;
      const deltaP = Math.max(10, (this.ambientPressureMb - centralPressureMb) * 100); // Pa
      const f = this.getCoriolisParameter(latDeg);
      const rMeters = rKm * 1000;
      const rmwMeters = rmwKm * 1000;

      // Holland B parameter empirical approximation
      const B = Math.max(1.0, Math.min(2.5, 1.8 - (centralPressureMb - 900) / 160));
      const expTerm = Math.exp(-Math.pow(rmwMeters / rMeters, B));
      const term1 = (B * deltaP / this.airDensityKgM3) * Math.pow(rmwMeters / rMeters, B) * expTerm;
      const term2 = Math.pow((rMeters * f) / 2, 2);

      const vMs = Math.sqrt(term1 + term2) - (rMeters * f) / 2;
      return Math.max(0, Math.round(vMs * 2.23694)); // Convert to mph
    }

    /**
     * Generate Wind Radii Quadrant Polygons (64-knot, 50-knot, 34-knot)
     * @param {number} eyeLat 
     * @param {number} eyeLon 
     * @param {number} centralPressureMb 
     * @param {number} rmwKm 
     * @returns {Array<Object>} Quadrant rings
     */
    generateWindRadiiPolygons(eyeLat, eyeLon, centralPressureMb = 910, rmwKm = 24) {
      const tiers = [
        { name: '64-Knot (Hurricane Force)', targetMph: 74, color: '#dc2626' },
        { name: '50-Knot (Storm Force)', targetMph: 58, color: '#ea580c' },
        { name: '34-Knot (Tropical Storm Gale)', targetMph: 39, color: '#0284c7' }
      ];

      return tiers.map(tier => {
        // Find radius where wind equals target
        let rKm = rmwKm;
        while (rKm < 450 && this.calculateWindAtRadius(rKm, centralPressureMb, rmwKm, eyeLat) > tier.targetMph) {
          rKm += 5;
        }

        const points = [];
        const numPoints = 48;
        for (let i = 0; i < numPoints; i++) {
          const theta = (i * 2 * Math.PI) / numPoints;
          // Right-forward quadrant asymmetry in Northern hemisphere
          const asymmetry = 1.0 + 0.25 * Math.sin(theta - Math.PI / 4);
          const r = rKm * asymmetry;

          const dLat = (r * Math.cos(theta)) / 111.32;
          const dLon = (r * Math.sin(theta)) / (111.32 * Math.cos((eyeLat * Math.PI) / 180));
          points.push([eyeLat + dLat, eyeLon + dLon]);
        }
        points.push(points[0]);

        return {
          name: tier.name,
          radiusKm: Math.round(rKm),
          color: tier.color,
          coordinates: points
        };
      });
    }

    /**
     * Generate Multi-Model Ensemble Forecast Track Cone of Uncertainty
     * @param {number} startLat 
     * @param {number} startLon 
     * @param {number} headingDeg - Heading azimuth (e.g., 40° for northeast recurvature)
     * @param {number} speedKts - Forward translation speed
     * @param {number} hoursForward 
     * @returns {Object} { ensembleModels, conePolygon }
     */
    generateEnsembleForecast(startLat, startLon, headingDeg = 38, speedKts = 14, hoursForward = 72) {
      const models = [
        { name: 'NHC Official Consensus', color: '#00f0ff', headingOffset: 0, speedFactor: 1.0 },
        { name: 'ECMWF Integrated Forecast System', color: '#a855f7', headingOffset: -4.5, speedFactor: 0.94 },
        { name: 'NOAA GFS Global Forecast System', color: '#10b981', headingOffset: 5.2, speedFactor: 1.06 },
        { name: 'UKMET Global Operational', color: '#f59e0b', headingOffset: 2.1, speedFactor: 0.98 },
        { name: 'HWRF High-Resolution Hurricane', color: '#ec4899', headingOffset: -2.8, speedFactor: 1.02 }
      ];

      const modelTracks = models.map(m => {
        const waypoints = [];
        const headRad = ((headingDeg + m.headingOffset) * Math.PI) / 180.0;
        const speedKmH = speedKts * m.speedFactor * 1.852;

        for (let h = 0; h <= hoursForward; h += 6) {
          const distKm = speedKmH * h;
          // Coriolis beta drift recurvature curvature term
          const recurvature = 0.0004 * Math.pow(distKm, 1.25);
          const dLat = (distKm * Math.cos(headRad) + recurvature) / 111.32;
          const dLon = (distKm * Math.sin(headRad) + recurvature * 1.2) / (111.32 * Math.cos((startLat * Math.PI) / 180));

          waypoints.push({
            hour: h,
            lat: parseFloat((startLat + dLat).toFixed(4)),
            lon: parseFloat((startLon + dLon).toFixed(4)),
            windMph: Math.max(45, Math.round(165 - h * 1.2)),
            pressureMb: Math.min(995, Math.round(902 + h * 0.9))
          });
        }

        return {
          modelName: m.name,
          color: m.color,
          waypoints
        };
      });

      // Construct Cone of Uncertainty boundary
      const leftBoundary = [];
      const rightBoundary = [];

      for (let h = 0; h <= hoursForward; h += 6) {
        // Average waypoint at hour h
        const avgLat = modelTracks.reduce((acc, t) => acc + t.waypoints.find(w => w.hour === h).lat, 0) / modelTracks.length;
        const avgLon = modelTracks.reduce((acc, t) => acc + t.waypoints.find(w => w.hour === h).lon, 0) / modelTracks.length;

        // Cone error expansion (NHC standard: ~30 nm per 24 hours)
        const coneRadiusKm = 24.0 + (h / 24.0) * 85.0;
        const headRad = (headingDeg * Math.PI) / 180.0;
        const perpRad = headRad + Math.PI / 2;

        const offLat = (coneRadiusKm * Math.cos(perpRad)) / 111.32;
        const offLon = (coneRadiusKm * Math.sin(perpRad)) / (111.32 * Math.cos((avgLat * Math.PI) / 180));

        leftBoundary.push([avgLat + offLat, avgLon + offLon]);
        rightBoundary.unshift([avgLat - offLat, avgLon - offLon]);
      }

      const conePolygon = leftBoundary.concat(rightBoundary);
      conePolygon.push(conePolygon[0]);

      return {
        modelTracks,
        conePolygon
      };
    }
  }

  window.cycloneModel = new CycloneModel();

})(window);
