#!/usr/bin/env python3
"""Render the hidden-test comparison as a chart, from the same JSON the page uses.

The page used to carry two HTML tables. Measured against 15 accepted project pages,
ZERO use an HTML number table; the five that show numbers at all use a bar chart or an
image of the paper's table. So the medium changes and the evidence stays.

Generating from data/results.json rather than hand-drawing keeps the predicate
enforceable: rows flagged `excluded` are drawn greyed and hatched and are labelled as
outside the predicate, so the chart cannot present the D4-TTA row as the headline the
way an earlier version of this page did.

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
ACCENT, TEXT, MUTED, RULE, GROUND = "#B85C00", "#2E3338", "#6B7280", "#E3E5E8", "#FFFFFF"


def main() -> None:
    rows = [r for r in json.loads((SITE / "data" / "results.json").read_text(encoding="utf-8"))
            if r.get("eval") == "test" and r.get("mIoU") is not None]
    rows.sort(key=lambda r: r["mIoU"])

    labels = [(r["method"].strip() or "ours").replace("SCPNet + S²D²", "SCPNet + S²D²") for r in rows]
    vals = [r["mIoU"] for r in rows]
    excl = [bool(r.get("excluded")) for r in rows]
    ours = [bool(r.get("ours")) for r in rows]

    fig, ax = plt.subplots(figsize=(9.4, 4.5), dpi=160)
    fig.patch.set_facecolor(GROUND)
    ax.set_facecolor(GROUND)

    for i, (v, e, o) in enumerate(zip(vals, excl, ours)):
        if e:
            ax.barh(i, v, color="#FFFFFF", edgecolor=MUTED, hatch="////", linewidth=1.0, height=0.62)
        else:
            ax.barh(i, v, color=ACCENT if o else "#C9CDD2", edgecolor="none", height=0.62)
        ax.text(v + 0.6, i, f"{v:.1f}", va="center", ha="left",
                fontsize=9.5, color=MUTED if e else TEXT,
                fontweight="600" if (o and not e) else "normal")

    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(
        [f"{l}  ·  outside the predicate" if e else l for l, e in zip(labels, excl)],
        fontsize=9.5)
    for tick, e in zip(ax.get_yticklabels(), excl):
        tick.set_color(MUTED if e else TEXT)
        if e:
            tick.set_style("italic")

    ax.set_xlabel("SemanticKITTI hidden-test mIoU (%)", fontsize=10, color=TEXT, labelpad=8)
    ax.set_xlim(0, max(vals) * 1.14)
    ax.tick_params(axis="x", colors=MUTED, labelsize=9)
    ax.tick_params(axis="y", length=0)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(RULE)
    ax.xaxis.grid(True, color=RULE, linewidth=0.8)
    ax.set_axisbelow(True)

    ax.legend(handles=[
        Patch(facecolor=ACCENT, label="ours"),
        Patch(facecolor="#C9CDD2", label="published baselines"),
        Patch(facecolor="#FFFFFF", edgecolor=MUTED, hatch="////",
              label="outside the predicate — not comparable"),
    ], loc="lower right", frameon=False, fontsize=9, labelcolor=TEXT)

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
