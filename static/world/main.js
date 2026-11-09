// The 2.5D world: loads the data, runs the frame loop, walking, camera and doors.
// Walking and the camera are only for showing. Every rule stays on the server.

import { inReach, nearestLocation, openPlaces } from "./locations.js";
import { findPath } from "./paths.js";
import { nearestFreePoint, pointBlocked, resolveMovement } from "./physics.js";
import { drawWorld } from "./render.js";
import { areaAt, stepRoofs, wingsAt } from "./roofs.js";
import {
  PLAYER_RADIUS,
  WALK_SPEED,
  activeZone,
  camera,
  canvas,
  canvasWorldPoint,
  ctx,
  reducedMotion,
  scene,
  world,
} from "./scene.js";
import { initUi, inputBlocked, updateClock, useLocation } from "./ui.js";
import { createWalkers, updateWalkers } from "./walkers.js";
import { joinDorm } from "./zones.js";

const CLICK_REACH = 1.35; // tiles around a door or desk that count as clicking it
const MOVE_KEYS = ["w", "a", "s", "d", "arrowup", "arrowdown", "arrowleft", "arrowright"];

const keys = new Set();
let route = []; // the points a click sends the player through
let pendingUse = null; // the door or desk to use on arrival
let stuckFor = 0; // seconds without getting closer to the target
let lastTime = 0;
let wasWalking = false;
let savedSpot = "";

// ---- position on the server ---------------------------------------------------------

function savePlayer() {
  const { x, y } = scene.player;
  const spot = `${scene.zoneId}:${x.toFixed(2)}:${y.toFixed(2)}`;
  if (spot === savedSpot) return;
  fetch("/api/player", {
    method: "POST",
    keepalive: true,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ zone: scene.zoneId, x, y }),
  })
    .then((res) => {
      if (res.ok) savedSpot = spot;
    })
    .catch(() => {}); // only the position: the next stop saves it again
}

function safePoint(point, zone = activeZone()) {
  return nearestFreePoint(point, zone, world.colliders[zone.id], PLAYER_RADIUS);
}

// ---- the place and the roof ----------------------------------------------------------

// The name of the place in the banner, and the chips: outside, or in the Nova (any of its wings).
// Only written to the page when it changes.
let shownPlace = "";

function renderPlace() {
  const zone = activeZone();
  const area = scene.inNova ? areaAt(scene.player, world.interiors.campus.areas) : null;
  const wing = world.nova.wings.find((entry) => entry.id === scene.wing);
  const name = scene.inNova ? (area ? area.label : (wing?.label ?? world.nova.label)) : zone.name;
  const sub = scene.inNova ? (wing?.label ?? world.nova.label).toUpperCase() : zone.sub;
  const place = `${scene.inNova}:${scene.wing}:${name}`;
  if (place === shownPlace) return;
  shownPlace = place;
  $("#zone-name").textContent = name;
  $("#zone-sub").textContent = sub;
  document.querySelectorAll("[data-place]").forEach((chip) => {
    chip.classList.toggle("active", (chip.dataset.place === "nova") === scene.inNova);
  });
}

// Is the player under the roof, and how far has the roof faded. `instant`: no fade (a new
// start, or the saved position after loading).
function updateRoof(dt, instant = false) {
  const inside = wingsAt(scene.player, world.nova.parts);
  const area = inside.length ? areaAt(scene.player, world.interiors.campus.areas) : null;
  scene.inNova = inside.length > 0;
  scene.wing = area?.wing ?? inside[0] ?? null;
  scene.roofs = stepRoofs(scene.roofs, world.nova.wings, inside, dt, reducedMotion || instant);
  renderPlace();
}

// a new run, or the saved position after loading
function placePlayer({ zone, x, y }) {
  scene.zoneId = zone;
  scene.player = safePoint({ x, y }, world.zones[zone]);
  camera.x = scene.player.x;
  camera.y = scene.player.y;
  route = [];
  pendingUse = null;
  savedSpot = `${zone}:${x.toFixed(2)}:${y.toFixed(2)}`;
  updateRoof(0, true);
}

function use(id) {
  const loc = world.locations[id];
  route = [];
  pendingUse = null;
  useLocation(loc.action);
}

// ---- input ---------------------------------------------------------------------------

function walkTo(point) {
  const zone = activeZone();
  const wanted = {
    x: Math.max(zone.minX, Math.min(zone.maxX, point.x)),
    y: Math.max(zone.minY, Math.min(zone.maxY, point.y)),
  };
  const solid = world.colliders[zone.id];
  const goal = pointBlocked(wanted, solid, PLAYER_RADIUS) ? safePoint(wanted, zone) : wanted;
  route = findPath(scene.player, goal, zone, solid, PLAYER_RADIUS) ?? [];
  stuckFor = 0;
}

function onClick(event) {
  if (scene.preview || inputBlocked()) return;
  window.focus();
  const point = canvasWorldPoint(event);
  // the desks stand inside the Nova and are only drawn while its roof is gone: a click on the
  // closed roof must not pick one
  const places = openPlaces();
  const hit = places.find(([, loc]) => Math.hypot(point.x - loc.x, point.y - loc.y) < CLICK_REACH);
  if (!hit) {
    pendingUse = null;
    return walkTo(point);
  }
  const [id, loc] = hit;
  if (inReach(loc)) return use(id);
  pendingUse = id;
  walkTo(loc); // to the free spot closest to it: the use happens as soon as it is in reach
}

function onKeyDown(event) {
  const key = event.key.toLowerCase();
  const typing = ["INPUT", "SELECT", "TEXTAREA"].includes(event.target?.tagName);
  if (typing || event.metaKey || event.ctrlKey || event.altKey || scene.preview || inputBlocked()) return;
  if (MOVE_KEYS.includes(key)) {
    keys.add(key);
    route = [];
    pendingUse = null;
    event.preventDefault();
  } else if (key === "e") {
    const near = nearestLocation();
    if (near) use(near[0]);
  }
}

function wireInput() {
  window.addEventListener("resize", resize);
  window.addEventListener("keydown", onKeyDown);
  window.addEventListener("keyup", (event) => keys.delete(event.key.toLowerCase()));
  window.addEventListener("blur", () => keys.clear());
  window.addEventListener("pagehide", savePlayer);
  canvas.addEventListener("click", onClick);
  $("#interaction-hint").addEventListener("click", () => {
    const near = nearestLocation();
    if (near) use(near[0]);
  });
}

// ---- frame loop ----------------------------------------------------------------------

function keyDirection() {
  let dx = 0;
  let dy = 0;
  if (keys.has("w") || keys.has("arrowup")) { dx--; dy--; }
  if (keys.has("s") || keys.has("arrowdown")) { dx++; dy++; }
  if (keys.has("a") || keys.has("arrowleft")) { dx--; dy++; }
  if (keys.has("d") || keys.has("arrowright")) { dx++; dy--; }
  return { dx, dy };
}

function stopWalking() {
  route = [];
  pendingUse = null;
  scene.walking = false;
  if (wasWalking) savePlayer();
  wasWalking = false;
}

function walk(dt) {
  if (scene.preview || inputBlocked()) return stopWalking();
  let { dx, dy } = keyDirection();
  if (!dx && !dy && route.length) {
    let distance = Math.hypot(route[0].x - scene.player.x, route[0].y - scene.player.y);
    while (route.length && distance < 0.15) {
      route.shift();
      if (route.length) distance = Math.hypot(route[0].x - scene.player.x, route[0].y - scene.player.y);
    }
    if (route.length) {
      dx = (route[0].x - scene.player.x) / distance;
      dy = (route[0].y - scene.player.y) / distance;
    }
  }
  scene.walking = Boolean(dx || dy);
  if (scene.walking) {
    const length = Math.hypot(dx, dy);
    dx /= length;
    dy /= length;
    scene.facing = { x: dx, y: dy };
    const next = route[0];
    const before = next ? Math.hypot(next.x - scene.player.x, next.y - scene.player.y) : 0;
    const moved = resolveMovement(
      scene.player,
      { x: dx * WALK_SPEED * dt, y: dy * WALK_SPEED * dt },
      activeZone(),
      world.colliders[scene.zoneId],
      PLAYER_RADIUS,
    );
    scene.player = { x: moved.x, y: moved.y };
    if (next) {
      // if something still blocks the way, give up instead of walking on the spot
      const gained = before - Math.hypot(next.x - scene.player.x, next.y - scene.player.y);
      stuckFor = gained > WALK_SPEED * dt * 0.2 ? 0 : stuckFor + dt;
      if (stuckFor > 0.5) {
        route = [];
        pendingUse = null;
      }
    }
  }
  if (pendingUse && inReach(world.locations[pendingUse])) use(pendingUse);
  if (wasWalking && !scene.walking) savePlayer();
  wasWalking = scene.walking;
}

function moveCamera(dt) {
  camera.x += (scene.player.x - camera.x) * Math.min(1, dt * 4.8);
  camera.y += (scene.player.y - camera.y) * Math.min(1, dt * 4.8);
  let zoom;
  if (scene.preview) zoom = Math.max(0.42, Math.min(0.7, canvas.clientWidth / 1400));
  else if (!scene.inNova) zoom = Math.max(0.72, Math.min(1.08, canvas.clientWidth / 1080));
  else zoom = Math.max(0.8, Math.min(1.1, canvas.clientWidth / 1100)); // closer inside, and the whole hall still fits
  camera.zoom += (zoom - camera.zoom) * Math.min(1, dt * 3.5);
}

function renderHint() {
  const near = nearestLocation();
  const hidden = !near || scene.preview;
  const hint = $("#interaction-hint");
  if (hint.hidden !== hidden) hint.hidden = hidden;
  const name = $("#interaction-name");
  if (near && name.textContent !== near[1].label) name.textContent = near[1].label;
}

function loop(t) {
  const dt = Math.min((t - lastTime) / 1000 || 0, 0.04);
  lastTime = t;
  scene.time = t;
  walk(dt);
  updateRoof(dt);
  updateWalkers(dt);
  moveCamera(dt);
  renderHint();
  updateClock();
  drawWorld(t);
  requestAnimationFrame(loop);
}

function resize() {
  const rect = canvas.getBoundingClientRect();
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}

// ---- start ---------------------------------------------------------------------------

async function boot() {
  resize();
  wireInput();
  let state;
  try {
    Object.assign(world, await (await fetch("/api/world")).json());
    joinDorm(world);
    state = await (await fetch("/api/state")).json();
  } catch {
    $("#loading").textContent = "Could not load the campus. Start the server with: uv run python app.py";
    return;
  }
  placePlayer(state.player);
  createWalkers();
  initUi(state, { placePlayer });
  $("#loading").hidden = true;
  requestAnimationFrame(loop);
}

boot();
