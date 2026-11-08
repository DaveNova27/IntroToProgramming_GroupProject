// The rooms inside the Nova: the floor, the furniture, the shops and the people.
// Drawing code started from Felix Antes' Nova Beach Ventures
// (https://github.com/felix-anthes-png/nova-beach-ventures) and was redrawn for the walk-in Nova.
// All of it is placed from the data in world.py (world.interiors.campus). Drawing only.
//
// The camera looks from the south-east, so the fronts that show are the south and east faces:
// counters and shelves stand against the north and west walls. Everything wider than about a
// tile is drawn in slices, so that a person standing in front of or behind it is sorted right.

import { drawPersonFigure } from "./people.js";
import { drawBlock, drawFacadeBandY, drawPlane, drawRaisedSlab, mixColor, roundedRect } from "./primitives.js";
import { DAY_END, DAY_START, TILE_H, TILE_W, ctx, isoPoint, scene, world } from "./scene.js";

const FLOOR_Z = 4;
export const GALLERY_Z = 54; // the upper floor along the north wall of the atrium
const INK = "#173743";
const TEAL = "#31545b";
const CORAL = "#ff7458";
const LIME = "#bce65f";
const SUN = "#f5c95e";
const AQUA = "#64cbc8";
const LILAC = "#9a7bc1";
const ACCENTS = [SUN, CORAL, AQUA, LIME, LILAC];

const layout = () => world.interiors.campus;
const dark = (color, amount) => mixColor(color, "#000000", amount);
const light = (color, amount) => mixColor(color, "#ffffff", amount);
const shades = (top) => [top, dark(top, 0.3), dark(top, 0.16)]; // top, east face, south face

// the walkable floor: the footprint of the Nova without its walls
export function floorBounds() {
  const { parts, wall } = world.nova;
  const x0 = Math.min(...parts.map((p) => p.x)) + wall;
  const y0 = Math.min(...parts.map((p) => p.y)) + wall;
  const x1 = Math.max(...parts.map((p) => p.x + p.w)) - wall;
  const y1 = Math.max(...parts.map((p) => p.y + p.h)) - wall;
  return { x: x0, y: y0, w: x1 - x0, h: y1 - y0 };
}

// ---- small drawing helpers ----------------------------------------------------------------

function floorQuad(x, y, w, h, fill, z = FLOOR_Z) {
  drawPlane([isoPoint(x, y, z), isoPoint(x + w, y, z), isoPoint(x + w, y + h, z), isoPoint(x, y + h, z)], fill, null);
}

function floorLine(x1, y1, x2, y2, color, width = 0.8, z = FLOOR_Z) {
  const a = isoPoint(x1, y1, z);
  const b = isoPoint(x2, y2, z);
  ctx.strokeStyle = color;
  ctx.lineWidth = width;
  ctx.beginPath();
  ctx.moveTo(a.x, a.y);
  ctx.lineTo(b.x, b.y);
  ctx.stroke();
}

function ellipseAt(p, rx, ry, fill) {
  ctx.fillStyle = fill;
  ctx.beginPath();
  ctx.ellipse(p.x, p.y, rx, ry, 0, 0, Math.PI * 2);
  ctx.fill();
}

// a ring on the floor: a circle of `radius` tiles is an ellipse on the screen
function floorRing(x, y, radius, stroke, width, fill = null) {
  const p = isoPoint(x, y, FLOOR_Z + 0.2);
  const rx = radius * TILE_W * 0.707;
  ctx.beginPath();
  ctx.ellipse(p.x, p.y, rx, rx / 2, 0, 0, Math.PI * 2);
  if (fill) {
    ctx.fillStyle = fill;
    ctx.fill();
  }
  if (stroke) {
    ctx.strokeStyle = stroke;
    ctx.lineWidth = width;
    ctx.stroke();
  }
}

// ---- the floor ---------------------------------------------------------------------------------

// every place has its own floor: timber, polished stone, carpet, concrete
function paintCafeFloor(area) {
  floorQuad(area.x, area.y, area.w, area.h, "#dcc59b");
  const rows = Math.ceil(area.h / 0.45);
  for (let i = 0; i < rows; i++) {
    const y = area.y + i * 0.45;
    const h = Math.min(0.45, area.y + area.h - y);
    if (i % 2) floorQuad(area.x, y, area.w, h, "rgba(255,244,214,.24)");
    floorLine(area.x, y, area.x + area.w, y, "rgba(112,76,38,.26)", 0.7);
    for (let x = area.x + ((i * 1.1) % 2.2) + 0.4; x < area.x + area.w; x += 2.2) {
      floorLine(x, y, x, y + h, "rgba(112,76,38,.2)", 0.6);
    }
  }
}

function paintAtriumFloor(area) {
  floorQuad(area.x, area.y, area.w, area.h, "#f1efea");
  for (let x = area.x + 2; x < area.x + area.w - 0.1; x += 2) floorLine(x, area.y, x, area.y + area.h, "rgba(20,61,66,.09)", 0.7);
  for (let y = area.y + 2; y < area.y + area.h - 0.1; y += 2) floorLine(area.x, y, area.x + area.w, y, "rgba(20,61,66,.09)", 0.7);
  // an inlaid border and a round medallion on the axis of the entrance
  const inset = 0.45;
  const left = area.x + inset;
  const top = area.y + inset;
  const right = area.x + area.w - inset;
  const bottom = area.y + area.h - inset;
  const border = "rgba(100,203,200,.55)";
  floorLine(left, top, right, top, border, 2.2);
  floorLine(right, top, right, bottom, border, 2.2);
  floorLine(right, bottom, left, bottom, border, 2.2);
  floorLine(left, bottom, left, top, border, 2.2);
  const cx = area.x + area.w / 2;
  floorRing(cx, 5.9, 1.2, "rgba(100,203,200,.55)", 1.6, "rgba(100,203,200,.1)");
  floorRing(cx, 5.9, 0.82, "rgba(49,84,91,.28)", 1.1);
  floorRing(cx, 5.9, 0.4, null, 0, "rgba(245,201,94,.4)");
}

function paintMerchFloor(area) {
  floorQuad(area.x, area.y, area.w, area.h, "#cfe3df");
  for (let i = 0, x = area.x + 0.3; x < area.x + area.w - 0.3; i++, x += 0.7) {
    if (i % 2 === 0) floorQuad(x, area.y, Math.min(0.7, area.x + area.w - x), area.h, "rgba(100,203,200,.17)");
  }
  const border = "rgba(150,200,60,.75)";
  const right = area.x + area.w - 0.3;
  const bottom = area.y + area.h - 0.25;
  floorLine(area.x + 0.3, bottom, right, bottom, border, 2);
  floorLine(right, area.y + 0.3, right, bottom, border, 2);
}

function paintPrintFloor(area) {
  floorQuad(area.x, area.y, area.w, area.h, "#d6d8d6");
  for (let x = area.x + 1.5; x < area.x + area.w; x += 1.5) floorLine(x, area.y, x, area.y + area.h, "rgba(20,61,66,.1)", 0.7);
  for (let y = area.y + 1.5; y < area.y + area.h; y += 1.5) floorLine(area.x, y, area.x + area.w, y, "rgba(20,61,66,.1)", 0.7);
  // a safety line in front of the machines
  const printer = layout().solid.find((item) => item.id.startsWith("printer"));
  if (printer) floorQuad(area.x + 0.3, printer.y - 0.32, area.w - 0.6, 0.07, "#f1c94b");
}

const FLOORS = { cafe: paintCafeFloor, atrium: paintAtriumFloor, merch: paintMerchFloor, print: paintPrintFloor };

// the mat inside the entrance
function paintEntranceMat() {
  const door = world.nova.entrances[0];
  const x = door.x + 0.7;
  const w = door.width - 1.4;
  const y = door.y - 0.7;
  floorQuad(x, y, w, 0.6, "#3b5d65");
  for (let i = 1; i < 8; i++) floorLine(x + (w * i) / 8, y, x + (w * i) / 8, y + 0.6, "rgba(255,255,255,.18)", 0.8);
}

// patches of light from the windows in the north wall, moving with the time of day
function paintWindowLight() {
  const { x, y, w } = floorBounds();
  const day = Math.max(0, Math.min(1, (scene.clock - DAY_START) / (DAY_END - DAY_START)));
  const slant = -2.4 + 4.8 * day;
  const strength = 0.1 + 0.07 * Math.sin(Math.PI * day);
  for (let px = x + 1.2; px < x + w - 1.4; px += 2.7) {
    const near = isoPoint(px, y, FLOOR_Z + 0.1);
    const far = isoPoint(px + 1.45, y, FLOOR_Z + 0.1);
    const farDown = isoPoint(px + 1.45 + slant, y + 3.1, FLOOR_Z + 0.1);
    const nearDown = isoPoint(px + slant, y + 3.1, FLOOR_Z + 0.1);
    drawPlane([near, far, farDown, nearDown], `rgba(255,248,222,${strength})`, null);
  }
}

// every piece of furniture sits on a soft shadow
function paintContactShadows() {
  ctx.save();
  for (const item of layout().solid) {
    if ("r" in item) {
      ellipseAt(isoPoint(item.x + 0.08, item.y + 0.1, FLOOR_Z + 0.1), item.r * 62, item.r * 31, "rgba(10,30,36,.16)");
    } else {
      floorQuad(item.x + 0.02, item.y + 0.06, item.w + 0.16, item.h + 0.16, "rgba(10,30,36,.15)", FLOOR_Z + 0.1);
    }
  }
  ctx.restore();
}

// along the north and west wall the floor darkens a little
function paintWallEdges() {
  const { x, y, w, h } = floorBounds();
  floorQuad(x, y, w, 0.32, "rgba(20,45,52,.1)");
  floorQuad(x, y, 0.32, h, "rgba(20,45,52,.08)");
}

export function drawInteriorFloor() {
  const floor = floorBounds();
  floorQuad(floor.x, floor.y, floor.w, floor.h, layout().floor);
  for (const area of layout().areas) FLOORS[area.id]?.(area);
  paintEntranceMat();
  paintWallEdges();
  paintWindowLight();
  paintContactShadows();
}

// the names of the places, written on the floor, and the marked way in
export function drawInteriorWayfinding() {
  ctx.save();
  for (const area of layout().areas) {
    const at = area.labelAt ?? { x: area.x + 0.4, y: area.y + area.h - 0.5 };
    const text = area.label.toUpperCase();
    const p = isoPoint(at.x, at.y, FLOOR_Z + 1);
    ctx.save();
    ctx.translate(p.x, p.y);
    ctx.rotate(Math.atan2(TILE_H / 2, TILE_W / 2));
    ctx.textAlign = "left";
    ctx.font = "800 6.5px Menlo, Consolas, monospace";
    ctx.fillStyle = INK;
    ctx.globalAlpha = 0.74;
    ctx.fillText(text, 0, 0);
    ctx.restore();
    floorLine(at.x, at.y + 0.17, at.x + 0.16 * text.length + 0.2, at.y + 0.17, area.color, 3, FLOOR_Z + 0.5);
  }
  const { route } = layout();
  ctx.globalAlpha = 0.34;
  ctx.strokeStyle = TEAL;
  ctx.lineWidth = 2.4;
  ctx.setLineDash([6, 6]);
  for (let index = 1; index < route.length; index++) {
    const a = isoPoint(route[index - 1].x, route[index - 1].y, FLOOR_Z + 1);
    const b = isoPoint(route[index].x, route[index].y, FLOOR_Z + 1);
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();
  }
  ctx.setLineDash([]);
  const entry = isoPoint(route[0].x, route[0].y, FLOOR_Z + 1);
  ctx.globalAlpha = 0.9;
  roundedRect(entry.x - 27, entry.y - 6, 54, 12, 6, "rgba(100,203,200,.92)");
  ctx.fillStyle = INK;
  ctx.textAlign = "center";
  ctx.font = "900 5.5px Menlo, Consolas, monospace";
  ctx.fillText("ENTRANCE", entry.x, entry.y + 2);
  ctx.restore();
}

// ---- plants, stools, benches, columns -------------------------------------------------------

export function drawIndoorPlant(x, y, scale = 1) {
  const base = isoPoint(x, y, FLOOR_Z);
  ctx.save();
  ctx.translate(base.x, base.y);
  ctx.scale(scale, scale);
  // the pot
  ctx.fillStyle = "#cdc4b3";
  ctx.beginPath();
  ctx.moveTo(-9, -15);
  ctx.lineTo(9, -15);
  ctx.lineTo(7, -1);
  ctx.quadraticCurveTo(0, 4, -7, -1);
  ctx.closePath();
  ctx.fill();
  ctx.fillStyle = "rgba(0,0,0,.1)";
  ctx.beginPath();
  ctx.moveTo(2, -15);
  ctx.lineTo(9, -15);
  ctx.lineTo(7, -1);
  ctx.quadraticCurveTo(4, 2, 1, 1);
  ctx.closePath();
  ctx.fill();
  ellipseAt({ x: 0, y: -15 }, 9, 4.4, "#e7e0d2");
  ellipseAt({ x: 0, y: -15.3 }, 7, 3.2, "#4a3a2c");
  // the leaves fan out from the middle
  const leaves = [-78, -50, -24, 0, 24, 50, 78, -36, 36];
  leaves.forEach((degrees, index) => {
    const angle = (degrees * Math.PI) / 180;
    const length = 17 + ((index * 7) % 5) * 3;
    const tipX = Math.sin(angle) * length;
    const tipY = -15 - Math.cos(angle) * length * 1.05;
    ctx.fillStyle = index % 2 ? "#4f8a5b" : "#6ba96b";
    ctx.beginPath();
    ctx.moveTo(0, -15);
    ctx.quadraticCurveTo(tipX * 0.35 - 4, tipY * 0.55 - 6, tipX, tipY);
    ctx.quadraticCurveTo(tipX * 0.35 + 4, tipY * 0.5 - 3, 0, -15);
    ctx.fill();
    ctx.strokeStyle = "rgba(255,255,255,.22)";
    ctx.lineWidth = 0.7;
    ctx.beginPath();
    ctx.moveTo(0, -15);
    ctx.lineTo(tipX * 0.92, tipY * 0.95 - 1);
    ctx.stroke();
  });
  ctx.restore();
}

function drawStool(x, y, height = 15, color = TEAL) {
  const base = isoPoint(x, y, FLOOR_Z);
  const top = isoPoint(x, y, FLOOR_Z + height);
  ctx.strokeStyle = "#22434b";
  ctx.lineWidth = 2.2;
  ctx.beginPath();
  ctx.moveTo(base.x, base.y);
  ctx.lineTo(top.x, top.y + 2);
  ctx.stroke();
  ellipseAt({ x: base.x, y: base.y }, 6, 3, "rgba(34,67,75,.55)");
  ellipseAt({ x: top.x, y: top.y + 2.2 }, 8.5, 4.4, dark(color, 0.35));
  ellipseAt(top, 8.5, 4.4, color);
}

function drawBenchSlice(item, x, w, index, count) {
  const [top, east, south] = shades("#d2a56c");
  if (index === 0) drawBlock(x + 0.08, item.y + 0.08, 0.1, item.h - 0.16, 14, "#ffffff", "#c9cdd0", "#e4e5e2");
  if (index === count - 1) drawBlock(x + w - 0.18, item.y + 0.08, 0.1, item.h - 0.16, 14, "#ffffff", "#c9cdd0", "#e4e5e2");
  drawRaisedSlab(x, item.y, w, item.h, 17, 4, top, east, south);
  if (index === 0 || index === count - 1) {
    const color = index === 0 ? AQUA : CORAL;
    drawRaisedSlab(x + 0.12, item.y + 0.06, w - 0.22, item.h - 0.12, 21, 4, color, dark(color, 0.3), dark(color, 0.16));
  }
}

// a column is cut off at the height of the people when the roof is gone, like the front walls
function drawColumn(item) {
  const height = 36 + 42 * scene.roof;
  drawBlock(item.x - 0.15, item.y - 0.15, 0.3, 0.3, height, "#ffffff", "#c9cdd0", "#e4e5e2");
}

// ---- the cafe --------------------------------------------------------------------------------

function drawCafeShelfSlice(item, x, w, index) {
  const [top, east, south] = shades("#efeadf");
  drawBlock(x, item.y, w, item.h, 28, top, east, south);
  const front = item.y + item.h + 0.01;
  drawFacadeBandY(x + 0.05, front, w - 0.1, 4, 20, "#c99a62", 1);
  for (const z of [46, 60]) drawRaisedSlab(x, item.y, w, item.h, z, 2.5, "#dbbb86", "#a98a58", "#c3a572");
  // posts hold the planks
  ctx.strokeStyle = "#a98a58";
  ctx.lineWidth = 1.5;
  for (const px of [x + 0.02, x + w - 0.02]) {
    const a = isoPoint(px, front, 28);
    const b = isoPoint(px, front, 61);
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();
  }
  // cups, jars and boxes
  const count = Math.max(2, Math.round(w / 0.36));
  const colors = ["#f3f1ea", SUN, "#f3f1ea", CORAL, AQUA, "#f3f1ea", LIME];
  for (let k = 0; k < count; k++) {
    const px = x + ((k + 0.5) * w) / count;
    for (const [level, z] of [[0, 28], [1, 46], [2, 60]]) {
      const tall = 5 + ((index + k + level) % 3) * 2;
      const p = isoPoint(px, item.y + item.h * 0.7, z + (level ? 1 : 0));
      ctx.fillStyle = colors[(index * 3 + k + level * 2) % colors.length];
      ctx.fillRect(p.x - 2.5, p.y - tall, 5, tall);
      ctx.fillStyle = "rgba(0,0,0,.14)";
      ctx.fillRect(p.x + 0.5, p.y - tall, 2, tall);
    }
  }
}

function drawEspressoMachine(x, y) {
  const machine = isoPoint(x, y, 28 + 13);
  roundedRect(machine.x - 17, machine.y - 15, 34, 20, 4, "#e9eae4");
  roundedRect(machine.x - 17, machine.y + 2, 34, 4, 2, "#b9bdb8");
  ctx.fillStyle = INK;
  ctx.fillRect(machine.x - 11, machine.y - 10, 22, 6);
  ctx.fillStyle = CORAL;
  ctx.beginPath();
  ctx.arc(machine.x + 12, machine.y - 7, 2, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = "#c9ccc6";
  ctx.fillRect(machine.x - 9, machine.y + 5, 3, 5);
  ctx.fillRect(machine.x + 5, machine.y + 5, 3, 5);
}

function drawCup(x, y, z) {
  const p = isoPoint(x, y, z);
  ellipseAt({ x: p.x, y: p.y + 1 }, 4.2, 2.2, "#dcdad2");
  ellipseAt(p, 4, 2.2, "#ffffff");
  ellipseAt({ x: p.x, y: p.y - 0.2 }, 2.8, 1.4, "#5b3b26");
}

// ---- counters ----------------------------------------------------------------------------------

// a counter: a body in the colour of its place, a stone top that sticks out a little at the front
const COUNTERS = {
  "cafe-counter": { top: "#ebe3d4", body: "#c99a62", front: "slats" },
  "supply-counter": { top: "#ddc08a", body: "#31545b", front: "panel" },
  "student-counter": { top: "#f3f1ea", body: "#2b6070", front: "glass" },
};

function drawCounterSlice(item, x, w) {
  const style = COUNTERS[item.id];
  const front = item.y + item.h + 0.01;
  drawBlock(x, item.y, w, item.h, 30, style.body, dark(style.body, 0.3), dark(style.body, 0.12));
  if (style.front === "slats") {
    ctx.strokeStyle = "rgba(90,55,25,.38)";
    ctx.lineWidth = 1;
    for (let px = x + 0.1; px < x + w - 0.04; px += 0.2) {
      const a = isoPoint(px, front, 4);
      const b = isoPoint(px, front, 27);
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.stroke();
    }
  } else if (style.front === "panel") {
    drawFacadeBandY(x + 0.06, front, w - 0.12, 5, 22, "#244e58", 1);
    drawFacadeBandY(x + 0.06, front, w - 0.12, 22, 25, SUN, 1);
  } else {
    drawFacadeBandY(x + 0.06, front, w - 0.12, 5, 26, "rgba(150,205,225,.82)", 2);
    drawFacadeBandY(x + 0.06, front, w - 0.12, 26, 28, "#ffffff", 1);
  }
  const [top, east, south] = shades(style.top);
  drawRaisedSlab(x - 0.02, item.y - 0.03, w + 0.04, item.h + 0.14, 34, 4, top, east, south);
}

function drawCartons(item) {
  const y = item.y;
  drawRaisedSlab(item.x + 0.15, y + 0.12, 0.55, 0.5, 46, 12, "#c9a26b", "#8d6c42", "#a98457");
  drawRaisedSlab(item.x + 0.78, y + 0.18, 0.5, 0.42, 43, 9, "#d8b47a", "#9a7849", "#b89158");
  drawRaisedSlab(item.x + 0.25, y + 0.17, 0.34, 0.34, 56, 10, "#bd9660", "#80603a", "#9b7a4d");
  const tape = isoPoint(item.x + 0.425, y + 0.37, 56);
  ctx.fillStyle = "rgba(245,201,94,.9)";
  ctx.fillRect(tape.x - 3, tape.y - 1.5, 6, 3);
}

function drawStudentScreens(item) {
  for (let i = 0; i < 3; i++) {
    const p = isoPoint(item.x + 0.55 + i * (item.w / 3), item.y + 0.4, 34);
    ctx.fillStyle = "#c9cdd0";
    ctx.fillRect(p.x - 1, p.y - 3, 2, 5);
    roundedRect(p.x - 10, p.y - 17, 20, 15, 2, INK);
    ctx.fillStyle = LIME;
    ctx.fillRect(p.x - 6, p.y - 13, 12, 2);
    ctx.fillStyle = AQUA;
    ctx.fillRect(p.x - 6, p.y - 9, 8, 2);
    ctx.fillStyle = "rgba(255,255,255,.18)";
    ctx.fillRect(p.x - 6, p.y - 5, 10, 1.5);
  }
}

// ---- tables ----------------------------------------------------------------------------------

function drawTableSlice(item, x, w, index, count) {
  const [top, east, south] = shades("#e3bd85");
  const leg = (px, py) => drawBlock(px, py, 0.09, 0.09, 24, "#274a52", "#1b363c", "#22434b");
  if (index === 0) leg(x + 0.1, item.y + item.h - 0.17);
  if (index === count - 1) leg(x + w - 0.19, item.y + item.h - 0.17);
  drawRaisedSlab(x, item.y, w, item.h, 28, 4, top, east, south);
  if (index === 0) drawCup(x + 0.45, item.y + 0.32, 28);
  if (index === count - 1) {
    const plate = isoPoint(x + w - 0.45, item.y + 0.36, 28);
    ellipseAt(plate, 5, 2.6, "#f3f1ea");
    ellipseAt({ x: plate.x, y: plate.y - 0.8 }, 3, 1.6, "#d9a35a");
  }
}

// ---- the staircase to the gallery --------------------------------------------------------------

function drawStaircase(item) {
  const steps = 6;
  const depth = item.h / steps;
  for (let i = 0; i < steps; i++) {
    const z = 8 + (steps - 1 - i) * ((GALLERY_Z - 8) / (steps - 1));
    drawBlock(item.x, item.y + i * depth, item.w, depth, z, "#f4f3ef", "#c4c9cb", "#e0e2e0");
    floorLine(item.x, item.y + i * depth + depth, item.x + item.w, item.y + i * depth + depth, "rgba(20,61,66,.18)", 0.8, z);
  }
  // a glass balustrade with a handrail along the open side
  const rail = 14;
  const a = isoPoint(item.x + item.w, item.y, GALLERY_Z + rail);
  const b = isoPoint(item.x + item.w, item.y + item.h, 8 + rail);
  drawPlane(
    [a, b, isoPoint(item.x + item.w, item.y + item.h, 8), isoPoint(item.x + item.w, item.y, GALLERY_Z)],
    "rgba(160,205,225,.38)",
    "rgba(255,255,255,.55)",
    0.9,
  );
  ctx.strokeStyle = "#ffffff";
  ctx.lineWidth = 2.2;
  ctx.beginPath();
  ctx.moveTo(a.x, a.y);
  ctx.lineTo(b.x, b.y);
  ctx.stroke();
}

// ---- merchandise -------------------------------------------------------------------------------

function drawMerchShelfSlice(item, x, w, index) {
  const [top, east, south] = shades("#f1efe7");
  drawBlock(x, item.y, w, item.h, 62, top, east, south);
  const front = item.y + item.h + 0.01;
  drawFacadeBandY(x + 0.06, front, w - 0.12, 40, 57, "#c9c3b3", 1);
  drawFacadeBandY(x + 0.06, front, w - 0.12, 21, 37, "#c9c3b3", 1);
  drawFacadeBandY(x + 0.06, front, w - 0.12, 4, 18, TEAL, 2);
  // folded shirts, mugs and caps
  for (const [row, floor] of [[0, 40], [1, 21]]) {
    for (let k = 0; k < 2; k++) {
      const p = isoPoint(x + w * (0.28 + k * 0.46), item.y + item.h * 0.75, floor);
      const layers = 3 + ((index + k + row) % 2);
      for (let layer = 0; layer < layers; layer++) {
        ctx.fillStyle = ACCENTS[(index * 2 + k + row * 3 + layer) % ACCENTS.length];
        ctx.fillRect(p.x - 6, p.y - 3.2 * (layer + 1), 12, 3);
      }
    }
    const mug = isoPoint(x + w * 0.5, item.y + item.h * 0.75, floor);
    if ((index + row) % 2 === 0) {
      ctx.fillStyle = "#ffffff";
      ctx.fillRect(mug.x - 2.5, mug.y - 7, 5, 7);
    }
  }
}

function drawDisplayTableSlice(item, x, w, index) {
  const leg = (px, py) => drawBlock(px, py, 0.09, 0.09, 20, "#31545b", "#1f3c43", "#294a51");
  if (index === 0) leg(x + 0.1, item.y + item.h - 0.17);
  leg(x + w - 0.19, item.y + item.h - 0.17);
  drawRaisedSlab(x, item.y, w, item.h, 24, 5, "#efebe0", "#8d9a96", "#b3bcb8");
  const color = ACCENTS[(index + 1) % ACCENTS.length];
  drawRaisedSlab(x + w * 0.22, item.y + 0.17, w * 0.5, 0.42, 40, 16, light(color, 0.15), dark(color, 0.35), dark(color, 0.2));
  const label = isoPoint(x + w * 0.47, item.y + 0.6, 30);
  ctx.fillStyle = "rgba(255,255,255,.5)";
  ctx.fillRect(label.x - 3, label.y - 2, 6, 2);
}

// a garment rack: a rail on two posts with shirts hanging from it
function drawRackSlice(item, x, w, index, count) {
  const rail = 52;
  const midY = item.y + item.h / 2;
  ctx.strokeStyle = TEAL;
  ctx.lineWidth = 2;
  const post = (px) => {
    const a = isoPoint(px, midY, FLOOR_Z);
    const b = isoPoint(px, midY, rail);
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();
  };
  if (index === 0) post(x + 0.08);
  if (index === count - 1) post(x + w - 0.08);
  for (let k = 0; k < 4; k++) {
    const p = isoPoint(x + 0.12 + ((w - 0.24) * (k + 0.5)) / 4, midY, rail);
    const color = ACCENTS[(index * 4 + k) % ACCENTS.length];
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.moveTo(p.x - 6, p.y + 2);
    ctx.lineTo(p.x - 2, p.y - 1);
    ctx.lineTo(p.x + 2, p.y - 1);
    ctx.lineTo(p.x + 6, p.y + 2);
    ctx.lineTo(p.x + 4.5, p.y + 6);
    ctx.lineTo(p.x + 3.5, p.y + 4.5);
    ctx.lineTo(p.x + 3.5, p.y + 20);
    ctx.lineTo(p.x - 3.5, p.y + 20);
    ctx.lineTo(p.x - 3.5, p.y + 4.5);
    ctx.lineTo(p.x - 4.5, p.y + 6);
    ctx.closePath();
    ctx.fill();
    ctx.fillStyle = "rgba(0,0,0,.12)";
    ctx.fillRect(p.x, p.y - 1, 3.5, 21);
  }
  ctx.strokeStyle = TEAL;
  ctx.lineWidth = 2.2;
  const a = isoPoint(x, midY, rail);
  const b = isoPoint(x + w, midY, rail);
  ctx.beginPath();
  ctx.moveTo(a.x, a.y);
  ctx.lineTo(b.x, b.y);
  ctx.stroke();
  const feet = [index === 0 ? x : null, index === count - 1 ? x + w - 0.16 : null].filter((v) => v !== null);
  for (const fx of feet) drawBlock(fx, item.y, 0.16, item.h, 5, "#31545b", "#1f3c43", "#294a51");
}

// ---- the print corner -------------------------------------------------------------------------

function drawPrinter(item) {
  drawBlock(item.x, item.y, item.w, item.h, 26, "#f2f2ee", "#b9bec0", "#d6d9d8");
  // the lid, the paper tray at the front and a stack of paper
  drawRaisedSlab(item.x + 0.05, item.y + 0.05, item.w - 0.1, item.h * 0.6, 29, 3, "#dfe2e1", "#a9afb1", "#c5c9c8");
  drawRaisedSlab(item.x + 0.12, item.y + item.h, item.w - 0.24, 0.26, 17, 3, "#ffffff", "#c9cdd0", "#e4e5e2");
  const paper = isoPoint(item.x + item.w * 0.5, item.y + item.h + 0.12, 18.5);
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(paper.x - 6, paper.y - 3, 12, 3);
  const panel = isoPoint(item.x + item.w * 0.5, item.y + item.h + 0.01, 20);
  roundedRect(panel.x - 8, panel.y - 7, 16, 8, 2, INK);
  // the middle machine is out of paper: a red light
  ctx.fillStyle = item.id === "printer-2" ? CORAL : LIME;
  ctx.beginPath();
  ctx.arc(panel.x + 4.5, panel.y - 3, 1.6, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = AQUA;
  ctx.fillRect(panel.x - 6, panel.y - 5.5, 7, 2);
}

// ---- people ------------------------------------------------------------------------------------

const SHIRTS = ["#f5c95e", "#ff8060", "#64cbc8", "#9a7bc1", "#bce65f", "#f0e9dc", "#e6a769"];

// the people in the rooms, and what they are doing once the player comes close
function drawRoomPerson(activity, t, index) {
  drawPersonFigure(activity.x, activity.y, t, index + 140, {
    color: SHIRTS[index % SHIRTS.length],
    phase: index * 0.7,
    moving: activity.pose === "repair",
    facing: activity.facing,
    pose: activity.pose,
    role: activity.role,
  });
  if (Math.hypot(scene.player.x - activity.x, scene.player.y - activity.y) < 2.15) {
    const p = isoPoint(activity.x, activity.y, 67);
    roundedRect(p.x - 31, p.y - 6, 62, 12, 5, "rgba(12,39,47,.9)");
    ctx.fillStyle = activity.role ? "#f5c95e" : "#dff4ef";
    ctx.textAlign = "center";
    ctx.font = "800 4.7px Menlo, Consolas, monospace";
    ctx.fillText(activity.label.toUpperCase(), p.x, p.y + 1.5);
  }
}

// ---- everything in the rooms, ready to be sorted with the rest of the scene -------------------

// a wide piece is drawn in slices; a person next to it sorts against the slice beside them
function sliced(item, maxWidth, drawSlice) {
  const count = Math.max(1, Math.ceil(item.w / maxWidth));
  const width = item.w / count;
  return Array.from({ length: count }, (_, i) => {
    const x = item.x + i * width;
    return { depth: x + width / 2 + item.y + item.h + 0.01, draw: () => drawSlice(x, width, i, count) };
  });
}

// something that stands on a sliced piece sorts after the slice below it
const onTop = (x, item) => x + 0.6 + item.y + item.h + 0.03;

// depth of a single small object: its front edge, a little beyond
const frontDepth = (item) => item.x + item.w / 2 + item.y + item.h + 0.3;

// stools around a table: two on each side
function tableStools(item) {
  const spots = [];
  for (const x of [item.x + 0.5, item.x + item.w - 0.5]) {
    spots.push({ x, y: item.y - 0.35, depth: x + item.y - 0.35 });
    spots.push({ x, y: item.y + item.h + 0.35, depth: x + item.y + item.h + 0.35 });
  }
  return spots;
}

export function roomActors(t) {
  const actors = [];
  for (const item of layout().solid) {
    const id = item.id;
    if (id === "cafe-shelf") {
      actors.push(...sliced(item, 1.1, (x, w, i) => drawCafeShelfSlice(item, x, w, i)));
      actors.push({ depth: onTop(item.x + 2.7, item), draw: () => drawEspressoMachine(item.x + 2.7, item.y + item.h * 0.5) });
      actors.push({ depth: onTop(item.x + 1.1, item), draw: () => drawCup(item.x + 1.1, item.y + item.h * 0.5, 28) });
      actors.push({ depth: onTop(item.x + 4.3, item), draw: () => drawCup(item.x + 4.3, item.y + item.h * 0.5, 28) });
    } else if (id in COUNTERS) {
      actors.push(...sliced(item, 1.1, (x, w) => drawCounterSlice(item, x, w)));
      if (id === "cafe-counter") {
        for (const px of [item.x + 0.7, item.x + 2.1, item.x + 4.6]) {
          actors.push({ depth: onTop(px, item), draw: () => drawCup(px, item.y + item.h * 0.45, 34) });
        }
        // the bar stools in front of it
        for (const px of [item.x + 0.7, item.x + 1.9, item.x + 3.9, item.x + 5.1]) {
          actors.push({ depth: px + item.y + item.h + 0.5, draw: () => drawStool(px, item.y + item.h + 0.45, 22, CORAL) });
        }
      }
      if (id === "supply-counter") actors.push({ depth: onTop(item.x + 1.3, item), draw: () => drawCartons(item) });
      if (id === "student-counter") actors.push({ depth: onTop(item.x + item.w - 0.3, item), draw: () => drawStudentScreens(item) });
    } else if (id.startsWith("cafe-table")) {
      actors.push(...sliced(item, 0.95, (x, w, i, n) => drawTableSlice(item, x, w, i, n)));
      for (const spot of tableStools(item)) {
        actors.push({ depth: spot.depth, draw: () => drawStool(spot.x, spot.y, 14, TEAL) });
      }
    } else if (id === "staircase") {
      actors.push({ depth: frontDepth(item), draw: () => drawStaircase(item) });
    } else if (id.startsWith("atrium-bench")) {
      actors.push(...sliced(item, 0.95, (x, w, i, n) => drawBenchSlice(item, x, w, i, n)));
    } else if (id === "merch-shelf") {
      actors.push(...sliced(item, 1.25, (x, w, i) => drawMerchShelfSlice(item, x, w, i)));
    } else if (id === "merch-table") {
      actors.push(...sliced(item, 0.95, (x, w, i) => drawDisplayTableSlice(item, x, w, i)));
    } else if (id === "merch-rack") {
      actors.push(...sliced(item, 0.95, (x, w, i, n) => drawRackSlice(item, x, w, i, n)));
    } else if (id.startsWith("printer")) {
      actors.push({ depth: frontDepth(item) + 0.3, draw: () => drawPrinter(item) });
    } else if (id.startsWith("column")) {
      actors.push({ depth: item.x + item.y + 0.2, draw: () => drawColumn(item) });
    } else if (id.includes("plant")) {
      const scale = 0.9 + item.r * 0.9;
      actors.push({ depth: item.x + item.y + 0.3, draw: () => drawIndoorPlant(item.x, item.y, scale) });
    }
  }
  layout().activities.forEach((activity, index) => {
    actors.push({ depth: activity.x + activity.y + 0.03, draw: () => drawRoomPerson(activity, t, index) });
  });
  return actors;
}
