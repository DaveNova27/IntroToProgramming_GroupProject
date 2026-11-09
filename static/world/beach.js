// The beach front south of the plaza and the Dorm's surroundings (spec nova-zones): the boardwalk, the
// Surf Shop and the Beach Cafe, the sand with loungers, dunes, a volleyball court and a lifeguard tower,
// the shoreline, and the Dorm's bench and door. Everything is drawn in code from the data in
// world.py (BEACH_WAY, SHOPS_OUTDOOR, BEACH, DORM). Nothing moves at random: waves, grass, flags and
// gulls follow the clock, and the lamps and string lights come on as the evening light falls.
// Only for showing: no rule reads any of this, and no label is evaluated.

import { drawCampusBench } from "./campus.js";
import { drawPersonFigure } from "./people.js";
import { drawTree, drawWindFlag, environmentalProfile, lightingProfile } from "./environment.js";
import {
  drawBlock,
  drawFacadeBandX,
  drawFacadeBandY,
  drawGroundSlab,
  drawPlane,
  drawRaisedSlab,
  drawFootprintShadow,
  drawSoftShadow,
  drawSpaceCaption,
  drawWorldLabel,
  mixColor,
} from "./primitives.js";
import { DEPTH, TILE, ctx, depthOf, isoPoint, reducedMotion, roofOf, scene, wingIsOpen, world } from "./scene.js";

const TEAL = "#31545b";
const AQUA = "#64cbc8";
const CORAL = "#ff7458";
const SUN = "#f5c95e";
const TIMBER = ["#c99a62", "#8f6a3f", "#a98050"]; // top, east face, south face
const SAND = "#dec27e";

const dark = (c, a) => mixColor(c, "#000000", a);
const light = (c, a) => mixColor(c, "#ffffff", a);

// how dark it is, 0 (day) to 1 (dusk): the lamps and string lights use it
const night = () => Math.max(0, Math.min(1, (lightingProfile(scene.clock).progress - 0.55) / 0.35));
const clock = (t) => (reducedMotion ? 0 : t);

function line(a, b, color, width = 1, alpha = 1) {
  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.strokeStyle = color;
  ctx.lineWidth = width;
  ctx.lineCap = "round";
  ctx.beginPath();
  ctx.moveTo(a.x, a.y);
  ctx.lineTo(b.x, b.y);
  ctx.stroke();
  ctx.restore();
}

function dot(p, r, color, alpha = 1) {
  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
}

function oval(p, rx, ry, fill, alpha = 1) {
  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.fillStyle = fill;
  ctx.beginPath();
  ctx.ellipse(p.x, p.y, rx, ry, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
}

// a soft pool of warm light on the ground (only while it is getting dark)
// Lights are queued while the scene is drawn and painted at the end, over the evening shade, so
// that the shade darkens the world but not the lamps (see drawNightGrade and drawNightLights).
const lightQueue = [];
function glow(x, y, z, radius, amount) {
  if (amount < 0.03) return;
  lightQueue.push({ p: isoPoint(x, y, z), radius, amount });
}

// the evening shade: a blue-violet multiply over everything, stronger as the light falls
export function drawNightGrade(w, h) {
  const shade = night() * 0.62;
  if (shade < 0.02) return;
  ctx.save();
  ctx.globalCompositeOperation = "multiply";
  ctx.fillStyle = mixColor("#ffffff", "#5b6a98", shade);
  ctx.fillRect(0, 0, w, h);
  ctx.restore();
}

// the queued lights, added on top of the shade; call inside the same camera transform as the scene
export function drawNightLights() {
  ctx.save();
  ctx.globalCompositeOperation = "lighter";
  for (const { p, radius, amount } of lightQueue) {
    ctx.save();
    ctx.translate(p.x, p.y);
    ctx.scale(1, 0.55); // a pool of light on the ground is an ellipse in this view
    const g = ctx.createRadialGradient(0, 0, 0, 0, 0, radius);
    g.addColorStop(0, `rgba(255,190,100,${0.5 * amount})`);
    g.addColorStop(0.55, `rgba(255,180,90,${0.2 * amount})`);
    g.addColorStop(1, "rgba(255,180,90,0)");
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.arc(0, 0, radius, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }
  ctx.restore();
  lightQueue.length = 0;
}

// a quad flat on the ground
const flat = (x, y, w, h, fill, z = 5, stroke = null) =>
  drawPlane([isoPoint(x, y, z), isoPoint(x + w, y, z), isoPoint(x + w, y + h, z), isoPoint(x, y + h, z)], fill, stroke);

// ---- the ground: sand, shoreline, boardwalk, decks --------------------------------------------

// sand drifting over the paving in front of the beach, with a wavy edge
function drawSandWash() {
  const points = [];
  for (let x = -13.8; x <= 58.2; x += 0.9) points.push(isoPoint(x, 24.7 - 0.38 * Math.sin(x * 0.55) - 0.14 * Math.sin(x * 1.9), 4.6));
  for (let x = 58.2; x >= -13.8; x -= 0.9) points.push(isoPoint(x, 25.3, 4.6));
  drawPlane(points, "rgba(222,194,126,.62)", null);
  // drifts of sand on the paving, more and bigger towards the beach (fixed places, nothing random)
  for (let i = 0; i < 110; i++) {
    const x = -2 + ((i * 17.3) % 46);
    const y = 19.8 + ((i * 5.9) % 5.0);
    if (((i * 7) % 10) / 10 > (y - 19.8) / 5.0 + 0.1) continue;
    const rx = 0.28 + ((i * 3) % 7) * 0.11;
    const pts = [];
    for (let a = 0; a < Math.PI * 2; a += 0.55) {
      const r = rx * (1 + 0.28 * Math.sin(a * 3 + i));
      pts.push(isoPoint(x + Math.cos(a) * r * 1.5, y + Math.sin(a) * r * 0.6, 4.7));
    }
    drawPlane(pts, "rgba(228,206,148,.38)", null);
  }
  // a tongue of sand blown through each opening of the low wall onto the promenade
  const kerb = world.beach.kerb;
  kerb.segments.slice(0, -1).forEach(([, a], i) => {
    const b = kerb.segments[i + 1][0];
    if (a > 11 && b < 17.5) return; // the beach way is there
    const mid = (a + b) / 2;
    const tip = 22.7 + ((Math.round(a * 10) * 7) % 5) * 0.18;
    const pts = [];
    for (let f = 0; f <= 1.001; f += 0.1) pts.push(isoPoint(a + 0.1 - 0.5 * Math.sin(f * 3) * 0.3 + (mid - a) * f * 0.8 + 0.2 * Math.sin(f * 9), 25.4 - (25.4 - tip) * f, 4.75));
    for (let f = 1; f >= -0.001; f -= 0.1) pts.push(isoPoint(b - 0.1 + 0.5 * Math.sin(f * 3) * 0.3 - (b - mid) * f * 0.8 + 0.2 * Math.sin(f * 8 + 1), 25.4 - (25.4 - tip) * f, 4.75));
    drawPlane(pts, "rgba(228,206,148,.7)", null);
  });
}

// ripples in the sand, a darker wet strip along the water, foam that comes in and goes out
function drawShore(t) {
  for (let j = 0; j < 16; j++) {
    for (let i = 0; i < 34; i++) {
      if ((i * 3 + j * 5) % 4 === 0) continue; // the ripples are not in a grid
      const x = 1.6 + i * 1.18 + (j % 2) * 0.6;
      const y = 25.9 + j * 0.56 + ((i * 7) % 5) * 0.05;
      line(isoPoint(x, y, 4.8), isoPoint(x + 0.55, y + 0.02, 4.8), "#b79b5c", 0.8, 0.28);
      // grains: darker and lighter specks, so the sand is not one flat colour
      const g = isoPoint(x + 0.3 + ((i * 11) % 7) * 0.09, y + 0.28, 4.8);
      dot(g, 0.8, (i + j) % 3 ? "#c4a766" : "#f3e2b0", 0.5);
    }
  }
  const wet = [];
  for (let x = -13.5; x <= 58.5; x += 0.9) wet.push(isoPoint(x, 34.2 + 0.18 * Math.sin(x * 0.6 + clock(t) * 0.0009), 4.7));
  for (let x = 58.5; x >= -13.5; x -= 0.9) wet.push(isoPoint(x, 35.05, 4.7));
  drawPlane(wet, "rgba(120,98,60,.2)", null);
  // damp sand above it, darker the nearer the water
  const damp = [];
  for (let x = -13.5; x <= 58.5; x += 0.9) damp.push(isoPoint(x, 33.2 + 0.25 * Math.sin(x * 0.5 + 1), 4.65));
  for (let x = 58.5; x >= -13.5; x -= 0.9) damp.push(isoPoint(x, 34.3, 4.65));
  drawPlane(damp, "rgba(150,120,70,.1)", null);
  // each wave runs up the sand, leaves a dark wet edge and foam, then slides back
  const swell = 0.5 + 0.5 * Math.sin(clock(t) * 0.00095);
  const wash = [];
  for (let x = -13.5; x <= 58.5; x += 0.6) wash.push(isoPoint(x, 34.98 - (0.25 + 0.55 * swell) * (0.65 + 0.35 * Math.sin(x * 0.8 + clock(t) * 0.0004)), 4.95));
  for (let x = 58.5; x >= -13.5; x -= 0.6) wash.push(isoPoint(x, 35.05, 4.95));
  drawPlane(wash, `rgba(255,255,255,${0.2 + 0.25 * swell})`, null);
  const trail = [];
  for (let x = -13.5; x <= 58.5; x += 0.6) trail.push(isoPoint(x, 34.2 - 0.1 * swell, 4.66));
  for (let x = 58.5; x >= -13.5; x -= 0.6) trail.push(isoPoint(x, 34.98 - (0.25 + 0.55 * swell) * 0.65, 4.66));
  drawPlane(trail, `rgba(110,88,55,${0.1 + 0.12 * (1 - swell)})`, null);
  for (let k = 0; k < 3; k++) {
    ctx.save();
    ctx.strokeStyle = "#ffffff";
    ctx.globalAlpha = 0.72 - k * 0.2;
    ctx.lineWidth = 2.6 - k * 0.7;
    ctx.beginPath();
    for (let x = -13.5; x <= 58.5; x += 0.5) {
      const swell = 0.16 * Math.sin(x * 0.7 + clock(t) * 0.0018 - k * 0.8) + 0.1 * Math.sin(x * 1.9 + clock(t) * 0.0011);
      const p = isoPoint(x, 34.92 - k * 0.2 + swell, 4.9);
      if (x === -13.5) ctx.moveTo(p.x, p.y);
      else ctx.lineTo(p.x, p.y);
    }
    ctx.stroke();
    ctx.restore();
  }
}

// a soft strip of heaped sand along the promenade, and a line of dried seaweed left by the tide
function drawDuneStrip() {
  const strip = [];
  for (let x = 1.2; x <= 41.4; x += 0.8) strip.push(isoPoint(x, 24.55 + 0.22 * Math.sin(x * 0.8) + 0.1 * Math.sin(x * 2.3), 5.2));
  for (let x = 41.4; x >= 1.2; x -= 0.8) strip.push(isoPoint(x, 25.35 + 0.18 * Math.sin(x * 0.6), 5.2));
  drawPlane(strip, "rgba(241,222,168,.7)", null);
  for (let x = 1.6; x <= 41; x += 0.37) {
    const y = 33.35 + 0.35 * Math.sin(x * 0.45) + 0.12 * Math.sin(x * 2.1);
    if ((Math.round(x * 100) % 5) % 2 === 0) continue; // broken: it is not a ruler line
    dot(isoPoint(x, y, 5.1), 0.9, (Math.round(x * 10) % 3) ? "#6f6a45" : "#8a6f43", 0.55);
  }
}

function drawTowel(t) {
  flat(t.x - 0.04, t.y - 0.04, t.w + 0.08, t.h + 0.08, "rgba(90,70,40,.18)", 5.2);
  flat(t.x, t.y, t.w, t.h, t.color, 5.6, "rgba(40,50,50,.25)");
  for (const f of [0.22, 0.42, 0.78]) flat(t.x, t.y + t.h * f, t.w, 0.1, t.stripe, 5.8);
}

function drawBeachDetails() {
  const beach = world.beach;
  drawDuneStrip();
  beach.towels.forEach(drawTowel);
  beach.footprints.forEach(({ x, y, side }) => {
    const p = isoPoint(x + (side ? 0.12 : -0.12), y, 4.9);
    oval(p, 2.6, 1.2, "#a58a52", 0.5);
    oval({ x: p.x + 3.4, y: p.y - 0.3 }, 1.2, 0.7, "#a58a52", 0.4);
  });
  beach.shells.forEach(([x, y], i) => {
    const p = isoPoint(x, y, 5);
    oval(p, 1.8, 1, i % 2 ? "#f4ddd0" : "#f6efe2");
    if (i === 1) {
      // a starfish
      for (let a = 0; a < 5; a++) {
        const ang = (a * Math.PI * 2) / 5;
        line({ x: p.x, y: p.y }, { x: p.x + Math.cos(ang) * 4, y: p.y + Math.sin(ang) * 2 }, "#e0805f", 1.6);
      }
    }
  });
  beach.driftwood.forEach(({ x, y, length }) => {
    flat(x, y, length, 0.14, "#8a7154", 5.6, "rgba(40,28,16,.4)");
    flat(x + 0.2, y + 0.2, length * 0.6, 0.1, "#9d8666", 5.6);
  });
  // the volleyball court: lines on the sand and a ball
  const net = beach.volleyball;
  const court = [net.x1 - 0.8, net.y - 1.6, net.x2 - net.x1 + 1.6, 3.2];
  flat(...court, "rgba(255,255,255,0)", 5.1, "rgba(255,255,255,.65)");
  line(isoPoint(net.x1 - 0.8, net.y, 5.2), isoPoint(net.x2 + 0.8, net.y, 5.2), "rgba(255,255,255,.35)", 1);
}

// the beach way: pale sandstone pavers on the promenade, then a weathered boardwalk behind the low wall
// that the sand drifts over: its edges, its end and a few patches along it
function drawBeachWay() {
  const way = world.beachWay;
  const kerb = world.beach.kerb;
  const start = kerb.y + kerb.h; // where the boards begin
  const end = way.y + way.h;
  // ---- the paved path: a border, two tones of pavers, a seam every few rows
  flat(way.x - 0.14, way.y, way.w + 0.28, start - way.y, "#bdb6a2", 4.7);
  const rows = Math.floor((start - way.y) / 0.75);
  for (let j = 0; j < rows; j++) {
    for (let i = 0; i < 4; i++) {
      const w = way.w / 4;
      flat(way.x + i * w + 0.02, way.y + j * 0.75 + 0.02, w - 0.04, 0.71, (i + j) % 2 ? "#e6dfcd" : "#ddd5c1", 4.9, "rgba(120,110,90,.22)");
    }
  }
  flat(way.x + way.w / 2 - 0.05, way.y, 0.1, start - way.y, "rgba(100,203,200,.35)", 5);
  // ---- the boardwalk: grey, sun-bleached boards on beams, low to the ground
  drawFootprintShadow(way.x + way.w / 2, (start + end) / 2, way.w, end - start, 0.06);
  flat(way.x - 0.12, start, way.w + 0.24, end - start, "#6c5d4b", 4.9);
  const boards = Math.floor((end - start) / 0.4);
  for (let j = 0; j < boards; j++) {
    const y = start + j * 0.4;
    const tone = (j * 5) % 3 === 0 ? "#a99a82" : j % 2 ? "#b8a98f" : "#c4b59a";
    flat(way.x, y, way.w, 0.36, tone, 5.2, "rgba(60,48,34,.35)");
    const cut = way.x + (((j * 37) % 23) / 23) * way.w;
    line(isoPoint(cut, y, 5.4), isoPoint(cut, y + 0.36, 5.4), "rgba(60,48,34,.4)", 0.8);
    if (j % 2 === 0) {
      dot(isoPoint(way.x + 0.2, y + 0.18, 5.5), 0.6, "#5a4a37");
      dot(isoPoint(way.x + way.w - 0.2, y + 0.18, 5.5), 0.6, "#5a4a37");
    }
  }
  flat(way.x + way.w / 2 - 0.3, start, 0.6, end - start, "rgba(255,246,222,.14)", 5.3); // the worn middle
  flat(way.x - 0.1, start, 0.1, end - start, "#7b6b57", 5.5);
  flat(way.x + way.w, start, 0.1, end - start, "#7b6b57", 5.5);
  // a threshold plank where the boards meet the paving
  flat(way.x - 0.12, start - 0.02, way.w + 0.24, 0.12, "#8b7a63", 5.5, "rgba(60,48,34,.4)");
  // ---- sand over the edges: a wavy tongue on each side, so the way sits in the sand, not on it
  const sandTone = "rgba(226,201,138,.96)";
  for (const side of [-1, 1]) {
    const edge = side < 0 ? way.x : way.x + way.w;
    const pts = [];
    for (let y = start + 0.1; y <= end + 0.5; y += 0.35) pts.push(isoPoint(edge + side * (0.45 - 0.2 * Math.sin(y * 1.3 + side) - 0.12 * Math.sin(y * 3.1)), y, 5.9));
    for (let y = end + 0.5; y >= start + 0.1; y -= 0.35) pts.push(isoPoint(edge + side * 0.9, y, 5.9));
    drawPlane(pts, sandTone, null);
  }
  // wind-blown patches across the boards and a deep drift over the end
  [[0.2, 2.6, 1.0], [0.9, 5.1, 0.8], [1.8, 7.0, 0.9]].forEach(([dx, dy, size]) => {
    const y = start + dy;
    if (y > end - 1.2) return;
    const cx = way.x + dx + 0.3;
    const pts = [];
    for (let a = 0; a < Math.PI * 2; a += 0.5) pts.push(isoPoint(cx + Math.cos(a) * size * 0.7, y + Math.sin(a) * size * 0.28, 5.7));
    drawPlane(pts, "rgba(226,201,138,.55)", null);
  });
  const drift = [];
  for (let x = way.x - 0.5; x <= way.x + way.w + 0.5; x += 0.25) drift.push(isoPoint(x, end - 1.5 + 0.5 * Math.sin(x * 2.4) + 0.2 * Math.sin(x * 5.7), 5.85));
  for (let x = way.x + way.w + 0.5; x >= way.x - 0.5; x -= 0.25) drift.push(isoPoint(x, end + 0.6, 5.85));
  drawPlane(drift, sandTone, null);
  const fade = [];
  for (let x = way.x - 0.5; x <= way.x + way.w + 0.5; x += 0.25) fade.push(isoPoint(x, end - 2.3 + 0.4 * Math.sin(x * 1.9), 5.8));
  for (let x = way.x + way.w + 0.5; x >= way.x - 0.5; x -= 0.25) fade.push(isoPoint(x, end - 1.4 + 0.4 * Math.sin(x * 2.4), 5.8));
  drawPlane(fade, "rgba(226,201,138,.5)", null);
}

// steps down from the promenade where the low wall is open
function drawKerbSteps() {
  const kerb = world.beach.kerb;
  const edges = [];
  kerb.segments.forEach(([a, b], i) => {
    const next = kerb.segments[i + 1];
    if (next) edges.push([b, next[0]]);
  });
  edges.forEach(([a, b]) => {
    if (a > 11 && b < 17.5) return; // the boardwalk itself is the way down
    for (let s = 0; s < 2; s++) flat(a + 0.1, kerb.y + 0.1 + s * 0.28, b - a - 0.2, 0.3, ["#e7e2d6", "#d6d1c4"][s], 5.6 - s * 0.5, "rgba(70,70,60,.3)");
  });
}

function drawDeck(x, y, w, h, base) {
  drawGroundSlab(x - 0.1, y - 0.1, w + 0.2, h + 0.2, "#8b6645", 5);
  const rows = Math.floor(h / 0.36);
  for (let j = 0; j < rows; j++) flat(x, y + j * 0.36, w, 0.33, j % 2 ? base : light(base, 0.1), 5.4, "rgba(70,45,22,.3)");
}

// where the Dorm stands, read from its data so that the drawing follows the walls and the door
function dormSpot() {
  const part = world.dorm.parts[0];
  const door = world.dorm.entrances[0];
  return { part, door, front: part.y + part.h, east: part.x + part.w };
}

function drawDormGround() {
  const { part, door, front } = dormSpot();
  // the way from the door: a pale stone threshold with a step, a welcome mat, and flagstones to the plaza
  drawBlock(door.x - 0.2, front, door.width + 0.4, 1.5, 3.5, "#ece6d6", "#bdb59f", "#d4ccb8");
  drawBlock(door.x + 0.1, front, door.width - 0.2, 1.2, 5.5, "#f3eee0", "#c6bfa9", "#ddd6c2");
  flat(door.x + 0.25, front + 0.15, door.width - 0.5, 0.4, "#3b5d65", 6.0);
  for (let i = 0; i < 5; i++) flat(door.x + 0.2 + (i % 2) * 0.4, front + 1.7 + i * 0.55, 1.3, 0.4, "#e7e2d6", 4.8, "rgba(70,70,60,.25)");
  // a strip of grass and flowers between the Dorm and the Hub
  drawGroundSlab(part.x - 1.4, part.y + 0.2, 1.3, 5.9, "#83a774", 3.4);
  for (let i = 0; i < 7; i++) dot(isoPoint(part.x - 1.0 + (i % 2) * 0.6, part.y + 0.8 + i * 0.75, 5), 1.5, [SUN, CORAL, "#ffffff"][i % 3]);
}

export function drawBeachGround(t) {
  drawSandWash();
  drawShore(t);
  drawBeachDetails();
  drawBeachWay();
  for (const shop of world.outdoorShops) {
    const base = shop.id === "surf-shop" ? "#b98b59" : "#c9a878";
    drawDeck(shop.x, shop.y, shop.w, shop.h, base);
    drawFootprintShadow(shop.x + shop.w / 2, shop.y + shop.h / 2, shop.w, shop.h, 0.1);
  }
  drawKerbSteps();
  world.beach.rockShelves.forEach(drawRockShelf);
  drawDormGround();
  drawSpaceCaption(18.4, 34.5, "Beach", "#8b6645");
}

// ---- things that stand ----------------------------------------------------------------------------

function drawLamp(x, y, amount) {
  const base = isoPoint(x, y, 5);
  const top = isoPoint(x, y, 62);
  line(base, top, "#31545b", 2.4);
  oval({ x: base.x, y: base.y + 0.5 }, 4, 2, "rgba(20,40,46,.45)");
  glow(x, y, 5, 70, amount);
  const head = { x: top.x, y: top.y - 2 };
  oval(head, 5.5, 3, amount > 0.1 ? "#ffe9a8" : "#f1ead2");
  oval({ x: head.x, y: head.y - 2.2 }, 6.6, 3.2, "#31545b");
}

// the arch over the start of the beach way, with its sign
function drawArch(amount) {
  const [a, b] = world.colliders.campus.filter((c) => c.id.startsWith("way-arch"));
  if (!a || !b) return;
  for (const post of [a, b]) {
    line(isoPoint(post.x, post.y, 5), isoPoint(post.x, post.y, 74), "#f4efe6", 5);
    line(isoPoint(post.x + 0.05, post.y, 5), isoPoint(post.x + 0.05, post.y, 74), "#c9c6bd", 2);
  }
  drawRaisedSlab(a.x - 0.2, a.y - 0.14, b.x - a.x + 0.4, 0.3, 80, 7, "#f7f7f4", "#c9cdd0", "#e4e5e2");
  drawFacadeBandY(a.x - 0.1, a.y + 0.17, b.x - a.x + 0.2, 64, 74, "#2a5573", 1);
  const p = isoPoint((a.x + b.x) / 2, a.y + 0.18, 69);
  ctx.save();
  ctx.fillStyle = "#ffffff";
  ctx.textAlign = "center";
  ctx.font = "800 6.5px Menlo, Consolas, monospace";
  ctx.fillText("BEACH WAY", p.x, p.y + 2.2);
  ctx.restore();
  for (const x of [a.x + 0.3, b.x - 0.3]) dot(isoPoint(x, a.y + 0.17, 63), 2.4, amount > 0.1 ? "#ffe9a8" : "#eee2b8");
}

// a striped awning: the roof of a pavilion, a front valance with a scalloped edge
function drawAwning(x, y, w, h, z, stripe, amount) {
  const count = Math.round(w / 0.55);
  const step = w / count;
  for (let i = 0; i < count; i++) {
    flat(x + i * step, y, step, h, i % 2 ? "#fbf7ee" : stripe, z, "rgba(40,50,50,.18)");
  }
  for (let i = 0; i < count; i++) {
    const px = x + i * step;
    drawPlane(
      [isoPoint(px, y + h, z), isoPoint(px + step, y + h, z), isoPoint(px + step, y + h, z - 5), isoPoint(px + step / 2, y + h, z - 8), isoPoint(px, y + h, z - 5)],
      i % 2 ? "#e9e3d4" : dark(stripe, 0.14),
      "rgba(40,50,50,.2)",
    );
  }
  if (amount > 0.05) {
    for (let i = 0; i <= count; i += 2) dot(isoPoint(x + i * step, y + h, z - 7), 1.6, "#ffe9a8", amount);
  }
}

function drawPost(x, y, z = 66) {
  line(isoPoint(x, y, 5), isoPoint(x, y, z), "#f4efe6", 3.4);
  line(isoPoint(x + 0.04, y, 5), isoPoint(x + 0.04, y, z), "#c9c6bd", 1.4);
}

// ---- the two huts: a back wall with things on it, a side wall, a roof over the back strip ------------
// The roof covers only the strip over the counter, so the wall below it stays in view.

const HUT_Z = 90;

function shelf(x0, x1, y, z, color = "#8f6a3f") {
  line(isoPoint(x0, y, z), isoPoint(x1, y, z), color, 2.6);
  line(isoPoint(x0, y, z - 1), isoPoint(x1, y, z - 1), dark(color, 0.3), 1);
  for (const x of [x0 + 0.1, x1 - 0.1]) line(isoPoint(x, y, z), isoPoint(x, y, z - 7), color, 1.6);
}

function drawSurfHut(shop, amount) {
  const { x, y, w } = shop;
  drawBlock(x, y, w, 0.2, HUT_Z, "#dfe9e6", "#6f9f9b", "#8fbcb7");
  const fy = y + 0.2 + 0.012;
  for (let px = x + 0.3; px < x + w - 0.1; px += 0.34) line(isoPoint(px, fy, 6), isoPoint(px, fy, HUT_Z - 2), "rgba(40,80,80,.28)", 0.8);
  // west wall with a shuttered window
  drawBlock(x, y + 0.2, 0.2, 1.2, HUT_Z, "#dfe9e6", "#6f9f9b", "#8fbcb7");
  drawFacadeBandX(x + 0.212, y + 0.5, 0.6, 46, 78, amount > 0.1 ? "#ffe3a0" : "#cfe7e6", 3);
  drawFacadeBandX(x + 0.214, y + 0.38, 0.12, 46, 78, "#2e8b8f", 1);
  drawFacadeBandX(x + 0.214, y + 1.0, 0.12, 46, 78, "#2e8b8f", 1);
  // wetsuits on a rail
  const rail = HUT_Z - 12;
  line(isoPoint(x + 1.7, fy, rail), isoPoint(x + 5.0, fy, rail), "#31545b", 2);
  ["#2f4d5a", "#ff7458", "#64cbc8", "#2f4d5a", "#f5c95e"].forEach((color, i) => {
    const p = isoPoint(x + 2.0 + i * 0.62, fy, rail);
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.moveTo(p.x - 5, p.y);
    ctx.lineTo(p.x + 5, p.y);
    ctx.lineTo(p.x + 6, p.y + 6);
    ctx.lineTo(p.x + 3, p.y + 6);
    ctx.lineTo(p.x + 2, p.y + 22);
    ctx.lineTo(p.x - 2, p.y + 22);
    ctx.lineTo(p.x - 3, p.y + 6);
    ctx.lineTo(p.x - 6, p.y + 6);
    ctx.closePath();
    ctx.fill();
  });
  // a shelf of helmets, wax and sun cream, a porthole, a painted sign
  shelf(x + 0.5, x + 2.4, fy, 50);
  [CORAL, AQUA, SUN].forEach((color, i) => oval(isoPoint(x + 0.8 + i * 0.5, fy - 0.03, 54), 3.4, 2.6, color));
  ctx.fillStyle = "#f4efe6";
  ctx.fillRect(isoPoint(x + 2.0, fy, 52).x - 2, isoPoint(x + 2.0, fy, 52).y - 4, 4, 4);
  const port = isoPoint(x + w - 0.7, fy, 62);
  dot(port, 8, "#f4efe6");
  dot(port, 6, "#1d4a55");
  dot({ x: port.x - 1.5, y: port.y - 2 }, 1.6, "rgba(255,255,255,.5)");
  if (amount > 0.05) glow(x + w / 2, y + 0.9, 50, 190, amount); // light spilling from under the roof
  const sign = isoPoint(x + w - 2.0, fy, 60);
  roundedRectAt({ x: sign.x, y: sign.y }, 34, 12, "#f4efe6");
  ctx.fillStyle = "#2e8b8f";
  ctx.textAlign = "center";
  ctx.font = "800 5px Menlo, Consolas, monospace";
  ctx.fillText("RENT · LEARN", sign.x, sign.y + 1.8);
}

function drawSurfRoof(shop, amount) {
  const { x, y, w } = shop;
  drawAwning(x - 0.35, y - 0.05, w + 0.7, 1.15, HUT_Z, "#2e8b8f", amount);
  // a surfboard standing on the ridge as the sign
  const c = isoPoint(x + w / 2, y + 0.5, HUT_Z + 4);
  ctx.save();
  ctx.translate(c.x, c.y - 24);
  ctx.rotate(0.06);
  ctx.fillStyle = "#e9e3d4";
  ctx.beginPath();
  ctx.ellipse(0, 0, 10, 28, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = CORAL;
  ctx.beginPath();
  ctx.ellipse(0, 0, 7.4, 25, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(-1.2, -24, 2.4, 48);
  ctx.fillStyle = "#31545b";
  ctx.font = "800 6px Menlo, Consolas, monospace";
  ctx.textAlign = "center";
  ctx.save();
  ctx.rotate(-Math.PI / 2);
  ctx.fillText("SURF", 0, 2.2);
  ctx.restore();
  ctx.restore();
}

function drawCafeHut(shop, amount) {
  const { x, y, w } = shop;
  drawBlock(x, y, w, 0.2, HUT_Z, "#fbf5e8", "#d9a483", "#f3e4cf");
  const fy = y + 0.2 + 0.012;
  drawFacadeBandY(x + 0.05, fy, w - 0.1, 6, 14, "#ff7458", 1);
  drawFacadeBandY(x + 0.05, fy + 0.002, w - 0.1, HUT_Z - 18, HUT_Z - 12, "#ff7458", 1);
  // west wall with a lifebuoy
  drawBlock(x, y + 0.2, 0.2, 1.2, HUT_Z, "#fbf5e8", "#d9a483", "#f3e4cf");
  const ring = isoPoint(x + 0.22, y + 0.8, 62);
  ctx.save();
  ctx.translate(ring.x, ring.y);
  ctx.scale(0.62, 1);
  dot({ x: 0, y: 0 }, 9, CORAL);
  dot({ x: 0, y: 0 }, 4.2, "#fbf5e8");
  for (const a of [0, Math.PI / 2, Math.PI, Math.PI * 1.5]) {
    ctx.fillStyle = "#ffffff";
    ctx.beginPath();
    ctx.arc(0, 0, 9, a - 0.32, a + 0.32);
    ctx.arc(0, 0, 4.2, a + 0.32, a - 0.32, true);
    ctx.closePath();
    ctx.fill();
  }
  ctx.restore();
  // two shelves with bottles and glasses
  shelf(x + 0.45, x + 2.6, fy, 50);
  shelf(x + 0.45, x + 2.6, fy, 66);
  ["#4f9d63", "#c46a52", "#e8c25a", "#4f7fa0", "#4f9d63", "#c46a52"].forEach((color, i) => {
    const p = isoPoint(x + 0.65 + i * 0.34, fy - 0.02, 66);
    ctx.fillStyle = color;
    ctx.fillRect(p.x - 1.4, p.y - 10, 2.8, 10);
    ctx.fillRect(p.x - 0.7, p.y - 13, 1.4, 3);
  });
  for (let i = 0; i < 6; i++) {
    const p = isoPoint(x + 0.7 + i * 0.34, fy - 0.02, 50);
    ctx.fillStyle = "rgba(220,240,240,.8)";
    ctx.fillRect(p.x - 1.6, p.y - 6, 3.2, 6);
  }
  // the chalk menu
  const board = isoPoint(x + 3.35, fy, 60);
  roundedRectAt({ x: board.x, y: board.y - 4 }, 52, 26, "#8f6a3f");
  roundedRectAt({ x: board.x, y: board.y - 4 }, 48, 22, "#22343a");
  ctx.fillStyle = "#e9f2ee";
  ctx.textAlign = "center";
  ctx.font = "800 5px Menlo, Consolas, monospace";
  ctx.fillText("BEACH MENU", board.x, board.y - 11);
  [[AQUA, 38], [SUN, 30], [CORAL, 34]].forEach(([color, len], i) => {
    line({ x: board.x - 18, y: board.y - 4 + i * 4.6 }, { x: board.x - 18 + len * 0.6, y: board.y - 4 + i * 4.6 }, color, 1.3, 0.9);
    line({ x: board.x + 12, y: board.y - 4 + i * 4.6 }, { x: board.x + 18, y: board.y - 4 + i * 4.6 }, "#e9f2ee", 1.1, 0.7);
  });
  if (amount > 0.05) glow(x + w / 2, y + 1.0, 50, 220, amount);
  // woven lamps on cords
  for (const px of [x + 5.0, x + 5.9]) {
    const top = isoPoint(px, fy, HUT_Z - 2);
    const lamp = isoPoint(px, fy, HUT_Z - 20);
    line(top, lamp, "#5a4a37", 1);
    oval(lamp, 6, 5, amount > 0.1 ? "#ffd980" : "#c9a45e");
    for (let k = -2; k <= 2; k++) line({ x: lamp.x + k * 2, y: lamp.y - 4 }, { x: lamp.x + k * 2.2, y: lamp.y + 4 }, "#a9823d", 0.8);
  }
}

// a roof of palm thatch: straw lines, a hanging fringe on the front and the east edge
function drawThatchRoof(x, y, w, h, z) {
  const top = [isoPoint(x, y, z), isoPoint(x + w, y, z), isoPoint(x + w, y + h, z), isoPoint(x, y + h, z)];
  drawPlane(top, "#c9a45e", "rgba(90,60,20,.4)");
  for (let px = x + 0.08; px < x + w; px += 0.14) {
    line(isoPoint(px, y, z), isoPoint(px, y + h, z), Math.round(px * 100) % 3 ? "#b58d45" : "#dcc07a", 1.2, 0.8);
  }
  line(isoPoint(x, y + h / 2, z + 1), isoPoint(x + w, y + h / 2, z + 1), "#8a6a30", 2.2); // the ridge
  drawPlane([isoPoint(x, y + h, z), isoPoint(x + w, y + h, z), isoPoint(x + w, y + h, z - 7), isoPoint(x, y + h, z - 7)], "#a9823d", null);
  for (let px = x; px <= x + w; px += 0.11) {
    const drop = 9 + ((Math.round(px * 100) * 7) % 5) * 1.6;
    line(isoPoint(px, y + h, z - 2), isoPoint(px + 0.02, y + h, z - drop), Math.round(px * 100) % 2 ? "#b58d45" : "#8f6f32", 1.7);
  }
  drawPlane([isoPoint(x + w, y, z), isoPoint(x + w, y + h, z), isoPoint(x + w, y + h, z - 7), isoPoint(x + w, y, z - 7)], "#957133", null);
  for (let py = y; py <= y + h; py += 0.11) {
    const drop = 9 + ((Math.round(py * 100) * 7) % 5) * 1.6;
    line(isoPoint(x + w, py, z - 2), isoPoint(x + w, py, z - drop), Math.round(py * 100) % 2 ? "#a47e3a" : "#7c5f28", 1.7);
  }
}

// ---- the Surf Shop --------------------------------------------------------------------------------

function drawSurfboard(x, y, height, color, lean) {
  const base = isoPoint(x, y, 6);
  const top = isoPoint(x, y + lean, 6 + height);
  line(base, top, dark(color, 0.35), 6.4);
  line(base, top, color, 5);
  line({ x: base.x - 0.4, y: base.y - 2 }, { x: top.x - 0.4, y: top.y + 3 }, "#ffffff", 1.1, 0.85);
}

function drawSurfShop(shop, amount) {
  const counter = world.colliders.campus.find((c) => c.id === "surf-counter");
  // the counter: timber with a teal front, a till and a chalk board
  drawBlock(counter.x, counter.y, counter.width, counter.height, 30, "#e8d9bd", dark("#c9a878", 0.3), "#c9a878");
  drawFacadeBandY(counter.x + 0.06, counter.y + counter.height + 0.012, counter.width - 0.12, 4, 22, "#2e8b8f", 5);
  drawFacadeBandY(counter.x + 0.06, counter.y + counter.height + 0.014, counter.width - 0.12, 22, 25, "#ffffff", 1);
  drawRaisedSlab(counter.x - 0.05, counter.y - 0.04, counter.width + 0.1, counter.height + 0.14, 34, 4, "#f1e7d2", "#a89b82", "#c9bea8");
  const till = isoPoint(counter.x + 0.7, counter.y + 0.4, 44);
  roundedRectAt(till, 8, 5, "#2f4d5a");
  ctx.fillStyle = AQUA;
  ctx.fillRect(till.x - 5, till.y - 3.6, 6, 1.4);
  const board = isoPoint(counter.x + 2.4, counter.y + counter.height + 0.02, 52);
  roundedRectAt({ x: board.x, y: board.y - 5 }, 24, 14, "#22343a");
  ctx.fillStyle = "#e9f2ee";
  ctx.textAlign = "center";
  ctx.font = "800 4.4px Menlo, Consolas, monospace";
  ctx.fillText("BOARDS", board.x, board.y - 6.5);
  ctx.fillText("LESSONS", board.x, board.y - 1);
  // the rack with boards leaning on it, and a rail with wetsuits
  const rack = world.colliders.campus.find((c) => c.id === "surf-rack");
  drawBlock(rack.x, rack.y, rack.width, rack.height, 10, ...TIMBER);
  ["#ff7458", "#64cbc8", "#f5c95e", "#bce65f", "#9a7bc1", "#ffffff"].forEach((color, i) => {
    drawSurfboard(rack.x + 0.2, rack.y + 0.2 + i * 0.27, 44 + (i % 3) * 5, color, -0.25);
  });
  drawSoftShadow(counter.x + 1.8, counter.y + 1.3, 60, 22, 0.1);
}

function roundedRectAt(p, w, h, fill) {
  ctx.fillStyle = fill;
  ctx.beginPath();
  ctx.roundRect(p.x - w / 2, p.y - h / 2, w, h, 2);
  ctx.fill();
}

// ---- the Beach Cafe -----------------------------------------------------------------------------

function drawParasol(x, y, color) {
  line(isoPoint(x, y, 5), isoPoint(x, y, 60), "#e6dfd0", 2);
  const top = isoPoint(x, y, 62);
  ctx.save();
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.moveTo(top.x - 22, top.y + 8);
  ctx.quadraticCurveTo(top.x, top.y - 14, top.x + 22, top.y + 8);
  ctx.lineTo(top.x + 22, top.y + 9);
  ctx.quadraticCurveTo(top.x, top.y + 4, top.x - 22, top.y + 9);
  ctx.closePath();
  ctx.fill();
  ctx.strokeStyle = "rgba(255,255,255,.7)";
  ctx.lineWidth = 1.2;
  for (const dx of [-11, 0, 11]) {
    ctx.beginPath();
    ctx.moveTo(top.x, top.y - 6);
    ctx.lineTo(top.x + dx * 1.9, top.y + 8);
    ctx.stroke();
  }
  ctx.restore();
}

function drawBeachTable(x, y, index) {
  const top = isoPoint(x, y, 24);
  line(isoPoint(x, y, 5), top, "#e6dfd0", 2.6);
  oval({ x: top.x, y: top.y }, 11, 5.5, "#f4efe6");
  oval({ x: top.x, y: top.y - 0.6 }, 9.6, 4.6, index % 2 ? "#ffe3d8" : "#d9f1ee");
  for (const [dx, dy] of [[-0.62, 0.35], [0.62, 0.35]]) {
    const c = isoPoint(x + dx, y + dy, 12);
    line(isoPoint(x + dx, y + dy, 5), c, "#31545b", 2);
    oval(c, 5.2, 2.6, index % 2 ? AQUA : CORAL);
  }
  oval(isoPoint(x + 0.12, y + 0.08, 25.4), 2, 1, "#ffffff"); // a glass
  dot(isoPoint(x - 0.18, y, 26), 1.4, SUN);
}

function drawBeachCafe(shop, t, amount) {
  const bar = world.colliders.campus.find((c) => c.id === "cafe-bar");
  drawBlock(bar.x, bar.y, bar.width, bar.height, 32, "#f6efe0", dark("#ff7458", 0.28), "#ff7458");
  ctx.strokeStyle = "rgba(120,50,30,.4)";
  ctx.lineWidth = 1;
  for (let px = bar.x + 0.12; px < bar.x + bar.width; px += 0.22) {
    line(isoPoint(px, bar.y + bar.height + 0.012, 4), isoPoint(px, bar.y + bar.height + 0.012, 28), "rgba(120,50,30,.38)", 1);
  }
  drawRaisedSlab(bar.x - 0.05, bar.y - 0.04, bar.width + 0.1, bar.height + 0.16, 36, 4, "#fbf6ea", "#b9b09a", "#d6cfbd");
  // bottles and glasses on the bar, the espresso machine, a speaker
  ["#4f9d63", "#c46a52", "#4f7fa0", "#e8c25a", "#4f9d63"].forEach((color, i) => {
    const p = isoPoint(bar.x + 0.5 + i * 0.28, bar.y + 0.28, 36);
    ctx.fillStyle = color;
    ctx.fillRect(p.x - 1.4, p.y - 9, 2.8, 9);
    ctx.fillRect(p.x - 0.7, p.y - 12, 1.4, 3);
  });
  for (const px of [bar.x + 2.4, bar.x + 3.1]) oval(isoPoint(px, bar.y + 0.4, 38), 2, 1, "rgba(255,255,255,.85)");
  const speaker = isoPoint(bar.x + bar.width - 0.5, bar.y + 0.4, 36);
  roundedRectAt({ x: speaker.x, y: speaker.y - 6 }, 8, 12, "#22343a");
  dot({ x: speaker.x, y: speaker.y - 4 }, 1.8, "#8aa6ad");
  dot({ x: speaker.x, y: speaker.y - 9 }, 1, "#8aa6ad");
  // the cooler
  const cooler = world.colliders.campus.find((c) => c.id === "cafe-cooler");
  drawBlock(cooler.x, cooler.y, cooler.width, cooler.height, 16, "#e9f4f2", dark("#64cbc8", 0.3), "#64cbc8");
  drawRaisedSlab(cooler.x - 0.02, cooler.y - 0.02, cooler.width + 0.04, cooler.height + 0.04, 19, 3, "#ffffff", "#b9c8c6", "#d4e0de");
  // stools in front of the bar
  for (const x of [26.4, 27.2, 29.2, 30.0]) {
    const p = isoPoint(x, 27.2, 16);
    line(isoPoint(x, 27.2, 5), p, "#31545b", 2);
    oval(p, 5, 2.5, CORAL);
  }
  drawSoftShadow(bar.x + 2.6, bar.y + 1.2, 110, 26, 0.1);
}

// string lights between the posts: a drooping wire with bulbs that glow in the evening
function drawStringLights(t, amount) {
  const posts = world.colliders.campus.filter((c) => c.id.startsWith("cafe-post"));
  const wire = (a, b) => {
    const count = 11;
    ctx.save();
    ctx.strokeStyle = "rgba(30,40,42,.7)";
    ctx.lineWidth = 0.9;
    ctx.beginPath();
    for (let i = 0; i <= count; i++) {
      const f = i / count;
      const p = isoPoint(a.x + (b.x - a.x) * f, a.y + (b.y - a.y) * f, 80 - 5 * Math.sin(Math.PI * f));
      if (i === 0) ctx.moveTo(p.x, p.y);
      else ctx.lineTo(p.x, p.y);
    }
    ctx.stroke();
    ctx.restore();
    for (let i = 1; i < count; i++) {
      const f = i / count;
      const p = isoPoint(a.x + (b.x - a.x) * f, a.y + (b.y - a.y) * f, 78 - 5 * Math.sin(Math.PI * f));
      const flicker = 1 + 0.12 * Math.sin(clock(t) * 0.004 + i * 1.7);
      dot(p, 1.8, amount > 0.1 ? "#ffe9a8" : "#f1e6b8");
      if (amount > 0.05) dot(p, 4.5 * flicker, "#ffd980", 0.22 * amount);
    }
  };
  if (posts.length === 4) {
    wire(posts[0], posts[1]);
    wire(posts[2], posts[3]);
  }
}

// ---- the sand: loungers, dunes, net, tower ------------------------------------------------------

function drawLounger(l, index) {
  const x = l.x;
  const y = l.y;
  drawBlock(x + 0.05, y + 0.5, 0.7, 1.2, 6, ...TIMBER);
  flat(x, y + 0.45, 0.8, 1.25, l.color, 10, "rgba(40,50,50,.25)");
  drawPlane([isoPoint(x, y + 0.45, 10), isoPoint(x + 0.8, y + 0.45, 10), isoPoint(x + 0.8, y, 24), isoPoint(x, y, 24)], dark(l.color, 0.12), "rgba(40,50,50,.25)");
  flat(x + 0.1, y + 1.0, 0.6, 0.12, "rgba(255,255,255,.7)", 10.2);
  // a rolled towel on some of them
  if (index % 2 === 0) oval(isoPoint(x + 0.4, y + 1.5, 12), 4, 1.8, index % 4 === 0 ? "#ffffff" : "#ffd5c8");
}

function drawDune(d, t, index) {
  const p = isoPoint(d.x, d.y, 5);
  const r = d.r * 40;
  const g = ctx.createRadialGradient(p.x - r * 0.2, p.y - r * 0.4, 2, p.x, p.y, r);
  g.addColorStop(0, "#f0dba0");
  g.addColorStop(1, "#cda965");
  ctx.fillStyle = g;
  ctx.beginPath();
  ctx.ellipse(p.x, p.y - r * 0.3, r, r * 0.62, 0, 0, Math.PI * 2);
  ctx.fill();
  // tufts of grass that sway
  for (let i = 0; i < 6; i++) {
    const bx = p.x + (i - 2.5) * r * 0.28;
    const by = p.y - r * 0.28 + ((i * 5) % 3) * 2;
    const sway = Math.sin(clock(t) * 0.0021 + index * 1.3 + i) * 2.2;
    for (const k of [-1, 0, 1]) {
      line({ x: bx, y: by }, { x: bx + k * 2.2 + sway, y: by - 9 - ((i + k + 3) % 3) * 2 }, i % 2 ? "#6f9a54" : "#8fb166", 1.2);
    }
  }
}

function drawVolleyNet(t) {
  const net = world.beach.volleyball;
  for (const x of [net.x1, net.x2]) {
    line(isoPoint(x, net.y, 5), isoPoint(x, net.y, 50), "#e6dfd0", 2.6);
  }
  ctx.save();
  ctx.strokeStyle = "rgba(255,255,255,.7)";
  ctx.lineWidth = 0.7;
  for (let r = 0; r < 5; r++) {
    ctx.beginPath();
    for (let i = 0; i <= 10; i++) {
      const f = i / 10;
      const p = isoPoint(net.x1 + (net.x2 - net.x1) * f, net.y, 46 - r * 3.4 - 3 * Math.sin(Math.PI * f) - Math.sin(clock(t) * 0.002 + f * 3) * 0.4);
      if (i === 0) ctx.moveTo(p.x, p.y);
      else ctx.lineTo(p.x, p.y);
    }
    ctx.stroke();
  }
  for (let i = 1; i < 10; i++) {
    const f = i / 10;
    const x = net.x1 + (net.x2 - net.x1) * f;
    line(isoPoint(x, net.y, 46 - 3 * Math.sin(Math.PI * f)), isoPoint(x, net.y, 32 - 3 * Math.sin(Math.PI * f)), "rgba(255,255,255,.55)", 0.6);
  }
  ctx.restore();
}

// the lifeguard station: a cabin on stilts with a deck, rails and stairs, a lifeguard on watch, a mast
function drawLifeguardTower(t, amount) {
  const tower = world.beach.tower;
  const { x, y, w, h } = tower;
  const deck = 40;
  drawFootprintShadow(x + w / 2, y + h / 2, w, h, 0.14);
  // stilts and bracing
  const posts = [[0.12, 0.12], [w - 0.12, 0.12], [0.12, h - 0.12], [w - 0.12, h - 0.12]];
  for (const [dx, dy] of posts) line(isoPoint(x + dx, y + dy, 5), isoPoint(x + dx, y + dy, deck), "#e9e3d4", 3.4);
  line(isoPoint(x + 0.12, y + h - 0.12, 8), isoPoint(x + w - 0.12, y + h - 0.12, deck - 4), "#c9c2b0", 1.6);
  line(isoPoint(x + w - 0.12, y + h - 0.12, 8), isoPoint(x + 0.12, y + h - 0.12, deck - 4), "#c9c2b0", 1.6);
  line(isoPoint(x + w - 0.12, y + 0.12, 8), isoPoint(x + w - 0.12, y + h - 0.12, deck - 4), "#c9c2b0", 1.6);
  line(isoPoint(x + w - 0.12, y + h - 0.12, 8), isoPoint(x + w - 0.12, y + 0.12, deck - 4), "#c9c2b0", 1.6);
  // stairs on the east side, rising towards the north
  for (let k = 0; k < 7; k++) {
    drawBlock(x + w + 0.02, y + h - 0.35 - k * 0.2, 0.4, 0.2, 6 + k * 5, "#c9a878", "#8a6a43", "#a98050");
  }
  drawRaisedSlab(x + w + 0.02, y + 0.1, 0.4, 0.2, deck, 3, "#c9a878", "#8a6a43", "#a98050");
  // the deck, the cabin on its north half, rails round the open south half
  drawRaisedSlab(x - 0.1, y - 0.1, w + 0.2, h + 0.2, deck, 4, "#d6b98a", "#8a6a43", "#a98050");
  drawBlock(x + 0.1, y + 0.1, w - 0.2, 0.85, deck + 36, "#fbfaf6", "#d5d8d4", "#f1efe8");
  drawFacadeBandY(x + 0.1, y + 0.95 + 0.012, w - 0.2, deck + 4, deck + 12, CORAL, 1);
  drawFacadeBandY(x + 0.22, y + 0.95 + 0.014, w - 0.44, deck + 18, deck + 31, amount > 0.1 ? "#ffe3a0" : "#2a5573", 3);
  drawFacadeBandX(x + w - 0.1 + 0.012, y + 0.2, 0.6, deck + 18, deck + 31, amount > 0.1 ? "#ffe3a0" : "#2a5573", 2);
  const cross = isoPoint(x + 0.55, y + 0.95 + 0.016, deck + 24);
  ctx.fillStyle = "#e24d3f";
  ctx.fillRect(cross.x - 1, cross.y - 4, 2, 8);
  ctx.fillRect(cross.x - 4, cross.y - 1, 8, 2);
  // the lifeguard, sitting at the front with binoculars
  ctx.save();
  ctx.translate(0, -(deck - 4));
  drawPersonFigure(x + w / 2, y + 1.3, t, 9, { color: CORAL, phase: 0.4, facing: { x: 0, y: 1 }, pose: "sit" });
  ctx.restore();
  // front and side rail
  const rail = deck + 14;
  line(isoPoint(x - 0.05, y + h + 0.05, rail), isoPoint(x + w + 0.05, y + h + 0.05, rail), "#e9e3d4", 2);
  line(isoPoint(x - 0.05, y + h + 0.05, rail - 7), isoPoint(x + w + 0.05, y + h + 0.05, rail - 7), "#e9e3d4", 1.2);
  for (const px of [x - 0.05, x + w / 2, x + w + 0.05]) line(isoPoint(px, y + h + 0.05, deck), isoPoint(px, y + h + 0.05, rail), "#e9e3d4", 1.6);
  line(isoPoint(x - 0.05, y + 0.95, rail), isoPoint(x - 0.05, y + h + 0.05, rail), "#e9e3d4", 2);
  // roof, mast, flag, a loudspeaker
  drawRaisedSlab(x - 0.2, y - 0.2, w + 0.4, 1.4, deck + 42, 5, CORAL, dark(CORAL, 0.3), dark(CORAL, 0.15));
  const cx = x + w / 2;
  line(isoPoint(cx, y + 0.5, deck + 42), isoPoint(cx, y + 0.5, deck + 76), "#e9e3d4", 2);
  drawWindFlag(cx, y + 0.5, deck + 74, SUN, t, environmentalProfile(scene.clock, scene.day, t), 0.8);
  roundedRectAt(isoPoint(x + 0.3, y + 1.22, deck + 46), 8, 6, "#31545b");
  if (amount > 0.05) dot(isoPoint(cx, y + 1.25, deck + 40), 3, "#ffe9a8", amount);
}

// the rescue boat: an orange inflatable on the sand with an outboard motor
function drawRescueBoat() {
  const b = world.beach.rescueBoat;
  const c = isoPoint(b.x + b.w / 2, b.y + b.h / 2, 7);
  // half its footprint in pixels: the boat fills its collider (spec map-view)
  const rx = (b.w * TILE) / 2;
  const ry = (b.h * DEPTH) / 2;
  oval({ x: c.x + 2, y: c.y + 6 }, rx, ry, "rgba(60,45,30,.25)");
  ctx.save();
  ctx.translate(c.x, c.y);
  ctx.fillStyle = "#f08a3c";
  ctx.beginPath();
  ctx.ellipse(0, 0, rx, ry * 0.85, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = "#3a4a52";
  ctx.beginPath();
  ctx.ellipse(0, 0, rx * 0.82, ry * 0.55, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = "rgba(255,255,255,.35)";
  ctx.beginPath();
  ctx.ellipse(-4, -ry * 0.6, rx * 0.75, 2, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = "#ffffff";
  ctx.font = "800 6px Menlo, Consolas, monospace";
  ctx.textAlign = "center";
  ctx.fillText("RESCUE", 0, 2);
  ctx.fillStyle = "#31545b";
  ctx.fillRect(-rx - 4, -3, 6, 9); // the motor at the stern
  ctx.restore();
}

// ---- people on the beach (only for the eye: nobody here is a customer) ---------------------------------

const SWIMSUITS = ["#ff7458", "#64cbc8", "#f5c95e", "#9a7bc1", "#bce65f"];

// someone lying on a towel: swimsuit, arms, legs, a head with sunglasses
function drawSunbather(towel, index) {
  const cx = towel.x + towel.w / 2;
  const suit = SWIMSUITS[index % SWIMSUITS.length];
  const skin = ["#d69b73", "#8d5943", "#efbd96"][index % 3];
  flat(cx - 0.22, towel.y + 0.5, 0.44, 0.55, suit, 8, "rgba(40,50,50,.25)"); // body
  flat(cx - 0.2, towel.y + 0.4, 0.4, 0.12, skin, 8); // shoulders
  flat(cx - 0.17, towel.y + 1.05, 0.14, 0.55, skin, 7.6);
  flat(cx + 0.03, towel.y + 1.05, 0.14, 0.55, skin, 7.6);
  flat(cx - 0.36, towel.y + 0.45, 0.12, 0.5, skin, 7.8); // arms
  flat(cx + 0.24, towel.y + 0.45, 0.12, 0.5, skin, 7.8);
  const head = isoPoint(cx, towel.y + 0.26, 9);
  oval(head, 4.6, 3.4, skin);
  oval({ x: head.x, y: head.y - 1.2 }, 4.8, 2.4, ["#3a2a22", "#54362a", "#ad6840"][index % 3]);
  oval({ x: head.x, y: head.y + 0.6 }, 3.2, 0.9, "#22343a");
  // a book or a bottle next to the towel
  if (index % 2 === 0) flat(cx + 0.5, towel.y + 0.3, 0.22, 0.3, "#ff7458", 8, "rgba(40,50,50,.3)");
  else oval(isoPoint(cx + 0.55, towel.y + 0.4, 9), 2.2, 3, "#64cbc8");
}

function drawFireSitter(p, index, t) {
  drawPersonFigure(p[0], p[1], t, 12 + index * 3, {
    color: SWIMSUITS[(index + 2) % SWIMSUITS.length],
    phase: index * 1.9,
    facing: { x: p[2], y: p[3] },
    pose: index === 1 ? "drink" : "sit",
  });
}

// a volleyball player: jumps now and then, arms up
function drawVolleyPlayer(pl, index, t) {
  const hop = Math.max(0, Math.sin(clock(t) * 0.0032 + pl.phase)) ** 2 * 11;
  const net = world.beach.volleyball;
  ctx.save();
  const ground = isoPoint(pl.x, pl.y, 4);
  oval({ x: ground.x, y: ground.y + 2 }, 8 - hop * 0.2, 3, "rgba(40,40,30,.25)");
  ctx.translate(0, -hop);
  drawPersonFigure(pl.x, pl.y, t, 30 + index * 4, {
    color: pl.team ? "#f5c95e" : "#64cbc8",
    phase: pl.phase,
    facing: { x: 0, y: pl.team ? -1 : 1 },
    pose: hop > 2 ? "dance" : "idle",
  });
  ctx.restore();
  return net;
}

// the ball flies over the net between the two teams, in an arc
function drawVolleyBall(t) {
  const [a, b] = [world.beach.players[0], world.beach.players[2]];
  const f = (clock(t) * 0.00045) % 2;
  const up = f < 1;
  const k = up ? f : 2 - f;
  const x = a.x + (b.x - a.x) * k;
  const y = a.y + (b.y - a.y) * k;
  const z = 24 + Math.sin(Math.PI * k) * 46;
  const p = isoPoint(x, y, z);
  oval({ x: isoPoint(x, y, 5).x, y: isoPoint(x, y, 5).y }, 3, 1.2, "rgba(40,40,30,.25)");
  dot(p, 3.2, "#ffffff");
  ctx.strokeStyle = "rgba(49,84,91,.55)";
  ctx.lineWidth = 0.7;
  ctx.beginPath();
  ctx.arc(p.x, p.y, 3.2, 0.4 + k * 3, 2.6 + k * 3);
  ctx.stroke();
}

// a dog that runs up and down the wet sand
function dogAt(t) {
  const d = world.beach.dog;
  const time = clock(t) * 0.00032;
  return {
    x: d.x0 + (d.x1 - d.x0) * (0.5 + 0.5 * Math.sin(time)),
    y: d.y + 0.25 * Math.sin(time * 3.1),
    dir: Math.cos(time) >= 0 ? 1 : -1,
  };
}

function drawDog(t) {
  const { x, y, dir } = dogAt(t);
  const p = isoPoint(x, y, 5);
  const gait = clock(t) * 0.02;
  oval({ x: p.x, y: p.y + 2 }, 8, 2.6, "rgba(40,30,20,.3)");
  ctx.save();
  ctx.translate(p.x, p.y - 5);
  ctx.scale(dir, 1);
  ctx.strokeStyle = "#a96d3a";
  ctx.lineWidth = 1.6;
  ctx.lineCap = "round";
  for (const [lx, ph] of [[-5, 0], [-2, Math.PI], [3, Math.PI * 0.5], [6, Math.PI * 1.5]]) {
    ctx.beginPath();
    ctx.moveTo(lx, 0);
    ctx.lineTo(lx + Math.sin(gait + ph) * 3, 5);
    ctx.stroke();
  }
  oval({ x: 0, y: -1 }, 8, 3.8, "#c68b4e");
  oval({ x: 7.5, y: -4.4 }, 3.6, 3.2, "#c68b4e");
  oval({ x: 10.6, y: -3.6 }, 1.8, 1.2, "#6b4a2a");
  ctx.fillStyle = "#8a5a2c";
  ctx.beginPath();
  ctx.ellipse(6.2, -6.8, 1.3, 2.2, 0.4, 0, Math.PI * 2);
  ctx.fill();
  ctx.beginPath();
  ctx.moveTo(-7, -3);
  ctx.lineTo(-11, -6 + Math.sin(gait * 1.5) * 2);
  ctx.stroke();
  dot({ x: 8.5, y: -5.2 }, 0.6, "#22343a");
  ctx.restore();
}

// a surfer riding along the face of a wave, and spray behind
function drawSurfer(s, index, t) {
  const f = (clock(t) * 0.00006 + s.phase) % 1;
  const sweep = f < 0.5 ? f * 2 : 2 - f * 2;
  const dir = f < 0.5 ? 1 : -1;
  const x = s.x0 + (s.x1 - s.x0) * sweep;
  const y = s.y + 0.3 * Math.sin(clock(t) * 0.0015 + index);
  const p = isoPoint(x, y, 4);
  oval({ x: p.x, y: p.y + 3 }, 20, 6, "rgba(255,255,255,.4)");
  for (let k = 0; k < 6; k++) dot({ x: p.x - dir * (8 + k * 5), y: p.y + 2 + (k % 3) - k * 0.4 }, 1.6, "#ffffff", 0.7 - k * 0.1);
  ctx.save();
  ctx.translate(p.x, p.y);
  ctx.fillStyle = s.color;
  ctx.beginPath();
  ctx.ellipse(0, 0, 16, 3.4, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(-12, -0.7, 24, 1.4);
  ctx.restore();
  // the rider: crouched, arms out
  const lean = Math.sin(clock(t) * 0.004 + index) * 1.4;
  ctx.fillStyle = "#2f4d5a";
  ctx.beginPath();
  ctx.moveTo(p.x - 3, p.y - 1);
  ctx.lineTo(p.x + 3, p.y - 1);
  ctx.lineTo(p.x + 2 + lean, p.y - 13);
  ctx.lineTo(p.x - 2 + lean, p.y - 13);
  ctx.closePath();
  ctx.fill();
  line({ x: p.x + lean, y: p.y - 11 }, { x: p.x - 9 + lean, y: p.y - 15 }, "#d69b73", 1.7);
  line({ x: p.x + lean, y: p.y - 11 }, { x: p.x + 9 + lean, y: p.y - 9 }, "#d69b73", 1.7);
  dot({ x: p.x + lean, y: p.y - 16.5 }, 3.1, "#d69b73");
  oval({ x: p.x + lean, y: p.y - 18 }, 3.2, 1.9, "#211d1c");
}

// someone paddling out on a board
function drawPaddler(pd, index, t) {
  const bob = Math.sin(clock(t) * 0.0018 + pd.phase) * 1.4;
  const x = pd.x + 1.2 * Math.sin(clock(t) * 0.0002 + pd.phase);
  const p = isoPoint(x, pd.y, 4);
  oval({ x: p.x, y: p.y + 3 }, 22, 6, "rgba(255,255,255,.3)");
  ctx.save();
  ctx.translate(p.x, p.y + bob);
  ctx.fillStyle = index ? "#64cbc8" : "#f5c95e";
  ctx.beginPath();
  ctx.ellipse(0, 0, 17, 3.6, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
  const stroke = Math.sin(clock(t) * 0.006 + pd.phase);
  ctx.fillStyle = "#2f4d5a";
  ctx.beginPath();
  ctx.ellipse(p.x - 1, p.y - 3 + bob, 7, 2.8, 0.45, 0, Math.PI * 2);
  ctx.fill();
  line({ x: p.x + 2, y: p.y - 5 + bob }, { x: p.x + 8 + stroke * 4, y: p.y + 1 + bob }, "#d69b73", 1.6);
  dot({ x: p.x + 7, y: p.y - 7 + bob }, 2.8, "#d69b73");
  oval({ x: p.x + 7, y: p.y - 8.4 + bob }, 3, 1.7, "#54362a");
}

// ---- rock shelves with tide pools, and the lighthouse -----------------------------------------------

function drawRockShelf(r, index) {
  const pts = [];
  const steps = 14;
  for (let i = 0; i < steps; i++) {
    const a = (i / steps) * Math.PI * 2;
    const wobble = 1 + 0.16 * Math.sin(a * 3 + index) + 0.08 * Math.sin(a * 7);
    pts.push(isoPoint(r.x + r.w / 2 + Math.cos(a) * r.w * 0.5 * wobble, r.y + r.h / 2 + Math.sin(a) * r.h * 0.5 * wobble, 5.5));
  }
  const rim = pts.map((q) => ({ x: q.x, y: q.y + 4 }));
  drawPlane(rim, "rgba(40,50,50,.35)", null);
  drawPlane(pts, index ? "#8a8479" : "#857f74", "rgba(40,40,36,.4)");
  // darker cracks and a wet, glossy edge
  for (let k = 0; k < 6; k++) {
    const a = isoPoint(r.x + 0.3 + ((k * 0.61) % 1) * (r.w - 0.6), r.y + 0.3 + ((k * 0.37) % 1) * (r.h - 0.6), 5.8);
    line(a, { x: a.x + 9 + k, y: a.y + 2 }, "rgba(40,40,36,.45)", 0.9);
  }
}

function drawTidePools(t) {
  const beach = world.beach;
  beach.pools.forEach(([x, y], i) => {
    const p = isoPoint(x, y, 6);
    oval(p, 9 + (i % 2) * 2, 4.2, "rgba(60,60,54,.5)");
    oval({ x: p.x, y: p.y - 0.4 }, 7.6 + (i % 2) * 2, 3.4, "#5cc0c0");
    oval({ x: p.x - 1.5, y: p.y - 1.2 }, 3.2, 1, "rgba(255,255,255,.5)");
    const ripple = 0.5 + 0.5 * Math.sin(clock(t) * 0.002 + i);
    ctx.strokeStyle = `rgba(255,255,255,${0.2 + ripple * 0.2})`;
    ctx.lineWidth = 0.8;
    ctx.beginPath();
    ctx.ellipse(p.x + 1, p.y, 3 + ripple * 2, 1.4 + ripple, 0, 0, Math.PI * 2);
    ctx.stroke();
  });
  beach.crabs.forEach(([x, y], i) => {
    const sidle = Math.sin(clock(t) * 0.0016 + i * 2) * 3;
    const p = isoPoint(x, y, 7);
    ctx.fillStyle = "#d9503a";
    ctx.beginPath();
    ctx.ellipse(p.x + sidle, p.y - 1, 3, 1.8, 0, 0, Math.PI * 2);
    ctx.fill();
    for (const side of [-1, 1]) {
      line({ x: p.x + sidle + side * 2.5, y: p.y - 1.5 }, { x: p.x + sidle + side * 4.6, y: p.y - 4 }, "#d9503a", 1);
      dot({ x: p.x + sidle + side * 4.8, y: p.y - 4.4 }, 1, "#d9503a");
      line({ x: p.x + sidle + side * 2, y: p.y }, { x: p.x + sidle + side * 4, y: p.y + 1.6 }, "#b03a28", 0.8);
    }
    dot({ x: p.x + sidle - 1, y: p.y - 2.4 }, 0.6, "#22343a");
    dot({ x: p.x + sidle + 1, y: p.y - 2.4 }, 0.6, "#22343a");
  });
}

// a small lighthouse on the east rocks: red and white bands, a gallery, a lantern whose beam turns at dusk
function drawLighthouse(lh, t, amount) {
  const base = isoPoint(lh.x, lh.y, 6);
  oval({ x: base.x + 4, y: base.y + 6 }, 30, 10, "rgba(30,40,40,.3)");
  const height = 92;
  const bands = ["#f4f1e8", "#d9503a", "#f4f1e8", "#d9503a", "#f4f1e8"];
  bands.forEach((color, i) => {
    const z0 = (i / bands.length) * height;
    const z1 = ((i + 1) / bands.length) * height;
    const r0 = 13 - (z0 / height) * 5;
    const r1 = 13 - (z1 / height) * 5;
    const a = { x: base.x, y: base.y - z0 };
    const b = { x: base.x, y: base.y - z1 };
    const g = ctx.createLinearGradient(base.x - r0, 0, base.x + r0, 0);
    g.addColorStop(0, dark(color, 0.12));
    g.addColorStop(0.45, color);
    g.addColorStop(1, dark(color, 0.3));
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.moveTo(a.x - r0, a.y);
    ctx.lineTo(a.x + r0, a.y);
    ctx.lineTo(b.x + r1, b.y);
    ctx.lineTo(b.x - r1, b.y);
    ctx.closePath();
    ctx.fill();
    ctx.beginPath();
    ctx.ellipse(a.x, a.y, r0, r0 * 0.42, 0, 0, Math.PI);
    ctx.fill();
  });
  const top = { x: base.x, y: base.y - height };
  oval({ x: top.x, y: top.y + 1 }, 11.5, 4.6, "#31545b"); // the gallery
  line({ x: top.x - 10, y: top.y - 4 }, { x: top.x + 10, y: top.y - 4 }, "#31545b", 1.2);
  const lantern = { x: top.x, y: top.y - 12 };
  const lit = amount > 0.1;
  ctx.fillStyle = lit ? "#ffe9a8" : "#bfe0e4";
  ctx.fillRect(lantern.x - 5, lantern.y - 5, 10, 10);
  ctx.strokeStyle = "#31545b";
  ctx.lineWidth = 1;
  ctx.strokeRect(lantern.x - 5, lantern.y - 5, 10, 10);
  ctx.fillStyle = "#31545b";
  ctx.beginPath();
  ctx.moveTo(lantern.x - 8, lantern.y - 5);
  ctx.lineTo(lantern.x, lantern.y - 14);
  ctx.lineTo(lantern.x + 8, lantern.y - 5);
  ctx.closePath();
  ctx.fill();
  const door = { x: base.x, y: base.y - 2 };
  ctx.fillStyle = "#31545b";
  ctx.fillRect(door.x - 2.4, door.y - 9, 4.8, 9);
  if (lit) {
    // the beam: a wedge that turns round, soft, twice as bright when it points at the viewer
    const angle = clock(t) * 0.0011;
    for (const side of [0, Math.PI]) {
      const a = angle + side;
      const reach = 170 + 40 * Math.cos(a);
      const spread = 0.12;
      const g = ctx.createRadialGradient(lantern.x, lantern.y, 4, lantern.x, lantern.y, reach);
      g.addColorStop(0, `rgba(255,236,170,${0.5 * amount})`);
      g.addColorStop(1, "rgba(255,236,170,0)");
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.moveTo(lantern.x, lantern.y);
      ctx.lineTo(lantern.x + Math.cos(a - spread) * reach, lantern.y + Math.sin(a - spread) * reach * 0.42);
      ctx.lineTo(lantern.x + Math.cos(a + spread) * reach, lantern.y + Math.sin(a + spread) * reach * 0.42);
      ctx.closePath();
      ctx.fill();
    }
    dot(lantern, 14, "#ffe9a8", 0.3 * amount);
  }
}

// ---- the water: buoys, boats, gulls -----------------------------------------------------------------

function drawBuoy(x, y, t, index) {
  const bob = Math.sin(clock(t) * 0.002 + index * 1.4) * 1.6;
  const p = isoPoint(x, y, 2);
  line({ x: p.x, y: p.y + 2 }, { x: p.x + 6, y: p.y + 14 }, "rgba(255,255,255,.3)", 0.8);
  oval({ x: p.x, y: p.y + 2 + bob * 0.2 }, 6, 2.4, "rgba(255,255,255,.35)");
  oval({ x: p.x, y: p.y - 3 + bob }, 3.6, 4.4, index % 2 ? CORAL : "#ffffff");
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(p.x - 3.4, p.y - 4 + bob, 6.8, 1.8);
}

function drawBoat(boat, t, index) {
  const bob = Math.sin(clock(t) * 0.0016 + index * 2.1) * 2;
  const p = isoPoint(boat.x, boat.y, 2);
  oval({ x: p.x, y: p.y + 4 }, 30, 9, "rgba(255,255,255,.28)");
  ctx.save();
  ctx.translate(p.x, p.y + bob);
  ctx.fillStyle = boat.color;
  ctx.beginPath();
  ctx.moveTo(-26, -4);
  ctx.lineTo(24, -6);
  ctx.quadraticCurveTo(22, 5, 8, 6);
  ctx.lineTo(-18, 5);
  ctx.quadraticCurveTo(-24, 3, -26, -4);
  ctx.fill();
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(-24, -5, 46, 2.4);
  ctx.strokeStyle = "#e9e3d4";
  ctx.lineWidth = 1.6;
  ctx.beginPath();
  ctx.moveTo(-4, -5);
  ctx.lineTo(-4, -34);
  ctx.stroke();
  ctx.fillStyle = "#fbf7ee";
  ctx.beginPath();
  ctx.moveTo(-3, -33);
  ctx.lineTo(14, -9);
  ctx.lineTo(-3, -9);
  ctx.closePath();
  ctx.fill();
  ctx.restore();
}

function drawGull(g, t) {
  const time = clock(t) * 0.00042 + g.phase;
  const x = g.x + 6 * Math.sin(time);
  const y = g.y + 1.6 * Math.cos(time * 1.3);
  const p = isoPoint(x, y, 92 + 6 * Math.sin(time * 5));
  const flap = reducedMotion ? 0 : Math.sin(clock(t) * 0.009 + g.phase * 3) * 3.2;
  oval({ x: isoPoint(x, y, 5).x, y: isoPoint(x, y, 5).y }, 5, 1.8, "rgba(20,40,46,.12)");
  ctx.save();
  ctx.strokeStyle = "#f8f8f4";
  ctx.lineWidth = 1.7;
  ctx.lineCap = "round";
  ctx.beginPath();
  ctx.moveTo(p.x - 7, p.y - flap);
  ctx.quadraticCurveTo(p.x - 3, p.y - 2.5 - flap, p.x, p.y);
  ctx.quadraticCurveTo(p.x + 3, p.y - 2.5 - flap, p.x + 7, p.y - flap);
  ctx.stroke();
  ctx.restore();
}

// ---- the Dorm's front -----------------------------------------------------------------------------

function drawMailbox() {
  const { part, front } = dormSpot();
  const p = isoPoint(part.x + 0.2, front + 0.25, 5);
  line(p, { x: p.x, y: p.y - 15 }, "#31545b", 2);
  roundedRectAt({ x: p.x, y: p.y - 19 }, 9, 7, "#ff7458");
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(p.x - 2.5, p.y - 20.5, 5, 1.2);
}

// ---- the low wall and the promenade -----------------------------------------------------------------

// the wall between the promenade and the dunes: pale concrete, a cap, a shadow on the sand, a lamp at each end
function drawKerbSegment(x0, x1) {
  const kerb = world.beach.kerb;
  drawSoftShadow((x0 + x1) / 2, kerb.y + kerb.h + 0.35, (x1 - x0) * 22, 14, 0.12);
  drawRaisedSlab(x0, kerb.y, x1 - x0, kerb.h, 10, 4, "#ebe1c8", "#b4a98c", "#d3c8ab");
  drawRaisedSlab(x0 - 0.03, kerb.y - 0.03, x1 - x0 + 0.06, kerb.h + 0.06, 12, 3, "#f6eed9", "#cdc3a6", "#e3d9bd");
  // sand piled against its foot, on both sides
  for (let x = x0; x < x1 - 0.05; x += 0.5) {
    const lift = 0.1 + 0.07 * Math.sin(x * 4.1);
    drawPlane([isoPoint(x, kerb.y + kerb.h, 5.2), isoPoint(x + 0.55, kerb.y + kerb.h, 5.2), isoPoint(x + 0.5, kerb.y + kerb.h + 0.3 + lift, 5.2), isoPoint(x + 0.05, kerb.y + kerb.h + 0.28, 5.2)], "rgba(228,206,148,.9)", null);
    drawPlane([isoPoint(x, kerb.y, 5.2), isoPoint(x + 0.55, kerb.y, 5.2), isoPoint(x + 0.5, kerb.y - 0.2 - lift, 5.2), isoPoint(x + 0.05, kerb.y - 0.18, 5.2)], "rgba(228,206,148,.6)", null);
  }
  for (let x = x0 + 0.7; x < x1 - 0.3; x += 1.4) {
    line(isoPoint(x, kerb.y + kerb.h + 0.012, 5), isoPoint(x, kerb.y + kerb.h + 0.012, 10), "rgba(90,80,60,.25)", 0.8);
  }
}

function drawBollard(x, y, amount) {
  drawRaisedSlab(x - 0.09, y - 0.09, 0.18, 0.18, 26, 4, "#31545b", "#1f3a40", "#274a52");
  oval(isoPoint(x, y, 28), 3, 1.4, amount > 0.1 ? "#ffe9a8" : "#e9e3d4");
  glow(x, y, 28, 36, amount);
}

function drawBin(x, y) {
  const p = isoPoint(x, y, 5);
  oval({ x: p.x, y: p.y + 1 }, 7, 2.8, "rgba(20,40,46,.25)");
  ctx.fillStyle = "#4d6c62";
  ctx.beginPath();
  ctx.moveTo(p.x - 6, p.y - 17);
  ctx.lineTo(p.x + 6, p.y - 17);
  ctx.lineTo(p.x + 5, p.y);
  ctx.lineTo(p.x - 5, p.y);
  ctx.closePath();
  ctx.fill();
  oval({ x: p.x, y: p.y - 17 }, 6, 2.2, "#2f4a43");
  ctx.fillStyle = "rgba(255,255,255,.7)";
  ctx.fillRect(p.x - 2, p.y - 11, 4, 3);
}

function drawPlanterBox([x, y, w, h], index) {
  drawRaisedSlab(x, y, w, h, 12, 4, "#e6e1d5", "#8e9690", "#aeb3ad");
  drawRaisedSlab(x + 0.08, y + 0.08, w - 0.16, h - 0.16, 14, 2, "#8a6a49", "#6a4f36", "#7a5c3f");
  for (let i = 0; i < Math.round(w / 0.3); i++) {
    const px = isoPoint(x + 0.2 + i * 0.3, y + h / 2 + ((i * 3) % 2) * 0.08, 14);
    const sway = Math.sin(clock(scene.time) * 0.0019 + i + index) * 1.3;
    for (const k of [-1, 1]) line(px, { x: px.x + k * 2 + sway, y: px.y - 9 - ((i + k + 3) % 3) * 2 }, i % 2 ? "#6f9a54" : "#8fb166", 1.2);
    if (i % 3 === 0) dot({ x: px.x + sway, y: px.y - 11 }, 1.6, [CORAL, SUN, "#ffffff"][(i + index) % 3]);
  }
}

function drawFountain(f) {
  const p = isoPoint(f.x, f.y, 5);
  oval({ x: p.x, y: p.y + 1 }, 9, 3.4, "rgba(100,203,200,.45)");
  drawBlock(f.x - 0.12, f.y - 0.12, 0.24, 0.24, 30, "#e7e2d6", "#9aa5a0", "#bcc3be");
  oval(isoPoint(f.x, f.y, 31), 3.4, 1.4, "#31545b");
  line(isoPoint(f.x, f.y, 31), isoPoint(f.x + 0.2, f.y + 0.1, 28), "rgba(100,203,200,.8)", 1);
}

function drawIceCart(c, t, amount) {
  drawFootprintShadow(c.x + c.w / 2, c.y + c.h / 2, c.w, c.h, 0.12);
  for (const dx of [0.2, c.w - 0.2]) {
    const w = isoPoint(c.x + dx, c.y + c.h + 0.02, 7);
    ctx.strokeStyle = "#22343a";
    ctx.lineWidth = 1.6;
    ctx.beginPath();
    ctx.arc(w.x, w.y, 4.6, 0, Math.PI * 2);
    ctx.stroke();
  }
  drawBlock(c.x, c.y, c.w, c.h, 26, "#fbf7ee", dark("#64cbc8", 0.25), "#64cbc8");
  drawFacadeBandY(c.x + 0.06, c.y + c.h + 0.012, c.w - 0.12, 8, 14, "#ffffff", 1);
  drawRaisedSlab(c.x - 0.04, c.y - 0.04, c.w + 0.08, c.h + 0.08, 29, 3, "#ffffff", "#b9c8c6", "#d4e0de");
  [CORAL, SUN, "#c9a0e0"].forEach((color, i) => {
    const sc = isoPoint(c.x + 0.4 + i * 0.3, c.y + 0.4, 30);
    oval(sc, 3, 1.4, "#f4efe6");
    dot({ x: sc.x, y: sc.y - 3 }, 3, color);
  });
  // a striped umbrella on a pole
  const px = c.x + c.w - 0.25;
  line(isoPoint(px, c.y + 0.2, 28), isoPoint(px, c.y + 0.2, 84), "#e6dfd0", 2);
  const top = isoPoint(px - 0.4, c.y + 0.4, 86);
  for (let i = 0; i < 6; i++) {
    ctx.fillStyle = i % 2 ? "#fbf7ee" : CORAL;
    ctx.beginPath();
    ctx.moveTo(top.x - 24 + i * 8, top.y + 8 - Math.abs(i - 2.5) * -1.2);
    ctx.quadraticCurveTo(top.x - 22 + i * 8, top.y - 10, top.x - 16 + i * 8, top.y + 8);
    ctx.lineTo(top.x - 24 + i * 8, top.y + 8);
    ctx.fill();
  }
  const m = isoPoint(c.x + c.w / 2 - 0.2, c.y + c.h + 0.03, 20);
  ctx.fillStyle = "#22343a";
  ctx.font = "800 3.8px Menlo, Consolas, monospace";
  ctx.textAlign = "center";
  ctx.fillText("ICE", m.x, m.y - 2);
  if (amount > 0.1) dot(isoPoint(c.x + 0.3, c.y + 0.3, 84), 2, "#ffe9a8", amount);
}

// ---- the beach's own character: grass, umbrellas, castle, rocks, flags, shower, kites, swimmers -------

// beach grass on the dune ridge: clumps that lean with the wind, a few small yellow flowers
function drawGrassClump(x, y, t, index) {
  const p = isoPoint(x, y, 5);
  oval({ x: p.x, y: p.y + 1 }, 6, 2.2, "rgba(120,100,60,.25)");
  const wind = environmentalProfile(scene.clock, scene.day, t).wind;
  for (let k = -3; k <= 3; k++) {
    const sway = Math.sin(clock(t) * 0.0022 + index * 0.9 + k * 0.5) * (1.4 + wind * 2.4);
    const tall = 10 + ((index * 5 + k * 3 + 9) % 5) * 2.2;
    line({ x: p.x + k * 1.3, y: p.y }, { x: p.x + k * 2.3 + sway, y: p.y - tall }, k % 2 ? "#7fa357" : "#a3bf72", 1.3);
  }
  if (index % 4 === 1) dot({ x: p.x + 3, y: p.y - 9 }, 1.5, SUN);
}

function grassClumps() {
  const g = world.beach.grassLine;
  const out = [];
  let i = 0;
  for (let x = g.from; x <= g.to; x += 0.62) {
    i += 1;
    if (g.gaps.some(([a, b]) => x > a && x < b)) continue;
    out.push({ x: x + ((i * 7) % 3) * 0.08, y: g.y + 0.25 * Math.sin(x * 0.8) + ((i * 5) % 3) * 0.09, index: i });
  }
  return out;
}

function drawStandingUmbrella(u) {
  const base = isoPoint(u.x, u.y, 5);
  oval({ x: base.x + 14, y: base.y + 5 }, 30, 10, "rgba(20,40,46,.14)");
  drawParasol(u.x, u.y, u.color);
}

function drawSandcastle(c) {
  const tone = ["#e6cc8c", "#b99a58", "#cfb270"];
  oval(isoPoint(c.x + 0.4, c.y + 0.4, 5), 22, 8, "rgba(90,70,40,.18)");
  drawBlock(c.x - 0.45, c.y - 0.45, 0.9, 0.9, 8, ...tone);
  for (const [dx, dy] of [[-0.5, -0.5], [0.26, -0.5], [-0.5, 0.26], [0.26, 0.26]]) {
    drawBlock(c.x + dx, c.y + dy, 0.24, 0.24, 20, ...tone);
    drawBlock(c.x + dx + 0.05, c.y + dy + 0.05, 0.14, 0.14, 25, ...tone);
  }
  drawBlock(c.x - 0.2, c.y - 0.2, 0.4, 0.4, 26, ...tone);
  const top = isoPoint(c.x, c.y, 26);
  line(top, { x: top.x, y: top.y - 14 }, "#8a6f43", 1.2);
  ctx.fillStyle = CORAL;
  ctx.beginPath();
  ctx.moveTo(top.x, top.y - 14);
  ctx.lineTo(top.x + 6, top.y - 11.5);
  ctx.lineTo(top.x, top.y - 9);
  ctx.closePath();
  ctx.fill();
  // a bucket and a spade next to it
  const b = isoPoint(c.x + 0.95, c.y + 0.1, 5);
  ctx.fillStyle = AQUA;
  ctx.beginPath();
  ctx.moveTo(b.x - 4, b.y - 8);
  ctx.lineTo(b.x + 4, b.y - 8);
  ctx.lineTo(b.x + 3, b.y);
  ctx.lineTo(b.x - 3, b.y);
  ctx.closePath();
  ctx.fill();
  oval({ x: b.x, y: b.y - 8 }, 4, 1.4, "#3aa8a4");
  line({ x: b.x + 7, y: b.y - 1 }, { x: b.x + 12, y: b.y - 9 }, SUN, 1.6);
}

// a rock in the wash of the waves, with foam that pulses round it
function drawRock(r, t, index) {
  const p = isoPoint(r.x, r.y, 5);
  const s = r.r * 42;
  const pulse = 0.5 + 0.5 * Math.sin(clock(t) * 0.0021 + index * 1.7);
  oval({ x: p.x, y: p.y + 2 }, s * 1.45 + pulse * 3, s * 0.72 + pulse * 1.2, "rgba(255,255,255,.55)", 0.5 + 0.2 * pulse);
  oval({ x: p.x, y: p.y + 1 }, s * 1.15, s * 0.55, "#4d5658");
  const g = ctx.createRadialGradient(p.x - s * 0.3, p.y - s * 0.8, 1, p.x, p.y - s * 0.3, s * 1.2);
  g.addColorStop(0, "#9a9a90");
  g.addColorStop(1, "#5d6462");
  ctx.fillStyle = g;
  ctx.beginPath();
  ctx.ellipse(p.x, p.y - s * 0.3, s, s * 0.82, 0, 0, Math.PI * 2);
  ctx.fill();
  oval({ x: p.x - s * 0.3, y: p.y - s * 0.62 }, s * 0.32, s * 0.2, "rgba(255,255,255,.28)");
  ctx.fillStyle = "rgba(60,90,70,.55)"; // green weed on the wet side
  ctx.beginPath();
  ctx.ellipse(p.x + s * 0.2, p.y + s * 0.12, s * 0.7, s * 0.2, 0, 0, Math.PI);
  ctx.fill();
}

// the red and yellow flags next to the lifeguard tower
function drawBeachFlag(f, t) {
  line(isoPoint(f.x, f.y, 5), isoPoint(f.x, f.y, 54), "#e9e3d4", 2);
  drawWindFlag(f.x, f.y, 52, f.color, t, environmentalProfile(scene.clock, scene.day, t), 0.6);
}

function drawShower(sh) {
  const base = isoPoint(sh.x, sh.y, 5);
  oval({ x: base.x, y: base.y + 1 }, 10, 4, "rgba(90,110,120,.3)");
  oval({ x: base.x, y: base.y + 1 }, 6, 2.4, "rgba(100,203,200,.5)"); // a puddle
  line(base, isoPoint(sh.x, sh.y, 64), "#8aa6ad", 2.4);
  line(isoPoint(sh.x, sh.y, 64), isoPoint(sh.x - 0.2, sh.y, 68), "#8aa6ad", 2.4);
  const head = isoPoint(sh.x - 0.3, sh.y, 66);
  oval(head, 4.4, 1.8, "#31545b");
  line({ x: head.x - 2, y: head.y + 2 }, { x: head.x - 2.6, y: head.y + 9 }, "rgba(100,203,200,.55)", 0.8);
  line({ x: head.x + 2, y: head.y + 2 }, { x: head.x + 2.6, y: head.y + 9 }, "rgba(100,203,200,.55)", 0.8);
  line(isoPoint(sh.x, sh.y, 40), isoPoint(sh.x + 0.15, sh.y, 40), "#31545b", 3);
}

// a kite, flying on a string from the sand
function drawKite(k, t) {
  const time = clock(t) * 0.0009 + k.phase;
  const anchor = isoPoint(k.x, k.y, 8);
  const p = isoPoint(k.x + 1.9 + 0.5 * Math.sin(time), k.y - 2.6 + 0.4 * Math.cos(time * 1.3), 132 + 9 * Math.sin(time * 1.4));
  const tilt = 0.25 * Math.sin(time * 1.9);
  ctx.save();
  ctx.strokeStyle = "rgba(60,60,60,.55)";
  ctx.lineWidth = 0.7;
  ctx.beginPath();
  ctx.moveTo(anchor.x, anchor.y);
  ctx.quadraticCurveTo((anchor.x + p.x) / 2 - 8, (anchor.y + p.y) / 2 + 14, p.x, p.y + 8);
  ctx.stroke();
  ctx.translate(p.x, p.y);
  ctx.rotate(tilt);
  ctx.fillStyle = k.color;
  ctx.beginPath();
  ctx.moveTo(0, -11);
  ctx.lineTo(8, -1);
  ctx.lineTo(0, 10);
  ctx.lineTo(-8, -1);
  ctx.closePath();
  ctx.fill();
  ctx.fillStyle = "rgba(255,255,255,.75)";
  ctx.beginPath();
  ctx.moveTo(0, -11);
  ctx.lineTo(8, -1);
  ctx.lineTo(0, -1);
  ctx.closePath();
  ctx.fill();
  ctx.strokeStyle = SUN;
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  ctx.moveTo(0, 10);
  for (let i = 1; i <= 5; i++) ctx.lineTo(Math.sin(time * 3 + i) * 3.2, 10 + i * 5);
  ctx.stroke();
  ctx.restore();
}

// a swimmer: head, one arm that strokes, rings in the water
function drawSwimmer(sw, t) {
  const time = clock(t) * 0.0014 + sw.phase;
  const x = sw.x + 0.5 * Math.sin(time * 0.6);
  const p = isoPoint(x, sw.y + 0.2 * Math.sin(time), 2);
  const bob = Math.sin(time * 2) * 1.2;
  oval({ x: p.x, y: p.y + 3 }, 13 + Math.sin(time * 2) * 1.5, 4.4, "rgba(255,255,255,.3)");
  oval({ x: p.x, y: p.y + 1 }, 7, 2.4, "rgba(30,90,110,.25)");
  const stroke = Math.sin(time * 3);
  line({ x: p.x + 2, y: p.y - 2 + bob }, { x: p.x + 8 + stroke * 3, y: p.y - 6 - stroke * 3 + bob }, "#c98a62", 2.2);
  oval({ x: p.x, y: p.y - 3 + bob }, 3.2, 3.4, "#d99a70");
  oval({ x: p.x - 0.4, y: p.y - 4.6 + bob }, 3.3, 2.2, sw.phase > 2 ? "#2f4d5a" : "#7a4b2a");
}

// ---- annexes, signs, bunting, the fire pit -----------------------------------------------------------

// two changing cabins next to the Surf Shop
function drawSurfCabins(a, amount) {
  drawFootprintShadow(a.x + a.w / 2, a.y + a.h / 2, a.w, a.h, 0.12);
  drawBlock(a.x, a.y, a.w, a.h, 66, "#e9eeea", "#5d8f8c", "#8fbcb7");
  drawRaisedSlab(a.x - 0.08, a.y - 0.08, a.w + 0.16, a.h + 0.16, 70, 4, "#2e8b8f", "#1f6568", "#277a7d");
  const fy = a.y + a.h + 0.012;
  [0, 1].forEach((i) => {
    const x0 = a.x + 0.08 + i * 0.56;
    drawFacadeBandY(x0, fy, 0.46, 6, 52, i ? "#ff7458" : "#64cbc8", 1);
    for (let k = 0; k < 4; k++) line(isoPoint(x0 + 0.05, fy + 0.002, 38 + k * 3.4), isoPoint(x0 + 0.41, fy + 0.002, 38 + k * 3.4), "rgba(255,255,255,.4)", 0.8);
    dot(isoPoint(x0 + 0.38, fy + 0.002, 26), 1.3, "#f4efe6");
    const n = isoPoint(x0 + 0.23, fy + 0.002, 58);
    ctx.fillStyle = "#31545b";
    ctx.font = "800 6px Menlo, Consolas, monospace";
    ctx.textAlign = "center";
    ctx.fillText(String(i + 1), n.x, n.y + 2);
  });
  if (amount > 0.1) dot(isoPoint(a.x + a.w / 2, fy, 64), 2.4, "#ffe9a8", amount);
}

// a shipping container turned into the cafe's kitchen, with an ice cream hatch
function drawCafeContainer(a, amount) {
  drawFootprintShadow(a.x + a.w / 2, a.y + a.h / 2, a.w, a.h, 0.12);
  drawBlock(a.x, a.y, a.w, a.h, 56, "#f3ecdc", "#2c7c80", "#3aa0a4");
  const fy = a.y + a.h + 0.012;
  for (let px = a.x + 0.1; px < a.x + a.w - 0.05; px += 0.12) line(isoPoint(px, fy, 6), isoPoint(px, fy, 54), "rgba(20,70,74,.28)", 0.8);
  // the hatch
  drawFacadeBandY(a.x + 0.22, fy + 0.002, 0.95, 24, 46, amount > 0.1 ? "#ffe3a0" : "#fff6e4", 1);
  drawRaisedSlab(a.x + 0.18, fy - 0.1, 1.03, 0.14, 24, 2, "#fbf6ea", "#b9b09a", "#d6cfbd");
  for (let i = 0; i < 4; i++) flat(a.x + 0.16 + i * 0.27, fy, 0.27, 0.34, i % 2 ? "#fbf7ee" : CORAL, 49 - 0, "rgba(40,50,50,.2)");
  [CORAL, SUN, "#c9a0e0"].forEach((color, i) => {
    const sc = isoPoint(a.x + 0.45 + i * 0.28, fy - 0.04, 28);
    dot({ x: sc.x, y: sc.y - 3 }, 2.8, color);
  });
  const n = isoPoint(a.x + 0.7, fy + 0.002, 52);
  ctx.fillStyle = "#31545b";
  ctx.font = "800 4px Menlo, Consolas, monospace";
  ctx.textAlign = "center";
  ctx.fillText("ICE · COFFEE", n.x, n.y - 1);
  // a rolled-up door on the side, a vent on the roof
  drawRaisedSlab(a.x + 1.15, a.y + 0.2, 0.4, 0.5, 60, 4, "#c9c6bd", "#8e9690", "#aeb3ad");
  oval(isoPoint(a.x + 1.35, a.y + 0.45, 62), 3.4, 1.6, "#31545b");
}

function drawChalkSign(sign) {
  const base = isoPoint(sign.x, sign.y, 5);
  oval({ x: base.x, y: base.y + 1 }, 9, 3, "rgba(20,40,46,.25)");
  ctx.fillStyle = "#8f6a3f";
  ctx.beginPath();
  ctx.moveTo(base.x - 9, base.y);
  ctx.lineTo(base.x - 4, base.y - 26);
  ctx.lineTo(base.x + 4, base.y - 26);
  ctx.lineTo(base.x + 9, base.y);
  ctx.closePath();
  ctx.fill();
  ctx.fillStyle = "#22343a";
  ctx.beginPath();
  ctx.moveTo(base.x - 7.4, base.y - 2);
  ctx.lineTo(base.x - 3.3, base.y - 24.4);
  ctx.lineTo(base.x + 3.3, base.y - 24.4);
  ctx.lineTo(base.x + 7.4, base.y - 2);
  ctx.closePath();
  ctx.fill();
  ctx.fillStyle = "#e9f2ee";
  ctx.font = "800 3.8px Menlo, Consolas, monospace";
  ctx.textAlign = "center";
  ctx.fillText(sign.id === "surf-sign" ? "TODAY" : "FRESH", base.x, base.y - 18);
  for (let i = 0; i < 3; i++) line({ x: base.x - 4, y: base.y - 14 + i * 4 }, { x: base.x + 4 - i * 1.5, y: base.y - 14 + i * 4 }, [AQUA, SUN, CORAL][i], 1.1, 0.9);
}

// a line of small flags (and, in the evening, small bulbs between them)
function drawBunting(a, b, z, amount, t, colors) {
  const count = 14;
  const pts = [];
  for (let i = 0; i <= count; i++) {
    const f = i / count;
    pts.push(isoPoint(a.x + (b.x - a.x) * f, a.y + (b.y - a.y) * f, z - 8 * Math.sin(Math.PI * f)));
  }
  ctx.save();
  ctx.strokeStyle = "rgba(60,50,40,.7)";
  ctx.lineWidth = 0.9;
  ctx.beginPath();
  pts.forEach((p, i) => (i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y)));
  ctx.stroke();
  for (let i = 1; i < count; i++) {
    const p = pts[i];
    const flutter = Math.sin(clock(t) * 0.004 + i * 1.3) * 0.8;
    ctx.fillStyle = colors[i % colors.length];
    ctx.beginPath();
    ctx.moveTo(p.x - 3, p.y);
    ctx.lineTo(p.x + 3, p.y);
    ctx.lineTo(p.x + flutter, p.y + 8);
    ctx.closePath();
    ctx.fill();
    if (amount > 0.05) dot({ x: p.x, y: p.y + 2 }, 4, "#ffd980", 0.22 * amount);
  }
  ctx.restore();
}

// the fire pit: stones, logs to sit on, and a fire that burns when it gets dark
function drawFirePit(pit, t, amount) {
  const p = isoPoint(pit.x, pit.y, 5);
  oval({ x: p.x, y: p.y + 2 }, 26, 10, "rgba(60,45,30,.35)");
  for (let i = 0; i < 9; i++) {
    const a = (i / 9) * Math.PI * 2;
    oval({ x: p.x + Math.cos(a) * 17, y: p.y + Math.sin(a) * 8 - 2 }, 5, 3, i % 2 ? "#85847b" : "#6d6e68");
  }
  oval({ x: p.x, y: p.y - 1 }, 14, 6, amount > 0.1 ? "#2a1d14" : "#4a3b2c");
  line({ x: p.x - 9, y: p.y - 2 }, { x: p.x + 8, y: p.y - 6 }, "#5a4128", 3.2);
  line({ x: p.x - 7, y: p.y - 5 }, { x: p.x + 9, y: p.y - 1 }, "#6b4d2e", 3);
  if (amount > 0.12) {
    glow(pit.x, pit.y, 6, 150 + 20 * Math.sin(clock(t) * 0.008), Math.min(1, amount * 1.6));
    for (let k = 0; k < 4; k++) {
      const h = 18 + 7 * Math.sin(clock(t) * 0.011 + k * 2.1) + (k === 1 ? 8 : 0);
      const dx = (k - 1.5) * 4.5;
      ctx.fillStyle = k % 2 ? "#ff9d3c" : "#ff6a2a";
      ctx.beginPath();
      ctx.moveTo(p.x + dx - 5, p.y - 3);
      ctx.quadraticCurveTo(p.x + dx - 2, p.y - h * 0.6, p.x + dx + Math.sin(clock(t) * 0.01 + k) * 2, p.y - h);
      ctx.quadraticCurveTo(p.x + dx + 2, p.y - h * 0.5, p.x + dx + 5, p.y - 3);
      ctx.closePath();
      ctx.fill();
    }
    ctx.fillStyle = "#ffe08a";
    ctx.beginPath();
    ctx.ellipse(p.x, p.y - 7, 3, 7 + 2 * Math.sin(clock(t) * 0.014), 0, 0, Math.PI * 2);
    ctx.fill();
    for (let k = 0; k < 6; k++) {
      const life = ((clock(t) * 0.0006 + k / 6) % 1);
      dot({ x: p.x + Math.sin(k * 3 + life * 6) * 9, y: p.y - 14 - life * 40 }, 1.1, "#ffcf70", 0.8 * (1 - life) * Math.min(1, amount * 2));
    }
  }
}

function drawLog(pit, [dx, dy, w, h]) {
  drawBlock(pit.x + dx, pit.y + dy, w, h, 8, "#a98050", "#6b4d2e", "#8a6a43");
  const e = isoPoint(pit.x + dx + w / 2, pit.y + dy + h, 8);
  oval({ x: e.x, y: e.y }, 0.1, 0.1, "#c9a878");
}

// tufts of grass that have found a crack in the paving, a few steps from the sand
let grassTufts = null; // fixed places, worked out once
function promenadeGrass() {
  if (grassTufts) return grassTufts;
  const out = [];
  for (let i = 0; i < 26; i++) {
    const x = 2 + ((i * 7.3) % 39);
    const y = 21.8 + ((i * 5) % 8) * 0.3;
    if (x > 12.4 && x < 16.4) continue;
    if (x > 18 && x < 23 && y > 21.7) continue;
    out.push({ x, y, index: i + 40 });
  }
  grassTufts = out;
  return out;
}

// ---- the Dorm's front, the edge of the campus, the delivery lorry -----------------------------------

// window boxes with flowers under the Dorm's windows, a white canopy over its door, a balcony on the east side
function drawDormFront(t, amount) {
  const { part, door, front, east } = dormSpot();
  const y = front + 0.02;
  const doorEnd = door.x + door.width;
  // the lamp's light on the ground stays, also while the roof is gone
  if (amount > 0.05) glow(doorEnd - 0.3, front + 0.4, 36, 90, amount);
  // the lamp in the room, seen while its roof is gone: on in the evening, off while the player sleeps
  // (spec day-cycle)
  if (amount > 0.05 && !scene.sleeping && wingIsOpen("dorm")) {
    glow(part.x + part.w / 2, part.y + part.h / 2, 8, 150, amount * 0.9);
  }
  // Seen from the front, the canopy and the flower boxes stand over the first row of the room: they
  // are part of the roof and fade with it, like the Nova's canopy (spec map-view).
  const roof = roofOf("dorm");
  if (roof < 0.02) return;
  ctx.save();
  ctx.globalAlpha = roof;
  // flower boxes
  for (const [x0, x1] of [[part.x + 0.3, door.x - 0.2], [doorEnd + 0.2, east - 0.3]]) {
    drawBlock(x0, y - 0.02, x1 - x0, 0.22, 33, "#f7f7f4", "#c9cdd0", "#e4e5e2");
    for (let x = x0 + 0.12; x < x1; x += 0.2) {
      const p = isoPoint(x, y + 0.1, 33);
      const sway = Math.sin(clock(t) * 0.002 + x) * 0.8;
      line(p, { x: p.x + sway, y: p.y - 6 }, "#6f9a54", 1.2);
      dot({ x: p.x + sway, y: p.y - 7 }, 1.7, [CORAL, SUN, "#ffffff", "#c9a0e0"][Math.round(x * 5) % 4]);
    }
  }
  // the canopy over the door, a thin white slab on two slim columns, like the Nova's
  drawRaisedSlab(door.x - 0.3, front - 0.1, door.width + 0.6, 1.3, 50, 4, "#f7f7f4", "#c9cdd0", "#e4e5e2");
  drawFacadeBandY(door.x - 0.3, front + 1.2 + 0.012, door.width + 0.6, 46, 47.5, "#bce65f", 1);
  for (const x of [door.x - 0.15, doorEnd + 0.15]) {
    drawBlock(x - 0.07, front + 1.03, 0.14, 0.14, 46, "#ffffff", "#c9cdd0", "#e4e5e2");
  }
  // a house number and a lantern by the door
  const sign = isoPoint(door.x + 0.2, front + 0.08, 40);
  roundedRectAt({ x: sign.x, y: sign.y }, 16, 9, "#31545b");
  ctx.fillStyle = "#f4efe6";
  ctx.font = "800 6px Menlo, Consolas, monospace";
  ctx.textAlign = "center";
  ctx.fillText("№ 7", sign.x, sign.y + 2.2);
  const lamp = isoPoint(doorEnd - 0.3, front + 0.1, 38);
  dot(lamp, 3, amount > 0.1 ? "#ffe9a8" : "#eee2b8");
  ctx.restore();
}

// the balcony on the Dorm's east wall: a white ledge, a glass rail, pots
function drawDormBalcony(t) {
  const { part, east: x } = dormSpot();
  const y0 = part.y + 0.9;
  const y1 = y0 + 3.2;
  drawRaisedSlab(x, y0, 0.7, 3.2, 33, 4, "#f7f7f4", "#c9cdd0", "#e4e5e2");
  const rail = 33 + 14;
  drawFacadeBandX(x + 0.7 + 0.01, y0, 3.2, 33, rail, "rgba(160,205,225,.34)", 6); // a glass balustrade
  line(isoPoint(x + 0.7, y0, rail), isoPoint(x + 0.7, y1, rail), "#ffffff", 2);
  line(isoPoint(x + 0.7, y1, rail), isoPoint(x, y1, rail), "#ffffff", 2);
  for (const [dy, color] of [[0.4, CORAL], [1.4, SUN], [2.7, "#ffffff"]]) {
    const y = y0 + dy;
    const p = isoPoint(x + 0.45, y, 36);
    ctx.fillStyle = "#c8795a";
    ctx.fillRect(p.x - 3, p.y - 5, 6, 5);
    for (const dx of [-2, 0, 2]) {
      line({ x: p.x + dx, y: p.y - 5 }, { x: p.x + dx * 1.4 + Math.sin(clock(t) * 0.002 + y) * 0.8, y: p.y - 11 }, "#6f9a54", 1.2);
    }
    dot({ x: p.x, y: p.y - 12 }, 2, color);
  }
}

// the lorry on the delivery lane: a box truck with a ribbed white cargo box and the Mercado stripe,
// a teal cab with windscreen, grille, headlights and mirror, tandem rear wheels and a bumper.
// It stands with its nose to the south, the way it leaves the lane.
function drawDeliveryLorry() {
  const x0 = -0.9, w = 1.5, east = x0 + w;
  const glass = "#cfe7e6";
  drawFootprintShadow(x0 + w / 2, 10.8, w, 4.3, 0.16);
  // chassis rail and cargo box
  drawBlock(x0 + 0.05, 8.75, w - 0.1, 4.2, 12, "#2a3438", "#1d2629", "#242e32");
  drawBlock(x0, 8.7, w, 3.15, 54, "#fbf9f2", "#d6d2c6", "#e8e4d8");
  // (the ribs, stripes and name on the east side of the box are seen edge-on from the front: not drawn)
  // south face of the box above the cab: roof spoiler edge and a vent
  drawFacadeBandY(x0 + 0.15, 11.85 + 0.012, 1.2, 44, 51, "#c9c6bd", 1);
  // cab: roof, windscreen, side window, door
  drawBlock(x0 + 0.04, 11.85, w - 0.08, 1.1, 36, "#2e8b8f", "#1f6568", "#277a7d");
  drawBlock(x0 + 0.04, 12.4, w - 0.08, 0.55, 25, "#35a1a5", "#1f6568", "#277a7d");
  drawFacadeBandY(x0 + 0.14, 12.4 + 0.014, w - 0.28, 26.5, 34.5, glass, 4);
  // grille, headlights, bumper, number plate
  drawFacadeBandY(x0 + 0.34, 12.95 + 0.014, w - 0.68, 12, 22, "#1b2a2e", 5);
  for (const hx of [x0 + 0.17, east - 0.17]) {
    const p = isoPoint(hx, 12.97, 19);
    oval(p, 3.4, 2.6, "#fff3c4");
    oval(p, 1.6, 1.2, "#ffd877");
  }
  drawBlock(x0 - 0.02, 12.93, w + 0.04, 0.2, 10, "#aab6b8", "#6f7e80", "#8c9a9c");
  const plate = isoPoint(x0 + w / 2, 13.14, 6);
  ctx.fillStyle = "#fbf9f2";
  ctx.fillRect(plate.x - 4, plate.y - 3, 8, 3.4);
  // mirror arm and mirror
  const arm = isoPoint(east - 0.02, 12.05, 31);
  line(arm, { x: arm.x + 5, y: arm.y - 1 }, "#22343a", 1.4);
  ctx.fillStyle = "#22343a";
  ctx.fillRect(arm.x + 4, arm.y - 6, 3, 7);
  // the front wheels, seen from the front: the tread under each corner of the cab
  for (const wx of [x0 + 0.12, east - 0.12]) {
    const wp = isoPoint(wx, 12.95, 7);
    oval(wp, 3.4, 7.6, "#151e21");
    oval(wp, 2.2, 6.4, "#22343a");
  }
  // a fuel tank behind the cab
  drawBlock(east - 0.02, 11.5, 0.14, 0.34, 9, "#8e9ca0", "#6a787c", "#7d8b8f");
}

function drawLorryCrew(t) {
  // a driver's mate with a crate and a trolley stacked with boxes at the dock
  drawCrateStack(1.35, 9.6, 2);
  drawPersonFigure(1.75, 10.9, t, 21, { color: "#f5c95e", facing: { x: -1, y: 0 }, pose: "idle" });
  drawCrateStack(1.2, 11.5, 1);
}

function drawCrateStack(x, y, count) {
  for (let i = 0; i < count; i++) {
    const z = 5 + (i + 1) * 9;
    drawBlock(x + i * 0.04, y, 0.55, 0.5, z, i % 2 ? "#e2c898" : "#d8b684", "#a9834f", "#c49a63");
    line(isoPoint(x + i * 0.04 + 0.275, y, z), isoPoint(x + i * 0.04 + 0.275, y + 0.5, z), "rgba(255,255,255,.55)", 1);
  }
}

// a thick low hedge along the east edge of the campus, with flowers in it
function drawHedge(y0, y1) {
  for (let y = y0; y < y1; y += 0.7) {
    drawBlock(41.35, y, 0.7, 0.72, 14 + 2 * Math.sin(y * 1.9), "#6f9a54", "#4e7a3c", "#5f8a48");
    const p = isoPoint(41.7, y + 0.35, 17);
    for (let k = 0; k < 3; k++) {
      dot({ x: p.x + (k - 1) * 4 + Math.sin(y * 3 + k) * 2, y: p.y - k % 2 * 1.5 }, 2.6, ["#83a774", "#5f8a48", "#8fb166"][k]);
    }
    if (Math.round(y * 10) % 3 === 0) dot({ x: p.x + 2, y: p.y - 2 }, 1.2, [CORAL, SUN, "#ffffff"][Math.round(y) % 3]);
  }
}

function drawGardenBed(x, y, index, t) {
  drawBlock(x, y, 2.3, 0.95, 9, "#7a5a3a", "#5a4128", "#94693f");
  drawBlock(x + 0.1, y + 0.1, 2.1, 0.75, 10.5, "#4a3626", "#3a2a1c", "#4a3626");
  for (let i = 0; i < 8; i++) {
    const p = isoPoint(x + 0.25 + i * 0.26, y + 0.5 + ((i * 3) % 2) * 0.12, 11);
    const sway = Math.sin(clock(t) * 0.002 + i + index) * 0.8;
    const crop = index % 3;
    if (crop === 0) { // salad: round green heads
      oval({ x: p.x, y: p.y - 3 }, 3.6, 2.8, i % 2 ? "#8fbf5c" : "#6fa84a");
    } else if (crop === 1) { // tomatoes on canes
      line(p, { x: p.x + sway, y: p.y - 16 }, "#8a6a43", 1);
      oval({ x: p.x + sway, y: p.y - 10 }, 3, 3.6, "#5f9a45");
      dot({ x: p.x + sway + 1.5, y: p.y - 7 }, 1.5, "#e24d3f");
    } else { // flowers
      line(p, { x: p.x + sway, y: p.y - 9 }, "#6f9a54", 1.2);
      dot({ x: p.x + sway, y: p.y - 10 }, 2.4, [SUN, CORAL, "#c9a0e0", "#ffffff"][i % 4]);
    }
  }
}

// a hammock between two palms, with someone in it
function drawHammock(t) {
  const a = { x: 43.4, y: 18.6 };
  const b = { x: 43.4, y: 21.4 };
  const sway = Math.sin(clock(t) * 0.0014) * 0.5;
  ctx.save();
  ctx.strokeStyle = "#c9a45e";
  ctx.lineWidth = 2.4;
  ctx.beginPath();
  for (let i = 0; i <= 12; i++) {
    const f = i / 12;
    const p = isoPoint(a.x + sway * Math.sin(Math.PI * f), a.y + (b.y - a.y) * f, 38 - 14 * Math.sin(Math.PI * f));
    if (i === 0) ctx.moveTo(p.x, p.y);
    else ctx.lineTo(p.x, p.y);
  }
  ctx.stroke();
  ctx.restore();
  const mid = isoPoint(a.x + sway, (a.y + b.y) / 2, 28);
  oval({ x: mid.x - 1, y: mid.y - 3 }, 11, 3.6, "#2f4d5a");
  dot({ x: mid.x - 9, y: mid.y - 6 }, 3.2, "#d99a70");
  oval({ x: mid.x - 9, y: mid.y - 8 }, 3.4, 2, "#54362a");
}

// palms and olive-like trees standing behind the campus edges: only scenery
const EDGE_TREES = [
  ...[5.2, 8.0, 10.9, 13.6, 16.5, 19.3, 22.2].map((y, i) => [43.8 + (i % 2) * 0.9, y + (i % 3) * 0.3, 0.84 + (i % 3) * 0.08]),
  ...[1.6, 4.4, 7.4, 10.2].map((x, i) => [x + (i % 2) * 0.8, 0.7 + (i % 3) * 0.5, 0.86 + (i % 2) * 0.1]),
  ...[9.2, 12.5, 15.8, 19.2, 22.4].map((y, i) => [-3.4 + (i % 2) * 0.8, y, 0.86 + (i % 3) * 0.07]),
];

// ---- everything that stands, sorted with the rest of the scene -------------------------------------

export function beachActors(t) {
  const amount = night();
  const solid = world.colliders.campus;
  const actors = [];
  const add = (depth, draw) => actors.push({ depth, draw });

  for (const c of solid) {
    if (c.id.startsWith("way-lamp")) add(depthOf(c.x, c.y) + 0.05, () => drawLamp(c.x, c.y, amount));
  }
  add(depthOf(14.4, 17.7), () => drawArch(amount));
  add(depthOf(11.9, 31.0), () => drawCampusBench(11.9, 30.5, 1));
  add(depthOf(16.5, 31.0), () => drawCampusBench(16.5, 30.5, 1));

  for (const shop of world.outdoorShops) {
    if (shop.id === "surf-shop") {
      add(depthOf(shop.x, shop.y) + 0.05, () => drawSurfHut(shop, amount));
      add(depthOf(shop.x, shop.y) + 1.0, () => drawSurfShop(shop, amount));
      for (const c of solid.filter((c) => c.id.startsWith("surf-post"))) add(depthOf(c.x, c.y) + 0.05, () => drawPost(c.x, c.y, HUT_Z));
      add(depthOf(shop.x + shop.w, shop.y + 1.3), () => drawSurfRoof(shop, amount));
      add(depthOf(shop.x, shop.y) + 0.2, () => drawWorldLabel(shop.x + shop.w / 2, shop.y + 0.4, 150, "SURF SHOP", AQUA));
    } else {
      add(depthOf(shop.x, shop.y) + 0.05, () => drawCafeHut(shop, amount));
      add(depthOf(shop.x, shop.y) + 1.0, () => drawBeachCafe(shop, t, amount));
      for (const c of solid.filter((c) => c.id.startsWith("cafe-post"))) add(depthOf(c.x, c.y) + 0.05, () => drawPost(c.x, c.y, HUT_Z));
      add(depthOf(shop.x + shop.w, shop.y + 1.3), () => drawThatchRoof(shop.x - 0.3, shop.y - 0.05, shop.w + 0.6, 1.3, HUT_Z));
      add(depthOf(shop.x + shop.w, shop.y + 1.35), () => drawStringLights(t, amount));
      add(depthOf(shop.x, shop.y) + 0.2, () => drawWorldLabel(shop.x + shop.w / 2 - 0.4, shop.y + 0.4, 150, "BEACH CAFE", CORAL));
      solid.filter((c) => c.id.startsWith("beach-table")).forEach((c, i) => {
        add(depthOf(c.x, c.y) + 0.1, () => drawBeachTable(c.x, c.y, i));
        add(depthOf(c.x, c.y) + 0.9, () => drawParasol(c.x, c.y, i % 2 ? SUN : AQUA));
      });
      glowAt(add, 28.2, 27.4, amount);
    }
  }
  world.beach.loungers.forEach((l, i) => add(depthOf(l.x, l.y) + 1.5, () => drawLounger(l, i)));
  world.beach.loungers.forEach((l, i) => {
    if (i % 2 === 1) add(depthOf(l.x, l.y) + 2.2, () => drawParasol(l.x + 0.4, l.y - 0.4, [CORAL, AQUA, SUN, "#bce65f"][i % 4]));
  });
  const kerb = world.beach.kerb;
  kerb.segments.forEach(([x0, x1]) => {
    for (let a = x0; a < x1 - 1e-6; a += 1.6) {
      const b = Math.min(a + 1.6, x1);
      add(depthOf(b, kerb.y + kerb.h + 0.05), () => drawKerbSegment(a, b));
    }
    for (const x of [x0 + 0.12, x1 - 0.12]) add(depthOf(x, kerb.y + 0.3), () => drawBollard(x, kerb.y + kerb.h / 2, amount));
  });
  world.beach.bins.forEach(([x, y]) => add(depthOf(x, y) + 0.2, () => drawBin(x, y)));
  world.beach.planterBoxes.forEach((b, i) => add(depthOf(b[0], b[1] + b[3]), () => drawPlanterBox(b, i)));
  add(depthOf(world.beach.fountain.x, world.beach.fountain.y) + 0.2, () => drawFountain(world.beach.fountain));
  add(depthOf(world.beach.iceCart.x, world.beach.iceCart.y) + world.beach.iceCart.h, () => drawIceCart(world.beach.iceCart, t, amount));
  for (const a of world.beach.annexes) {
    if (a.id === "surf-cabins") add(depthOf(a.x, a.y) + a.h + 0.1, () => drawSurfCabins(a, amount));
    else add(depthOf(a.x, a.y) + a.h + 0.1, () => drawCafeContainer(a, amount));
  }
  world.beach.signs.forEach((sg) => add(depthOf(sg.x, sg.y) + 0.2, () => drawChalkSign(sg)));
  add(depthOf(6.0, 27.6), () => drawBunting({ x: 6.0, y: 27.5 }, { x: 10.75, y: 27.5 }, 86, amount, t, [CORAL, "#ffffff", AQUA, SUN]));
  add(depthOf(25.3, 28.6), () => drawBunting({ x: 25.3, y: 28.5 }, { x: 31.4, y: 28.5 }, 84, amount, t, [SUN, "#ffffff", CORAL, "#bce65f"]));
  const pit = world.beach.firePit;
  add(depthOf(pit.x, pit.y) + 0.4, () => drawFirePit(pit, t, amount));
  pit.logs.forEach((l) => add(depthOf(pit.x + l[0], pit.y + l[1] + l[3]), () => drawLog(pit, l)));
  promenadeGrass().forEach((g) => add(depthOf(g.x, g.y) + 0.2, () => drawGrassClump(g.x, g.y, t, g.index)));
  world.beach.towels.forEach((tw, i) => {
    if (tw.occupied) add(depthOf(tw.x, tw.y) + tw.h + 0.1, () => drawSunbather(tw, i));
  });
  world.beach.fireside.forEach((p, i) => add(depthOf(p[0], p[1] + 0.35), () => drawFireSitter(p, i, t)));
  world.beach.players.forEach((pl, i) => add(depthOf(pl.x, pl.y), () => drawVolleyPlayer(pl, i, t)));
  add(depthOf(world.beach.volleyball.x1, world.beach.volleyball.y + 3.2), () => drawVolleyBall(t));
  const dog = dogAt(t);
  add(depthOf(dog.x, dog.y), () => drawDog(t));
  world.beach.surfers.forEach((sf, i) => add(depthOf(sf.x0, sf.y), () => drawSurfer(sf, i, t)));
  world.beach.paddlers.forEach((pd, i) => add(depthOf(pd.x, pd.y), () => drawPaddler(pd, i, t)));
  add(1, () => drawTidePools(t));
  add(depthOf(world.beach.lighthouse.x, world.beach.lighthouse.y), () => drawLighthouse(world.beach.lighthouse, t, amount));
  const dorm = dormSpot();
  // the Dorm front sorts by the front edge of its canopy, which reaches 1.2 tiles beyond the wall
  add(depthOf(dorm.part.x, dorm.front + 1.2), () => drawDormFront(t, amount));
  add(depthOf(dorm.east, dorm.part.y + 0.9 + 3.3), () => drawDormBalcony(t));
  add(depthOf(-0.9, 12.95), drawDeliveryLorry); // the front edge of the lorry
  add(depthOf(1.75, 10.9), () => drawLorryCrew(t));
  add(depthOf(41.35, 12.2), () => drawHedge(4.5, 12.0));
  add(depthOf(41.35, 25.2), () => drawHedge(12.0, 25.0));
  [8.4, 10.3, 12.2].forEach((y, i) => add(depthOf(42.6, y + 1.0), () => drawGardenBed(42.6, y, i, t)));
  add(depthOf(43.4, 20.0), () => drawHammock(t));
  const environment = environmentalProfile(scene.clock, scene.day, t);
  EDGE_TREES.forEach(([x, y, size]) => add(depthOf(x, y) + 0.3, () => drawTree(x, y, size, t, environment)));
  world.beach.dunes.forEach((d, i) => add(depthOf(d.x, d.y) + 0.5, () => drawDune(d, t, i)));
  grassClumps().forEach((g) => add(depthOf(g.x, g.y) + 0.2, () => drawGrassClump(g.x, g.y, t, g.index)));
  world.beach.benches.forEach(([x, y]) => add(depthOf(x, y) + 0.6, () => drawCampusBench(x, y, 0)));
  world.beach.umbrellas.forEach((u) => add(depthOf(u.x, u.y) + 1.2, () => drawStandingUmbrella(u)));
  add(depthOf(world.beach.sandcastle.x, world.beach.sandcastle.y) + 0.6, () => drawSandcastle(world.beach.sandcastle));
  world.beach.rocks.forEach((r, i) => add(depthOf(r.x, r.y) + 0.3, () => drawRock(r, t, i)));
  world.beach.flags.forEach((f) => add(depthOf(f.x, f.y) + 0.2, () => drawBeachFlag(f, t)));
  add(depthOf(world.beach.shower.x, world.beach.shower.y) + 0.3, () => drawShower(world.beach.shower));
  world.beach.swimmers.forEach((sw) => add(depthOf(sw.x, sw.y), () => drawSwimmer(sw, t)));
  world.beach.kites.forEach((k) => add(200, () => drawKite(k, t)));
  add(depthOf(world.beach.volleyball.x1, world.beach.volleyball.y + 0.2), () => drawVolleyNet(t));
  add(depthOf(world.beach.tower.x, world.beach.tower.y) + 1.7, () => drawLifeguardTower(t, amount));
  add(depthOf(world.beach.rescueBoat.x, world.beach.rescueBoat.y) + 1.0, drawRescueBoat);
  world.beach.buoys.forEach(([x, y], i) => add(depthOf(x, y), () => drawBuoy(x, y, t, i)));
  world.beach.boats.forEach((b, i) => add(depthOf(b.x, b.y), () => drawBoat(b, t, i)));
  world.beach.gulls.forEach((g) => add(200, () => drawGull(g, t)));

  const bench = solid.find((c) => c.id === "dorm-bench");
  add(depthOf(bench.x, bench.y) + 0.5, () => drawCampusBench(bench.x, bench.y, 0));
  add(depthOf(dorm.part.x + 0.2, dorm.front + 0.55), drawMailbox);
  return actors;
}

function glowAt(add, x, y, amount) {
  add(depthOf(x, y) - 0.5, () => glow(x, y, 5, 130, amount));
}
