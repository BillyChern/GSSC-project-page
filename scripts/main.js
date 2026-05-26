/* =============================================================
   main.js — entry point: scroll reveal, section links, BibTeX copy,
             safe DOM table hydration from JSON.
   ============================================================= */

(function () {
  'use strict';

  // ---------- Scroll reveal via IntersectionObserver ----------
  const revealElements = document.querySelectorAll(
    '.section, .hero__lede, .hero__art, .figure-wide, .method-card, .table-card, .code-card, .metric'
  );
  revealElements.forEach((el) => el.classList.add('reveal'));

  if (!('IntersectionObserver' in window) ||
      window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    revealElements.forEach((el) => el.classList.add('is-in'));
  } else {
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) {
          e.target.classList.add('is-in');
          io.unobserve(e.target);
        }
      });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.05 });
    revealElements.forEach((el) => io.observe(el));
  }

  // ---------- BibTeX copy-to-clipboard ----------
  const copyBtn = document.getElementById('bibtex-copy');
  const copyLabel = document.getElementById('bibtex-copy-label');
  const bibtexEl = document.getElementById('bibtex-code');
  if (copyBtn && bibtexEl) {
    copyBtn.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(bibtexEl.textContent);
        copyLabel.textContent = 'Copied';
        copyBtn.setAttribute('aria-pressed', 'true');
        setTimeout(() => {
          copyLabel.textContent = 'Copy';
          copyBtn.setAttribute('aria-pressed', 'false');
        }, 1600);
      } catch (err) {
        copyLabel.textContent = 'Press \u2318C';
      }
    });
  }

  // ---------- Smooth scroll with sticky-nav offset ----------
  document.querySelectorAll('a[href^="#"]').forEach((a) => {
    a.addEventListener('click', (e) => {
      // Placeholder links under double-blind review: swallow the click so
      // the page does not jump to top when the user clicks Paper/arXiv/Code.
      if (a.getAttribute('aria-disabled') === 'true') {
        e.preventDefault();
        return;
      }
      const id = a.getAttribute('href').slice(1);
      if (!id) {
        // Bare href="#" with no target: prevent the implicit top-scroll.
        e.preventDefault();
        return;
      }
      const target = document.getElementById(id);
      if (!target) return;
      e.preventDefault();
      const navH = document.querySelector('.topnav')?.getBoundingClientRect().height || 0;
      const rect = target.getBoundingClientRect();
      window.scrollTo({
        top: rect.top + window.scrollY - navH - 8,
        behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'
      });
    });
  });

  // ---------- Safe DOM builders (no innerHTML) ----------
  function el(tag, opts = {}) {
    const node = document.createElement(tag);
    if (opts.className) node.className = opts.className;
    if (opts.text !== undefined) node.textContent = opts.text;
    if (opts.attrs) for (const [k, v] of Object.entries(opts.attrs)) node.setAttribute(k, v);
    if (opts.children) opts.children.forEach((c) => c && node.appendChild(c));
    return node;
  }

  function chip(label, variant) {
    const cls = 'chip' + (variant ? ' chip--' + variant : '');
    return el('span', { className: cls, text: label });
  }

  function renderMain(rows) {
    const body = document.getElementById('main-results-body');
    if (!body) return;
    body.textContent = '';
    rows.forEach((r) => {
      const tr = el('tr');
      if (r.ours) tr.classList.add('is-ours');

      // Method cell
      const methodTd = el('td');
      methodTd.appendChild(document.createTextNode(r.method));
      if (r.note_inline) {
        methodTd.appendChild(document.createTextNode(' '));
        methodTd.appendChild(chip(r.note_inline));
      }
      tr.appendChild(methodTd);

      // Modality chip
      const modTd = el('td', { className: 'td--center' });
      const modVariant = r.mod === 'C' ? 'camera' : (r.ours ? 'ours' : 'lidar');
      const modLabel = r.mod === 'C' ? 'camera' : 'LiDAR-SF';
      modTd.appendChild(chip(modLabel, modVariant));
      tr.appendChild(modTd);

      // mIoU
      const miouTd = el('td', {
        className: 'num' + (r.best ? ' num--best' : ''),
        text: r.mIoU.toFixed(1)
      });
      tr.appendChild(miouTd);

      // Note
      tr.appendChild(el('td', { className: 'td--center', text: r.note || '\u2014' }));

      body.appendChild(tr);
    });
  }

  function renderPerclass(rows) {
    const body = document.getElementById('perclass-body');
    if (!body) return;
    body.textContent = '';
    rows.forEach((r) => {
      const tr = el('tr');
      const delta = r.ours - r.scp;
      const deltaClass = delta >= 1 ? 'num num--gain'
                        : delta <= -1 ? 'num num--loss'
                        : 'num';

      const klassTd = el('td');
      klassTd.appendChild(document.createTextNode(r.klass));
      if (r.safety) {
        const dagger = el('span', {
          text: ' \u2020',
          attrs: { role: 'img', 'aria-label': 'safety-critical', style: 'color:var(--c-accent)' }
        });
        klassTd.appendChild(dagger);
      }
      tr.appendChild(klassTd);

      tr.appendChild(el('td', { className: 'num', text: r.scp.toFixed(1) }));
      tr.appendChild(el('td', { className: 'num', text: r.ours.toFixed(1) }));
      tr.appendChild(el('td', {
        className: deltaClass,
        text: (delta >= 0 ? '+' : '') + delta.toFixed(1)
      }));

      body.appendChild(tr);
    });
  }

  // ---------- Hydrate tables from JSON ----------
  const hydrate = async () => {
    try {
      const [mainResp, perclassResp] = await Promise.all([
        fetch('data/results.json'),
        fetch('data/perclass.json'),
      ]);
      if (!mainResp.ok || !perclassResp.ok) return;
      const main = await mainResp.json();
      const perclass = await perclassResp.json();
      renderMain(main);
      renderPerclass(perclass);
      if (window.initTableSort) window.initTableSort();
    } catch (err) {
      console.warn('Results data failed to load', err);
    }
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', hydrate);
  } else {
    hydrate();
  }

})();
