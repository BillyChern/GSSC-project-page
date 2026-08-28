# Generative Semantic Scene Completion — Project Page

Static, build-free project page for the paper
**Generative Semantic Scene Completion**.

The page is centred on **S²D²** (Structured Source Discrete Diffusion),
a one-step refiner that lifted every SSC base we tested (LMSCNet, JS3C-Net,
SCPNet) by learning a correction on the discrete probability simplex. The paper
does not claim it lifts *any* base: on a weaker source it can erase a rare class
rather than recover it, which is why the transfer claim is scoped to
voxel-grid-native sources.

**Headline numbers (SemanticKITTI hidden test).** Every number below is indexed on the
paper's predicate — *causal, single-sweep, single-sample*: one sweep, no future moments, no
ensembling.

- **38.8 %** mIoU at one step ($N{=}1$) with **no test-time augmentation** — to our knowledge the
  best *causal, single-sweep, single-sample* result on the SemanticKITTI hidden test, **+2.1 pp**
  over the previous best published score (SCPNet, 36.7 %).
- **39.2 %** with four correction steps and an eight-view $D_4$ ensemble — the entry Codabench
  displays, since the platform lists each team's best score. Four steps plus the ensemble sit
  outside the predicate the superlative is indexed on.
- Excluded for the same reason, and not comparable to ours: TALoS (37.9 %, test-time adaptation)
  and SCPNet at four sweeps (47.5 %).
- **+2.36 pp** added on top of the frozen SCPNet base on validation (36.17 → 38.54 %). The
  operator is base-agnostic: it also lifts JS3C-Net (22.7 → 24.3, +1.6) and LMSCNet (+1.8).

**Honesty notes carried from the paper.** We do not lead on safety — S3CNet, not us, takes the
vulnerable-road-user column (VRU-IoU 32.6 against our 21.6). The largest single-class gain
(motorcyclist, +8.3) **does not reproduce**: an independent from-scratch retrain recovers +0.3, so
the paper does not claim it and neither does this page. Latency is not repaid: the correction pass
costs 107 ms, dropping the deployed base-plus-refiner pipeline to 3.23 FPS end-to-end on an idle
H100 against the frozen base's 4.95. On a weaker base the refiner can *erase* a rare class rather
than recover it.

**Zero-shot transfer:** the frozen SemanticKITTI checkpoint lifts the base on two unseen domains
with no fine-tuning — SemanticPOSS mIoU 1.0 → 6.5 % and SSCBench-KITTI360 on completion IoU.

## Publication status — read before deploying

**The patent hold is LIFTED.** The patent was approved (author, 2026-08-18), so the
release gate that governed this repo no longer applies. Earlier revisions of this file
and of `tools/push_to_github.sh` said *"Do NOT enable GitHub Pages until the patents are
filed"* — that instruction is now spent, and it is recorded here rather than silently
deleted so nobody re-applies it from an old checkout.

**Review here is single-anonymous** (author, 2026-08-18): reviewers are anonymous to
the authors, authors are not anonymous to reviewers. Nothing about the submission
requires this page to hide author identity, so the revealed default is correct and no
blinding step is needed before release. See *Author visibility*.

What remains before going public is a judgement call, not a hold:

- ~~`github.com/BillyChern/GSSC-S2D2` (code) and the model/data releases are still 404.~~
  **Spent, 2026-08-25.** Code, checkpoints, the PS³ corpus (Hugging Face *and* the IEEE
  DataPort deposit) and the baseline-prediction release are all public and all return 200
  unauthenticated, and all of them are linked from the page — see *Release links* for the
  table and the checks. Nothing on the page says any artefact arrives "on publication"
  any more; that wording is recorded here only so nobody restores it from an old checkout.
- This repository's **history has been rewritten and re-pushed**: the `.audit/` screenshots
  it once carried are gone from the object graph. Measured 2026-08-23 —
  `git rev-list --objects --all` lists 82 distinct paths and none under `.audit/`, and
  `origin/main` is the same commit as local `HEAD`. A fresh clone therefore gets nothing the
  checkout does not. (GitHub may still serve an unreachable blob to anyone who already knows
  its SHA; that is a property of the forge, not of this history.)

- Repository: <https://github.com/BillyChern/GSSC-project-page> (private)
- Intended URL once released: <https://shichen.world/GSSC-project-page/>
  (**not** the `billychern.github.io` form — that 301-redirects; see
  *Hosting URL and the account-wide redirect*)

**Licence: MIT** — `LICENSE` at the repo root, © 2026 Shi Chen, Weifeng Ge, identical to
the release repo's. It covers this page's own material: the HTML, CSS, JS, `tools/` and
the generated charts. It does **not** cover the SemanticKITTI-derived files —
`assets/ply/*_gt.ply` and the ground-truth renders inside the qualitative, gallery and
viewer figures — which stay under CC BY-NC-SA 4.0 for the reasons in *Third-party data*
below. Until this file existed the page's own code shipped with no licence at all.

A `.nojekyll` sentinel sits at the repo root so `assets/` is served as-is. Note the
consequence: with Jekyll disabled, Pages serves dotdirs verbatim, so anything like
`.audit/` that gets committed becomes publicly fetchable. It is gitignored for
exactly that reason.

## What's on the page

Structure and styling follow the conventions measured across 30 accepted-paper project pages,
including 11 from this subfield (PaSCo, MonoScene, SceneRF, LiDPM, SemCity, TPVFormer, OccWorld,
SelfOcc, SurroundOcc, Occ3D, XCube): white ground, one accent used only for links, a single
humanist sans at 16 px, one centred column with prose at 720 px inside media at 960 px
(`--w-prose` / `--w-media` in `styles/tokens.css` — those two tokens are the source of
truth, not this sentence), plain noun headings, and no page animation — motion belongs to
results, not to chrome.

The rows below are in the order the page reads them, which is also the order
`tools/check_page.py` pins (`CANON` in that file).

| Section | What it shows |
|---|---|
| Header | Title, venue, authors, and the resource row: **seven slots in two tiers**, all seven live links. Tier 1 is the paper and what runs it (Paper — the arXiv preprint; SemanticKITTI leaderboard; Code; Checkpoints), tier 2 the three data releases (PS³ corpus; PS³ on IEEE DataPort; baseline predictions & object bank). See *Release links* for why it is two tiers and not one row |
| **The semantic scene completion challenge** (`#task`) | Paper Fig. 1(a): a sparse sweep at ~1% occupancy and the dense scene to be predicted. A reader new to the subfield learns the problem from a figure before any prose |
| Abstract (`#abstract`) | The paper's abstract **verbatim**, below the media — measured convention: of 12 top project pages diffed against their arXiv text, 10 reproduce it verbatim or near-verbatim, **0 rewrite it**, and all sit below the first figure |
| **Results** (`#results`) | Paper Fig. 6 qualitative comparison, then a generated bar chart of hidden-test mIoU. The chart plots the **nine** test rows in `data/results.json`; the two outside the headline predicate — TALoS (test-time adaptation) and our own D₄ row — carry a leading `‡`, explained on the second line of the x-axis. **That is not all of paper Table I.** SCPNet at four sweeps (47.5, the one published test row above ours) was removed from `data/results.json` **by author decision, 2026-08-25**, taken with the counter-argument in hand; the paper still carries the row, this chart does not, and no caption, `alt` string or line here may say the chart plots every test row of Table I. The paper marks its excluded rows individually (`‖` test-time adaptation, `§` D₄ ensemble), so the single `‡` is this chart's simplification, not Table I's notation |
| Interactive comparison (`#viewer`) | Three.js viewer over four views (input / base / ours / ground truth) on two rare-class frames. Its legend states the configuration the chips come from — N=4, +D₄ TTA, outside the headline predicate — and `check_page.py` asserts that string is present |
| **How it works** (`#method`) | The three contributions as figures: PS³ (Fig. 2) and what the corpus does about the long tail (Fig. 9); SGSC (Fig. 4); S²D² (Fig. 5) |
| Rare classes, before and after (`#gallery`) | Paper Fig. 10: six validation scenes, base against refinement, one per rare class |
| Acknowledgements (`#ack`) | Funding, the provenance of the renders, and the SemanticKITTI licence and attribution (see *Third-party data*) |
| BibTeX (`#bibtex`) | Copy-to-clipboard citation block for this paper, plus the two dataset citations SemanticKITTI requires |

Ordering and length follow measurement, not taste. Across 15 accepted project pages the
median is **363–379 visible words**. This page was 1,561, was trimmed to ~760, drifted back
to **1,132**, and is now **903** — measured the same way each time: `document.body.innerText`
of the served page, tokens containing a letter or a digit, Chromium at 1280×900.

903 is above the band and stays there on purpose. Four blocks account for 439 of it and none
of them is running text a corpus page has to carry:

| Block | Words | Why it cannot be cut |
|---|---:|---|
| Abstract, verbatim | 200 | 0 of 12 corpus pages rewrite theirs; rewriting it is how claims drift |
| Three BibTeX entries | 133 | Two of them — Behley et al. and Geiger et al. — are required by SemanticKITTI's own terms |
| CC BY-NC-SA attribution | 80 | The page redistributes modified SemanticKITTI material; see *Third-party data* |
| Grant acknowledgement | 26 | Named grants, 624B1006 and 24511103900 |

The **113** left over is chrome the counter cannot tell from prose: the title block
(44 — title, venue, authors, affiliations and the seven button labels), the skip link, the
section headings outside the two fixed sections, the viewer's control labels, and the
viewer's generated IoU readout (23). Which puts the actual **running
text — the eight figcaptions (245), the viewer note (20), the render-provenance paragraph
(47) and the footer (39) — at 351**, *below* the corpus median for an entire page. Measured
2026-08-26 against the arXiv-linked page, per element, by the same counter. The page is long
because of what it is obliged to say, not because of how it says it.

`903 = 439 fixed + 351 running + 113 chrome`. If a future round needs it shorter, the only
places left are the four fixed blocks, and each one costs something real.

**0 of 15 use an HTML number table**, and the five that show numbers use a chart or an image
of the paper's table — hence `tools/make_results_chart.py`. **1 of 15** carries a limitations
section, so that section is gone; the two honesty facts it held (S3CNet leads on safety, and
the motorcyclist gain that does not reproduce) are stated in the paper, and the page no
longer claims to mirror every hedge.

Authors are named in the header and in the BibTeX. There is no visibility toggle;
see *Author visibility*.

## Local preview

```bash
cd s2d2_website
python3 -m http.server 8099
# then open http://localhost:8099
```

Any static file server works — there's no build step. Port 8099 matches the
default the checks below expect.

## Checks

Three gates, each with a `--selftest` that injects faults and requires each one to trip
the check it names. A check never seen failing is not evidence of anything — and not
every check has an arm yet, so the counts are stated rather than implied:

| Gate | checks | `--selftest` arms |
|---|---|---|
| `check_artifact.py` | 6 | **6 — complete.** `no console errors` and `parity with the served page` had none until this round; the parity arm is guarded by a clean-baseline run, since with the served page down parity fails on every arm and for none of their own reasons |
| `check_content.py` | 17 | 8 arms + an allowlist control. Measured 2026-08-23 by running every arm and collecting the failing names: **6 of the 17 printed names** go red, plus 2 names that exist only under injection (`Fig. 99 exists in the paper`, and the numeric-claims check, whose name carries the LIVE count — `all N numeric claims appear in the paper` — so an injected claim makes it print `N+1` and it never appears red under the name it prints when clean. That count is not a constant: it was 121 clean on 2026-08-23 and is 116 on 2026-08-25, because the trim took numbers off the page. Do not pin it here; read it off a run). `check_provenance` is armed once (Fig. 6 → Fig. 2) and then runs unarmed over the other seven floats. Never seen failing: those seven `Fig. N / Table I is the float the caption describes` checks, `README citation title is the paper's title`, `chart's best ELIGIBLE bar is the headline`, and `every in-page link resolves to a real id` |
| `check_page.py` | 47 assertions over 25 names | 18. Unarmed: `watchdog fires while three.js is held`, `late-arriving viewer still draws`, `truthful aria-label restored`, `no-JS still shows every figure`, `print hides the copy button`, `scene failure offers a link`, `viewer still draws under reduced motion` |

```bash
python3 -m http.server 8099 &          # check_page.py, and check_artifact.py's parity check, need the site served
python tools/check_page.py             # behaviour: structure, figures, viewer, a11y
python tools/check_page.py --selftest   # ~3 min: proves all 18 arms can fail

python tools/check_content.py           # site claims vs the built paper
python tools/check_content.py --selftest

python tools/check_artifact.py          # the BUILT single-file page, under a harsh CSP
python tools/check_artifact.py --selftest
```

`check_page.py` emits **47 assertions over 25 distinct names** — 11 per viewport across
three viewports, plus the print, no-JS, slow-load, reduced-motion, scene-failure and
link-hover/focus contexts — and deliberately pins earlier fixes: the reading order, the
viewer legend still discloses the configuration its IoU chips come from, all text clears
WCAG AA contrast measured on the rendered page (not read off the tokens), a late-arriving
three.js retracts the watchdog's failure claim, the scene-failure link lands on the
qualitative figure, and console errors are visible. It no longer checks table styling:
the page has carried no HTML table since the results became a chart.

`check_artifact.py` gates the **output** of `build_standalone.py`, which the other two
never see: they measure `localhost:8099` and the source tree, i.e. the build's input.
Three defects shipped from that blind spot — an `@font-face` `url()` that was never
inlined, a tag strip that matched `<header ...>` as well as `<head>`, and a 3D viewer
whose clouds were fetched from `data:` URIs (governed by `connect-src`, which the host
withholds). It loads the built document under a policy harsher than the documented one,
`connect-src 'none'`, so the page cannot depend on a header we are unable to read.

`tools/make_results_chart.py` regenerates the results figure from `data/results.json`
and writes a manifest beside it; `check_content.py` compares that manifest against the
data, so editing the numbers without regenerating the chart fails the gate rather than
leaving a stale picture of the results on the page. That comparison is against the
**unfiltered** test split plus an explicit (currently empty) `CHART_OMISSIONS`
allowlist. It used to apply the same filter the generator did, which is how the chart
came to drop SCPNet at four sweeps — 47.5, the one published test row above ours — with
every check still green. Omitting a row now means naming it in that allowlist, and the
allowlist now bites in **both** places it has to: the row-by-row comparison and the
`every test row is plotted unless allowlisted` check, which counted an allowlisted row as
unplotted and so turned red on the very diff it was meant to make reviewable. Two
`--selftest` arms pin that: deleting a row from a healthy manifest must fail the check,
and the same deletion, named in `CHART_OMISSIONS`, must be accepted. The row those arms
delete (`DROP_FIXTURE`) **was** SCPNet at four sweeps and is now **`SCPNet (published)`**,
36.7 — the previous best under the paper's own predicate, the number our "+2.1 pp" is
measured against, and so the remaining row whose silent disappearance would flatter us
most. The fixture had to move because the old one is no longer in the data; it did not
rot silently, because `_chart_manifest()` raises on a deletion that deletes nothing.

`check_content.py` compares the page against `/workspace/GSSC-paper/pdf`
(`--paper` to point elsewhere): every caption's `data-paper-float` citation must resolve
to a float whose real caption is about the same thing, the chart's manifest must match
`data/results.json` row for row, and every number in the page — prose **and** `alt` /
`aria-label` / `title` / `<meta content>` attribute text, which the sweep used to drop
along with the tags — plus `data/*.json` must appear in the paper or supplement.
**Run it after any float moves in the manuscript** — moving one float renumbers every
figure after it, and these captions cite eight floats by number.

Two coverage limits are stated in that file rather than left implicit: numbers rendered
*inside* images are invisible to it, and `<pre>` citation blocks are exempt from the
numeric sweep because the page must carry SemanticKITTI's required references and
"CVPR 2012, pp. 3354–3361" is not in our reference list. The exemption is itself gated —
a `<pre>` that is not a citation block fails the run — so it cannot quietly widen.

## Regenerating the 3D viewer's PLY assets

The viewer loads all 8 PLY point clouds in `assets/ply/`:

| Scene        | Views (sparse · SCPNet · S²D² · GT) |
|--------------|-------------------------------------|
| bicyclist    | `bicyclist_{sparse,scpnet,s2d2,gt}.ply` (seq 08 · 003096)    |
| motorcyclist | `motorcyclist_{sparse,scpnet,s2d2,gt}.ply` (seq 08 · 001417) |

These are the two scenes defined in `SCENES` in `scripts/viewer3d.js` and the two
rows of main-paper Fig. 6. A third `traffic_*` set was exported early and never
wired in; it was removed rather than left as 1.1 MB of dead weight in every clone,
and it is absent from the exporter's `FRAMES`. Restoring it would need a `label`
and per-scene `stats`, and no verified source for those figures exists — do not
invent them.

Provenance worth knowing before you regenerate: the `*_s2d2.ply` files are the
**N=4, +D₄-TTA** prediction, verified by recomputing per-class IoU across every
local prediction variant — it is the only one reproducing Fig. 6's own chips
(frame 003096: TP 2724 / FP 1956 → 56.9%; frame 001417: 255 / 94 → 62.3%). That
configuration sits outside the paper's headline predicate, which is why the viewer's
legend names it — "Chips: N=4, +D₄ TTA — outside the headline predicate" — and why
`check_page.py` asserts that disclosure is present. It was removed once, silently, and
this README went on claiming it was gated; do not remove it again without removing the
assertion and its selftest arm in the same commit.

Regenerate from source voxel data:

```bash
python tools/export_ply.py
```

The exporter reads SemanticKITTI GT voxel labels, SCPNet pre-computed
predictions, and our S²D² label outputs, colour-codes each voxel by class,
and writes ASCII PLY files ready for `three.js` `PLYLoader`.

### Third-party data — read before republishing anything under `assets/`

`*_gt.ply` are voxelised, class-recoloured exports of SemanticKITTI's ground-truth
annotations (seq 08, frames 003096 and 001417), and the qualitative and gallery figures
render the same annotations. That is **modified SemanticKITTI material, redistributed**,
not merely a picture of it: the point clouds are machine-readable and ship inside the
single-file build as well.

SemanticKITTI is licensed **CC BY-NC-SA 4.0**
(<https://creativecommons.org/licenses/by-nc-sa/4.0/>): credit the creators, non-commercial
use only, share-alike, and indicate that the material was modified. Its
[dataset page](http://www.semantic-kitti.org/dataset.html) additionally requires citing
**both** the SemanticKITTI paper (Behley et al., ICCV 2019) and the original KITTI Vision
Benchmark (Geiger et al., CVPR 2012). The page carries all of this in its Acknowledgements
and both BibTeX entries in the BibTeX section; naming "SemanticKITTI" in prose is not the
attribution the licence asks for, which is why it says the rest explicitly. Keep that
notice with the assets if either is ever moved, re-exported or vendored elsewhere.

## Author visibility

Authors are named, in the header and in the BibTeX. **The "Hide authors" toggle and
everything behind it were removed** (author, 2026-08-19): `scripts/anon.js`,
`body[data-anon]`, `.anon-note`, the paired `.identity-inline` / `.anon-inline`
spans, and the gate check that exercised them.

Two reasons. **Review here is single-anonymous** (author, 2026-08-18) — authors are
visible to reviewers — so the control could not serve this submission. And it never
delivered what its label implied: it hid on-page text only, while `og:url` and
`og:image` hardcode the author's own domain (`shichen.world`; they named
`billychern.github.io` until 2026-08-25 — see *Hosting URL and the account-wide
redirect*), crawlers need those absolute and ignore JS-set metadata, and the hosting
URL itself carries the author's identity under either form. A control that
cannot do what it says is worse than no control.

> If a future venue is double-anonymous, do not reinstate this. Blinding needs
> anonymous **hosting** — a fresh repository under a neutral account, with the `og:*`
> URLs and the BibTeX rewritten. No amount of CSS reaches a meta tag.

## Release links

**Seven slots sit under the author block: every released artefact of this project is
linked from the page** (author, 2026-08-25 — "everything related to our project should be
well linked and well shown on the webpage"). All seven are live `<a>` elements. The last
inert one, **Paper**, went live when the arXiv preprint was posted; nothing on this page
is an `aria-disabled` label any more.

| Slot | Target | Live |
|---|---|:--:|
| Paper — arXiv | `arxiv.org/abs/2608.26737` | ✓ |
| SemanticKITTI leaderboard | `codabench.org/competitions/13814` | ✓ |
| Code | `github.com/BillyChern/GSSC-S2D2` | ✓ |
| Checkpoints | `huggingface.co/Stone-Chern/GSSC-S2D2-checkpoints` | ✓ |
| PS³ corpus | `huggingface.co/datasets/Stone-Chern/PS3-SemanticKITTI` | ✓ |
| PS³ on IEEE DataPort | `dx.doi.org/10.21227/nqgf-9k39` | ✓ |
| Baseline predictions & object bank | `huggingface.co/datasets/Stone-Chern/GSSC-S2D2-datasets` | ✓ |

Each was checked unauthenticated before it was linked — the rule is that a control which
cannot do what it says is worse than no control, so nothing here gets an `href` until it
returns 200 to a logged-out request:

```
arxiv.org/abs/2608.26737                                   200
github.com/BillyChern/GSSC-S2D2                            200
huggingface.co/Stone-Chern/GSSC-S2D2-checkpoints           200
huggingface.co/datasets/Stone-Chern/PS3-SemanticKITTI      200
huggingface.co/datasets/Stone-Chern/GSSC-S2D2-datasets     200
dx.doi.org/10.21227/nqgf-9k39                              200
```

The single "Models & PS³ data" slot was split in two, because one button cannot point at
two hosts; the PS³ corpus then took a second slot for the same reason — the Hugging Face
copy is the free mirror, the IEEE DataPort deposit is the citable record, and they are
different hosts.

**Why two tiers and not one row.** Seven buttons do not fit one line at the 720 px prose
measure: tier 1 alone measures 652 px against 672 px of content width (`.link-tier`
in `styles/site.css`, measured in Chromium at 1280 px). Left as a single wrapping row the
break would land wherever the box ran out and read as an accident. So the split is made
deliberately and given a reason — tier 1 is the paper and what runs it, tier 2 the three
data releases — and proximity carries it: **24 px between tiers against 12 px within**, a
2:1 ratio. Measured at 1440/1024/390 px: one line per tier at 1440 and 1024 (652 px and
588 px), and at 390 px each tier stacks *inside itself*, so the grouping survives the
stack and the page still has no horizontal scroll. The corpus is no help above four
buttons — PaSCo, Occ3D, LiDPM and SceneRF each carry three or four in one flat row — so
what is followed from them is the label convention (short, specific nouns; Occ3D names its
two dataset downloads outright) rather than a layout none of them has to solve.

**The DataPort DOI lives in the `href`, not in the label.** `check_content.py` sweeps every
number in visible text *and* in `alt` / `aria-label` / `title` / `<meta content>` against
the paper, and `10.21227` is an identifier that no paper can contain — it failed the gate
for as long as the old links-note printed `doi:10.21227/nqgf-9k39` as link text. The fix is
the button, not an exemption in the gate: the DOI is reachable in one click and the sweep
keeps its full reach. **Do not put the DOI back into a label or a `title`** without adding
a gated exemption for it, and prefer not adding one — a filter in front of a gate is where
the next defect hides.

**The same rule binds the arXiv id.** `2608.26737` and its DataCite DOI
`10.48550/arXiv.2608.26737` live in the Paper button's `href` and in the BibTeX `<pre>` —
which the numeric sweep exempts — and nowhere else. Measured against the built paper by
injection: put either in the button's label and `all N numeric claims appear in the paper`
goes red on `2608.26737`; put the id in the button's `title` and it goes red the same way;
put the DOI in the label and it goes red on `10.48550`. That is why the button reads
**Paper — arXiv** with no identifier in it, and why the id is in an HTML comment nowhere
near an attribute. **Do not** widen `SWEPT_ATTRS` or add an exemption to make a prettier
label possible.

**Done — the preprint is posted.** The Paper `<span>` is now
`<a class="btn" href="https://arxiv.org/abs/2608.26737" target="_blank" rel="noopener" title="The preprint on arXiv; the paper is under review.">Paper &mdash; arXiv</a>`,
and there is no inert control left on the page. Consequence: `.btn[aria-disabled="true"]`
in `styles/site.css` and the `--faint` token it is the only user of are now dead rules.
They are kept for the next control that needs them, not because anything uses them — if
you delete them, delete both, and the CSS comment above `.links` that counts the tiers
stays correct either way.

## Editing numbers

- **Main comparison**: `data/results.json` — **16 rows** across both splits, drawn from
  paper Table I but **no longer the whole of it**: SCPNet at four sweeps (47.5) was
  deleted from this file by author decision on 2026-08-25, so the page's chart and the
  paper's Table I are now different sets of rows. The deletion is in the data, in a
  reviewable one-line diff — not behind a filter in the generator and not behind
  `CHART_OMISSIONS`, which stays empty. Keys: `eval` (`test`|`val`), `ours`, and
  `excluded` for rows outside the paper's predicate (now TALoS and our D₄ row). There is
  no `best` flag and nothing in the browser reads this file: `tools/make_results_chart.py`
  draws every test row from it, and `tools/check_content.py` RECOMPUTES which row is the
  best eligible one and fails if that is not 38.8. Never hand-bold a row, and never mark
  an `excluded` row as best — the 39.2 D₄ row is excluded. **Editing this file means
  re-running the generator**, or the manifest check fails on the next run.
- **Per-class figures**: `data/perclass.json` — paper Table II: base IoU plus both
  the Released Δ and the Retrain Δ, the VRU-IoU row, and `disclaimed: true` on
  motorcyclist, whose released +8.3 does not reproduce (retrain recovers +0.3). Nothing
  renders this file any more — the per-class table came off the page with the other one.
  It is kept because `check_content.py` still sweeps its numbers against the paper, so it
  stays a live claim: correct it if the manuscript's Table II moves.

## Deploying to GitHub Pages

> **Ungated as of 2026-08-18** — the patent is approved, and the 69 `.audit/` screenshots
> of this page's over-claiming predecessor have been removed from the history and the repo
> re-pushed (see *Publication status*), so enabling Pages no longer republishes them.

1. Push this directory to the repo's default branch (`main`).
2. Settings → Pages → Source = **Deploy from a branch**, branch = `main`, folder = `/ (root)`.
3. The `.nojekyll` file at the repo root disables Jekyll so `assets/` loads cleanly.

Or, with a workflow:

```yaml
# .github/workflows/pages.yml
name: Deploy to Pages
on:
  push: { branches: [main] }
permissions: { contents: read, pages: write, id-token: write }
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/upload-pages-artifact@v3
        with: { path: . }
      - uses: actions/deploy-pages@v4
```

### Hosting URL and the account-wide redirect

The live URL is **<https://shichen.world/GSSC-project-page/>**, not the
`billychern.github.io` form. The account has a verified custom domain
(`shichen.world`) with HTTPS enforced, so GitHub answers *every* project-page path
under `billychern.github.io` with a permanent redirect to it. Measured 2026-08-25:

```
$ curl -sSI https://billychern.github.io/GSSC-project-page/
HTTP/2 301
location: https://shichen.world/GSSC-project-page/
```

There is no `CNAME` file anywhere in this repository. The domain is configured at the
**account** level, so the redirect applies to this repo whether or not it opts in, and
adding or removing a file here will not change it — `https://billychern.github.io/<anything>/`
redirects the same way (verified against a path that does not exist).

So record the `shichen.world` form in anything absolute: `og:url` and `og:image` in
`index.html`, the `"Project page"` entry in the release repo's `pyproject.toml`, and any
URL printed in the paper. The `github.io` form is not broken — browsers follow the 301 —
but social-card scrapers that do not follow redirects will drop the card, and a redirect
sitting inside a published citation is one more thing that can go stale.

Both forms return 404 today because Pages has not been enabled on this repo yet
(`has_pages: false`, measured 2026-08-25). That is the deploy step above; it is not a
problem with the URL.

## Tech stack

- **three.js** r160, import map from unpkg, for the voxel viewer
- **Google Fonts**: Hanken Grotesk (200/400/500), the body face, and the only webfont
  fetched from a third party
- **Display face**: CMU Serif, **self-hosted** at `assets/fonts/cmu-serif-roman.woff2`
  and vendored deliberately — the single-file build has to render under a CSP that
  admits no font host but Google Fonts, which does not serve Computer Modern. Licence
  and provenance in `assets/fonts/NOTICE.md`. Monospace comes from the system stack
- Vanilla CSS, tokens in `styles/tokens.css`, everything else in `styles/site.css`
- Vanilla JS, no build step: `scripts/main.js` is the BibTeX copy button plus a watchdog
  for a three.js that never arrives, and `scripts/viewer3d.js` is the viewer. **Neither
  fetches `data/*.json`** — the results tables became a generated figure, so that JSON is
  now read at build time by `tools/make_results_chart.py`, not in the browser
- No tracker, no analytics, no cookies. Two third-party fetches: the webfont and three.js

## Accessibility notes

- Semantic landmarks (`<header>`, `<main>`, `<section>`, `<footer>`) and a skip link
- Keyboard focus rings via `:focus-visible`; `.seg` deliberately does not set
  `overflow: hidden`, which would clip the offset ring on the viewer buttons
- The viewer's segmented controls keep `aria-pressed` in sync with the visual state,
  and each group is a labelled `role="group"`
- `prefers-reduced-motion` is honoured in two places. The CSS rule zeroes animation
  and transition durations, which covers CSS animation only — the page has none of its
  own, so it guards future additions. The viewer honours it separately in
  `viewer3d.js`, because `OrbitControls` damping runs from `requestAnimationFrame` and
  no CSS duration override can reach it: damping is switched off and auto-rotate no
  longer self-starts. Ticking Auto-rotate still works — that is an explicit request for
  motion. Gated by `check_page.py`'s reduced-motion context
- The viewer stage is `role="img"` with a descriptive label that states plainly it is
  not keyboard-operable and points at the static figure. (It is deliberately not
  `role="application"`, which would claim to handle keyboard input it does not.) The
  label is rewritten on every failure path, and `#viewer3d-loading` is a
  `role="status" aria-live="polite"` region so failures are announced, not just drawn
- The page carries no HTML table; the results are a generated figure with a
  figcaption, and all **nine** of its bars are named with their values in the image's
  `alt` text, so a screen-reader user gets the same numbers a sighted reader does.
  Checked by counting: each of the nine `mIoU` values in `data/results.json` whose
  `eval` is `test` appears in that `alt` string. It was ten until the four-sweep row
  came out of the data (see *Editing numbers*)
- Contrast: every text/background pair used meets WCAG AA on white. Disabled link
  labels were lifted from 2.61:1 to 4.83:1; state is carried by the dashed border

## File map

```
s2d2_website/
├── index.html
├── .nojekyll
├── README.md
├── LICENSE              MIT — this page's own code (see Publication status)
├── styles/
│   ├── tokens.css       design tokens (palette, type, measures)
│   └── site.css         everything else (replaces base/layout/components)
├── scripts/
│   ├── main.js          BibTeX copy button; watchdog for a three.js that never loads
│   └── viewer3d.js      interactive voxel comparison
├── data/
│   ├── results.json     test-set leaderboard table
│   └── perclass.json    val per-class IoU table
├── assets/
│   ├── favicon.svg
│   ├── og-card.jpg
│   ├── fonts/           cmu-serif-roman.woff2 + NOTICE.md (licence, provenance)
│   ├── figures/         PNG+WebP for every figure the page shows — paper Fig 1(a), 2,
│   │                    4, 5, 6, 9, 10 — plus results_chart.{png,webp,json}, generated
│   └── ply/             8 PLY point clouds (2 scenes × 4 views)
└── tools/
    ├── export_ply.py           voxel-grid → colored PLY exporter
    ├── make_results_chart.py   data/results.json → the results figure + its manifest
    ├── build_standalone.py     the site → one self-contained HTML file
    ├── check_page.py           47 behaviour assertions, 25 names + --selftest (18 arms)
    ├── check_content.py        site claims vs the built paper + --selftest (8 arms + 1 control)
    ├── check_artifact.py       the built single-file page under a harsh CSP + --selftest (6 arms)
    └── push_to_github.sh       publish (ungated since 2026-08-18: see Publication status)
```

Nothing in `assets/figures/` is unreferenced. Ten orphaned exports — paper Fig. 1(c)/(d)
and the Fig. 12 failure triptych, 2.3 MB left behind when those panels came off the page
— were deleted rather than shipped as publicly fetchable files no caption explains. If a
limitations figure goes back on the page, re-export it then.

## Develop locally

The page is build-free — just serve the repo root over HTTP. Opening `index.html`
directly via `file://` still renders the text and every figure (the results are a static
image now, not a hydrated table), but the **3D viewer will not run**: browsers refuse ES
module scripts over the file scheme, and the viewer's point clouds are fetched. The page
degrades to its documented failure note rather than breaking silently, and that path is
gated by `check_page.py`.

```bash
cd GSSC-project-page
python3 -m http.server 8099
```

Then open <http://localhost:8099>. Any free port works, but 8099 is what the
checks above expect; stop later with `pkill -f "http.server 8099"`.

## Citation

```bibtex
@misc{chen2026gssc,
  title         = {Generative Semantic Scene Completion},
  author        = {Chen, Shi and Ge, Weifeng},
  year          = {2026},
  eprint        = {2608.26737},
  archivePrefix = {arXiv},
  primaryClass  = {cs.CV},
  doi           = {10.48550/arXiv.2608.26737},
  url           = {https://arxiv.org/abs/2608.26737},
  note          = {Under review}
}
```
