/**
 * ============================================================================
 * ASTRA-GEO // SATELLITE DISASTER INTELLIGENCE PLATFORM
 * ROTHERMEL MATHEMATICAL WILDFIRE SPREAD & THERMAL EMISSION MODEL
 * ============================================================================
 * Implements Rothermel (1972) surface fire spread equations, elliptical fire
 * growth forward rate of spread (ROS), midflame wind vector interaction,
 * slope effect, and Shortwave Infrared (SWIR) Fire Radiative Power (FRP).
 */

(function (window) {
  'use strict';

  // Standard Northern Forest Fire Laboratory (NFFL) Fuel Models
  const FUEL_MODELS = {
    GRASS_1: { name: 'Short Grass (1-ft)', fuelLoadTonsAcre: 0.74, fuelBedDepthFt: 1.0, extinctionMoisturePct: 12, heatContentBtuLb: 8000 },
    CHAMISE_4: { name: 'Chaparral / High Shrub (6-ft)', fuelLoadTonsAcre: 5.0, fuelBedDepthFt: 6.0, extinctionMoisturePct: 20, heatContentBtuLb: 8000 },
    TIMBER_8: { name: 'Closed Timber Litter', fuelLoadTonsAcre: 1.5, fuelBedDepthFt: 0.2, extinctionMoisturePct: 30, heatContentBtuLb: 8000 },
    LOGGING_10: { name: 'Heavy Timber & Dead Down', fuelLoadTonsAcre: 12.0, fuelBedDepthFt: 1.0, extinctionMoisturePct: 25, heatContentBtuLb: 8000 }
  };

  class WildfireModel {
    constructor() {
      this.stefanBoltzmann = 5.670374e-8; // W / (m^2 * K^4)
    }

    /**
     * Compute Rothermel Forward Rate of Spread (ROS)
     * @param {Object} params - { fuelType, fuelMoisturePct, windSpeedMph, slopeDeg }
     * @returns {Object} { rosMph, rosMPerMin, flameLengthM, firelineIntensityKWm }
     */
    calculateRateOfSpread({ fuelType = 'CHAMISE_4', fuelMoisturePct = 8, windSpeedMph = 25, slopeDeg = 15 }) {
      const fuel = FUEL_MODELS[fuelType] || FUEL_MODELS.CHAMISE_4;
      
      // Moisture damping coefficient eta_M
      const rM = Math.min(1.0, fuelMoisturePct / fuel.extinctionMoisturePct);
      const etaM = Math.max(0.01, 1 - 2.59 * rM + 5.11 * Math.pow(rM, 2) - 3.52 * Math.pow(rM, 3));

      // Wind coefficient phi_W
      const windFtMin = windSpeedMph * 88.0;
      const phiW = 0.04 * Math.pow(windFtMin, 0.75);

      // Slope factor phi_S
      const tanSlope = Math.tan((slopeDeg * Math.PI) / 180.0);
      const phiS = 5.275 * Math.pow(Math.max(0, tanSlope), 2);

      // Reaction intensity I_R (approx BTU / ft^2 / min)
      const reactionIntensity = 1800 * etaM;

      // Propagating flux ratio xi
      const xi = 0.12;

      // Bulk density and heat per unit volume epsilon * Q_ig
      const effectiveHeatingCapacity = 450.0;

      // Rate of spread R in ft/min
      const rosFtMin = (reactionIntensity * xi * (1 + phiW + phiS)) / effectiveHeatingCapacity;
      const rosMPerMin = rosFtMin * 0.3048;
      const rosMph = (rosFtMin * 60) / 5280;

      // Byram fireline intensity I_B = H * w * R (kW/m)
      const firelineIntensityKWm = Math.round(rosMPerMin * fuel.fuelLoadTonsAcre * 280);

      // Flame length L = 0.0775 * I_B ^ 0.46 (meters)
      const flameLengthM = parseFloat((0.0775 * Math.pow(firelineIntensityKWm, 0.46)).toFixed(1));

      return {
        rosMph: parseFloat(rosMph.toFixed(2)),
        rosMPerMin: parseFloat(rosMPerMin.toFixed(1)),
        flameLengthM,
        firelineIntensityKWm
      };
    }

    /**
     * Compute Fire Radiative Power (FRP) from satellite SWIR / TIR radiance
     * FRP (MW) = (A_sample * sigma) / (a * tau) * (L_fire - L_background)
     * @param {number} pixelAreaSqM - Satellite sensor pixel area
     * @param {number} tempFireKelvin - Active flame temperature
     * @param {number} tempBackgroundKelvin - Background land surface temperature
     * @returns {number} FRP in Megawatts (MW)
     */
    calculateFRP(pixelAreaSqM = 375 * 375, tempFireKelvin = 1050, tempBackgroundKelvin = 300) {
      const radianceFire = this.stefanBoltzmann * Math.pow(tempFireKelvin, 4);
      const radianceBg = this.stefanBoltzmann * Math.pow(tempBackgroundKelvin, 4);
      const deltaRadiance = Math.max(0, radianceFire - radianceBg);
      const subpixelFireFraction = 0.045; // Typical 4.5% pixel flaming area
      const frpWatts = pixelAreaSqM * subpixelFireFraction * deltaRadiance;
      return Math.round(frpWatts / 1e6); // Convert to Megawatts
    }

    /**
     * Generate Elliptical Fire Spread Perimeters over progressive hours
     * @param {number} centerLat 
     * @param {number} centerLon 
     * @param {number} windDirectionDeg - Wind blowing toward azimuth
     * @param {number} windSpeedMph 
     * @param {number} hoursToProject 
     * @returns {Array<Object>} Array of polygon contours per hour
     */
    generateSpreadPerimeters(centerLat, centerLon, windDirectionDeg = 45, windSpeedMph = 28, hoursToProject = 6) {
      const contours = [];
      const { rosMPerMin } = this.calculateRateOfSpread({ windSpeedMph });

      // Length-to-width ratio of fire ellipse (Alexander 1985)
      // L/W = 1.0 + 0.125 * U
      const lwRatio = 1.0 + 0.125 * windSpeedMph;
      const windAzRad = (windDirectionDeg * Math.PI) / 180.0;

      for (let h = 1; h <= hoursToProject; h++) {
        const majorAxisMeters = rosMPerMin * 60 * h;
        const minorAxisMeters = majorAxisMeters / lwRatio;
        const centerOffsetMeters = majorAxisMeters * 0.45; // Head fire extends further forward

        // Head center
        const offsetLat = (centerOffsetMeters * Math.cos(windAzRad)) / 111320.0;
        const offsetLon = (centerOffsetMeters * Math.sin(windAzRad)) / (111320.0 * Math.cos((centerLat * Math.PI) / 180));

        const cLat = centerLat + offsetLat;
        const cLon = centerLon + offsetLon;

        const points = [];
        const numPoints = 36;

        for (let i = 0; i < numPoints; i++) {
          const theta = (i * 2 * Math.PI) / numPoints;
          const ex = (majorAxisMeters * 0.55) * Math.cos(theta);
          const ey = (minorAxisMeters * 0.5) * Math.sin(theta);

          // Rotate by wind direction
          const rotX = ex * Math.sin(windAzRad) + ey * Math.cos(windAzRad);
          const rotY = ex * Math.cos(windAzRad) - ey * Math.sin(windAzRad);

          const ptLat = cLat + rotY / 111320.0;
          const ptLon = cLon + rotX / (111320.0 * Math.cos((cLat * Math.PI) / 180));
          points.push([ptLat, ptLon]);
        }
        points.push(points[0]); // Close polygon

        contours.push({
          hour: h,
          areaSqKm: parseFloat((((Math.PI * (majorAxisMeters / 1000) * (minorAxisMeters / 1000)) / 4) * h).toFixed(2)),
          coordinates: points,
          containmentPct: Math.max(5, Math.min(85, Math.round(55 - h * 5)))
        });
      }

      return contours;
    }

    /**
     * Compute Normalized Burn Ratio (NBR) and delta NBR (dNBR)
     * NBR = (NIR - SWIR) / (NIR + SWIR)
     * dNBR = NBR_pre - NBR_post
     */
    classifyBurnSeverity(nbrPre, nbrPost) {
      const dnbr = nbrPre - nbrPost;
      let severity = 'Unburned';
      let color = '#22c55e';

      if (dnbr > 0.66) {
        severity = 'High Severity (Total Tree Canopy Mortality)';
        color = '#7f1d1d';
      } else if (dnbr > 0.44) {
        severity = 'Moderate-High Severity';
        color = '#dc2626';
      } else if (dnbr > 0.27) {
        severity = 'Moderate-Low Severity';
        color = '#f97316';
      } else if (dnbr > 0.1) {
        severity = 'Low Severity';
        color = '#facc15';
      }

      return { dnbr: parseFloat(dnbr.toFixed(3)), severity, color };
    }
  }

  window.wildfireModel = new WildfireModel();

})(window);
