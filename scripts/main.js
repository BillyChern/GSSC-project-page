/* Renders the two paper tables from data/*.json and wires the BibTeX copy button.
   No innerHTML anywhere: every node is built and text-assigned explicitly. */
(function () {
  'use strict';

  var el = function (tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined && text !== null) n.textContent = String(text);
    return n;
  };

  /* A signed delta, coloured, with an explicit + on gains. */
  var delta = function (v) {
    var td = el('td', 'num');
    var s = (v > 0 ? '+' : '') + v.toFixed(1);
    var span = el('span', v > 0 ? 'pos' : (v < 0 ? 'neg' : ''), s);
    td.appendChild(span);
    return td;
  };

  /* Render at the precision the paper prints. Forcing toFixed(1) would turn
     Table I's 50.24 and 59.25 into 50.2 / 59.3 and silently disagree with it. */
  var fmt = function (v) {
    if (v === null || v === undefined) return '—';
    return Number.isInteger(v * 10) ? v.toFixed(1) : String(v);
  };
  var num = function (v) { return el('td', 'num', fmt(v)); };

  function mainResults(rows) {
    var body = document.getElementById('main-results-body');
    if (!body) return;
    /* The best eligible cell is computed, never hard-coded, so the table
       cannot drift from the predicate it claims to apply. */
    var bestIn = function (split) {
      return rows.reduce(function (m, r) {
        return (r.eval === split && !r.excluded && r.mIoU > m) ? r.mIoU : m;
      }, -Infinity);
    };
    var best = { test: bestIn('test'), val: bestIn('val') };
    var split = null;

    rows.forEach(function (r) {
      /* The paper bolds best-per-column WITHIN a split, so the splits are
         separated and each carries its own maximum. */
      /* Only emit a split header for a split the data actually declares. A row
         missing `eval` used to fall through to the else-branch and get stamped
         "Validation (sequence 08)", labelling rows with a split they never
         claimed. */
      var known = (r.eval === 'test' || r.eval === 'val');
      if (known && r.eval !== split) {
        split = r.eval;
        var sep = el('tr', 'split');
        var sth = el('th', null, split === 'test' ? 'SemanticKITTI hidden test' : 'Validation (sequence 08)');
        sth.setAttribute('colspan', '6'); sth.setAttribute('scope', 'colgroup');
        sep.appendChild(sth); body.appendChild(sep);
      }
      var tr = el('tr', (r.ours ? 'ours ' : '') + (r.excluded ? 'excluded' : ''));
      var th = el('th', null, r.method);
      th.setAttribute('scope', 'row');
      th.style.fontWeight = '400';
      tr.appendChild(th);

      var m = el('td', 'num');
      var mv = el('span', (!r.excluded && r.mIoU === best[r.eval]) ? 'best' : '', fmt(r.mIoU));
      m.appendChild(mv);
      tr.appendChild(m);

      tr.appendChild(num(r.comp));
      tr.appendChild(num(r.scm));
      tr.appendChild(num(r.vru));
      tr.appendChild(el('td', 'note', r.note || ''));
      body.appendChild(tr);
    });
  }

  function perClass(data) {
    var body = document.getElementById('perclass-body');
    if (!body) return;

    data.classes.forEach(function (c) {
      var tr = el('tr');
      var th = el('th', null, c.klass);
      th.setAttribute('scope', 'row');
      th.style.fontWeight = '400';
      if (c.vru) th.appendChild(el('span', 'note', '  (VRU)'));
      tr.appendChild(th);
      tr.appendChild(num(c.base));

      /* The one entry the paper does not claim is struck through in the
         Released column and titled with the reason, so the page cannot
         present it as a result. */
      var rel = delta(c.released);
      if (c.disclaimed) {
        rel.firstChild.className += ' disclaimed';
        rel.title = 'Not claimed: fails to reproduce. The from-scratch retrain recovers only +0.3.';
      }
      tr.appendChild(rel);
      tr.appendChild(delta(c.retrain));
      body.appendChild(tr);
    });

    /* The overall row keeps the paper's own precision (36.17, +2.36); rounding it
       to one decimal here would silently disagree with Table II. */
    var tot = el('tr');
    var th = el('th', null, 'Overall mIoU');
    th.setAttribute('scope', 'row');
    tot.appendChild(th);
    tot.appendChild(el('td', 'num', data.base_miou.toFixed(2)));
    ['released_delta', 'retrain_delta'].forEach(function (k) {
      var td = el('td', 'num');
      /* Print what the paper prints: +2.36 and +1.9. toFixed(2) invented a
         trailing zero the paper does not carry. */
      td.appendChild(el('span', 'pos', '+' + fmt(data[k])));
      tot.appendChild(td);
    });
    body.appendChild(tot);

    /* Table II's last row. Omitting it while captioning the table "Source:
       paper Table II" made the page's own safety claim unsourced. */
    if (data.vru_iou) {
      var v = el('tr');
      var vth = el('th', null, 'VRU-IoU');
      vth.setAttribute('scope', 'row');
      vth.appendChild(el('span', 'note', '  (person, bicyclist, motorcyclist)'));
      v.appendChild(vth);
      v.appendChild(num(data.vru_iou.base));
      v.appendChild(delta(data.vru_iou.released));
      v.appendChild(delta(data.vru_iou.retrain));
      body.appendChild(v);
    }
  }

  function bibtex() {
    var btn = document.getElementById('bibtex-copy');
    var code = document.getElementById('bibtex-code');
    var label = document.getElementById('bibtex-copy-label');
    if (!btn || !code) return;
    /* Hide the control where the API does not exist rather than leaving a button
       that silently does nothing. */
    if (!navigator.clipboard) { btn.hidden = true; return; }
    btn.hidden = false;   // ships hidden so JS-off readers are not offered a dead control
    btn.addEventListener('click', function () {
      navigator.clipboard.writeText(code.textContent).then(function () {
        label.textContent = 'Copied';
        setTimeout(function () { label.textContent = 'Copy'; }, 1600);
      }).catch(function () { label.textContent = 'Press \u2318/Ctrl+C'; });
    });
  }

  /* A table that renders its headers and no rows, with nothing said, is a silent
     failure: the reader cannot tell an empty result from a broken fetch. Say so. */
  function tableError(bodyId, cols, url) {
    var body = document.getElementById(bodyId);
    if (!body || body.children.length) return;
    var tr = el('tr');
    var td = el('td', 'note', 'This table could not be loaded from ' + url +
                              '. The same table is in the paper.');
    td.setAttribute('colspan', String(cols));
    tr.appendChild(td);
    body.appendChild(tr);
  }

  function load(url, fn, bodyId, cols) {
    fetch(url)
      .then(function (r) {
        if (!r.ok) throw new Error(r.status + ' ' + r.statusText);
        return r.json();
      })
      .then(fn)
      .then(function () { tableError(bodyId, cols, url); })   // parsed but produced no rows
      .catch(function (e) {
        console.error('Could not load ' + url, e);
        tableError(bodyId, cols, url);
      });
  }

  /* viewer3d.js is an ES module importing three.js from a CDN. If that fetch
     fails -- CDN down, offline, a firewall -- the module never executes, boot()
     never runs, and the stage sits on "Loading scene..." indefinitely with no
     explanation. viewer3d.js cannot report this itself, because it is the thing
     that did not load. main.js is a classic script and always runs, so the
     watchdog belongs here. */
  function viewerWatchdog() {
    var stage = document.getElementById('viewer3d-stage');
    var note = document.getElementById('viewer3d-loading');
    if (!stage || !note) return;
    setTimeout(function () {
      if (stage.querySelector('canvas')) return;          // the viewer booted
      if (note.classList.contains('viewer3d__fallback')) return;  // already explained
      note.classList.remove('is-hidden');
      note.classList.add('viewer3d__fallback');
      /* The stage is one labelled image to assistive tech, and its label promises a
         comparison. When the library never arrives no module code runs, so this is
         the only place that can stop the promise being announced. */
      if (stage.getAttribute('aria-label')) {
        /* Preserve the truthful label so a late-arriving viewer can restore it. */
        if (!stage.dataset.labelReady) stage.dataset.labelReady = stage.getAttribute('aria-label');
        stage.setAttribute('aria-label', '3D comparison unavailable: the viewer library did not load. '
          + 'The same comparison is in the qualitative figure above.');
      }
      while (note.firstChild) note.removeChild(note.firstChild);
      var p = document.createElement('p');
      p.className = 'viewer3d__fallback-text';
      p.append('The 3D viewer could not load its library, so nothing is drawn. ');
      var a = document.createElement('a');
      a.href = '#teaser';
      a.textContent = 'The same comparison is in the figure above.';
      p.appendChild(a);
      note.appendChild(p);
    }, 8000);
  }
  viewerWatchdog();

  load('data/results.json', mainResults, 'main-results-body', 6);
  load('data/perclass.json', perClass, 'perclass-body', 4);
  bibtex();
})();
