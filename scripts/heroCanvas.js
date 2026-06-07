/* =============================================================
   heroCanvas.js — autorotating hero showcase for the landing page.

   v2 (2026-04-19): switched from THREE.Points (flat sprites) to
   THREE.InstancedMesh of Lambert-shaded 0.2 m cubes so the look
   matches the headless-Blender renders used in the paper figures.
   Same PLY assets; one cube per voxel with shadowing + ambient fill.

   Loads a real S²D² prediction PLY and renders it with a gentle
   continuous yaw. Respects prefers-reduced-motion. No user controls;
   this is a background showcase, not a viewer.
   ============================================================= */

import * as THREE from 'three';
import { PLYLoader } from 'three/addons/loaders/PLYLoader.js';

// Must match tools/export_ply.py VOXEL_SIZE. Each PLY vertex is the
// centre of a 0.2 m cube in world space.
const VOXEL_SIZE = 0.2;

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
  // The mount div carries role=img + aria-label, so the WebGL canvas itself
  // is decorative to screen readers — hide it to avoid a nameless canvas node.
  renderer.domElement.setAttribute('aria-hidden', 'true');
  mount.appendChild(renderer.domElement);

  const scene = new THREE.Scene();

  // Tighter framing: closer + slightly wider FOV so the cloud fills
  // ~75% of the hero square instead of sitting far away in the centre.
  const camera = new THREE.PerspectiveCamera(34, 1, 0.1, 2000);
  camera.position.set(48, 38, 48);
  camera.lookAt(0, 0, 0);

  // 3-light rig that mimics the Blender "dramatic" preset used in the
  // paper: warm key from upper-right, cool fill from the opposite side,
  // soft ambient floor so shadows read but don't crush the low classes.
  scene.add(new THREE.AmbientLight(0xFFFFFF, 0.55));
  const key = new THREE.DirectionalLight(0xFFE2BE, 1.1);
  key.position.set(40, 80, 30);
  scene.add(key);
  const fill = new THREE.DirectionalLight(0x9DB7D8, 0.45);
  fill.position.set(-50, 30, -40);
  scene.add(fill);
  const rim = new THREE.DirectionalLight(0xFFAE60, 0.35);
  rim.position.set(-10, 10, -60);
  scene.add(rim);

  const yawGroup = new THREE.Group();
  scene.add(yawGroup);

  // Faint grid for spatial context; matches the main viewer palette.
  const grid = new THREE.GridHelper(60, 30, 0x232A38, 0x18202C);
  grid.material.opacity = 0.32;
  grid.material.transparent = true;
  grid.position.y = -0.05;
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

  // Load the champion PLY (S²D² prediction on the bicyclist frame);
  // same file the main viewer uses, so it's already in browser cache.
  const loader = new PLYLoader();
  loader.load(
    'assets/ply/bicyclist_s2d2.ply',
    (geometry) => addCubes(geometry),
    undefined,
    () => addCubes(makeFallback()),
  );

  function addCubes(geometry) {
    // Normalize colour attribute: our exporter writes red/green/blue
    // uchar; three.js wants a single "color" attribute in [0, 1].
    const n = geometry.attributes.position.count;
    let colors;
    if (geometry.getAttribute('color')) {
      colors = geometry.getAttribute('color').array;
    } else if (geometry.getAttribute('red')) {
      colors = new Float32Array(n * 3);
      const r = geometry.attributes.red.array;
      const g = geometry.attributes.green.array;
      const b = geometry.attributes.blue.array;
      for (let i = 0; i < n; i++) {
        colors[3 * i    ] = r[i] / 255;
        colors[3 * i + 1] = g[i] / 255;
        colors[3 * i + 2] = b[i] / 255;
      }
    } else {
      colors = new Float32Array(n * 3).fill(0.75);
    }

    // Centre the cloud about the origin so the yawGroup rotates
    // around the scene's centre of mass, not a corner voxel.
    geometry.computeBoundingBox();
    const bb = geometry.boundingBox;
    const cx = (bb.min.x + bb.max.x) * 0.5;
    const cy = (bb.min.y + bb.max.y) * 0.5;
    const cz = (bb.min.z + bb.max.z) * 0.5;
    const pos = geometry.attributes.position.array;

    // Build the InstancedMesh. One small cube per voxel, same 0.2 m
    // metric size as the Blender paper renderer.
    const boxGeo = new THREE.BoxGeometry(VOXEL_SIZE, VOXEL_SIZE, VOXEL_SIZE);
    const mat = new THREE.MeshLambertMaterial({
      vertexColors: false,  // per-instance colour via setColorAt
    });
    const mesh = new THREE.InstancedMesh(boxGeo, mat, n);
    mesh.instanceMatrix.setUsage(THREE.StaticDrawUsage);
    mesh.frustumCulled = false;

    const tmp = new THREE.Object3D();
    const tmpColor = new THREE.Color();
    for (let i = 0; i < n; i++) {
      const x = pos[3 * i    ] - cx;
      const y = pos[3 * i + 1] - cy;
      const z = pos[3 * i + 2] - cz;
      tmp.position.set(x, y, z);
      tmp.updateMatrix();
      mesh.setMatrixAt(i, tmp.matrix);
      tmpColor.setRGB(colors[3 * i], colors[3 * i + 1], colors[3 * i + 2]);
      mesh.setColorAt(i, tmpColor);
    }
    mesh.instanceMatrix.needsUpdate = true;
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;

    // Voxel Z-up → scene Y-up.
    mesh.rotateX(-Math.PI / 2);
    yawGroup.add(mesh);

    // Retarget the camera so it frames this particular cloud tightly,
    // rather than relying on a hard-coded distance. The SemanticKITTI
    // grid after centering spans roughly 51 m across in XY and 6 m in Z.
    const spanXY = Math.max(bb.max.x - bb.min.x, bb.max.y - bb.min.y);
    const camDist = Math.max(28, spanXY * 0.62);
    camera.position.set(camDist, camDist * 0.75, camDist);
    camera.lookAt(0, 0, 0);

    requestAnimationFrame(() => caption.classList.add('is-loaded'));
  }

  function makeFallback() {
    // Tiny stand-in scene if the PLY fetch fails. Uses the same
    // position scale so the cube renderer still looks right.
    const geom = new THREE.BufferGeometry();
    const pos = [];
    const col = [];
    const palette = [
      [0.95, 0.58, 0.25],
      [0.42, 0.66, 1.00],
      [0.55, 0.81, 0.66],
      [0.78, 0.35, 0.19],
    ];
    for (let i = 0; i < 800; i++) {
      const x = (Math.random() - 0.5) * 24;
      const y = (Math.random() - 0.5) * 4;
      const z = (Math.random() - 0.5) * 24;
      pos.push(x, y, z);
      const c = palette[(Math.random() * palette.length) | 0];
      col.push(c[0], c[1], c[2]);
    }
    geom.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    geom.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
    return geom;
  }

  // Resize handling: hero canvas is a square; match the mount's
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

  // Pause rendering when off-screen to save battery.
  let onScreen = true;
  const io = new IntersectionObserver((entries) => {
    onScreen = entries[0].isIntersecting;
  }, { threshold: 0.1 });
  io.observe(mount);

  // Animation loop.
  const ROT_SPEED = prefersReduced ? 0 : 0.18; // rad/sec
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
