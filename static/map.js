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
const DOORS = { west: new THREE.Vector3(-10.5, 0, -7.6), east: new THREE.Vector3(10.5, 0, -7.6) };
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

// Inside the dashboard page the map runs embedded: as a small live window
// ("preview") or as the main view. Opened on its own it is always the main view.
const embedded = new URLSearchParams(location.search).has("embed");
let mode = embedded ? "preview" : "main";

// Animations play one after another, in the order the actions happened,
// whether the action came from the map or from the dashboard.
let chain = Promise.resolve();
function enqueue(job) {
  chain = chain.then(job).catch((err) => console.error(err));
  return chain;
}
function tellDashboard(message) {
  if (embedded) window.parent.postMessage(message, location.origin);
}

// scene objects that change with the run
let scene, camera, renderer, labels, controls;
const world = { pallets: {}, displays: {}, menu: null, lamps: [], sun: null, hemi: null, clouds: [], hotspots: [], windows: null, sea: null, foam: null, lighthouse: null };

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

// ---- the campus: a stylised Nova SBE in Carcavelos -----------------------------------
// Low white buildings with glass ribbons ("fingers") behind the plaza, the coastal
// road in front, then Carcavelos beach and the Atlantic. Not a measured model.

const FOOTPATHS = [
  [new THREE.Vector3(-10.5, 0, -7.6), new THREE.Vector3(-10.2, 0, -3), new THREE.Vector3(-9, 0, 2.5), new THREE.Vector3(-7, 0, 6)],
  [new THREE.Vector3(10.5, 0, -7.6), new THREE.Vector3(12.8, 0, -4), new THREE.Vector3(13, 0, 3), new THREE.Vector3(8, 0, 5.8), new THREE.Vector3(0, 0, 6.6)],
];
const TUNNEL = { x: -17, campusZ: 7.4, beachZ: 17.9 };   // under the coastal road to the beach
const SHORE_Z = 24.5;                                    // where the sand meets the water

const WHITE = 0xf4f2ec;

function buildGround() {
  // the campus ends at the beach: grass only up to the promenade
  const grass = new THREE.Mesh(new THREE.PlaneGeometry(240, 112), mat(0x8cc870));
  grass.rotation.x = -Math.PI / 2;
  grass.position.z = -40;
  grass.receiveShadow = true;
  scene.add(grass);

  for (const [x, z, r] of [[-20, 2, 5], [20, 2, 4], [0, -2, 4], [-34, -4, 6], [34, -2, 5]]) {
    const patch = new THREE.Mesh(new THREE.CircleGeometry(r, 24), mat(0x80bd65));
    patch.rotation.x = -Math.PI / 2;
    patch.position.set(x, 0.005, z);
    patch.receiveShadow = true;
    scene.add(patch);
  }

  // footpaths from the buildings to the plaza and to the beach tunnel, and the plaza
  const pathMat = mat(0xeadfc4, { side: THREE.DoubleSide });
  for (const pts of FOOTPATHS) scene.add(ribbon(new THREE.CatmullRomCurve3(pts), 2.2, pathMat));
  scene.add(ribbon(new THREE.CatmullRomCurve3([
    new THREE.Vector3(-11, 0, 6.6), new THREE.Vector3(-14.5, 0, 7.2), new THREE.Vector3(TUNNEL.x, 0, TUNNEL.campusZ - 0.6),
  ]), 2, pathMat));
  const plaza = new THREE.Mesh(new THREE.CircleGeometry(6.5, 40), pathMat);
  plaza.rotation.x = -Math.PI / 2;
  plaza.scale.set(1.35, 1, 1);
  plaza.position.set(KIOSK.x, 0.018, 5.2);
  plaza.receiveShadow = true;
  scene.add(plaza);

  // driveway, sidewalk, coastal road with lane markings, promenade
  scene.add(box(3.2, 0.06, 6.6, mat(0xc9c5ba), SHED.x, 0.03, 5.3));
  scene.add(box(240, 0.14, 1.0, mat(0xdcd7ca), 0, 0.07, 9.0));
  const road = box(240, 0.06, 6.2, mat(0x5d6168), 0, 0.03, 12.6);
  road.castShadow = false;
  scene.add(road);
  const dash = mat(0xf5f2e8);
  for (let x = -110; x <= 110; x += 5) {
    const d = box(2.6, 0.02, 0.18, dash, x, 0.07, 12.6);
    d.castShadow = false;
    scene.add(d);
  }
  scene.add(box(240, 0.22, 1.1, mat(0xd8d1bf), 0, 0.11, 16.25));
}

function buildCoast() {
  // Carcavelos beach
  const sand = new THREE.Mesh(new THREE.PlaneGeometry(240, SHORE_Z - 16.6 + 1.5), mat(0xedd9a6));
  sand.rotation.x = -Math.PI / 2;
  sand.position.set(0, 0.0, (16.6 + SHORE_Z + 1.5) / 2);
  sand.receiveShadow = true;
  scene.add(sand);

  // the Atlantic, with gentle waves (moved in the render loop)
  const sea = new THREE.Mesh(
    new THREE.PlaneGeometry(320, 160, 96, 48),
    new THREE.MeshStandardMaterial({ color: 0x2f8fc4, roughness: 0.35, metalness: 0.05, flatShading: true }),
  );
  sea.rotation.x = -Math.PI / 2;
  sea.position.set(0, -0.25, SHORE_Z + 80);
  sea.receiveShadow = true;
  scene.add(sea);
  world.sea = sea;
  const foam = new THREE.Mesh(new THREE.PlaneGeometry(240, 1.2), new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.7 }));
  foam.rotation.x = -Math.PI / 2;
  foam.position.set(0, 0.04, SHORE_Z + 0.2);
  scene.add(foam);
  world.foam = foam;

  // beach umbrellas and towels
  const colours = [0xe34948, 0xffd25a, 0x2a78d6, 0x1baf7a, 0xe87ba4, 0xeb6834];
  [[-30, 19.5], [-22, 21], [-6, 20.2], [3, 21.6], [14, 19.8], [26, 21], [36, 19.6]].forEach(([x, z], i) => {
    const pole = cylinder(0.05, 0.05, 2.2, mat(0xf4f2ec), 6);
    pole.position.set(x, 1.1, z);
    const top = new THREE.Mesh(new THREE.ConeGeometry(1.5, 0.6, 10), mat(colours[i % colours.length], { flatShading: true }));
    top.position.set(x, 2.3, z);
    top.castShadow = true;
    const towel = box(0.9, 0.03, 1.8, mat(colours[(i + 2) % colours.length]), x + 1.1, 0.02, z + 0.4);
    towel.castShadow = false;
    scene.add(pole, top, towel);
  });

  // the tunnel under the road: one portal on campus, one on the beach
  scene.add(portal(TUNNEL.x, TUNNEL.campusZ, 0));
  scene.add(portal(TUNNEL.x, TUNNEL.beachZ, Math.PI));
  const sign = label("lbl-building", "🏖️ BEACH TUNNEL");
  sign.position.set(TUNNEL.x, 3.6, TUNNEL.campusZ);
  scene.add(sign);
  const beach = label("lbl-building", "PRAIA DE CARCAVELOS");
  beach.position.set(8, 1.5, 22.5);
  scene.add(beach);
}

// a concrete tunnel mouth facing +z (rotated for the beach side)
function portal(x, z, rot) {
  const g = new THREE.Group();
  const concrete = mat(0xd9d6cf);
  g.add(box(0.5, 2.6, 2.2, concrete, -1.75, 1.3, 0), box(0.5, 2.6, 2.2, concrete, 1.75, 1.3, 0));
  g.add(box(4, 0.5, 2.2, concrete, 0, 2.85, 0));
  const dark = box(3, 2.6, 0.1, mat(0x1d1f24), 0, 1.3, -0.9);
  dark.castShadow = false;
  g.add(dark);
  g.position.set(x, 0, z);
  g.rotation.y = rot;
  return g;
}

// the Forte de São Julião da Barra on the coast, with its lighthouse
function buildFort() {
  const g = new THREE.Group();
  g.position.set(-56, 0, 27);
  const rock = new THREE.Mesh(new THREE.CylinderGeometry(15, 17, 1.6, 9), mat(0x9c9483, { flatShading: true }));
  rock.position.y = -0.5;
  rock.receiveShadow = true;
  g.add(rock);
  // star-shaped bastions
  const star = new THREE.Shape();
  const points = 10;
  for (let i = 0; i <= points; i++) {
    const a = (i / points) * Math.PI * 2;
    const r = i % 2 ? 7.2 : 11.5;
    const px = Math.cos(a) * r;
    const py = Math.sin(a) * r;
    if (i === 0) star.moveTo(px, py);
    else star.lineTo(px, py);
  }
  const wallGeo = new THREE.ExtrudeGeometry(star, { depth: 3.4, bevelEnabled: false });
  wallGeo.rotateX(-Math.PI / 2);
  const walls = new THREE.Mesh(wallGeo, mat(0xd8c39a, { flatShading: true }));
  walls.position.y = 0.2;
  walls.castShadow = true;
  walls.receiveShadow = true;
  g.add(walls);
  g.add(box(9, 4, 7, mat(0xe9dcc0), 0, 5.4, 0));
  g.add(box(9.4, 0.5, 7.4, mat(0xc8704c), 0, 7.6, 0));
  const tower = cylinder(0.9, 1.1, 8, mat(0xffffff), 14);
  tower.position.set(3, 9, 1.5);
  const lantern = cylinder(0.75, 0.75, 1.2, mat(0xfff3c4, { emissive: 0xffd77a, emissiveIntensity: 0 }), 12);
  lantern.position.set(3, 13.6, 1.5);
  const cap = new THREE.Mesh(new THREE.ConeGeometry(1, 1, 12), mat(0xc03030));
  cap.position.set(3, 14.7, 1.5);
  g.add(tower, lantern, cap);
  world.lighthouse = lantern.material;
  const name = label("lbl-building", "FORTE DE S. JULIÃO DA BARRA");
  name.position.set(0, 16.5, 0);
  g.add(name);
  scene.add(g);
}

// a low white building with glass ribbons, its front facing the plaza (+z)
function finger(x, front, length, floors, width = 9) {
  const g = new THREE.Group();
  const h = floors * 3.4;
  g.position.set(x, 0, front - length / 2);
  g.add(box(width, h, length, mat(WHITE), 0, h / 2, 0));
  g.add(box(width + 1.4, 0.45, length + 1.4, mat(0xffffff), 0, h + 0.22, 0));          // thin roof slab
  for (let f = 0; f < floors; f++) {
    const y = f * 3.4 + 1.85;
    g.add(box(0.16, 1.7, length - 1.6, world.windows, width / 2 + 0.04, y, 0));
    g.add(box(0.16, 1.7, length - 1.6, world.windows, -width / 2 - 0.04, y, 0));
    g.add(box(width - 1.6, 1.7, 0.16, world.windows, 0, y, length / 2 + 0.04));
  }
  g.add(box(3.2, 2.7, 0.3, mat(0x2d3a48, { roughness: 0.3 }), 0, 1.35, length / 2 + 0.12)); // entrance
  g.add(box(4.6, 0.25, 2.4, mat(0xffffff), 0, 3.0, length / 2 + 1.2));                   // entrance canopy
  scene.add(g);
  return g;
}

function buildNovaCampus() {
  world.windows = mat(0x5f87a6, { roughness: 0.15, metalness: 0.3, emissive: 0x000000 });

  // four fingers behind the plaza, joined at the back by the learning street
  finger(-24, -8, 28, 2);
  const main = finger(-10.5, -7.8, 28, 3);
  finger(10.5, -7.8, 28, 3);
  finger(24, -8, 28, 2);
  const street = box(60, 6.8, 9, mat(WHITE), 0, 3.4, -40);
  scene.add(street);
  scene.add(box(61.4, 0.45, 10.4, mat(0xffffff), 0, 7.02, -40));
  scene.add(box(57, 1.7, 0.16, world.windows, 0, 1.85, -35.46));
  scene.add(box(57, 1.7, 0.16, world.windows, 0, 5.25, -35.46));

  // school name on the main finger, facing the plaza
  const nameTex = canvasTexture(512, 128, (c, w, h) => {
    c.fillStyle = "#f4f2ec";
    c.fillRect(0, 0, w, h);
    c.fillStyle = "#1d2a4a";
    c.font = "800 78px system-ui, sans-serif";
    c.textAlign = "center";
    c.textBaseline = "middle";
    c.fillText("NOVA SBE", w / 2, h / 2 + 4);
  });
  // lettering standing on the roof edge, facing the plaza
  const white = mat(WHITE);
  const nameSign = new THREE.Mesh(new THREE.BoxGeometry(6.4, 1.6, 0.2), [white, white, white, white, mat(0xffffff, { map: nameTex }), white]);
  nameSign.position.set(0, 11.5, 13.6);
  nameSign.castShadow = true;
  main.add(nameSign);

  // the atrium between the middle fingers: steel frame and a glass roof
  const atrium = new THREE.Group();
  atrium.position.set(0, 0, -29);
  const glass = new THREE.MeshStandardMaterial({ color: 0xbfe1f2, transparent: true, opacity: 0.38, roughness: 0.1 });
  atrium.add(new THREE.Mesh(new THREE.BoxGeometry(11.6, 6.4, 12), glass));
  atrium.children[0].position.y = 3.2;
  const steel = mat(0xe8e8e8);
  for (const sx of [-5.8, 5.8]) for (const sz of [-6, 6]) atrium.add(box(0.3, 6.6, 0.3, steel, sx, 3.3, sz));
  for (let i = -5; i <= 5; i += 2.5) atrium.add(box(0.18, 0.18, 12, steel, i, 6.5, 0));
  scene.add(atrium);

  // the pentagonal water tank on the lawn
  const pentagon = new THREE.Shape();
  for (let i = 0; i <= 5; i++) {
    const a = (i / 5) * Math.PI * 2 - Math.PI / 2;
    if (i === 0) pentagon.moveTo(Math.cos(a) * 3.6, Math.sin(a) * 3.6);
    else pentagon.lineTo(Math.cos(a) * 3.6, Math.sin(a) * 3.6);
  }
  const rim = new THREE.ExtrudeGeometry(pentagon, { depth: 0.45, bevelEnabled: false });
  rim.rotateX(-Math.PI / 2);
  const tank = new THREE.Mesh(rim, mat(0xe2ddd2));
  tank.position.set(0, 0, -15);
  tank.receiveShadow = true;
  scene.add(tank);
  const water = new THREE.Mesh(new THREE.CircleGeometry(3.1, 5), mat(0x3d9bd0, { roughness: 0.2 }));
  water.rotation.x = -Math.PI / 2;
  water.rotation.z = Math.PI / 2;
  water.position.set(0, 0.47, -15);
  scene.add(water);

  // student residences to the east, a sports field to the west
  const res = finger(42, -6, 22, 3, 8);
  for (let f = 1; f < 3; f++) res.add(box(8.6, 0.15, 1.2, mat(0xffffff), 0, f * 3.4, 11.6));
  const field = new THREE.Mesh(new THREE.PlaneGeometry(14, 22), mat(0x5fae4f));
  field.rotation.x = -Math.PI / 2;
  field.position.set(-42, 0.01, -18);
  field.receiveShadow = true;
  scene.add(field);
  const line = mat(0xffffff);
  for (const [w, d, x, z] of [[14, 0.15, -42, -7.1], [14, 0.15, -42, -28.9], [0.15, 22, -48.9, -18], [0.15, 22, -35.1, -18], [14, 0.15, -42, -18]]) {
    const l = box(w, 0.02, d, line, x, 0.03, z);
    l.castShadow = false;
    scene.add(l);
  }

  for (const [text, x, y, z] of [["LIBRARY", -24, 8.6, -8], ["ATRIUM", 0, 8, -25],
    ["LEARNING STREET", 0, 9.5, -40], ["RESIDENCES", 42, 12.4, -6], ["SPORTS FIELD", -42, 1.5, -18]]) {
    const tag = label("lbl-building", text);
    tag.position.set(x, y, z);
    scene.add(tag);
  }
}

// Mediterranean stone pine: tall bare trunk, flat wide crown
function stonePine(x, z, s = 1) {
  const g = new THREE.Group();
  const trunk = cylinder(0.18 * s, 0.3 * s, 4.6 * s, mat(0x7a5236), 7);
  trunk.position.y = 2.3 * s;
  trunk.rotation.z = (Math.random() - 0.5) * 0.18;
  const crown = new THREE.Mesh(new THREE.SphereGeometry(2.7 * s, 9, 6), mat(pick([0x3f7f3a, 0x4a8a3f, 0x3b7536]), { flatShading: true }));
  crown.scale.set(1, 0.42, 1);
  crown.position.y = 4.9 * s;
  crown.castShadow = true;
  const crown2 = new THREE.Mesh(new THREE.SphereGeometry(1.8 * s, 8, 5), mat(0x4f9445, { flatShading: true }));
  crown2.scale.set(1, 0.45, 1);
  crown2.position.set(1.2 * s, 5.4 * s, 0.6 * s);
  crown2.castShadow = true;
  g.add(trunk, crown, crown2);
  g.position.set(x, 0, z);
  g.rotation.y = Math.random() * Math.PI;
  scene.add(g);
}

function juniper(x, z, s = 1) {
  const bush = new THREE.Mesh(new THREE.ConeGeometry(0.9 * s, 2.4 * s, 7), mat(0x2f6a3a, { flatShading: true }));
  bush.position.set(x, 1.2 * s, z);
  bush.castShadow = true;
  scene.add(bush);
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
    t.x = THREE.MathUtils.clamp(t.x, -50, 45);
    t.z = THREE.MathUtils.clamp(t.z, -40, 26);
    t.y = 0;
  });

  world.hemi = new THREE.HemisphereLight(0xdff1ff, 0x6a8f4e, 1.1);
  scene.add(world.hemi);
  const sun = new THREE.DirectionalLight(0xfff4e0, 2.4);
  sun.castShadow = true;
  sun.shadow.mapSize.set(2048, 2048);
  Object.assign(sun.shadow.camera, { left: -70, right: 70, top: 60, bottom: -60, near: 1, far: 200 });
  sun.shadow.bias = -0.0004;
  scene.add(sun, sun.target);
  world.sun = sun;

  buildGround();
  buildCoast();
  buildNovaCampus();
  buildFort();
  buildKiosk();
  buildShed();
  buildClouds();
  // the pine and juniper woodland around the campus
  for (const [x, z, s] of [[-17, -2, 1.1], [-30, 4, 1.2], [-36, -2, 1], [-52, -8, 1.3], [-56, -24, 1.2], [-50, 4, 1.1],
    [18, -2, 1], [31, 3, 1.2], [52, -8, 1.2], [56, -26, 1.3], [-31, -26, 1.1], [31, -27, 1], [-6, -46, 1.2],
    [14, -50, 1.3], [-24, -50, 1.1], [36, -44, 1.2], [-44, -40, 1.3]]) stonePine(x, z, s);
  for (const [x, z] of [[-14, 3], [-20, 5], [17, 4.5], [22, 5], [-5, -12], [5, -12], [-29, -6], [29, -6]]) juniper(x, z, 0.8 + Math.random() * 0.4);
  lamp(-11.5, 6.4);
  lamp(3.4, 6.6);
  lamp(-4, 8.3);
  bench(-12.5, 8, 0);
  bench(2.2, 8.2, 0);

  resetCamera(false);
  resize();
  window.addEventListener("resize", resize);
  setSky(0);

  renderer.setAnimationLoop((now) => {
    controls.update();
    waves(now / 1000);
    world.clouds.forEach((c, i) => {
      c.position.x += 0.004 * (i + 1);
      if (c.position.x > 60) c.position.x = -60;
    });
    renderer.render(scene, camera);
    labels.render(scene, camera);
  });
}

// gentle Atlantic swell and foam at the shoreline
function waves(t) {
  if (calm.matches) return;
  const pos = world.sea.geometry.attributes.position;
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i);
    const y = pos.getY(i);
    pos.setZ(i, Math.sin(x * 0.11 + t * 1.1) * 0.16 + Math.cos(y * 0.17 + t * 0.8) * 0.14);
  }
  pos.needsUpdate = true;
  world.foam.material.opacity = 0.45 + Math.sin(t * 1.3) * 0.25;
  world.foam.position.z = SHORE_Z + 0.2 + Math.sin(t * 1.3) * 0.35;
}

function defaultView() {
  if (mode === "preview") return { position: new THREE.Vector3(-9, 21, 29), target: new THREE.Vector3(2, 0, -1) };
  const aspect = window.innerWidth / window.innerHeight;
  const k = aspect < 0.8 ? 1.9 : aspect < 1.3 ? 1.35 : 1;
  return { position: new THREE.Vector3(-8 * k, 30 * k, 56 * k), target: new THREE.Vector3(1, 0, -4) };
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
  world.lighthouse.emissiveIntensity = night * 3;
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
  tellDashboard({ type: "panel-open" }); // the map's panel and the dashboard panel share the right side
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
  if (data.error) {
    // nothing changed; keep the panel and what was typed, show why
    state = data.state;
    renderHud();
    renderToolbar();
    $("#order-error").textContent = data.error;
    return toast(data.error, "error");
  }
  closePanel();
  tellDashboard({ type: "action", after: data.state });
  await enqueue(async () => {
    state = data.state;
    await run(() => playDelivery(pid, before));
  });
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
  tellDashboard({ type: "action", after: data.state });
  toast(data.message);
}

async function openDay() {
  if (animating || state.finished) return;
  closePanel();
  const before = state;
  const data = await send("/api/open", { day: state.day });
  if (!data) return;
  if (data.error) {
    state = data.state;
    renderAll();
    return toast(data.error, "error");
  }
  tellDashboard({ type: "action", after: data.state });
  await enqueue(async () => {
    state = data.state;
    const result = state.history[state.history.length - 1];
    dayRunning = result.day;
    await run(() => playDay(before, result));
    showDaySummary(result);
  });
}

// The dashboard did something: show it on the campus. Its own screen already
// shows the numbers, so a trading day ends without the summary card here.
function syncFromDashboard(msg) {
  enqueue(async () => {
    const before = msg.before;
    state = msg.after;
    if (msg.kind === "buy") {
      closePanel();
      await run(() => playDelivery(msg.product, before));
    } else if (msg.kind === "open") {
      closePanel();
      hideOverlay();
      const result = state.history[state.history.length - 1];
      dayRunning = result.day;
      await run(() => playDay(before, result));
      await wait(1200);
      await tween(900, (k) => setSky(1 - k), linear);
    } else {
      if (msg.kind === "new-run") {
        hideOverlay();
        $("#ticker").hidden = true;
        setSky(0);
      }
      renderAll();
    }
  });
}

function setMode(next) {
  mode = next;
  const preview = mode === "preview";
  document.body.classList.toggle("preview", preview);
  controls.enabled = !preview;
  controls.autoRotate = preview;
  controls.autoRotateSpeed = 0.5;
  if (preview) closePanel();
  resetCamera(!calm.matches);
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
  const path = door === DOORS.west ? FOOTPATHS[0] : FOOTPATHS[1];
  const approach = new THREE.Vector3(to.x + (door.x < to.x ? -1.2 : 1.2), 0, Math.max(to.z + 1.6, 6.4));
  return [...path.slice(0, -1), approach, to];
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

// After buying, some students head back along the road, others take the tunnel to the beach.
async function leaveCampus(person) {
  const from = person.position.clone();
  if (Math.random() < 0.45) {
    await walkAlong(person, [
      from,
      new THREE.Vector3(from.x - 1.5, 0, Math.max(from.z + 1.5, 6.8)),
      new THREE.Vector3(TUNNEL.x + 2, 0, 7.2),
      new THREE.Vector3(TUNNEL.x, 0, TUNNEL.campusZ - 0.4),
    ]);
    await tween(450, (k) => { person.position.y = -1.9 * k; }, linear);       // down into the tunnel
    person.position.set(TUNNEL.x, -1.9, TUNNEL.beachZ - 0.4);
    person.rotation.y = 0;
    await tween(450, (k) => { person.position.y = -1.9 * (1 - k); }, linear); // up on the beach
    const spot = new THREE.Vector3(TUNNEL.x - 8 + Math.random() * 30, 0, 19.5 + Math.random() * 3.5);
    await walkAlong(person, [person.position.clone(), new THREE.Vector3(TUNNEL.x, 0, TUNNEL.beachZ + 1.2), spot]);
    await wait(500);
  } else {
    await walkAlong(person, routeOut(from));
  }
  scene.remove(person);
}

// one lane per product window: students queue and are served one by one
function makeLanes() {
  return Object.fromEntries(Object.keys(WINDOW_X).map((pid) => [pid, { queue: [], turn: Promise.resolve() }]));
}

async function visit(customer, ledger, lanes) {
  const person = buildPerson();
  const door = Math.random() < 0.5 ? DOORS.west : DOORS.east;
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
    leave = leaveCampus(person);
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
    tellDashboard({ type: "action", after: data.state });
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
  // embedded: the "Dashboard" link slides the dashboard panel in instead of leaving
  $(".views a").addEventListener("click", (e) => {
    if (!embedded) return;
    e.preventDefault();
    tellDashboard({ type: "open-dashboard" });
  });
  window.addEventListener("message", (e) => {
    if (e.origin !== location.origin || e.source !== window.parent) return;
    const msg = e.data || {};
    if (msg.type === "mode") setMode(msg.mode);
    if (msg.type === "action") syncFromDashboard(msg);
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && panelMode) closePanel();
  });
}

async function boot() {
  document.body.classList.toggle("preview", mode === "preview");
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
  if (mode === "preview") setMode("preview");
  tellDashboard({ type: "ready" });
}

chain = boot();
