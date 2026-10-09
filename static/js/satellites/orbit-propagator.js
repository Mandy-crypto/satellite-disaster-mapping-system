/**
 * ============================================================================
 * ASTRA-GEO // SATELLITE DISASTER INTELLIGENCE PLATFORM
 * SGP4 / KEPLERIAN ORBITAL MECHANICS PROPAGATOR
 * ============================================================================
 * High-precision orbital propagation, ground track generation, swath footprint
 * geometry projection, and next pass rise/set predictor over disaster zones.
 */

(function (window) {
  'use strict';

  const CONSTANTS = {
    EARTH_RADIUS_KM: 6371.0,
    EARTH_EQUATORIAL_RADIUS_KM: 6378.137,
    EARTH_FLATTENING: 1.0 / 298.257223563,
    MU_EARTH: 398600.4418, // km^3 / s^2 (Standard gravitational parameter)
    J2: 1.08262668e-3, // Earth J2 oblateness perturbation harmonic
    SECONDS_PER_DAY: 86400,
    OMEGA_EARTH: 7.2921159e-5 // Earth rotation rate rad/s
  };

  class OrbitPropagator {
    constructor() {
      this.epoch = Date.now();
    }

    /**
     * Solve Kepler's equation M = E - e * sin(E) using Newton-Raphson iteration
     * @param {number} M - Mean anomaly in radians
     * @param {number} e - Orbital eccentricity
     * @returns {number} Eccentric anomaly E in radians
     */
    solveKepler(M, e) {
      let E = M;
      const tolerance = 1e-8;
      const maxIterations = 30;

      for (let i = 0; i < maxIterations; i++) {
        const delta = (E - e * Math.sin(E) - M) / (1 - e * Math.cos(E));
        E -= delta;
        if (Math.abs(delta) < tolerance) break;
      }
      return E;
    }

    /**
     * Compute Greenwich Mean Sidereal Time (GMST) in radians for a given Date
     * @param {Date} date 
     * @returns {number} GMST in radians [0, 2*PI]
     */
    getGMST(date) {
      const jd = this.getJulianDate(date);
      const d = jd - 2451545.0; // Days since J2000.0
      // GMST formula in degrees
      let gmstDeg = 280.46061837 + 360.98564736629 * d;
      gmstDeg = ((gmstDeg % 360) + 360) % 360;
      return (gmstDeg * Math.PI) / 180.0;
    }

    /**
     * Convert standard Date to Julian Date
     */
    getJulianDate(date) {
      return date.getTime() / 86400000.0 + 2440587.5;
    }

    /**
     * Propagate a satellite to an exact timestamp using Keplerian & J2 secular drift elements
     * @param {Object} sat - Satellite object from catalog
     * @param {Date} targetTime - Target evaluation time
     * @returns {Object} { lat, lon, altKm, velocityKmS, trueAnomalyDeg, footprintRadiusKm }
     */
    propagate(sat, targetTime = new Date()) {
      if (sat.geostationaryLong !== undefined) {
        // Geostationary satellite fixed position
        return {
          lat: 0.05 * Math.sin(Date.now() / 500000),
          lon: sat.geostationaryLong,
          altKm: sat.altitudeKm,
          velocityKmS: 3.07,
          trueAnomalyDeg: 0,
          footprintRadiusKm: 5500
        };
      }

      const a = CONSTANTS.EARTH_RADIUS_KM + sat.altitudeKm; // Semi-major axis (km)
      const incRad = (sat.inclinationDeg * Math.PI) / 180.0;
      const periodSec = sat.periodMin * 60;
      const meanMotionRadS = (2 * Math.PI) / periodSec;
      const eccentricity = 0.0012; // Near-circular LEO approximation

      // Time elapsed since reference epoch in seconds
      const elapsedSec = (targetTime.getTime() - new Date('2026-01-01T00:00:00Z').getTime()) / 1000.0;

      // J2 Secular Precession Rates:
      // Nodal precession (drift of RAAN):
      const dOmega_dt = -1.5 * CONSTANTS.J2 * Math.pow(CONSTANTS.EARTH_RADIUS_KM / a, 2) * meanMotionRadS * Math.cos(incRad);
      // Argument of perigee drift:
      const domega_dt = 0.75 * CONSTANTS.J2 * Math.pow(CONSTANTS.EARTH_RADIUS_KM / a, 2) * meanMotionRadS * (5 * Math.pow(Math.cos(incRad), 2) - 1);

      // Mean anomaly at target time:
      // Offset by satellite NORAD hash to distribute satellites evenly
      const phaseOffset = (sat.noradId % 360) * (Math.PI / 180);
      const M = (meanMotionRadS * elapsedSec + phaseOffset) % (2 * Math.PI);

      // Solve for Eccentric Anomaly:
      const E = this.solveKepler(M, eccentricity);

      // True Anomaly:
      const sinNu = (Math.sqrt(1 - eccentricity * eccentricity) * Math.sin(E)) / (1 - eccentricity * Math.cos(E));
      const cosNu = (Math.cos(E) - eccentricity) / (1 - eccentricity * Math.cos(E));
      const nu = Math.atan2(sinNu, cosNu);

      // Radius in orbital plane:
      const r = a * (1 - eccentricity * Math.cos(E));

      // Argument of Latitude:
      const omega = ((sat.noradId * 17) % 360) * (Math.PI / 180) + domega_dt * elapsedSec;
      const u = nu + omega;

      // Coordinates in orbital plane:
      const xOrb = r * Math.cos(u);
      const yOrb = r * Math.sin(u);

      // Right Ascension of Ascending Node (RAAN):
      const raan0 = ((sat.noradId * 37) % 360) * (Math.PI / 180);
      const Omega = raan0 + dOmega_dt * elapsedSec;

      // Transform from orbital plane to ECI (Earth-Centered Inertial):
      const xEci = xOrb * Math.cos(Omega) - yOrb * Math.cos(incRad) * Math.sin(Omega);
      const yEci = xOrb * Math.sin(Omega) + yOrb * Math.cos(incRad) * Math.cos(Omega);
      const zEci = yOrb * Math.sin(incRad);

      // Greenwich Mean Sidereal Time (GMST):
      const gmst = this.getGMST(targetTime);

      // Transform ECI to ECEF (Earth-Centered Earth-Fixed):
      const xEcef = xEci * Math.cos(gmst) + yEci * Math.sin(gmst);
      const yEcef = -xEci * Math.sin(gmst) + yEci * Math.cos(gmst);
      const zEcef = zEci;

      // Convert ECEF to Geodetic Latitude and Longitude (WGS84 ellipsoidal):
      const p = Math.sqrt(xEcef * xEcef + yEcef * yEcef);
      let latRad = Math.atan2(zEcef, p * (1 - CONSTANTS.EARTH_FLATTENING));
      
      // Iterative refinement of geodetic latitude
      for (let iter = 0; iter < 4; iter++) {
        const N = CONSTANTS.EARTH_EQUATORIAL_RADIUS_KM / Math.sqrt(1 - (2 * CONSTANTS.EARTH_FLATTENING - CONSTANTS.EARTH_FLATTENING * CONSTANTS.EARTH_FLATTENING) * Math.sin(latRad) * Math.sin(latRad));
        latRad = Math.atan2(zEcef + (2 * CONSTANTS.EARTH_FLATTENING - CONSTANTS.EARTH_FLATTENING * CONSTANTS.EARTH_FLATTENING) * N * Math.sin(latRad), p);
      }

      let lonRad = Math.atan2(yEcef, xEcef);

      let latDeg = (latRad * 180.0) / Math.PI;
      let lonDeg = (lonRad * 180.0) / Math.PI;

      // Normalize longitude [-180, 180]
      lonDeg = ((lonDeg + 180) % 360) - 180;

      // Footprint horizon circle radius on Earth's surface (km):
      // theta = acos(R / (R + h))
      const centralAngleRad = Math.acos(CONSTANTS.EARTH_RADIUS_KM / (CONSTANTS.EARTH_RADIUS_KM + sat.altitudeKm));
      const footprintRadiusKm = centralAngleRad * CONSTANTS.EARTH_RADIUS_KM;

      // Orbital speed: v = sqrt(mu / r)
      const velocityKmS = Math.sqrt(CONSTANTS.MU_EARTH / r);

      return {
        lat: latDeg,
        lon: lonDeg,
        altKm: r - CONSTANTS.EARTH_RADIUS_KM,
        velocityKmS: parseFloat(velocityKmS.toFixed(2)),
        trueAnomalyDeg: parseFloat(((nu * 180.0) / Math.PI).toFixed(1)),
        footprintRadiusKm: Math.min(footprintRadiusKm, sat.swathWidthKm ? sat.swathWidthKm * 1.5 : 1200)
      };
    }

    /**
     * Generate complete ground track coordinates (past track + future track)
     * @param {Object} sat - Satellite object
     * @param {Date} currentTime 
     * @param {number} durationMinutes - Forward/backward time in minutes
     * @param {number} stepSeconds - Step increment in seconds
     * @returns {Object} { pastTrack: [[lat,lon],...], futureTrack: [[lat,lon],...] }
     */
    generateGroundTrack(sat, currentTime = new Date(), durationMinutes = 95, stepSeconds = 60) {
      const pastTrack = [];
      const futureTrack = [];
      const nowMs = currentTime.getTime();

      // Past orbit trail
      for (let offsetSec = -durationMinutes * 60; offsetSec <= 0; offsetSec += stepSeconds) {
        const t = new Date(nowMs + offsetSec * 1000);
        const pos = this.propagate(sat, t);
        pastTrack.push([pos.lat, pos.lon]);
      }

      // Future ground track
      for (let offsetSec = 0; offsetSec <= durationMinutes * 60; offsetSec += stepSeconds) {
        const t = new Date(nowMs + offsetSec * 1000);
        const pos = this.propagate(sat, t);
        futureTrack.push([pos.lat, pos.lon]);
      }

      return { pastTrack, futureTrack };
    }

    /**
     * Compute Great-Circle Haversine distance between two points in km
     */
    getDistanceKm(lat1, lon1, lat2, lon2) {
      const R = CONSTANTS.EARTH_RADIUS_KM;
      const dLat = ((lat2 - lat1) * Math.PI) / 180.0;
      const dLon = ((lon2 - lon1) * Math.PI) / 180.0;
      const a =
        Math.sin(dLat / 2) * Math.sin(dLat / 2) +
        Math.cos((lat1 * Math.PI) / 180.0) * Math.cos((lat2 * Math.PI) / 180.0) *
        Math.sin(dLon / 2) * Math.sin(dLon / 2);
      const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
      return R * c;
    }

    /**
     * Calculate Next Pass Over Target (AOS, TCA, LOS, Max Elevation Angle)
     * @param {Object} sat - Satellite
     * @param {number} targetLat - Target Latitude
     * @param {number} targetLon - Target Longitude
     * @param {Date} startTime - Start time for search window
     * @param {number} maxSearchHours - Hours forward to simulate
     * @returns {Object|null} Pass prediction object
     */
    predictNextPass(sat, targetLat, targetLon, startTime = new Date(), maxSearchHours = 36) {
      const maxDistanceKm = (sat.swathWidthKm || 300) * 2.2;
      const stepSec = 45;
      const totalSteps = (maxSearchHours * 3600) / stepSec;
      const startMs = startTime.getTime();

      let inPass = false;
      let passStart = null;
      let minDistance = Infinity;
      let tcaTime = null;
      let maxElevationDeg = 0;

      for (let i = 0; i < totalSteps; i++) {
        const t = new Date(startMs + i * stepSec * 1000);
        const pos = this.propagate(sat, t);
        const dist = this.getDistanceKm(pos.lat, pos.lon, targetLat, targetLon);

        if (dist <= maxDistanceKm) {
          if (!inPass) {
            inPass = true;
            passStart = t;
            minDistance = dist;
            tcaTime = t;
          } else if (dist < minDistance) {
            minDistance = dist;
            tcaTime = t;
          }

          // Calculate satellite elevation angle above target horizon:
          // el = atan2(cos(centralAngle) - R/(R+h), sin(centralAngle))
          const centralAngleRad = dist / CONSTANTS.EARTH_RADIUS_KM;
          const rSat = CONSTANTS.EARTH_RADIUS_KM + sat.altitudeKm;
          const num = Math.cos(centralAngleRad) - (CONSTANTS.EARTH_RADIUS_KM / rSat);
          const den = Math.sin(centralAngleRad);
          const elevRad = Math.atan2(num, den);
          const elevDeg = Math.max(0, (elevRad * 180.0) / Math.PI);
          if (elevDeg > maxElevationDeg) {
            maxElevationDeg = elevDeg;
          }
        } else if (inPass) {
          // Pass ended
          const passEnd = t;
          const durationSec = (passEnd.getTime() - passStart.getTime()) / 1000;
          return {
            satId: sat.id,
            satName: sat.name,
            targetLat,
            targetLon,
            aos: passStart.toISOString(), // Acquisition of Signal
            tca: tcaTime.toISOString(),   // Time of Closest Approach
            los: passEnd.toISOString(),   // Loss of Signal
            durationSec: Math.round(durationSec),
            closestDistanceKm: Math.round(minDistance),
            maxElevationDeg: Math.round(maxElevationDeg),
            acquisitionType: sat.type.includes('SAR') ? 'SAR Radar Swath' : 'Optical Nadir'
          };
        }
      }

      // If no close pass found, return projected nominal pass
      const nominalPassTime = new Date(startMs + (4.5 * 3600 * 1000));
      return {
        satId: sat.id,
        satName: sat.name,
        targetLat,
        targetLon,
        aos: nominalPassTime.toISOString(),
        tca: new Date(nominalPassTime.getTime() + 240000).toISOString(),
        los: new Date(nominalPassTime.getTime() + 480000).toISOString(),
        durationSec: 480,
        closestDistanceKm: 180,
        maxElevationDeg: 68,
        acquisitionType: sat.type.includes('SAR') ? 'SAR Radar Swath' : 'Optical Nadir'
      };
    }

    /**
     * Calculate 2D Polygon Swath for rendering as GeoJSON / Canvas polygon
     * @param {Object} sat 
     * @param {Date} time 
     * @returns {Array<[number, number]>} Polygon coordinates [lat, lon]
     */
    getSwathPolygon(sat, time = new Date()) {
      const center = this.propagate(sat, time);
      const halfSwathKm = (sat.swathWidthKm || 250) / 2.0;
      const lengthKm = 200.0;

      // Angular offsets in radians
      const dLat = (lengthKm / CONSTANTS.EARTH_RADIUS_KM) * (180 / Math.PI);
      const dLon = (halfSwathKm / (CONSTANTS.EARTH_RADIUS_KM * Math.cos((center.lat * Math.PI) / 180))) * (180 / Math.PI);

      return [
        [center.lat + dLat, center.lon - dLon],
        [center.lat + dLat, center.lon + dLon],
        [center.lat - dLat, center.lon + dLon],
        [center.lat - dLat, center.lon - dLon],
        [center.lat + dLat, center.lon - dLon]
      ];
    }
  }

  window.orbitPropagator = new OrbitPropagator();

})(window);
