/**
 * ============================================================================
 * ASTRA-GEO // SATELLITE DISASTER INTELLIGENCE PLATFORM
 * HYDRODYNAMIC FLOOD INUNDATION & DEM SLICING MODEL
 * ============================================================================
 * Simulates digital elevation model (DEM) water depth slicing, river basin runoff,
 * inundated surface area, water volume metrics, SAR radar backscatter drop,
 * and critical infrastructure vulnerability exposure.
 */

(function (window) {
  'use strict';

  class FloodModel {
    constructor() {
      this.gravity = 9.80665; // m/s^2
    }

    /**
     * Compute Inundation Area and Water Volume based on water surge level
     * @param {Object} basinParams - { baselineElevationM, surgeHeightM, basinAreaSqKm, soilSaturationPct }
     * @returns {Object} { inundatedAreaSqKm, waterVolumeM3, maxDepthM, criticalAssetsAtRisk }
     */
    simulateSurgeInundation({ baselineElevationM = 15.0, surgeHeightM = 2.8, basinAreaSqKm = 350.0, soilSaturationPct = 95 }) {
      // Non-linear elevation hypsometric curve of river floodplain
      // Lower elevation terrain floods exponentially faster
      const runoffRatio = Math.min(1.0, 0.4 + (soilSaturationPct / 100) * 0.6);
      const effectiveSurge = surgeHeightM * runoffRatio;

      // Inundated fraction of floodplain area
      const floodedFraction = Math.min(0.95, Math.pow(effectiveSurge / 4.0, 0.85));
      const inundatedAreaSqKm = parseFloat((basinAreaSqKm * floodedFraction).toFixed(1));

      // Estimated water volume in cubic meters: V = Area * MeanDepth
      const meanDepthM = effectiveSurge * 0.58;
      const waterVolumeM3 = Math.round(inundatedAreaSqKm * 1e6 * meanDepthM);

      // Infrastructure exposure estimator based on urban density
      const buildingDensityPerSqKm = 420;
      const submergedBuildings = Math.round(inundatedAreaSqKm * buildingDensityPerSqKm * 0.45);
      const severedRoadKm = parseFloat((inundatedAreaSqKm * 1.85).toFixed(1));
      const floodedSubstations = Math.max(1, Math.round(inundatedAreaSqKm * 0.04));

      return {
        inundatedAreaSqKm,
        waterVolumeM3,
        meanDepthM: parseFloat(meanDepthM.toFixed(2)),
        maxDepthM: parseFloat(effectiveSurge.toFixed(2)),
        submergedBuildings,
        severedRoadKm,
        floodedSubstations
      };
    }

    /**
     * Compute SAR Radar Backscatter Drop (dB)
     * Calm standing water acts as a specular reflector, scattering radar pulses
     * away from the receiver, producing a sharp drop in backscatter sigma-0.
     * @param {number} preBackscatterDb - Dry land (typically -8 to -11 dB)
     * @param {number} postBackscatterDb - Inundated land (typically -20 to -26 dB)
     * @returns {Object} { deltaDb, isWater, confidencePct }
     */
    detectWaterSAR(preBackscatterDb = -9.2, postBackscatterDb = -22.8) {
      const deltaDb = postBackscatterDb - preBackscatterDb;
      const isWater = postBackscatterDb < -18.0 && deltaDb < -6.0;
      const confidencePct = Math.min(99, Math.max(20, Math.round(Math.abs(deltaDb) * 6.5)));

      return {
        preBackscatterDb,
        postBackscatterDb,
        deltaDb: parseFloat(deltaDb.toFixed(2)),
        isWater,
        confidencePct
      };
    }

    /**
     * Generate Inundation Polygon Contours around a central river / coast
     * @param {number} centerLat 
     * @param {number} centerLon 
     * @param {number} radiusKm 
     * @param {number} surgeHeightM 
     * @returns {Array<Object>} Multi-tier flood depth contours
     */
    generateFloodContours(centerLat, centerLon, radiusKm = 8.0, surgeHeightM = 2.8) {
      const contours = [];
      const depthTiers = [
        { label: 'Deep Inundation (> 2.0m)', depth: surgeHeightM, scale: 0.55, color: '#0369a1' },
        { label: 'Moderate Inundation (1.0m - 2.0m)', depth: surgeHeightM * 0.65, scale: 0.85, color: '#0ea5e9' },
        { label: 'Shallow Flow / Waterlogged (< 1.0m)', depth: surgeHeightM * 0.35, scale: 1.15, color: '#7dd3fc' }
      ];

      depthTiers.forEach((tier) => {
        const points = [];
        const numPoints = 48;
        const rKm = radiusKm * tier.scale;

        for (let i = 0; i < numPoints; i++) {
          const theta = (i * 2 * Math.PI) / numPoints;
          // Organic river meandering noise
          const noise = 1 + 0.28 * Math.sin(theta * 3.5) + 0.18 * Math.cos(theta * 5.2);
          const distKm = rKm * noise;

          const dLat = (distKm * Math.cos(theta)) / 111.32;
          const dLon = (distKm * Math.sin(theta)) / (111.32 * Math.cos((centerLat * Math.PI) / 180));

          points.push([centerLat + dLat, centerLon + dLon]);
        }
        points.push(points[0]); // Close ring

        contours.push({
          tier: tier.label,
          waterDepthM: parseFloat(tier.depth.toFixed(1)),
          color: tier.color,
          coordinates: points
        });
      });

      return contours;
    }

    /**
     * Compute Flood Recession Time Decay (Days to Drain)
     * h(t) = h0 * exp(-k * t)
     * @param {number} initialDepthM 
     * @param {number} drainageRateMPerDay 
     * @returns {number} Days until water recedes below 0.15m
     */
    estimateDaysToRecede(initialDepthM = 2.8, drainageRateMPerDay = 0.45) {
      const targetDepthM = 0.15;
      if (initialDepthM <= targetDepthM) return 0;
      const decayK = drainageRateMPerDay / initialDepthM;
      const days = Math.log(initialDepthM / targetDepthM) / decayK;
      return parseFloat(days.toFixed(1));
    }
  }

  window.floodModel = new FloodModel();

})(window);
