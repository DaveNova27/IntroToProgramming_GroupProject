// The Nova: one big building on the campus map (spec walk-in). While the player is inside, the
// roof fades out and the two walls that face the camera sink to a low rim, so the rooms show.
// Stylised after the real Nova SBE in Carcavelos: long white volumes with flat roofs and a thick
// edge, dark glass fronts, slim white columns under a deep canopy, and an atrium with a glass roof.
// Only for showing: no rule reads any of this.

import { drawRoofLights } from "./campus.js";
import { drawWindFlag, environmentalProfile } from "./environment.js";
import {
  drawBlock,
  drawFacadeBandX,
  drawFacadeBandY,
  drawPlane,
  drawRaisedSlab,
  drawSoftShadow,
  drawWorldLabel,
} from "./primitives.js";
import { GALLERY_Z, drawInteriorFloor, drawInteriorWayfinding, roomActors } from "./rooms.js";
import { ctx, isoPoint, scene, world } from "./scene.js";

// colours estimated from photographs of the real campus
const WHITE = { top: "#f7f7f4", south: "#e4e5e2", east: "#c9cdd0" };
const GLASS = "#2a5573";
const GLASS_EAST = "#234a64";
const GLASS_LIGHT = "#3a6d8c";
const RIM = 9; // height of a front wall while the roof is gone
const SLICE = 2.5; // longest piece of wall drawn at once, so people sort correctly around it
const OPEN_BELOW = 0.98; // the rooms are drawn while the roof is thinner than this

export const novaIsOpen = () => scene.roof < OPEN_BELOW;

const zAt = (x, y) => world.nova.parts.find((p) => x >= p.x && x <= p.x + p.w && y >= p.y && y <= p.y + p.h)?.z ?? 78;

function bounds() {
  const { parts } = world.nova;
  const x = Math.min(...parts.map((p) => p.x));
  const y = Math.min(...parts.map((p) => p.y));
  return { x, y, w: Math.max(...parts.map((p) => p.x + p.w)) - x, h: Math.max(...parts.map((p) => p.y + p.h)) - y };
}

// ---- ground: shadow, plinth, floor and the signs on the floor -----------------------------

export function drawNovaGround() {
  const b = bounds();
  drawSoftShadow(b.x + b.w / 2, b.y + b.h * 0.8, 600, 160, 0.17);
  drawBlock(b.x - 0.25, b.y - 0.2, b.w + 0.5, b.h + 0.4, 3, "#dcdbd5", "#8d9b97", "#abb3ae");
  drawInteriorFloor();
  if (novaIsOpen()) drawInteriorWayfinding();
}

// ---- walls --------------------------------------------------------------------------------

function drawWallSlice(wall, x, y, w, h, z) {
  drawBlock(x, y, w, h, z, WHITE.top, WHITE.east, WHITE.south);
  // the back walls show their inside to the camera: a dark skirting board along the floor
  if (wall.side === "north") drawFacadeBandY(x, y + h + 0.015, w, 0, 4, "#aab2b5", 1);
  if (wall.side === "west") drawFacadeBandX(x + w + 0.015, y, h, 0, 4, "#aab2b5", 1);
  if (z < 40) return;
  const bands = wall.side === "north" || wall.side === "west" ? [[0.52, 0.86, GLASS_LIGHT]] : [[0.12, 0.48, GLASS], [0.58, 0.88, GLASS]];
  for (const [low, high, color] of bands) {
    if (wall.side === "north" || wall.side === "south") {
      drawFacadeBandY(x + 0.12, y + h + 0.015, w - 0.24, z * low, z * high, color, Math.max(2, Math.round(w * 1.4)));
    } else {
      drawFacadeBandX(x + w + 0.015, y + 0.12, h - 0.24, z * low, z * high, wall.side === "east" ? GLASS_EAST : color, Math.max(2, Math.round(h * 1.4)));
    }
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

function wallActors() {
  const actors = [];
  const atrium = world.nova.parts.find((part) => part.glassRoof);
  for (const wall of world.nova.walls) {
    const alongX = wall.w >= wall.h;
    const length = alongX ? wall.w : wall.h;
    const count = Math.max(1, Math.ceil(length / SLICE));
    const size = length / count;
    const front = wall.side === "south" || wall.side === "east";
    for (let i = 0; i < count; i++) {
      const x = alongX ? wall.x + i * size : wall.x;
      const y = alongX ? wall.y : wall.y + i * size;
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
          const full = zAt(cx, cy);
          drawWallSlice(wall, x, y, w, h, front ? RIM + (full - RIM) * scene.roof : full);
          if (wall.side === "north" && atrium && x < atrium.x + atrium.w && x + w > atrium.x && scene.roof < OPEN_BELOW) {
            drawGallery(wall, Math.max(x, atrium.x), Math.min(x + w, atrium.x + atrium.w));
          }
        },
      });
    }
  }
  return actors;
}

// ---- the canopy and its columns in front of the entrance side -----------------------------

const CANOPY_Y = 9.25;
const CANOPY_DEPTH = 1.1;
const CANOPY_Z = 72;
const COLUMNS = [12.2, 15.8, 19.4, 26.6, 30.2, 33.0];

function canopyActors() {
  const b = bounds();
  const actors = [];
  const slices = Math.ceil(b.w / 3);
  const size = b.w / slices;
  for (let i = 0; i < slices; i++) {
    const x = b.x + i * size;
    actors.push({
      depth: x + size / 2 + CANOPY_Y + 0.02,
      draw: () => {
        // the canopy is part of the roof: it fades with it, so that it does not hide the floor
        if (scene.roof < 0.02) return;
        ctx.save();
        ctx.globalAlpha = scene.roof;
        drawRaisedSlab(x, CANOPY_Y, size, CANOPY_DEPTH, CANOPY_Z, 5, WHITE.top, WHITE.east, WHITE.south);
        ctx.restore();
      },
    });
  }
  for (const x of COLUMNS) {
    const y = CANOPY_Y + CANOPY_DEPTH - 0.15;
    actors.push({
      depth: x + y + 0.02,
      draw: () => {
        ctx.save();
        ctx.globalAlpha = 0.35 + 0.65 * scene.roof;
        drawBlock(x - 0.1, y - 0.1, 0.2, 0.2, CANOPY_Z - 4, "#ffffff", WHITE.east, WHITE.south);
        ctx.restore();
      },
    });
  }
  return actors;
}

// ---- the roof -------------------------------------------------------------------------------

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

function drawNovaRoof(t) {
  if (scene.roof < 0.01) return;
  const { parts } = world.nova;
  const wings = parts.filter((p) => !p.glassRoof);
  const atrium = parts.find((p) => p.glassRoof);
  ctx.save();
  ctx.globalAlpha = scene.roof;
  for (const part of wings) {
    drawRaisedSlab(part.x - 0.2, part.y - 0.2, part.w + 0.4, part.h + 0.4, part.z + 6, 7, WHITE.top, WHITE.east, WHITE.south);
    drawRoofLights(part.x + 0.7, part.y + 0.7, part.w - 1.4, part.h - 1.4, part.z + 6);
  }
  if (atrium) {
    drawAtriumRoof(atrium, Math.max(...wings.map((p) => p.z)) + 6);
    const environment = environmentalProfile(scene.clock, scene.day, t);
    drawWindFlag(atrium.x + 0.7, atrium.y + 0.8, atrium.z + 14, "#ed7458", t, environment, 0.86);
    drawWindFlag(atrium.x + atrium.w - 0.7, atrium.y + 0.8, atrium.z + 14, "#64cbc8", t + 260, environment, 0.86);
  }
  drawWorldLabel(23, 10.6, 118, "NOVA COAST CAMPUS", "#f5c95e");
  ctx.restore();
}

// ---- everything of the Nova that is sorted with the rest of the scene -----------------------

export function novaActors(t) {
  // the roof is drawn after every wall piece and every person under it (their depths stay below 40)
  const actors = [...wallActors(), ...canopyActors(), { depth: 45, draw: () => drawNovaRoof(t) }];
  if (novaIsOpen()) actors.push(...roomActors(t));
  return actors;
}
