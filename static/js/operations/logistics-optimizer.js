/**
 * ============================================================================
 * ASTRA-GEO // SATELLITE DISASTER INTELLIGENCE PLATFORM
 * HUMANITARIAN LOGISTICS & EMERGENCY SUPPLY CHAIN OPTIMIZER
 * ============================================================================
 * Computes Sphere Humanitarian Standard resource burn rates (water, MRE rations,
 * trauma surgical units, power generators), days of supply (DOS), and airlift sorties.
 */

(function (window) {
  'use strict';

  // Sphere Humanitarian Minimum Standards (2018 Edition)
  const SPHERE_STANDARDS = {
    WATER_LITERS_PER_PERSON_DAY: 15.0, // 3L drinking, 6L hygiene, 6L cooking
    MRE_RATIONS_PER_PERSON_DAY: 1.0,   // 2,100 kcal standard humanitarian ration pack
    SHELTER_TARPS_PER_FAMILY: 2.0,      // 4x5m heavy-duty reinforced tarpaulin
    HYGIENE_KITS_PER_FAMILY_MONTH: 1.0,
    PERSONS_PER_FAMILY: 4.5,
    DIESEL_LITERS_PER_GENERATOR_DAY: 180.0
  };

  class LogisticsOptimizer {
    constructor() {
      this.supplyInventory = {
        potableWaterLiters: 1200000,
        mreRationPacks: 450000,
        surgicalTraumaPacks: 1850,
        dieselGenerators50kw: 120,
        waterPurificationUnits: 45,
        starlinkEmergencyTerminals: 85
      };
    }

    /**
     * Calculate Daily Resource Burn Rate for an affected population
     * @param {number} affectedPopulation 
     * @param {number} displacedPct 
     * @returns {Object} Burn rate and logistics requirement
     */
    calculateBurnRate(affectedPopulation = 50000, displacedPct = 40) {
      const displacedPopulation = Math.round(affectedPopulation * (displacedPct / 100));
      const familiesCount = Math.round(displacedPopulation / SPHERE_STANDARDS.PERSONS_PER_FAMILY);

      // Daily burn metrics
      const dailyWaterLiters = displacedPopulation * SPHERE_STANDARDS.WATER_LITERS_PER_PERSON_DAY;
      const dailyMreRations = displacedPopulation * SPHERE_STANDARDS.MRE_RATIONS_PER_PERSON_DAY;
      const dailyMedicalTraumaCases = Math.round(displacedPopulation * 0.008); // 0.8% acute medical rate

      // Days of supply (DOS) remaining in strategic reserve
      const dosWater = parseFloat((this.supplyInventory.potableWaterLiters / Math.max(1, dailyWaterLiters)).toFixed(1));
      const dosMre = parseFloat((this.supplyInventory.mreRationPacks / Math.max(1, dailyMreRations)).toFixed(1));
      const dosMedical = parseFloat((this.supplyInventory.surgicalTraumaPacks / Math.max(1, dailyMedicalTraumaCases)).toFixed(1));

      return {
        displacedPopulation,
        familiesCount,
        dailyRequirements: {
          waterLiters: dailyWaterLiters,
          waterTons: parseFloat((dailyWaterLiters / 1000).toFixed(1)),
          mrePacks: dailyMreRations,
          traumaCases: dailyMedicalTraumaCases,
          shelterTarpsNeeded: Math.round(familiesCount * SPHERE_STANDARDS.SHELTER_TARPS_PER_FAMILY)
        },
        daysOfSupplyRemaining: {
          waterDays: dosWater,
          mreDays: dosMre,
          medicalDays: dosMedical,
          criticalShortage: dosWater < 3.0 || dosMre < 3.0
        }
      };
    }

    /**
     * Compute Airlift Cargo Sorties needed to bridge supply deficit
     * @param {number} requiredCargoTons 
     * @param {string} aircraftType - 'C130_HERCULES', 'CH47_CHINOOK', 'UH60_BLACKHAWK'
     * @returns {Object} Sortie schedule
     */
    scheduleAirliftSorties(requiredCargoTons = 120, aircraftType = 'C130_HERCULES') {
      const fleetSpecs = {
        C130_HERCULES: { name: 'Lockheed C-130H Hercules', payloadTons: 19.0, rangeKm: 3800, cruiseKmh: 540 },
        CH47_CHINOOK: { name: 'Boeing CH-47 Chinook Heavy Lift Helo', payloadTons: 10.5, rangeKm: 740, cruiseKmh: 280 },
        UH60_BLACKHAWK: { name: 'Sikorsky UH-60M Blackhawk', payloadTons: 4.1, rangeKm: 590, cruiseKmh: 270 }
      };

      const ac = fleetSpecs[aircraftType] || fleetSpecs.C130_HERCULES;
      const sortiesNeeded = Math.ceil(requiredCargoTons / ac.payloadTons);
      const totalFlightHoursEst = Math.round(sortiesNeeded * 2.8);

      return {
        aircraftName: ac.name,
        payloadPerFlightTons: ac.payloadTons,
        totalTonsToMove: requiredCargoTons,
        sortiesNeeded,
        totalFlightHoursEst,
        turnaroundMinutesPerSortie: 75
      };
    }
  }

  window.logisticsOptimizer = new LogisticsOptimizer();

})(window);
