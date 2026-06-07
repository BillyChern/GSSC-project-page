/* =============================================================
   main.js — entry point: scroll reveal, section links, BibTeX copy,
             safe DOM table hydration from JSON.
   ============================================================= */

(function () {
  'use strict';

  // ---------- Scroll reveal via IntersectionObserver ----------
  // Reveal is one-shot: once an element fades in, it stays in (we unobserve
  // it) so content never re-hides when a section scrolls back out of view.
  // The hidden opacity:0 state only applies when JS is running (the .reveal
  // class is added here), so with JS disabled / failed the content defaults
  // to visible. A belt-and-suspenders fallback force-reveals anything still
  // hidden shortly after load, so a card that was scrolled past too fast to
  // trip the observer can never get stuck blank.
  const revealElements = document.querySelectorAll(
    '.section, .hero__lede, .hero__art, .figure-wide, .method-card, .table-card, .code-card, .metric'
  );

  const revealAll = () => revealElements.forEach((el) => el.classList.add('is-in'));

  if (!('IntersectionObserver' in window) ||
      window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    // No fade: show everything immediately (also covers reduced-motion).
    revealElements.forEach((el) => el.classList.add('reveal'));
    revealAll();
  } else {
    revealElements.forEach((el) => el.classList.add('reveal'));
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) {
          e.target.classList.add('is-in');   // reveal once
          io.unobserve(e.target);            // never re-hide
        }
      });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.05 });
    revealElements.forEach((el) => io.observe(el));

    // Safety net: anything not yet revealed a moment after full load is
    // force-shown so fast scrolls / never-in-view elements can't stay blank.
    const flush = () => { io.disconnect(); revealAll(); };
    window.addEventListener('load', () => setTimeout(flush, 1200));
  }

  // ---------- Mobile / tablet nav toggle (<=880px) ----------
  const navToggle = document.getElementById('nav-toggle');
  const navLinks = document.getElementById('topnav-links');
  if (navToggle && navLinks) {
    const closeNav = () => {
      navLinks.classList.remove('is-open');
      navToggle.setAttribute('aria-expanded', 'false');
      navToggle.setAttribute('aria-label', 'Open navigation menu');
    };
    const openNav = () => {
      navLinks.classList.add('is-open');
      navToggle.setAttribute('aria-expanded', 'true');
      navToggle.setAttribute('aria-label', 'Close navigation menu');
    };
    navToggle.addEventListener('click', () => {
      if (navLinks.classList.contains('is-open')) closeNav();
      else openNav();
    });
    // Close after picking a section so the panel doesn't cover the target.
    navLinks.querySelectorAll('a').forEach((a) => {
      a.addEventListener('click', closeNav);
    });
    // Close on Escape and when widening past the breakpoint.
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') closeNav();
    });
    window.addEventListener('resize', () => {
      if (window.innerWidth > 880) closeNav();
    });
  }

  // ---------- Table horizontal-scroll affordance ----------
  // Flag any table-card whose inner scroller overflows so the CSS
  // right-edge fade + scroll hint appear only when content is clipped.
  const tableCards = document.querySelectorAll('.table-card');
  // Overflow-aware right-edge fade: hide the scrim once the inner scroller
  // is at (or within 2px of) its right end, so it never scrims fully-
  // revealed NOTE text. Re-evaluated on scroll and on overflow recompute.
  function updateScrollEnd(card, sc) {
    const atEnd = sc.scrollLeft + sc.clientWidth >= sc.scrollWidth - 2;
    card.setAttribute('data-scroll-end', atEnd ? 'true' : 'false');
  }
  function updateTableOverflow() {
    tableCards.forEach((card) => {
      const sc = card.querySelector('.table-card__scroll');
      if (!sc) return;
      const overflows = sc.scrollWidth > sc.clientWidth + 1;
      card.setAttribute('data-overflow', overflows ? 'true' : 'false');
      if (overflows) {
        updateScrollEnd(card, sc);
        if (!sc.dataset.scrollBound) {
          sc.addEventListener('scroll', () => updateScrollEnd(card, sc), { passive: true });
          sc.dataset.scrollBound = 'true';
        }
      } else {
        card.removeAttribute('data-scroll-end');
      }
      // Inject a one-time "scroll →" hint into the card head.
      if (overflows && !card.querySelector('.table-card__scroll-hint')) {
        const head = card.querySelector('.table-card__head p')
          || card.querySelector('.table-card__head');
        if (head) {
          const hint = document.createElement('span');
          hint.className = 'table-card__scroll-hint';
          hint.textContent = 'scroll →';
          head.appendChild(document.createTextNode(' '));
          head.appendChild(hint);
        }
      }
    });
  }
  updateTableOverflow();
  window.addEventListener('resize', updateTableOverflow);
  // Re-check after table hydration (tables fill in async below).
  window.__updateTableOverflow = updateTableOverflow;

  // ---------- Mobile dense-figure tap-to-zoom (<=480px) ----------
  // Each wide figure fits the column by default (CSS). The toggle switches the
  // media box into the secondary scrollable detail view (.is-zoomed) and, on
  // zoom, scrolls it so the key column (the "Ours"/S2D2-output region near the
  // right) is visible first instead of the leftmost panel.
  document.querySelectorAll('.figure-wide--dense').forEach((fig) => {
    const media = fig.querySelector('.figure-wide__media');
    if (!media) return;
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'figure-zoom-toggle';
    btn.textContent = 'tap to zoom →';
    btn.setAttribute('aria-pressed', 'false');
    media.insertAdjacentElement('afterend', btn);
    btn.addEventListener('click', () => {
      const zoom = !media.classList.contains('is-zoomed');
      media.classList.toggle('is-zoomed', zoom);
      btn.setAttribute('aria-pressed', zoom ? 'true' : 'false');
      btn.textContent = zoom ? 'tap to fit ←' : 'tap to zoom →';
      if (zoom) {
        // Reveal the key column: scroll to ~58% of the overflow so the
        // "Ours"/result region (right-of-center) lands in view.
        requestAnimationFrame(() => {
          const overflow = media.scrollWidth - media.clientWidth;
          if (overflow > 0) media.scrollLeft = Math.round(overflow * 0.58);
        });
      } else {
        media.scrollLeft = 0;
      }
    });
  });

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
      // Tables just gained rows — re-evaluate overflow for the scroll cue.
      if (window.__updateTableOverflow) window.__updateTableOverflow();
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
