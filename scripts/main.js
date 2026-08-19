/* Two jobs, both small.

   This file used to render the page's two results tables from data/*.json. The page
   now shows results as a figure (assets/figures/results_chart.png, generated from that
   same JSON by tools/make_results_chart.py), so the renderers and their error paths are
   gone rather than left unreachable. The JSON is still the source of truth for the
   chart, and tools/check_content.py gates the two against each other.

   What remains: the BibTeX copy button, and a watchdog for a three.js that never
   arrives — which has to live here, in a classic script that always runs, because the
   module that fails cannot report its own absence. */
(function () {
  'use strict';

  function bibtex() {
    var btn = document.getElementById('bibtex-copy');
    var code = document.getElementById('bibtex-code');
    var label = document.getElementById('bibtex-copy-label');
    if (!btn || !code) return;
    /* Ships hidden so a JS-off reader is not offered a control that cannot work; the
       same reason it stays hidden where the Clipboard API is absent. */
    if (!navigator.clipboard) { btn.hidden = true; return; }
    btn.hidden = false;
    btn.addEventListener('click', function () {
      navigator.clipboard.writeText(code.textContent).then(function () {
        label.textContent = 'Copied';
        setTimeout(function () { label.textContent = 'Copy'; }, 1600);
      }).catch(function () {
        /* Never claim a copy that did not happen. */
        label.textContent = 'Press ⌘/Ctrl+C';
      });
    });
  }

  function viewerWatchdog() {
    var stage = document.getElementById('viewer3d-stage');
    var note = document.getElementById('viewer3d-loading');
    if (!stage || !note) return;
    setTimeout(function () {
      if (stage.querySelector('canvas')) return;                  // the viewer booted
      if (note.classList.contains('viewer3d__fallback')) return;   // already explained
      note.classList.remove('is-hidden');
      note.classList.add('viewer3d__fallback');
      /* The stage is one labelled image to assistive tech and its label promises a
         comparison. When the library never arrives no module code runs, so this is the
         only place that can stop that promise being announced. Preserve the truthful
         label so a late-arriving viewer can restore it. */
      if (stage.getAttribute('aria-label')) {
        if (!stage.dataset.labelReady) stage.dataset.labelReady = stage.getAttribute('aria-label');
        stage.setAttribute('aria-label', '3D comparison unavailable: the viewer library did not load. '
          + 'The same comparison is in the qualitative figure above.');
      }
      while (note.firstChild) note.removeChild(note.firstChild);
      var p = document.createElement('p');
      p.className = 'viewer3d__fallback-text';
      p.append('The 3D viewer could not load its library, so nothing is drawn. ');
      var a = document.createElement('a');
      /* '#results', not '#teaser': since the page was restructured #teaser is the
         Fig. 1(a) task figure, and this link promises the qualitative comparison,
         which is Fig. 6 in the results section. */
      a.href = '#results';
      a.textContent = 'The same comparison is in the figure above.';
      p.appendChild(a);
      note.appendChild(p);
    }, 8000);
  }

  bibtex();
  viewerWatchdog();
})();
