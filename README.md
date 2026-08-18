# Generative Semantic Scene Completion — Project Page

Static, dependency-free project page for the paper
**Generative Semantic Scene Completion**.

The page is centred on **S²D²** (Structured Source Discrete Diffusion),
a one-step refiner that lifts any base SSC model by learning a correction
on the discrete probability simplex.

**Headline numbers (SemanticKITTI hidden test).** Every number below is indexed on the
paper's predicate — *causal, single-sweep, single-sample*: one sweep, no future moments, no
ensembling.

- **38.8 %** mIoU at one step ($N{=}1$) with **no test-time augmentation** — to our knowledge the
  best *causal, single-sweep, single-sample* result on the SemanticKITTI hidden test, **+2.1 pp**
  over the previous best published score (SCPNet, 36.7 %).
- **39.2 %** with four correction steps and an eight-view $D_4$ ensemble. This row is **excluded
  by the predicate** and is not the headline.
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

## Live site

Served from GitHub Pages:

- Production URL: <https://billychern.github.io/GSSC-project-page/>
- Repository: <https://github.com/BillyChern/GSSC-project-page>

A `.nojekyll` sentinel sits at the repo root so `assets/` is served as-is.

## What's on the page

Structure and styling follow the conventions measured across 30 accepted-paper project pages,
including 11 from this subfield (PaSCo, MonoScene, SceneRF, LiDPM, SemCity, TPVFormer, OccWorld,
SelfOcc, SurroundOcc, Occ3D, XCube): white ground, one accent used only for links, a single
humanist sans at 16 px, one centred column with prose at 760 px inside media at 1040 px, plain
noun headings, and no page animation — motion belongs to results, not to chrome.

| Section | What it shows |
|---|---|
| Header | Title, venue, authors (withheld by default while under review), four resource links |
| Teaser | Qualitative comparison, paper Fig. 6, immediately after the header |
| Abstract | The paper's abstract verbatim, plus the predicate that scopes every number |
| Method | One paragraph and the S²D² diagram, paper Fig. 5 |
| Data augmentation | One paragraph and the PS³ pipeline, paper Fig. 2 |
| Results | The paper's Table I in full, with rows outside the predicate greyed and named; per-class Table II with both Released and Retrain deltas |
| Interactive comparison | Three.js viewer over four views (input / base / ours / ground truth) on two rare-class frames; the IoU chips are the N=4 +D4-TTA configuration, as the paper states |
| Limitations | The failure case, paper Fig. 12, and the paper's own limitations paragraph |
| BibTeX | Copy-to-clipboard citation block |

Author names are hidden by default (`body[data-anon="true"]`) and revealed by the toggle in the
header; the preference persists in `localStorage`. Flip the default in `index.html` if the venue
turns out not to require it.

## Local preview

```bash
cd s2d2_website
python3 -m http.server 8000
# then open http://localhost:8000
```

Any static file server works — there's no build step.

## Regenerating the 3D viewer's PLY assets

The viewer loads 8 PLY point clouds from `assets/ply/`:

| Scene        | Views (sparse · SCPNet · S²D² · GT) |
|--------------|-------------------------------------|
| bicyclist    | `bicyclist_{sparse,scpnet,s2d2,gt}.ply` (seq 08 · 003096) |
| traffic-sign | `traffic_{sparse,scpnet,s2d2,gt}.ply` (seq 08 · 002870)   |

The hero preview reuses `bicyclist_s2d2.ply`, so there's no extra network cost.

Regenerate from source voxel data:

```bash
python tools/export_ply.py
```

The exporter reads SemanticKITTI GT voxel labels, SCPNet pre-computed
predictions, and our S²D² label outputs, colour-codes each voxel by class,
and writes ASCII PLY files ready for `three.js` `PLYLoader`.

## Single-blind submission

The page is single-blind: authors (Shi Chen, Weifeng Ge — Fudan University)
are visible by default and the bibtex carries the real names. The earlier
double-blind toggle / `data-anon` attribute / `scripts/anon.js` machinery
has been removed. The orphaned `scripts/anon.js` file remains on disk for
git history but is no longer referenced by `index.html` and can be deleted
in a future cleanup commit if desired.

## Filling in the release links

The hero has four release buttons. Each is currently a placeholder
(`href="#"` + `aria-disabled="true"`) so clicks are swallowed by the
smooth-scroll handler in `scripts/main.js` — the page never jumps to top.

| Button | `data-link` | Destination once live |
|---|---|---|
| Paper | `paper` | arXiv abstract page |
| Code | `code` | GitHub repo |
| Model | `model` | Pretrained checkpoint on HuggingFace |
| Dataset | `dataset` | Full synthetic dataset on HuggingFace |

Swap each placeholder when the URL lands, for example:

```html
<!-- from (placeholder) -->
<a class="btn" href="#" data-link="paper" aria-disabled="true" title="Paper (arXiv) coming soon.">Paper</a>
<!-- to (live) -->
<a class="btn" href="https://arxiv.org/abs/XXXX.YYYYY" data-link="paper" target="_blank" rel="noopener">Paper</a>
```

Remove the `aria-disabled` attribute and the tooltip `title` once the URL is live.

## Editing numbers

- **Main comparison (test set)**: `data/results.json` — 7 rows, ordered by mIoU,
  with `best:true` on the `S²D² + D₄ TTA` row and `ours:true` on both of our
  deployment configurations (`S²D² 1-step` and `S²D² + D₄ TTA`).
- **Per-class table (val set)**: `data/perclass.json` — SCPNet → S²D² val
  per-class IoUs with safety-class flags.

## Deploying to GitHub Pages

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

## Tech stack

- **Three.js** r161 for the main viewer and the hero preview (import map + CDN)
- **Google Fonts**: Instrument Serif (display) · IBM Plex Sans (body) · JetBrains Mono (code)
- Vanilla CSS with design tokens in `styles/tokens.css` — no Tailwind runtime
- Vanilla JS with `IntersectionObserver`, Clipboard API, and `ResizeObserver`
- No tracker, no analytics, no cookies

## Accessibility notes

- Semantic landmarks (`<nav>`, `<header>`, `<section>`, `<footer>`)
- Keyboard focus rings with `:focus-visible`
- `prefers-reduced-motion` disables fills, reveal transitions, the hero rotation, and the live-dot pulse
- Table headers announce `aria-sort` on click
- The viewer has a `role="application"` label describing mouse/touch controls
- The hero preview is announced with an `aria-label` on both the aside and the canvas mount
- Colour contrast checked against WCAG AA on body text

## File map

```
s2d2_website/
├── index.html
├── .nojekyll
├── README.md
├── styles/
│   ├── tokens.css       design tokens (palette, type, measures)
│   └── site.css         everything else (replaces base/layout/components)
├── scripts/
│   ├── main.js          renders both paper tables from data/*.json; BibTeX copy
│   ├── anon.js          author-anonymity toggle (default: revealed)
│   └── viewer3d.js      interactive voxel comparison
├── data/
│   ├── results.json     test-set leaderboard table
│   └── perclass.json    val per-class IoU table
├── assets/
│   ├── favicon.svg
│   ├── figures/         paper Fig 2 / Fig 3 / Fig 4 PNG exports
│   └── ply/             8 PLY point clouds (2 scenes × 4 views)
└── tools/
    └── export_ply.py    voxel-grid → colored PLY exporter
```

## Develop locally

The page is dependency-free — just serve the repo root over HTTP. Opening
`index.html` directly via `file://` will NOT populate the leaderboard or
per-class tables, because `scripts/main.js` loads `data/results.json` and
`data/perclass.json` via `fetch()`, which browsers block over the local
file scheme.

```bash
cd GSSC-project-page
python3 -m http.server 8000
```

Then open <http://localhost:8000>. Any free port works; stop later with
`pkill -f "http.server 8000"`.

## Citation

```bibtex
@article{chen2026gssc,
  title   = {Generative Semantic Scene Completion through Modeling the Underlying Geometry and Semantics in Point Clouds},
  author  = {Chen, Shi and Ge, Weifeng},
  journal = {IEEE Transactions on Pattern Analysis and Machine Intelligence (under review)},
  year    = {2026}
}
```
