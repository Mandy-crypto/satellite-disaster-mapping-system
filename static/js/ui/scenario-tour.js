/**
 * ============================================================================
 * ASTRA-GEO // SATELLITE DISASTER INTELLIGENCE PLATFORM
 * INTERACTIVE MISSION BRIEFING & SCENARIO WALKTHROUGH TOUR
 * ============================================================================
 * Automated aerospace mission briefing director choreographing 3D globe camera,
 * 2D GIS vector overlays, multispectral band switching, and audio telemetry.
 */

(function (window) {
  'use strict';

  const TOUR_MISSIONS = [
    {
      id: 'tour-valencia-flood',
      title: 'Mission 1: Flash Flood Emergency Inundation Response (Valencia)',
      disasterId: 'disaster-valencia-dana-2024',
      steps: [
        {
          title: 'Step 1: Orbital Detection & Anomaly Ingestion',
          text: 'Copernicus Sentinel-1A SAR C-Band radar downlinks flood coherence drop over Rambla del Poyo river basin. Standing water is identified despite dense cloud cover.',
          bandMode: 'NDWI',
          timeOffsetHours: 6
        },
        {
          title: 'Step 2: Critical Infrastructure Severance Audit',
          text: 'AI damage segmentation confirms V-31 and CV-400 highway corridors submerged under 2.8m surge. Over 155,000 households disconnected from electric power.',
          bandMode: 'TRUE_COLOR',
          timeOffsetHours: 12
        },
        {
          title: 'Step 3: First Responder Dispatch & Shelter Routing',
          text: 'Heuristic A* router computes bypass corridors. Paiporta USAR Task Force 1 and Swiftwater Rescue Boats are dispatched to extract survivors to Feria Valencia Emergency Hub.',
          bandMode: 'FALSE_COLOR_NIR',
          timeOffsetHours: 24
        }
      ]
    },
    {
      id: 'tour-turkey-quake',
      title: 'Mission 2: Fault Rupture Search & Rescue (Turkey M7.8)',
      disasterId: 'disaster-turkey-syria-quake-2023',
      steps: [
        {
          title: 'Step 1: InSAR Co-Seismic Surface Offset Mapping',
          text: 'Differential Interferometry (DInSAR) reveals up to 6.8 meters of left-lateral strike-slip ground displacement along the East Anatolian Fault.',
          bandMode: 'SAR_COHERENCE',
          timeOffsetHours: 0
        },
        {
          title: 'Step 2: Sub-Meter Optical Structural Collapse Analysis',
          text: 'WorldView-3 0.31m tasking pass captures 164,000 building footprints. European Macroseismic Scale Grade 5 total collapse zones are highlighted for heavy rescue.',
          bandMode: 'TRUE_COLOR',
          timeOffsetHours: 18
        }
      ]
    },
    {
      id: 'tour-california-fire',
      title: 'Mission 3: Pyrocumulonimbus Wildfire Defense (Sierra Nevada)',
      disasterId: 'disaster-california-wildfire-complex',
      steps: [
        {
          title: 'Step 1: SWIR Smoke Penetration & Active Fire Front',
          text: 'Shortwave Infrared (Bands 12/8A) penetrates dense smoke plumes to map active flaming fronts radiating 4,850 Megawatts of Fire Radiative Power (FRP).',
          bandMode: 'SWIR',
          timeOffsetHours: 0
        },
        {
          title: 'Step 2: Rothermel Elliptical Spread Simulation',
          text: 'Forward rate of spread projected at 2.8 mph under 45 mph downslope gales. Mandatory evacuation perimeter generated for Wildland-Urban Interface towns.',
          bandMode: 'NBR',
          timeOffsetHours: 12
        }
      ]
    }
  ];

  class ScenarioTourDirector {
    constructor() {
      this.activeMission = null;
      this.currentStepIdx = 0;
      this.tourContainer = null;
    }

    init() {
      this.createTourOverlay();
    }

    createTourOverlay() {
      this.tourContainer = document.createElement('div');
      this.tourContainer.id = 'scenario-tour-overlay';
      this.tourContainer.style.cssText = `
        position: fixed;
        bottom: 180px;
        left: 50%;
        transform: translateX(-50%);
        width: 90%;
        max-width: 680px;
        background: rgba(10, 14, 26, 0.96);
        border: 1px solid var(--accent-cyan);
        border-radius: var(--radius-sm);
        box-shadow: 0 10px 40px rgba(0,0,0,0.8), var(--glow-cyan);
        padding: 16px 20px;
        z-index: 500;
        display: none;
        flex-direction: column;
        gap: 10px;
        font-family: var(--font-sans);
        backdrop-filter: blur(16px);
      `;

      document.body.appendChild(this.tourContainer);
    }

    startMission(missionId) {
      const mission = TOUR_MISSIONS.find(m => m.id === missionId) || TOUR_MISSIONS[0];
      this.activeMission = mission;
      this.currentStepIdx = 0;

      // Select disaster
      if (window.disasterManager) {
        window.disasterManager.selectDisaster(mission.disasterId);
      }

      this.renderCurrentStep();
      this.tourContainer.style.display = 'flex';

      if (window.soundEngine) {
        window.soundEngine.playSatTelemetryAcquired();
      }
    }

    renderCurrentStep() {
      if (!this.activeMission || !this.tourContainer) return;
      const step = this.activeMission.steps[this.currentStepIdx];
      const isLast = this.currentStepIdx === this.activeMission.steps.length - 1;

      // Apply step effects
      if (step.bandMode && window.spectralAnalysis) {
        window.spectralAnalysis.setBandMode(step.bandMode);
      }
      if (step.timeOffsetHours !== undefined && window.timelineScrubber) {
        window.timelineScrubber.setTimeOffset(step.timeOffsetHours);
      }

      this.tourContainer.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid var(--border-subtle); padding-bottom:8px;">
          <div>
            <span style="font-family:var(--font-mono); font-size:0.65rem; color:var(--accent-cyan); text-transform:uppercase; letter-spacing:1px;">TACTICAL BRIEFING // ${this.activeMission.title}</span>
            <h3 style="font-family:var(--font-display); font-size:1.05rem; color:#fff; margin-top:2px;">${step.title}</h3>
          </div>
          <button id="btn-close-tour" style="background:none; border:none; color:var(--text-muted); cursor:pointer; font-size:1.1rem;">✕</button>
        </div>
        <p style="font-family:var(--font-mono); font-size:0.75rem; color:var(--text-primary); line-height:1.6;">
          ${step.text}
        </p>
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top:4px;">
          <span style="font-family:var(--font-mono); font-size:0.7rem; color:var(--text-muted);">
            STEP ${this.currentStepIdx + 1} OF ${this.activeMission.steps.length}
          </span>
          <div style="display:flex; gap:8px;">
            ${this.currentStepIdx > 0 ? '<button class="btn-tactical" id="btn-tour-prev">PREV</button>' : ''}
            <button class="btn-tactical primary" id="btn-tour-next">${isLast ? 'FINISH BRIEFING' : 'NEXT STEP ➔'}</button>
          </div>
        </div>
      `;

      document.getElementById('btn-close-tour').addEventListener('click', () => this.endTour());

      const prevBtn = document.getElementById('btn-tour-prev');
      if (prevBtn) {
        prevBtn.addEventListener('click', () => {
          this.currentStepIdx--;
          this.renderCurrentStep();
          if (window.soundEngine) window.soundEngine.playClick();
        });
      }

      document.getElementById('btn-tour-next').addEventListener('click', () => {
        if (isLast) {
          this.endTour();
        } else {
          this.currentStepIdx++;
          this.renderCurrentStep();
          if (window.soundEngine) window.soundEngine.playToggle();
        }
      });
    }

    endTour() {
      if (this.tourContainer) {
        this.tourContainer.style.display = 'none';
      }
      this.activeMission = null;
      if (window.soundEngine) window.soundEngine.playClick();
    }
  }

  window.scenarioTour = new ScenarioTourDirector();
  window.addEventListener('DOMContentLoaded', () => {
    if (window.scenarioTour) window.scenarioTour.init();
  });

})(window);
