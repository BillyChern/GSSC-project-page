#!/usr/bin/env python3
"""Assert the project page's invariants, and prove the assertions can fail.

Replaces an earlier scratch script that printed a JSON report with NO assertions.
That script was read through a grep which matched `pageerror` but not `"error: ..."`,
so console errors -- including the ones this page's own failure guards emit -- were
invisible, and "no page errors" was reported off a filter that could not see them.

Each check below pins a fix that a previous round landed, so a regression fails loudly
instead of needing to be noticed by eye.

Usage:
    python tools/check_page.py                 # gate the page (exit 1 on any failure)
    python tools/check_page.py --selftest      # prove every check can fail
    python tools/check_page.py --url http://localhost:8099/
"""
from __future__ import annotations

import argparse
import re
import sys

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
        browser.close()
    print(f"\n{'SELFTEST FAILED' if silent else 'SELFTEST OK'}: "
          f"{len(FAULTS) - silent}/{len(FAULTS)} checks provably fail when broken")
    return 1 if silent else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    sys.exit(selftest(a.url) if a.selftest else gate(a.url))
