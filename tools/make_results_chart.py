#!/usr/bin/env python3
"""Render the hidden-test comparison as a chart, from the same JSON the page uses.

The page used to carry two HTML tables. Measured against 15 accepted project pages,
ZERO use an HTML number table; the five that show numbers at all use a bar chart or an
image of the paper's table. So the medium changes and the evidence stays.

Generating from data/results.json rather than hand-drawing keeps the numbers honest, and
tools/check_content.py gates the manifest this writes against that JSON.

WHAT THIS CHART PLOTS: every test row in data/results.json, unfiltered. There is no filter
in this file and there must not be one -- a filter here is invisible to the gate, which is
how the chart once dropped a row while every check stayed green.

The row that is NOT in the data: SCPNet at #frame=4, 47.5, the only published test row above
ours. It was REMOVED FROM data/results.json BY AUTHOR DECISION (2026-08-25), taken with the
counter-argument in front of the author -- that it is the one published test row above ours,
and that dropping it once before was reverted here as cherry-picking. That is the author's
call to make and it is recorded, not re-argued. What follows from it, and must stay true:

  * The paper still carries the row. This page's chart and the paper's Table I are no
    longer the same set of rows, so no caption, alt text or README line may say the chart
    plots "every test row of Table I". They said exactly that until this decision landed.
  * data/results.json is the single source of truth for the chart, and tools/check_content.py
    compares this chart's manifest against it. The row is gone from the DATA, not hidden by a
    filter or an allowlist entry, so CHART_OMISSIONS stays empty and nothing here special-cases
    a method name.

WHAT THIS CHART DOES **NOT** DO, because an earlier docstring here claimed it did and the
page's caption was then written from the docstring rather than from the picture: excluded
rows are NOT hatched and NOT greyed. Both of our bars carry the accent, by request. What
marks a row as outside the predicate is its AXIS LABEL: a leading double-dagger, plus the
configuration spelled out in words (test-time adaptation / N=4, +D4 TTA). The
double-dagger is explained on the second line of the x-axis label. It is THIS CHART'S mark,
not a quotation of the paper's: Table I gives each marked row a symbol of its own --
‖ test-time adaptation, § the D4 ensemble, per its "Excluded from bolding" footnote --
so any wording that calls the single dagger "the paper's mark" is false. Collapsing the
symbols to one is a fine simplification; describing it as the paper's notation is not.

THE MARK STAYS, and losing 47.5 is the reason it now matters MORE, not less. Two marked rows
remain, TALoS at 37.9 and our own D4 row at 39.2, and BOTH are longer than the 38.8 bar the
headline is indexed on -- so the longest bar on this chart is now OURS and is outside the
predicate. Unmarked, the picture would read 39.2 as the headline number. The dropped word is
"multi-sweep": no multi-sweep row is plotted any more, so the axis line names test-time
adaptation and ensembling only.

If you ever change that division of labour, change index.html's figcaption AND alt text AND
README.md's "What's on the page" row in the same commit -- naming only the caption is how
this file once spent three commits claiming a hatching the chart had stopped drawing.

Usage:  python tools/make_results_chart.py
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

SITE = Path(__file__).resolve().parent.parent
# The page's own tokens, so the chart belongs to the page rather than sitting on it.
# ACCENT is red because that is what was asked for. The previous #B85C00 measured hue
# 30 degrees -- the textbook midpoint of orange -- so "painted red" was not satisfied.
ACCENT, TEXT, MUTED, RULE, GROUND = "#B3261E", "#2E3338", "#6B7280", "#E3E5E8", "#FFFFFF"


def main() -> None:
    # No filter. Every test row in the data is plotted; tools/check_content.py asserts
    # that against the UNFILTERED data plus an explicit (currently empty) omission
    # allowlist, so a future silent drop fails the gate instead of being mirrored by it.
    rows = [r for r in json.loads((SITE / "data" / "results.json").read_text(encoding="utf-8"))
            if r.get("eval") == "test" and r.get("mIoU") is not None]
    rows.sort(key=lambda r: r["mIoU"])

    # Name what each method IS rather than classifying it as (non-)comparable: a reader
    # who sees "test-time adaptation" can judge for themselves, and the configuration
    # that produced our higher bar is stated on the bar instead of in a footnote.
    RELABEL = {"TALoS": "TALoS  (test-time adaptation)",
               "with D₄ ensemble (N=4)": "Ours + D₄ ensemble  (N=4, +D₄ TTA)"}
    # One double-dagger for every out-of-predicate row -- this chart's own mark, not the
    # paper's (see the docstring) -- explained on the x-axis. It goes on OURS too, so the
    # mark reads as a property of the configuration and not as a way of discounting
    # somebody else's number. Both marked rows now sit ABOVE our headline bar, one of them
    # ours, so the mark is what stops the longest bar reading as the headline number.
    labels = ["\u2021 " * bool(r.get("excluded")) + RELABEL.get(r["method"].strip(), r["method"].strip())
              for r in rows]
    vals = [r["mIoU"] for r in rows]
    excl = [bool(r.get("excluded")) for r in rows]
    ours = [bool(r.get("ours")) for r in rows]

    fig, ax = plt.subplots(figsize=(9.4, 4.5), dpi=160)
    fig.patch.set_facecolor(GROUND)
    ax.set_facecolor(GROUND)

    for i, (v, o) in enumerate(zip(vals, ours)):
        # Both of ours carry the accent, including the ensemble row: it is ours either
        # way, and the label says which configuration produced it. `excl` is deliberately
        # NOT consulted here -- see the docstring.
        ax.barh(i, v, color=ACCENT if o else "#C9CDD2", edgecolor="none", height=0.62)
        ax.text(v + 0.6, i, f"{v:.1f}", va="center", ha="left",
                fontsize=9.5, color=TEXT, fontweight="600" if o else "normal")

    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=9.5)
    for tick, o in zip(ax.get_yticklabels(), ours):
        tick.set_color(TEXT)
        tick.set_fontweight("600" if o else "normal")

    ax.set_xlabel("SemanticKITTI hidden-test mIoU (%)\n"
                  "\u2021 outside the headline predicate: test-time adaptation or ensembling",
                  fontsize=10, color=TEXT, labelpad=8)
    ax.set_xlim(0, max(vals) * 1.14)
    ax.tick_params(axis="x", colors=MUTED, labelsize=9)
    ax.tick_params(axis="y", length=0)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(RULE)
    ax.xaxis.grid(True, color=RULE, linewidth=0.8)
    ax.set_axisbelow(True)

    ax.legend(handles=[Patch(facecolor=ACCENT, label="ours"),
                       Patch(facecolor="#C9CDD2", label="published baselines")],
              loc="lower right", frameon=False, fontsize=9, labelcolor=TEXT)

    fig.tight_layout()
    out_png = SITE / "assets" / "figures" / "results_chart.png"
    fig.savefig(out_png, facecolor=GROUND)
    from PIL import Image
    Image.open(out_png).convert("RGB").save(
        SITE / "assets" / "figures" / "results_chart.webp", quality=90, method=6)
    plt.close(fig)
    # A manifest of what was actually plotted. check_content.py compares it against
    # data/results.json, so editing the data without regenerating the chart fails the
    # gate instead of silently leaving a stale picture of the results on the page.
    (SITE / "assets" / "figures" / "results_chart.json").write_text(
        json.dumps({"rows": [{"method": r["method"].strip(), "mIoU": r["mIoU"],
                              "excluded": bool(r.get("excluded")), "ours": bool(r.get("ours"))}
                             for r in rows]}, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {out_png.name}, .webp and .json — {len(rows)} test rows, "
          f"{sum(excl)} marked outside the predicate")


if __name__ == "__main__":
    main()
