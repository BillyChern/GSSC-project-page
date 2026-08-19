# Bundled webfont

`cmu-serif-roman.woff2` — the display face for headings on this page.

| | |
|---|---|
| Typeface | Computer Modern Unicode (CMU) Serif Roman, derived from Donald Knuth's Computer Modern |
| Obtained from | npm package [`computer-modern@0.1.3`](https://github.com/stevenpetryk/computer-modern) |
| Package license | MIT, as declared in that package's metadata |
| Upstream typeface | The CMU faces are distributed by their authors under the SIL Open Font License |

The two licenses cover different things: MIT is the packaging, OFL is the typeface
itself. Both permit redistribution of the font file alongside this page. For the
authoritative terms consult the upstream projects above rather than this summary,
which is a provenance record and not a legal opinion.

Why the file is vendored rather than linked: the page is also built into a single
self-contained HTML file (`tools/build_standalone.py`) that must render under a
Content-Security-Policy admitting no font host except Google Fonts, which does not
serve Computer Modern. The build inlines this file as a data: URI.
