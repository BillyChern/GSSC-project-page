/* =============================================================
   tableSort.js — click-to-sort data tables.
   Reads data-sort="string|number" on each <th>. Toggles aria-sort.
   ============================================================= */
(function () {
  'use strict';

  function init() {
    document.querySelectorAll('.datatable').forEach((table) => {
      const headers = table.querySelectorAll('thead th[data-sort]');
      headers.forEach((th, colIndex) => {
        th.addEventListener('click', () => {
          const kind = th.dataset.sort;
          const prev = th.getAttribute('aria-sort');
          const next = prev === 'ascending' ? 'descending' : 'ascending';
          // Clear siblings, set self
          th.parentNode.querySelectorAll('th').forEach((s) => s.removeAttribute('aria-sort'));
          th.setAttribute('aria-sort', next);
          sortColumn(table, colIndex, kind, next === 'ascending');
        });
      });
      // Apply any default sort (ascending/descending already on a th)
      const defaultTh = table.querySelector('thead th[aria-sort]');
      if (defaultTh) {
        const colIndex = Array.from(defaultTh.parentNode.children).indexOf(defaultTh);
        const kind = defaultTh.dataset.sort;
        const asc = defaultTh.getAttribute('aria-sort') === 'ascending';
        sortColumn(table, colIndex, kind, asc);
      }
    });
  }

  function parseCell(text, kind) {
    if (kind === 'number') {
      const m = String(text).match(/-?\d+(?:\.\d+)?/);
      return m ? parseFloat(m[0]) : -Infinity;
    }
    return String(text).toLowerCase();
  }

  function sortColumn(table, colIndex, kind, ascending) {
    const tbody = table.tBodies[0];
    if (!tbody) return;
    const rows = Array.from(tbody.querySelectorAll('tr'));
    rows.sort((a, b) => {
      const av = parseCell(a.children[colIndex].textContent.trim(), kind);
      const bv = parseCell(b.children[colIndex].textContent.trim(), kind);
      if (av < bv) return ascending ? -1 : 1;
      if (av > bv) return ascending ? 1 : -1;
      return 0;
    });
    rows.forEach((r) => tbody.appendChild(r));
  }

  window.initTableSort = init;
  // Defer; main.js calls initTableSort() after hydrate
})();
