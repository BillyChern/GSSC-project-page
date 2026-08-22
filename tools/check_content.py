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

   ATTRIBUTE TEXT IS SWEPT TOO. It was not: stripping tags with <[^>]+> takes every
   attribute with them, so no number in an alt, aria-label, title or <meta content>
   was ever checked -- and alt text is exactly where a screen-reader user gets a
   figure's numbers. Twelve of the page's fifteen attribute numbers were invisible
   while this file printed "all N numeric claims appear in the paper".

Coverage limits, stated rather than assumed:
 - Numbers rendered INSIDE images are invisible here (assets/og-card.jpg asserts
   fourteen); they were checked by hand and are noted in the project memory.
 - <pre> citation blocks are excluded, because the page must carry the SemanticKITTI
   licence's required references and those are OTHER PEOPLE'S papers: "CVPR 2012,
   pp. 3354-3361" cannot be expected to appear in our own reference list. The exclusion
   is not blind -- check_code_blocks() fails if any <pre> on the page is not a citation
   block, so the exemption cannot quietly widen to cover a results table -- and the one
   block that matters, our own BibTeX entry, is gated separately by check_citation().

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


# Attributes that carry text a reader is shown -- by a screen reader, on hover, or in a
# social card. Named individually rather than swept by pattern so a new attribute has to
# be added deliberately. `title` is matched with a guard so data-title does not qualify.
SWEPT_ATTRS = ("alt", "aria-label", "title")

# The only <meta> numbers on the page that are not claims: the social card's pixel
# dimensions. Named, not pattern-filtered -- a filter is where the next defect hides,
# and a new meta claim must be swept by default rather than exempted by resemblance.
UNSWEPT_META = {"og:image:width", "og:image:height"}


def attribute_text(html: str) -> str:
    """Text carried in attributes, which tag-stripping deletes along with the tag."""
    out: list[str] = []
    for m in re.finditer(r"<meta\b([^>]*)>", html, re.I):
        attrs = m.group(1)
        key = re.search(r'(?:property|name)\s*=\s*"([^"]*)"', attrs, re.I)
        if key and key.group(1).strip().lower() in UNSWEPT_META:
            continue
        val = re.search(r'content\s*=\s*"([^"]*)"', attrs, re.I)
        if val:
            out.append(val.group(1))
    for attr in SWEPT_ATTRS:
        for m in re.finditer(rf'(?<![-\w]){attr}\s*=\s*"([^"]*)"', html, re.I):
            out.append(m.group(1))
    return " ".join(out)


def code_blocks(html: str | None = None) -> list[str]:
    html = html if html is not None else (SITE / "index.html").read_text(encoding="utf-8")
    return [m.group(1) for m in re.finditer(r"<pre\b[^>]*>(.*?)</pre>", html, re.S | re.I)]


def site_prose(html: str | None = None) -> str:
    # README.md is deliberately NOT swept. It repeats result numbers, but it also
    # documents the implementation -- CSS token widths, contrast ratios, an HTTP
    # status, a port -- and requiring those to appear in the paper produced 8 false
    # failures. Muzzling them with an allowlist would put a filter in front of the
    # gate, which is where defects hide. Its result numbers duplicate the page's and
    # are swept there; they were also checked directly once (107 ms, 3.23 FPS: both
    # present). Re-check by hand if the README ever states a result the page does not.
    html = html if html is not None else (SITE / "index.html").read_text(encoding="utf-8")
    # Drop <script>/<style> first: tag-stripping alone leaves the importmap behind, and
    # "three@0.160.0" is a dependency version, not a numeric claim about results.
    html = re.sub(r"<(script|style)\b.*?</\1>", " ", html, flags=re.S | re.I)
    attrs = attribute_text(html)
    # Citation blocks carry third-party years and page ranges; see the module docstring,
    # and check_code_blocks() for the assertion that keeps this exemption honest.
    html = re.sub(r"<pre\b[^>]*>.*?</pre>", " ", html, flags=re.S | re.I)
    return normalise(htmllib.unescape(re.sub(r"<[^>]+>", " ", html) + " " + attrs))


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


def site_numbers(extra_prose: str = "", html: str | None = None) -> set[str]:
    nums: set[str] = set()
    for m in re.finditer(r"-?\d+(?:,\d{3})*(?:\.\d+)?", site_prose(html) + " " + extra_prose):
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
        lines = [ln.strip() for ln in doc[0].get_text().splitlines()]
    for ln in lines:
        if not ln or ln.upper().startswith("IEEE TRANSACTIONS") or ln.isdigit():
            continue
        return normalise(ln)
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


# Test rows of data/results.json the chart is allowed NOT to plot, by method name.
# It is EMPTY, and that is the point. This gate used to recompute its expectation with
# the same `"#frame=4" not in method` filter the generator applied, so the one row the
# chart dropped -- SCPNet at four sweeps, 47.5, the only published test row above ours --
# was dropped from the expectation too, and the check passed while the picture was
# missing it. A shared filter is a gate agreeing with the thing it is gating. Omitting a
# row now means naming it here, in a diff someone reviews.
CHART_OMISSIONS: set[str] = set()

# The row selftest() deletes to prove the row-drop check can go red, and re-adds to the
# allowlist to prove an allowlisted omission is accepted. It is the row that was actually
# dropped once: SCPNet at four sweeps, the only published test row above ours.
DROP_FIXTURE = "SCPNet at #frame=4"


def check_chart(paper_dir: Path, manifest=None,
                omissions: set[str] | None = None) -> list[tuple[str, bool, str]]:
    """The results chart replaced two HTML tables. Nothing in the DOM can now be
    asserted about the predicate, so the check moves here: the chart's manifest must
    match what data/results.json says, or the page is showing a stale picture.

    `manifest` and `omissions` exist so selftest() can run this against a fixture. Until
    they did, the row-drop arm below could not be written at all, and the one check
    standing between a silent omission and the public page had never been seen failing.
    """
    if manifest is None:
        man_path = SITE / "assets" / "figures" / "results_chart.json"
        if not man_path.exists():
            return [("results chart manifest exists", False, "run tools/make_results_chart.py")]
        manifest = json.loads(man_path.read_text(encoding="utf-8"))["rows"]
    omit = CHART_OMISSIONS if omissions is None else omissions
    all_rows = [r for r in json.loads((SITE / "data" / "results.json").read_text(encoding="utf-8"))
                if r.get("eval") == "test" and r.get("mIoU") is not None]
    rows = [r for r in all_rows if r["method"].strip() not in omit]
    rows.sort(key=lambda r: r["mIoU"])
    expect = [{"method": r["method"].strip(), "mIoU": r["mIoU"],
               "excluded": bool(r.get("excluded")), "ours": bool(r.get("ours"))} for r in rows]
    plotted = {r["method"].strip() for r in manifest}
    # The allowlist has to bite HERE too, not only in `expect`. It did not: a row named in
    # CHART_OMISSIONS was still counted unplotted, so the documented one-line way to omit a
    # row -- name it in a diff someone reviews -- turned the gate red anyway, and the check
    # called "unless allowlisted" had no allowlist in it. The control arm in selftest()
    # pins the repaired behaviour.
    unplotted = [m for m in (r["method"].strip() for r in all_rows)
                 if m not in plotted and m not in omit]
    best = max((r["mIoU"] for r in rows if not r.get("excluded")), default=None)
    top = max((r["mIoU"] for r in rows), default=None)
    return [
        ("results chart matches results.json", manifest == expect,
         f"{len(manifest)} plotted vs {len(expect)} expected"),
        ("every test row is plotted unless allowlisted", not unplotted,
         ", ".join(unplotted) or (f"{len(all_rows)} test rows, " + (
             f"{len(omit)} allowlisted: {', '.join(sorted(omit))}" if omit else "none omitted"))),
        ("chart's best ELIGIBLE bar is the headline, not the largest",
         best == 38.8 and top != best,
         f"best eligible {best}, largest overall {top}"),
    ]


def check_code_blocks(html: str | None = None) -> list[tuple[str, bool, str]]:
    """Keep the numeric sweep's <pre> exemption from widening.

    site_prose() drops <pre> blocks because the page has to carry the SemanticKITTI
    licence's required references, whose years and page ranges are not in our paper.
    That is only safe while every <pre> on the page IS a citation block, so this asserts
    it rather than trusting it -- an exemption nobody re-checks is how a claim ends up
    somewhere no gate can see it.
    """
    blocks = code_blocks(html)
    bad = [normalise(re.sub(r"<[^>]+>", " ", b)).strip()[:44]
           for b in blocks if "@" not in b or "title" not in b]
    return [("every <pre> block is a citation block, so the numeric exemption holds",
             not bad, "; ".join(bad[:3]) or f"{len(blocks)} citation block(s)")]


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
        anchors=None, html=None, manifest=None,
        omissions: set[str] | None = None) -> list[tuple[str, bool, str]]:
    paper = normalise(paper_text(paper_dir))
    return (check_provenance(paper, caps if caps is not None else captions())
            + check_citation(paper_dir, title_override)
            + check_chart(paper_dir, manifest, omissions)
            + check_anchors(anchors)
            + check_code_blocks(html)
            + check_numbers(paper, site_numbers(extra_prose, html)))


def gate(paper_dir: Path) -> int:
    failures = 0
    for name, ok, detail in run(paper_dir):
        if not ok:
            failures += 1
        print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  -> {detail}"))
    print(f"\n{'FAILED' if failures else 'OK'}: {failures} failing check(s)")
    return 1 if failures else 0


def _inject_alt(prefix: str) -> str:
    """index.html with `prefix` prepended to the results chart's alt text.

    A fault that silently fails to modify anything is a fault that always passes, so
    this raises instead of returning the file unchanged.
    """
    html = (SITE / "index.html").read_text(encoding="utf-8")
    needle = 'alt="Horizontal bar chart'
    if needle not in html:
        raise AssertionError(f"selftest fault is stale: {needle!r} is no longer in index.html")
    return html.replace(needle, f'alt="{prefix}Horizontal bar chart', 1)


def _chart_manifest(drop: str | None = None) -> list[dict]:
    """A HEALTHY chart manifest, built from data/results.json, optionally missing one row.

    Built rather than copied: a fixture cloned from the shipped file would freeze whatever
    that file happens to say, so the arm would be asserting today's state instead of a
    fault. Here the only difference between the healthy fixture and the faulty one is the
    deletion, and selftest() runs the healthy one first to prove the gate is green on it.

    A deletion that deletes nothing always passes, so an unknown `drop` raises.
    """
    rows = [r for r in json.loads((SITE / "data" / "results.json").read_text(encoding="utf-8"))
            if r.get("eval") == "test" and r.get("mIoU") is not None]
    rows.sort(key=lambda r: r["mIoU"])
    man = [{"method": r["method"].strip(), "mIoU": r["mIoU"],
            "excluded": bool(r.get("excluded")), "ours": bool(r.get("ours"))} for r in rows]
    if drop is None:
        return man
    kept = [r for r in man if r["method"] != drop]
    if len(kept) == len(man):
        raise AssertionError(f"selftest fault is stale: no test row named {drop!r} to drop")
    return kept


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
        # Attribute text was invisible to the sweep for the whole life of this file, so
        # this arm exists to prove it no longer is. It injects into an ALT, the channel
        # a screen-reader user reads the figure's numbers from.
        ("fabricated number in an alt attribute", "numeric claims",
         dict(html=_inject_alt("99.97 percent. "))),
        # The defect this gate was written for and had never been seen catching: the
        # chart quietly stops plotting the one published test row above ours. The
        # fixture is healthy apart from that one deletion (see _chart_manifest).
        ("results row dropped from the chart with no allowlist entry", "is plotted",
         dict(manifest=_chart_manifest(drop=DROP_FIXTURE))),
        # And the exemption that pays for the licence citations: a <pre> that is not a
        # citation block must fail, or the exemption has quietly widened.
        ("non-citation <pre> block on the page", "citation block",
         dict(html=(SITE / "index.html").read_text(encoding="utf-8").replace(
             "</main>", "<pre>headline 99.97</pre></main>", 1))),
    ]
    # A fault is only evidence against a clean baseline. If the gate is already failing,
    # every arm "trips" for the wrong reason.
    baseline = [n for n, ok, _ in run(paper_dir) if not ok]
    if baseline:
        print(f"  BASELINE NOT CLEAN: {len(baseline)} check(s) already failing -- "
              f"{'; '.join(baseline[:3])}")
        return 1
    # The chart arm injects a fixture, so the fixture needs its own clean baseline: if
    # the healthy manifest already failed, the deletion would prove nothing.
    unhealthy = [n for n, ok, _ in run(paper_dir, manifest=_chart_manifest()) if not ok]
    if unhealthy:
        print(f"  CHART FIXTURE NOT HEALTHY: {len(unhealthy)} check(s) failing on the "
              f"undeleted manifest -- {'; '.join(unhealthy[:3])}")
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
    # Positive control on the allowlist, not a fault: the SAME deletion, named in
    # CHART_OMISSIONS, must be ACCEPTED. Without this the arm above could be satisfied by
    # a check that simply always fails on any omission, and the documented reviewable
    # one-line lever -- name the row in a diff -- would not exist.
    ctl = check_chart(paper_dir, manifest=_chart_manifest(drop=DROP_FIXTURE),
                      omissions={DROP_FIXTURE})
    ctl_red = [n for n, ok, _ in ctl if not ok]
    if ctl_red:
        print(f"  CONTROL FAILED  an ALLOWLISTED omission still turns the gate red "
              f"-- {'; '.join(ctl_red)}")
    else:
        print(f"  CONTROL OK      the same omission, allowlisted, is accepted "
              f"({len(ctl)} chart check(s) green)")
    print(f"\n{'SELFTEST FAILED' if silent or ctl_red else 'SELFTEST OK'}: "
          f"{len(cases) - silent}/{len(cases)} faults detected, "
          f"allowlist control {'FAILED' if ctl_red else 'passed'}")
    return 1 if (silent or ctl_red) else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper", type=Path, default=DEFAULT_PAPER)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    sys.exit(selftest(a.paper) if a.selftest else gate(a.paper))
