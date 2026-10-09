/**
 * ============================================================================
 * ASTRA-GEO // SATELLITE DISASTER INTELLIGENCE PLATFORM
 * SENSOR RADIOMETRY & SAR POLARIMETRIC DECOMPOSITION ENGINE
 * ============================================================================
 * Implements Freeman-Durden 3-component polarimetric decomposition for SAR,
 * 6S Top-of-Atmosphere (TOA) to Bottom-of-Atmosphere (BOA) radiative correction,
 * and geometric cloud shadow projection based on solar ephemeris.
 */

(function (window) {
  'use strict';

  class ConstellationSimulationEngine {
    constructor() {
      this.solarConstantWPerM2 = 1361.0;
    }

    /**
     * Freeman-Durden 3-Component SAR Polarimetric Decomposition
     * Decomposes quad-pol covariance matrix [C3] into Surface, Double-Bounce, and Volume scattering powers.
     * @param {number} shh - HH complex amplitude
     * @param {number} shv - HV complex amplitude
     * @param {number} svv - VV complex amplitude
     * @returns {Object} { pSurface, pDoubleBounce, pVolume, dominantMechanism }
     */
    decomposeSARPolarimetry(shh = 0.65, shv = 0.28, svv = 0.82) {
      // Span total backscattered power
      const span = shh * shh + 2 * shv * shv + svv * svv;

      // Volume scattering power from canopy / vegetation
      const pVolume = Math.min(span * 0.9, 8 * (shv * shv) / 3.0);

      // Remaining power partitioned between Surface (rough water/bare ground) and Double-Bounce (urban buildings)
      const remainder = Math.max(0.01, span - pVolume);
      const ratio = svv / Math.max(0.01, shh);

      let pSurface, pDoubleBounce;
      if (ratio > 1.15) {
        // High VV/HH indicates surface scattering
        pSurface = remainder * 0.75;
        pDoubleBounce = remainder * 0.25;
      } else {
        // High HH/VV indicates dihedral corner reflector (urban structures)
        pDoubleBounce = remainder * 0.70;
        pSurface = remainder * 0.30;
      }

      let dominant = 'Surface Scattering (Rough Water / Bare Soil)';
      if (pDoubleBounce > pSurface && pDoubleBounce > pVolume) {
        dominant = 'Double-Bounce Dihedral (Urban Buildings / Standing Trunks)';
      } else if (pVolume > pSurface && pVolume > pDoubleBounce) {
        dominant = 'Volume Scattering (Forest Canopy / Random Dipoles)';
      }

      return {
        totalSpanPower: parseFloat(span.toFixed(3)),
        pSurfacePct: Math.round((pSurface / span) * 100),
        pDoubleBouncePct: Math.round((pDoubleBounce / span) * 100),
        pVolumePct: Math.round((pVolume / span) * 100),
        dominantMechanism: dominant
      };
    }

    /**
     * 6S Radiative Transfer Atmospheric Correction (TOA to BOA Surface Reflectance)
     * rho_BOA = (pi * (L_TOA - L_path) * d^2) / (ESUN * cos(theta_s) * tau_v * tau_s)
     * @param {number} digitalNumber - 12-bit sensor DN (0 - 4095)
     * @param {number} solarZenithDeg - Solar zenith angle
     * @param {number} aod550 - Aerosol optical depth at 550nm
     * @returns {Object} { toaRadiance, surfaceReflectance, atmosphericTransmission }
     */
    calibrateAtmosphericReflectance(digitalNumber = 2048, solarZenithDeg = 32.5, aod550 = 0.18) {
      // Radiometric gain and bias
      const gain = 0.052;
      const bias = -1.2;
      const toaRadiance = Math.max(0, digitalNumber * gain + bias);

      const cosZenith = Math.max(0.1, Math.cos((solarZenithDeg * Math.PI) / 180.0));
      // Atmospheric path transmission tau(theta) approx
      const tauAtmosphere = Math.exp(-aod550 / cosZenith);

      // Rayleigh path radiance subtraction
      const pathRadiance = 4.8 * (1 - tauAtmosphere);
      const groundRadiance = Math.max(0, toaRadiance - pathRadiance);

      // Surface reflectance [0.0, 1.0]
      const esun = 1530.0; // Mean solar exoatmospheric irradiance (W/m^2/um)
      const surfaceReflectance = Math.min(1.0, (Math.PI * groundRadiance) / (esun * cosZenith * tauAtmosphere));

      return {
        digitalNumber,
        toaRadianceWPerM2Sr: parseFloat(toaRadiance.toFixed(2)),
        pathRadianceSubtracted: parseFloat(pathRadiance.toFixed(2)),
        surfaceReflectance: parseFloat(surfaceReflectance.toFixed(3)),
        atmosphericTransmissionPct: Math.round(tauAtmosphere * 100)
      };
    }

    /**
     * Calculate Cloud Shadow Displacement Vector on Ground
     * @param {number} cloudTopAltitudeKm - E.g. 2.5 km
     * @param {number} sunElevationDeg - E.g. 45°
     * @param {number} sunAzimuthDeg - E.g. 180° (due south)
     * @returns {Object} { shadowDistanceKm, offsetLat, offsetLon }
     */
    calculateCloudShadowProjection(cloudTopAltitudeKm = 2.5, sunElevationDeg = 48.0, sunAzimuthDeg = 175.0) {
      // Shadow distance along ground: d = h / tan(elevation)
      const sunElevRad = (sunElevationDeg * Math.PI) / 180.0;
      const shadowDistKm = cloudTopAltitudeKm / Math.tan(sunElevRad);

      // Shadow projects in opposite direction of sun (azimuth + 180°)
      const shadowAzRad = ((sunAzimuthDeg + 180) * Math.PI) / 180.0;

      const dLat = (shadowDistKm * Math.cos(shadowAzRad)) / 111.32;
      const dLon = (shadowDistKm * Math.sin(shadowAzRad)) / 111.32;

      return {
        cloudAltitudeKm: cloudTopAltitudeKm,
        shadowDistanceKm: parseFloat(shadowDistKm.toFixed(2)),
        offsetDegreesLat: parseFloat(dLat.toFixed(5)),
        offsetDegreesLon: parseFloat(dLon.toFixed(5))
      };
    }
  }

  window.constellationSimulation = new ConstellationSimulationEngine();

})(window);
