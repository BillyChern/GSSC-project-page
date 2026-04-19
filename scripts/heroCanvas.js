/* =============================================================
   heroCanvas.js — autorotating hero showcase for the landing page.
   Loads a real S²D² prediction PLY and renders it with a gentle
   continuous yaw. Respects prefers-reduced-motion. No user controls;
   this is a background showcase, not a viewer.
   ============================================================= */

import * as THREE from 'three';
import { PLYLoader } from 'three/addons/loaders/PLYLoader.js';

const mount = document.getElementById('hero-canvas');
if (mount) boot();

function boot() {
  // Respect reduced motion: no continuous rotation for sensitive users.
  const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const renderer = new THREE.WebGLRenderer({
    antialias: true,
    alpha: true,           // keep the background gradient visible behind the cloud
    powerPreference: 'low-power',
  });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setClearColor(0x000000, 0);
  mount.appendChild(renderer.domElement);

  const scene = new THREE.Scene();

  const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 2000);
  camera.position.set(130, 95, 130);
  camera.lookAt(0, 0, 0);

  const amb = new THREE.AmbientLight(0xFFFFFF, 0.9);
  scene.add(amb);
  const key = new THREE.DirectionalLight(0xFFE2BE, 0.35);
  key.position.set(60, 120, 40);
  scene.add(key);

  const yawGroup = new THREE.Group();
  scene.add(yawGroup);

  // Faint grid for spatial context; matches the palette used in the main viewer.
  const grid = new THREE.GridHelper(180, 18, 0x232A38, 0x18202C);
  grid.material.opacity = 0.35;
  grid.material.transparent = true;
  grid.position.y = -0.5;
  yawGroup.add(grid);

  // Caption overlay built via safe DOM APIs (no innerHTML).
  const caption = document.createElement('figcaption');
  caption.className = 'hero-canvas__caption';
  const dot = document.createElement('span');
  dot.className = 'hero-canvas__dot';
  caption.appendChild(dot);
  const capText = document.createElement('span');
  const sSup = (txt) => {
    const s = document.createElement('sup');
    s.textContent = txt;
    return s;
  };
  capText.append('S', sSup('2'), 'D', sSup('2'),
    ' prediction · SemanticKITTI seq 08 · frame 003096');
  caption.appendChild(capText);
  mount.appendChild(caption);

  // --- Load the champion PLY (S²D² prediction on the bicyclist frame).
  // This is the same asset used in the main interactive viewer, so no
  // extra network cost. If it is missing we render a tasteful fallback.
  const loader = new PLYLoader();
  loader.load(
    'assets/ply/bicyclist_s2d2.ply',
    (geometry) => addCloud(geometry),
    undefined,
    () => addCloud(makeFallback()),
  );

  function addCloud(geometry) {
    // PLYs from our exporter may use red/green/blue attributes; normalize.
    if (!geometry.getAttribute('color') && geometry.getAttribute('red')) {
      const n = geometry.attributes.position.count;
      const colors = new Float32Array(n * 3);
      const r = geometry.attributes.red.array;
      const g = geometry.attributes.green.array;
      const b = geometry.attributes.blue.array;
      for (let i = 0; i < n; i++) {
        colors[3 * i    ] = r[i] / 255;
        colors[3 * i + 1] = g[i] / 255;
        colors[3 * i + 2] = b[i] / 255;
      }
      geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    }

    // Center the cloud so it rotates around its own axis, not the ego origin.
    geometry.computeBoundingBox();
    const center = new THREE.Vector3();
    geometry.boundingBox.getCenter(center);
    geometry.translate(-center.x, -center.y, -center.z);

    const mat = new THREE.PointsMaterial({
      size: 0.95,
      vertexColors: true,
      sizeAttenuation: true,
      transparent: true,
      opacity: 0.96,
    });
    const cloud = new THREE.Points(geometry, mat);
    cloud.rotateX(-Math.PI / 2); // voxel Z-up -> scene Y-up
    yawGroup.add(cloud);

    // Fade the caption dot in once the cloud is on screen.
    requestAnimationFrame(() => caption.classList.add('is-loaded'));
  }

  function makeFallback() {
    // Tiny stand-in scene: scattered coloured voxels in our palette so the
    // hero never looks empty even if the PLY fetch fails.
    const geom = new THREE.BufferGeometry();
    const pos = [];
    const col = [];
    const palette = [
      [0.95, 0.58, 0.25], // orange accent (S²D²)
      [0.42, 0.66, 1.00], // blue
      [0.55, 0.81, 0.66], // green
      [0.78, 0.35, 0.19], // terracotta
    ];
    for (let i = 0; i < 3500; i++) {
      const x = (Math.random() - 0.5) * 90;
      const y = (Math.random() - 0.5) * 16;
      const z = (Math.random() - 0.5) * 90;
      pos.push(x, y, z);
      const c = palette[(Math.random() * palette.length) | 0];
      col.push(c[0], c[1], c[2]);
    }
    geom.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    geom.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
    return geom;
  }

  // --- Resize handling: the hero canvas is a square; match the mount's
  // current client size so rendering stays crisp on retina and resizes.
  function resize() {
    const w = mount.clientWidth;
    const h = mount.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }
  resize();
  window.addEventListener('resize', resize);

  // --- Pause rendering when off-screen to save the user's battery.
  let onScreen = true;
  const io = new IntersectionObserver((entries) => {
    onScreen = entries[0].isIntersecting;
  }, { threshold: 0.1 });
  io.observe(mount);

  // --- Animation loop.
  const ROT_SPEED = prefersReduced ? 0 : 0.12; // rad/sec
  let lastT = performance.now();
  function tick(now) {
    const dt = (now - lastT) / 1000;
    lastT = now;
    if (onScreen) {
      yawGroup.rotation.y += ROT_SPEED * dt;
      renderer.render(scene, camera);
    }
    requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}
