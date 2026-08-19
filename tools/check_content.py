#!/usr/bin/env python3
"""Gate the page's CONTENT against the built paper, not against its own last version.

This page is a derivative artifact. The original audit found 27 critical defects here
precisely because the page had drifted from the manuscript, so the check that matters is
site -> paper, re-runnable, because the paper keeps moving.

Two arms:

1. Provenance. Every "Source: paper Fig. N / Table X" caption claim must resolve to a
   float whose real caption is about the same thing. Moving one float to the supplement
   renumbers everything after it -- the single most likely way these citations go stale.

2. Numbers. Every numeric claim in the page prose and in data/*.json must appear in the
   paper or supplement. Two traps are handled: the PDFs write minus as U+2212, so an
   ASCII-hyphen search reports a present number missing; and `bool` is a subclass of
   `int` in Python, so JSON true/false leak into a naive numeric walk as fake claims.

Numbers rendered INSIDE images are invisible here (assets/og-card.jpg asserts fourteen);
they were checked by hand and are noted in the project memory.

Usage:
    python tools/check_content.py
    python tools/check_content.py --selftest
    python tools/check_content.py --paper /workspace/GSSC-paper/pdf
"""
from __future__ import annotations

import argparse
import html as htmllib
import json
import re
import sys
from pathlib import Path

import fitz  # PyMuPDF

SITE = Path(__file__).resolve().parent.parent
DEFAULT_PAPER = Path("/workspace/GSSC-paper/pdf")

# Words too generic to confirm that a caption and a float are about the same thing.
STOP = {"the", "a", "an", "on", "of", "and", "in", "our", "with", "for", "is", "at",
        "from", "to", "one", "two", "three", "its", "it", "as", "by", "that", "this",
        "base", "paper", "source", "fig", "table", "left", "right", "top", "bottom"}


def paper_text(paper_dir: Path) -> str:
    parts = []
    for name in ("main.pdf", "supplementary.pdf"):
        p = paper_dir / name
        if not p.exists():
            raise SystemExit(f"missing {p}; build the paper first")
        with fitz.open(p) as doc:
            parts.append("".join(page.get_text() for page in doc))
    return "".join(parts)


def normalise(text: str) -> str:
    """One spacing convention, and every dash-like character as ASCII hyphen."""
    text = text.replace("−", "-").replace("–", "-").replace("—", "-")
    return re.sub(r"[\s ]+", " ", text)


def site_prose() -> str:
    # README.md is deliberately NOT swept. It repeats result numbers, but it also
    # documents the implementation -- CSS token widths, contrast ratios, an HTTP
    # status, a port -- and requiring those to appear in the paper produced 8 false
    # failures. Muzzling them with an allowlist would put a filter in front of the
    # gate, which is where defects hide. Its result numbers duplicate the page's and
    # are swept there; they were also checked directly once (107 ms, 3.23 FPS: both
    # present). Re-check by hand if the README ever states a result the page does not.
    html = (SITE / "index.html").read_text(encoding="utf-8")
    # Drop <script>/<style> first: tag-stripping alone leaves the importmap behind, and
    # "three@0.160.0" is a dependency version, not a numeric claim about results.
    html = re.sub(r"<(script|style)\b.*?</\1>", " ", html, flags=re.S | re.I)
    return normalise(htmllib.unescape(re.sub(r"<[^>]+>", " ", html)))


def captions(html: str | None = None) -> list[tuple[str, str]]:
    """[(claimed float, the caption text that claims it)].

    The citation lives in a data-paper-float attribute, not in the visible text: a
    reader does not need "Paper Fig. 6." at the end of every caption, but the gate
    still needs something to check the caption against. Moving it to an attribute keeps
    provenance verifiable while removing the clutter — the alternative was deleting the
    citations and losing the check with them.
    """
    html = html if html is not None else (SITE / "index.html").read_text(encoding="utf-8")
    out = []
    for m in re.finditer(r"<(figcaption|caption)\b([^>]*)>(.*?)</\1>", html, re.S | re.I):
        attrs, inner = m.group(2), m.group(3)
        text = normalise(htmllib.unescape(re.sub(r"<[^>]+>", " ", inner)))
        cite = re.search(r'data-paper-float="([^"]+)"', attrs)
        if cite:
            out.append((cite.group(1).strip(), text))
            continue
        # Legacy in-text form, still accepted so a hand-written caption is not silently
        # dropped from the gate's coverage.
        legacy = re.search(r"(?:Source: paper|Paper)\s+(Fig\.\s*\d+|Table\s*[IVXL]+)", text)
        if legacy:
            out.append((re.sub(r"\s+", " ", legacy.group(1)), text))
    return out


def check_provenance(paper: str, caps) -> list[tuple[str, bool, str]]:
    results = []
    for claim, caption in caps:
        num = re.search(r"(\d+|[IVXL]+)$", claim).group(1)
        # Take a WINDOW, not up-to-the-first-period: paper captions contain "val seq. 08"
        # and "Fig. 1(a)", so a [^.] capture truncated "Qualitative comparison on val
        # seq. 08. Three frozen sources..." to four words and left nothing to match.
        if claim.startswith("Fig"):
            m = re.search(rf"Fig\.\s*{num}\.\s*(.{{6,420}})", paper, re.S)
        else:
            m = re.search(rf"TABLE\s+{num}\s+([A-Z].{{6,420}})", paper, re.S)
        if not m:
            results.append((f"{claim} exists in the paper", False, "no such float"))
            continue
        real = m.group(1)
        # Topical agreement: distinctive words shared between the site's caption lead
        # and the paper's real caption. A renumbered float lands on another topic.
        lead = set(w for w in re.findall(r"[A-Za-z]{3,}", caption.lower()) if w not in STOP)
        theirs = set(w for w in re.findall(r"[A-Za-z]{3,}", real.lower()) if w not in STOP)
        shared = lead & theirs
        ok = len(shared) >= 2
        results.append((f"{claim} is the float the caption describes", ok,
                        f"shared={sorted(shared)[:4]} real={real[:52]!r}"))
    return results


def site_numbers(extra_prose: str = "") -> set[str]:
    nums: set[str] = set()
    for m in re.finditer(r"-?\d+(?:,\d{3})*(?:\.\d+)?", site_prose() + " " + extra_prose):
        nums.add(m.group(0))

    def walk(o):
        if isinstance(o, dict):
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
        # bool is a subclass of int: without this, JSON true/false become "claims".
        elif isinstance(o, bool):
            return
        elif isinstance(o, (int, float)):
            nums.add(str(o))

    for name in ("results.json", "perclass.json"):
        walk(json.loads((SITE / "data" / name).read_text(encoding="utf-8")))
    return nums


def paper_title(paper_dir: Path) -> str | None:
    """The paper's TYPESET title, from page 1 of main.pdf.

    IEEEtran page 1 reads: running head, page number, title, authors, Abstract.
    So skip the running head and any bare page number; the next non-empty line is
    the title. This is the source of truth -- an earlier version of this check
    anchored on README.md's citation block instead, and that block carried a longer
    working title than the built paper, which is how a CORRECT BibTeX entry on the
    page got "fixed" into a wrong one. Anchor on the artifact, not on a derivative.
    """
    with fitz.open(paper_dir / "main.pdf") as doc:
        lines = [l.strip() for l in doc[0].get_text().splitlines()]
    for l in lines:
        if not l or l.upper().startswith("IEEE TRANSACTIONS") or l.isdigit():
            continue
        return normalise(l)
    return None


def _bibtex_title(text: str) -> str | None:
    m = re.search(r"title\s*=\s*\{(.*?)\}", text, re.S)
    if not m:
        return None
    return normalise(htmllib.unescape(re.sub(r"<[^>]+>", " ", m.group(1)))).strip()


def check_citation(paper_dir: Path, title_override: str | None = None) -> list[tuple[str, bool, str]]:
    """Every citation this repo hands out must name the paper as the paper names itself.

    The copy button is the one thing a reader takes away and reuses. Both the page's
    BibTeX and README.md's citation block are checked against the typeset title.
    """
    truth = paper_title(paper_dir)
    if truth is None:
        return [("paper title extracted", False, "could not read page 1")]

    html = (SITE / "index.html").read_text(encoding="utf-8")
    block = re.search(r'id="bibtex-code">(.*?)</code>', html, re.S)
    site_title = title_override if title_override is not None else (
        _bibtex_title(block.group(1)) if block else None)
    readme_title = _bibtex_title((SITE / "README.md").read_text(encoding="utf-8"))

    return [
        ("page BibTeX title is the paper's title",
         site_title is not None and site_title.lower() == truth.lower(),
         f"page={(site_title or '<none>')[:52]!r} paper={truth[:52]!r}"),
        ("README citation title is the paper's title",
         readme_title is not None and readme_title.lower() == truth.lower(),
         f"readme={(readme_title or '<none>')[:52]!r} paper={truth[:52]!r}"),
    ]


def check_chart(paper_dir: Path) -> list[tuple[str, bool, str]]:
    """The results chart replaced two HTML tables. Nothing in the DOM can now be
    asserted about the predicate, so the check moves here: the chart's manifest must
    match what data/results.json says, or the page is showing a stale picture."""
    man_path = SITE / "assets" / "figures" / "results_chart.json"
    if not man_path.exists():
        return [("results chart manifest exists", False, "run tools/make_results_chart.py")]
    manifest = json.loads(man_path.read_text(encoding="utf-8"))["rows"]
    rows = [r for r in json.loads((SITE / "data" / "results.json").read_text(encoding="utf-8"))
            if r.get("eval") == "test" and r.get("mIoU") is not None
            and "#frame=4" not in r["method"]]   # dropped from the chart, see the generator
    rows.sort(key=lambda r: r["mIoU"])
    expect = [{"method": r["method"].strip(), "mIoU": r["mIoU"],
               "excluded": bool(r.get("excluded")), "ours": bool(r.get("ours"))} for r in rows]
    best = max((r["mIoU"] for r in rows if not r.get("excluded")), default=None)
    top = max((r["mIoU"] for r in rows), default=None)
    return [
        ("results chart matches results.json", manifest == expect,
         f"{len(manifest)} plotted vs {len(expect)} in data"),
        ("chart's best ELIGIBLE bar is the headline, not the largest",
         best == 38.8 and top != best,
         f"best eligible {best}, largest overall {top}"),
    ]


# Every in-page anchor the site may point at, and what each one is FOR. An allowlist,
# not a resolvability check: all five anchors on the page resolved to a real id while
# four of them landed on the wrong content, so "the target exists" would have passed
# every one of them. #results is where the qualitative comparison (paper Fig. 6) lives;
# #main is the skip link's target. Anything else has to be added here deliberately.
ANCHOR_ALLOWLIST = {"#main", "#results"}


def internal_anchors(extra: dict[str, str] | None = None) -> list[tuple[str, str]]:
    """(source, anchor) for every in-page link, from the HTML and the script literals.

    The scripts are included because three of the four wrong links were built in JS and
    only exist once a failure path runs -- invisible to any check that reads the DOM of
    a healthy page.
    """
    out: list[tuple[str, str]] = []
    files = {"index.html": (SITE / "index.html").read_text(encoding="utf-8")}
    for js in sorted((SITE / "scripts").glob("*.js")):
        files[f"scripts/{js.name}"] = js.read_text(encoding="utf-8")
    if extra:
        files.update(extra)
    for name, text in files.items():
        # href="#x" in markup, and href = '#x' assigned in script.
        for m in re.finditer(r"""href\s*=\s*["']?(#[A-Za-z][\w-]*)["']?""", text):
            out.append((name, m.group(1)))
    return out


def check_anchors(anchors=None) -> list[tuple[str, bool, str]]:
    anchors = internal_anchors() if anchors is None else anchors
    html = (SITE / "index.html").read_text(encoding="utf-8")
    ids = set(re.findall(r'id="([^"]+)"', html))
    stray = [f"{src} -> {a}" for src, a in anchors if a not in ANCHOR_ALLOWLIST]
    missing = [f"{src} -> {a}" for src, a in anchors if a.lstrip("#") not in ids]
    return [
        ("every in-page link points at an allowlisted target",
         not stray, "; ".join(stray[:4]) or f"{len(anchors)} anchors, all allowlisted"),
        ("every in-page link resolves to a real id",
         not missing, "; ".join(missing[:4]) or "all resolve"),
    ]


def check_numbers(paper: str, nums: set[str]) -> list[tuple[str, bool, str]]:
    flat = paper.replace(",", "")
    missing = []
    for n in nums:
        if len(n.lstrip("-")) < 2:      # single digits carry no claim
            continue
        if n in paper or n.replace(",", "") in flat:
            continue
        missing.append(n)
    return [(f"all {len(nums)} numeric claims appear in the paper", not missing,
             ", ".join(sorted(missing)[:8]) or "none")]


def run(paper_dir: Path, caps=None, extra_prose="", title_override=None,
        anchors=None) -> list[tuple[str, bool, str]]:
    paper = normalise(paper_text(paper_dir))
    return (check_provenance(paper, caps if caps is not None else captions())
            + check_citation(paper_dir, title_override)
            + check_chart(paper_dir)
            + check_anchors(anchors)
            + check_numbers(paper, site_numbers(extra_prose)))


def gate(paper_dir: Path) -> int:
    failures = 0
    for name, ok, detail in run(paper_dir):
        if not ok:
            failures += 1
        print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  -> {detail}"))
    print(f"\n{'FAILED' if failures else 'OK'}: {failures} failing check(s)")
    return 1 if failures else 0


def selftest(paper_dir: Path) -> int:
    """Each fault must make some check fail. A check never seen failing proves nothing."""
    # (label, a substring of the check this fault MUST trip, kwargs). Asserting only
    # that *something* failed is the vacuity mode: a drifted fault plus one unrelated
    # baseline failure still prints SELFTEST OK. The other two tools already name their
    # target; this one did not.
    cases = [
        ("renumbered float (Fig. 6 -> Fig. 99)", "Fig. 99",
         dict(caps=[("Fig. 99", c[1]) for c in captions() if c[0] == "Fig. 6"])),
        ("float pointing at another topic (Fig. 6 -> Fig. 2)", "Fig. 2",
         dict(caps=[("Fig. 2", c[1]) for c in captions() if c[0] == "Fig. 6"])),
        # 99.97 is VERIFIED ABSENT from both PDFs. The first draft of this fault used
        # 41.7, which is a real SGSC row in the paper -- so the gate rightly passed and
        # the selftest read that as the gate being broken. A negative control has to be
        # verified negative.
        ("fabricated number in the prose", "numeric claims",
         dict(extra_prose="a headline of 99.97 percent")),
        # The exact defect this arm was written for: the title the copy button handed
        # out was truncated to its first four words.
        # The exact error I made: "correcting" the page's BibTeX to a longer working
        # title carried by README.md and the directory name, rather than the title the
        # built paper actually prints.
        # The exact defect a reader reported: the scene-failure note promised the
        # qualitative comparison and linked to #abstract. All five anchors resolved, so
        # only an allowlist catches it.
        ("fallback link pointing at the abstract", "allowlisted",
         dict(anchors=internal_anchors() + [("scripts/viewer3d.js", "#abstract")])),
        ("BibTeX title longer than the paper's", "title",
         dict(title_override="Generative Semantic Scene Completion through Modeling "
                             "the Underlying Geometry and Semantics in Point Clouds")),
    ]
    # A fault is only evidence against a clean baseline. If the gate is already failing,
    # every arm "trips" for the wrong reason.
    baseline = [n for n, ok, _ in run(paper_dir) if not ok]
    if baseline:
        print(f"  BASELINE NOT CLEAN: {len(baseline)} check(s) already failing -- "
              f"{'; '.join(baseline[:3])}")
        return 1
    silent = 0
    for label, expect, kwargs in cases:
        results = run(paper_dir, **kwargs)
        hits = [n for n, ok, _ in results if not ok]
        tripped = any(expect in n for n in hits)
        if not tripped:
            silent += 1
        note = "" if tripped else f"   (expected a check naming {expect!r}; got {hits or 'nothing'})"
        print(f"  {'TRIPPED ' if tripped else 'SILENT  '} {label}{note}")
    print(f"\n{'SELFTEST FAILED' if silent else 'SELFTEST OK'}: "
          f"{len(cases) - silent}/{len(cases)} faults detected")
    return 1 if silent else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper", type=Path, default=DEFAULT_PAPER)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    sys.exit(selftest(a.paper) if a.selftest else gate(a.paper))
