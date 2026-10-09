/**
 * ============================================================================
 * ASTRA-GEO // SATELLITE DISASTER INTELLIGENCE PLATFORM
 * SURFACE RADIATION ENERGY BALANCE & THERMAL ANOMALY DETECTION ENGINE
 * ============================================================================
 * Implements Split-Window Land Surface Temperature (LST) algorithms,
 * Giglio et al. (2003) MODIS C6 contextual fire hotspot detection,
 * and surface radiation energy balance partitioning (Rn = H + G + LE).
 */

(function (window) {
  'use strict';

  class RadiationThermalBudgetEngine {
    constructor() {
      this.stefanBoltzmann = 5.670374e-8; // W / (m^2 * K^4)
      this.c1 = 1.19104e8; // First radiation constant (W * um^4 / m^2 / sr)
      this.c2 = 14387.7;   // Second radiation constant (um * K)
    }

    /**
     * Planck Inversion: Convert Spectral Radiance L_lambda to Brightness Temperature T_b (Kelvin)
     * T_b = c2 / (lambda * ln( (c1 / (lambda^5 * L_lambda)) + 1 ))
     * @param {number} radianceWPerM2SrUm - Radiance at sensor
     * @param {number} wavelengthUm - Channel wavelength in micrometers (e.g. 11.0 um for TIR)
     * @returns {number} Brightness temperature in Kelvin
     */
    radianceToBrightnessTemp(radianceWPerM2SrUm, wavelengthUm = 11.0) {
      if (radianceWPerM2SrUm <= 0) return 0;
      const num = this.c2 / wavelengthUm;
      const den = Math.log((this.c1 / (Math.pow(wavelengthUm, 5) * radianceWPerM2SrUm)) + 1.0);
      return parseFloat((num / den).toFixed(2));
    }

    /**
     * Split-Window Land Surface Temperature (LST) Retrieval
     * T_s = T11 + c1*(T11 - T12) + c2*(T11 - T12)^2 + c0 + (1 - eps)*c3 - deltaEps*c4
     * @param {number} t11Kelvin - Brightness temp in 11-um band (e.g. Landsat TIRS Band 10)
     * @param {number} t12Kelvin - Brightness temp in 12-um band (e.g. Landsat TIRS Band 11)
     * @param {number} meanEmissivity - Surface emissivity (approx 0.96 for soil/vegetation)
     * @param {number} deltaEmissivity - Emissivity difference between bands
     * @returns {Object} { lstKelvin, lstCelsius }
     */
    calculateSplitWindowLST(t11Kelvin = 305.2, t12Kelvin = 302.8, meanEmissivity = 0.965, deltaEmissivity = 0.005) {
      const deltaT = t11Kelvin - t12Kelvin;

      // Sobrino et al. (2008) split-window regression coefficients
      const c0 = -0.268;
      const c1 = 1.378;
      const c2 = 0.183;
      const c3 = 54.3;
      const c4 = -22.4;

      const lstKelvin = t11Kelvin + c1 * deltaT + c2 * Math.pow(deltaT, 2) + c0 +
        (1 - meanEmissivity) * c3 - deltaEmissivity * c4;
      const lstCelsius = lstKelvin - 273.15;

      return {
        t11Kelvin,
        t12Kelvin,
        lstKelvin: parseFloat(lstKelvin.toFixed(2)),
        lstCelsius: parseFloat(lstCelsius.toFixed(1))
      };
    }

    /**
     * Giglio et al. Contextual Active Fire Detection Algorithm (MODIS C6 / VIIRS)
     * Tests middle-infrared (4-um, e.g. MODIS Band 21/22) vs thermal (11-um, Band 31)
     * @param {number} t4Kelvin - 4-um brightness temperature
     * @param {number} t11Kelvin - 11-um brightness temperature
     * @param {number} bgT4Mean - Background window mean 4-um temp
     * @param {number} bgT4Mad - Background window mean absolute deviation
     * @param {number} bgDeltaMean - Background (T4 - T11) mean
     * @param {number} bgDeltaMad - Background (T4 - T11) MAD
     * @returns {Object} { isFire, confidenceScore, reason }
     */
    detectActiveFireHotspot(t4Kelvin, t11Kelvin, bgT4Mean = 298.0, bgT4Mad = 2.5, bgDeltaMean = 2.0, bgDeltaMad = 1.8) {
      const deltaT = t4Kelvin - t11Kelvin;

      // Absolute threshold test for flaming infernos (T4 > 360 K daytime or 320 K nighttime)
      if (t4Kelvin > 360.0) {
        return { isFire: true, confidenceScore: 100, reason: 'Absolute High-Radiance Flaming Anomaly (T4 > 360 K)' };
      }

      // Contextual threshold tests:
      // Test 1: T4 must exceed background by 3 * MAD
      const test1 = t4Kelvin > (bgT4Mean + 3.0 * bgT4Mad);
      // Test 2: Delta T (T4 - T11) must exceed background difference by 3.5 * MAD
      const test2 = deltaT > (bgDeltaMean + 3.5 * bgDeltaMad);
      // Test 3: Absolute delta T must exceed minimum threshold
      const test3 = deltaT > 10.0;

      const isFire = test1 && test2 && test3;
      let confidence = 0;
      if (isFire) {
        // Calculate ramp confidence score
        confidence = Math.min(99, Math.round(50 + (deltaT - 10) * 2.5 + (t4Kelvin - bgT4Mean) * 1.5));
      }

      return {
        isFire,
        confidenceScore: confidence,
        deltaT: parseFloat(deltaT.toFixed(2)),
        reason: isFire ? 'Contextual Spectral Contrast Validated Fire Pixel' : 'Background Surface Thermal Variation'
      };
    }

    /**
     * Surface Energy Balance Partitioning: Rn = H + G + LE
     * Rn: Net Radiation, H: Sensible Heat, G: Soil Heat, LE: Latent Heat (evaporation)
     * @param {number} netRadiationWPerM2 
     * @param {number} soilMoistureFraction - [0.0, 1.0]
     * @returns {Object} Energy fluxes in W/m^2
     */
    partitionEnergyBalance(netRadiationWPerM2 = 550, soilMoistureFraction = 0.45) {
      // Soil heat flux G ~ 10-15% of Rn
      const gFlux = netRadiationWPerM2 * 0.12;
      const availableEnergy = netRadiationWPerM2 - gFlux;

      // Priestley-Taylor parameter alpha based on soil water availability
      const alpha = Math.min(1.26, Math.max(0.2, soilMoistureFraction * 1.8));

      // Latent heat flux LE
      const leFlux = availableEnergy * (alpha / 1.26) * 0.75;
      // Sensible heat flux H (Bowen ratio balance)
      const hFlux = availableEnergy - leFlux;

      const bowenRatio = hFlux / Math.max(1, leFlux);

      return {
        netRadiationWPerM2,
        sensibleHeatFluxH: Math.round(hFlux),
        latentHeatFluxLE: Math.round(leFlux),
        soilHeatFluxG: Math.round(gFlux),
        bowenRatio: parseFloat(bowenRatio.toFixed(2)),
        evaporativeFraction: parseFloat((leFlux / availableEnergy).toFixed(2))
      };
    }
  }

  window.radiationThermalEngine = new RadiationThermalBudgetEngine();

})(window);
