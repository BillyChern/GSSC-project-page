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

39 assertions: 10 x 3 viewports, plus print, no-JS and slow-load contexts. ~40s;
--selftest ~2min, because the slow-load check must outwait an 8s watchdog twice.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

DEFAULT_URL = "http://localhost:8099/"
VIEWPORTS = ((1280, 900, "desktop"), (768, 1024, "tablet"), (375, 812, "mobile"))

# Author identifiers that must not survive anonymous mode. Word-boundary matched:
# an unanchored search hits "Ge" inside "Generative" and manufactures failures.
IDENTIFIERS = ("Chen", "Shi", "Weifeng", "Fudan", "billychern")

PROBE = """() => {
  const q = (s) => document.querySelector(s);
  const identity = q('.identity');
  const legend = q('#viewer3d-stat-row');
  const excluded = q('#main-results-body tr.excluded td');
  return {
    hscroll: document.documentElement.scrollWidth > document.documentElement.clientWidth,
    resultRows: document.querySelectorAll('#main-results-body tr').length,
    perclassRows: document.querySelectorAll('#perclass-body tr').length,
    // CSS keyframes only. rAF render loops and transitions are NOT counted, so this
    // pins the corpus "no animation" convention, not the absence of all motion.
    cssAnimations: [...document.querySelectorAll('*')]
      .filter((e) => getComputedStyle(e).animationName !== 'none').length,
    canvas: !!q('#viewer3d-stage canvas'),
    // getComputedStyle(null) throws, which previously killed the whole measurement
    // into a traceback instead of a named failure.
    identityPresent: !!identity,
    legendText: legend ? legend.innerText.replace(/\\s+/g, ' ').trim() : null,
    excludedFontStyle: excluded ? getComputedStyle(excluded).fontStyle : null,
    stageLabel: (q('#viewer3d-stage') || {}).ariaLabel
                || (q('#viewer3d-stage') ? q('#viewer3d-stage').getAttribute('aria-label') : null),
  };
}"""


def anon_leaks(page) -> list[str]:
    """Identifiers still visible after switching to anonymous mode."""
    page.evaluate("document.body.dataset.anon = 'true'")
    page.wait_for_timeout(150)
    text = page.evaluate("document.body.innerText")
    leaks = [i for i in IDENTIFIERS if re.search(rf"\b{i}\b", text, re.I)]
    page.evaluate("document.body.dataset.anon = 'false'")
    return leaks


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
    leaks = anon_leaks(page) if d["identityPresent"] else ["<.identity missing>"]
    page.close()

    legend = d["legendText"] or ""
    return [
        ("results table has 19 rows", d["resultRows"] == 19, str(d["resultRows"])),
        ("per-class table has 21 rows", d["perclassRows"] == 21, str(d["perclassRows"])),
        ("no horizontal page scroll", not d["hscroll"], str(d["hscroll"])),
        ("no CSS keyframe animation", d["cssAnimations"] == 0, str(d["cssAnimations"])),
        ("viewer drew a canvas", d["canvas"], str(d["canvas"])),
        ("author block present", d["identityPresent"], str(d["identityPresent"])),
        ("anon mode leaks no identifiers", not leaks, ", ".join(leaks) or "none"),
        ("viewer legend discloses N=4 +D4 TTA",
         "D4 TTA" in legend and "predicate" in legend, legend[-58:] or "<empty>"),
        ("excluded rows are italic", d["excludedFontStyle"] == "italic", str(d["excludedFontStyle"])),
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
    notes = page.locator("tbody.nojs-note").first.is_visible()
    rows = page.locator("#main-results-body tr").count()
    loading = page.locator("#viewer3d-loading").is_visible()
    copy_btn = page.locator("#bibtex-copy").is_visible()
    ctx.close()
    return [("no-JS explains the empty tables", notes and rows == 0, f"notes={notes} rows={rows}"),
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


CONTEXTS = (("print", inspect_print), ("no-JS", inspect_nojs), ("slow load", inspect_slowload))


def gate(url: str) -> int:
    failures = 0
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
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


FAULTS = [
    ("results table has 19 rows",
     lambda p: p.route("**/data/results.json",
                       lambda r: r.fulfill(status=200, content_type="application/json",
                                           body='{"rows":[]}'))),
    ("per-class table has 21 rows",
     lambda p: p.route("**/data/perclass.json", lambda r: r.abort())),
    ("no horizontal page scroll", _wide),
    ("no CSS keyframe animation", _animate),
    ("viewer drew a canvas",
     lambda p: p.route("**/three.module.js", lambda r: r.abort())),
    ("no console errors",
     lambda p: p.route("**/bicyclist_s2d2.ply", lambda r: r.abort())),
    ("viewer legend discloses N=4 +D4 TTA",
     lambda p: p.add_init_script(
         "addEventListener('load',()=>{const e=document.querySelector('#viewer3d-stat-row .faint');"
         "if(e)e.remove();})")),
    ("excluded rows are italic",
     lambda p: p.add_init_script(
         "addEventListener('load',()=>{const s=document.createElement('style');"
         "s.textContent='tbody tr.excluded td{font-style:normal!important}';"
         "document.head.appendChild(s);})")),
    ("anon mode leaks no identifiers",
     lambda p: p.add_init_script(
         "addEventListener('load',()=>{const p=document.createElement('p');"
         "p.textContent='Shi Chen';document.body.appendChild(p);})")),
    ("author block present",
     lambda p: p.add_init_script(
         "addEventListener('load',()=>{const e=document.querySelector('.identity');"
         "if(e)e.remove();})")),
]


CONTEXT_FAULTS = [
    ("print hides the 3D viewer", inspect_print,
     lambda p: _serve_css(p, lambda c: c.replace(
         ".viewer-shell, .viewer-legend, .anon-ctl, #bibtex-copy, .skip-link { display: none !important; }",
         ".skip-link { display: none !important; }"))),
    ("no-JS hides 'Loading scene…'", inspect_nojs,
     lambda p: _serve_css(p, lambda c: c.replace(
         'html:not(.js) #viewer3d-loading { display: none; }', ''))),
    ("no-JS hides the copy button", inspect_nojs,
     lambda p: _serve_css(p, lambda c: c.replace(
         '#bibtex-copy[hidden] { display: none; }', ''))),
    # The original round-18 bug, faithfully: .is-hidden declared BEFORE
    # .viewer3d__fallback loses the specificity tie, so the claim never hides.
    ("false failure claim is retracted", inspect_slowload,
     lambda p: _serve_css(p, lambda c: c.replace(
         '#viewer3d-loading.is-hidden { display: none; }', '', 1))),
]


def selftest(url: str) -> int:
    print("Each fault must trip its named check.\n")
    silent = 0
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
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
    a = ap.parse_args()
    sys.exit(selftest(a.url) if a.selftest else gate(a.url))
