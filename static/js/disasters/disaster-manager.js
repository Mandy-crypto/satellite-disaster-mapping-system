/**
 * ============================================================================
 * ASTRA-GEO // SATELLITE DISASTER INTELLIGENCE PLATFORM
 * MASTER DISASTER STATE & GEOSPATIAL QUERY COORDINATOR
 * ============================================================================
 * Coordinates planetary disaster state, active hazard selection, filtering,
 * cross-module event dispatching, and critical crisis analytics.
 */

(function (window) {
  'use strict';

  class DisasterManager {
    constructor() {
      this.selectedDisaster = null;
      this.filterType = 'ALL';
      this.searchQuery = '';
      this.subscribers = [];
    }

    init() {
      const all = this.getAll();
      if (all && all.length > 0) {
        this.selectDisaster(all[0].id, false);
      }
    }

    getAll() {
      return window.DisasterCatalog ? window.DisasterCatalog.getAll() : [];
    }

    getFilteredList() {
      if (!window.DisasterCatalog) return [];
      let list = window.DisasterCatalog.filterByType(this.filterType);
      if (this.searchQuery.trim().length > 0) {
        const q = this.searchQuery.toLowerCase();
        list = list.filter(d => 
          d.title.toLowerCase().includes(q) ||
          d.type.toLowerCase().includes(q) ||
          d.location.name.toLowerCase().includes(q) ||
          d.location.country.toLowerCase().includes(q)
        );
      }
      return list;
    }

    setFilterType(type) {
      this.filterType = type;
      this.notifySubscribers('FILTER_CHANGED', { filterType: type });
    }

    setSearchQuery(q) {
      this.searchQuery = q;
      this.notifySubscribers('SEARCH_CHANGED', { query: q });
    }

    selectDisaster(id, triggerAudio = true) {
      if (!window.DisasterCatalog) return;
      const disaster = window.DisasterCatalog.getById(id);
      if (!disaster) return;

      this.selectedDisaster = disaster;

      if (triggerAudio && window.soundEngine) {
        window.soundEngine.playTargetLock();
      }

      if (window.telemetryFeed) {
        window.telemetryFeed.logEvent(
          'CRISIS_C2',
          `TARGET LOCKED [${disaster.type.toUpperCase()}]: ${disaster.title} (${disaster.location.name})`,
          'alert'
        );
      }

      this.notifySubscribers('DISASTER_SELECTED', disaster);
      return disaster;
    }

    getSelected() {
      return this.selectedDisaster;
    }

    /**
     * Compute Global Impact Aggregates across active and monitored crisis events
     */
    getGlobalImpactSummary() {
      const all = this.getAll();
      let totalAffected = 0;
      let totalCasualties = 0;
      let totalInundatedSqKm = 0;
      let activeIncidentsCount = 0;

      all.forEach(d => {
        if (d.metrics) {
          totalAffected += (d.metrics.affectedPopulation || 0);
          totalCasualties += (d.metrics.casualties || 0);
          totalInundatedSqKm += (d.metrics.inundatedAreaSqKm || 0);
        }
        if (!d.status.includes('HISTORICAL')) {
          activeIncidentsCount++;
        }
      });

      return {
        totalDisasters: all.length,
        activeIncidentsCount,
        totalAffected: totalAffected.toLocaleString(),
        totalCasualties: totalCasualties.toLocaleString(),
        totalInundatedSqKm: totalInundatedSqKm.toFixed(1)
      };
    }

    subscribe(callback) {
      if (typeof callback === 'function') {
        this.subscribers.push(callback);
      }
    }

    notifySubscribers(eventType, payload) {
      this.subscribers.forEach(cb => {
        try {
          cb(eventType, payload);
        } catch (e) {
          console.error('Error in disaster manager subscriber:', e);
        }
      });
    }
  }

  window.disasterManager = new DisasterManager();

})(window);
