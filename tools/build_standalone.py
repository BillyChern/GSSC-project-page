#!/usr/bin/env python3
"""Build a single self-contained HTML file from the site, for private preview hosting.

The published page must survive a strict Content-Security-Policy that blocks every
external host except Google Fonts, and it has no sibling files to fetch. So every
stylesheet, script, JSON table, PLY point cloud and figure is folded into one document.

Design note: this changes NOTHING visual. The site already carries a measured design
system in styles/tokens.css; a preview that diverged from it would be a new drift
surface, which is the opposite of the point. The only substantive difference is that
the <picture> elements collapse to their WebP source — every browser that can open the
preview supports WebP, and carrying the PNG fallbacks as well would double the file.

Two mechanisms do the heavy lifting without touching a line of application logic:
  * fetch() accepts data: URLs, so data/*.json and assets/ply/*.ply are rewritten in
    place and main.js / viewer3d.js keep their existing loaders, error handling and
    failure states.
  * an import map can point bare specifiers at data: URLs, so three.js and its two
    addons are vendored without bundling or rewriting their imports.

If the host CSP refuses data: URLs for modules, the viewer degrades to the failure
state the page already implements (a note pointing at the static qualitative figure)
rather than breaking silently. That path is gated by tools/check_page.py.

Usage:
    python tools/build_standalone.py [-o out.html]
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
THREE = "0.160.0"
CDN = {
    "three": f"https://unpkg.com/three@{THREE}/build/three.module.js",
    "three/addons/controls/OrbitControls.js":
        f"https://unpkg.com/three@{THREE}/examples/jsm/controls/OrbitControls.js",
    "three/addons/loaders/PLYLoader.js":
        f"https://unpkg.com/three@{THREE}/examples/jsm/loaders/PLYLoader.js",
}


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def data_uri(data: bytes, mime: str) -> str:
    return f"data:{mime};base64,{b64(data)}"


def fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read()


def bundle_viewer() -> str:
    """Resolve viewer3d.js's three.js imports into one self-contained ES module."""
    out = SITE / ".tmp" / "viewer_bundle.js"
    out.parent.mkdir(parents=True, exist_ok=True)
    esbuild = SITE / "node_modules" / ".bin" / "esbuild"
    if not esbuild.exists():
        sys.exit("esbuild not installed: npm install --no-save esbuild three@0.160.0")
    subprocess.run([str(esbuild), str(SITE / "scripts" / "viewer3d.js"), "--bundle",
                    "--format=esm", "--alias:three/addons=three/examples/jsm",
                    f"--outfile={out}"], cwd=SITE, check=True, capture_output=True)
    code = out.read_text(encoding="utf-8")
    if "unpkg.com" in code:
        sys.exit("bundle still references unpkg")
    return code


def build(artifact: bool = False) -> str:
    html = (SITE / "index.html").read_text(encoding="utf-8")

    # --- stylesheets -----------------------------------------------------
    css = "\n".join((SITE / "styles" / n).read_text(encoding="utf-8")
                    for n in ("tokens.css", "site.css"))
    for name in ("tokens.css", "site.css"):
        pat = f'<link rel="stylesheet" href="styles/{name}" />'
        if pat not in html:
            sys.exit(f"stylesheet link not found: {name}")
        html = html.replace(pat, "" if name == "site.css" else "@@CSS@@", 1)

    # url() inside the CSS is a relative reference too, and it was NOT being inlined:
    # the @font-face for CMU Serif reads url('../assets/fonts/cmu-serif-roman.woff2'),
    # so every heading in the built file silently fell back to the body sans while the
    # build reported success. The leftover-reference guard below could not see it
    # either -- it matched only "assets/..." in DOUBLE quotes, and this is a
    # single-quoted ../ path inside url(). Both halves are fixed: rewrite here, and
    # widen the guard so a url() can never slip through again.
    def inline_css_url(m: re.Match) -> str:
        ref = m.group("ref").strip()
        if ref.startswith(("data:", "http:", "https:", "//", "#")):
            return m.group(0)
        target = (SITE / "styles" / ref).resolve()
        if not target.is_file():
            sys.exit(f"css url() points at a missing file: {ref}")
        mime = {".woff2": "font/woff2", ".woff": "font/woff", ".ttf": "font/ttf",
                ".png": "image/png", ".webp": "image/webp", ".jpg": "image/jpeg",
                ".svg": "image/svg+xml"}.get(target.suffix.lower())
        if not mime:
            sys.exit(f"css url() has no known mime type: {ref}")
        return f"url({data_uri(target.read_bytes(), mime)})"

    css, n_url = re.subn(r"""url\(\s*['"]?(?P<ref>[^'")]+)['"]?\s*\)""", inline_css_url, css)
    if n_url < 1:
        sys.exit("expected at least the CMU Serif @font-face url() in the CSS, found none")

    html = html.replace("@@CSS@@", "<style>\n" + css + "\n</style>")

    # --- three.js: BUNDLED, not import-mapped -----------------------------
    # An earlier revision repointed the import map at data: URLs. That worked under a
    # CSP that allows data: in script-src -- but import-map addresses are fetched under
    # script-src, and the host policy is not ours to see, so the viewer's survival was
    # riding on a guess about someone else's header. Bundling removes the question:
    # the module graph becomes one inline script, which any policy permitting inline
    # code will run. Deleting the import map is what makes the guess irrelevant.
    old_map = re.search(r'<script type="importmap">.*?</script>', html, re.S)
    if not old_map:
        sys.exit("import map not found")
    html = html.replace(old_map.group(0), "", 1)

    # The page no longer fetches JSON at runtime: the results are a generated figure
    # (tools/make_results_chart.py), so there is nothing to inline here. data/*.json
    # remains the source of truth for that chart and is gated in check_content.py.

    # --- scripts ---------------------------------------------------------
    def inline_script(src_attr: str, path: str, module: bool = False) -> None:
        nonlocal html
        code = (SITE / path).read_text(encoding="utf-8")
        if path == "scripts/viewer3d.js":
            code = bundle_viewer()
        if path == "scripts/viewer3d.js":
            # The point clouds travel INSIDE the script, as string data, not as data:
            # URIs. A data: URI is still fetch()ed by three's FileLoader, and a fetch
            # is judged by connect-src -- not img-src. The published host does not
            # admit data: under connect-src, so every scene failed there while the
            # figures and the webfont (img-src / font-src) were fine, and the served
            # page was healthy throughout. Measured in tools/check_artifact.py.
            # Quote-agnostic: esbuild normalises single-quoted literals to double
            # quotes, so matching only "'path'" silently rewrote nothing.
            embedded: dict[str, str] = {}
            for ply in sorted((SITE / "assets" / "ply").glob("*.ply")):
                rel = f"assets/ply/{ply.name}"
                key = f"gssc-embedded:{ply.name}"   # not a path, so the guard below stays strict
                hit = False
                for q in ("'", '"'):
                    if f"{q}{rel}{q}" in code:
                        code = code.replace(f"{q}{rel}{q}", f"{q}{key}{q}"); hit = True
                if not hit:
                    sys.exit(f"PLY reference not found in viewer code: {rel}")
                text = ply.read_text(encoding="utf-8")
                if not text.lstrip().startswith("ply"):
                    sys.exit(f"not a PLY file: {rel}")
                if "format ascii" not in text[:200]:
                    sys.exit(f"{rel} is not ASCII PLY; embedding as text would corrupt it")
                embedded[key] = text
            if not embedded:
                sys.exit("no PLY clouds found to embed")
            # JSON is a subset of JS. "</" is escaped so a cloud can never terminate
            # the inline <script> that carries it.
            code = ("globalThis.__GSSC_PLY__=" + json.dumps(embedded).replace("</", "<\\/")
                    + ";\n" + code)
        tag = '<script type="module">' if module else "<script>"
        if src_attr not in html:
            sys.exit(f"script tag not found: {src_attr}")
        html = html.replace(src_attr, tag + "\n" + code + "\n</script>", 1)

    inline_script('<script src="scripts/main.js"></script>', "scripts/main.js")
    inline_script('<script type="module" src="scripts/viewer3d.js"></script>',
                  "scripts/viewer3d.js", module=True)

    # --- figures: <picture> collapses to its WebP source ------------------
    def swap_picture(m: re.Match) -> str:
        block = m.group(0)
        webp = re.search(r'srcset="([^"]+\.webp)"', block)
        img = re.search(r"<img\b[^>]*>", block)
        if not webp or not img:
            sys.exit("unrecognised <picture> block")
        tag = img.group(0)
        path = SITE / webp.group(1)
        tag = re.sub(r'src="[^"]+"', 'src="' + data_uri(path.read_bytes(), "image/webp") + '"', tag, count=1)
        return tag

    html, n = re.subn(r"<picture>.*?</picture>", swap_picture, html, flags=re.S)
    # A floor, not a fixed count: the page gains figures over time, and re.subn already
    # guarantees every block matched was rewritten. The unresolved-relative-reference
    # guard below is what actually proves nothing was left pointing at a sibling file.
    if n < 6:
        sys.exit(f"expected at least 6 <picture> blocks, rewrote {n}")

    # --- favicon ---------------------------------------------------------
    fav = SITE / "assets" / "favicon.svg"
    html = html.replace('href="assets/favicon.svg"',
                        'href="' + data_uri(fav.read_bytes(), "image/svg+xml") + '"', 1)

    if artifact:
        # Artifacts supply their own <!doctype>/<head>/<body> skeleton, so ours must go.
        # <title> is kept: the host scans the first 8 KB for it. Nothing else on
        # <body> needs re-asserting -- the author-visibility toggle that used to live
        # in a data-anon attribute has been removed -- and the 'js' class comes from
        # the inline script in the head, whose CONTENT survives this strip.
        # (?=[\s>/]) is load-bearing: r"</?head[^>]*>" also matches
        # <header class="head prose">, so this loop was DELETING the page header. The
        # h1 rule is .head h1, so with its ancestor gone the title silently lost the
        # CMU Serif display face and its 48px size -- in the published artifact only,
        # which is why the served page measured correct throughout. Requiring a tag
        # boundary after the name is what separates <head> from <header>.
        for pat in (r"<!DOCTYPE[^>]*>", r"</?html(?=[\s>/])[^>]*>",
                    r"</?head(?=[\s>/])[^>]*>", r"</?body(?=[\s>/])[^>]*>"):
            html = re.sub(pat, "", html, flags=re.I)
        # Assert the survivor, rather than trusting the regexes not to over-match again.
        # Every selector scoped to a wrapper is invisible to a substring-level strip.
        for survivor in ('<header class="head', '<main id="main"', '<footer'):
            if survivor not in html:
                sys.exit(f"artifact strip removed a required wrapper: {survivor}")

    # Two shapes of relative reference, because only checking the first one let the
    # webfont ship broken: a quoted attribute value, and a bare path inside url().
    leftovers = sorted(set(re.findall(r'"\.{0,2}/?(?:assets|styles|scripts|data)/[^"]+"', html)))
    leftovers += sorted({m for m in re.findall(r"""url\(\s*['"]?([^'")]+)['"]?\s*\)""", html)
                         if not m.strip().startswith(("data:", "http:", "https:", "//", "#"))})
    if leftovers:
        sys.exit("unresolved relative references: " + ", ".join(leftovers[:6]))
    return html


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default=str(SITE / ".tmp" / "standalone.html"))
    ap.add_argument("--artifact", action="store_true",
                    help="strip the document skeleton for hosts that supply their own")
    a = ap.parse_args()
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    doc = build(artifact=a.artifact)
    out.write_text(doc, encoding="utf-8")
    print(f"wrote {out}  ({len(doc.encode('utf-8')) / 1048576:.2f} MB)")
