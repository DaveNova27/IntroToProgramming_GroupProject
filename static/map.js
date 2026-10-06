// 3D campus map: the same run as the dashboard, drawn as a tycoon scene.
// Every action goes to the server first. Only an accepted action is animated,
// and the animation only shows what the server already decided and saved.
// $, esc, fmt, fmtSigned, toast and EMOJI come from common.js.

import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { CSS2DRenderer, CSS2DObject } from "three/addons/renderers/CSS2DRenderer.js";

const COLOR = { sandwich: "#2a78d6", coffee: "#eb6834", cookie: "#1baf7a" };
const DARK = { sandwich: "#1c5cab", coffee: "#b94d22", cookie: "#14855c" };
const FACES = ["🧑‍🎓", "👩‍🎓", "👨‍🎓", "🧑", "👩", "👨", "🧕", "🧔"];
const SHIRTS = [0x2a78d6, 0xeb6834, 0x1baf7a, 0xe87ba4, 0x4a3aa7, 0xeda100, 0x6b6f76, 0xe34948];
const SKIN = [0xf1c7a3, 0xd9a47c, 0xa8714d, 0x6e4630, 0xf5d6bd];
const EMOJI_FONT = "'Apple Color Emoji','Segoe UI Emoji','Noto Color Emoji',sans-serif";

// world layout in metres: the kiosk faces the plaza (+z), the road runs along z = 12
const KIOSK = { x: -4, z: 0 };
const WINDOW_X = { sandwich: -6, coffee: -4, cookie: -2 };
const SPOT_Z = 3.5;            // where a customer stands at the counter
const QUEUE_GAP = 0.95;
const SHED = { x: 7.5, z: -0.5 };
const PALLET_X = { sandwich: 5.4, coffee: 7.5, cookie: 9.6 };
const PALLET_Z = -0.6;
const CRATE = 0.66;
const UNITS_PER_CRATE = 5;
const MAX_CRATES = 16;         // 2 x 2 per layer, 4 layers; the sign shows the exact count
const LANE_Z = 10.9;           // truck lane
const DOORS = { library: new THREE.Vector3(-20, 0, -9.2), hall: new THREE.Vector3(19, 0, -9.6) };
const SERVICE_MS = 750;
const MAX_CUSTOMERS = 20;
const WALK_SPEED = 4.2;        // metres per second

let state = null;
let animating = false;
let dayRunning = null;
let fast = false;
let panelMode = null;
let orderProduct = "sandwich";
const calm = window.matchMedia("(prefers-reduced-motion: reduce)");

// scene objects that change with the run
let scene, camera, renderer, labels, controls;
const world = { pallets: {}, displays: {}, menu: null, lamps: [], sun: null, hemi: null, clouds: [], hotspots: [], windows: null };

// ---- small helpers -----------------------------------------------------------

const product = (pid) => state.products.find((p) => p.id === pid);
const stockOf = (run) => Object.fromEntries(run.products.map((p) => [p.id, p.stock]));
const pick = (list) => list[Math.floor(Math.random() * list.length)];
const linear = (t) => t;
const easeInOut = (t) => (t < 0.5 ? 2 * t * t : 1 - (-2 * t + 2) ** 2 / 2);
const easeOut = (t) => 1 - (1 - t) ** 3;
const easeIn = (t) => t ** 3;

// Browsers pause animation frames in a hidden tab; keep going with a timer there,
// so an animation (and Skip) still finishes when the player switches tabs.
const nextFrame = (cb) => (document.hidden ? setTimeout(() => cb(performance.now()), 100) : requestAnimationFrame(cb));

// Run update(0..1) over `ms`. "Skip" (fast) or reduced motion jumps to the end.
function tween(ms, update, easing = easeInOut) {
  if (fast || calm.matches || ms <= 0) {
    update(1);
    return Promise.resolve();
  }
  return new Promise((resolve) => {
    const start = performance.now();
    const frame = (now) => {
      const t = fast ? 1 : Math.min((now - start) / ms, 1);
      update(easing(t));
      if (t < 1) nextFrame(frame);
      else resolve();
    };
    nextFrame(frame);
  });
}
const wait = (ms) => tween(ms, () => {}, linear);

function previewDemand(cents, ref) {
  if (cents <= ref) return state.demand_levels.at_or_below_ref;
  if (cents <= 2 * ref) return state.demand_levels.up_to_double_ref;
  return 0;
}

async function send(path, body) {
  try {
    const res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    try {
      return await res.json();
    } catch {
      toast("The server hit an error. Nothing was saved.", "error");
      return null;
    }
  } catch {
    toast("Could not reach the server. Is app.py still running?", "error");
    return null;
  }
}

// ---- building blocks -------------------------------------------------------------

function mat(color, extra = {}) {
  return new THREE.MeshStandardMaterial({ color, roughness: 0.85, metalness: 0, ...extra });
}

function box(w, h, d, material, x = 0, y = 0, z = 0) {
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), material);
  mesh.position.set(x, y, z);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  return mesh;
}

function cylinder(rTop, rBottom, h, material, segments = 16) {
  const mesh = new THREE.Mesh(new THREE.CylinderGeometry(rTop, rBottom, h, segments), material);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  return mesh;
}

// A triangular prism (gable roof, pediment): triangle in x/y, extruded along z.
function prism(width, height, depth, material) {
  const shape = new THREE.Shape();
  shape.moveTo(-width / 2, 0);
  shape.lineTo(width / 2, 0);
  shape.lineTo(0, height);
  shape.closePath();
  const geo = new THREE.ExtrudeGeometry(shape, { depth, bevelEnabled: false });
  geo.translate(0, 0, -depth / 2);
  const mesh = new THREE.Mesh(geo, material);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  return mesh;
}

function canvasTexture(w, h, draw) {
  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  draw(canvas.getContext("2d"), w, h);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.anisotropy = 8;
  return texture;
}

function label(className, html) {
  const el = document.createElement("div");
  el.className = className;
  el.innerHTML = html;
  return new CSS2DObject(el);
}

// A flat strip along a curve (footpaths).
function ribbon(curve, width, material, y = 0.02) {
  const steps = 90;
  const positions = [];
  const index = [];
  for (let i = 0; i <= steps; i++) {
    const t = i / steps;
    const p = curve.getPointAt(t);
    const tan = curve.getTangentAt(t);
    const side = new THREE.Vector3(-tan.z, 0, tan.x).normalize().multiplyScalar(width / 2);
    positions.push(p.x + side.x, y, p.z + side.z, p.x - side.x, y, p.z - side.z);
    if (i < steps) {
      const a = i * 2;
      index.push(a, a + 1, a + 2, a + 1, a + 3, a + 2);
    }
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  geo.setIndex(index);
  geo.computeVertexNormals();
  const mesh = new THREE.Mesh(geo, material);
  mesh.receiveShadow = true;
  return mesh;
}

// ---- products as small 3D things (window display, in the customer's hand) ---------

function productMesh(pid) {
  const g = new THREE.Group();
  if (pid === "sandwich") {
    const bread = prism(0.42, 0.36, 0.14, mat(0xe9c27a));
    bread.rotation.x = -Math.PI / 2;
    const filling = prism(0.38, 0.32, 0.05, mat(0x6fbf4a));
    filling.rotation.x = -Math.PI / 2;
    filling.position.y = 0.09;
    const top = bread.clone();
    top.position.y = 0.14;
    g.add(bread, filling, top);
  } else if (pid === "coffee") {
    const cup = cylinder(0.15, 0.12, 0.32, mat(0xffffff));
    cup.position.y = 0.16;
    const sleeve = cylinder(0.152, 0.135, 0.12, mat(COLOR.coffee));
    sleeve.position.y = 0.15;
    const lid = cylinder(0.16, 0.16, 0.04, mat(0x5a3a2a));
    lid.position.y = 0.34;
    g.add(cup, sleeve, lid);
  } else {
    const cookie = cylinder(0.22, 0.22, 0.06, mat(0xc68a4a), 20);
    cookie.position.y = 0.03;
    g.add(cookie);
    for (let i = 0; i < 6; i++) {
      const chip = new THREE.Mesh(new THREE.SphereGeometry(0.03, 6, 6), mat(0x3b2416));
      const a = (i / 6) * Math.PI * 2;
      chip.position.set(Math.cos(a) * 0.12, 0.065, Math.sin(a) * 0.12);
      g.add(chip);
    }
  }
  return g;
}

const crateMaterialCache = {};
function crateMaterials(pid) {
  if (crateMaterialCache[pid]) return crateMaterialCache[pid];
  const side = canvasTexture(128, 128, (g, w, h) => {
    g.fillStyle = COLOR[pid];
    g.fillRect(0, 0, w, h);
    g.strokeStyle = DARK[pid];
    g.lineWidth = 12;
    g.strokeRect(6, 6, w - 12, h - 12);
    g.fillStyle = "rgba(255,255,255,0.92)";
    g.beginPath();
    g.arc(64, 64, 38, 0, Math.PI * 2);
    g.fill();
    g.font = `46px ${EMOJI_FONT}`;
    g.textAlign = "center";
    g.textBaseline = "middle";
    g.fillText(EMOJI[pid], 64, 68);
  });
  const sides = mat(0xffffff, { map: side });
  const top = mat(COLOR[pid]);
  crateMaterialCache[pid] = [sides, sides, top, top, sides, sides];
  return crateMaterialCache[pid];
}
function crateMesh(pid) {
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(CRATE, CRATE, CRATE), crateMaterials(pid));
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  return mesh;
}
// position of crate number i on a pallet (2 x 2 per layer)
function crateSlot(pid, i) {
  const layer = Math.floor(i / 4);
  const k = i % 4;
  return new THREE.Vector3(
    PALLET_X[pid] + (k % 2 ? 0.36 : -0.36),
    0.3 + CRATE / 2 + layer * (CRATE + 0.02),
    PALLET_Z + (k < 2 ? -0.36 : 0.36),
  );
}

// ---- the campus ------------------------------------------------------------------

const FOOTPATHS = [
  [new THREE.Vector3(-20, 0, -9.2), new THREE.Vector3(-17, 0, -3), new THREE.Vector3(-11, 0, 3.5), new THREE.Vector3(-7, 0, 6)],
  [new THREE.Vector3(19, 0, -9.6), new THREE.Vector3(15, 0, -2.5), new THREE.Vector3(9, 0, 4.6), new THREE.Vector3(0, 0, 6.6)],
];

function buildGround() {
  const grass = new THREE.Mesh(new THREE.PlaneGeometry(220, 160), mat(0x8cc870));
  grass.rotation.x = -Math.PI / 2;
  grass.receiveShadow = true;
  scene.add(grass);

  for (const [x, z, r] of [[-12, -4, 5], [14, 4, 4], [-26, 4, 6], [26, -2, 5], [0, -12, 6]]) {
    const patch = new THREE.Mesh(new THREE.CircleGeometry(r, 24), mat(0x80bd65));
    patch.rotation.x = -Math.PI / 2;
    patch.position.set(x, 0.005, z);
    patch.receiveShadow = true;
    scene.add(patch);
  }

  // footpaths from the buildings to the plaza, and the plaza itself
  const pathMat = mat(0xeadfc4, { side: THREE.DoubleSide });
  for (const pts of FOOTPATHS) scene.add(ribbon(new THREE.CatmullRomCurve3(pts), 2.2, pathMat));
  const plaza = new THREE.Mesh(new THREE.CircleGeometry(6.5, 40), pathMat);
  plaza.rotation.x = -Math.PI / 2;
  plaza.scale.set(1.35, 1, 1);
  plaza.position.set(KIOSK.x, 0.018, 5.2);
  plaza.receiveShadow = true;
  scene.add(plaza);

  // driveway, sidewalk, road with lane markings
  scene.add(box(3.2, 0.06, 6.6, mat(0xc9c5ba), SHED.x, 0.03, 5.3));
  scene.add(box(220, 0.14, 1.0, mat(0xdcd7ca), 0, 0.07, 9.0));
  const road = box(220, 0.06, 6.2, mat(0x5d6168), 0, 0.03, 12.6);
  road.castShadow = false;
  scene.add(road);
  const dash = mat(0xf5f2e8);
  for (let x = -100; x <= 100; x += 5) {
    const d = box(2.6, 0.02, 0.18, dash, x, 0.07, 12.6);
    d.castShadow = false;
    scene.add(d);
  }
}

function buildLibrary() {
  const g = new THREE.Group();
  g.position.set(-20, 0, -15);
  const stone = mat(0xefe4d2);
  const trim = mat(0xd8c7a6);
  g.add(box(15, 6.4, 8, stone, 0, 3.2, 0));
  g.add(box(16, 0.6, 9.4, trim, 0, 6.7, 0.3));
  const pediment = prism(16, 2.4, 1.2, trim);
  pediment.position.set(0, 7, 4.4);
  g.add(pediment);
  g.add(box(16, 0.5, 2.6, trim, 0, 0.25, 5));
  g.add(box(14, 0.35, 1.8, trim, 0, 0.6, 4.6));
  for (let i = 0; i < 6; i++) {
    const col = cylinder(0.38, 0.42, 5.8, mat(0xfbf7ef));
    col.position.set(-6 + i * 2.4, 3.6, 4.4);
    g.add(col);
  }
  g.add(box(2.2, 3.4, 0.2, mat(0x6b4f3a), 0, 2.2, 4.05));
  const name = label("lbl-building", "LIBRARY");
  name.position.set(0, 10, 4);
  g.add(name);
  scene.add(g);
}

function buildHall() {
  const g = new THREE.Group();
  g.position.set(19, 0, -15.5);
  const brick = canvasTexture(256, 256, (c, w, h) => {
    c.fillStyle = "#c8704c";
    c.fillRect(0, 0, w, h);
    c.strokeStyle = "#a95b3c";
    c.lineWidth = 3;
    for (let y = 0; y < h; y += 16) {
      c.beginPath(); c.moveTo(0, y); c.lineTo(w, y); c.stroke();
      for (let x = (y / 16) % 2 ? 0 : 16; x < w; x += 32) {
        c.beginPath(); c.moveTo(x, y); c.lineTo(x, y + 16); c.stroke();
      }
    }
  });
  brick.wrapS = brick.wrapT = THREE.RepeatWrapping;
  brick.repeat.set(3, 2);
  g.add(box(15, 8.5, 9, mat(0xffffff, { map: brick }), 0, 4.25, 0));
  g.add(box(15.6, 0.6, 9.6, mat(0x8e4a32), 0, 8.8, 0));
  const glass = mat(0xcfe7f7, { roughness: 0.3, emissive: 0x000000 });
  world.windows = glass;
  for (let row = 0; row < 2; row++) {
    for (let i = 0; i < 5; i++) {
      if (row === 0 && i === 2) continue;
      g.add(box(1.6, 1.7, 0.12, glass, -5.6 + i * 2.8, 2.6 + row * 3, 4.52));
    }
  }
  g.add(box(2.4, 3.2, 0.2, mat(0x5a3426), 0, 1.6, 4.55));
  g.add(box(3.6, 0.3, 1.4, mat(0x8e4a32), 0, 3.5, 5.1));
  const name = label("lbl-building", "HALL A");
  name.position.set(0, 10.6, 4);
  g.add(name);
  scene.add(g);
}

function buildDorms() {
  const g = new THREE.Group();
  g.position.set(0, 0, -26);
  g.add(box(12, 11, 7, mat(0xd9cbb5), 0, 5.5, 0));
  for (let row = 0; row < 4; row++) {
    for (let i = 0; i < 4; i++) g.add(box(1.4, 1.4, 0.12, world.windows, -4.2 + i * 2.8, 2 + row * 2.4, 3.52));
  }
  g.add(box(12.4, 0.5, 7.4, mat(0xb8a588), 0, 11.2, 0));
  const name = label("lbl-building", "DORMS");
  name.position.set(0, 12.6, 3);
  g.add(name);
  scene.add(g);
}

function tree(x, z, s = 1) {
  const g = new THREE.Group();
  const trunk = cylinder(0.18 * s, 0.26 * s, 1.6 * s, mat(0x7a5236), 7);
  trunk.position.y = 0.8 * s;
  const leaves = new THREE.Mesh(new THREE.IcosahedronGeometry(1.3 * s, 0), mat(pick([0x4f9e4a, 0x5cae55, 0x47924a]), { flatShading: true }));
  leaves.position.y = 2.3 * s;
  leaves.castShadow = true;
  const top = new THREE.Mesh(new THREE.IcosahedronGeometry(0.85 * s, 0), mat(0x63b85b, { flatShading: true }));
  top.position.set(0.3 * s, 3.1 * s, 0.1 * s);
  top.castShadow = true;
  g.add(trunk, leaves, top);
  g.position.set(x, 0, z);
  g.rotation.y = Math.random() * Math.PI;
  scene.add(g);
}

function lamp(x, z) {
  const pole = cylinder(0.07, 0.09, 3.2, mat(0x3a3d44), 8);
  pole.position.set(x, 1.6, z);
  const bulbMat = mat(0xfff3c4, { emissive: 0xffd77a, emissiveIntensity: 0 });
  const bulb = new THREE.Mesh(new THREE.SphereGeometry(0.22, 12, 12), bulbMat);
  bulb.position.set(x, 3.3, z);
  const light = new THREE.PointLight(0xffd27a, 0, 9, 1.6);
  light.position.set(x, 3.2, z);
  scene.add(pole, bulb, light);
  world.lamps.push({ bulbMat, light });
}

function bench(x, z, rot) {
  const g = new THREE.Group();
  const wood = mat(0xa8694a);
  const metal = mat(0x3a3d44);
  g.add(box(1.8, 0.1, 0.5, wood, 0, 0.5, 0), box(1.8, 0.45, 0.08, wood, 0, 0.8, -0.22));
  g.add(box(0.08, 0.5, 0.45, metal, -0.75, 0.25, 0), box(0.08, 0.5, 0.45, metal, 0.75, 0.25, 0));
  g.position.set(x, 0, z);
  g.rotation.y = rot;
  scene.add(g);
}

function buildClouds() {
  const white = mat(0xffffff, { roughness: 1 });
  for (const [x, y, z, s] of [[-30, 22, -30, 1.2], [10, 26, -40, 1.6], [35, 21, -24, 1], [-5, 24, -55, 1.4]]) {
    const g = new THREE.Group();
    for (const [dx, dy, r] of [[0, 0, 2.2], [2.2, 0.4, 1.7], [-2.1, 0.2, 1.6], [0.8, 1.3, 1.5]]) {
      const puff = new THREE.Mesh(new THREE.IcosahedronGeometry(r * s, 1), white);
      puff.position.set(dx * s, dy * s, 0);
      g.add(puff);
    }
    g.position.set(x, y, z);
    scene.add(g);
    world.clouds.push(g);
  }
}

function buildKiosk() {
  const g = new THREE.Group();
  g.position.set(KIOSK.x, 0, KIOSK.z);
  g.userData.hotspot = "prices";

  g.add(box(6, 2.7, 4, mat(0xf6e6cb), 0, 1.35, 0));
  g.add(box(5.4, 1.05, 0.1, mat(0x3b2b2b), 0, 2.0, 2.0));                 // window opening
  g.add(box(6.4, 0.16, 1.1, mat(0xb98455), 0, 1.42, 2.3));                // counter top
  g.add(box(6.0, 1.34, 0.12, mat(0xd8a46f), 0, 0.67, 2.78));              // counter front
  g.add(box(6.6, 0.25, 4.6, mat(0x2b2d42), 0, 2.82, 0));                  // roof

  // sign on the roof
  const sign = canvasTexture(512, 96, (c, w, h) => {
    c.fillStyle = "#2b2d42";
    c.fillRect(0, 0, w, h);
    c.fillStyle = "#ffd25a";
    c.font = "800 52px system-ui, sans-serif";
    c.textAlign = "center";
    c.textBaseline = "middle";
    c.fillText("CAMPUS SNACKS", w / 2, h / 2 + 3);
  });
  const navy = mat(0x2b2d42);
  const signMesh = new THREE.Mesh(new THREE.BoxGeometry(5.8, 1.0, 0.25), [navy, navy, navy, navy, mat(0xffffff, { map: sign }), navy]);
  signMesh.position.set(0, 3.5, 1.7);
  signMesh.castShadow = true;
  g.add(signMesh);

  // striped awning with scalloped edge
  const awningTex = canvasTexture(512, 160, (c, w) => {
    const stripe = w / 16;
    for (let i = 0; i < 16; i++) {
      c.fillStyle = i % 2 ? "#fff6e8" : "#e34948";
      c.fillRect(i * stripe, 0, stripe, 120);
      c.beginPath();
      c.arc(i * stripe + stripe / 2, 120, stripe / 2, 0, Math.PI);
      c.fill();
    }
  });
  const awning = new THREE.Mesh(
    new THREE.PlaneGeometry(6.6, 1.9),
    new THREE.MeshStandardMaterial({ map: awningTex, transparent: true, alphaTest: 0.5, side: THREE.DoubleSide, roughness: 0.9 }),
  );
  awning.position.set(0, 2.55, 2.75);
  awning.rotation.x = -1.05;
  awning.castShadow = true;
  g.add(awning);

  // menu board on the counter front: price and demand per product
  const menuCanvas = document.createElement("canvas");
  menuCanvas.width = 768;
  menuCanvas.height = 150;
  const menuTex = new THREE.CanvasTexture(menuCanvas);
  menuTex.colorSpace = THREE.SRGBColorSpace;
  menuTex.anisotropy = 8;
  const menu = new THREE.Mesh(new THREE.PlaneGeometry(5.8, 1.13), mat(0xffffff, { map: menuTex }));
  menu.position.set(0, 0.68, 2.85);
  g.add(menu);
  world.menu = { canvas: menuCanvas, texture: menuTex };

  // products on display in the window
  for (const pid of Object.keys(WINDOW_X)) {
    const item = productMesh(pid);
    item.scale.setScalar(1.6);
    item.position.set(WINDOW_X[pid] - KIOSK.x, 1.52, 2.0);
    g.add(item);
    world.displays[pid] = item;
  }
  scene.add(g);
  world.hotspots.push(g);
}

function buildShed() {
  const g = new THREE.Group();
  g.position.set(SHED.x, 0, SHED.z);
  g.userData.hotspot = "order";

  const planks = canvasTexture(256, 256, (c, w, h) => {
    c.fillStyle = "#a8694a";
    c.fillRect(0, 0, w, h);
    c.strokeStyle = "#8e563b";
    c.lineWidth = 4;
    for (let y = 0; y < h; y += 32) { c.beginPath(); c.moveTo(0, y); c.lineTo(w, y); c.stroke(); }
  });
  planks.wrapS = planks.wrapT = THREE.RepeatWrapping;
  planks.repeat.set(2, 1.5);
  const wood = mat(0xffffff, { map: planks });

  g.add(box(7.4, 0.12, 5.2, mat(0x6e5446), 0, 0.06, 0));                 // floor
  g.add(box(7.4, 3.4, 0.2, wood, 0, 1.7, -2.5));                          // back
  g.add(box(0.2, 3.4, 5.2, wood, -3.6, 1.7, 0));                          // sides
  g.add(box(0.2, 3.4, 5.2, wood, 3.6, 1.7, 0));
  g.add(box(7.4, 0.5, 0.2, wood, 0, 3.15, 2.5));                          // lintel
  const roof = prism(8.2, 1.8, 5.8, mat(0x7a4a35));
  roof.position.set(0, 3.4, 0);
  g.add(roof);
  const sign = canvasTexture(256, 64, (c, w, h) => {
    c.fillStyle = "#f3e3c3";
    c.fillRect(0, 0, w, h);
    c.fillStyle = "#5b3a2a";
    c.font = "800 34px system-ui, sans-serif";
    c.textAlign = "center";
    c.textBaseline = "middle";
    c.fillText("STORAGE", w / 2, h / 2 + 2);
  });
  const signMesh = new THREE.Mesh(new THREE.PlaneGeometry(2.4, 0.6), mat(0xffffff, { map: sign }));
  signMesh.position.set(0, 3.95, 2.92);
  g.add(signMesh);
  scene.add(g);
  world.hotspots.push(g);

  // the storage board above the shed names every product and its stock
  world.storageBoard = label("lbl-storage", "");
  world.storageBoard.position.set(SHED.x, 6.6, SHED.z);
  scene.add(world.storageBoard);

  // one pallet per product, with a small sign at its front
  for (const pid of Object.keys(PALLET_X)) {
    scene.add(box(1.6, 0.18, 1.6, mat(0xc39a6b), PALLET_X[pid], 0.21, PALLET_Z));
    const crates = new THREE.Group();
    scene.add(crates);
    const palletSign = label("lbl-pallet", "");
    palletSign.element.style.setProperty("--accent", COLOR[pid]);
    palletSign.position.set(PALLET_X[pid], 0.35, PALLET_Z + 1.3);
    scene.add(palletSign);
    world.pallets[pid] = { crates, sign: palletSign };
  }
}

function buildTruck(pid) {
  const g = new THREE.Group();
  const side = canvasTexture(512, 256, (c, w, h) => {
    c.fillStyle = "#f6f3ec";
    c.fillRect(0, 0, w, h);
    c.fillStyle = COLOR[pid];
    c.fillRect(0, h - 46, w, 46);
    c.fillStyle = "#4b4f57";
    c.font = "800 40px system-ui, sans-serif";
    c.textAlign = "center";
    c.fillText("CAMPUS SUPPLY", w / 2 + 50, 92);
    c.font = `110px ${EMOJI_FONT}`;
    c.textBaseline = "middle";
    c.fillText(EMOJI[pid], 90, 120);
  });
  const white = mat(0xf6f3ec);
  const painted = mat(0xffffff, { map: side });
  const cargo = new THREE.Mesh(new THREE.BoxGeometry(4.4, 2.3, 2.1), [white, white, white, white, painted, painted]);
  cargo.position.set(0, 1.75, 0);
  cargo.castShadow = true;
  g.add(cargo);
  g.add(box(1.7, 1.75, 2.1, mat(COLOR[pid]), 3.0, 1.45, 0));
  g.add(box(0.1, 0.8, 1.8, mat(0xcfe7f7, { roughness: 0.2 }), 3.86, 1.85, 0));
  g.add(box(6.2, 0.3, 1.9, mat(0x3a3d44), 0.6, 0.55, 0));
  const wheels = [];
  for (const [x, z] of [[-1.4, 1], [-1.4, -1], [2.9, 1], [2.9, -1]]) {
    const w = cylinder(0.45, 0.45, 0.32, mat(0x25262b), 14);
    w.rotation.x = Math.PI / 2;
    w.position.set(x, 0.45, z);
    g.add(w);
    wheels.push(w);
  }
  g.roll = (x) => wheels.forEach((w) => { w.rotation.y = -x / 0.45; });
  return g;
}

function buildPerson() {
  const g = new THREE.Group();
  const shirt = mat(pick(SHIRTS));
  const pants = mat(pick([0x2f3a56, 0x3a3d44, 0x5b4a3a]));
  // legs pivot at the hip so they can swing
  const legs = [-0.12, 0.12].map((x) => {
    const leg = box(0.16, 0.75, 0.18, pants);
    leg.geometry.translate(0, -0.375, 0);
    leg.position.set(x, 0.75, 0);
    g.add(leg);
    return leg;
  });
  const body = new THREE.Mesh(new THREE.CapsuleGeometry(0.25, 0.45, 4, 10), shirt);
  body.position.y = 1.1;
  body.castShadow = true;
  const head = new THREE.Mesh(new THREE.SphereGeometry(0.21, 14, 12), mat(pick(SKIN)));
  head.position.y = 1.6;
  head.castShadow = true;
  const hair = new THREE.Mesh(new THREE.SphereGeometry(0.22, 12, 8, 0, Math.PI * 2, 0, Math.PI / 2), mat(pick([0x2b1d14, 0x5a3a22, 0xd9b26a, 0x111111])));
  hair.position.y = 1.62;
  g.add(body, head, hair);
  if (Math.random() < 0.6) g.add(box(0.36, 0.42, 0.18, mat(pick(SHIRTS)), 0, 1.15, -0.3));
  g.legs = legs;
  return g;
}

// ---- scene setup -----------------------------------------------------------------

function initScene() {
  const stage = $("#stage");
  renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  stage.append(renderer.domElement);

  labels = new CSS2DRenderer();
  labels.domElement.className = "labels";
  stage.append(labels.domElement);

  scene = new THREE.Scene();
  scene.background = new THREE.Color(0xbfe3fb);
  scene.fog = new THREE.Fog(0xbfe3fb, 70, 160);

  camera = new THREE.PerspectiveCamera(40, 1, 0.5, 400);
  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.maxPolarAngle = 1.32;
  controls.minDistance = 12;
  controls.maxDistance = 85;
  controls.addEventListener("change", () => {
    const t = controls.target;
    t.x = THREE.MathUtils.clamp(t.x, -28, 28);
    t.z = THREE.MathUtils.clamp(t.z, -24, 14);
    t.y = 0;
  });

  world.hemi = new THREE.HemisphereLight(0xdff1ff, 0x6a8f4e, 1.1);
  scene.add(world.hemi);
  const sun = new THREE.DirectionalLight(0xfff4e0, 2.4);
  sun.castShadow = true;
  sun.shadow.mapSize.set(2048, 2048);
  Object.assign(sun.shadow.camera, { left: -45, right: 45, top: 45, bottom: -45, near: 1, far: 160 });
  sun.shadow.bias = -0.0004;
  scene.add(sun, sun.target);
  world.sun = sun;

  buildGround();
  buildLibrary();
  buildHall();
  buildDorms();
  buildKiosk();
  buildShed();
  buildClouds();
  for (const [x, z, s] of [[-9, -6, 1.1], [-14, 6, 0.9], [-28, -2, 1.2], [-30, 8, 1], [12, -6, 1.1], [16, 6, 0.9],
    [28, -4, 1.2], [30, 6, 1], [-6, -10, 1], [6, -12, 1.1], [-34, -16, 1.3], [34, -14, 1.2], [-22, 7, 0.8], [24, 8, 0.8]]) tree(x, z, s);
  lamp(-11.5, 6.4);
  lamp(3.4, 6.6);
  lamp(-4, 8.3);
  bench(-12.5, 8, 0);
  bench(2.2, 8.2, 0);

  resetCamera(false);
  resize();
  window.addEventListener("resize", resize);
  setSky(0);

  renderer.setAnimationLoop(() => {
    controls.update();
    world.clouds.forEach((c, i) => {
      c.position.x += 0.004 * (i + 1);
      if (c.position.x > 60) c.position.x = -60;
    });
    renderer.render(scene, camera);
    labels.render(scene, camera);
  });
}

function defaultView() {
  const aspect = window.innerWidth / window.innerHeight;
  const k = aspect < 0.8 ? 1.9 : aspect < 1.3 ? 1.35 : 1;
  return { position: new THREE.Vector3(-4 * k, 33 * k, 42 * k), target: new THREE.Vector3(1.5, 0, -4.5) };
}

function resetCamera(animate = true) {
  const view = defaultView();
  if (!animate) {
    camera.position.copy(view.position);
    controls.target.copy(view.target);
    controls.update();
    return;
  }
  const fromPos = camera.position.clone();
  const fromTarget = controls.target.clone();
  tween(700, (k) => {
    camera.position.lerpVectors(fromPos, view.position, k);
    controls.target.lerpVectors(fromTarget, view.target, k);
  });
}

function resize() {
  const w = window.innerWidth;
  const h = window.innerHeight;
  renderer.setSize(w, h);
  labels.setSize(w, h);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}

// k = 0 morning ... 1 evening: sun crosses the sky, light warms, lamps come on
const SKY = [
  [0, new THREE.Color(0xbfe3fb)],
  [0.65, new THREE.Color(0xbfe3fb)],
  [0.85, new THREE.Color(0xf4b27a)],
  [1, new THREE.Color(0x5d6aa8)],
];
function setSky(k) {
  let color = SKY[SKY.length - 1][1].clone();
  for (let i = 0; i < SKY.length - 1; i++) {
    const [a, ca] = SKY[i];
    const [b, cb] = SKY[i + 1];
    if (k >= a && k <= b) {
      color = ca.clone().lerp(cb, (k - a) / (b - a));
      break;
    }
  }
  scene.background.copy(color);
  scene.fog.color.copy(color);

  const angle = Math.PI * (0.12 + 0.76 * k);
  world.sun.position.set(-Math.cos(angle) * 40, Math.sin(angle) * 38 + 4, 18);
  const dusk = THREE.MathUtils.smoothstep(k, 0.65, 1);
  world.sun.intensity = 2.4 - dusk * 1.5;
  world.sun.color.set(0xfff4e0).lerp(new THREE.Color(0xff9a5a), dusk);
  world.hemi.intensity = 1.1 - dusk * 0.45;
  const night = THREE.MathUtils.smoothstep(k, 0.8, 1);
  for (const l of world.lamps) {
    l.bulbMat.emissiveIntensity = night * 2.2;
    l.light.intensity = night * 14;
  }
  world.windows.emissive.set(0x000000).lerp(new THREE.Color(0x8a6a20), night);
}

// clicks on the kiosk or the shed open their panel; dragging the camera does not
function wirePicking() {
  const ray = new THREE.Raycaster();
  const pointer = new THREE.Vector2();
  const hit = (e) => {
    const rect = renderer.domElement.getBoundingClientRect();
    pointer.set(((e.clientX - rect.left) / rect.width) * 2 - 1, -((e.clientY - rect.top) / rect.height) * 2 + 1);
    ray.setFromCamera(pointer, camera);
    let node = ray.intersectObjects(world.hotspots, true)[0]?.object;
    while (node && !node.userData.hotspot) node = node.parent;
    return node?.userData.hotspot ?? null;
  };
  let down = null;
  renderer.domElement.addEventListener("pointerdown", (e) => { down = { x: e.clientX, y: e.clientY }; });
  renderer.domElement.addEventListener("pointerup", (e) => {
    if (!down || Math.hypot(e.clientX - down.x, e.clientY - down.y) > 6) return;
    const spot = hit(e);
    if (spot) openPanel(spot);
  });
  renderer.domElement.addEventListener("pointermove", (e) => {
    if (e.buttons) return;
    $("#stage").classList.toggle("pointer", Boolean(hit(e)));
  });
}

// ---- drawing the run into the scene ----------------------------------------------

function renderPallets(stock) {
  for (const p of state.products) {
    const { crates, sign } = world.pallets[p.id];
    const want = Math.min(Math.ceil(stock[p.id] / UNITS_PER_CRATE), MAX_CRATES);
    while (crates.children.length > want) crates.remove(crates.children[crates.children.length - 1]);
    while (crates.children.length < want) {
      const c = crateMesh(p.id);
      c.position.copy(crateSlot(p.id, crates.children.length));
      crates.add(c);
    }
    sign.element.className = `lbl-pallet ${stock[p.id] ? "" : "empty"}`;
    sign.element.title = p.name;
    sign.element.innerHTML = `<span class="em">${EMOJI[p.id]}</span><b>${stock[p.id]}</b>`;
  }
  world.storageBoard.element.innerHTML = `<h4>📦 Storage</h4>` + state.products.map((p) => `
    <div class="row ${stock[p.id] ? "" : "empty"}" style="--accent:${COLOR[p.id]}">
      <span class="em">${EMOJI[p.id]}</span><span class="nm">${esc(p.name)}</span><b>${stock[p.id]}</b>
    </div>`).join("");
}

function renderKiosk(stock) {
  const { canvas, texture } = world.menu;
  const c = canvas.getContext("2d");
  const { width: w, height: h } = canvas;
  c.fillStyle = "#2f3a33";
  c.fillRect(0, 0, w, h);
  c.strokeStyle = "#f6e6cb";
  c.lineWidth = 8;
  c.strokeRect(4, 4, w - 8, h - 8);
  state.products.forEach((p, i) => {
    const cx = (w / 6) * (1 + i * 2);
    c.textAlign = "center";
    c.textBaseline = "middle";
    c.font = `44px ${EMOJI_FONT}`;
    c.fillText(EMOJI[p.id], cx - 70, h / 2);
    c.fillStyle = "#ffffff";
    c.font = "800 40px system-ui, sans-serif";
    c.fillText(fmt(p.price), cx + 30, h / 2 - 18);
    c.fillStyle = state.finished ? "#d9d4c4" : p.demand ? "#bfe6b0" : "#ffb3a8";
    c.font = "700 26px system-ui, sans-serif";
    c.fillText(state.finished ? "closed" : `${p.demand}/day`, cx + 30, h / 2 + 26);
    if (i < 2) {
      c.fillStyle = "rgba(246,230,203,.35)";
      c.fillRect((w / 3) * (i + 1) - 2, 20, 4, h - 40);
    }
  });
  texture.needsUpdate = true;
  for (const p of state.products) world.displays[p.id].visible = stock[p.id] > 0;
}

// ---- HUD ---------------------------------------------------------------------------

function renderStockRows(stock) {
  const forecast = Object.fromEntries(state.stock_overview.lines.map((l) => [l.product, l]));
  $("#hud-stock").innerHTML = `<h3>In storage</h3>` + state.products.map((p) => {
    const sub = dayRunning ? "on sale now" : state.finished ? "trading closed" : `sells ${forecast[p.id].sells_today} today`;
    return `<div class="stock-row" style="--accent:${COLOR[p.id]}">
      <span class="em" aria-hidden="true">${EMOJI[p.id]}</span>
      <span class="nm">${esc(p.name)}<small>${sub}</small></span>
      <span class="units" aria-label="${esc(p.name)} in stock">${stock[p.id]}</span>
    </div>`;
  }).join("");
}

function setCash(cents, bump = false) {
  const el = $("#hud-cash");
  el.textContent = fmt(cents);
  if (bump && !calm.matches) {
    el.classList.remove("bump");
    void el.getBoundingClientRect();
    el.classList.add("bump");
  }
}

function renderHud() {
  const pips = [];
  for (let d = 1; d <= state.last_day; d++) {
    const cls = d < state.day ? "done" : d === state.day ? "current" : "";
    pips.push(`<li class="${cls}">${d < state.day ? "✓" : d}</li>`);
  }
  $("#day-pips").innerHTML = pips.join("");
  $("#day-label").textContent = state.finished ? "Run complete" : `Day ${state.day} of ${state.last_day}`;
  setCash(state.cash);
  const gain = state.overall_gain;
  const gainEl = $("#hud-gain");
  gainEl.textContent = `${fmtSigned(gain)} overall`;
  gainEl.className = `sub ${gain > 0 ? "up" : gain < 0 ? "down" : ""}`;
}

function renderToolbar() {
  const locked = animating || state.finished;
  $("#btn-order").disabled = locked;
  $("#btn-prices").disabled = locked;
  $("#btn-open").disabled = locked;
  $("#open-label").textContent = dayRunning
    ? `Day ${dayRunning} is open…`
    : state.finished ? "Run complete" : `Open day ${state.day}`;
  $("#btn-fast").hidden = !animating;
  const empty = state.products.every((p) => p.stock === 0);
  $("#btn-order").classList.toggle("hint", empty && !locked);
}

function renderAll() {
  renderHud();
  renderStockRows(stockOf(state));
  renderPallets(stockOf(state));
  renderKiosk(stockOf(state));
  renderToolbar();
  if (panelMode) renderPanel();
}

// live sales ticker: every sale and every student who turned away
const tally = { units: {}, revenue: 0 };
function resetTicker(day) {
  tally.units = Object.fromEntries(state.products.map((p) => [p.id, 0]));
  tally.revenue = 0;
  $("#ticker-day").textContent = `Day ${day}`;
  $("#ticker-list").innerHTML = "";
  $("#ticker").hidden = false;
  renderTally();
}
function renderTally() {
  $("#ticker-totals").innerHTML = state.products.map((p) =>
    `<span>${EMOJI[p.id]}<b>${tally.units[p.id]}</b>sold</span>`).join("")
    + `<span class="rev">Revenue<b>${fmt(tally.revenue)}</b></span>`;
}
function tick(customer) {
  const p = product(customer.pid);
  const li = document.createElement("li");
  if (customer.reason) {
    li.className = "miss";
    li.innerHTML = `<span>😞</span><span>wanted ${EMOJI[p.id]} ${esc(p.name)}</span><span class="amt">${customer.reason}</span>`;
  } else {
    tally.units[p.id] += customer.units;
    tally.revenue += customer.amount;
    li.innerHTML = `<span>${customer.face}</span><span>bought ${customer.units}× ${EMOJI[p.id]} ${esc(p.name)}</span><span class="amt">+${fmt(customer.amount)}</span>`;
    renderTally();
  }
  const list = $("#ticker-list");
  list.prepend(li);
  while (list.children.length > 7) list.lastChild.remove();
}

// ---- side panel: order stock and prices ------------------------------------------

function openPanel(mode) {
  if (animating || state.finished) return;
  panelMode = mode;
  $("#panel").hidden = false;
  renderPanel();
}
function closePanel() {
  panelMode = null;
  $("#panel").hidden = true;
}

function renderPanel() {
  const body = $("#panel-body");
  if (panelMode === "order") {
    $("#panel-title").textContent = "🚚 Order stock";
    const p = product(orderProduct);
    const max = Math.floor(state.cash / p.cost);
    body.innerHTML = `
      <div class="pick" role="group" aria-label="Product">
        ${state.products.map((x) => `
          <button type="button" data-pick="${x.id}" aria-pressed="${x.id === orderProduct}" style="--accent:${COLOR[x.id]}">
            <span class="em" aria-hidden="true">${EMOJI[x.id]}</span>
            <span class="nm">${esc(x.name)}</span>
            <small>${fmt(x.cost)} each · ${x.stock} in shed</small>
          </button>`).join("")}
      </div>
      <form id="order-form">
        <div class="field-label"><span>Quantity</span><span>up to ${max} affordable</span></div>
        <div class="stepper">
          <button type="button" data-step="-1" aria-label="One less">−</button>
          <input name="quantity" inputmode="numeric" autocomplete="off" value="10" aria-label="Quantity">
          <button type="button" data-step="1" aria-label="One more">+</button>
        </div>
        <div class="chips">
          ${[5, 10, 25].map((n) => `<button type="button" class="chip" data-set="${n}">${n}</button>`).join("")}
          <button type="button" class="chip" data-set="${max}">Max (${max})</button>
        </div>
        <div class="total" id="order-total" style="margin-top:14px"></div>
        <p class="error" id="order-error"></p>
        <button class="btn wide" type="submit" style="margin-top:12px">Order delivery 🚚</button>
      </form>`;
    updateOrderTotal();
  } else if (panelMode === "prices") {
    $("#panel-title").textContent = "🏷️ Menu board";
    body.innerHTML = `
      <p class="note">Students buy ${state.demand_levels.at_or_below_ref} a day at or below the reference price, ${state.demand_levels.up_to_double_ref} up to twice it, none above.</p>
      ${state.products.map((p) => `
        <form class="price-row" data-price-form="${p.id}">
          <span class="em" aria-hidden="true">${EMOJI[p.id]}</span>
          <span class="nm">${esc(p.name)}<small>Ref. ${fmt(p.ref_price)} · cost ${fmt(p.cost)}</small></span>
          <label class="euro"><span>€</span><input name="price" inputmode="decimal" autocomplete="off"
            value="${(p.price / 100).toFixed(2)}" aria-label="${esc(p.name)} price in euro"></label>
          <button class="btn" type="submit">Save</button>
          <span class="demand" data-demand>Sells up to <b>${p.demand}</b> a day</span>
          <p class="error" data-error></p>
        </form>`).join("")}`;
  }
}

function updateOrderTotal() {
  const out = $("#order-total");
  if (!out) return;
  const text = $("#order-form").quantity.value.trim();
  if (!/^\d+$/.test(text)) {
    out.className = "total";
    out.innerHTML = `<span>Enter a whole number</span><strong>—</strong>`;
    return;
  }
  const total = Number(text) * product(orderProduct).cost;
  const tooMuch = total > state.cash;
  out.className = `total ${tooMuch ? "too-much" : ""}`;
  out.innerHTML = `<span>${tooMuch ? "More than your cash" : "Total cost"}</span><strong>${fmt(total)}</strong>`;
}

function wirePanel() {
  const panel = $("#panel");
  panel.addEventListener("click", (e) => {
    if (e.target.closest("[data-close]")) return closePanel();
    const pickBtn = e.target.closest("[data-pick]");
    if (pickBtn) {
      const typed = $("#order-form")?.quantity.value;
      orderProduct = pickBtn.dataset.pick;
      renderPanel();
      if (typed) $("#order-form").quantity.value = typed;
      return updateOrderTotal();
    }
    const input = $("#order-form")?.quantity;
    const step = e.target.closest("[data-step]");
    const set = e.target.closest("[data-set]");
    if (input && step) {
      const current = /^\d+$/.test(input.value.trim()) ? Number(input.value) : 0;
      input.value = Math.max(1, current + Number(step.dataset.step));
      updateOrderTotal();
    } else if (input && set) {
      input.value = set.dataset.set;
      updateOrderTotal();
    }
  });

  panel.addEventListener("input", (e) => {
    if (e.target.name === "quantity") return updateOrderTotal();
    const form = e.target.closest("[data-price-form]");
    if (!form) return;
    const p = product(form.dataset.priceForm);
    const value = Number(e.target.value.trim().replace(",", "."));
    const note = form.querySelector("[data-demand]");
    if (!Number.isFinite(value) || value <= 0) return;
    const cents = Math.round(value * 100);
    note.innerHTML = cents === p.price
      ? `Sells up to <b>${p.demand}</b> a day`
      : `Sells up to <b>${previewDemand(cents, p.ref_price)}</b> a day · not saved yet`;
  });

  panel.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (e.target.id === "order-form") return order(orderProduct, e.target.quantity.value);
    const form = e.target.closest("[data-price-form]");
    if (form) savePrice(form);
  });
}

// ---- actions -------------------------------------------------------------------

async function run(sequence) {
  animating = true;
  renderToolbar();
  try {
    await sequence();
  } finally {
    animating = false;
    dayRunning = null;
    fast = false;
    renderAll();
  }
}

async function order(pid, quantityText) {
  if (animating) return;
  const before = state;
  const data = await send("/api/buy", { product: pid, quantity: quantityText });
  if (!data) return;
  state = data.state;
  if (data.error) {
    // nothing changed; keep the panel and what was typed, show why
    renderHud();
    renderToolbar();
    $("#order-error").textContent = data.error;
    return toast(data.error, "error");
  }
  closePanel();
  await run(() => playDelivery(pid, before));
  toast(data.message);
}

async function savePrice(form) {
  const pid = form.dataset.priceForm;
  const data = await send("/api/price", { product: pid, price: form.price.value });
  if (!data) return;
  state = data.state;
  if (data.error) {
    form.querySelector("[data-error]").textContent = data.error;
    return toast(data.error, "error");
  }
  form.querySelector("[data-error]").textContent = "";
  const p = product(pid);
  form.price.value = (p.price / 100).toFixed(2);
  form.querySelector("[data-demand]").innerHTML = `Sells up to <b>${p.demand}</b> a day`;
  renderKiosk(stockOf(state));
  renderStockRows(stockOf(state));
  toast(data.message);
}

async function openDay() {
  if (animating || state.finished) return;
  closePanel();
  const before = state;
  const data = await send("/api/open", { day: state.day });
  if (!data) return;
  state = data.state;
  if (data.error) {
    renderAll();
    return toast(data.error, "error");
  }
  const result = state.history[state.history.length - 1];
  dayRunning = result.day;
  await run(() => playDay(before, result));
  showDaySummary(result);
}

// ---- animation helpers ---------------------------------------------------------------

// A label that rises and fades (coins, costs).
function floatLabel(className, text, at, rise = 2.2, ms = 1300) {
  const obj = label(className, text);
  obj.position.copy(at);
  scene.add(obj);
  const y0 = at.y;
  tween(ms, (k) => {
    obj.position.y = y0 + rise * k;
    obj.element.style.opacity = k < 0.6 ? 1 : 1 - (k - 0.6) / 0.4;
  }, easeOut).then(() => scene.remove(obj));
}

// ---- animation: delivery truck ---------------------------------------------------

async function drive(truck, from, to, ms, easing) {
  await tween(ms, (k) => {
    const x = from + (to - from) * k;
    truck.position.set(x, 0, LANE_Z);
    truck.roll(x);
  }, easing);
}

async function flyCrate(pid, from, to) {
  const c = crateMesh(pid);
  scene.add(c);
  await tween(420, (k) => {
    c.position.lerpVectors(from, to, k);
    c.position.y += Math.sin(Math.PI * k) * 2.2;
    c.rotation.y = k * Math.PI;
  }, easeInOut);
  scene.remove(c);
}

async function playDelivery(pid, before) {
  const truck = buildTruck(pid);
  scene.add(truck);
  await drive(truck, -70, SHED.x, 2000, easeOut);

  // pay on delivery: cash goes down by what the server charged
  const cost = before.cash - state.cash;
  floatLabel("lbl-cost", `−${fmt(cost)}`, new THREE.Vector3(SHED.x, 3.6, LANE_Z));
  setCash(state.cash, true);

  // unload onto the product's pallet: one flying crate per 5 units (1 to 8)
  const startStock = stockOf(before);
  const quantity = stockOf(state)[pid] - startStock[pid];
  const flights = Math.max(1, Math.min(Math.ceil(quantity / UNITS_PER_CRATE), 8));
  const shown = { ...startStock };
  for (let i = 0; i < flights; i++) {
    const after = startStock[pid] + Math.round((quantity * (i + 1)) / flights);
    const slot = Math.min(Math.ceil(after / UNITS_PER_CRATE), MAX_CRATES) - 1;
    await flyCrate(pid, new THREE.Vector3(SHED.x - 1.5, 1.6, LANE_Z - 0.8), crateSlot(pid, Math.max(slot, 0)));
    shown[pid] = after;
    renderPallets(shown);
    renderStockRows(shown);
  }
  renderKiosk(stockOf(state));
  await wait(300);
  await drive(truck, SHED.x, 80, 1600, easeIn);
  scene.remove(truck);
}

// ---- animation: a trading day ------------------------------------------------------

// Turn the day's result into students: one per sale (grouped if many),
// plus a few who leave because a product was sold out or too expensive.
function customersFor(before, result) {
  const total = result.lines.reduce((sum, l) => sum + l.sold, 0);
  const per = Math.max(1, Math.ceil(total / MAX_CUSTOMERS));
  const startStock = stockOf(before);
  const queues = result.lines.map((line) => {
    const q = [];
    for (let left = line.sold; left > 0; left -= per) {
      const units = Math.min(per, left);
      q.push({ pid: line.product, units, amount: units * line.price });
    }
    if (line.sold < line.demand) {
      for (let i = 0; i < Math.min(line.demand - line.sold, 3); i++) q.push({ pid: line.product, reason: "sold out" });
    } else if (line.demand === 0 && startStock[line.product] > 0) {
      for (let i = 0; i < 2; i++) q.push({ pid: line.product, reason: "too pricey" });
    }
    return q;
  });
  const order = [];
  while (queues.some((q) => q.length)) queues.forEach((q) => q.length && order.push(q.shift()));
  return order.map((c) => ({ ...c, face: pick(FACES) }));
}

function queueSpot(pid, place) {
  return new THREE.Vector3(WINDOW_X[pid], 0, SPOT_Z + place * QUEUE_GAP);
}

// Walk a person along a curve, swinging the legs and facing the way they go.
async function walkAlong(person, points) {
  const curve = new THREE.CatmullRomCurve3(points);
  const length = curve.getLength();
  await tween((length / WALK_SPEED) * 1000, (k) => {
    person.position.copy(curve.getPointAt(k));
    const tan = curve.getTangentAt(k);
    person.rotation.y = Math.atan2(tan.x, tan.z);
    const swing = Math.sin(k * length * 3.2) * 0.5;
    person.legs[0].rotation.x = swing;
    person.legs[1].rotation.x = -swing;
  }, linear);
  person.legs.forEach((l) => { l.rotation.x = 0; });
}

function routeIn(door, to) {
  const path = door === DOORS.library ? FOOTPATHS[0] : FOOTPATHS[1];
  const approach = new THREE.Vector3(to.x + (door.x < to.x ? -1.2 : 1.2), 0, Math.max(to.z + 1.6, 6.4));
  return [...path.slice(0, 3), approach, to];
}

function routeOut(from) {
  const side = Math.random() < 0.5 ? -1 : 1;
  return [
    from,
    new THREE.Vector3(from.x + side * 1.6, 0, Math.max(from.z + 1.4, 6.6)),
    new THREE.Vector3(from.x + side * 7, 0, 8.9),
    new THREE.Vector3(side * 60, 0, 9.0),
  ];
}

// one lane per product window: students queue and are served one by one
function makeLanes() {
  return Object.fromEntries(Object.keys(WINDOW_X).map((pid) => [pid, { queue: [], turn: Promise.resolve() }]));
}

async function visit(customer, ledger, lanes) {
  const person = buildPerson();
  const door = Math.random() < 0.5 ? DOORS.library : DOORS.hall;
  person.position.copy(door);
  scene.add(person);
  const lane = lanes[customer.pid];
  lane.queue.push(person);
  await walkAlong(person, routeIn(door, queueSpot(customer.pid, lane.queue.length - 1)));
  person.arrived = true;

  let leave = Promise.resolve();
  const myTurn = lane.turn.then(async () => {
    // step up to the window
    const from = person.position.clone();
    const spot = queueSpot(customer.pid, 0);
    if (from.distanceTo(spot) > 0.05) await walkAlong(person, [from, from.clone().lerp(spot, 0.5), spot]);
    person.rotation.y = Math.PI;

    const p = product(customer.pid);
    const bubble = label(`lbl-bubble ${customer.reason ? "bad" : ""}`,
      customer.reason
        ? `${EMOJI[p.id]} ${customer.reason === "sold out" ? "Sold out? 😞" : "Too pricey! 💸"}`
        : `${customer.units}× ${EMOJI[p.id]} ${esc(p.name)}, please!`);
    bubble.position.set(0, 2.25, 0);
    person.add(bubble);
    await wait(SERVICE_MS * 0.55);

    if (!customer.reason) {
      // the sale: coin over the window, cash up, pallet down, product in hand
      ledger.cash += customer.amount;
      ledger.stock[customer.pid] -= customer.units;
      floatLabel("lbl-coin", `+${fmt(customer.amount)}`, new THREE.Vector3(WINDOW_X[customer.pid], 3.0, 2.4));
      setCash(ledger.cash, true);
      renderPallets(ledger.stock);
      renderStockRows(ledger.stock);
      renderKiosk(ledger.stock);
      const item = productMesh(customer.pid);
      item.scale.setScalar(0.9);
      item.position.set(0.32, 1.05, 0.28);
      person.add(item);
    }
    tick(customer);
    ledger.served += 1;
    moveSun(ledger);
    await wait(SERVICE_MS * 0.45);
    person.remove(bubble);

    // leave and let the next student step up
    lane.queue.splice(lane.queue.indexOf(person), 1);
    lane.queue.forEach((other, i) => {
      if (!other.arrived) return;
      const target = queueSpot(customer.pid, i);
      const start = other.position.clone();
      tween(350, (k) => other.position.lerpVectors(start, target, k));
    });
    leave = walkAlong(person, routeOut(person.position.clone())).then(() => scene.remove(person));
  });
  lane.turn = myTurn;
  await myTurn;
  await leave;
}

// The sun follows the sales: midday when half the students are served,
// late afternoon when the last one is; dusk comes after closing.
function moveSun(ledger) {
  const from = ledger.sky;
  const to = 0.72 * (ledger.served / Math.max(ledger.total, 1));
  ledger.sky = to;
  tween(500, (k) => setSky(from + (to - from) * k), linear);
}

async function playDay(before, result) {
  resetTicker(result.day);
  const customers = customersFor(before, result);
  const ledger = { cash: before.cash, stock: stockOf(before), served: 0, total: customers.length, sky: 0 };
  const lanes = makeLanes();
  const lanesUsed = new Set(customers.map((c) => c.pid)).size || 1;
  const spacing = Math.max(320, SERVICE_MS / lanesUsed + 120);

  setSky(0);
  if (!customers.length) await tween(2500, (k) => setSky(0.72 * k), linear);
  const visits = [];
  for (const c of customers) {
    visits.push(visit(c, ledger, lanes));
    await wait(spacing);
  }
  await Promise.all(visits);
  // closing time: dusk falls and the lamps come on
  await tween(1800, (k) => setSky(0.72 + 0.28 * k), linear);
  await wait(300);
}

// ---- overlays: end of day, end of run, new run --------------------------------------

function showOverlay(html) {
  $("#overlay-card").innerHTML = html;
  $("#overlay").hidden = false;
  $("#overlay-card").querySelector("button, a")?.focus();
}
function hideOverlay() {
  $("#overlay").hidden = true;
}

function showDaySummary(result) {
  const gp = result.gross_profit;
  const rows = result.lines.map((line) => `
    <tr><td>${EMOJI[line.product]} ${esc(product(line.product).name)}</td><td>${line.sold}</td>
    <td>${fmt(line.revenue)}</td><td>${fmt(line.gross_profit)}</td></tr>`).join("");
  const sold = result.lines.reduce((sum, l) => sum + l.sold, 0);
  showOverlay(`
    <p class="eyebrow">🌇 Day ${result.day} closed</p>
    <p class="big ${gp > 0 ? "up" : gp < 0 ? "down" : ""}">${fmtSigned(gp)}</p>
    <p class="note">gross profit · cost of goods sold ${fmt(result.cogs)} · cash now ${fmt(result.cash_after)}</p>
    <table>
      <thead><tr><th>Product</th><th>Sold</th><th>Revenue</th><th>Profit</th></tr></thead>
      <tbody>${rows}</tbody>
      <tfoot><tr><td>Total</td><td>${sold}</td><td>${fmt(result.revenue)}</td><td>${fmt(gp)}</td></tr></tfoot>
    </table>
    <div class="actions">
      <button class="btn" type="button" data-next>${state.finished ? "See the final result" : `Start day ${state.day} ☀️`}</button>
    </div>`);
}

function showFinal() {
  const gain = state.overall_gain;
  showOverlay(`
    <p class="eyebrow">🏁 Run complete · ${state.history.length} days</p>
    <p class="big ${gain > 0 ? "up" : gain < 0 ? "down" : ""}">${fmtSigned(gain)}</p>
    <p class="note">overall result = final cash ${fmt(state.cash)} + stock at cost ${fmt(state.stock_value)} − ${fmt(state.starting_cash)} start</p>
    <div class="actions" style="margin-top:18px">
      <button class="btn" type="button" data-new-run>Start a new run</button>
      <a class="btn ghost" href="/">Dashboard</a>
    </div>
    <div class="actions"><button class="btn ghost" type="button" data-dismiss>Look around the campus</button></div>`);
}

function askNewRun() {
  $("#dialog-text").textContent = state.finished
    ? `Your completed run (${fmtSigned(state.overall_gain)}) is replaced by a fresh one: day 1, ${fmt(state.starting_cash)}, empty storage. This cannot be undone.`
    : `This ends your run on day ${state.day} with ${fmt(state.cash)} cash. You start again on day 1 with ${fmt(state.starting_cash)} and empty storage. This cannot be undone.`;
  const dialog = $("#new-run-dialog");
  dialog.returnValue = "";
  dialog.showModal();
}

function wireOverlay() {
  $("#overlay").addEventListener("click", (e) => {
    if (e.target.closest("[data-next]")) {
      hideOverlay();
      setSky(0);
      if (state.finished) showFinal();
    } else if (e.target.closest("[data-dismiss]")) {
      hideOverlay();
    } else if (e.target.closest("[data-new-run]")) {
      askNewRun();
    }
  });
  $("#new-run-dialog").addEventListener("close", async (e) => {
    if (e.target.returnValue !== "confirm") return;
    const data = await send("/api/new-run", { confirm: true });
    if (!data) return;
    state = data.state;
    if (data.error) return toast(data.error, "error");
    hideOverlay();
    $("#ticker").hidden = true;
    setSky(0);
    renderAll();
    toast(data.message);
  });
}

// ---- boot ----------------------------------------------------------------------

function wireUi() {
  $("#btn-order").addEventListener("click", () => openPanel("order"));
  $("#btn-prices").addEventListener("click", () => openPanel("prices"));
  $("#btn-open").addEventListener("click", openDay);
  $("#btn-fast").addEventListener("click", () => { fast = true; });
  $("#btn-camera").addEventListener("click", () => resetCamera(true));
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && panelMode) closePanel();
  });
}

async function boot() {
  initScene();
  wirePicking();
  wireUi();
  wirePanel();
  wireOverlay();
  try {
    state = await (await fetch("/api/state")).json();
  } catch {
    return toast("Could not load the run. Start the server with: uv run python app.py", "error");
  }
  renderAll();
  $("#loading").hidden = true;
  if (state.finished) showFinal();
}

boot();
