/**
 * ============================================================================
 * ASTRA-GEO // SATELLITE DISASTER INTELLIGENCE PLATFORM
 * DENSITY-BASED SPATIAL CLUSTERING (DBSCAN) & RESCUE SECTOR ENGINE
 * ============================================================================
 * Implements geodetic Haversine DBSCAN clustering to partition thousands of
 * raw damage pings and civilian SOS distress calls into prioritized tactical
 * search-and-rescue sectors with convex hull bounds and urgency scoring.
 */

(function (window) {
  'use strict';

  class SpatialClusteringEngine {
    constructor() {
      this.clusters = [];
      this.noise = [];
    }

    /**
     * Run DBSCAN Algorithm on Geospatial Point Dataset
     * @param {Array<Object>} points - Array of { id, lat, lon, weight, category }
     * @param {number} epsKm - Epsilon neighborhood radius in km (default 1.2 km)
     * @param {number} minPts - Minimum points to form a dense core (default 3)
     * @returns {Array<Object>} Partitioned clusters
     */
    runDBSCAN(points, epsKm = 1.2, minPts = 3) {
      if (!points || points.length === 0) return [];

      const visited = new Set();
      const clustered = new Set();
      const clusters = [];
      const noise = [];

      const getNeighbors = (p) => {
        const neighbors = [];
        for (const other of points) {
          if (p === other) continue;
          const dist = window.orbitPropagator ? window.orbitPropagator.getDistanceKm(p.lat, p.lon, other.lat, other.lon) : 0.5;
          if (dist <= epsKm) {
            neighbors.push(other);
          }
        }
        return neighbors;
      };

      for (const p of points) {
        if (visited.has(p)) continue;
        visited.add(p);

        const neighbors = getNeighbors(p);

        if (neighbors.length < minPts - 1) {
          noise.push(p);
        } else {
          // New Cluster
          const currentCluster = [p];
          clustered.add(p);

          const queue = [...neighbors];
          while (queue.length > 0) {
            const q = queue.shift();
            if (!visited.has(q)) {
              visited.add(q);
              const qNeighbors = getNeighbors(q);
              if (qNeighbors.length >= minPts - 1) {
                queue.push(...qNeighbors);
              }
            }
            if (!clustered.has(q)) {
              currentCluster.push(q);
              clustered.add(q);
            }
          }

          clusters.push(currentCluster);
        }
      }

      this.noise = noise;

      // Calculate centroid, convex hull boundary, and urgency rating for each cluster
      this.clusters = clusters.map((clusterPts, idx) => {
        const totalWeight = clusterPts.reduce((acc, pt) => acc + (pt.weight || 1), 0);
        const centerLat = clusterPts.reduce((acc, pt) => acc + pt.lat, 0) / clusterPts.length;
        const centerLon = clusterPts.reduce((acc, pt) => acc + pt.lon, 0) / clusterPts.length;

        // Generate convex hull
        const ptCoords = clusterPts.map(pt => [pt.lat, pt.lon]);
        const hullCoords = window.spatialIntersection ? window.spatialIntersection.computeConvexHull(ptCoords) : ptCoords;

        // Urgency score (1 to 100)
        const urgencyScore = Math.min(100, Math.round(clusterPts.length * 12 + totalWeight * 4));

        const sectorNames = ['Sector Alpha', 'Sector Bravo', 'Sector Charlie', 'Sector Delta', 'Sector Echo'];
        const name = sectorNames[idx % sectorNames.length] || `Rescue Sector ${idx + 1}`;

        return {
          clusterId: `CLUSTER-${idx + 1}`,
          sectorName: `${name} (Priority ${idx + 1})`,
          pointCount: clusterPts.length,
          totalWeight,
          centerLat: parseFloat(centerLat.toFixed(4)),
          centerLon: parseFloat(centerLon.toFixed(4)),
          urgencyScore,
          points: clusterPts,
          hullPolygon: hullCoords,
          recommendedUnits: Math.max(1, Math.ceil(clusterPts.length / 4))
        };
      });

      // Sort clusters by urgency descending
      this.clusters.sort((a, b) => b.urgencyScore - a.urgencyScore);

      return this.clusters;
    }

    getClusters() {
      return this.clusters;
    }

    getNoise() {
      return this.noise;
    }
  }

  window.spatialClustering = new SpatialClusteringEngine();

})(window);
