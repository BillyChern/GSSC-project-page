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
      if (r.eval !== split) {
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
      td.appendChild(el('span', 'pos', '+' + data[k].toFixed(2)));
      tot.appendChild(td);
    });
    body.appendChild(tot);
  }

  function bibtex() {
    var btn = document.getElementById('bibtex-copy');
    var code = document.getElementById('bibtex-code');
    var label = document.getElementById('bibtex-copy-label');
    if (!btn || !code || !navigator.clipboard) return;
    btn.addEventListener('click', function () {
      navigator.clipboard.writeText(code.textContent).then(function () {
        label.textContent = 'Copied';
        setTimeout(function () { label.textContent = 'Copy'; }, 1600);
      });
    });
  }

  function load(url, fn) {
    fetch(url).then(function (r) { return r.json(); }).then(fn).catch(function () {
      /* A failed fetch leaves the table empty rather than showing stale markup. */
    });
  }

  load('data/results.json', mainResults);
  load('data/perclass.json', perClass);
  bibtex();
})();
