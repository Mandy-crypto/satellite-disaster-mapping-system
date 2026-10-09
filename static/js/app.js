/**
 * ============================================================================
 * ASTRA-GEO // SATELLITE DISASTER INTELLIGENCE PLATFORM
 * MASTER APPLICATION ORCHESTRATOR & COCKPIT CONTROLLER
 * ============================================================================
 * Connects 3D Globe, 2D GIS, Orbital Mechanics, Multispectral Analysis,
 * Emergency Tasking, Damage Grading, Audio Synthesizer, and HUD Telemetry.
 */

(function (window) {
  'use strict';

  class AstraGeoApplication {
    constructor() {
      this.initialized = false;
    }

    init() {
      console.log('🚀 ASTRA-GEO System Initializing...');

      // 1. Initialize Subsystems
      if (window.soundEngine) window.soundEngine.init();
      if (window.telemetryFeed) window.telemetryFeed.init();
      if (window.hudOverlayManager) window.hudOverlayManager.init();
      if (window.globeEngine) window.globeEngine.init('globe-canvas-container');
      if (window.mapEngine) window.mapEngine.init('leaflet-map-container');
      if (window.spectralAnalysis) window.spectralAnalysis.init();
      if (window.timelineScrubber) window.timelineScrubber.init();
      if (window.disasterManager) window.disasterManager.init();

      // 2. Setup UI Controllers
      this.bindViewportModeSwitchers();
      this.bindTabNavigation();
      this.bindSearchAndFilters();
      this.bindModalControllers();
      this.bindAudioControls();
      this.bindKeyboardShortcuts();
      this.bindDisasterList();
      this.bindSatelliteFleetList();
      this.bindOperationsPanel();
      this.bindBottomDeckControls();

      this.initialized = true;
      console.log('✅ ASTRA-GEO Orbital Operations Platform Online');
    }

    /**
     * Viewport Layout Mode (Split-Screen, 3D Globe Only, 2D GIS Only, PIP)
     */
    bindViewportModeSwitchers() {
      const stage = document.querySelector('.viewport-stage');
      const modeButtons = document.querySelectorAll('.viewport-mode-btn');

      modeButtons.forEach(btn => {
        btn.addEventListener('click', () => {
          modeButtons.forEach(b => b.classList.remove('active'));
          btn.classList.add('active');

          const mode = btn.getAttribute('data-mode');
          if (stage) stage.setAttribute('data-mode', mode);

          if (window.soundEngine) window.soundEngine.playClick();

          // Trigger map and globe resize recalculation
          setTimeout(() => {
            if (window.globeEngine) window.globeEngine.handleResize();
            if (window.mapEngine && window.mapEngine.map) window.mapEngine.map.invalidateSize();
          }, 150);
        });
      });
    }

    /**
     * Tab Switchers for Left Sidebar, Right Sidebar, and Bottom Deck
     */
    bindTabNavigation() {
      // Left Sidebar Tabs
      const leftTabs = document.querySelectorAll('.tactical-sidebar-left .tactical-tab-btn');
      leftTabs.forEach(tab => {
        tab.addEventListener('click', () => {
          leftTabs.forEach(t => t.classList.remove('active'));
          tab.classList.add('active');

          const targetPaneId = tab.getAttribute('data-target');
          const panes = document.querySelectorAll('.tactical-sidebar-left .tab-pane');
          panes.forEach(p => p.classList.remove('active'));

          const target = document.getElementById(targetPaneId);
          if (target) target.classList.add('active');

          if (window.soundEngine) window.soundEngine.playClick();
        });
      });

      // Right Sidebar Tabs
      const rightTabs = document.querySelectorAll('.tactical-sidebar-right .tactical-tab-btn');
      rightTabs.forEach(tab => {
        tab.addEventListener('click', () => {
          rightTabs.forEach(t => t.classList.remove('active'));
          tab.classList.add('active');

          const targetPaneId = tab.getAttribute('data-target');
          const panes = document.querySelectorAll('.tactical-sidebar-right .tab-pane');
          panes.forEach(p => p.classList.remove('active'));

          const target = document.getElementById(targetPaneId);
          if (target) target.classList.add('active');

          if (window.soundEngine) window.soundEngine.playClick();
        });
      });

      // Bottom Deck Tabs
      const bottomTabs = document.querySelectorAll('.bottom-tab-btn');
      bottomTabs.forEach(tab => {
        tab.addEventListener('click', () => {
          bottomTabs.forEach(t => t.classList.remove('active'));
          tab.classList.add('active');

          const targetPaneId = tab.getAttribute('data-target');
          const panes = document.querySelectorAll('.bottom-panel');
          panes.forEach(p => p.classList.remove('active'));

          const target = document.getElementById(targetPaneId);
          if (target) target.classList.add('active');

          if (window.soundEngine) window.soundEngine.playClick();
        });
      });
    }

    /**
     * Search Input & Hazard Type Filter Pills
     */
    bindSearchAndFilters() {
      const searchInput = document.getElementById('search-disasters-input');
      if (searchInput && window.disasterManager) {
        searchInput.addEventListener('input', (e) => {
          window.disasterManager.setSearchQuery(e.target.value);
          this.renderDisasterCards();
        });
      }

      const filterPills = document.querySelectorAll('.filter-pill');
      filterPills.forEach(pill => {
        pill.addEventListener('click', () => {
          filterPills.forEach(p => p.classList.remove('active'));
          pill.classList.add('active');

          const filterType = pill.getAttribute('data-filter');
          if (window.disasterManager) {
            window.disasterManager.setFilterType(filterType);
            this.renderDisasterCards();
          }

          if (window.soundEngine) window.soundEngine.playClick();
        });
      });
    }

    /**
     * Populate Disaster Cards List in Left Sidebar
     */
    bindDisasterList() {
      this.renderDisasterCards();

      // Subscribe to disaster selection to update active card highlight
      if (window.disasterManager) {
        window.disasterManager.subscribe((type, data) => {
          if (type === 'DISASTER_SELECTED') {
            this.updateActiveDisasterUI(data);
          }
        });
      }
    }

    renderDisasterCards() {
      const container = document.getElementById('disaster-cards-container');
      if (!container || !window.disasterManager) return;

      const list = window.disasterManager.getFilteredList();
      container.innerHTML = '';

      if (list.length === 0) {
        container.innerHTML = '<div style="color:var(--text-muted); padding:20px; text-align:center; font-family:monospace;">NO MATCHING DISASTER RECORDS FOUND</div>';
        return;
      }

      const active = window.disasterManager.getSelected();

      list.forEach(d => {
        const card = document.createElement('div');
        const isActive = active && active.id === d.id;
        card.className = `disaster-card ${d.category} ${isActive ? 'active' : ''}`;
        card.setAttribute('data-id', d.id);

        card.innerHTML = `
          <div class="disaster-card-header">
            <span class="disaster-name">${d.title}</span>
            <span class="disaster-badge badge-red">${d.severity.split(' ')[0]}</span>
          </div>
          <div class="disaster-card-location">
            📍 <span>${d.location.name}</span>
          </div>
          <div class="disaster-metrics-grid">
            <div class="metric-cell">
              <span class="cell-label">AFFECTED</span>
              <span class="cell-val">${(d.metrics.affectedPopulation || 0).toLocaleString()}</span>
            </div>
            <div class="metric-cell">
              <span class="cell-label">CASUALTIES</span>
              <span class="cell-val" style="color:var(--accent-crimson);">${d.metrics.casualties || 0}</span>
            </div>
            <div class="metric-cell">
              <span class="cell-label">EST DAMAGE</span>
              <span class="cell-val" style="color:var(--accent-amber);">$${d.metrics.estDamageUSD || 'N/A'}</span>
            </div>
          </div>
        `;

        card.addEventListener('click', () => {
          window.disasterManager.selectDisaster(d.id);
        });

        container.appendChild(card);
      });
    }

    updateActiveDisasterUI(disaster) {
      // Highlight card
      const cards = document.querySelectorAll('.disaster-card');
      cards.forEach(c => {
        if (c.getAttribute('data-id') === disaster.id) c.classList.add('active');
        else c.classList.remove('active');
      });

      // Update Header Telemetry Strip
      const targetElem = document.getElementById('header-active-target');
      if (targetElem) targetElem.textContent = disaster.title;

      const popElem = document.getElementById('header-affected-pop');
      if (popElem) popElem.textContent = (disaster.metrics.affectedPopulation || 0).toLocaleString();

      // Trigger CAP Alert banner
      if (window.telemetryFeed) {
        window.telemetryFeed.triggerCapAlert(`Active Crisis Event: ${disaster.title} [${disaster.severity}]`, disaster.severity.includes('CAT 5') ? 'FLASH EMERGENCY' : 'WARNING');
      }

      // Refresh Damage Analytics in Right Sidebar
      this.renderDamageAnalytics(disaster);
    }

    /**
     * Populate Satellite Fleet Catalog List in Left Sidebar
     */
    bindSatelliteFleetList() {
      const container = document.getElementById('satellite-fleet-container');
      if (!container || !window.SatelliteCatalog) return;

      const sats = window.SatelliteCatalog.satellites;
      container.innerHTML = '';

      sats.forEach(sat => {
        const card = document.createElement('div');
        card.className = 'satellite-card';
        card.setAttribute('data-id', sat.id);

        card.innerHTML = `
          <div class="sat-header-row">
            <div class="sat-title-group">
              <div class="sat-icon-box" style="border-color:${sat.color}; color:${sat.color};">🛰️</div>
              <div>
                <div class="sat-name-txt">${sat.name}</div>
                <div style="font-size:0.65rem; color:var(--text-muted); font-family:var(--font-mono);">${sat.agency}</div>
              </div>
            </div>
            <span class="badge-emerald" style="font-size:0.62rem;">${sat.status}</span>
          </div>
          <div class="sat-spec-row">
            <div><span style="color:var(--text-muted);">ALT:</span> ${sat.altitudeKm} km</div>
            <div><span style="color:var(--text-muted);">RES:</span> ${sat.spatialResolutionM}m</div>
            <div><span style="color:var(--text-muted);">SWATH:</span> ${sat.swathWidthKm} km</div>
          </div>
        `;

        card.addEventListener('click', () => {
          document.querySelectorAll('.satellite-card').forEach(sc => sc.classList.remove('active'));
          card.classList.add('active');

          if (window.soundEngine) window.soundEngine.playSatTelemetryAcquired();
          if (window.telemetryFeed) {
            window.telemetryFeed.logEvent('FLEET', `Inspecting ${sat.name} (${sat.sensor})`, 'info');
          }
        });

        container.appendChild(card);
      });
    }

    /**
     * Populate Right Sidebar Operations & Damage Analytics Panels
     */
    bindOperationsPanel() {
      // 1. First Responders List
      const unitsContainer = document.getElementById('first-responders-container');
      if (unitsContainer && window.rescueDispatch) {
        const units = window.rescueDispatch.getAllUnits();
        unitsContainer.innerHTML = '';

        units.forEach(u => {
          const uCard = document.createElement('div');
          uCard.className = 'unit-asset-card';
          uCard.innerHTML = `
            <div class="unit-header">
              <span class="unit-callsign">🛡️ ${u.callsign}</span>
              <span class="badge-${u.status === 'ON_SCENE' ? 'emerald' : 'cyan'}" style="font-size:0.62rem;">${u.status}</span>
            </div>
            <div style="font-size:0.72rem; color:var(--text-secondary); font-family:var(--font-mono);">
              ${u.assignedSector}
            </div>
            <div class="unit-progress-bar">
              <div class="unit-progress-fill" style="width:${u.fuelPct}%;"></div>
            </div>
            <div style="display:flex; justify-content:space-between; font-size:0.64rem; color:var(--text-muted); font-family:var(--font-mono); margin-top:2px;">
              <span>PERSONNEL: ${u.personnel}</span>
              <span>FUEL / BATTERY: ${u.fuelPct}%</span>
            </div>
          `;
          unitsContainer.appendChild(uCard);
        });
      }

      // Initial damage render with active disaster
      if (window.disasterManager) {
        const active = window.disasterManager.getSelected();
        if (active) this.renderDamageAnalytics(active);
      }
    }

    renderDamageAnalytics(disaster) {
      if (!disaster || !window.damageAssessment) return;

      const damageStats = window.damageAssessment.assessDisasterDamage(disaster);
      const chartContainer = document.getElementById('damage-chart-container');
      if (chartContainer && window.chartEngine) {
        window.chartEngine.renderDamageBarChart(chartContainer, damageStats);
      }

      // Lifelines
      const lifelinesContainer = document.getElementById('lifelines-status-container');
      if (lifelinesContainer) {
        const lifelines = window.damageAssessment.getLifelineStatus(disaster);
        lifelinesContainer.innerHTML = '';

        lifelines.forEach(l => {
          const item = document.createElement('div');
          item.style.cssText = 'background:var(--bg-secondary); border:1px solid var(--border-subtle); border-radius:3px; padding:8px; margin-bottom:6px; font-family:monospace; font-size:11px;';
          item.innerHTML = `
            <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
              <strong>${l.name}</strong>
              <span style="color:${l.operationalPct > 60 ? 'var(--accent-emerald)' : 'var(--accent-amber)'};">${l.operationalPct}% OPERATIONAL</span>
            </div>
            <div style="color:var(--text-secondary); font-size:10px;">${l.detail}</div>
          `;
          lifelinesContainer.appendChild(item);
        });
      }
    }

    /**
     * Bottom Deck Multispectral Buttons & Controls
     */
    bindBottomDeckControls() {
      const bandButtons = document.querySelectorAll('.band-mode-btn');
      bandButtons.forEach(btn => {
        btn.addEventListener('click', () => {
          bandButtons.forEach(b => b.classList.remove('active'));
          btn.classList.add('active');

          const mode = btn.getAttribute('data-mode');
          if (window.spectralAnalysis) {
            window.spectralAnalysis.setBandMode(mode);
          }
        });
      });

      // Timeline Buttons
      const playBtn = document.getElementById('btn-timeline-play');
      if (playBtn && window.timelineScrubber) {
        playBtn.addEventListener('click', () => window.timelineScrubber.togglePlayPause());
      }

      const stepBackBtn = document.getElementById('btn-timeline-step-back');
      if (stepBackBtn && window.timelineScrubber) {
        stepBackBtn.addEventListener('click', () => window.timelineScrubber.stepBackward());
      }

      const stepFwdBtn = document.getElementById('btn-timeline-step-fwd');
      if (stepFwdBtn && window.timelineScrubber) {
        stepFwdBtn.addEventListener('click', () => window.timelineScrubber.stepForward());
      }

      const speedSelect = document.getElementById('select-playback-speed');
      if (speedSelect && window.timelineScrubber) {
        speedSelect.addEventListener('change', (e) => {
          window.timelineScrubber.setSpeed(parseFloat(e.target.value));
        });
      }

      // Swipe comparison toggle
      const swipeToggle = document.getElementById('toggle-swipe-curtain');
      if (swipeToggle && window.spectralAnalysis) {
        swipeToggle.addEventListener('change', (e) => {
          window.spectralAnalysis.toggleSwipeLens(e.target.checked);
        });
      }
    }

    /**
     * Modals: Tasking, Drone Live Stream, Situation Report, Shortcuts
     */
    bindModalControllers() {
      // 1. Tasking Modal
      const openTaskingBtn = document.getElementById('btn-open-tasking');
      const taskingModal = document.getElementById('modal-tasking');
      const submitTaskBtn = document.getElementById('btn-submit-tasking');

      if (openTaskingBtn && taskingModal) {
        openTaskingBtn.addEventListener('click', () => {
          taskingModal.classList.add('open');
          if (window.soundEngine) window.soundEngine.playClick();
        });
      }

      if (submitTaskBtn && taskingModal && window.taskingSystem) {
        submitTaskBtn.addEventListener('click', () => {
          const satId = document.getElementById('tasking-select-sat').value;
          const priority = document.getElementById('tasking-select-priority').value;
          const activeDisaster = window.disasterManager ? window.disasterManager.getSelected() : null;

          window.taskingSystem.submitTask({
            satelliteId: satId,
            targetLat: activeDisaster ? activeDisaster.location.lat : 39.469,
            targetLon: activeDisaster ? activeDisaster.location.lon : -0.376,
            targetName: activeDisaster ? activeDisaster.title : 'Crisis Target',
            priority
          });

          taskingModal.classList.remove('open');
        });
      }

      // 2. Drone Modal
      const openDroneBtn = document.getElementById('btn-open-drone');
      const droneModal = document.getElementById('modal-drone');
      const droneCanvas = document.getElementById('drone-stream-canvas');

      if (openDroneBtn && droneModal) {
        openDroneBtn.addEventListener('click', () => {
          droneModal.classList.add('open');
          if (droneCanvas && window.rescueDispatch) {
            window.rescueDispatch.initDroneStream(droneCanvas);
          }
          if (window.soundEngine) window.soundEngine.playClick();
        });
      }

      // 3. SitRep Modal
      const openSitrepBtn = document.getElementById('btn-open-sitrep');
      const sitrepModal = document.getElementById('modal-sitrep');
      const sitrepDocContainer = document.getElementById('sitrep-modal-doc');

      if (openSitrepBtn && sitrepModal) {
        openSitrepBtn.addEventListener('click', () => {
          if (window.sitRepGenerator && sitrepDocContainer) {
            const report = window.sitRepGenerator.generateSitRep();
            sitrepDocContainer.innerHTML = window.sitRepGenerator.renderHTML(report);
          }
          sitrepModal.classList.add('open');
          if (window.soundEngine) window.soundEngine.playClick();
        });
      }

      // SitRep Export Markdown
      const exportMdBtn = document.getElementById('btn-export-sitrep-md');
      if (exportMdBtn && window.sitRepGenerator) {
        exportMdBtn.addEventListener('click', () => {
          const report = window.sitRepGenerator.generateSitRep();
          const md = window.sitRepGenerator.toMarkdown(report);
          const blob = new Blob([md], { type: 'text/markdown' });
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `SITREP_${Date.now()}.md`;
          a.click();
          URL.revokeObjectURL(url);
          if (window.soundEngine) window.soundEngine.playClick();
        });
      }

      // SitRep Print / PDF
      const printSitrepBtn = document.getElementById('btn-print-sitrep');
      if (printSitrepBtn) {
        printSitrepBtn.addEventListener('click', () => {
          window.print();
        });
      }

      // 4. Keyboard Shortcuts Modal
      const openShortcutsBtn = document.getElementById('btn-open-shortcuts');
      const shortcutsModal = document.getElementById('modal-shortcuts');
      if (openShortcutsBtn && shortcutsModal) {
        openShortcutsBtn.addEventListener('click', () => {
          shortcutsModal.classList.add('open');
          if (window.soundEngine) window.soundEngine.playClick();
        });
      }

      // Close all modals on [x] click or backdrop click
      document.querySelectorAll('.modal-close-btn').forEach(btn => {
        btn.addEventListener('click', () => {
          document.querySelectorAll('.tactical-modal-backdrop').forEach(m => m.classList.remove('open'));
          if (window.rescueDispatch) window.rescueDispatch.stopDroneStream();
          if (window.soundEngine) window.soundEngine.playClick();
        });
      });

      document.querySelectorAll('.tactical-modal-backdrop').forEach(modal => {
        modal.addEventListener('click', (e) => {
          if (e.target === modal) {
            modal.classList.remove('open');
            if (window.rescueDispatch) window.rescueDispatch.stopDroneStream();
          }
        });
      });
    }

    /**
     * Audio Volume & Mute Switchers
     */
    bindAudioControls() {
      const muteBtn = document.getElementById('btn-toggle-sound');
      if (muteBtn && window.soundEngine) {
        muteBtn.addEventListener('click', () => {
          const isMuted = window.soundEngine.toggleMute();
          muteBtn.innerHTML = isMuted ? '🔇 MUTED' : '🔊 AUDIO';
          muteBtn.classList.toggle('active', !isMuted);
        });
      }
    }

    /**
     * Keyboard Shortcuts (Space, 1-6, T, M, E, S, D, H)
     */
    bindKeyboardShortcuts() {
      window.addEventListener('keydown', (e) => {
        // Do not intercept if user is typing in an input
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') {
          return;
        }

        const key = e.key.toUpperCase();

        if (e.code === 'Space') {
          e.preventDefault();
          if (window.timelineScrubber) window.timelineScrubber.togglePlayPause();
        } else if (key >= '1' && key <= '8') {
          // Switch disaster preset
          const idx = parseInt(key, 10) - 1;
          const all = window.DisasterCatalog ? window.DisasterCatalog.getAll() : [];
          if (all[idx] && window.disasterManager) {
            window.disasterManager.selectDisaster(all[idx].id);
          }
        } else if (key === 'T') {
          // Urgent Tasking Modal
          const modal = document.getElementById('modal-tasking');
          if (modal) modal.classList.toggle('open');
        } else if (key === 'S') {
          // Situation Report Modal
          const modal = document.getElementById('modal-sitrep');
          if (modal) {
            if (!modal.classList.contains('open') && window.sitRepGenerator) {
              const docContainer = document.getElementById('sitrep-modal-doc');
              if (docContainer) docContainer.innerHTML = window.sitRepGenerator.renderHTML(window.sitRepGenerator.generateSitRep());
            }
            modal.classList.toggle('open');
          }
        } else if (key === 'D') {
          // Drone Modal
          const modal = document.getElementById('modal-drone');
          if (modal) {
            modal.classList.toggle('open');
            if (modal.classList.contains('open') && window.rescueDispatch) {
              window.rescueDispatch.initDroneStream(document.getElementById('drone-stream-canvas'));
            } else if (window.rescueDispatch) {
              window.rescueDispatch.stopDroneStream();
            }
          }
        } else if (key === 'H') {
          // Toggle CRT scanlines
          if (window.hudOverlayManager) window.hudOverlayManager.toggleScanlines();
        } else if (key === 'M') {
          // Toggle Mute
          if (window.soundEngine) {
            const isMuted = window.soundEngine.toggleMute();
            const muteBtn = document.getElementById('btn-toggle-sound');
            if (muteBtn) muteBtn.innerHTML = isMuted ? '🔇 MUTED' : '🔊 AUDIO';
          }
        } else if (key === 'ESCAPE') {
          // Close all open modals
          document.querySelectorAll('.tactical-modal-backdrop').forEach(m => m.classList.remove('open'));
          if (window.rescueDispatch) window.rescueDispatch.stopDroneStream();
        }
      });
    }
  }

  // Initialize Application on DOM Ready
  window.addEventListener('DOMContentLoaded', () => {
    window.app = new AstraGeoApplication();
    window.app.init();
  });

})(window);
