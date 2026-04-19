# Generative Semantic Scene Completion — Project Page

Static, dependency-free project page for the paper
**Generative Semantic Scene Completion**.

The page is centered on **S²D²** (Structured Source Discrete Diffusion),
a one-step refiner that lifts any base SSC model by learning a correction
on the discrete probability simplex. On SemanticKITTI val it reaches
**38.54 %** mIoU (**+2.37** over the SCPNet base) while adding only
**107 ms** per frame on an H100 — no distillation, no multi-step rollout.

## Live site

Served from GitHub Pages:

- Production URL: https://billychern.github.io/GSSC-project-page/ (once Pages is enabled on the repo)
- Repository: https://github.com/BillyChern/GSSC-project-page

A `.nojekyll` sentinel sits at the repo root so `assets/` is served as-is.

## What's on the page

| Section | What it shows |
|---|---|
| Hero | Title, abstract lede, headline metrics, live 3D preview of an S²D² prediction (seq 08 frame 003096) |
| Abstract | Two-paragraph summary of the method and its headline numbers |
| Teaser (Fig 4) | Qualitative rare-class recovery on SemanticKITTI val |
| Method | Three plain-language cards + full pipeline figure + open-by-default "Architecture in detail" and "Equations" disclosures |
| 3D Viewer | Interactive Three.js comparison across four views (sparse / SCPNet / S²D² / GT) on two rare-class frames |
| Efficiency | Four-lane latency race (H100 80 GB, real measurements) |
| Results | Sortable main-results table plus per-class IoU table (SCPNet → S²D²) |
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

## Anonymous mode (double-blind review)

The top-right button toggles between anonymous and named mode. State is
remembered in `localStorage`. Default:

```html
<body data-anon="true">   <!-- show the 'Anonymous under review' placeholder -->
```

Flip to `data-anon="false"` to reveal authors by default; the button still
lets visitors toggle.

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

- Main comparison table: `data/results.json`
- Per-class table: `data/perclass.json`
- Inference-race latencies: the `LANES` object at the top of `scripts/latencyRace.js`

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
│   ├── tokens.css       design tokens (colors, fonts, spacing)
│   ├── base.css         reset + typography
│   ├── layout.css       nav, hero, section grids
│   └── components.css   buttons, tables, cards, controls, equations list
├── scripts/
│   ├── main.js          reveal, smooth scroll, table hydration
│   ├── anon.js          double-blind toggle
│   ├── tableSort.js     click-to-sort
│   ├── latencyRace.js   4-lane latency visualization
│   ├── viewer3d.js      main interactive point cloud viewer
│   └── heroCanvas.js    autorotating hero preview
├── data/
│   ├── results.json
│   └── perclass.json
├── assets/
│   ├── favicon.svg
│   ├── figures/         paper Fig 2 / Fig 3 / Fig 4 PNG exports
│   └── ply/             8 PLY point clouds (2 scenes × 4 views)
└── tools/
    └── export_ply.py    voxel-grid → colored PLY exporter
```
