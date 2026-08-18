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

  // Persist preference across reloads. The DEFAULT IS REVEALED: index.html ships
  // <body data-anon="false">, and this only overrides it when a preference is stored.
  //
  // SCOPE, so nobody mistakes this for blinding: it hides on-page text only. It cannot
  // reach <meta og:url>/<meta og:image>, which hardcode billychern.github.io and are what
  // a shared link previews, and it cannot change the hosting URL itself. A double-anonymous
  // submission needs anonymous HOSTING, not this toggle.
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
