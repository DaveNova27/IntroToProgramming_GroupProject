// The rooms inside the Nova and its wings: the floor, the furniture, the shops and the people.
// Drawing code started from Felix Antes' Nova Beach Ventures
// (https://github.com/felix-anthes-png/nova-beach-ventures) and was redrawn for the walk-in Nova.
// All of it is placed from the data in world.py (world.interiors.campus). Drawing only.
//
// The camera looks from the south (spec map-view), so the front that shows is the south face:
// counters and shelves stand against the north and west walls. Everything wider than about a
// tile is drawn in slices. The draw order goes by the front edge (y), so the slices along y (pieces
// against a side wall) sort a person beside them right; the slices along x all share one front edge
// and only keep their old shape (see "Known issues" in specs/map-view.md).

import { drawPersonFigure } from "./people.js";
import { drawBlock, drawFacadeBandX, drawFacadeBandY, drawPlane, drawRaisedSlab, mixColor, roundedRect } from "./primitives.js";
import { DAY_END, DAY_START, DEPTH, TILE, ctx, depthOf, isoPoint, roofOf, scene, server, wingIsOpen, world } from "./scene.js";

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

const areasOf = (wingId) => layout().areas.filter((area) => area.wing === wingId);
const solidsOf = (wingId) => layout().solid.filter((item) => item.wing === wingId);

// the walkable floor of a wing: the box around its places (they split it between them)
export function floorBounds(wingId = "nova") {
  const areas = areasOf(wingId);
  const x0 = Math.min(...areas.map((a) => a.x));
  const y0 = Math.min(...areas.map((a) => a.y));
  const x1 = Math.max(...areas.map((a) => a.x + a.w));
  const y1 = Math.max(...areas.map((a) => a.y + a.h));
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
  ctx.beginPath();
  ctx.ellipse(p.x, p.y, radius * TILE, radius * DEPTH, 0, 0, Math.PI * 2);
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
function paintCafeFloor(area, base = "#dcc59b") {
  floorQuad(area.x, area.y, area.w, area.h, base);
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

// the Learning Center: grey-green carpet, a rug under the long tables; timber with a rug for the seminar
function paintStudyFloor(area) {
  floorQuad(area.x, area.y, area.w, area.h, "#c9d6d3");
  for (let y = area.y + 0.5; y < area.y + area.h; y += 0.5) floorLine(area.x, y, area.x + area.w, y, "rgba(49,84,91,.1)", 0.8);
  const tables = solidsOf(area.wing).filter((item) => item.id.startsWith("study-table"));
  if (tables.length) {
    const x0 = Math.min(...tables.map((t) => t.x)) - 0.45;
    const x1 = Math.max(...tables.map((t) => t.x + t.w)) + 0.45;
    const y0 = Math.min(...tables.map((t) => t.y)) - 0.7;
    const y1 = Math.max(...tables.map((t) => t.y + t.h)) + 0.7;
    floorQuad(x0, y0, x1 - x0, y1 - y0, "rgba(100,203,200,.26)");
    floorLine(x0, y0, x1, y0, "rgba(49,84,91,.3)", 1.4);
    floorLine(x1, y0, x1, y1, "rgba(49,84,91,.3)", 1.4);
    floorLine(x1, y1, x0, y1, "rgba(49,84,91,.3)", 1.4);
    floorLine(x0, y1, x0, y0, "rgba(49,84,91,.3)", 1.4);
  }
}

function paintSeminarFloor(area) {
  paintCafeFloor(area, "#d9c4a2");
  const table = solidsOf(area.wing).find((item) => item.id === "seminar-table");
  if (table) {
    floorRing(table.x + table.w / 2, table.y + table.h / 2, 1.5, "rgba(154,123,193,.5)", 1.6, "rgba(154,123,193,.17)");
    floorRing(table.x + table.w / 2, table.y + table.h / 2, 1.1, "rgba(154,123,193,.4)", 1);
  }
}

// the Mercado: concrete, joints, and yellow lines along the aisle
function paintSupplyFloor(area) {
  floorQuad(area.x, area.y, area.w, area.h, "#cfd0cb");
  for (let x = area.x + 1.8; x < area.x + area.w; x += 1.8) floorLine(x, area.y, x, area.y + area.h, "rgba(20,61,66,.1)", 0.7);
  for (let y = area.y + 1.8; y < area.y + area.h; y += 1.8) floorLine(area.x, y, area.x + area.w, y, "rgba(20,61,66,.1)", 0.7);
  const entrance = world.nova.entrances.find((e) => e.wing === area.wing);
  if (entrance) {
    for (const x of [entrance.x - 0.05, entrance.x + entrance.width + 0.05]) {
      floorLine(x, area.y + 0.15, x, area.y + area.h, "rgba(241,201,75,.85)", 2);
    }
  }
}

// the Student Hub: a warm carpet with a big rug in the lounge, a cool one in the meeting room
function paintLoungeFloor(area) {
  floorQuad(area.x, area.y, area.w, area.h, "#efddd2");
  floorQuad(area.x + 1.3, area.y + 0.5, area.w - 2.6, area.h - 0.9, "rgba(255,123,91,.2)");
  floorLine(area.x + 1.3, area.y + 0.5, area.x + area.w - 1.3, area.y + 0.5, "rgba(255,123,91,.45)", 1.4);
  floorLine(area.x + 1.3, area.y + area.h - 0.4, area.x + area.w - 1.3, area.y + area.h - 0.4, "rgba(255,123,91,.45)", 1.4);
}

function paintMeetingFloor(area) {
  floorQuad(area.x, area.y, area.w, area.h, "#d3dfe0");
  for (let x = area.x + 1; x < area.x + area.w; x += 1) floorLine(x, area.y, x, area.y + area.h, "rgba(49,84,91,.08)", 0.7);
}

// the Dorm (spec nova-zones): timber, a teal rug at the foot of the bed
function paintBedroomFloor(area) {
  paintCafeFloor(area, "#dcc4a0");
  floorQuad(area.x + 0.7, 10.35, 1.7, 1.55, "rgba(100,203,200,.34)");
  for (const [x1, y1, x2, y2] of [[0, 0, 1, 0], [1, 0, 1, 1], [1, 1, 0, 1], [0, 1, 0, 0]]) {
    floorLine(area.x + 0.7 + x1 * 1.7, 10.35 + y1 * 1.55, area.x + 0.7 + x2 * 1.7, 10.35 + y2 * 1.55, "rgba(49,84,91,.4)", 1.2);
  }
}

const FLOORS = {
  "dorm-sleep": paintBedroomFloor,
  "dorm-desk": (area) => paintCafeFloor(area, "#d6bd9b"),
  cafe: paintCafeFloor, atrium: paintAtriumFloor, merch: paintMerchFloor, print: paintPrintFloor,
  study: paintStudyFloor, seminar: paintSeminarFloor, supply: paintSupplyFloor,
  lounge: paintLoungeFloor, meeting: paintMeetingFloor,
};

// the mat inside an entrance
function paintEntranceMat(wingId) {
  for (const door of world.nova.entrances.filter((entrance) => entrance.wing === wingId)) {
    const inset = door.width >= 3 ? 0.7 : 0.3;
    const x = door.x + inset;
    const w = door.width - 2 * inset;
    const y = door.y - 0.7;
    floorQuad(x, y, w, 0.6, "#3b5d65");
    for (let i = 1; i < 8; i++) floorLine(x + (w * i) / 8, y, x + (w * i) / 8, y + 0.6, "rgba(255,255,255,.18)", 0.8);
  }
}

// patches of light from the windows in the north wall, moving with the time of day
const LIT_FROM_THE_NORTH = ["nova", "learning-center", "dorm"];

function paintWindowLight(wingId) {
  if (!LIT_FROM_THE_NORTH.includes(wingId)) return;
  const { x, y, w } = floorBounds(wingId);
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
function paintContactShadows(wingId) {
  ctx.save();
  for (const item of solidsOf(wingId)) {
    if ("r" in item) {
      ellipseAt(isoPoint(item.x + 0.08, item.y + 0.1, FLOOR_Z + 0.1), item.r * 62, item.r * 31, "rgba(10,30,36,.16)");
    } else {
      floorQuad(item.x + 0.02, item.y + 0.06, item.w + 0.16, item.h + 0.16, "rgba(10,30,36,.15)", FLOOR_Z + 0.1);
    }
  }
  ctx.restore();
}

// along the north and west wall the floor darkens a little
function paintWallEdges(wingId) {
  const { x, y, w, h } = floorBounds(wingId);
  floorQuad(x, y, w, 0.32, "rgba(20,45,52,.1)");
  floorQuad(x, y, 0.32, h, "rgba(20,45,52,.08)");
}

export function drawInteriorFloor(wingId = "nova") {
  const floor = floorBounds(wingId);
  floorQuad(floor.x, floor.y, floor.w, floor.h, layout().floor);
  for (const area of areasOf(wingId)) FLOORS[area.id]?.(area);
  paintEntranceMat(wingId);
  paintWallEdges(wingId);
  paintWindowLight(wingId);
  paintContactShadows(wingId);
}

// the names of the places, written on the floor, and the marked way in
export function drawInteriorWayfinding(wingId = "nova") {
  ctx.save();
  for (const area of areasOf(wingId)) {
    const at = area.labelAt ?? { x: area.x + 0.4, y: area.y + area.h - 0.5 };
    const text = area.label.toUpperCase();
    const p = isoPoint(at.x, at.y, FLOOR_Z + 1);
    ctx.save();
    ctx.translate(p.x, p.y);
    ctx.textAlign = "left";
    ctx.font = "800 6.5px Menlo, Consolas, monospace";
    ctx.fillStyle = INK;
    ctx.globalAlpha = 0.74;
    ctx.fillText(text, 0, 0);
    ctx.restore();
    floorLine(at.x, at.y + 0.17, at.x + 0.16 * text.length + 0.2, at.y + 0.17, area.color, 3, FLOOR_Z + 0.5);
  }
  const { route } = layout();
  if (wingId !== "nova") {
    ctx.restore();
    return; // the marked way in leads through the main entrance
  }
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
  const height = 36 + 42 * roofOf(item.wing);
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

// ---- the Learning Center ------------------------------------------------------------------------

const BOOKS = ["#c46a52", "#4f7fa0", "#d9b84f", "#5b9a74", "#8f6bb0", "#e8e1d0", "#2f4d5a"];

// a bookshelf wall on the north wall: dark back, planks, rows of books
function drawBookshelfSlice(item, x, w, index) {
  const [top, east, south] = shades("#d9b987");
  drawBlock(x, item.y, w, item.h, 58, top, east, south);
  const front = item.y + item.h + 0.01;
  drawFacadeBandY(x + 0.04, front, w - 0.08, 3, 55, "#7b5a3a", 1);
  for (const z of [17, 31, 45]) drawRaisedSlab(x, item.y, w, item.h, z, 2, "#d9b987", "#a98a58", "#c3a572");
  const count = Math.max(3, Math.round(w / 0.17));
  [4, 17, 31, 45].forEach((floor, row) => {
    for (let k = 0; k < count; k++) {
      if ((index * 3 + k * 2 + row) % 7 === 0) continue; // a gap now and then
      const tall = 7 + ((index * 5 + k * 3 + row * 2) % 4) * 1.6;
      const p = isoPoint(x + ((k + 0.5) * w) / count, item.y + item.h * 0.8, floor);
      ctx.fillStyle = BOOKS[(index * 7 + k + row * 3) % BOOKS.length];
      ctx.fillRect(p.x - 1.6, p.y - tall, 3.2, tall);
      ctx.fillStyle = "rgba(0,0,0,.14)";
      ctx.fillRect(p.x + 0.3, p.y - tall, 1.3, tall);
    }
  });
}

function drawLaptop(x, y, z) {
  const p = isoPoint(x, y, z);
  roundedRect(p.x - 7, p.y - 2, 14, 5, 1.5, "#cfd3d3");
  ctx.fillStyle = INK;
  ctx.fillRect(p.x - 6, p.y - 13, 12, 10);
  ctx.fillStyle = AQUA;
  ctx.fillRect(p.x - 4.5, p.y - 10.5, 6, 1.6);
  ctx.fillStyle = LIME;
  ctx.fillRect(p.x - 4.5, p.y - 7.5, 8, 1.6);
}

function drawDeskLamp(x, y, z) {
  const base = isoPoint(x, y, z);
  const top = isoPoint(x, y, z + 15);
  ctx.strokeStyle = TEAL;
  ctx.lineWidth = 1.8;
  ctx.beginPath();
  ctx.moveTo(base.x, base.y);
  ctx.lineTo(top.x, top.y);
  ctx.stroke();
  ellipseAt({ x: top.x + 2, y: top.y + 1 }, 5, 2.6, CORAL);
  ellipseAt({ x: base.x, y: base.y + 0.5 }, 4, 2, "rgba(34,67,75,.6)");
}

function drawOpenBook(x, y, z) {
  const p = isoPoint(x, y, z);
  ctx.fillStyle = "#f6f3ea";
  ctx.beginPath();
  ctx.moveTo(p.x - 7, p.y);
  ctx.lineTo(p.x, p.y - 3);
  ctx.lineTo(p.x + 7, p.y);
  ctx.lineTo(p.x, p.y + 3);
  ctx.closePath();
  ctx.fill();
  ctx.strokeStyle = "rgba(49,84,91,.4)";
  ctx.lineWidth = 0.8;
  ctx.beginPath();
  ctx.moveTo(p.x, p.y - 3);
  ctx.lineTo(p.x, p.y + 3);
  ctx.stroke();
}

// a long study table: laptops at one end, a lamp and an open book at the other
function drawStudyTableSlice(item, x, w, index, count) {
  const [top, east, south] = shades("#eee8d9");
  const leg = (px, py) => drawBlock(px, py, 0.09, 0.09, 24, "#274a52", "#1b363c", "#22434b");
  if (index === 0) leg(x + 0.1, item.y + item.h - 0.17);
  if (index === count - 1) leg(x + w - 0.19, item.y + item.h - 0.17);
  drawRaisedSlab(x, item.y, w, item.h, 28, 4, top, east, south);
  if (index === 0) drawLaptop(x + 0.5, item.y + 0.4, 28);
  if (index === count - 1) {
    drawDeskLamp(x + w - 0.3, item.y + 0.3, 28);
    drawOpenBook(x + w - 0.75, item.y + 0.5, 28);
  }
}

// the seminar table in the corner: a lilac top, papers and a cup
function drawSeminarTable(item) {
  const leg = (px, py) => drawBlock(px, py, 0.1, 0.1, 24, "#274a52", "#1b363c", "#22434b");
  leg(item.x + 0.1, item.y + item.h - 0.2);
  leg(item.x + item.w - 0.2, item.y + item.h - 0.2);
  drawRaisedSlab(item.x, item.y, item.w, item.h, 28, 4, "#d9cbe6", "#8f7fa3", "#b6a8c7");
  drawOpenBook(item.x + 0.4, item.y + 0.45, 28);
  drawOpenBook(item.x + 0.8, item.y + 0.7, 28);
  drawCup(item.x + item.w - 0.3, item.y + 0.35, 28);
}

// ---- the Mercado ----------------------------------------------------------------------------------

const CARTONS = ["#c9a26b", "#d8b47a", "#bd9660", "#cfa970"];

// a steel rack on the west wall: back panel, four shelves with cartons, uprights at the ends
function drawStorageRackSlice(item, y, length, index) {
  const x = item.x;
  drawBlock(x, y, 0.1, length, 76, "#aeb6b9", "#8f989b", "#9ea6a9");
  const shelves = [8, 28, 48, 68];
  shelves.forEach((z, level) => {
    drawRaisedSlab(x, y, item.w, length, z, 2.5, "#dfe3e3", "#9ba4a7", "#c1c7c8");
    const boxes = Math.max(1, Math.round(length / 0.5));
    for (let k = 0; k < boxes; k++) {
      if ((index * 2 + k + level) % 5 === 0) continue;
      const tall = 9 + ((index + k * 2 + level) % 3) * 2;
      const by = y + 0.05 + (k * (length - 0.1)) / boxes;
      const color = CARTONS[(index * 3 + k + level) % CARTONS.length];
      drawRaisedSlab(x + 0.14, by, item.w - 0.28, (length - 0.1) / boxes - 0.05, z + tall, tall, color, dark(color, 0.3), dark(color, 0.16));
    }
  });
  const post = (py) => drawBlock(x + item.w - 0.08, py, 0.08, 0.08, 76, "#31545b", "#1f3c43", "#294a51");
  if (index === 0) post(y);
  post(y + length - 0.08);
}

// a pallet with two layers of cartons and a strip of tape on each
function drawPallet(item) {
  drawBlock(item.x, item.y, item.w, item.h, 6, "#b88b55", "#8a6740", "#a17747");
  const bw = (item.w - 0.18) / 2;
  const bh = (item.h - 0.15) / 2;
  const layers = [
    { z: 22, offset: 0.06, rows: [0, 1], cols: [0, 1] },
    { z: 38, offset: 0.06 + bw / 2, rows: [0, 1], cols: [0] },
  ];
  let n = 0;
  for (const layer of layers) {
    for (const row of layer.rows) {
      for (const col of layer.cols) {
        const bx = item.x + layer.offset + col * (bw + 0.06);
        const by = item.y + 0.05 + row * (bh + 0.05);
        const color = CARTONS[(n++ + (item.x > 5 ? 1 : 0)) % CARTONS.length];
        drawRaisedSlab(bx, by, bw, bh, layer.z, 16, color, dark(color, 0.3), dark(color, 0.16));
        const tape = isoPoint(bx + bw / 2, by + bh, layer.z - 7);
        ctx.fillStyle = "rgba(245,201,94,.92)";
        ctx.fillRect(tape.x - 3, tape.y - 1, 6, 2);
      }
    }
  }
}

// plastic crates, two high
function drawCrates(item) {
  const colors = [SUN, AQUA, SUN];
  const width = (item.w - 0.12) / 3;
  colors.forEach((color, i) => {
    const bx = item.x + 0.03 + i * (width + 0.03);
    drawRaisedSlab(bx, item.y + 0.05, width, item.h - 0.1, 18, 18, color, dark(color, 0.32), dark(color, 0.16));
    drawFacadeBandY(bx + 0.04, item.y + item.h - 0.04, width - 0.08, 5, 8, dark(color, 0.3), 1);
    if (i !== 1) {
      drawRaisedSlab(bx + 0.03, item.y + 0.1, width - 0.06, item.h - 0.2, 36, 16, light(color, 0.1), dark(color, 0.3), dark(color, 0.14));
      drawFacadeBandY(bx + 0.07, item.y + item.h - 0.09, width - 0.14, 23, 26, dark(color, 0.3), 1);
    }
  });
}

// ---- the Student Hub -------------------------------------------------------------------------------

// a sofa along a side wall, drawn in slices along its length; its back is at the wall
function drawSofaSlice(item, y, length, index, count) {
  const west = item.x < 30;
  const color = west ? CORAL : "#3d8c94";
  const back = 0.3;
  const seatX = west ? item.x + back : item.x;
  const backX = west ? item.x : item.x + item.w - back;
  drawBlock(seatX, y, item.w - back, length, 17, light(color, 0.18), dark(color, 0.3), dark(color, 0.14));
  drawBlock(backX, y, back, length, 32, color, dark(color, 0.34), dark(color, 0.18));
  if (index === 0) drawBlock(seatX, y, item.w - back, 0.14, 27, color, dark(color, 0.34), dark(color, 0.18));
  if (index === count - 1) drawBlock(seatX, y + length - 0.14, item.w - back, 0.14, 27, color, dark(color, 0.34), dark(color, 0.18));
  const cushion = isoPoint(seatX + (item.w - back) / 2, y + length / 2, 18);
  ctx.fillStyle = "rgba(255,255,255,.2)";
  ctx.beginPath();
  ctx.ellipse(cushion.x, cushion.y, 5, 2.4, 0, 0, Math.PI * 2);
  ctx.fill();
}

// a charging bar with phones on it
function drawChargingBar(item) {
  drawBlock(item.x, item.y, item.w, item.h, 34, "#2b6070", "#1c4350", "#245566");
  drawFacadeBandY(item.x + 0.06, item.y + item.h + 0.01, item.w - 0.12, 8, 26, "rgba(150,205,225,.55)", 2);
  drawRaisedSlab(item.x - 0.02, item.y - 0.02, item.w + 0.04, item.h + 0.06, 38, 4, "#f3f1ea", "#a6aeab", "#c9cecb");
  [0.3, 0.7].forEach((fy, i) => {
    const p = isoPoint(item.x + item.w / 2, item.y + item.h * fy, 38);
    roundedRect(p.x - 4, p.y - 7, 8, 6, 1.5, INK);
    ctx.fillStyle = i ? LIME : SUN;
    ctx.fillRect(p.x - 2.5, p.y - 5.5, 5, 1.4);
  });
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

// a wide piece is drawn in slices along x; they all sort by the same front edge
function sliced(item, maxWidth, drawSlice) {
  const count = Math.max(1, Math.ceil(item.w / maxWidth));
  const width = item.w / count;
  return Array.from({ length: count }, (_, i) => {
    const x = item.x + i * width;
    return { depth: depthOf(x + width / 2, item.y + item.h + 0.01), draw: () => drawSlice(x, width, i, count) };
  });
}

// the same along y, for pieces that stand against a side wall: each slice sorts by its front end
function slicedY(item, maxLength, drawSlice) {
  const count = Math.max(1, Math.ceil(item.h / maxLength));
  const length = item.h / count;
  return Array.from({ length: count }, (_, i) => {
    const y = item.y + i * length;
    return { depth: depthOf(item.x + item.w, y + length + 0.01), draw: () => drawSlice(y, length, i, count) };
  });
}

// something that stands on a sliced piece sorts after the slice below it
const onTop = (x, item) => depthOf(x + 0.6, item.y + item.h + 0.04);

// depth of a single small object: its front edge, a little beyond
const frontDepth = (item) => depthOf(item.x + item.w / 2, item.y + item.h + 0.3);

// stools around a table: two on each side (only on the north side if the table stands against the south wall)
function tableStools(item, sides = "both") {
  const spots = [];
  for (const x of [item.x + 0.5, item.x + item.w - 0.5]) {
    spots.push({ x, y: item.y - 0.35, depth: depthOf(x, item.y - 0.35) });
    if (sides === "both") spots.push({ x, y: item.y + item.h + 0.35, depth: depthOf(x, item.y + item.h + 0.35) });
  }
  return spots;
}

// ---- the employees (staff) -----------------------------------------------------------------
// Drawn from what the server sent: job, whether they work, and whether the shift is running.
// The spots are data from world.py; a figure only walks between them for show.

const lerp = (a, b, k) => a + (b - a) * k;

function employeeState(employee, t, index) {
  const spots = world.work_spots?.[employee.shop];
  if (!spots) return null;
  const shift = server.shift;
  const busy = employee.working && shift && shift.shop === employee.shop && !shift.over;
  const rest = spots.break[index % spots.break.length];
  if (!busy) return { x: rest.x, y: rest.y, pose: "idle", moving: false, facing: { x: 0, y: 1 }, spots };
  if (employee.job === "seller") {
    return { x: spots.seller.x, y: spots.seller.y, pose: "service", role: "service", moving: false, facing: { x: 0, y: 1 }, spots };
  }
  // a refiller carries stock from the storeroom to the counter and walks back for more. He only
  // does it while the server has stock to carry and room on the counter; the speed follows the level
  const from = spots.storeroom, to = spots.counter;
  const room = shift.counter_space > 0 && server.storeroom > 0;
  if (!room) return { x: from.x, y: from.y, pose: "idle", role: "technician", moving: false, facing: { x: 0, y: 1 }, spots };
  const period = 5200 / employee.level;
  const u = ((t + employee.id * 770) % period) / period; // 0..1
  const out = u < 0.5; // going to the counter with the stock
  const k = out ? u * 2 : (1 - u) * 2;
  const pause = k < 0.05 || k > 0.95;
  return {
    x: lerp(from.x, to.x, k), y: lerp(from.y, to.y, k), pose: "walk", role: "technician",
    moving: !pause, carrying: out && !pause, facing: { x: out ? -1 : 1, y: 0 }, spots,
  };
}

function drawEmployee(employee, t, index) {
  const view = employeeState(employee, t, index);
  if (!view) return;
  drawPersonFigure(view.x, view.y, t, employee.id + 30, {
    color: SHIRTS[(employee.id + 2) % SHIRTS.length],
    phase: employee.id * 0.9,
    moving: view.moving,
    facing: view.facing,
    pose: view.pose,
    role: view.role,
  });
  if (view.carrying) { // the crate he carries to the counter
    const c = isoPoint(view.x, view.y, 30);
    roundedRect(c.x - 6, c.y - 4, 12, 8, 2, "#c89a5b");
    ctx.fillStyle = "#8a6638";
    ctx.fillRect(c.x - 6, c.y - 1, 12, 1.6);
  }
  if (Math.hypot(scene.player.x - view.x, scene.player.y - view.y) < 2.4) {
    const p = isoPoint(view.x, view.y, 67);
    const text = `${employee.name} · ${employee.job_name} L${employee.level}${employee.working ? "" : " · no pay"}`;
    roundedRect(p.x - 46, p.y - 6, 92, 12, 5, "rgba(12,39,47,.9)");
    ctx.fillStyle = employee.working ? "#f5c95e" : "#ff8060";
    ctx.textAlign = "center";
    ctx.font = "800 4.7px Menlo, Consolas, monospace";
    ctx.fillText(text.toUpperCase(), p.x, p.y + 1.5);
  }
}

function employeeActors(t) {
  const staff = server.staff?.employees ?? [];
  const actors = [];
  const perShop = {};
  for (const employee of staff) {
    const spots = world.work_spots?.[employee.shop];
    if (!spots || !wingIsOpen(spots.wing)) continue;
    const index = (perShop[employee.shop] = (perShop[employee.shop] ?? -1) + 1);
    const view = employeeState(employee, t, index);
    if (!view) continue;
    actors.push({ depth: depthOf(view.x, view.y) + 0.03, draw: () => drawEmployee(employee, t, index) });
  }
  return actors;
}

// ---- the Dorm (spec nova-zones) ------------------------------------------------------------------

const BED_WOOD = ["#c99a62", "#8f6a3f", "#a98050"];

// a bed with its head at the north wall: frame, mattress, a blanket over the foot, two pillows
function drawBed(item) {
  drawBlock(item.x, item.y, item.w, item.h, 13, ...BED_WOOD);
  drawBlock(item.x, item.y, item.w, 0.14, 32, ...BED_WOOD); // headboard
  drawRaisedSlab(item.x + 0.07, item.y + 0.14, item.w - 0.14, item.h - 0.2, 19, 5, "#f4efe6", "#c9c6bd", "#dedad0");
  const blanket = item.y + item.h * 0.42;
  drawRaisedSlab(item.x + 0.05, blanket, item.w - 0.1, item.y + item.h - blanket - 0.02, 22, 4, "#ff8a6e", "#c25a42", "#e06d52");
  for (const px of [item.x + item.w * 0.28, item.x + item.w * 0.72]) {
    const p = isoPoint(px, item.y + 0.45, 24);
    ellipseAt(p, 9, 4.4, "#ffffff");
    ctx.strokeStyle = "rgba(49,84,91,.25)";
    ctx.lineWidth = 0.8;
    ctx.beginPath();
    ctx.ellipse(p.x, p.y, 9, 4.4, 0, 0, Math.PI * 2);
    ctx.stroke();
  }
  // a stripe across the blanket and a folded corner
  drawFacadeBandY(item.x + 0.05, item.y + item.h + 0.01, item.w - 0.1, 8, 20, "#e06d52", 1);
  drawFacadeBandY(item.x + 0.05, item.y + item.h + 0.012, item.w - 0.1, 14, 16, "#fff1e6", 1);
}

// a wardrobe against the west wall, its doors facing east, drawn in slices along y
function drawWardrobeSlice(item, y, length, index, count) {
  drawBlock(item.x, y, item.w, length, 62, "#d3b17c", "#8f6a3f", "#b58e5b");
  const face = item.x + item.w + 0.012;
  drawFacadeBandX(face, y + 0.04, length - 0.08, 5, 58, "#c49a62", 1);
  if (index === 0) drawFacadeBandX(face + 0.001, y + 0.02, 0.05, 5, 58, "#7b5a3a", 1);
  const p = isoPoint(face, y + length * (index % 2 ? 0.25 : 0.75), 32);
  ellipseAt(p, 1.4, 1, "#3b2c1c");
  if (index === count - 1) ellipseAt(isoPoint(face, y + length - 0.1, 62), 0.1, 0.1, "#8f6a3f");
}

// a desk against the north wall with a chair; the laptop and the lamp come from the study tables
function drawDormChair(item) {
  const x = item.x + 0.8;
  const y = item.y + item.h + 0.5;
  drawStool(x, y, 17, CORAL);
}

// the pictures on the north wall: a poster over the bed, a cork board with notes over the desk
function drawDormPoster() {
  const x = 35.7;
  drawFacadeBandY(x, 8.12, 1.1, 38, 58, "#173743", 1);
  drawFacadeBandY(x + 0.06, 8.121, 0.98, 41, 55, "#64cbc8", 1);
  const p = isoPoint(x + 0.55, 8.13, 49);
  ctx.strokeStyle = "#ffffff";
  ctx.lineWidth = 1.4;
  ctx.beginPath();
  ctx.moveTo(p.x - 8, p.y + 2);
  ctx.quadraticCurveTo(p.x - 3, p.y - 7, p.x + 1, p.y);
  ctx.quadraticCurveTo(p.x + 4, p.y + 5, p.x + 8, p.y - 3);
  ctx.stroke();
  ellipseAt({ x: p.x + 5, y: p.y - 6 }, 2, 1.5, SUN);
}

function drawDormCorkboard() {
  const x = 38.55;
  drawFacadeBandY(x, 8.12, 1.3, 36, 56, "#7b5a3a", 1);
  drawFacadeBandY(x + 0.05, 8.121, 1.2, 38, 54, "#c99a62", 1);
  [[0.15, 0.2, "#fff6c9"], [0.55, 0.12, "#ffd3c4"], [0.85, 0.3, "#d6f1c4"], [0.3, 0.55, "#c4e8f0"]].forEach(([fx, fz, color]) => {
    const p = isoPoint(x + 0.05 + fx * 1.1, 8.13, 38 + fz * 16);
    ctx.fillStyle = color;
    ctx.fillRect(p.x - 2.6, p.y - 3, 5.2, 5);
    ctx.fillStyle = CORAL;
    ctx.fillRect(p.x - 0.5, p.y - 3.4, 1, 1);
  });
}

function dormActors(item) {
  if (item.id === "dorm-bed") return [{ depth: depthOf(item.x + item.w / 2, item.y + item.h + 0.01), draw: () => drawBed(item) }];
  if (item.id === "dorm-wardrobe") return slicedY(item, 1.0, (y, length, i, n) => drawWardrobeSlice(item, y, length, i, n));
  if (item.id === "dorm-shelf") return sliced(item, 1.1, (x, w, i) => drawBookshelfSlice(item, x, w, i));
  if (item.id === "dorm-desk") {
    return [
      ...sliced(item, 0.95, (x, w, i, n) => drawStudyTableSlice(item, x, w, i, n)),
      { depth: depthOf(item.x + 0.8, item.y + item.h + 0.5), draw: () => drawDormChair(item) },
    ];
  }
  return [];
}

const dormDecor = () => [
  // both hang on the north wall (y 8.1): after the wall, before everything in the room
  { depth: depthOf(36.25, 8.12), draw: drawDormPoster },
  { depth: depthOf(38.55, 8.12), draw: drawDormCorkboard },
];

export function roomActors(t) {
  const actors = [];
  for (const item of layout().solid) {
    if (!wingIsOpen(item.wing)) continue; // a closed wing shows nothing of what is inside
    const id = item.id;
    if (id.startsWith("dorm-") && id !== "dorm-plant") {
      actors.push(...dormActors(item));
    } else if (id === "cafe-shelf") {
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
          actors.push({ depth: depthOf(px, item.y + item.h + 0.5), draw: () => drawStool(px, item.y + item.h + 0.45, 22, CORAL) });
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
      actors.push({ depth: depthOf(item.x, item.y) + 0.2, draw: () => drawColumn(item) });
    } else if (id === "study-shelf") {
      actors.push(...sliced(item, 1.1, (x, w, i) => drawBookshelfSlice(item, x, w, i)));
    } else if (id.startsWith("study-table") || id === "hub-meeting-table") {
      actors.push(...sliced(item, 0.95, (x, w, i, n) => drawStudyTableSlice(item, x, w, i, n)));
      for (const spot of tableStools(item, id === "hub-meeting-table" ? "north" : "both")) {
        actors.push({ depth: spot.depth, draw: () => drawStool(spot.x, spot.y, 14, TEAL) });
      }
    } else if (id === "seminar-table") {
      actors.push({ depth: frontDepth(item), draw: () => drawSeminarTable(item) });
      for (const [sx, sy] of [[item.x - 0.35, item.y + item.h / 2], [item.x + item.w / 2, item.y - 0.35]]) {
        actors.push({ depth: depthOf(sx, sy), draw: () => drawStool(sx, sy, 14, LILAC) });
      }
    } else if (id === "stock-rack-west") {
      actors.push(...slicedY(item, 1.15, (y, length, i) => drawStorageRackSlice(item, y, length, i)));
    } else if (id.startsWith("stock-pallet")) {
      actors.push({ depth: frontDepth(item), draw: () => drawPallet(item) });
    } else if (id.startsWith("stock-crates")) {
      actors.push({ depth: frontDepth(item), draw: () => drawCrates(item) });
    } else if (id.startsWith("hub-sofa")) {
      actors.push(...slicedY(item, 1.0, (y, length, i, n) => drawSofaSlice(item, y, length, i, n)));
    } else if (id === "hub-charging-bar") {
      actors.push({ depth: frontDepth(item), draw: () => drawChargingBar(item) });
    } else if (id.includes("plant")) {
      const scale = 0.9 + item.r * 0.9;
      actors.push({ depth: depthOf(item.x, item.y) + 0.3, draw: () => drawIndoorPlant(item.x, item.y, scale) });
    }
  }
  if (wingIsOpen("dorm")) actors.push(...dormDecor());
  layout().activities.forEach((activity, index) => {
    if (!wingIsOpen(activity.wing)) return;
    actors.push({ depth: depthOf(activity.x, activity.y) + 0.03, draw: () => drawRoomPerson(activity, t, index) });
  });
  actors.push(...employeeActors(t));
  return actors;
}
