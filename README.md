# Generative Semantic Scene Completion — Project Page

Static, dependency-free project page for the paper
**Generative Semantic Scene Completion**.

The page is centred on **S²D²** (Structured Source Discrete Diffusion),
a one-step refiner that lifts any base SSC model by learning a correction
on the discrete probability simplex.

**Headline numbers (SemanticKITTI hidden test leaderboard, single-frame single-sample):**

- **39.2 %** mIoU with $D_4$ test-time augmentation — to our knowledge **the best single-frame single-sample result on the leaderboard to date**, +1.3 % over the previous best (TALoS, 37.9 %), which had held the leaderboard for ~2 years.
- **38.8 %** mIoU at the **1-step real-time** configuration ($N{=}1$, no TTA; 107 ms / 9.33 FPS marginal cost on H100), still +0.9 % over TALoS at no test-time-augmentation cost.
- **+2.37 pp** mIoU added by S²D² on top of the frozen SCPNet base — S²D² is base-agnostic (it likewise lifts JS3C-Net by +3.3 and LMSCNet by +1.8); we report on the SCPNet base for an apples-to-apples comparison with TALoS.

**Validation set:** 38.54 % mIoU (+2.37 over the SCPNet port at 36.17 %).
**LiDAR-only BEV (secondary task):** 36.1 % mIoU, +9.1 over the previous best dedicated 2D method.
**Zero-shot transfer:** the frozen SemanticKITTI checkpoint also lifts the base on two unseen domains (no fine-tuning) — SemanticPOSS +5.5 mIoU and SSCBench-KITTI360 +1.4 completion-IoU.

## Live site

Served from GitHub Pages:

- Production URL: <https://billychern.github.io/GSSC-project-page/>
- Repository: <https://github.com/BillyChern/GSSC-project-page>

A `.nojekyll` sentinel sits at the repo root so `assets/` is served as-is.

## What's on the page

| Section | What it shows |
|---|---|
| Hero | Title, abstract lede, four headline metrics (39.2 %, +1.3 over TALoS, 107 ms, 1 step), live 3D preview of an S²D² prediction (seq 08 frame 003096) |
| Abstract | Two-paragraph summary leading with the test SOTA story and the real-time 1-step result |
| Teaser (Fig 4) | Qualitative rare-class recovery on SemanticKITTI val |
| Method | Three plain-language cards + full pipeline figure + open-by-default "Architecture in detail" disclosure |
| 3D Viewer | Interactive Three.js comparison across four views (sparse / SCPNet / S²D² / GT) on two rare-class frames |
| Efficiency | Four-lane latency race with explicit log-warp disclosure (real H100 80 GB measurements) |
| Results | Sortable test-set leaderboard table (LMSCNet → SSA-SC → JS3C-Net → SCPNet → TALoS → S²D² 1-step / plain N=4 / +D₄ TTA) plus per-class IoU table |
| BibTeX | Copy-to-clipboard citation block |

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

- **Main comparison (test set)**: `data/results.json` — 8 rows, ordered by mIoU,
  with `best:true` on the `S²D² + D₄ TTA` row and `ours:true` on all three of
  our deployment configurations.
- **Per-class table (val set)**: `data/perclass.json` — SCPNet → S²D² val
  per-class IoUs with safety-class flags.
- **Inference-race latencies**: the `LANES` object at the top of
  `scripts/latencyRace.js`. Real Apr-2026 contention-free H100 measurements:
  SCPNet base 202 ms · S²D² 1-step 107 ms · 100-step 10 784 ms.

## Speed-race time-warp disclosure

The four-lane latency race in §Efficiency uses **log-warped UI pacing** so
the 100-step lane completes its bar in ~6 s of UI time instead of the
actual ~11 s — without the warp the contrast across lanes would not be
visible in a single viewing.

- **Bar widths** are linearly proportional to the real measured latency.
- **Numeric readouts** beside each bar are the real measured ms.
- Only the **per-pixel animation pacing** is compressed.

The disclosure is rendered directly under the race widget in
`index.html`, so visitors can see the caveat without reading source.

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
│   ├── tokens.css       design tokens (colours, fonts, spacing)
│   ├── base.css         reset + typography
│   ├── layout.css       nav, hero, section grids
│   └── components.css   buttons, tables, cards, controls
├── scripts/
│   ├── main.js          reveal, smooth scroll, table hydration
│   ├── anon.js          orphaned (no longer referenced; can delete)
│   ├── tableSort.js     click-to-sort
│   ├── latencyRace.js   4-lane latency visualisation (log-warp pacing)
│   ├── viewer3d.js      main interactive point cloud viewer
│   └── heroCanvas.js    autorotating hero preview
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
  title   = {Generative Semantic Scene Completion},
  author  = {Chen, Shi and Ge, Weifeng},
  journal = {Submitted to IEEE Transactions on Pattern Analysis and Machine Intelligence},
  year    = {2026}
}
```
