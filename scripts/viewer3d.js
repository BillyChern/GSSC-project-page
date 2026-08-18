/* =============================================================
   viewer3d.js — Three.js-based interactive point cloud viewer.
   Loads PLY voxel clouds and lets the user switch between
   (scene × view) combinations while keeping the camera pose.
   ============================================================= */

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { PLYLoader } from 'three/addons/loaders/PLYLoader.js';

// SemanticKITTI palette — must stay in lockstep with tools/export_ply.py
// CLASS_RGB. Key = class_id, value = RGB triplet in [0, 255].
const CLASS_RGB_LUT = {
   1: [100, 150, 245],   2: [100, 230, 245],   3: [ 30,  60, 150],
   4: [ 80,  30, 180],   5: [  0,   0, 255],   6: [255,  30,  30],
   7: [255,  40, 200],   8: [150,  30,  90],   9: [255,   0, 255],
  10: [255, 150, 255],  11: [ 75,   0,  75],  12: [175,   0,  75],
  13: [255, 200,   0],  14: [255, 120,  50],  15: [  0, 175,   0],
  16: [135,  60,   0],  17: [150, 240,  80],  18: [255, 240, 150],
  19: [255,   0,   0],
};
// Reverse lookup: "R,G,B" (0..255) -> class_id. Rebuilt once.
const RGB_TO_CLASS = Object.fromEntries(
  Object.entries(CLASS_RGB_LUT).map(([k, v]) => [v.join(','), Number(k)])
);
// Same rare-class set as tools/export_ply.py RARE_CLASS_BOOST:
// bicycle, motorcycle, other-vehicle, person, bicyclist, motorcyclist,
// pole, traffic-sign. Eight classes.
const RARE_CLASSES = new Set([2, 3, 5, 6, 7, 8, 18, 19]);

// Walk a float32 [n*3] colour buffer and produce a Uint8Array flag per
// instance: 1 if the voxel's colour maps to a rare class, else 0.
/* three's PLYLoader calls convertSRGBToLinear() on vertex colours, so the buffer
   is linear-light while CLASS_RGB_LUT is sRGB 0-255. Without undoing the transfer
   the reverse lookup matched only the classes whose channels are all 0 or 255 --
   17 of 19 missed, which is why "Highlight rare classes" appeared to do nothing. */
function linearToSRGB(c) {
  return c <= 0.0031308 ? c * 12.92 : 1.055 * Math.pow(c, 1 / 2.4) - 0.055;
}

function computeRareMask(colors, n) {
  const mask = new Uint8Array(n);
  for (let i = 0; i < n; i++) {
    const r = Math.round(linearToSRGB(colors[3 * i    ]) * 255);
    const g = Math.round(linearToSRGB(colors[3 * i + 1]) * 255);
    const b = Math.round(linearToSRGB(colors[3 * i + 2]) * 255);
    const cls = RGB_TO_CLASS[r + ',' + g + ',' + b];
    mask[i] = cls !== undefined && RARE_CLASSES.has(cls) ? 1 : 0;
  }
  return mask;
}

// Asset map: each scene has four views. Files live under assets/ply/.
// If a PLY is missing we fall back to a procedurally-generated cube
// of colored voxels so the viewer never looks broken.
const SCENES = {
  'bicyclist': {
    label: 'Bicyclist — SemanticKITTI seq 08 · frame 003096',
    stats: { scp: 31.3, ours: 56.9, delta: '+25.6', klass: 'bicyclist IoU' },
    plys: {
      'sparse': 'assets/ply/bicyclist_sparse.ply',
      'scpnet': 'assets/ply/bicyclist_scpnet.ply',
      's2d2':   'assets/ply/bicyclist_s2d2.ply',
      'gt':     'assets/ply/bicyclist_gt.ply',
    }
  },
  'motorcyclist': {
    label: 'Motorcyclist — SemanticKITTI seq 08 · frame 001417',
    stats: { scp: 33.0, ours: 62.3, delta: '+29.3', klass: 'motorcyclist IoU' },
    plys: {
      'sparse': 'assets/ply/motorcyclist_sparse.ply',
      'scpnet': 'assets/ply/motorcyclist_scpnet.ply',
      's2d2':   'assets/ply/motorcyclist_s2d2.ply',
      'gt':     'assets/ply/motorcyclist_gt.ply',
    }
  }
};

const stage = document.getElementById('viewer3d-stage');
const loadingEl = document.getElementById('viewer3d-loading');
if (stage) boot();

// (R5) No-WebGL fallback: if the browser cannot create a WebGL context the
// spinner would otherwise spin forever. Replace the loading element with a
// visible in-stage note that links to the static qualitative figure (the
// #teaser panel) so a no-WebGL visitor still gets the comparison content.
function showNoWebGLFallback() {
  if (!loadingEl) return;
  loadingEl.classList.remove('is-hidden');
  while (loadingEl.firstChild) loadingEl.removeChild(loadingEl.firstChild);
  loadingEl.classList.add('viewer3d__fallback');
  const note = document.createElement('p');
  note.className = 'viewer3d__fallback-text';
  note.append('Your browser could not start WebGL, so the interactive 3D viewer is unavailable. ');
  const link = document.createElement('a');
  link.href = '#teaser';
  link.textContent = 'View the static qualitative comparison instead.';
  note.appendChild(link);
  loadingEl.appendChild(note);
}

// A scene file that cannot be fetched or parsed shows this instead of geometry.
// Mirrors showNoWebGLFallback: say what happened, and point at the static figure
// that carries the same comparison.
function showLoadFailure() {
  if (!loadingEl) return;
  loadingEl.classList.remove('is-hidden');
  while (loadingEl.firstChild) loadingEl.removeChild(loadingEl.firstChild);
  loadingEl.classList.add('viewer3d__fallback');
  const note = document.createElement('p');
  note.className = 'viewer3d__fallback-text';
  note.append('This scene could not be loaded, so nothing is drawn rather than a stand-in. ');
  const link = document.createElement('a');
  link.href = '#abstract';
  link.textContent = 'The static qualitative comparison is above.';
  note.appendChild(link);
  loadingEl.appendChild(note);
}

function boot() {
  // Probe first. three's WebGLRenderer does not reliably throw when no context
  // can be created -- it still constructs and still appends a canvas -- so the
  // try/catch below is not sufficient on its own, and a reader with WebGL
  // disabled saw a 520px black box with per-scene IoU numbers printed under it.
  try {
    const probe = document.createElement('canvas');
    if (!(probe.getContext('webgl2') || probe.getContext('webgl'))) {
      console.warn('No WebGL context available; showing the static-figure fallback.');
      showNoWebGLFallback();
      return;
    }
  } catch (e) {
    showNoWebGLFallback();
    return;
  }

  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({
      antialias: true, alpha: false, powerPreference: 'high-performance'
    });
  } catch (e) {
    console.warn('WebGL unavailable; showing static-figure fallback in viewer', e);
    showNoWebGLFallback();
    return;
  }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setClearColor(0x0B0E14, 1);
  // The stage carries role=application + aria-label describing the viewer;
  // hide the raw canvas so SR users get the stage's name, not a bare canvas.
  renderer.domElement.setAttribute('aria-hidden', 'true');
  stage.appendChild(renderer.domElement);

  const scene  = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x0B0E14, 0.005);

  const camera = new THREE.PerspectiveCamera(45, 16/10, 0.1, 2000);
  // Hand-tuned default pose: close enough to read individual voxels at a
  // glance on first load, but far enough that drag-to-orbit still reveals
  // the scene in full. Matches the framing of the hero preview so the
  // two viewers feel consistent.
  camera.position.set(55, 42, 55);
  camera.lookAt(0, 0, 0);

  // 3-light rig that mimics the Blender "dramatic" preset used in
  // the paper renders so Lambert-shaded InstancedMesh cubes read with
  // proper depth. Warm key from above-right, cool fill opposite,
  // warm rim from behind; ambient floor set low enough that normal
  // variation is visible but the unlit back faces don't go black.
  scene.add(new THREE.AmbientLight(0xFFFFFF, 0.55));
  const key = new THREE.DirectionalLight(0xFFE2BE, 1.1);
  key.position.set(60, 120, 40);
  scene.add(key);
  const fill = new THREE.DirectionalLight(0x9DB7D8, 0.45);
  fill.position.set(-80, 50, -60);
  scene.add(fill);
  const rim = new THREE.DirectionalLight(0xFFAE60, 0.35);
  rim.position.set(-20, 20, -90);
  scene.add(rim);

  // Controls
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.rotateSpeed = 0.9;
  controls.zoomSpeed = 0.8;
  controls.minDistance = 12;
  controls.maxDistance = 400;
  controls.target.set(0, 0, 0);

  // --- helpers for ego-marker and grid ---
  const egoGroup = new THREE.Group();
  egoGroup.add(makeEgoMarker());
  scene.add(egoGroup);

  const grid = new THREE.GridHelper(200, 20, 0x232A38, 0x18202C);
  grid.position.y = -0.5;
  scene.add(grid);

  // --- current point cloud object ---
  let currentCloud = null;
  let currentScene = 'bicyclist';
  let currentView  = 's2d2';

  const loader = new PLYLoader();

  const sceneCenters = new Map();
  /* Every load takes a ticket. A switch made while a fetch is in flight bumps the
     counter, so the slower request discards its own result instead of painting a
     scene the controls no longer claim. */
  let loadGeneration = 0;

  async function loadAndShow(sceneId, viewId) {
    const myGeneration = ++loadGeneration;
    currentScene = sceneId;
    currentView  = viewId;
    const url = SCENES[sceneId].plys[viewId];
    showLoading(true);

    let geometry;
    try {
      geometry = await new Promise((res, rej) => {
        loader.load(url, res, undefined, rej);
      });
    } catch (e) {
      // A scene that will not load must FAIL VISIBLY. The previous behaviour here
      // was to synthesise a seeded lattice "so the viewer always shows something" —
      // which renders fabricated geometry inside the panel labelled with our method
      // name, where a reader has every reason to read it as model output. Showing
      // nothing is strictly better than showing something invented.
      console.error(`PLY ${url} failed to load; not substituting synthetic geometry.`, e);
      showLoadFailure();
      return;   // draw nothing; rethrowing left an unhandled rejection
    }

    if (myGeneration !== loadGeneration) return;   // superseded while fetching

    // A truncated or empty PLY does NOT make the loader reject: it parses the
    // header and hands back a geometry with no vertices. Without this check the
    // stage showed a blank canvas and the readout below still printed per-scene
    // IoU numbers -- asserting a result for a scene that was never drawn.
    // A file whose header lies about its vertex count parses to a handful of
    // points rather than zero, so a strict ==0 test let a two-voxel remnant render
    // under the scene's real IoU numbers. The floor is set far below any genuine
    // view: the sparsest shipped cloud (traffic_sparse) carries 1,767 vertices,
    // so 64 cannot reject real data and cannot accept a corrupt remnant.
    const MIN_VERTICES = 64;
    const vertexCount = geometry.attributes.position ? geometry.attributes.position.count : 0;
    if (vertexCount < MIN_VERTICES) {
      console.error(`PLY ${url} parsed to ${vertexCount} vertices (floor ${MIN_VERTICES}); treating as a load failure.`);
      showLoadFailure();
      return;
    }

    // Normalize colour: our exporter writes red/green/blue uchar; we
    // want a single per-vertex "color" float attribute in [0, 1] that
    // we can read back when building InstancedMesh colours below.
    const n = geometry.attributes.position.count;
    let cols;
    if (geometry.getAttribute('color')) {
      cols = geometry.getAttribute('color').array;
    } else if (geometry.getAttribute('red')) {
      cols = new Float32Array(n * 3);
      const r = geometry.attributes.red.array;
      const g = geometry.attributes.green.array;
      const b = geometry.attributes.blue.array;
      for (let i = 0; i < n; i++) {
        cols[3*i  ] = r[i] / 255;
        cols[3*i+1] = g[i] / 255;
        cols[3*i+2] = b[i] / 255;
      }
    } else {
      cols = new Float32Array(n * 3).fill(0.75);
    }

    // Per-instance rare/common mask, derived by reverse-looking each PLY
    // voxel colour back to its SemanticKITTI class ID. Palette matches
    // CLASS_RGB in tools/export_ply.py and RARE_CLASS_BOOST below.
    const isRare = computeRareMask(cols, n);

    // Centre on ONE reference per scene, not per view. Re-centring each cloud on
    // its own bounding box shifted the sparse scan relative to the dense
    // completions, so the four views were not spatially comparable — which is the
    // whole point of holding the camera still across a switch.
    geometry.computeBoundingBox();
    let center = sceneCenters.get(sceneId);
    if (!center) {
      center = new THREE.Vector3();
      geometry.boundingBox.getCenter(center);
      sceneCenters.set(sceneId, center);
    }
    const pos = geometry.attributes.position.array;

    // Instanced solid cubes at 0.2 m each — matches the voxel size used
    // by tools/export_ply.py and by the headless Blender paper pipeline,
    // giving the website the same chunky-voxel look as the figures in
    // the paper rather than a soft point-cloud.
    const VOXEL_SIZE = 0.2;
    const boxGeo = new THREE.BoxGeometry(VOXEL_SIZE, VOXEL_SIZE, VOXEL_SIZE);
    const material = new THREE.MeshLambertMaterial({ vertexColors: false });
    const inst = new THREE.InstancedMesh(boxGeo, material, n);
    inst.instanceMatrix.setUsage(THREE.StaticDrawUsage);
    inst.frustumCulled = false;

    const tmp = new THREE.Object3D();
    const tmpColor = new THREE.Color();
    for (let i = 0; i < n; i++) {
      const x = pos[3 * i    ] - center.x;
      const y = pos[3 * i + 1] - center.y;
      const z = pos[3 * i + 2] - center.z;
      tmp.position.set(x, y, z);
      tmp.updateMatrix();
      inst.setMatrixAt(i, tmp.matrix);
      tmpColor.setRGB(cols[3 * i], cols[3 * i + 1], cols[3 * i + 2]);
      inst.setColorAt(i, tmpColor);
    }
    inst.instanceMatrix.needsUpdate = true;
    if (inst.instanceColor) inst.instanceColor.needsUpdate = true;
    inst.rotateX(-Math.PI / 2); // voxel Z-up -> scene Y-up

    // Stash base colors + rare mask + centered positions so the
    // "Highlight rare classes" checkbox can rescale rare-class instances
    // and boost their colour saturation without re-parsing the PLY.
    // Positions are post-centering, in world units.
    const basePositions = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) {
      basePositions[3 * i    ] = pos[3 * i    ] - center.x;
      basePositions[3 * i + 1] = pos[3 * i + 1] - center.y;
      basePositions[3 * i + 2] = pos[3 * i + 2] - center.z;
    }
    inst.userData.baseColors = cols;
    inst.userData.isRare = isRare;
    inst.userData.basePositions = basePositions;

    if (currentCloud) scene.remove(currentCloud);
    currentCloud = inst;
    scene.add(inst);
    applyHighlight(currentCloud, isHighlightOn());

    // Update stats panel
    updateStats(sceneId);
    showLoading(false);
  }

  function showLoading(v) {
    if (!loadingEl) return;
    loadingEl.classList.toggle('is-hidden', !v);
  }

  function updateStats(sceneId) {
    const s = SCENES[sceneId].stats;
    const row = document.getElementById('viewer3d-stat-row');
    if (!row) return;
    /* `klass` and `label` were carried in SCENES but never rendered; the readout
       now names which class and which frame the numbers refer to. */
    const map = { scp: s.scp.toFixed(1) + '%', ours: s.ours.toFixed(1) + '%', delta: s.delta + '\u00A0pp',
                  klass: s.klass, label: SCENES[sceneId].label };
    row.querySelectorAll('[data-stat]').forEach((cell) => {
      const k = cell.dataset.stat;
      if (map[k] !== undefined) cell.textContent = map[k];
    });
    row.setAttribute('data-ready', '');
  }

  function makeEgoMarker() {
    // A small glowing ring at the origin to indicate sensor position.
    const group = new THREE.Group();
    const ringGeom = new THREE.RingGeometry(1.4, 2.0, 32);
    const ringMat  = new THREE.MeshBasicMaterial({ color: 0xF19340, side: THREE.DoubleSide, transparent: true, opacity: 0.85 });
    const ring = new THREE.Mesh(ringGeom, ringMat);
    ring.rotateX(-Math.PI / 2);
    group.add(ring);
    const dot = new THREE.Mesh(new THREE.SphereGeometry(0.6, 12, 12),
      new THREE.MeshBasicMaterial({ color: 0xF19340 }));
    group.add(dot);
    return group;
  }

  // Resize handling
  function resize() {
    const w = stage.clientWidth;
    const h = stage.clientHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }
  new ResizeObserver(resize).observe(stage);
  resize();

  // Pause the render loop when the viewer is scrolled off-screen so the
  // continuous Three.js draw (and its per-frame GPU work) does not run —
  // and resumes cleanly on re-entry. This also
  // removes the steady "GPU stall due to ReadPixels" perf warnings that
  // a never-idle render loop produces while the canvas is not visible.
  let onScreen = true;
  const vio = new IntersectionObserver((entries) => {
    onScreen = entries[0].isIntersecting;
  }, { threshold: 0.01 });
  vio.observe(stage);

  // Animation loop
  function frame() {
    controls.update();
    if (onScreen) renderer.render(scene, camera);
    requestAnimationFrame(frame);
  }
  frame();

  // UI wiring
  const sceneBtns = document.querySelectorAll('.seg__btn[data-scene]');
  const viewBtns  = document.querySelectorAll('.seg__btn[data-view]');

  sceneBtns.forEach((b) => {
    b.addEventListener('click', () => {
      /* aria-pressed must track the visual state, not just the class, or the
         control lies to assistive tech and the highlight never moves. */
      sceneBtns.forEach((x) => { x.classList.remove('is-active'); x.setAttribute('aria-pressed', 'false'); });
      b.classList.add('is-active'); b.setAttribute('aria-pressed', 'true');
      loadAndShow(b.dataset.scene, currentView);
    });
  });
  viewBtns.forEach((b) => {
    b.addEventListener('click', () => {
      viewBtns.forEach((x) => { x.classList.remove('is-active'); x.setAttribute('aria-pressed', 'false'); });
      b.classList.add('is-active'); b.setAttribute('aria-pressed', 'true');
      loadAndShow(currentScene, b.dataset.view);
    });
  });

  // Checkboxes
  const egoChk = document.getElementById('viewer3d-ego');
  if (egoChk) egoChk.addEventListener('change', () => egoGroup.visible = egoChk.checked);
  const autoChk = document.getElementById('viewer3d-autorotate');
  if (autoChk) autoChk.addEventListener('change', () => controls.autoRotate = autoChk.checked);
  controls.autoRotateSpeed = 0.6;

  const hlChk = document.getElementById('viewer3d-highlight');
  if (hlChk) hlChk.addEventListener('change', () => {
    if (!currentCloud) return;
    applyHighlight(currentCloud, hlChk.checked);
  });

  // When "Highlight rare classes" is ON, make the 8 rare classes visually
  // dominant by (i) scaling their cubes up 1.6x and (ii) shifting their
  // colour toward white to boost perceived brightness. Common classes
  // are left completely unchanged (not dimmed) so the scene stays
  // readable as a scene. Toggling OFF restores the default per-voxel
  // colour and scale. We rewrite both instanceMatrix and instanceColor
  // in place rather than rebuilding the mesh.
  function applyHighlight(mesh, on) {
    const base = mesh.userData && mesh.userData.baseColors;
    const rare = mesh.userData && mesh.userData.isRare;
    const basePos = mesh.userData && mesh.userData.basePositions;
    if (!base || !rare || !basePos) return;

    const RARE_SCALE = on ? 1.6 : 1.0;
    const RARE_LIGHTEN = 0.35; // lerp toward white by this much when ON
    const c = new THREE.Color();
    const tmp = new THREE.Object3D();
    const count = rare.length;

    for (let i = 0; i < count; i++) {
      const x = basePos[3 * i    ];
      const y = basePos[3 * i + 1];
      const z = basePos[3 * i + 2];
      tmp.position.set(x, y, z);
      tmp.rotation.set(0, 0, 0);

      const isR = rare[i] === 1;
      if (isR && on) {
        tmp.scale.set(RARE_SCALE, RARE_SCALE, RARE_SCALE);
        const br = base[3 * i    ];
        const bg = base[3 * i + 1];
        const bb = base[3 * i + 2];
        c.setRGB(
          br + (1 - br) * RARE_LIGHTEN,
          bg + (1 - bg) * RARE_LIGHTEN,
          bb + (1 - bb) * RARE_LIGHTEN,
        );
      } else {
        tmp.scale.set(1, 1, 1);
        c.setRGB(base[3 * i], base[3 * i + 1], base[3 * i + 2]);
      }
      tmp.updateMatrix();
      mesh.setMatrixAt(i, tmp.matrix);
      mesh.setColorAt(i, c);
    }
    mesh.instanceMatrix.needsUpdate = true;
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
  }
  function isHighlightOn() {
    return !!(hlChk && hlChk.checked);
  }

  // Double-click to re-frame
  stage.addEventListener('dblclick', () => {
    controls.target.set(0, 0, 0);
    camera.position.set(55, 42, 55);
  });

  // Kick off first load
  loadAndShow(currentScene, currentView);
}
