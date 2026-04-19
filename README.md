# S²D² Project Page

A static, dependency-free project page for the paper **Structured Source Discrete Diffusion for Semantic Scene Completion**.

## Local preview

```bash
cd s2d2_website
python3 -m http.server 8000
# open http://localhost:8000
```

Anything that serves static files will work; no build step.

## Interactive viewer data

The 3D viewer loads 8 PLY point clouds from `assets/ply/`:

| Scene        | Views (sparse · SCPNet · S²D² · GT) |
|--------------|-------------------------------------|
| bicyclist    | `bicyclist_{sparse,scpnet,s2d2,gt}.ply` |
| traffic-sign | `traffic_{sparse,scpnet,s2d2,gt}.ply`   |

Regenerate from source voxel data:

```bash
python tools/export_ply.py
```

The exporter reads SemanticKITTI ground-truth voxel labels, SCPNet pre-computed
predictions, and our S²D² label outputs, colour-codes each voxel by class, and
writes ASCII PLY files ready for `three.js` `PLYLoader`.

## Anonymous mode

The top-right button toggles between anonymous (for double-blind review) and
named mode. The state is remembered in `localStorage`. When the paper is
accepted, flip the default in `index.html`:

```html
<body data-anon="true">   <!-- default; show "Anonymous under review" -->
```

Change `data-anon="true"` to `data-anon="false"` to make the public default
show authors. The button still lets visitors toggle.

## Editing numbers

Main comparison table: `data/results.json`
Per-class table:      `data/perclass.json`
Inference timings:    edit the `LANES` object at the top of `scripts/latencyRace.js`

## Deploying to GitHub Pages

1. Create a repo and push this directory to `gh-pages` branch (or `main` with Pages
   set to `/ (root)`).
2. The `.nojekyll` file at the root disables Jekyll so `assets/` loads cleanly.
3. Enable Pages in repo settings.

Example workflow (push to `main`):

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

- **Three.js** r161 (point-cloud viewer, loaded via import map + CDN)
- **Google Fonts**: Instrument Serif (display) · IBM Plex Sans (body) · JetBrains Mono (code)
- Vanilla CSS with design tokens — no Tailwind runtime
- Vanilla JS with IntersectionObserver, Clipboard API, and `ResizeObserver`
- No tracker, no analytics, no cookie banner — the page is purely read-only.

## Accessibility

- Semantic HTML landmarks (`<nav>`, `<header>`, `<section>`, `<footer>`)
- Keyboard focus rings with `:focus-visible`
- `prefers-reduced-motion` disables transitions and animated fills
- Table headers announce `aria-sort` on click
- Viewer has a role=application label describing mouse/touch controls
- Colour contrast checked against WCAG AA on body text

## File map

```
s2d2_website/
├── index.html
├── .nojekyll
├── styles/
│   ├── tokens.css       design tokens (colors, fonts, spacing)
│   ├── base.css         reset + typography
│   ├── layout.css       nav, hero, section grids
│   └── components.css   buttons, tables, cards, controls
├── scripts/
│   ├── main.js          reveal, smooth scroll, table hydration
│   ├── anon.js          double-blind toggle
│   ├── tableSort.js     click-to-sort
│   ├── latencyRace.js   3-lane latency visualization
│   └── viewer3d.js      three.js point cloud viewer
├── data/
│   ├── results.json
│   └── perclass.json
├── assets/
│   ├── favicon.svg
│   ├── figures/         paper Fig 2, Fig 4 PNG exports
│   └── ply/             8 PLY point clouds (2 scenes × 4 views)
└── tools/
    └── export_ply.py    voxel-grid → colored-PLY exporter
```
