three.js r160, vendored from node_modules/three@0.160.0 on 2026-08-26.

Why: the served page used to import three from unpkg.com. That was a single point
of failure with no SRI and no fallback -- if unpkg had a bad day, every 3D scene on
the page died and the page gave no sign why. These three files are the complete
module graph: OrbitControls and PLYLoader import only from 'three'.

Do not edit. To upgrade, bump node_modules/three, re-copy these three files, and
update the version in index.html's import map AND tools/build_standalone.py (THREE).

MIT License -- Copyright (c) 2010-2024 three.js authors. See LICENSE-three.txt.
