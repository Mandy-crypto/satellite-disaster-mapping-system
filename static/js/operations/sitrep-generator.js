/**
 * ============================================================================
 * ASTRA-GEO // SATELLITE DISASTER INTELLIGENCE PLATFORM
 * UN-OCHA / FEMA STANDARD SITUATION REPORT (SITREP) GENERATOR
 * ============================================================================
 * Assembles official military & humanitarian situation reports, compiles
 * satellite intelligence, casualty statistics, operational tasks, and provides
 * instant Markdown, GeoJSON, and Print-to-PDF export pipelines.
 */

(function (window) {
  'use strict';

  class SitRepGenerator {
    constructor() {
      this.currentSitRepNumber = 4;
    }

    /**
     * Generate Situation Report Data Object
     * @param {Object} disaster 
     * @returns {Object} Compiled SitRep
     */
    generateSitRep(disaster) {
      if (!disaster) {
        disaster = window.disasterManager ? window.disasterManager.getSelected() : null;
      }
      if (!disaster) return null;

      const reportDate = new Date().toUTCString();
      const sitRepId = `SITREP-${disaster.id.toUpperCase()}-00${this.currentSitRepNumber}`;
      const damageStats = window.damageAssessment ? window.damageAssessment.assessDisasterDamage(disaster) : null;
      const lifelines = window.damageAssessment ? window.damageAssessment.getLifelineStatus(disaster) : [];

      return {
        sitRepId,
        disasterTitle: disaster.title,
        disasterType: disaster.type,
        location: disaster.location.name,
        country: disaster.location.country,
        severity: disaster.severity,
        generatedAt: reportDate,
        agency: 'ASTRA-GEO Crisis Command // UN-SPIDER & Copernicus EMS Relay',
        metrics: disaster.metrics,
        hazardTelemetry: disaster.hazardTelemetry,
        satellitePasses: disaster.satellitePasses,
        spectralIndices: disaster.spectralIndices,
        evacuationCorridors: disaster.evacuationCorridors,
        shelterLocations: disaster.shelterLocations,
        damageStats,
        lifelines,
        description: disaster.description
      };
    }

    /**
     * Render SitRep as Rich HTML Document
     */
    renderHTML(sitrep) {
      if (!sitrep) return '<p>No active situation report available.</p>';

      const passesRows = (sitrep.satellitePasses || []).map(p => `
        <tr>
          <td><strong>${p.satId.toUpperCase()}</strong></td>
          <td>${p.sensor}</td>
          <td>${p.passTime}</td>
          <td>${p.mode}</td>
        </tr>
      `).join('');

      const corridorsRows = (sitrep.evacuationCorridors || []).map(c => `
        <tr>
          <td><strong>${c.name}</strong></td>
          <td><span class="badge-${c.status.includes('IMPASSABLE') ? 'red' : 'emerald'}">${c.status}</span></td>
          <td>${c.impassableLengthKm} km</td>
        </tr>
      `).join('');

      const sheltersRows = (sitrep.shelterLocations || []).map(s => `
        <tr>
          <td><strong>${s.name}</strong></td>
          <td>${s.capacity.toLocaleString()}</td>
          <td>${s.occupancy.toLocaleString()} (${Math.round((s.occupancy / s.capacity) * 100)}%)</td>
        </tr>
      `).join('');

      return `
        <div class="sitrep-document-view">
          <div class="sitrep-doc-header">
            <div class="sitrep-doc-title">
              <h2>${sitrep.disasterTitle}</h2>
              <p>DOC ID: ${sitrep.sitRepId} | DATE: ${sitrep.generatedAt}</p>
              <p style="color: var(--accent-cyan); font-weight:600;">ISSUING BODY: ${sitrep.agency}</p>
            </div>
            <div style="text-align: right;">
              <span class="badge-red" style="font-size:0.85rem; padding:4px 10px;">${sitrep.severity}</span>
            </div>
          </div>

          <div class="sitrep-doc-section">
            <h3>1. Executive Summary & Context</h3>
            <p>${sitrep.description}</p>
            <table class="sitrep-stat-table" style="margin-top:10px;">
              <thead>
                <tr>
                  <th>Affected Population</th>
                  <th>Casualties</th>
                  <th>Missing</th>
                  <th>Estimated Direct Damage</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><strong>${(sitrep.metrics.affectedPopulation || 0).toLocaleString()}</strong></td>
                  <td style="color:var(--accent-crimson);"><strong>${sitrep.metrics.casualties || 0}</strong></td>
                  <td style="color:var(--accent-amber);"><strong>${sitrep.metrics.missing || 0}</strong></td>
                  <td><strong>$${sitrep.metrics.estDamageUSD || 'N/A'}</strong></td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="sitrep-doc-section">
            <h3>2. Earth Observation (EO) Satellite Acquisitions</h3>
            <table class="sitrep-stat-table">
              <thead>
                <tr>
                  <th>Spacecraft</th>
                  <th>Payload Sensor</th>
                  <th>Acquisition Time (UTC)</th>
                  <th>Operational Product Mode</th>
                </tr>
              </thead>
              <tbody>
                ${passesRows}
              </tbody>
            </table>
          </div>

          <div class="sitrep-doc-section">
            <h3>3. Evacuation Corridors & Transport Lifelines</h3>
            <table class="sitrep-stat-table">
              <thead>
                <tr>
                  <th>Route Identification</th>
                  <th>Operational Status</th>
                  <th>Impassable Extent</th>
                </tr>
              </thead>
              <tbody>
                ${corridorsRows}
              </tbody>
            </table>
          </div>

          <div class="sitrep-doc-section">
            <h3>4. Emergency Shelter Staging Hubs</h3>
            <table class="sitrep-stat-table">
              <thead>
                <tr>
                  <th>Shelter Facility</th>
                  <th>Rated Bed Capacity</th>
                  <th>Active Occupancy</th>
                </tr>
              </thead>
              <tbody>
                ${sheltersRows}
              </tbody>
            </table>
          </div>

          <div class="sitrep-doc-section">
            <h3>5. Immediate Operational Priorities (Next 24 Hours)</h3>
            <ul style="padding-left: 20px; font-family: var(--font-mono); font-size: 0.74rem; color: var(--text-primary); line-height: 1.8;">
              <li>Execute urgent S-Band tasking uplink to WorldView-3 for sub-meter optical assessment of isolated pockets.</li>
              <li>Deploy high-clearance amphibious rescue convoys to congested bottlenecks along CV-400 / V-31 corridors.</li>
              <li>Deliver mobile satellite communication terminals (Starlink/Iridium) to restore emergency hospital telemetry.</li>
              <li>Distribute potable water supplies and chlorination kits to prevent secondary waterborne contamination.</li>
            </ul>
          </div>
        </div>
      `;
    }

    /**
     * Export SitRep to Markdown String
     */
    toMarkdown(sitrep) {
      if (!sitrep) return '';
      return `# SITUATION REPORT: ${sitrep.disasterTitle}
**DOCUMENT ID:** ${sitrep.sitRepId}  
**DATE ISSUED:** ${sitrep.generatedAt}  
**CLASSIFICATION:** ${sitrep.severity}  
**ISSUING COMMAND:** ${sitrep.agency}  

---

## 1. EXECUTIVE SUMMARY
${sitrep.description}

- **Affected Population:** ${(sitrep.metrics.affectedPopulation || 0).toLocaleString()}
- **Casualties Reported:** ${sitrep.metrics.casualties || 0}
- **Missing Persons:** ${sitrep.metrics.missing || 0}
- **Estimated Damage:** $${sitrep.metrics.estDamageUSD || 'N/A'}

## 2. SATELLITE ASSET TASKINGS
${(sitrep.satellitePasses || []).map(p => `- **${p.satId.toUpperCase()}** (${p.sensor}) | ${p.passTime} | ${p.mode}`).join('\n')}

## 3. EVACUATION CORRIDORS
${(sitrep.evacuationCorridors || []).map(c => `- **${c.name}**: ${c.status} (${c.impassableLengthKm} km impassable)`).join('\n')}

## 4. SHELTER CAPACITIES
${(sitrep.shelterLocations || []).map(s => `- **${s.name}**: ${s.occupancy} / ${s.capacity} occupied`).join('\n')}
`;
    }

    /**
     * Export All Disaster Features to GeoJSON Feature Collection
     */
    toGeoJSON(disaster) {
      if (!disaster) return null;

      const features = [
        {
          type: 'Feature',
          geometry: {
            type: 'Point',
            coordinates: [disaster.location.lon, disaster.location.lat]
          },
          properties: {
            name: disaster.title,
            type: disaster.type,
            severity: disaster.severity,
            metrics: disaster.metrics
          }
        }
      ];

      (disaster.shelterLocations || []).forEach(s => {
        features.push({
          type: 'Feature',
          geometry: {
            type: 'Point',
            coordinates: [s.lon, s.lat]
          },
          properties: {
            name: s.name,
            type: 'Shelter',
            capacity: s.capacity,
            occupancy: s.occupancy
          }
        });
      });

      return {
        type: 'FeatureCollection',
        features
      };
    }
  }

  window.sitRepGenerator = new SitRepGenerator();

})(window);
