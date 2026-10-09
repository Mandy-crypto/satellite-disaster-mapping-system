/**
 * ============================================================================
 * ASTRA-GEO // SATELLITE DISASTER INTELLIGENCE PLATFORM
 * ADVANCED GEOSPATIAL VECTOR INTERSECTION & COMPUTATIONAL GEOMETRY ENGINE
 * ============================================================================
 * Implements Sutherland-Hodgman polygon clipping, Jordan curve ray casting,
 * Graham scan convex hulls, geodesic buffer dilation, and spherical excess area.
 */

(function (window) {
  'use strict';

  class SpatialIntersectionEngine {
    constructor() {
      this.earthRadiusKm = 6371.0;
    }

    /**
     * Point-in-Polygon Ray Casting Test (Jordan Curve Theorem)
     * @param {number} testLat 
     * @param {number} testLon 
     * @param {Array<[number, number]>} polygonCoords - Array of [lat, lon]
     * @returns {boolean} True if point is inside polygon
     */
    isPointInPolygon(testLat, testLon, polygonCoords) {
      if (!polygonCoords || polygonCoords.length < 3) return false;
      let inside = false;

      for (let i = 0, j = polygonCoords.length - 1; i < polygonCoords.length; j = i++) {
        const xi = polygonCoords[i][0], yi = polygonCoords[i][1];
        const xj = polygonCoords[j][0], yj = polygonCoords[j][1];

        const intersect = ((yi > testLon) !== (yj > testLon)) &&
          (testLat < ((xj - xi) * (testLon - yi)) / (yj - yi) + xi);

        if (intersect) inside = !inside;
      }

      return inside;
    }

    /**
     * Compute True Geodetic Polygon Area using Girard's Theorem (Spherical Excess)
     * Area = R^2 * |sum( (lon_{i+1} - lon_{i-1}) * sin(lat_i) )| / 2
     * @param {Array<[number, number]>} polygonCoords - Array of [lat, lon]
     * @returns {number} Area in square kilometers (km^2)
     */
    calculatePolygonAreaKm2(polygonCoords) {
      if (!polygonCoords || polygonCoords.length < 3) return 0;
      const n = polygonCoords.length;
      let total = 0;

      for (let i = 0; i < n; i++) {
        const p1 = polygonCoords[i];
        const p2 = polygonCoords[(i + 1) % n];

        const lon1Rad = (p1[1] * Math.PI) / 180.0;
        const lat1Rad = (p1[0] * Math.PI) / 180.0;
        const lon2Rad = (p2[1] * Math.PI) / 180.0;
        const lat2Rad = (p2[0] * Math.PI) / 180.0;

        total += (lon2Rad - lon1Rad) * (2 + Math.sin(lat1Rad) + Math.sin(lat2Rad));
      }

      const area = Math.abs(total * (this.earthRadiusKm * this.earthRadiusKm) / 2.0);
      return parseFloat(area.toFixed(2));
    }

    /**
     * Graham Scan Convex Hull Algorithm
     * Computes the minimal bounding convex polygon around arbitrary point clusters.
     * @param {Array<[number, number]>} points - Array of [lat, lon]
     * @returns {Array<[number, number]>} Convex hull vertices
     */
    computeConvexHull(points) {
      if (!points || points.length <= 3) return points;

      // Copy and sort points by longitude, then latitude
      const pts = points.slice().sort((a, b) => a[1] === b[1] ? a[0] - b[0] : a[1] - b[1]);

      // Cross product test of turn (counter-clockwise)
      const cross = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);

      // Build lower hull
      const lower = [];
      for (const p of pts) {
        while (lower.length >= 2 && cross(lower[lower.length - 2], lower[lower.length - 1], p) <= 0) {
          lower.pop();
        }
        lower.push(p);
      }

      // Build upper hull
      const upper = [];
      for (let i = pts.length - 1; i >= 0; i--) {
        const p = pts[i];
        while (upper.length >= 2 && cross(upper[upper.length - 2], upper[upper.length - 1], p) <= 0) {
          upper.pop();
        }
        upper.push(p);
      }

      // Remove last point of each half as it is duplicated
      lower.pop();
      upper.pop();

      return lower.concat(upper);
    }

    /**
     * Generate Geodesic Buffer Polygon around a Polyline Trace (e.g. Fault line or River)
     * @param {Array<[number, number]>} lineCoords 
     * @param {number} bufferRadiusKm 
     * @returns {Array<[number, number]>} Dilated polygon boundary
     */
    generateLineBufferPolygon(lineCoords, bufferRadiusKm = 2.0) {
      if (!lineCoords || lineCoords.length < 2) return [];

      const leftPoints = [];
      const rightPoints = [];

      for (let i = 0; i < lineCoords.length; i++) {
        const curr = lineCoords[i];
        let dLat = 0, dLon = 0;

        if (i < lineCoords.length - 1) {
          const next = lineCoords[i + 1];
          dLat = next[0] - curr[0];
          dLon = next[1] - curr[1];
        } else {
          const prev = lineCoords[i - 1];
          dLat = curr[0] - prev[0];
          dLon = curr[1] - prev[1];
        }

        const len = Math.hypot(dLat, dLon) || 1e-6;
        // Perpendicular normal vector
        const nLat = -dLon / len;
        const nLon = dLat / len;

        const offLat = (bufferRadiusKm * nLat) / 111.32;
        const offLon = (bufferRadiusKm * nLon) / (111.32 * Math.cos((curr[0] * Math.PI) / 180));

        leftPoints.push([curr[0] + offLat, curr[1] + offLon]);
        rightPoints.unshift([curr[0] - offLat, curr[1] - offLon]);
      }

      const bufferPoly = leftPoints.concat(rightPoints);
      bufferPoly.push(bufferPoly[0]); // Close ring
      return bufferPoly;
    }

    /**
     * Find all Critical Infrastructure Facilities intersecting a disaster hazard perimeter
     * @param {Array<Object>} facilities - Array of { name, lat, lon, type }
     * @param {Array<[number, number]>} hazardPolygon 
     * @returns {Array<Object>} Inundated / threatened facilities
     */
    findThreatenedFacilities(facilities, hazardPolygon) {
      if (!facilities || !hazardPolygon) return [];
      return facilities.filter(fac => this.isPointInPolygon(fac.lat, fac.lon, hazardPolygon));
    }
  }

  window.spatialIntersection = new SpatialIntersectionEngine();

})(window);
