/* =============================================================
   latencyRace.js — three-lane horizontal latency race.
   SCPNet base | S²D² 1-step (base + 107ms) | 100-step comparison.
   Real measurements on H100 80GB, padded with SCPNet estimate until
   we swap in a measured number.
   ============================================================= */
(function () {
  'use strict';

  // --- Data: each lane has a color, a label, segments (name + ms), total.
  // Add multiple segments to stack sub-bars inside one lane (for the
  // "base + add-on" story).
  const LANES = [
    {
      id: 'scpnet',
      label: 'SCPNet base only',
      sub:   'Single-frame LiDAR \u2192 3D voxel prediction',
      color: '#6BA8FF',
      segments: [
        { name: 'SCPNet forward', ms: 210 }
      ]
    },
    {
      id: 's2d2',
      label: 'S\u00B2D\u00B2 1-step (ours)',
      sub:   'SCPNet + one correction UNet forward',
      color: '#F19340',
      segments: [
        { name: 'SCPNet base',  ms: 210 },
        { name: '+ S\u00B2D\u00B2 1-step', ms: 107 }
      ]
    },
    {
      id: 'multi',
      label: '100-step diffusion alt.',
      sub:   'DiffSSC-style multi-step unrolled sampling',
      color: '#6B7487',
      segments: [
        { name: 'SCPNet base',  ms: 210 },
        { name: '100\u00D7 UNet', ms: 10790 }
      ]
    }
  ];

  function init() {
    const root = document.getElementById('race-lanes');
    const startBtn = document.getElementById('race-start');
    if (!root || !startBtn) return;

    // Build static DOM with safe constructors.
    LANES.forEach((lane) => {
      const row = document.createElement('div');
      row.className = 'lane';
      row.dataset.id = lane.id;
      row.style.setProperty('--lane-color', lane.color);

      const labelWrap = document.createElement('div');
      labelWrap.className = 'lane__label';
      labelWrap.appendChild(document.createTextNode(lane.label));
      const sub = document.createElement('span');
      sub.textContent = lane.sub;
      labelWrap.appendChild(sub);
      row.appendChild(labelWrap);

      const track = document.createElement('div');
      track.className = 'lane__track';
      const fill = document.createElement('div');
      fill.className = 'lane__fill';
      fill.style.setProperty('--lane-color', lane.color);
      track.appendChild(fill);
      row.appendChild(track);

      const time = document.createElement('div');
      time.className = 'lane__time';
      time.textContent = '—';
      row.appendChild(time);

      root.appendChild(row);
    });

    startBtn.addEventListener('click', () => {
      if (startBtn.dataset.running === 'true') return;
      run(root, startBtn);
    });
  }

  function run(root, startBtn) {
    startBtn.dataset.running = 'true';
    startBtn.disabled = true;
    const originalLabel = startBtn.textContent.trim();
    startBtn.textContent = 'Running\u2026';

    // Determine max total (longest lane) to scale to 100% width.
    const totals = LANES.map((l) => l.segments.reduce((a, s) => a + s.ms, 0));
    const MAX = Math.max(...totals);

    // We compress wall-clock: show 1s of real UI per 1s of model time,
    // BUT cap the 100-step lane at 6 seconds max UI duration so the
    // viewer doesn't wait 11 seconds. We use a non-linear time mapping:
    //   UI_ms = MAX * log1p(model_ms) / log1p(MAX) * 6.0 seconds
    // The horizontal fill reflects linear proportion to MAX (truth),
    // but fill animates via a pseudo-log time warp so the contrast
    // is visible and no lane drags forever.
    const UI_DURATION_MS = 6000;
    const scaleMs = (ms) => {
      // fraction of MAX
      return Math.max(0, Math.min(1, ms / MAX));
    };

    // Reset lanes
    const rows = root.querySelectorAll('.lane');
    rows.forEach((r) => {
      r.classList.remove('is-done');
      r.querySelector('.lane__fill').style.width = '0%';
      r.querySelector('.lane__fill').style.transition = 'none';
      r.querySelector('.lane__time').textContent = '—';
    });

    // Kick off animations
    const startT = performance.now();
    const finalFractions = LANES.map((l) => scaleMs(l.segments.reduce((a, s) => a + s.ms, 0)));

    rows.forEach((r, i) => {
      // Each lane's own UI duration is proportional to log1p(totalMs)/log1p(MAX) * UI_DURATION_MS
      const totalMs = LANES[i].segments.reduce((a, s) => a + s.ms, 0);
      const warped = Math.log1p(totalMs) / Math.log1p(MAX) * UI_DURATION_MS;
      const fill = r.querySelector('.lane__fill');
      // force reflow, then animate
      fill.getBoundingClientRect();
      fill.style.transition = `width ${Math.round(warped)}ms linear`;
      fill.style.width = (finalFractions[i] * 100).toFixed(2) + '%';
    });

    // Continuously update the numeric readout until each lane finishes
    const timeCells = Array.from(rows).map((r) => r.querySelector('.lane__time'));
    const framesMs = LANES.map((l) => l.segments.reduce((a, s) => a + s.ms, 0));
    const uiDurs  = framesMs.map((m) => Math.log1p(m) / Math.log1p(MAX) * UI_DURATION_MS);

    const finished = new Array(LANES.length).fill(false);

    function tick(now) {
      const t = now - startT;
      LANES.forEach((lane, i) => {
        if (finished[i]) return;
        const ui = Math.min(t / uiDurs[i], 1);
        // Reverse-map the UI progress to the "model time" displayed.
        // Since the fill rendered with log warp, the readout is its
        // inverse: model_ms = (expm1(ui * log1p(MAX))) scaled to this lane.
        const curMs = expm1(ui * log1p(MAX)) * (framesMs[i] / MAX);
        timeCells[i].textContent = fmtMs(curMs);
        if (ui >= 1) {
          finished[i] = true;
          timeCells[i].textContent = fmtMs(framesMs[i]);
          rows[i].classList.add('is-done');
        }
      });
      if (finished.every(Boolean)) {
        startBtn.disabled = false;
        startBtn.dataset.running = 'false';
        startBtn.textContent = 'Run again';
        return;
      }
      requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }

  function log1p(x)  { return Math.log(1 + x); }
  function expm1(x)  { return Math.exp(x) - 1; }
  function fmtMs(ms) {
    if (ms < 10) return ms.toFixed(1) + ' ms';
    if (ms < 1000) return Math.round(ms) + ' ms';
    return (ms / 1000).toFixed(2) + ' s';
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
