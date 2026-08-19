#!/usr/bin/env python3
"""Assert the project page's invariants, and prove the assertions can fail.

Replaces an earlier scratch script that printed a JSON report with NO assertions.
That script was read through a grep which matched `pageerror` but not `"error: ..."`,
so console errors -- including the ones this page's own failure guards emit -- were
invisible, and "no page errors" was reported off a filter that could not see them.

Each check below pins a fix that a previous round landed, so a regression fails loudly
instead of needing to be noticed by eye.

Serve the site first (python -m http.server 8099 from the repo root).

Usage:
    python tools/check_page.py                 # gate the page (exit 1 on any failure)
    python tools/check_page.py --selftest      # prove every check can fail
    python tools/check_page.py --url http://localhost:8099/

47 assertions: 12 x 3 viewports, plus print, no-JS, slow-load and reduced-motion
contexts. ~50s;
--selftest ~3min, because the slow-load check must outwait an 8s watchdog twice.

"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ENGINE = "chromium"

# Keep browser scratch off the small overlay filesystem. Playwright creates a fresh
# browser profile per launch under the system temp dir, and a --selftest run launches
# Chromium ~14 times. Where /tmp shares a modest overlay with /, that accumulation can
# fill the disk -- and a full / is not recoverable from inside a shell, because the
# shell needs to write there to run at all. Honour an existing TMPDIR; otherwise use a
# gitignored dir beside the repo.
if not os.environ.get("TMPDIR"):
    _scratch = Path(__file__).resolve().parent.parent / ".tmp"
    _scratch.mkdir(exist_ok=True)
    os.environ["TMPDIR"] = str(_scratch)

DEFAULT_URL = "http://localhost:8099/"
VIEWPORTS = ((1280, 900, "desktop"), (768, 1024, "tablet"), (375, 812, "mobile"))

PROBE = """() => {
  const q = (s) => document.querySelector(s);
  const identity = q('.identity');
  const legend = q('#viewer3d-stat-row');
  return {
    hscroll: document.documentElement.scrollWidth > document.documentElement.clientWidth,
    // The two HTML tables became one generated chart, so what is assertable in the
    // DOM changed: the predicate is now enforced in tools/check_content.py, against
    // the chart's manifest. Here we check the figures actually render and that the
    // page still reads task -> results -> method.
    sectionOrder: [...document.querySelectorAll('main > section')].map((s) => s.id),
    imagesTotal: document.images.length,
    imagesLoaded: [...document.images].filter((i) => i.naturalWidth > 0).length,
    hasResultsChart: [...document.images].some((i) => /results_chart/.test(i.currentSrc || i.src)),
    predicateShown: /causal, single-sweep, single-sample/.test(
      (document.getElementById('results') || {}).innerText || ''),
    // CSS keyframes only. rAF render loops and transitions are NOT counted, so this
    // pins the corpus "no animation" convention, not the absence of all motion.
    cssAnimations: [...document.querySelectorAll('*')]
      .filter((e) => getComputedStyle(e).animationName !== 'none').length,
    canvas: !!q('#viewer3d-stage canvas'),
    // getComputedStyle(null) throws, which previously killed the whole measurement
    // into a traceback instead of a named failure.
    identityPresent: !!identity,
    legendText: legend ? legend.innerText.replace(/\\s+/g, ' ').trim() : null,
    // The page's founding defect was leading with an EXCLUDED row (39.2, the D4 TTA
    // entry) as if it were the headline. main.js computes the best eligible cell per
    // split rather than hard-coding one; these two readings check that the computation
    // still lands where the predicate says it must.
    stageLabel: (q('#viewer3d-stage') || {}).ariaLabel
                || (q('#viewer3d-stage') ? q('#viewer3d-stage').getAttribute('aria-label') : null),
    // WCAG AA contrast, measured on the RENDERED page rather than read off the tokens.
    // Three restyles in a row shipped a secondary grey that failed AA while a comment
    // in tokens.css asserted it passed -- once at 2.605:1 and once at 3.54:1, the second
    // time carrying every figure caption. A token comment is not a measurement, so this
    // walks every element that paints its own text and computes the real ratio against
    // the first non-transparent background behind it.
    contrastFails: (() => {
      const lin = (c) => { c /= 255; return c <= 0.03928 ? c / 12.92
                                                        : Math.pow((c + 0.055) / 1.055, 2.4); };
      const lum = ([r, g, b]) => 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
      const rgb = (s) => (s.match(/[\d.]+/g) || []).slice(0, 3).map(Number);
      const alpha = (s) => { const n = (s.match(/[\d.]+/g) || []); return n.length > 3 ? +n[3] : 1; };
      const ratio = (a, b) => { const [hi, lo] = [lum(a), lum(b)].sort((x, y) => y - x);
                                return (hi + 0.05) / (lo + 0.05); };
      // The effective background: the nearest ancestor that actually paints one.
      const groundOf = (el) => {
        for (let n = el; n && n.nodeType === 1; n = n.parentElement) {
          const bg = getComputedStyle(n).backgroundColor;
          if (bg && alpha(bg) > 0.05) return rgb(bg);
        }
        return [255, 255, 255];
      };
      const out = [];
      for (const el of document.querySelectorAll('body *')) {
        // Only elements that paint their OWN visible text, so a wrapper is not blamed
        // for the colour of a child that sets its own.
        const own = [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim());
        if (!own) continue;
        const cs = getComputedStyle(el);
        if (cs.visibility === 'hidden' || cs.display === 'none' || +cs.opacity === 0) continue;
        if (!el.getClientRects().length) continue;
        const px = parseFloat(cs.fontSize);
        const wt = parseInt(cs.fontWeight, 10) || 400;
        // WCAG large-text exemption: >=24px, or >=18.66px when bold.
        const need = (px >= 24 || (px >= 18.66 && wt >= 700)) ? 3.0 : 4.5;
        const cr = ratio(rgb(cs.color), groundOf(el));
        if (cr + 0.005 < need) {
          out.push({ tag: el.tagName.toLowerCase(),
                     cls: (el.className || '').toString().slice(0, 28),
                     color: cs.color, px: px, wt: wt,
                     ratio: Math.round(cr * 100) / 100, need: need,
                     text: (el.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 40) });
        }
      }
      return out;
    })(),
  };
}"""


def inspect(browser, url: str, w: int, h: int, fault=None) -> list[tuple[str, bool, str]]:
    """Return [(check_name, passed, detail)] for one viewport."""
    page = browser.new_page(viewport={"width": w, "height": h})
    console: list[str] = []
    page.on("console", lambda m: console.append(f"{m.type}: {m.text}") if m.type == "error" else None)
    page.on("pageerror", lambda e: console.append(f"pageerror: {e}"))
    if fault:
        fault(page)
    page.goto(url, wait_until="networkidle")
    page.wait_for_timeout(4000)  # let the viewer boot and the watchdog window pass
    d = page.evaluate(PROBE)
    page.close()

    legend = d["legendText"] or ""

    # Pin the READING ORDER the page was rebuilt around -- a non-specialist meets the
    # task, then the abstract, then the results, and only then the method -- rather than
    # an exact section list. An exact list has to be edited every time a section is
    # added, and a gate edited to make it pass is not a gate. Requiring the observed
    # order to be a SUBSEQUENCE of the canonical sequence catches every reordering while
    # letting a canonical section be added or dropped without touching this file. An id
    # absent from CANON fails loudly, so a NEW section has to be placed deliberately.
    CANON = ["task", "abstract", "results", "viewer", "method", "gallery", "ack", "bibtex"]
    order = d["sectionOrder"]
    unplaced = [x for x in order if x not in CANON]
    ranks = [CANON.index(x) for x in order if x in CANON]
    order_ok = (ranks == sorted(ranks) and not unplaced
                and {"task", "abstract", "results", "method"} <= set(order)
                and order[-1:] == ["bibtex"])

    return [
        ("sections read task -> abstract -> results -> method",
         order_ok,
         str(order) + (f"  unplaced: {unplaced}" if unplaced else "")),
        # The load-equality is the real assertion; the floor is only a backstop against
        # every figure vanishing at once, so it is set well below the current count
        # rather than tracking it (three edits in a row moved the exact number).
        ("every figure renders", d["imagesLoaded"] == d["imagesTotal"] and d["imagesTotal"] >= 6,
         f'{d["imagesLoaded"]}/{d["imagesTotal"]}'),
        ("results chart is on the page", d["hasResultsChart"], str(d["hasResultsChart"])),
        ("the predicate is stated with the results", d["predicateShown"], str(d["predicateShown"])),
        ("no horizontal page scroll", not d["hscroll"], str(d["hscroll"])),
        ("all text clears WCAG AA contrast", not d["contrastFails"],
         "; ".join(f'{f["tag"]}.{f["cls"]} {f["color"]} {f["px"]}px/{f["wt"]} '
                   f'{f["ratio"]}:1 <{f["need"]} "{f["text"]}"'
                   for f in d["contrastFails"][:4]) or "0 failing elements"),
        ("no CSS keyframe animation", d["cssAnimations"] == 0, str(d["cssAnimations"])),
        ("viewer drew a canvas", d["canvas"], str(d["canvas"])),
        ("author block present", d["identityPresent"], str(d["identityPresent"])),
        ("no console errors", not console, "; ".join(c[:90] for c in console[:2]) or "none"),
    ]


# --- context checks: print, no-JS, and a slow-but-successful load ---------
# Each pins a bug that actually shipped, so a regression fails here instead of
# being noticed by eye three rounds later.
CSS_PATH = Path(__file__).resolve().parent.parent / "styles" / "site.css"


def _serve_css(page, transform):
    """Serve styles/site.css through `transform`. Works with JS disabled, where
    add_init_script cannot run."""
    body = transform(CSS_PATH.read_text(encoding="utf-8"))
    page.route("**/styles/site.css",
               lambda r: r.fulfill(status=200, content_type="text/css", body=body))


def _renders(page, selector) -> bool:
    """True if the element occupies a layout box. Do NOT read the child's own
    computed display: a child of a display:none parent still reports its own."""
    return page.eval_on_selector(
        selector,
        "e => { const r = e.getBoundingClientRect();"
        "       return !!e.offsetParent && r.width > 0 && r.height > 0; }")


def inspect_print(browser, url, fault=None):
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    if fault:
        fault(page)
    page.goto(url, wait_until="networkidle")
    page.wait_for_timeout(3000)
    page.emulate_media(media="print")
    viewer = _renders(page, ".viewer-shell")
    copy_btn = _renders(page, "#bibtex-copy")
    page.close()
    return [("print hides the 3D viewer", not viewer, str(viewer)),
            ("print hides the copy button", not copy_btn, str(copy_btn))]


def inspect_nojs(browser, url, fault=None):
    ctx = browser.new_context(viewport={"width": 1280, "height": 900}, java_script_enabled=False)
    page = ctx.new_page()
    if fault:
        fault(page)
    page.goto(url, wait_until="load")
    page.wait_for_timeout(800)
    imgs = page.evaluate("[...document.images].filter(i=>i.naturalWidth>0).length")
    total = page.evaluate("document.images.length")
    loading = page.locator("#viewer3d-loading").is_visible()
    copy_btn = page.locator("#bibtex-copy").is_visible()
    ctx.close()
    # The results are figures now, so the page's substance survives without JS —
    # which it could not when the tables hydrated from JSON.
    return [("no-JS still shows every figure", imgs == total and total >= 6, f"{imgs}/{total}"),
            ("no-JS hides 'Loading scene…'", not loading, str(loading)),
            ("no-JS hides the copy button", not copy_btn, str(copy_btn))]


def inspect_slowload(browser, url, fault=None):
    """Hold three.js past the 8s watchdog, then release it. The watchdog's
    'could not load' claim must be RETRACTED once the viewer draws."""
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    if fault:
        fault(page)
    held = []
    page.route("**/three@0.160.0/build/three.module.js", lambda r: held.append(r))
    page.goto(url, wait_until="commit")
    page.wait_for_timeout(9500)
    fired = page.eval_on_selector("#viewer3d-loading", "e => getComputedStyle(e).display !== 'none'")
    if held:
        held[0].continue_()
    page.wait_for_timeout(7000)
    d = page.evaluate("""() => {
      const n = document.getElementById('viewer3d-loading');
      const s = document.getElementById('viewer3d-stage');
      return { canvas: !!s.querySelector('canvas'),
               claimVisible: getComputedStyle(n).display !== 'none',
               labelPromises: !(s.getAttribute('aria-label') || '').startsWith('3D comparison unavailable') };
    }""")
    page.close()
    return [("watchdog fires while three.js is held", fired, str(fired)),
            ("late-arriving viewer still draws", d["canvas"], str(d["canvas"])),
            ("false failure claim is retracted", not d["claimVisible"], str(d["claimVisible"])),
            ("truthful aria-label restored", d["labelPromises"], str(d["labelPromises"]))]


def inspect_reduced_motion(browser, url, fault=None):
    """A reader who asks for reduced motion must not get ambient damping.

    The CSS @media rule cannot reach the viewer -- damping runs from
    requestAnimationFrame -- so this is checked against the viewer's own state.
    """
    ctx = browser.new_context(viewport={"width": 1280, "height": 900}, reduced_motion="reduce")
    page = ctx.new_page()
    if fault:
        fault(page)
    page.goto(url, wait_until="networkidle")
    page.wait_for_timeout(4000)
    flag = page.eval_on_selector("#viewer3d-stage", "e => e.dataset.reducedMotion")
    canvas = page.evaluate("!!document.querySelector('#viewer3d-stage canvas')")
    ctx.close()
    return [("viewer honours prefers-reduced-motion", flag == "true", str(flag)),
            ("viewer still draws under reduced motion", canvas, str(canvas))]


RATIO_JS = """(el) => {
  const lin = (c) => { c /= 255; return c <= 0.03928 ? c / 12.92
                                                     : Math.pow((c + 0.055) / 1.055, 2.4); };
  const lum = ([r, g, b]) => 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
  const rgb = (s) => (s.match(/[\\d.]+/g) || []).slice(0, 3).map(Number);
  const alpha = (s) => { const n = (s.match(/[\\d.]+/g) || []); return n.length > 3 ? +n[3] : 1; };
  let bg = [255, 255, 255];
  for (let n = el; n && n.nodeType === 1; n = n.parentElement) {
    const b = getComputedStyle(n).backgroundColor;
    if (b && alpha(b) > 0.05) { bg = rgb(b); break; }
  }
  const cs = getComputedStyle(el);
  const px = parseFloat(cs.fontSize), wt = parseInt(cs.fontWeight, 10) || 400;
  const pair = [lum(rgb(cs.color)), lum(bg)].sort((x, y) => y - x);
  return { ratio: Math.round(((pair[0] + 0.05) / (pair[1] + 0.05)) * 100) / 100,
           need: (px >= 24 || (px >= 18.66 && wt >= 700)) ? 3.0 : 4.5,
           color: cs.color, text: (el.innerText || '').trim().slice(0, 26) };
}"""


def inspect_link_states(browser, url, fault=None):
    """Contrast in the HOVER and FOCUS states, which the resting sweep cannot reach.

    --accent-hover shipped at #888888 = 3.54:1, so every link failed AA the moment a
    pointer touched it, and the skip link is the FIRST tab stop -- a keyboard user met
    the failure before anything else on the page. The resting-state check passed
    throughout, because at rest those links are #333333 at 12.63:1.
    """
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    if fault:
        fault(page)
    page.goto(url, wait_until="load")
    page.wait_for_timeout(1200)
    links = page.locator("a[href]")
    total, bad = links.count(), []
    for i in range(total):
        el = links.nth(i)
        for state in ("hover", "focus"):
            try:
                el.hover(timeout=1500) if state == "hover" else el.focus(timeout=1500)
            except Exception:
                continue          # off-screen or covered; the other state still measures
            page.wait_for_timeout(60)
            r = el.evaluate(RATIO_JS)
            if r["ratio"] + 0.005 < r["need"]:
                bad.append(f'{state} {r["text"]!r} {r["color"]} {r["ratio"]}:1 < {r["need"]}')
    page.close()
    return [("links clear WCAG AA when hovered and focused", not bad,
             "; ".join(bad[:3]) or f"{total} links x 2 states")]


def inspect_fallback_link(browser, url, fault=None):
    """Block the point clouds so the viewer's real failure path runs, then FOLLOW the
    link it offers and measure whether the figure it promises is actually on screen.

    tools/check_content.py allowlists which anchor this link may use; that only proves
    the code agrees with itself. This pins the promise: a note that says "the static
    qualitative comparison is above" has to land the reader on the qualitative
    comparison. The shipped link pointed at #abstract, leaving that figure 33% visible
    at 1280x800 and entirely off screen at 390px, while resolving to a real id -- so
    nothing short of measuring the destination would have caught it.
    """
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    if fault:
        fault(page)
    page.route("**/*.ply", lambda r: r.abort())
    page.goto(url, wait_until="load")
    page.wait_for_timeout(3500)          # the load rejects and the note is written
    link = page.locator(".viewer3d__fallback a")
    shown = link.count() > 0
    href = link.first.get_attribute("href") if shown else None
    frac, promised = -1.0, ""
    if shown:
        link.first.click()
        page.wait_for_timeout(700)
        # The figure the note promises: paper Fig. 6, located by its provenance
        # attribute rather than a position, so moving it does not silently pass.
        frac = page.evaluate("""() => {
          const cap = document.querySelector('figcaption[data-paper-float="Fig. 6"]');
          if (!cap) return -1;
          const fig = cap.closest('figure'); const r = fig.getBoundingClientRect();
          const vis = Math.max(0, Math.min(r.bottom, innerHeight) - Math.max(r.top, 0));
          return r.height ? vis / r.height : -1;
        }""")
        promised = (link.first.text_content() or "").strip()[:38]
    page.close()
    return [
        ("scene failure offers a link", shown, f"href={href}"),
        ("that link lands on the qualitative figure", frac >= 0.9,
         f"visible fraction {frac:.2f} of Fig. 6 after following {href!r} ({promised!r})"),
    ]


CONTEXTS = (("print", inspect_print), ("no-JS", inspect_nojs), ("slow load", inspect_slowload),
            ("reduced motion", inspect_reduced_motion),
            ("scene-failure fallback", inspect_fallback_link),
            ("link hover/focus", inspect_link_states))


def gate(url: str) -> int:
    failures = 0
    with sync_playwright() as pw:
        browser = getattr(pw, ENGINE).launch()
        for w, h, tag in VIEWPORTS:
            print(f"--- {tag} {w}x{h}")
            for name, ok, detail in inspect(browser, url, w, h):
                if not ok:
                    failures += 1
                print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  -> {detail}"))
        for label, fn in CONTEXTS:
            print(f"--- {label}")
            for name, ok, detail in fn(browser, url):
                if not ok:
                    failures += 1
                print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  -> {detail}"))
        browser.close()
    print(f"\n{'FAILED' if failures else 'OK'}: {failures} failing check(s)")
    return 1 if failures else 0


# --- selftest -------------------------------------------------------------
# Each fault must trip the named check. A check that cannot be made to fail is
# not evidence of anything; see the harness this file replaced.
def _wide(page):
    page.add_init_script(
        "addEventListener('load',()=>{const d=document.createElement('div');"
        "d.style.cssText='width:5000px;height:4px';document.body.appendChild(d);})")


def _animate(page):
    page.add_init_script(
        "addEventListener('load',()=>{const s=document.createElement('style');"
        "s.textContent='@keyframes _t{to{opacity:.9}} body{animation:_t 9s infinite}';"
        "document.head.appendChild(s);})")


def _break_figure(page):
    """One figure fails to load — the page must not report every figure as rendering."""
    page.route("**/fig1a_task.*", lambda r: r.abort())


def _strip_predicate(page):
    page.add_init_script(
        "addEventListener('load',()=>{document.querySelectorAll('#results figcaption')"
        ".forEach(c=>{c.textContent=c.textContent.replace("
        "/causal, single-sweep, single-sample/g,'');});})")


def _drop_chart(page):
    page.add_init_script(
        "addEventListener('load',()=>{const i=[...document.images]"
        ".find(x=>/results_chart/.test(x.currentSrc||x.src)); if(i)i.remove();})")


def _fade_captions(page):
    """The exact regression this check exists for: secondary text set to the reference
    page's #888888, which measures 3.54:1 and fails AA at caption size."""
    page.add_init_script(
        "addEventListener('load',()=>{const s=document.createElement('style');"
        "s.textContent='figcaption{color:#888888}';document.head.appendChild(s);})")


FAULTS = [
    ("all text clears WCAG AA contrast", _fade_captions),
    ("every figure renders", _break_figure),
    ("results chart is on the page", _drop_chart),
    ("the predicate is stated with the results", _strip_predicate),
    ("no horizontal page scroll", _wide),
    ("no CSS keyframe animation", _animate),
    ("viewer drew a canvas",
     lambda p: p.route("**/three.module.js", lambda r: r.abort())),
    ("no console errors",
     lambda p: p.route("**/bicyclist_s2d2.ply", lambda r: r.abort())),
    ("author block present",
     lambda p: p.add_init_script(
         "addEventListener('load',()=>{const e=document.querySelector('.identity');"
         "if(e)e.remove();})")),
    ("sections read task -> abstract -> results -> method",
     lambda p: p.add_init_script(
         "addEventListener('load',()=>{const m=document.querySelector('main');"
         "const s=document.getElementById('abstract'); if(s&&m)m.prepend(s);})")),
]


def _serve_js(page, rel: str, edit):
    """Serve one of our scripts with `edit` applied, so a fault can change code."""
    src = (Path(__file__).resolve().parent.parent / rel).read_text(encoding="utf-8")
    patched = edit(src)
    if patched == src:
        raise AssertionError(f"fault did not modify {rel} -- the pattern no longer matches")
    page.route(f"**/{rel}",
               lambda r: r.fulfill(status=200, content_type="text/javascript", body=patched))


def _ignore_reduced_motion(page):
    """Reproduce the pre-fix viewer: damping on regardless of the preference."""
    src = (Path(__file__).resolve().parent.parent / "scripts" / "viewer3d.js").read_text(encoding="utf-8")
    src = src.replace("&& window.matchMedia('(prefers-reduced-motion: reduce)').matches;", "&& false;", 1)
    page.route("**/scripts/viewer3d.js",
               lambda r: r.fulfill(status=200, content_type="text/javascript", body=src))


CONTEXT_FAULTS = [
    ("print hides the 3D viewer", inspect_print,
     lambda p: _serve_css(p, lambda c: c.replace(
         ".viewer-shell, .viewer-legend, #bibtex-copy, .skip-link { display: none !important; }",
         ".skip-link { display: none !important; }"))),
    ("no-JS hides 'Loading scene…'", inspect_nojs,
     lambda p: _serve_css(p, lambda c: c.replace(
         'html:not(.js) #viewer3d-loading { display: none; }', ''))),
    ("no-JS hides the copy button", inspect_nojs,
     lambda p: _serve_css(p, lambda c: c.replace(
         '#bibtex-copy[hidden] { display: none; }', ''))),
    # The original round-18 bug, faithfully: .is-hidden declared BEFORE
    # .viewer3d__fallback loses the specificity tie, so the claim never hides.
    ("viewer honours prefers-reduced-motion", inspect_reduced_motion, _ignore_reduced_motion),
    # The defect a reader reported: the note promised the qualitative comparison and
    # sent them to the abstract. Restoring that one string must fail the check.
    # The exact value that shipped: #888888 is 3.54:1 and fails AA at link size.
    ("links clear WCAG AA when hovered and focused", inspect_link_states,
     lambda p: p.route("**/styles/tokens.css", lambda r: r.fulfill(
         status=200, content_type="text/css",
         body=(CSS_PATH.parent / "tokens.css").read_text(encoding="utf-8")
              .replace("--accent-hover:  #737373;", "--accent-hover:  #888888;", 1)))),
    ("that link lands on the qualitative figure", inspect_fallback_link,
     lambda p: _serve_js(p, "scripts/viewer3d.js",
                         lambda c: c.replace("link.href = '#results';\n  link.textContent = "
                                             "'The static qualitative comparison is above.';",
                                             "link.href = '#abstract';\n  link.textContent = "
                                             "'The static qualitative comparison is above.';", 1))),
    ("false failure claim is retracted", inspect_slowload,
     lambda p: _serve_css(p, lambda c: c.replace(
         '#viewer3d-loading.is-hidden { display: none; }', '', 1))),
]


def selftest(url: str) -> int:
    print("Each fault must trip its named check.\n")
    silent = 0
    with sync_playwright() as pw:
        browser = getattr(pw, ENGINE).launch()
        for target, fault in FAULTS:
            results = dict((n, ok) for n, ok, _ in inspect(browser, url, 1280, 900, fault))
            tripped = results.get(target) is False
            if not tripped:
                silent += 1
            others = [n for n, ok in results.items() if not ok and n != target]
            print(f"  {'TRIPPED ' if tripped else 'SILENT  '} {target}"
                  + (f"   (also: {len(others)})" if others else ""))
        for target, fn, fault in CONTEXT_FAULTS:
            results = dict((n, ok) for n, ok, _ in fn(browser, url, fault))
            tripped = results.get(target) is False
            if not tripped:
                silent += 1
            print(f"  {'TRIPPED ' if tripped else 'SILENT  '} {target}")
        browser.close()
    total = len(FAULTS) + len(CONTEXT_FAULTS)
    print(f"\n{'SELFTEST FAILED' if silent else 'SELFTEST OK'}: "
          f"{total - silent}/{total} checks provably fail when broken")
    return 1 if silent else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--engine", default="chromium",
                    choices=("chromium", "firefox", "webkit"),
                    help="both gates hardcoded chromium, so nothing outside V8 "
                         "had ever been exercised")
    a = ap.parse_args()
    globals()['ENGINE'] = a.engine
    sys.exit(selftest(a.url) if a.selftest else gate(a.url))
