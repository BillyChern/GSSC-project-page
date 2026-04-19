/* =============================================================
   viewer3d.js — Three.js-based interactive point cloud viewer.
   Loads PLY voxel clouds and lets the user switch between
   (scene × view) combinations while keeping the camera pose.
   ============================================================= */

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { PLYLoader } from 'three/addons/loaders/PLYLoader.js';

// Asset map: each scene has four views. Files live under assets/ply/.
// If a PLY is missing we fall back to a procedurally-generated cube
// of colored voxels so the viewer never looks broken.
const SCENES = {
  'bicyclist': {
    label: 'Bicyclist — SemanticKITTI seq 08 · frame 003096',
    stats: { scp: 31.3, ours: 56.4, delta: '+25.1', klass: 'bicyclist IoU' },
    plys: {
      'sparse': 'assets/ply/bicyclist_sparse.ply',
      'scpnet': 'assets/ply/bicyclist_scpnet.ply',
      's2d2':   'assets/ply/bicyclist_s2d2.ply',
      'gt':     'assets/ply/bicyclist_gt.ply',
    }
  },
  'traffic-sign': {
    label: 'Traffic-sign — SemanticKITTI seq 08 · frame 002870',
    stats: { scp: 17.1, ours: 39.5, delta: '+22.4', klass: 'traffic-sign IoU' },
    plys: {
      'sparse': 'assets/ply/traffic_sparse.ply',
      'scpnet': 'assets/ply/traffic_scpnet.ply',
      's2d2':   'assets/ply/traffic_s2d2.ply',
      'gt':     'assets/ply/traffic_gt.ply',
    }
  }
};

const stage = document.getElementById('viewer3d-stage');
const loadingEl = document.getElementById('viewer3d-loading');
if (stage) boot();

function boot() {
  const renderer = new THREE.WebGLRenderer({
    antialias: true, alpha: false, powerPreference: 'high-performance'
  });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setClearColor(0x0B0E14, 1);
  stage.appendChild(renderer.domElement);

  const scene  = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x0B0E14, 0.005);

  const camera = new THREE.PerspectiveCamera(45, 16/10, 0.1, 2000);
  camera.position.set(140, 100, 140);
  camera.lookAt(0, 0, 0);

  // Ambient glow + a warm key light for voxel depth cues
  const amb = new THREE.AmbientLight(0xFFFFFF, 0.85);
  scene.add(amb);
  const key = new THREE.DirectionalLight(0xFFE2BE, 0.35);
  key.position.set(60, 120, 40);
  scene.add(key);

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

  async function loadAndShow(sceneId, viewId) {
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
      // Fallback: synthetic cloud so the viewer always shows something.
      console.warn(`PLY ${url} missing, falling back to synthetic cloud`, e);
      geometry = makeSyntheticCloud(sceneId, viewId);
    }

    // PLY from our exporter uses "color" attribute RGB [0..1]
    if (!geometry.getAttribute('color') && geometry.getAttribute('red')) {
      const n = geometry.attributes.position.count;
      const colors = new Float32Array(n * 3);
      const r = geometry.attributes.red.array;
      const g = geometry.attributes.green.array;
      const b = geometry.attributes.blue.array;
      for (let i = 0; i < n; i++) {
        colors[3*i  ] = r[i] / 255;
        colors[3*i+1] = g[i] / 255;
        colors[3*i+2] = b[i] / 255;
      }
      geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    }

    // Center the cloud around origin for consistent camera framing.
    geometry.computeBoundingBox();
    const center = new THREE.Vector3();
    geometry.boundingBox.getCenter(center);
    geometry.translate(-center.x, -center.y, -center.z);

    const material = new THREE.PointsMaterial({
      size: 0.9,
      vertexColors: true,
      sizeAttenuation: true,
      transparent: true,
      opacity: 0.95,
    });

    const next = new THREE.Points(geometry, material);
    next.rotateX(-Math.PI / 2); // align voxel Z-up to scene Y-up

    if (currentCloud) scene.remove(currentCloud);
    currentCloud = next;
    scene.add(next);

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
    const map = { scp: s.scp + '%', ours: s.ours + '%', delta: s.delta };
    row.querySelectorAll('[data-stat]').forEach((cell) => {
      const k = cell.dataset.stat;
      if (map[k] !== undefined) cell.textContent = map[k];
    });
  }

  function makeSyntheticCloud(sceneId, viewId) {
    // Build a 60x60x10 lattice with some holes + palette tied to view.
    const geom = new THREE.BufferGeometry();
    const pos = [];
    const col = [];
    const palette = viewPalette(viewId);
    const dim = 60, h = 10;
    const rng = mulberry32(hash(sceneId + viewId));
    for (let z = 0; z < h; z++) {
      for (let x = -dim; x < dim; x++) {
        for (let y = -dim; y < dim; y++) {
          // thin plane + scattered obstacles
          const isGround = (z < 2);
          const isObstacle = rng() < (isGround ? 0.35 : 0.012);
          if (!isObstacle) continue;
          // Sparse view drops 80% of points
          if (viewId === 'sparse' && rng() > 0.18) continue;
          pos.push(x, z * 2 - 5, y);
          const c = palette[Math.floor(rng() * palette.length)];
          col.push(c[0], c[1], c[2]);
        }
      }
    }
    geom.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    geom.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
    return geom;
  }

  function viewPalette(viewId) {
    const base = [
      [0.55, 0.72, 0.88],  // road blue-grey
      [0.80, 0.82, 0.34],  // vegetation
      [0.78, 0.35, 0.19],  // building
      [0.46, 0.40, 0.55],  // sidewalk
    ];
    if (viewId === 'sparse') return [[0.7, 0.75, 0.82]];
    if (viewId === 's2d2')   return [...base, [0.95, 0.58, 0.25]]; // orange accent
    if (viewId === 'gt')     return [...base, [0.55, 0.81, 0.66]];
    return base;
  }

  function hash(s) { let h = 0; for (const c of s) h = ((h<<5) - h + c.charCodeAt(0)) | 0; return h; }
  function mulberry32(a) { return function() { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }

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

  // Animation loop
  function frame() {
    controls.update();
    renderer.render(scene, camera);
    requestAnimationFrame(frame);
  }
  frame();

  // UI wiring
  const sceneBtns = document.querySelectorAll('.seg__btn[data-scene]');
  const viewBtns  = document.querySelectorAll('.seg__btn[data-view]');

  sceneBtns.forEach((b) => {
    b.addEventListener('click', () => {
      sceneBtns.forEach((x) => x.classList.remove('is-active'));
      b.classList.add('is-active');
      loadAndShow(b.dataset.scene, currentView);
    });
  });
  viewBtns.forEach((b) => {
    b.addEventListener('click', () => {
      viewBtns.forEach((x) => x.classList.remove('is-active'));
      b.classList.add('is-active');
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
    currentCloud.material.opacity = hlChk.checked ? 0.95 : 0.6;
  });

  // Double-click to re-frame
  stage.addEventListener('dblclick', () => {
    controls.target.set(0, 0, 0);
    camera.position.set(140, 100, 140);
  });

  // Kick off first load
  loadAndShow(currentScene, currentView);
}
