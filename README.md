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

## Publication status — read before deploying

**GitHub Pages is deliberately NOT enabled.** `tools/push_to_github.sh` carries the
standing instruction: *"Do NOT enable GitHub Pages until the patents are filed."*
The repository is private and `https://billychern.github.io/GSSC-project-page/`
returns 404 by design, not by accident. The paper is also under review.

Do not follow the deploy steps below until that hold is lifted by the author.

> **This repository's HISTORY carries material the checkout does not.** `.git` is
> ~153 MB against a small working tree, because history retains 69 `.audit/`
> screenshots — full-page renders of an earlier, over-claiming version of this page,
> including one of the author-revealed state — plus two copies of
> `fig4_qualitative.pdf` at 18.2 MB and 16.6 MB. All were removed from tracking; none
> were removed from history, so anyone who clones a public copy can recover them.
> No credentials are present (the remote is SSH with no embedded token, and a scan of
> 200 commits for GitHub/AWS/private-key patterns found nothing).
>
> Two ways to handle it, both the author's call:
> 1. **Publish a clean snapshot** (recommended, non-destructive): create the public
>    repo, copy the working tree in, and make one initial commit. This private repo
>    keeps the full development history.
> 2. **Rewrite history** (`git filter-repo --path .audit --path-glob 'assets/**/*.pdf'
>    --invert-paths`), then force-push. This rewrites every commit hash and is
>    irreversible — do it only if you want the development history published minus
>    those paths.

- Repository: <https://github.com/BillyChern/GSSC-project-page> (private)
- Intended URL once released: <https://billychern.github.io/GSSC-project-page/>

A `.nojekyll` sentinel sits at the repo root so `assets/` is served as-is. Note the
consequence: with Jekyll disabled, Pages serves dotdirs verbatim, so anything like
`.audit/` that gets committed becomes publicly fetchable. It is gitignored for
exactly that reason.

## What's on the page

Structure and styling follow the conventions measured across 30 accepted-paper project pages,
including 11 from this subfield (PaSCo, MonoScene, SceneRF, LiDPM, SemCity, TPVFormer, OccWorld,
SelfOcc, SurroundOcc, Occ3D, XCube): white ground, one accent used only for links, a single
humanist sans at 16 px, one centred column with prose at 760 px inside media at 1040 px, plain
noun headings, and no page animation — motion belongs to results, not to chrome.

| Section | What it shows |
|---|---|
| Header | Title, venue, authors (**visible** by default — see *Author visibility*), four resource links |
| Teaser | Qualitative comparison, paper Fig. 6, immediately after the header |
| Abstract | The paper's abstract verbatim, plus the predicate that scopes every number |
| Method | One paragraph and the S²D² diagram, paper Fig. 5 |
| Data augmentation | One paragraph and the PS³ pipeline, paper Fig. 2 |
| Results | The paper's Table I in full, with rows outside the predicate greyed and named; per-class Table II with both Released and Retrain deltas |
| Interactive comparison | Three.js viewer over four views (input / base / ours / ground truth) on two rare-class frames; the IoU chips are the N=4 +D4-TTA configuration, as the paper states |
| Limitations | The failure case, paper Fig. 12, and the paper's own limitations paragraph |
| BibTeX | Copy-to-clipboard citation block |

Authors are **visible** by default: `index.html` ships `<body data-anon="false">`.
The header toggle flips it and the preference persists in `localStorage`. Set
`data-anon="true"` to ship hidden — but read *Author visibility* below first, because
the toggle is not blinding.

## Local preview

```bash
cd s2d2_website
python3 -m http.server 8099
# then open http://localhost:8099
```

Any static file server works — there's no build step. Port 8099 matches the
default the checks below expect.

## Checks

Two gates, each with a `--selftest` that injects one fault per assertion and
requires it to trip. A check never seen failing is not evidence of anything.

```bash
python3 -m http.server 8099 &          # check_page.py needs the site served
python tools/check_page.py             # 47 behaviour assertions; exit 1 on failure
python tools/check_page.py --selftest   # ~3 min: proves all 17 arms can fail

python tools/check_content.py           # site claims vs the built paper
python tools/check_content.py --selftest
```

`check_page.py` covers three viewports plus the print, no-JS, slow-load and
reduced-motion contexts, and deliberately pins earlier fixes: the viewer legend still discloses
its configuration, excluded table rows stay italic so the distinction survives
forced-colors mode, anonymous mode leaks no identifier, and console errors are
visible.

`check_content.py` compares the page against `/workspace/GSSC-paper/pdf`
(`--paper` to point elsewhere): every "Source: paper Fig. N / Table X" caption
must resolve to a float whose caption is about the same thing, and every number
in the prose and `data/*.json` must appear in the paper. **Run it after any float
moves in the manuscript** — moving one float renumbers every figure after it, and
these captions cite six floats by number.

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
configuration sits outside the paper's headline predicate, which is why the
viewer's legend says so on the page.

Regenerate from source voxel data:

```bash
python tools/export_ply.py
```

The exporter reads SemanticKITTI GT voxel labels, SCPNet pre-computed
predictions, and our S²D² label outputs, colour-codes each voxel by class,
and writes ASCII PLY files ready for `three.js` `PLYLoader`.

## Author visibility

Authors are visible by default (`<body data-anon="false">`) and the BibTeX
carries the real names. `scripts/anon.js` IS wired: the header toggle flips
`body[data-anon]`, `styles/site.css` hides `.identity` and reveals the withheld
notice, and the preference persists in `localStorage`. Verified: in anonymous mode
no author identifier survives the rendered page, and the BibTeX author field
becomes "Author names withheld".

> **The toggle is NOT blinding, and must not be relied on for a double-anonymous
> submission.** It hides on-page text only. `og:url` and `og:image` hardcode
> `billychern.github.io`; CSS cannot reach meta tags, crawlers need them absolute
> and ignore JS-set metadata, and the hosting URL itself carries the username — so
> a shared link still previews the author's account, and the address bar always
> did. If the venue is double-anonymous, host the page under a non-identifying
> account or an anonymising service. Setting `data-anon="true"` is the text layer,
> not the requirement.

## Release links

Four slots sit under the author block. Three are inert
`<span class="btn" role="link" aria-disabled="true">` elements — they are not
anchors and carry no `href`, so there is no dead link to click. The fourth, the
SemanticKITTI leaderboard, is a live `<a>`.

To publish one, replace the `<span>` with
`<a class="btn" href="..." target="_blank" rel="noopener">Code</a>` and drop the
sentence under the row that says the release happens on publication. Do not link
`github.com/BillyChern/GSSC-S2D2` until it actually resolves; it currently
returns 404, and the honest inert state is deliberate.

## Editing numbers

- **Main comparison**: `data/results.json` — 17 rows across both splits, mirroring
  paper Table I. Keys: `eval` (`test`|`val`), `ours`, and `excluded` for rows
  outside the paper's predicate (TALoS, our D₄ row, the four-sweep entry). There is
  no `best` flag: `scripts/main.js` COMPUTES the best eligible cell per split, so
  the table cannot drift from the predicate it claims to apply. Never hand-bold a
  row, and never mark an `excluded` row as best — the 39.2 D₄ row is excluded.
- **Per-class table**: `data/perclass.json` — paper Table II: base IoU plus both
  the Released Δ and the Retrain Δ, the VRU-IoU row, and `disclaimed: true` on
  motorcyclist, whose released +8.3 does not reproduce (retrain recovers +0.3).

## Deploying to GitHub Pages

> **Gated.** See *Publication status* above: do not perform these steps
> until the patent filing is complete and the author lifts the hold.

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

- **three.js** r160, import map from unpkg, for the voxel viewer
- **Google Fonts**: IBM Plex Sans only (400/500/600). Monospace comes from the
  system stack; the display serif and JetBrains Mono were dropped in the rebuild
- Vanilla CSS, tokens in `styles/tokens.css`, everything else in `styles/site.css`
- Vanilla JS: `fetch` for the two JSON tables, Clipboard API for BibTeX. No build step
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
- Every table has a `<caption>`; numeric cells use `tabular-nums`
- Contrast: every text/background pair used meets WCAG AA on white. Disabled link
  labels were lifted from 2.61:1 to 4.83:1; state is carried by the dashed border

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
│   ├── figures/         PNG+WebP exports of paper Fig 2 / Fig 5 / Fig 6 / Fig 12
│   └── ply/             8 PLY point clouds (2 scenes × 4 views)
└── tools/
    ├── export_ply.py       voxel-grid → colored PLY exporter
    ├── check_page.py       39 behaviour assertions + --selftest
    ├── check_content.py    site claims vs the built paper + --selftest
    └── push_to_github.sh   publish (gated: see Publication status)
```

## Develop locally

The page is build-free — just serve the repo root over HTTP. Opening
`index.html` directly via `file://` will NOT populate the leaderboard or
per-class tables, because `scripts/main.js` loads `data/results.json` and
`data/perclass.json` via `fetch()`, which browsers block over the local
file scheme.

```bash
cd GSSC-project-page
python3 -m http.server 8099
```

Then open <http://localhost:8099>. Any free port works, but 8099 is what the
checks above expect; stop later with `pkill -f "http.server 8099"`.

## Citation

```bibtex
@article{chen2026gssc,
  title   = {Generative Semantic Scene Completion},
  author  = {Chen, Shi and Ge, Weifeng},
  journal = {IEEE Transactions on Pattern Analysis and Machine Intelligence (under review)},
  year    = {2026}
}
```
