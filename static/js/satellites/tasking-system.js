/**
 * ============================================================================
 * ASTRA-GEO // SATELLITE DISASTER INTELLIGENCE PLATFORM
 * SATELLITE EMERGENCY TASKING & SLEW SCHEDULING SYSTEM
 * ============================================================================
 * Simulates urgent spacecraft attitude retasking, off-nadir slew computation,
 * downlink contact scheduling, payload energy budget, and International
 * Charter on Space and Major Disasters priority activations.
 */

(function (window) {
  'use strict';

  class SatelliteTaskingSystem {
    constructor() {
      this.taskQueue = [];
      this.activeSlews = new Map();
      this.initDefaultTasks();
    }

    initDefaultTasks() {
      this.taskQueue = [
        {
          taskId: 'TSK-2026-0941',
          satelliteId: 'worldview-3',
          satelliteName: 'WorldView-3',
          targetName: 'Valencia DANA Sector Sedaví',
          targetLat: 39.423,
          targetLon: -0.384,
          priority: 'FLASH (EMERGENCY)',
          status: 'COMPLETED',
          sensorMode: '0.31m High-Res Optical Panchromatic + VNIR',
          slewAngleDeg: 18.4,
          estimatedDataGb: 48.2,
          downlinkStation: 'Svalbard (SKS)',
          downlinkEta: 'Ingested (05:22 UTC)',
          submittedAt: new Date(Date.now() - 3600000 * 4).toISOString()
        },
        {
          taskId: 'TSK-2026-0942',
          satelliteId: 'iceye-x24',
          satelliteName: 'ICEYE-X24',
          targetName: 'Tampa Bay Storm Surge Coastline',
          targetLat: 27.810,
          targetLon: -82.632,
          priority: 'IMMEDIATE',
          status: 'IMAGING_IN_PROGRESS',
          sensorMode: 'Spotlight X-Band High Coherence SAR',
          slewAngleDeg: 24.1,
          estimatedDataGb: 22.8,
          downlinkStation: 'Inuvik (INU)',
          downlinkEta: 'In 34 mins',
          submittedAt: new Date(Date.now() - 3600000 * 1.5).toISOString()
        },
        {
          taskId: 'TSK-2026-0943',
          satelliteId: 'sentinel-1a',
          satelliteName: 'Sentinel-1A',
          targetName: 'Sierra Nevada Active Fire Front',
          targetLat: 39.816,
          targetLon: -121.432,
          priority: 'PRIORITY',
          status: 'SCHEDULED',
          sensorMode: 'Interferometric Wide Swath (IW) VV+VH',
          slewAngleDeg: 8.5,
          estimatedDataGb: 64.0,
          downlinkStation: 'Kiruna (KRN)',
          downlinkEta: 'In 2 hrs 15 mins',
          submittedAt: new Date(Date.now() - 1800000).toISOString()
        }
      ];
    }

    /**
     * Submit an urgent emergency tasking request
     */
    submitTask({ satelliteId, targetLat, targetLon, targetName, priority, sensorMode }) {
      const sat = window.SatelliteCatalog ? window.SatelliteCatalog.getById(satelliteId) : null;
      if (!sat) {
        throw new Error('Specified satellite not found in fleet catalog');
      }

      // Compute off-nadir slew angle needed:
      const satPos = window.orbitPropagator.propagate(sat, new Date());
      const distKm = window.orbitPropagator.getDistanceKm(satPos.lat, satPos.lon, targetLat, targetLon);
      const slewAngleDeg = Math.min(45.0, parseFloat(((Math.atan2(distKm, sat.altitudeKm) * 180) / Math.PI).toFixed(1)));

      // Estimate payload data volume
      const resolution = sat.spatialResolutionM || 10;
      const dataVolumeGb = parseFloat(((1000 / (resolution * resolution)) * 1.8 + 12).toFixed(1));

      // Calculate next downlink station window
      const groundStations = window.SatelliteCatalog ? window.SatelliteCatalog.groundStations : [];
      const primaryGs = groundStations[Math.floor(Math.random() * groundStations.length)] || { name: 'Svalbard (SKS)' };
      const minutesToDownlink = Math.floor(Math.random() * 45) + 15;

      const newTask = {
        taskId: `TSK-2026-${Math.floor(1000 + Math.random() * 9000)}`,
        satelliteId: sat.id,
        satelliteName: sat.name,
        targetName: targetName || `Lat: ${targetLat.toFixed(2)}, Lon: ${targetLon.toFixed(2)}`,
        targetLat,
        targetLon,
        priority: priority || 'FLASH (EMERGENCY)',
        status: 'COMMAND_UPLINKED',
        sensorMode: sensorMode || (sat.type.includes('SAR') ? 'Stripmap SAR High Coherence' : 'Multispectral 10m Nadir'),
        slewAngleDeg,
        estimatedDataGb: dataVolumeGb,
        downlinkStation: primaryGs.name,
        downlinkEta: `In ${minutesToDownlink} mins`,
        submittedAt: new Date().toISOString()
      };

      this.taskQueue.unshift(newTask);

      // Play tactical audio
      if (window.soundEngine) {
        window.soundEngine.playTaskingUplink();
      }

      // Post telemetry event
      if (window.telemetryFeed) {
        window.telemetryFeed.logEvent(
          'TASKING',
          `URGENT TASKING APPROVED [${newTask.taskId}]: ${sat.name} off-nadir slew ${slewAngleDeg}° over ${newTask.targetName}`,
          'alert'
        );
      }

      // Simulate status progression over time
      this.simulateTaskProgression(newTask);

      return newTask;
    }

    simulateTaskProgression(task) {
      setTimeout(() => {
        task.status = 'SPACECRAFT_SLEWING';
        if (window.telemetryFeed) {
          window.telemetryFeed.logEvent('ATTITUDE_CONTROL', `${task.satelliteName} reaction wheels torque slew to ${task.slewAngleDeg}° completed.`, 'info');
        }
      }, 5000);

      setTimeout(() => {
        task.status = 'IMAGING_IN_PROGRESS';
        if (window.soundEngine) window.soundEngine.playRadarPing();
        if (window.telemetryFeed) {
          window.telemetryFeed.logEvent('PAYLOAD', `${task.satelliteName} sensor active. Capturing ${task.sensorMode}...`, 'info');
        }
      }, 11000);

      setTimeout(() => {
        task.status = 'DOWNLINK_TRANSMITTING';
        if (window.telemetryFeed) {
          window.telemetryFeed.logEvent('COMMS', `${task.satelliteName} X-Band downlink transmitting ${task.estimatedDataGb} GB to ${task.downlinkStation}`, 'success');
        }
      }, 18000);

      setTimeout(() => {
        task.status = 'COMPLETED';
        if (window.soundEngine) window.soundEngine.playSatTelemetryAcquired();
        if (window.telemetryFeed) {
          window.telemetryFeed.logEvent('ARCHIVE', `Task ${task.taskId} complete. Orthorectified imagery published to GIS layers.`, 'success');
        }
      }, 25000);
    }

    getAllTasks() {
      return this.taskQueue;
    }

    getTaskById(taskId) {
      return this.taskQueue.find(t => t.taskId === taskId);
    }
  }

  window.taskingSystem = new SatelliteTaskingSystem();

})(window);
