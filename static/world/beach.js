// The beach front south of the plaza and the Dorm's surroundings (spec nova-zones): the boardwalk, the
// Surf Shop and the Beach Cafe, the sand with loungers, dunes, a volleyball court and a lifeguard tower,
// the shoreline, and the Dorm's bikes, bench and door. Everything is drawn in code from the data in
// world.py (BEACH_WAY, SHOPS_OUTDOOR, BEACH, DORM). Nothing moves at random: waves, grass, flags and
// gulls follow the clock, and the lamps and string lights come on as the evening light falls.
// Only for showing: no rule reads any of this, and no label is evaluated.

import { drawCampusBench } from "./campus.js";
import { drawWindFlag, environmentalProfile, lightingProfile } from "./environment.js";
import {
  drawBlock,
  drawFacadeBandY,
  drawGroundSlab,
  drawPlane,
  drawRaisedSlab,
  drawSoftShadow,
  drawSpaceCaption,
  drawWorldLabel,
  mixColor,
} from "./primitives.js";
import { ctx, isoPoint, reducedMotion, scene, world } from "./scene.js";

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
function glow(x, y, z, radius, amount) {
  if (amount < 0.03) return;
  const p = isoPoint(x, y, z);
  ctx.save();
  const g = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, radius);
  g.addColorStop(0, `rgba(255,214,130,${0.5 * amount})`);
  g.addColorStop(1, "rgba(255,214,130,0)");
  ctx.fillStyle = g;
  ctx.beginPath();
  ctx.ellipse(p.x, p.y, radius, radius * 0.5, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
}

// a quad flat on the ground
const flat = (x, y, w, h, fill, z = 5, stroke = null) =>
  drawPlane([isoPoint(x, y, z), isoPoint(x + w, y, z), isoPoint(x + w, y + h, z), isoPoint(x, y + h, z)], fill, stroke);

// ---- the ground: sand, shoreline, boardwalk, decks --------------------------------------------

// sand drifting over the paving in front of the beach, with a wavy edge
function drawSandWash() {
  const points = [];
  for (let x = 1.2; x <= 41.4; x += 0.9) points.push(isoPoint(x, 19.7 - 0.38 * Math.sin(x * 0.55) - 0.14 * Math.sin(x * 1.9), 4.6));
  for (let x = 41.4; x >= 1.2; x -= 0.9) points.push(isoPoint(x, 20.3, 4.6));
  drawPlane(points, "rgba(222,194,126,.62)", null);
}

// ripples in the sand, a darker wet strip along the water, foam that comes in and goes out
function drawShore(t) {
  for (let j = 0; j < 9; j++) {
    for (let i = 0; i < 34; i++) {
      if ((i * 3 + j * 5) % 4 === 0) continue; // the ripples are not in a grid
      const x = 1.6 + i * 1.18 + (j % 2) * 0.6;
      const y = 20.9 + j * 0.56 + ((i * 7) % 5) * 0.05;
      line(isoPoint(x, y, 4.8), isoPoint(x + 0.55, y + 0.02, 4.8), "#b79b5c", 0.8, 0.28);
    }
  }
  const wet = [];
  for (let x = 1.5; x <= 41.5; x += 0.9) wet.push(isoPoint(x, 25.2 + 0.18 * Math.sin(x * 0.6 + clock(t) * 0.0009), 4.7));
  for (let x = 41.5; x >= 1.5; x -= 0.9) wet.push(isoPoint(x, 26.05, 4.7));
  drawPlane(wet, "rgba(120,98,60,.2)", null);
  for (let k = 0; k < 3; k++) {
    ctx.save();
    ctx.strokeStyle = "#ffffff";
    ctx.globalAlpha = 0.72 - k * 0.2;
    ctx.lineWidth = 2.6 - k * 0.7;
    ctx.beginPath();
    for (let x = 1.5; x <= 41.5; x += 0.5) {
      const swell = 0.16 * Math.sin(x * 0.7 + clock(t) * 0.0018 - k * 0.8) + 0.1 * Math.sin(x * 1.9 + clock(t) * 0.0011);
      const p = isoPoint(x, 25.92 - k * 0.2 + swell, 4.9);
      if (x === 1.5) ctx.moveTo(p.x, p.y);
      else ctx.lineTo(p.x, p.y);
    }
    ctx.stroke();
    ctx.restore();
  }
}

function drawBeachDetails() {
  const beach = world.beach;
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
  dot(isoPoint(net.x1 + 0.9, net.y + 0.9, 8), 2.8, "#ffffff");
  ctx.strokeStyle = "rgba(49,84,91,.5)";
  ctx.lineWidth = 0.7;
  const b = isoPoint(net.x1 + 0.9, net.y + 0.9, 8);
  ctx.beginPath();
  ctx.arc(b.x, b.y, 2.8, 0.4, 2.6);
  ctx.stroke();
}

// the boardwalk: planks in two tones with dark gaps, edge beams, nails, a worn middle, steps to the sand
function drawBoardwalk() {
  const way = world.beachWay;
  drawSoftShadow(way.x + way.w / 2, way.y + way.h / 2, way.w * 22, way.h * 20, 0.08);
  drawGroundSlab(way.x - 0.2, way.y, way.w + 0.4, way.h, "#8b6645", 5);
  const rows = Math.floor(way.h / 0.4);
  for (let j = 0; j < rows; j++) {
    const y = way.y + j * 0.4;
    const tone = (j * 5) % 3 === 0 ? "#b88a58" : j % 2 ? "#c49a62" : "#cfa970";
    flat(way.x, y, way.w, 0.36, tone, 5.4, "rgba(70,45,22,.35)");
    // the boards are cut at different places
    const cut = way.x + ((j * 37) % 23) / 23 * way.w;
    line(isoPoint(cut, y, 5.6), isoPoint(cut, y + 0.36, 5.6), "rgba(70,45,22,.45)", 0.8);
    if (j % 2 === 0) {
      dot(isoPoint(way.x + 0.2, y + 0.18, 5.7), 0.7, "#6b4a2a");
      dot(isoPoint(way.x + way.w - 0.2, y + 0.18, 5.7), 0.7, "#6b4a2a");
    }
  }
  flat(way.x + way.w / 2 - 0.35, way.y, 0.7, way.h, "rgba(255,244,214,.16)", 5.5);
  flat(way.x - 0.14, way.y, 0.14, way.h, "#8b6645", 5.8);
  flat(way.x + way.w, way.y, 0.14, way.h, "#8b6645", 5.8);
  // steps down to the sand
  for (let s = 0; s < 3; s++) {
    flat(way.x + s * 0.18, way.y + way.h + s * 0.2, way.w - s * 0.36, 0.2, ["#a98050", "#97703f", "#86602f"][s], 5.3 - s * 0.3, "rgba(60,40,20,.4)");
  }
}

function drawDeck(x, y, w, h, base) {
  drawGroundSlab(x - 0.1, y - 0.1, w + 0.2, h + 0.2, "#8b6645", 5);
  const rows = Math.floor(h / 0.36);
  for (let j = 0; j < rows; j++) flat(x, y + j * 0.36, w, 0.33, j % 2 ? base : light(base, 0.1), 5.4, "rgba(70,45,22,.3)");
}

function drawDormGround() {
  // the way from the door: timber threshold, a welcome mat, and flagstones to the plaza
  drawDeck(37.0, 12.65, 2.0, 1.4, "#c9a878");
  flat(37.25, 12.7, 1.5, 0.4, "#3b5d65", 5.8);
  for (let i = 0; i < 5; i++) flat(37.2 + (i % 2) * 0.4, 14.3 + i * 0.55, 1.3, 0.4, "#e7e2d6", 4.8, "rgba(70,70,60,.25)");
  // a strip of grass and flowers between the Dorm and the Hub
  drawGroundSlab(33.6, 7.8, 1.3, 5.9, "#83a774", 3.4);
  for (let i = 0; i < 7; i++) dot(isoPoint(34.0 + (i % 2) * 0.6, 8.4 + i * 0.75, 5), 1.5, [SUN, CORAL, "#ffffff"][i % 3]);
}

export function drawBeachGround(t) {
  drawSandWash();
  drawShore(t);
  drawBeachDetails();
  drawBoardwalk();
  for (const shop of world.outdoorShops) {
    const base = shop.id === "surf-shop" ? "#b98b59" : "#c9a878";
    drawDeck(shop.x, shop.y, shop.w, shop.h, base);
    drawSoftShadow(shop.x + shop.w / 2, shop.y + shop.h / 2, shop.w * 22, shop.h * 18, 0.1);
  }
  drawDormGround();
  drawSpaceCaption(18.4, 25.5, "Beach", "#8b6645");
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
  const railTop = isoPoint(11.15, 21.5, 52);
  const railEnd = isoPoint(11.15, 22.8, 52);
  line(railTop, railEnd, "#31545b", 2);
  line(isoPoint(11.15, 21.5, 5), railTop, "#31545b", 2);
  line(isoPoint(11.15, 22.8, 5), railEnd, "#31545b", 2);
  ["#2f4d5a", "#ff7458", "#64cbc8"].forEach((color, i) => {
    const p = isoPoint(11.15, 21.7 + i * 0.42, 52);
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.moveTo(p.x - 4, p.y);
    ctx.lineTo(p.x + 4, p.y);
    ctx.lineTo(p.x + 3, p.y + 20);
    ctx.lineTo(p.x - 3, p.y + 20);
    ctx.closePath();
    ctx.fill();
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
    const p = isoPoint(x, 22.2, 16);
    line(isoPoint(x, 22.2, 5), p, "#31545b", 2);
    oval(p, 5, 2.5, CORAL);
  }
  // the menu board under the awning
  const m = isoPoint(28.1, 21.02, 54);
  roundedRectAt({ x: m.x, y: m.y - 8 }, 30, 18, "#22343a");
  ctx.fillStyle = "#e9f2ee";
  ctx.textAlign = "center";
  ctx.font = "800 4.4px Menlo, Consolas, monospace";
  ctx.fillText("BEACH MENU", m.x, m.y - 12);
  for (const [i, color] of [AQUA, SUN, CORAL].entries()) line({ x: m.x - 9, y: m.y - 8 + i * 3.4 }, { x: m.x + 9 - i * 3, y: m.y - 8 + i * 3.4 }, color, 1.2, 0.9);
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
      const p = isoPoint(a.x + (b.x - a.x) * f, a.y + (b.y - a.y) * f, 66 - 5 * Math.sin(Math.PI * f));
      if (i === 0) ctx.moveTo(p.x, p.y);
      else ctx.lineTo(p.x, p.y);
    }
    ctx.stroke();
    ctx.restore();
    for (let i = 1; i < count; i++) {
      const f = i / count;
      const p = isoPoint(a.x + (b.x - a.x) * f, a.y + (b.y - a.y) * f, 64 - 5 * Math.sin(Math.PI * f));
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

function drawLifeguardTower(t) {
  const tower = world.beach.tower;
  const cx = tower.x + tower.w / 2;
  const cy = tower.y + tower.h / 2;
  for (const [dx, dy] of [[0.1, 0.1], [tower.w - 0.1, 0.1], [0.1, tower.h - 0.1], [tower.w - 0.1, tower.h - 0.1]]) {
    line(isoPoint(tower.x + dx, tower.y + dy, 5), isoPoint(tower.x + dx, tower.y + dy, 30), "#e9e3d4", 3);
  }
  line(isoPoint(tower.x + 0.1, tower.y + tower.h - 0.1, 5), isoPoint(tower.x + 0.1, tower.y + tower.h - 0.1, 30), "#e9e3d4", 3);
  for (let r = 0; r < 4; r++) {
    line(isoPoint(tower.x + 0.1, tower.y + tower.h + 0.1 + r * 0.14, 8 + r * 5), isoPoint(tower.x + 0.5, tower.y + tower.h + 0.1 + r * 0.14, 8 + r * 5), "#b98b59", 1.4);
  }
  drawBlock(tower.x - 0.05, tower.y - 0.05, tower.w + 0.1, tower.h + 0.1, 32, "#ffffff", "#c9cdd0", "#e4e5e2");
  drawBlock(tower.x - 0.05, tower.y - 0.05, tower.w + 0.1, tower.h + 0.1, 56, "#fbfaf6", dark("#ffffff", 0.2), "#eceae2");
  drawFacadeBandY(tower.x, tower.y + tower.h + 0.06, tower.w, 36, 48, "#2a5573", 3);
  drawFacadeBandY(tower.x, tower.y + tower.h + 0.062, tower.w, 32, 36, CORAL, 1);
  drawRaisedSlab(tower.x - 0.2, tower.y - 0.2, tower.w + 0.4, tower.h + 0.4, 62, 5, CORAL, dark(CORAL, 0.3), dark(CORAL, 0.15));
  line(isoPoint(cx, cy, 62), isoPoint(cx, cy, 86), "#e9e3d4", 2);
  drawWindFlag(cx, cy, 84, SUN, t, environmentalProfile(scene.clock, scene.day, t), 0.7);
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

function drawBikeRack() {
  const rack = world.colliders.campus.find((c) => c.id === "dorm-bike-rack");
  for (let i = 0; i < 4; i++) {
    const x = rack.x + 0.1 + i * 0.4;
    line(isoPoint(x, rack.y + 0.15, 5), isoPoint(x, rack.y + 0.15, 17), "#31545b", 1.6);
    line(isoPoint(x, rack.y + 0.15, 17), isoPoint(x + 0.2, rack.y + 0.15, 17), "#31545b", 1.6);
    line(isoPoint(x + 0.2, rack.y + 0.15, 17), isoPoint(x + 0.2, rack.y + 0.15, 5), "#31545b", 1.6);
  }
  [[rack.x + 0.4, "#ff7458"], [rack.x + 1.0, "#64cbc8"]].forEach(([x, color]) => {
    const front = isoPoint(x + 0.2, rack.y + 0.15, 9);
    const back = isoPoint(x - 0.28, rack.y + 0.15, 9);
    for (const w of [front, back]) {
      ctx.strokeStyle = "#22343a";
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.arc(w.x, w.y, 5.2, 0, Math.PI * 2);
      ctx.stroke();
    }
    const seat = { x: (front.x + back.x) / 2 - 1, y: front.y - 9 };
    line(back, seat, color, 1.8);
    line(seat, front, color, 1.8);
    line({ x: front.x - 1, y: front.y - 11 }, front, color, 1.8);
    line({ x: seat.x - 3, y: seat.y - 1 }, { x: seat.x + 2, y: seat.y - 1 }, "#22343a", 1.8);
  });
}

function drawMailbox() {
  const p = isoPoint(35.2, 12.85, 5);
  line(p, { x: p.x, y: p.y - 15 }, "#31545b", 2);
  roundedRectAt({ x: p.x, y: p.y - 19 }, 9, 7, "#ff7458");
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(p.x - 2.5, p.y - 20.5, 5, 1.2);
}

// ---- everything that stands, sorted with the rest of the scene -------------------------------------

export function beachActors(t) {
  const amount = night();
  const solid = world.colliders.campus;
  const actors = [];
  const add = (depth, draw) => actors.push({ depth, draw });

  for (const c of solid) {
    if (c.id.startsWith("way-lamp")) add(c.x + c.y + 0.05, () => drawLamp(c.x, c.y, amount));
  }
  add(14.4 + 17.5 + 0.2, () => drawArch(amount));
  add(11.5 + 23.5 + 1.3, () => drawCampusBench(11.5, 23.5, 1));
  add(17.0 + 23.5 + 1.3, () => drawCampusBench(17.0, 23.5, 1));

  for (const shop of world.outdoorShops) {
    if (shop.id === "surf-shop") {
      add(shop.x + shop.y + 1.0, () => drawSurfShop(shop, amount));
      for (const c of solid.filter((c) => c.id.startsWith("surf-post"))) add(c.x + c.y + 0.05, () => drawPost(c.x, c.y));
      add(shop.x + shop.y + 0.4, () => drawAwning(6.5, 21.0, 4.4, 2.2, 66, "#2e8b8f", amount));
      add(shop.x + shop.y + 0.2, () => drawWorldLabel(shop.x + shop.w / 2, shop.y + 0.4, 96, "SURF SHOP", AQUA));
    } else {
      add(shop.x + shop.y + 1.0, () => drawBeachCafe(shop, t, amount));
      for (const c of solid.filter((c) => c.id.startsWith("cafe-post"))) add(c.x + c.y + 0.05, () => drawPost(c.x, c.y, 68));
      add(shop.x + shop.y + 0.4, () => drawAwning(25.3, 20.8, 5.8, 1.9, 68, CORAL, amount));
      add(shop.x + shop.y + 0.45, () => drawStringLights(t, amount));
      add(shop.x + shop.y + 0.2, () => drawWorldLabel(shop.x + shop.w / 2 - 0.4, shop.y + 0.4, 98, "BEACH CAFE", CORAL));
      solid.filter((c) => c.id.startsWith("beach-table")).forEach((c, i) => {
        add(c.x + c.y + 0.1, () => drawBeachTable(c.x, c.y, i));
        add(c.x + c.y + 0.9, () => drawParasol(c.x, c.y, i % 2 ? SUN : AQUA));
      });
      glowAt(add, 28.2, 22.4, amount);
    }
  }
  world.beach.loungers.forEach((l, i) => add(l.x + l.y + 1.5, () => drawLounger(l, i)));
  world.beach.loungers.forEach((l, i) => {
    if (i % 2 === 1) add(l.x + l.y + 2.2, () => drawParasol(l.x + 0.4, l.y - 0.4, [CORAL, AQUA, SUN, "#bce65f"][i % 4]));
  });
  world.beach.dunes.forEach((d, i) => add(d.x + d.y + 0.5, () => drawDune(d, t, i)));
  add(world.beach.volleyball.x1 + world.beach.volleyball.y + 0.2, () => drawVolleyNet(t));
  add(world.beach.tower.x + world.beach.tower.y + 1.2, () => drawLifeguardTower(t));
  world.beach.buoys.forEach(([x, y], i) => add(x + y, () => drawBuoy(x, y, t, i)));
  world.beach.boats.forEach((b, i) => add(b.x + b.y, () => drawBoat(b, t, i)));
  world.beach.gulls.forEach((g) => add(200, () => drawGull(g, t)));

  add(35.3 + 13.1 + 0.5, drawBikeRack);
  add(39.3 + 13.1 + 0.5, () => drawCampusBench(39.3, 13.1, 0));
  add(35.2 + 12.85 + 0.3, drawMailbox);
  return actors;
}

function glowAt(add, x, y, amount) {
  add(x + y - 0.5, () => glow(x, y, 5, 130, amount));
}
