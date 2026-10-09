/**
 * ============================================================================
 * ASTRA-GEO // SATELLITE DISASTER INTELLIGENCE PLATFORM
 * COCKPIT COMMAND PALETTE & TACTICAL CLI CONSOLE
 * ============================================================================
 * Aerospace terminal and command palette (Ctrl+K) supporting rapid manual
 * spacecraft retasking, spectral band switching, casualty triage runs,
 * dam breach hydrographs, and emergency mesh communication triggers.
 */

(function (window) {
  'use strict';

  class CockpitCommandPalette {
    constructor() {
      this.isOpen = false;
      this.commandHistory = [];
      this.historyIdx = -1;
      this.modalElem = null;
      this.inputElem = null;
      this.outputElem = null;
    }

    init() {
      this.createPaletteDOM();
      this.bindShortcuts();
    }

    createPaletteDOM() {
      const backdrop = document.createElement('div');
      backdrop.id = 'cockpit-command-palette-backdrop';
      backdrop.className = 'tactical-modal-backdrop';

      backdrop.innerHTML = `
        <div class="tactical-modal-dialog" style="max-width: 680px; height: 500px;">
          <div class="modal-header">
            <span class="modal-title">⌨️ COCKPIT COMMAND PALETTE // CLI C2</span>
            <button class="modal-close-btn" id="btn-close-cmd-palette">✕</button>
          </div>
          <div class="modal-body" style="padding: 12px; gap: 8px;">
            <div style="font-family: var(--font-mono); font-size: 0.72rem; color: var(--text-muted); background: var(--bg-secondary); padding: 8px; border-radius: 4px; border: 1px solid var(--border-subtle);">
              AVAILABLE COMMANDS: <code>target &lt;id&gt;</code>, <code>band &lt;mode&gt;</code>, <code>tour &lt;1|2|3&gt;</code>, <code>triage</code>, <code>sos</code>, <code>radar &lt;on|off&gt;</code>, <code>status</code>, <code>help</code>
            </div>
            <div id="cmd-palette-output" style="flex: 1; background: #020408; border: 1px solid var(--border-subtle); border-radius: 4px; padding: 10px; font-family: var(--font-mono); font-size: 0.72rem; overflow-y: auto; display: flex; flex-direction: column; gap: 4px;">
              <div style="color: var(--accent-emerald);">ASTRA-GEO TACTICAL SHELL v4.5 // TYPE 'help' FOR COMMAND LIST</div>
            </div>
            <div style="display: flex; gap: 8px; align-items: center;">
              <span style="font-family: var(--font-mono); color: var(--accent-cyan); font-weight: 700;">&gt;</span>
              <input type="text" id="cmd-palette-input" class="input-tactical" placeholder="Enter tactical command (e.g. tour 1, band ndwi, triage)..." autocomplete="off" />
            </div>
          </div>
        </div>
      `;

      document.body.appendChild(backdrop);
      this.modalElem = backdrop;
      this.inputElem = document.getElementById('cmd-palette-input');
      this.outputElem = document.getElementById('cmd-palette-output');

      document.getElementById('btn-close-cmd-palette').addEventListener('click', () => this.close());
      backdrop.addEventListener('click', (e) => {
        if (e.target === backdrop) this.close();
      });

      this.inputElem.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          const cmd = this.inputElem.value.trim();
          if (cmd) {
            this.execute(cmd);
            this.commandHistory.unshift(cmd);
            this.historyIdx = -1;
            this.inputElem.value = '';
          }
        } else if (e.key === 'ArrowUp') {
          if (this.historyIdx < this.commandHistory.length - 1) {
            this.historyIdx++;
            this.inputElem.value = this.commandHistory[this.historyIdx];
          }
        } else if (e.key === 'ArrowDown') {
          if (this.historyIdx > 0) {
            this.historyIdx--;
            this.inputElem.value = this.commandHistory[this.historyIdx];
          } else if (this.historyIdx === 0) {
            this.historyIdx = -1;
            this.inputElem.value = '';
          }
        }
      });
    }

    bindShortcuts() {
      window.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
          e.preventDefault();
          this.toggle();
        }
      });
    }

    open() {
      this.isOpen = true;
      if (this.modalElem) this.modalElem.classList.add('open');
      if (this.inputElem) {
        setTimeout(() => this.inputElem.focus(), 100);
      }
      if (window.soundEngine) window.soundEngine.playClick();
    }

    close() {
      this.isOpen = false;
      if (this.modalElem) this.modalElem.classList.remove('open');
      if (window.soundEngine) window.soundEngine.playClick();
    }

    toggle() {
      if (this.isOpen) this.close();
      else this.open();
    }

    printOutput(text, type = 'info') {
      if (!this.outputElem) return;
      const row = document.createElement('div');
      let color = '#f1f5f9';
      if (type === 'error') color = 'var(--accent-crimson)';
      if (type === 'success') color = 'var(--accent-emerald)';
      if (type === 'warn') color = 'var(--accent-amber)';
      if (type === 'cmd') color = 'var(--accent-cyan)';

      row.style.color = color;
      row.innerHTML = text;
      this.outputElem.appendChild(row);
      this.outputElem.scrollTop = this.outputElem.scrollHeight;
    }

    /**
     * Parse & Execute Command
     * @param {string} rawCommand 
     */
    execute(rawCommand) {
      this.printOutput(`&gt; ${rawCommand}`, 'cmd');
      const parts = rawCommand.trim().split(/\s+/);
      const action = parts[0].toLowerCase();
      const arg = parts[1] ? parts[1].toLowerCase() : '';

      switch (action) {
        case 'help':
          this.printOutput(`
            <strong>ASTRA-GEO COMMAND REFERENCE:</strong><br>
            • <code>tour &lt;1|2|3&gt;</code> : Launch interactive disaster mission briefing<br>
            • <code>target &lt;valencia|turkey|milton|california&gt;</code> : Select active crisis<br>
            • <code>band &lt;true|nir|swir|ndvi|ndwi|nbr&gt;</code> : Switch satellite band preset<br>
            • <code>triage</code> : Run START mass casualty classification<br>
            • <code>sos</code> : Broadcast civilian LoRa SOS distress beacon<br>
            • <code>radar &lt;on|off&gt;</code> : Toggle Doppler weather precipitation radar<br>
            • <code>task &lt;satId&gt;</code> : Submit urgent emergency satellite tasking<br>
            • <code>status</code> : View constellation telemetry summary<br>
            • <code>clear</code> : Clear command output log
          `);
          break;

        case 'tour':
          const tourId = arg === '2' ? 'tour-turkey-quake' : arg === '3' ? 'tour-california-fire' : 'tour-valencia-flood';
          if (window.scenarioTour) {
            window.scenarioTour.startMission(tourId);
            this.printOutput(`Launched Mission Tour: ${tourId}`, 'success');
            this.close();
          }
          break;

        case 'target':
          let dId = 'disaster-valencia-dana-2024';
          if (arg.includes('turk')) dId = 'disaster-turkey-syria-quake-2023';
          else if (arg.includes('milt')) dId = 'disaster-hurricane-milton-2024';
          else if (arg.includes('cali')) dId = 'disaster-california-wildfire-complex';
          else if (arg.includes('tong')) dId = 'disaster-tonga-volcano-tsunami-2022';

          if (window.disasterManager) {
            window.disasterManager.selectDisaster(dId);
            this.printOutput(`Crisis Target Locked: ${dId}`, 'success');
          }
          break;

        case 'band':
          let bMode = 'TRUE_COLOR';
          if (arg === 'nir') bMode = 'FALSE_COLOR_NIR';
          else if (arg === 'swir') bMode = 'SWIR';
          else if (arg === 'ndvi') bMode = 'NDVI';
          else if (arg === 'ndwi') bMode = 'NDWI';
          else if (arg === 'nbr') bMode = 'NBR';

          if (window.spectralAnalysis) {
            window.spectralAnalysis.setBandMode(bMode);
            this.printOutput(`Spectral Band Mode Activated: ${bMode}`, 'success');
          }
          break;

        case 'triage':
          if (window.casualtyTriage && window.disasterManager) {
            const active = window.disasterManager.getSelected();
            const triage = window.casualtyTriage.classifyCasualties(active);
            this.printOutput(`
              <strong>START TRIAGE REPORT (${active.title}):</strong><br>
              • Immediate (Red): ${triage.triageBreakdown.immediateRed} patients<br>
              • Delayed (Yellow): ${triage.triageBreakdown.delayedYellow} patients<br>
              • Minor (Green): ${triage.triageBreakdown.minorGreen} patients<br>
              • Available ICU Beds: ${triage.traumaCapacity.totalAvailableIcu} beds (Deficit: ${triage.traumaCapacity.criticalBedDeficit})
            `, 'warn');
          }
          break;

        case 'sos':
          if (window.evacuationMeshNetwork) {
            const active = window.disasterManager ? window.disasterManager.getSelected() : null;
            const lat = active ? active.location.lat + (Math.random() * 0.04 - 0.02) : 39.43;
            const lon = active ? active.location.lon + (Math.random() * 0.04 - 0.02) : -0.39;
            const beacon = window.evacuationMeshNetwork.broadcastSOS(lat, lon, 'TRAPPED_COLLAPSE', 3, 'Civilian SOS beacon broadcast via LoRa relay');
            this.printOutput(`SOS Beacon Dispatched [${beacon.beaconId}] at (${lat.toFixed(4)}, ${lon.toFixed(4)})`, 'success');
          }
          break;

        case 'radar':
          if (window.weatherRadar) {
            const isOn = window.weatherRadar.toggleRadar(arg !== 'off');
            this.printOutput(`Doppler Weather Radar: ${isOn ? 'ONLINE' : 'MUTED'}`, 'info');
          }
          break;

        case 'status':
          if (window.SatelliteCatalog) {
            const activeCount = window.SatelliteCatalog.getAllActive().length;
            this.printOutput(`CONSTELLATION STATUS: ${activeCount} active spacecraft operating in nominal Sun-Synchronous LEO and Geostationary orbits. SGP4 propagator healthy.`, 'info');
          }
          break;

        case 'clear':
          if (this.outputElem) this.outputElem.innerHTML = '';
          break;

        default:
          this.printOutput(`Unknown command: '${action}'. Type 'help' for command listing.`, 'error');
          break;
      }
    }
  }

  window.commandPalette = new CockpitCommandPalette();
  window.addEventListener('DOMContentLoaded', () => {
    if (window.commandPalette) window.commandPalette.init();
  });

})(window);
