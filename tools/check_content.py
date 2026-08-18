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
    """[(claimed float, the full caption that claims it)].

    Scoped to caption ELEMENTS, both <figcaption> and <caption>: a window of text
    before the citation picks up the caption's tail (here, a TTA disclosure) rather
    than its topical lead, and bleeds into neighbouring content.

    Entities are decoded first. The markup writes "Table&nbsp;I", so matching
    r"Table\s*[IVXL]+" against raw tag-stripped text silently found neither table.
    """
    html = html if html is not None else (SITE / "index.html").read_text(encoding="utf-8")
    out = []
    for m in re.finditer(r"<(figcaption|caption)\b[^>]*>(.*?)</\1>", html, re.S | re.I):
        text = normalise(htmllib.unescape(re.sub(r"<[^>]+>", " ", m.group(2))))
        cite = re.search(r"Source: paper (Fig\.\s*\d+|Table\s*[IVXL]+)", text)
        if cite:
            out.append((re.sub(r"\s+", " ", cite.group(1)), text))
    return out


def check_provenance(paper: str, caps) -> list[tuple[str, bool, str]]:
    results = []
    for claim, caption in caps:
        num = re.search(r"(\d+|[IVXL]+)$", claim).group(1)
        if claim.startswith("Fig"):
            m = re.search(rf"Fig\.\s*{num}\.\s*([^.]{{6,120}})", paper)
        else:
            m = re.search(rf"TABLE\s+{num}\s+([A-Z][^\n]{{6,90}})", paper)
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


def run(paper_dir: Path, caps=None, extra_prose="") -> list[tuple[str, bool, str]]:
    paper = normalise(paper_text(paper_dir))
    return (check_provenance(paper, caps if caps is not None else captions())
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
    cases = [
        ("renumbered float (Fig. 6 -> Fig. 99)",
         dict(caps=[("Fig. 99", c[1]) for c in captions() if c[0] == "Fig. 6"])),
        ("float pointing at another topic (Fig. 6 -> Fig. 2)",
         dict(caps=[("Fig. 2", c[1]) for c in captions() if c[0] == "Fig. 6"])),
        # 99.97 is VERIFIED ABSENT from both PDFs. The first draft of this fault used
        # 41.7, which is a real SGSC row in the paper -- so the gate rightly passed and
        # the selftest read that as the gate being broken. A negative control has to be
        # verified negative.
        ("fabricated number in the prose",
         dict(extra_prose="a headline of 99.97 percent")),
    ]
    silent = 0
    for label, kwargs in cases:
        results = run(paper_dir, **kwargs)
        tripped = any(not ok for _, ok, _ in results)
        if not tripped:
            silent += 1
        print(f"  {'TRIPPED ' if tripped else 'SILENT  '} {label}")
    print(f"\n{'SELFTEST FAILED' if silent else 'SELFTEST OK'}: "
          f"{len(cases) - silent}/{len(cases)} faults detected")
    return 1 if silent else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper", type=Path, default=DEFAULT_PAPER)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    sys.exit(selftest(a.paper) if a.selftest else gate(a.paper))
