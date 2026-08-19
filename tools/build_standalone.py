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
import re
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
    html = html.replace("@@CSS@@", "<style>\n" + css + "\n</style>")

    # --- three.js and addons, vendored into the import map ---------------
    imports = {spec: data_uri(fetch(url), "text/javascript") for spec, url in CDN.items()}
    old_map = re.search(r'<script type="importmap">.*?</script>', html, re.S)
    if not old_map:
        sys.exit("import map not found")
    entries = ",\n    ".join(f'"{k}": "{v}"' for k, v in imports.items())
    html = html.replace(old_map.group(0),
                        '<script type="importmap">\n{ "imports": {\n    ' + entries + '\n} }\n</script>', 1)

    # --- JSON tables: fetch() handles data: URLs, so the loader is untouched
    for name in ("results.json", "perclass.json"):
        uri = data_uri((SITE / "data" / name).read_bytes(), "application/json")
        # rewritten inside main.js below, once it is inlined
        globals().setdefault("_json", {})[f"data/{name}"] = uri

    # --- scripts ---------------------------------------------------------
    def inline_script(src_attr: str, path: str, module: bool = False) -> None:
        nonlocal html
        code = (SITE / path).read_text(encoding="utf-8")
        if path == "scripts/main.js":
            for rel, uri in globals()["_json"].items():
                if f"'{rel}'" not in code:
                    sys.exit(f"expected {rel} reference in main.js")
                code = code.replace(f"'{rel}'", f"'{uri}'")
        if path == "scripts/viewer3d.js":
            for ply in sorted((SITE / "assets" / "ply").glob("*.ply")):
                rel = f"assets/ply/{ply.name}"
                if f"'{rel}'" in code:
                    code = code.replace(f"'{rel}'", "'" + data_uri(ply.read_bytes(),
                                                                  "application/octet-stream") + "'")
        tag = '<script type="module">' if module else "<script>"
        if src_attr not in html:
            sys.exit(f"script tag not found: {src_attr}")
        html = html.replace(src_attr, tag + "\n" + code + "\n</script>", 1)

    inline_script('<script src="scripts/anon.js"></script>', "scripts/anon.js")
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
    if n != 6:
        sys.exit(f"expected 6 <picture> blocks, rewrote {n}")

    # --- favicon ---------------------------------------------------------
    fav = SITE / "assets" / "favicon.svg"
    html = html.replace('href="assets/favicon.svg"',
                        'href="' + data_uri(fav.read_bytes(), "image/svg+xml") + '"', 1)

    if artifact:
        # Artifacts supply their own <!doctype>/<head>/<body> skeleton, so ours must go.
        # <title> is kept: the host scans the first 8 KB for it. body's data-anon
        # attribute would be lost with the tag, so re-assert it in script instead --
        # the anonymity default is exactly the kind of thing that must not drift.
        body_attrs = re.search(r"<body([^>]*)>", html)
        anon = re.search(r'data-anon="([a-z]+)"', body_attrs.group(1) if body_attrs else "")
        for pat in (r"<!DOCTYPE[^>]*>", r"</?html[^>]*>", r"</?head[^>]*>", r"</?body[^>]*>"):
            html = re.sub(pat, "", html, flags=re.I)
        if anon:
            html = html.replace("</style>", "</style>\n<script>document.documentElement.classList.add('js');"
                                f"addEventListener('DOMContentLoaded',()=>{{document.body.dataset.anon='{anon.group(1)}';}});</script>", 1)

    if "assets/" in html or "styles/" in html or "scripts/" in html or "data/" in html:
        leftovers = sorted(set(re.findall(r'"(?:assets|styles|scripts|data)/[^"]+"', html)))
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
