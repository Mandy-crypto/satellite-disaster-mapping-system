/**
 * ============================================================================
 * ASTRA-GEO // SATELLITE DISASTER INTELLIGENCE PLATFORM
 * MASS-CASUALTY TRIAGE & EMERGENCY MEDEVAC DISPATCH SYSTEM
 * ============================================================================
 * Implements START (Simple Triage and Rapid Treatment) algorithms, trauma center
 * ICU bed saturation tracking, and air ambulance MEDEVAC flight coordination.
 */

(function (window) {
  'use strict';

  // Regional Level-1 & Level-2 Trauma Hospitals
  const TRAUMA_HOSPITALS = [
    {
      id: 'HOSP-LA-FE',
      name: 'Hospital Universitari i Politècnic La Fe (Valencia)',
      level: 'Level 1 Comprehensive Trauma Center',
      lat: 39.4442,
      lon: -0.3776,
      helipadActive: true,
      totalBeds: 1000,
      icuBedsTotal: 120,
      icuBedsAvailable: 18,
      operatingRoomsActive: 14,
      bloodUnitsO_NegRemaining: 85,
      status: 'SURGE CAPACITY ACTIVATED'
    },
    {
      id: 'HOSP-CLINICO',
      name: 'Hospital Clínico Universitario de Valencia',
      level: 'Level 2 Trauma Center',
      lat: 39.4775,
      lon: -0.3582,
      helipadActive: false,
      totalBeds: 580,
      icuBedsTotal: 65,
      icuBedsAvailable: 6,
      operatingRoomsActive: 8,
      bloodUnitsO_NegRemaining: 42,
      status: 'APPROACHING SATURATION'
    },
    {
      id: 'HOSP-GENERAL',
      name: 'Hospital General Universitari de Valencia',
      level: 'Level 2 Trauma Center',
      lat: 39.4678,
      lon: -0.4072,
      helipadActive: true,
      totalBeds: 500,
      icuBedsTotal: 50,
      icuBedsAvailable: 9,
      operatingRoomsActive: 6,
      bloodUnitsO_NegRemaining: 38,
      status: 'OPERATIONAL'
    }
  ];

  class CasualtyTriageSystem {
    constructor() {
      this.hospitals = JSON.parse(JSON.stringify(TRAUMA_HOSPITALS));
      this.activeMedevacs = [];
    }

    /**
     * Compute START Triage Distribution for an active disaster incident
     * @param {Object} disaster 
     * @returns {Object} Triage classification counts and bed deficit
     */
    classifyCasualties(disaster) {
      if (!disaster) return null;

      const estimatedInjuries = Math.round((disaster.metrics.casualties || 20) * 8.5);

      // Typical MCI Triage Percentages:
      // Red: 15% | Yellow: 25% | Green: 50% | Black: 10%
      const redCount = Math.round(estimatedInjuries * 0.15);
      const yellowCount = Math.round(estimatedInjuries * 0.25);
      const greenCount = Math.round(estimatedInjuries * 0.50);
      const blackCount = Math.round(estimatedInjuries * 0.10);

      // Total available ICU beds across regional trauma centers
      const totalAvailableIcu = this.hospitals.reduce((acc, h) => acc + h.icuBedsAvailable, 0);
      const bedDeficit = Math.max(0, redCount - totalAvailableIcu);

      return {
        estimatedInjuredTotal: estimatedInjuries,
        triageBreakdown: {
          immediateRed: redCount,
          delayedYellow: yellowCount,
          minorGreen: greenCount,
          expectantBlack: blackCount
        },
        traumaCapacity: {
          totalAvailableIcu,
          criticalBedDeficit: bedDeficit,
          saturationPct: Math.round(((redCount) / Math.max(1, totalAvailableIcu)) * 100)
        }
      };
    }

    /**
     * Dispatch Air Ambulance MEDEVAC Helicopter
     * @param {string} extractionPointName 
     * @param {number} lat 
     * @param {number} lon 
     * @param {string} targetHospitalId 
     * @returns {Object} Medevac flight mission
     */
    dispatchMedevac(extractionPointName, lat, lon, targetHospitalId = 'HOSP-LA-FE') {
      const hospital = this.hospitals.find(h => h.id === targetHospitalId) || this.hospitals[0];

      // Distance and flight time
      const distKm = window.orbitPropagator ? window.orbitPropagator.getDistanceKm(lat, lon, hospital.lat, hospital.lon) : 12.0;
      const flightMinutes = Math.round((distKm / 240.0) * 60 + 4); // 240 km/h helo cruise speed + 4m landing approach

      const medevacMission = {
        missionId: `MEDEVAC-${Math.floor(100 + Math.random() * 900)}`,
        callsign: 'HELO-MED-2 (AgustaWestland AW139)',
        extractionZone: extractionPointName,
        targetHospital: hospital.name,
        distanceKm: parseFloat(distKm.toFixed(1)),
        flightTimeMinutes: flightMinutes,
        patientStatus: 'RED PRIORITY // CRITICAL MULTIPLE TRAUMA',
        status: 'EN_ROUTE_TO_LZ',
        dispatchedAt: new Date().toISOString()
      };

      this.activeMedevacs.push(medevacMission);

      // Decrement hospital ICU bed
      if (hospital.icuBedsAvailable > 0) {
        hospital.icuBedsAvailable--;
      }

      if (window.soundEngine) {
        window.soundEngine.playRadioStatic();
      }

      if (window.telemetryFeed) {
        window.telemetryFeed.logEvent(
          'MEDEVAC',
          `AIR AMBULANCE DISPATCHED [${medevacMission.missionId}]: Inbound to ${hospital.name} (Flight Time: ${flightMinutes}m)`,
          'alert'
        );
      }

      return medevacMission;
    }

    getHospitals() {
      return this.hospitals;
    }
  }

  window.casualtyTriage = new CasualtyTriageSystem();

})(window);
