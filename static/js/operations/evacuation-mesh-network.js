/**
 * ============================================================================
 * ASTRA-GEO // SATELLITE DISASTER INTELLIGENCE PLATFORM
 * EMERGENCY OFF-GRID LORA MESH NETWORK & CIVILIAN SOS LOCATOR
 * ============================================================================
 * Simulates decentralized tactical LoRa / BLE mesh relay topologies, multi-hop
 * packet forwarding, signal attenuation (RSSI/SNR), and civilian SOS emergency beacons.
 */

(function (window) {
  'use strict';

  // Civilian Emergency SOS Beacon Categories
  const SOS_CATEGORIES = {
    TRAPPED_COLLAPSE: { code: 'TRAPPED', priority: 1, label: 'Trapped in Structural Debris', color: '#ff3366' },
    WATER_RISING: { code: 'WATER_RISING', priority: 1, label: 'Water Level Rising / Rooftop Refuged', color: '#00f0ff' },
    MEDICAL_CRITICAL: { code: 'MEDICAL_CRITICAL', priority: 1, label: 'Severe Hemorrhage / Acute Cardiac', color: '#ffaa00' },
    STRANDED_SAFE: { code: 'STRANDED_SAFE', priority: 3, label: 'Sheltered / Awaiting Extraction', color: '#00ff88' }
  };

  class EvacuationMeshNetworkEngine {
    constructor() {
      this.meshNodes = [];
      this.activeDistressPings = [];
      this.initDefaultMeshNetwork();
    }

    initDefaultMeshNetwork() {
      // 6 Tactical LoRa Mesh Gateway & Relay Nodes
      this.meshNodes = [
        { id: 'NODE-GW-1', name: 'Command HQ Tactical Satellite Gateway', lat: 39.469, lon: -0.376, type: 'GATEWAY', batteryPct: 99, hopsToEoc: 0, connectedClients: 42 },
        { id: 'NODE-RELAY-2', name: 'Paiporta Church Belltower Relay', lat: 39.428, lon: -0.418, type: 'RELAY', batteryPct: 84, hopsToEoc: 1, connectedClients: 68 },
        { id: 'NODE-RELAY-3', name: 'Sedaví Highway Overpass Solar Repeater', lat: 39.412, lon: -0.385, type: 'RELAY', batteryPct: 91, hopsToEoc: 1, connectedClients: 55 },
        { id: 'NODE-RELAY-4', name: 'Alfafar Rooftop Ad-Hoc Node', lat: 39.432, lon: -0.392, type: 'RELAY', batteryPct: 76, hopsToEoc: 2, connectedClients: 39 },
        { id: 'NODE-RELAY-5', name: 'Torrent High Ground Repeater', lat: 39.434, lon: -0.468, type: 'RELAY', batteryPct: 88, hopsToEoc: 1, connectedClients: 31 },
        { id: 'NODE-AIR-6', name: 'Tethered Aerostat Comms Balloon', lat: 39.445, lon: -0.410, type: 'AIRBORNE_RELAY', batteryPct: 95, hopsToEoc: 0, connectedClients: 180 }
      ];

      // Simulated Civilian Distress Beacons
      this.activeDistressPings = [
        {
          beaconId: 'SOS-9421',
          lat: 39.4241,
          lon: -0.4152,
          category: SOS_CATEGORIES.TRAPPED_COLLAPSE,
          occupantsCount: 4,
          timestamp: new Date(Date.now() - 1800000).toISOString(),
          rssiDb: -86,
          snrDb: 6.5,
          hops: 2,
          relayNodeId: 'NODE-RELAY-2',
          message: 'Family of 4 trapped on 2nd floor, basement completely flooded. Power cut.'
        },
        {
          beaconId: 'SOS-9422',
          lat: 39.4085,
          lon: -0.3821,
          category: SOS_CATEGORIES.WATER_RISING,
          occupantsCount: 2,
          timestamp: new Date(Date.now() - 3600000).toISOString(),
          rssiDb: -92,
          snrDb: 4.2,
          hops: 1,
          relayNodeId: 'NODE-RELAY-3',
          message: 'On roof of commercial warehouse. Current is fast. Water 1m below roof edge.'
        },
        {
          beaconId: 'SOS-9423',
          lat: 39.4312,
          lon: -0.3940,
          category: SOS_CATEGORIES.MEDICAL_CRITICAL,
          occupantsCount: 1,
          timestamp: new Date(Date.now() - 900000).toISOString(),
          rssiDb: -78,
          snrDb: 8.9,
          hops: 1,
          relayNodeId: 'NODE-RELAY-4',
          message: 'Elderly patient with severe hypothermia and oxygen concentrator battery depleted.'
        }
      ];
    }

    /**
     * Compute Path Loss & RSSI between transmitter and receiver (Log-Distance Path Loss Model)
     * PL(d) = PL(d0) + 10 * n * log10(d / d0) + X_sigma
     * @param {number} distKm 
     * @param {number} freqMhz - E.g. 868 MHz or 915 MHz
     * @returns {number} RSSI in dBm
     */
    calculatePathLossRSSI(distKm = 2.5, freqMhz = 868.0) {
      const txPowerDbm = 14.0; // Standard 25mW LoRa EIRP
      const pathLossExp = 3.2; // Urban / flood disaster environment
      const distM = Math.max(10, distKm * 1000);

      // Free space path loss at 1 meter: FSPL = 20*log10(d) + 20*log10(f) - 27.55
      const pl0 = 20 * Math.log10(1) + 20 * Math.log10(freqMhz) - 27.55;
      const totalLoss = pl0 + 10 * pathLossExp * Math.log10(distM);
      const rssi = txPowerDbm - totalLoss;

      return Math.round(Math.max(-128, Math.min(-40, rssi)));
    }

    /**
     * Submit New Civilian Distress SOS Beacon
     */
    broadcastSOS(lat, lon, categoryKey = 'WATER_RISING', occupants = 1, message = 'Urgent assistance requested') {
      const cat = SOS_CATEGORIES[categoryKey] || SOS_CATEGORIES.WATER_RISING;

      // Find nearest mesh relay node
      let nearestNode = this.meshNodes[0];
      let minDist = Infinity;
      this.meshNodes.forEach(node => {
        const d = window.orbitPropagator ? window.orbitPropagator.getDistanceKm(lat, lon, node.lat, node.lon) : 3.0;
        if (d < minDist) {
          minDist = d;
          nearestNode = node;
        }
      });

      const rssi = this.calculatePathLossRSSI(minDist);

      const newBeacon = {
        beaconId: `SOS-${Math.floor(1000 + Math.random() * 9000)}`,
        lat,
        lon,
        category: cat,
        occupantsCount: occupants,
        timestamp: new Date().toISOString(),
        rssiDb: rssi,
        snrDb: 7.2,
        hops: nearestNode.hopsToEoc + 1,
        relayNodeId: nearestNode.id,
        message
      };

      this.activeDistressPings.unshift(newBeacon);

      if (window.soundEngine) {
        window.soundEngine.playEmergencyAlarm();
      }

      if (window.telemetryFeed) {
        window.telemetryFeed.logEvent(
          'LORA_MESH',
          `DISTRESS BEACON RECEIVED [${newBeacon.beaconId}]: ${cat.label} at (${lat.toFixed(3)}, ${lon.toFixed(3)}) via ${nearestNode.name}`,
          'alert'
        );
      }

      return newBeacon;
    }

    getActiveDistressPings() {
      return this.activeDistressPings;
    }

    getMeshNodes() {
      return this.meshNodes;
    }
  }

  window.evacuationMeshNetwork = new EvacuationMeshNetworkEngine();

})(window);
