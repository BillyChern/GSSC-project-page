/* =============================================================
   anon.js — toggle anonymous mode for double-blind review.
   Flipping aria-pressed on #anon-toggle flips body[data-anon].
   ============================================================= */
(function () {
  'use strict';
  const toggle = document.getElementById('anon-toggle');
  const label  = document.getElementById('anon-label');
  if (!toggle || !label) return;

  const setMode = (anon) => {
    document.body.dataset.anon = anon ? 'true' : 'false';
    toggle.setAttribute('aria-pressed', anon ? 'true' : 'false');
    // The label names the ACTION the button performs, not the current state.
    // It previously read 'Reveal authors' while the authors were already visible.
    label.textContent = anon ? 'Show authors' : 'Hide authors';
  };

  // Persist preference across reloads; default: anonymous.
  try {
    const stored = localStorage.getItem('s2d2-anon');
    if (stored !== null) setMode(stored === 'true');
  } catch (_) {}

  toggle.addEventListener('click', () => {
    const next = document.body.dataset.anon !== 'true';
    setMode(next);
    try { localStorage.setItem('s2d2-anon', String(next)); } catch (_) {}
  });
})();
