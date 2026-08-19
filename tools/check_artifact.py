#!/usr/bin/env python3
"""Gate the BUILT single-file page, under a deliberately harsh Content-Security-Policy.

Why this exists as a third gate. check_page.py loads http://localhost:8099/ and
check_content.py reads the source tree -- both measure the INPUT to
tools/build_standalone.py, never its output. Every defect the build itself introduces
lives in that blind spot, and three have shipped from it:

  * the @font-face url() was never inlined, so the built file lost its display face;
  * the artifact-mode tag strip matched <header ...> as well as <head>, deleting the
    page header and with it the .head h1 rule;
  * the 3D viewer fetched its point clouds from data: URIs, which is governed by
    connect-src, not img-src -- so under the host policy every scene failed to load
    while figures and fonts were fine.

All three were invisible to both existing gates, and the first two were invisible to a
screenshot as well. So this file asserts on the artifact as PUBLISHED.

The CSP used here is deliberately harsher than the documented one: connect-src 'none',
no network of any kind. The published page must not depend on a policy we cannot read.
If it renders here, it renders there.

Usage:
    python tools/check_artifact.py             # gate the built file
    python tools/check_artifact.py --selftest  # prove every check can fail
"""
from __future__ import annotations

import argparse
import re
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

ENGINE = "chromium"

SITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SITE / "tools"))
SERVED_URL = "http://localhost:8099/"

# No network at all. Inline script and style only; data: for the assets that are
# fetched by the parser (images, fonts) but NOT for connect-src.
# Google Fonts IS documented as permitted, so blocking it here would manufacture a
# failure that says nothing about the artifact. connect-src stays at 'none': that is
# the directive the host actually withholds, and the page must not need it.
HARSH_CSP = ("default-src 'none'; img-src data: blob:; "
             "style-src 'unsafe-inline' https://fonts.googleapis.com; "
             "font-src data: https://fonts.gstatic.com; "
             "script-src 'unsafe-inline' 'unsafe-eval'; connect-src 'none'")

PROBE = """() => {
  const stage = document.querySelector('#viewer3d-stage');
  const q = (s) => document.querySelector(s);
  return {
    // The viewer's own signals. dataset.vertices is set only after a cloud parses
    // above the MIN_VERTICES floor, so it is a measurement of geometry rather than
    // an inference from "a canvas exists" -- a canvas exists even when every scene
    // failed, which is exactly how this shipped broken.
    vertices: stage ? parseInt(stage.dataset.vertices || '0', 10) : -1,
    fallback: !!document.querySelector('.viewer3d__fallback'),
    canvas: !!(stage && stage.querySelector('canvas')),
    headerPresent: !!q('header.head') && !!q('header.head h1'),
    h1Font: q('header.head h1') ? getComputedStyle(q('header.head h1')).fontFamily : '',
    // Declaring the family is NOT using it: getComputedStyle keeps reporting
    // "CMU Serif" when the @font-face failed to load and the text is actually
    // rendering in the fallback. The selftest caught that -- the fault that breaks
    // the font left this check passing. FontFace.status is the direct measurement.
    displayFaceLoaded: [...document.fonts].some(
      (f) => f.family.replace(/["']/g, '') === 'CMU Serif' && f.status === 'loaded'),
    h1Size: q('header.head h1') ? getComputedStyle(q('header.head h1')).fontSize : '',
    imagesTotal: document.images.length,
    imagesLoaded: [...document.images].filter((i) => i.naturalWidth > 0).length,
    sectionOrder: [...document.querySelectorAll('main > section')].map((s) => s.id),
    bodyFont: getComputedStyle(document.body).fontFamily,
    capColor: q('figcaption') ? getComputedStyle(q('figcaption')).color : '',
  };
}"""


def build_artifact() -> str:
    import build_standalone
    return build_standalone.build(artifact=True)


def render(browser, doc: str, csp: str = HARSH_CSP) -> tuple[dict, list[str]]:
    """Load `doc` wrapped in the skeleton the host supplies, under `csp`."""
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "artifact.html"
        f.write_text(
            "<!doctype html><html><head><meta charset='utf-8'>"
            f"<meta http-equiv='Content-Security-Policy' content=\"{csp}\">"
            f"</head><body>{doc}</body></html>", encoding="utf-8")
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        console: list[str] = []
        page.on("console", lambda m: console.append(f"{m.type}: {m.text}") if m.type == "error" else None)
        page.on("pageerror", lambda e: console.append(f"pageerror: {e}"))
        page.goto(f.as_uri(), wait_until="load")
        page.wait_for_timeout(9000)   # the viewer boots, parses a cloud, and draws
        d = page.evaluate(PROBE)
        page.close()
    return d, console


def served(browser) -> dict | None:
    """The same measurements on the served page, for a parity comparison."""
    try:
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(SERVED_URL, wait_until="networkidle", timeout=15000)
        page.wait_for_timeout(6000)
        d = page.evaluate(PROBE)
        page.close()
        return d
    except Exception:
        return None


def checks(d: dict, console: list[str], ref: dict | None) -> list[tuple[str, bool, str]]:
    out = [
        # The headline assertion. Under a policy with no network, the scene must still
        # draw -- which is only possible if its geometry travels inside the document.
        ("viewer renders a scene with no network",
         d["vertices"] >= 64 and not d["fallback"],
         f'vertices={d["vertices"]} fallback={d["fallback"]} canvas={d["canvas"]}'),
        ("page header survived the artifact strip",
         d["headerPresent"], str(d["headerPresent"])),
        ("title keeps the display face",
         "CMU Serif" in d["h1Font"] and d["displayFaceLoaded"],
         f'declared={d["h1Font"][:34]!r} actuallyLoaded={d["displayFaceLoaded"]} @ {d["h1Size"]}'),
        ("every figure renders",
         d["imagesLoaded"] == d["imagesTotal"] and d["imagesTotal"] >= 6,
         f'{d["imagesLoaded"]}/{d["imagesTotal"]}'),
        ("no console errors", not console, "; ".join(c[:80] for c in console[:2]) or "none"),
    ]
    if ref is None:
        out.append(("parity with the served page", False,
                    f"served page not reachable at {SERVED_URL} -- start it and re-run"))
    else:
        keys = ("h1Font", "h1Size", "bodyFont", "capColor", "sectionOrder", "imagesTotal")
        bad = [f'{k}: served={ref[k]!r} artifact={d[k]!r}' for k in keys if ref[k] != d[k]]
        out.append(("parity with the served page", not bad, "; ".join(bad)[:200] or "identical"))
    return out


def report(rows) -> int:
    fails = 0
    for name, ok, detail in rows:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"   ({detail})"))
        fails += not ok
    return fails


def gate() -> int:
    doc = build_artifact()
    print(f"built artifact: {len(doc.encode('utf-8')) / 1048576:.2f} MB")
    with sync_playwright() as pw:
        b = getattr(pw, ENGINE).launch()
        ref = served(b)
        d, console = render(b, doc)
        b.close()
    n = report(checks(d, console, ref))
    print(f"\n{'OK: 0 failing check(s)' if not n else f'FAILED: {n} failing check(s)'}")
    return 1 if n else 0


# --- selftest --------------------------------------------------------------
# Each fault mutates the BUILT document, which is the artefact this file gates.
def _drop_embedded_ply(doc: str) -> str:
    """The bug this gate was written for: scene data reachable only over the network."""
    return re.sub(r"globalThis\.__GSSC_PLY__=\{.*?\};\n", "globalThis.__GSSC_PLY__={};\n",
                  doc, count=1, flags=re.S)


def _eat_header(doc: str) -> str:
    """Reproduce the strip that matched <header ...> as well as <head>."""
    return doc.replace('<header class="head prose">', "", 1).replace("</header>", "", 1)


def _drop_font(doc: str) -> str:
    """Reproduce the @font-face that was never inlined."""
    return re.sub(r"src:\s*url\(data:font/woff2[^)]*\)",
                  "src: url(../assets/fonts/cmu-serif-roman.woff2)", doc, count=1)


def _break_figure(doc: str) -> str:
    return doc.replace('src="data:image/webp;base64,', 'src="data:image/webp;base64,ZZZ', 1)


FAULTS = [
    ("viewer renders a scene with no network", _drop_embedded_ply),
    ("page header survived the artifact strip", _eat_header),
    ("title keeps the display face", _drop_font),
    ("every figure renders", _break_figure),
]


def selftest() -> int:
    doc = build_artifact()
    print("Each fault must trip its named check.\n")
    missed = []
    with sync_playwright() as pw:
        b = getattr(pw, ENGINE).launch()
        ref = served(b)
        for target, fault in FAULTS:
            mutated = fault(doc)
            if mutated == doc:
                missed.append(f"{target}  (fault did not modify the document)")
                print(f"  NOT APPLIED  {target}")
                continue
            d, console = render(b, mutated)
            failed = {n for n, ok, _ in checks(d, console, ref) if not ok}
            if target in failed:
                extra = failed - {target, "no console errors"}
                print(f"  TRIPPED  {target}" + (f"   (also: {len(extra)})" if extra else ""))
            else:
                missed.append(target)
                print(f"  MISSED   {target}")
        b.close()
    total = len(FAULTS)
    print(f"\n{'SELFTEST OK' if not missed else 'SELFTEST FAILED'}: "
          f"{total - len(missed)}/{total} checks provably fail when broken")
    return 1 if missed else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--engine", default="chromium",
                    choices=("chromium", "firefox", "webkit"),
                    help="both gates hardcoded chromium, so nothing outside V8 "
                         "had ever been exercised")
    a = ap.parse_args()
    globals()['ENGINE'] = a.engine
    sys.exit(selftest() if a.selftest else gate())
