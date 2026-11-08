// The Nova: one big building on the campus map, made of four wings (specs walk-in and nova-wings).
// While the player is in a wing, its roof fades out and the walls that would hide the rooms sink to a
// low rim, so the rooms show. Every wing has its own roof; a wing that stands in front of another one
// fades with it (`fadesWith` in the data).
// Stylised after the real Nova SBE in Carcavelos: long white volumes with flat roofs and a thick
// edge, dark glass fronts, slim white columns under a deep canopy, and an atrium with a glass roof.
// Only for showing: no rule reads any of this.

import { drawRoofGarden, drawRoofLights } from "./campus.js";
import { drawWindFlag, environmentalProfile } from "./environment.js";
import {
  drawBlock,
  drawFacadeBandX,
  drawFacadeBandY,
  drawPlane,
  drawRaisedSlab,
  drawSoftShadow,
  drawTimberScreen,
  drawWorldLabel,
} from "./primitives.js";
import { GALLERY_Z, drawInteriorFloor, drawInteriorWayfinding, roomActors } from "./rooms.js";
import { ctx, isoPoint, roofOf, scene, wingIsOpen, world } from "./scene.js";

// colours estimated from photographs of the real campus
const WHITE = { top: "#f7f7f4", south: "#e4e5e2", east: "#c9cdd0" };
const GLASS = "#2a5573";
const GLASS_EAST = "#234a64";
const GLASS_LIGHT = "#3a6d8c";
const RIM = 9; // height of a front wall while its roof is gone
const SLICE = 2.5; // longest piece of wall drawn at once, so people sort correctly around it

// what makes each wing recognisable (the data says where it is, this says how it looks)
const LOOK = {
  nova: {},
  "learning-center": { accent: "#64cbc8", garden: true, label: "LEARNING CENTER" },
  mercado: { accent: "#f5c95e", label: "MERCADO SUPPLY" },
  hub: { accent: "#ff7b5b", glassy: true, label: "STUDENT HUB" },
  dorm: { accent: "#c99a62", garden: true, timber: true, label: "DORM" },
};

export const novaIsOpen = () => wingIsOpen("nova");

const wingParts = (wingId) => world.nova.parts.filter((part) => part.wing === wingId);
const covers = (p, x, y) => x >= p.x && x <= p.x + p.w && y >= p.y && y <= p.y + p.h;
const zAt = (wingId, x, y) => {
  const parts = wingParts(wingId);
  return (parts.find((p) => covers(p, x, y)) ?? parts[0])?.z ?? 78;
};

function wingBounds(wingId) {
  const parts = wingParts(wingId);
  const x = Math.min(...parts.map((p) => p.x));
  const y = Math.min(...parts.map((p) => p.y));
  return { x, y, w: Math.max(...parts.map((p) => p.x + p.w)) - x, h: Math.max(...parts.map((p) => p.y + p.h)) - y };
}

// ---- ground: shadow, plinth, floor and the signs on the floor -----------------------------

export function drawNovaGround() {
  const wings = world.nova.wings.map((wing) => wing.id);
  for (const id of wings) {
    const b = wingBounds(id);
    drawSoftShadow(b.x + b.w / 2, b.y + b.h * 0.8, b.w * 27, b.h * 20, 0.17);
  }
  for (const id of wings) {
    const b = wingBounds(id);
    drawBlock(b.x - 0.25, b.y - 0.2, b.w + 0.5, b.h + 0.4, 3, "#dcdbd5", "#8d9b97", "#abb3ae");
  }
  for (const id of wings) drawInteriorFloor(id);
  for (const id of wings) if (wingIsOpen(id)) drawInteriorWayfinding(id);
}

// ---- walls --------------------------------------------------------------------------------

function drawWallSlice(wall, x, y, w, h, z) {
  drawBlock(x, y, w, h, z, WHITE.top, WHITE.east, WHITE.south);
  // the back walls show their inside to the camera: a dark skirting board along the floor
  if (wall.side === "north") drawFacadeBandY(x, y + h + 0.015, w, 0, 4, "#aab2b5", 1);
  if (wall.side === "west") drawFacadeBandX(x + w + 0.015, y, h, 0, 4, "#aab2b5", 1);
  if (z < 40) return;
  const back = wall.side === "north" || wall.side === "west";
  const glassy = LOOK[wall.wing]?.glassy;
  let bands = back ? [[0.52, 0.86, GLASS_LIGHT]] : [[0.12, 0.48, GLASS], [0.58, 0.88, GLASS]];
  if (glassy) bands = [[0.14, 0.9, back ? GLASS_LIGHT : GLASS]];
  // the Dorm: windows in the upper half of the front, warm timber slats below them
  if (LOOK[wall.wing]?.timber && wall.side === "south") {
    bands = [[0.58, 0.88, GLASS]];
    drawFacadeBandY(x, y + h + 0.015, w, 4, z * 0.52, "#c99a62", 1);
    drawTimberScreen(x + 0.05, y + h + 0.02, w - 0.1, 4, z * 0.52, Math.max(3, Math.round(w * 3)));
  }
  for (const [low, high, color] of bands) {
    if (wall.side === "north" || wall.side === "south") {
      drawFacadeBandY(x + 0.12, y + h + 0.015, w - 0.24, z * low, z * high, color, Math.max(2, Math.round(w * 1.4)));
    } else {
      drawFacadeBandX(x + w + 0.015, y + 0.12, h - 0.24, z * low, z * high, wall.side === "east" ? GLASS_EAST : color, Math.max(2, Math.round(h * 1.4)));
    }
  }
  // a coloured line along the top of the facade that faces the plaza
  const accent = LOOK[wall.wing]?.accent;
  if (accent && wall.side === "south" && wall.wing !== "nova" && z > 50) {
    drawFacadeBandY(x, y + h + 0.02, w, z - 11, z - 8, accent, 1);
  }
}

// The upper floor along the north wall of the atrium: a slab with a glass balustrade, reached by the
// staircase. The staircase end is only a landing.
function drawGallery(wall, x0, x1) {
  const inner = wall.y + wall.h;
  const stairs = world.interiors.campus.solid.find((item) => item.id === "staircase");
  const split = Math.min(x1, stairs ? stairs.x : x1);
  if (x0 < split) {
    drawRaisedSlab(x0, inner, split - x0, 0.7, GALLERY_Z, 5, WHITE.top, WHITE.east, WHITE.south);
    drawFacadeBandY(x0, inner + 0.71, split - x0, GALLERY_Z, GALLERY_Z + 14, "rgba(160,205,225,.34)", Math.max(1, Math.round((split - x0) * 1.4)));
    const a = isoPoint(x0, inner + 0.71, GALLERY_Z + 14);
    const b = isoPoint(split, inner + 0.71, GALLERY_Z + 14);
    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = 1.8;
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();
  }
  if (x1 > split) drawRaisedSlab(Math.max(x0, split), inner, x1 - Math.max(x0, split), 0.2, GALLERY_Z, 5, WHITE.top, WHITE.east, WHITE.south);
}

// How far up is a wall? A front wall (south, east) hides its own wing, so it sinks to a rim when that
// roof is gone. A wall can also hide another wing behind it (`hides`), like the west wall of the Nova
// hides the Learning Center. A back wall that hides nothing stays full height.
function wallHeight(wall, full) {
  const front = wall.side === "south" || wall.side === "east";
  const hides = wall.hides ?? (front ? [wall.wing] : []);
  if (!hides.length) return full;
  const closed = Math.min(...hides.map(roofOf));
  return RIM + (full - RIM) * closed;
}

// A wall is cut at the seams between the parts of the building, so that no slice reaches over two
// parts with different heights: [start, length] pieces along the wall.
function wallSegments(wall, alongX) {
  const start = alongX ? wall.x : wall.y;
  const end = start + (alongX ? wall.w : wall.h);
  const seams = wingParts(wall.wing)
    .flatMap((p) => (alongX ? [p.x, p.x + p.w] : [p.y, p.y + p.h]))
    .filter((at) => at > start + 1e-9 && at < end - 1e-9);
  const cuts = [...new Set([start, ...seams.sort((a, b) => a - b), end])];
  return cuts.slice(1).map((to, i) => [cuts[i], to - cuts[i]]);
}

function wallActors() {
  const actors = [];
  const atrium = wingParts("nova").find((part) => part.glassRoof);
  for (const wall of world.nova.walls) {
    const alongX = wall.w >= wall.h;
    for (const [from, length] of wallSegments(wall, alongX)) {
      const count = Math.max(1, Math.ceil(length / SLICE));
      const size = length / count;
      for (let i = 0; i < count; i++) {
        const x = alongX ? from + i * size : wall.x;
        const y = alongX ? wall.y : from + i * size;
        const w = alongX ? size : wall.w;
        const h = alongX ? wall.h : size;
        const cx = x + w / 2;
        const cy = y + h / 2;
        // The front walls sort by their front line (everything inside is behind them). The back walls
        // sort by their back corner, so that everything standing in the rooms is drawn after them.
        let depth = cx + wall.y + wall.h + 0.01;
        if (wall.side === "north") depth = x + wall.y;
        if (wall.side === "west") depth = wall.x + y;
        if (wall.side === "east") depth = wall.x + wall.w + cy + 0.01;
        actors.push({
          depth,
          draw: () => {
            drawWallSlice(wall, x, y, w, h, wallHeight(wall, zAt(wall.wing, cx, cy)));
            if (wall.wing === "nova" && wall.side === "north" && atrium && x < atrium.x + atrium.w && x + w > atrium.x && wingIsOpen("nova")) {
              drawGallery(wall, Math.max(x, atrium.x), Math.min(x + w, atrium.x + atrium.w));
            }
          },
        });
      }
    }
  }
  return actors;
}

// ---- the canopy and its columns in front of the entrance side of the main block -------------

const CANOPY_Y = 9.25;
const CANOPY_DEPTH = 1.1;
const CANOPY_Z = 72;
const COLUMNS = [12.2, 15.8, 19.4, 26.6, 30.2, 33.0];

// The canopy runs along the main block, but not where another wing stands in front of it.
function canopySpans() {
  const b = wingBounds("nova");
  let spans = [[b.x, b.x + b.w]];
  const blockers = world.nova.parts.filter(
    (p) => p.wing !== "nova" && p.y < CANOPY_Y + CANOPY_DEPTH && p.y + p.h > CANOPY_Y && p.x + p.w > b.x && p.x < b.x + b.w,
  );
  for (const p of blockers) {
    spans = spans
      .flatMap(([from, to]) => [[from, Math.min(to, p.x)], [Math.max(from, p.x + p.w), to]])
      .filter(([from, to]) => to - from > 0.05);
  }
  return spans;
}

function canopyActors() {
  const actors = [];
  const spans = canopySpans();
  for (const [from, to] of spans) {
    const slices = Math.ceil((to - from) / 3);
    const size = (to - from) / slices;
    for (let i = 0; i < slices; i++) {
      const x = from + i * size;
      actors.push({
        depth: x + size / 2 + CANOPY_Y + 0.02,
        draw: () => {
          // the canopy is part of the roof: it fades with it, so that it does not hide the floor
          const roof = roofOf("nova");
          if (roof < 0.02) return;
          ctx.save();
          ctx.globalAlpha = roof;
          drawRaisedSlab(x, CANOPY_Y, size, CANOPY_DEPTH, CANOPY_Z, 5, WHITE.top, WHITE.east, WHITE.south);
          ctx.restore();
        },
      });
    }
  }
  for (const x of COLUMNS.filter((column) => spans.some(([from, to]) => column > from && column < to))) {
    const y = CANOPY_Y + CANOPY_DEPTH - 0.15;
    actors.push({
      depth: x + y + 0.02,
      draw: () => {
        ctx.save();
        ctx.globalAlpha = 0.35 + 0.65 * roofOf("nova");
        drawBlock(x - 0.1, y - 0.1, 0.2, 0.2, CANOPY_Z - 4, "#ffffff", WHITE.east, WHITE.south);
        ctx.restore();
      },
    });
  }
  return actors;
}

// ---- the roofs -------------------------------------------------------------------------------

function drawAtriumRoof(a, wingTop) {
  // the taller block above the wings: a glass band, then the thick white edge, then the glass roof
  const top = a.z + 6;
  drawFacadeBandY(a.x + 0.2, a.y + a.h + 0.01, a.w - 0.4, wingTop + 2, top - 8, GLASS, 7);
  drawFacadeBandX(a.x + a.w + 0.01, a.y + 0.2, a.h - 0.4, wingTop + 2, top - 8, GLASS_EAST, 5);
  drawRaisedSlab(a.x - 0.2, a.y - 0.2, a.w + 0.4, a.h + 0.4, top, 7, WHITE.top, WHITE.east, WHITE.south);
  const inset = 0.5;
  const x = a.x + inset;
  const y = a.y + inset;
  const w = a.w - 2 * inset;
  const h = a.h - 2 * inset;
  drawPlane(
    [isoPoint(x, y, top), isoPoint(x + w, y, top), isoPoint(x + w, y + h, top), isoPoint(x, y + h, top)],
    "rgba(168,212,236,.92)",
    "rgba(255,255,255,.9)",
    1.2,
  );
  ctx.strokeStyle = "rgba(255,255,255,.88)";
  ctx.lineWidth = 1.4;
  for (let i = 1; i < 7; i++) {
    const p = isoPoint(x + (w * i) / 7, y, top);
    const q = isoPoint(x + (w * i) / 7, y + h, top);
    ctx.beginPath();
    ctx.moveTo(p.x, p.y);
    ctx.lineTo(q.x, q.y);
    ctx.stroke();
  }
  for (let j = 1; j < 5; j++) {
    const p = isoPoint(x, y + (h * j) / 5, top);
    const q = isoPoint(x + w, y + (h * j) / 5, top);
    ctx.beginPath();
    ctx.moveTo(p.x, p.y);
    ctx.lineTo(q.x, q.y);
    ctx.stroke();
  }
}

function drawWingRoof(wing, t) {
  const opacity = roofOf(wing.id);
  if (opacity < 0.01) return;
  const look = LOOK[wing.id] ?? {};
  const parts = wingParts(wing.id);
  const plain = parts.filter((p) => !p.glassRoof);
  const atrium = parts.find((p) => p.glassRoof);
  ctx.save();
  ctx.globalAlpha = opacity;
  for (const part of plain) {
    drawRaisedSlab(part.x - 0.2, part.y - 0.2, part.w + 0.4, part.h + 0.4, part.z + 6, 7, WHITE.top, WHITE.east, WHITE.south);
    if (look.garden) drawRoofGarden(part.x + 0.55, part.y + 0.45, part.w - 1.1, part.h - 1.0, part.z + 6);
    else drawRoofLights(part.x + 0.7, part.y + 0.7, part.w - 1.4, part.h - 1.4, part.z + 6);
  }
  if (atrium) {
    drawAtriumRoof(atrium, Math.max(...plain.map((p) => p.z)) + 6);
    const environment = environmentalProfile(scene.clock, scene.day, t);
    drawWindFlag(atrium.x + 0.7, atrium.y + 0.8, atrium.z + 14, "#ed7458", t, environment, 0.86);
    drawWindFlag(atrium.x + atrium.w - 0.7, atrium.y + 0.8, atrium.z + 14, "#64cbc8", t + 260, environment, 0.86);
  }
  if (wing.id === "nova") {
    drawWorldLabel(23, 10.6, 118, "NOVA COAST CAMPUS", "#f5c95e");
  } else if (look.label) {
    const b = wingBounds(wing.id);
    drawWorldLabel(b.x + b.w / 2, b.y + b.h + 0.1, Math.max(...parts.map((p) => p.z)) + 16, look.label, look.accent);
  }
  ctx.restore();
}

// A roof is drawn after every wall piece and every person under it, and before what stands in front.
const roofDepth = (wingId) => {
  const b = wingBounds(wingId);
  return b.x + b.w + b.y + b.h + 1;
};

// ---- everything of the Nova that is sorted with the rest of the scene -----------------------

export function novaActors(t) {
  const actors = [...wallActors(), ...canopyActors(), ...roomActors(t)];
  for (const wing of world.nova.wings) actors.push({ depth: roofDepth(wing.id), draw: () => drawWingRoof(wing, t) });
  return actors;
}
