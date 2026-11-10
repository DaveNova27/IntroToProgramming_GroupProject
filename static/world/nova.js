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
  drawFootprintShadow,
  drawSoftShadow,
  drawWorldLabel,
} from "./primitives.js";
import { GALLERY_Z, drawInteriorFloor, drawInteriorWayfinding, roomActors } from "./rooms.js";
import { ctx, depthOf, isoPoint, reducedMotion, roofOf, scene, wingIsOpen, world } from "./scene.js";

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
  dorm: { accent: "#bce65f", garden: true, label: "DORM" },
};

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
    drawFootprintShadow(b.x + b.w / 2, b.y + b.h * 0.8, b.w, b.h, 0.17);
  }
  for (const id of wings) {
    const b = wingBounds(id);
    drawBlock(b.x - 0.25, b.y - 0.2, b.w + 0.5, b.h + 0.4, 3, "#dcdbd5", "#8d9b97", "#abb3ae");
  }
  drawNovaPortal();
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
  for (const [low, high, color] of bands) {
    if (wall.side === "north" || wall.side === "south") {
      drawFacadeBandY(x + 0.12, y + h + 0.015, w - 0.24, z * low, z * high, color, Math.max(2, Math.round(w * 1.4)));
    } else {
      drawFacadeBandX(x + w + 0.015, y + 0.12, h - 0.24, z * low, z * high, wall.side === "east" ? GLASS_EAST : color, Math.max(2, Math.round(h * 1.4)));
    }
  }
  if (wall.wing === "nova") drawNovaFacade(wall, x, y, w, h, z);
  // a coloured line along the top of the facade that faces the plaza
  const accent = LOOK[wall.wing]?.accent;
  if (accent && wall.side === "south" && wall.wing !== "nova" && z > 50) {
    drawFacadeBandY(x, y + h + 0.02, w, z - 11, z - 8, accent, 1);
  }
}

// The main block is not a flat white box: a stone plinth, white fins between the windows, the edge of each
// floor sticking out as a ledge and a coral line under the roof. The fins stand on a fixed grid, so
// neighbouring slices of the wall never draw one twice.
const FIN_STEP = 2.0;
function drawNovaFacade(wall, x, y, w, h, z) {
  const fins = (from, to) => {
    const list = [];
    for (let at = Math.ceil(from / FIN_STEP) * FIN_STEP; at < to - 1e-9; at += FIN_STEP) list.push(at);
    return list;
  };
  if (wall.side === "south") {
    const face = y + h;
    drawFacadeBandY(x, face + 0.02, w, 0, 7, "#a9b0ad", 1);
    drawRaisedSlab(x, face, w, 0.24, z * 0.53, 3.5, WHITE.top, WHITE.east, WHITE.south);
    drawFacadeBandY(x, face + 0.26, w, z - 12, z - 9, "#ff7b5b", 1);
    for (const at of fins(x, x + w)) drawBlock(at - 0.08, face, 0.16, 0.22, z * 0.93, "#ffffff", WHITE.east, WHITE.south);
  }
  // the east face is seen edge-on from the front (spec map-view): no ledge and no fins there
}

// The entrance: a stone apron with two steps, a dark header beam under the canopy between the two middle
// columns, and the name of the school on it. The beam fades with the roof, like the canopy.
function drawNovaPortal() {
  const entrance = world.nova.entrances.find((e) => e.id === "main");
  if (!entrance) return;
  const left = entrance.x - 0.9;
  const width = entrance.width + 1.8;
  drawBlock(left, 9.2, width, 1.45, 3.5, "#ece6d6", "#bdb59f", "#d4ccb8");
  drawBlock(left + 0.35, 9.2, width - 0.7, 1.05, 5.5, "#f3eee0", "#c6bfa9", "#ddd6c2");
  const step = (inset, depth, z, alpha) => {
    const p = isoPoint(left + inset, 9.2 + depth, z);
    const q = isoPoint(left + width - inset, 9.2 + depth, z);
    ctx.strokeStyle = `rgba(120,110,90,${alpha})`;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(p.x, p.y);
    ctx.lineTo(q.x, q.y);
    ctx.stroke();
  };
  step(0, 1.45, 3.5, 0.75);
  step(0.35, 1.05, 5.5, 0.9);
}

function drawNovaSign() {
  const roof = roofOf("nova");
  if (roof < 0.02) return;
  const entrance = world.nova.entrances.find((e) => e.id === "main");
  if (!entrance) return;
  const from = entrance.x - 0.5;
  const to = entrance.x + entrance.width + 0.5;
  const y = CANOPY_Y + CANOPY_DEPTH - 0.2;
  ctx.save();
  ctx.globalAlpha = roof;
  drawRaisedSlab(from, y, to - from, 0.2, CANOPY_Z - 5, 9, "#4c7380", "#1d3a43", "#25444e");
  drawFacadeBandY(from + 0.12, y + 0.212, to - from - 0.24, CANOPY_Z - 17, CANOPY_Z - 15.5, "#ff7b5b", 1);
  const p = isoPoint((from + to) / 2, y + 0.22, CANOPY_Z - 11);
  ctx.translate(p.x, p.y);
  ctx.fillStyle = "#ffffff";
  ctx.font = "800 9px Menlo, Consolas, monospace";
  ctx.textAlign = "center";
  ctx.fillText("NOVA SBE", 0, 0);
  ctx.restore();
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

// How far up is a wall? The front wall (south, the camera looks from there) hides its own wing, so it
// sinks to a rim when that roof is gone. A wall can also hide another wing behind it (`hides`), like the
// west wall of the Nova hides the Learning Center. A wall that hides nothing stays full height.
function wallHeight(wall, full) {
  const front = wall.side === "south";
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
        // The front (south) walls sort by their front line: everything inside is behind them. The north
        // walls sort by their back line, so everything standing in the rooms is drawn after them. The
        // side walls sort by the front end of each slice.
        let depth = depthOf(cx, wall.y + wall.h + 0.01);
        if (wall.side === "north") depth = depthOf(x, wall.y);
        if (wall.side === "west") depth = depthOf(wall.x, y + h);
        if (wall.side === "east") depth = depthOf(wall.x + wall.w, y + h + 0.01);
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
        depth: depthOf(x + size / 2, CANOPY_Y + CANOPY_DEPTH + 0.02), // overhead: sorts by its front edge
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
      depth: depthOf(x, y + 0.02),
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

// on the Dorm's roof: a clothes line with washing that sways, a chimney, an aerial
function drawDormRoofLife(part, t) {
  const z = part.z + 6;
  const y = part.y + part.h - 1.0;
  const x0 = part.x + 0.9;
  const x1 = part.x + part.w - 1.2;
  for (const x of [x0, x1]) {
    ctx.strokeStyle = "#5d6765";
    ctx.lineWidth = 1.8;
    ctx.beginPath();
    const a = isoPoint(x, y, z + 1);
    const b = isoPoint(x, y, z + 20);
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();
  }
  const count = 6;
  const sway = reducedMotion ? 0 : Math.sin(t * 0.0021) * 1.3;
  ctx.strokeStyle = "rgba(60,60,60,.7)";
  ctx.lineWidth = 0.8;
  ctx.beginPath();
  for (let i = 0; i <= count * 2; i++) {
    const f = i / (count * 2);
    const p = isoPoint(x0 + (x1 - x0) * f, y, z + 19 - 3 * Math.sin(Math.PI * f));
    if (i === 0) ctx.moveTo(p.x, p.y);
    else ctx.lineTo(p.x, p.y);
  }
  ctx.stroke();
  ["#ff7458", "#ffffff", "#64cbc8", "#f5c95e", "#9a7bc1", "#ffffff"].forEach((color, i) => {
    const f = (i + 0.5) / count;
    const p = isoPoint(x0 + (x1 - x0) * f, y, z + 19 - 3 * Math.sin(Math.PI * f));
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.moveTo(p.x - 4, p.y);
    ctx.lineTo(p.x + 4, p.y);
    ctx.lineTo(p.x + 3.4 + sway, p.y + (i % 2 ? 12 : 9));
    ctx.lineTo(p.x - 3.4 + sway, p.y + (i % 2 ? 12 : 9));
    ctx.closePath();
    ctx.fill();
  });
  drawBlock(part.x + part.w - 1.4, part.y + 0.9, 0.5, 0.5, z + 16, "#e4e5e2", "#aeb5b3", "#c9cdd0");
  const aerial = isoPoint(part.x + 1.3, part.y + 1.1, z);
  ctx.strokeStyle = "#31545b";
  ctx.lineWidth = 1.4;
  ctx.beginPath();
  ctx.moveTo(aerial.x, aerial.y);
  ctx.lineTo(aerial.x, aerial.y - 26);
  ctx.moveTo(aerial.x - 7, aerial.y - 22);
  ctx.lineTo(aerial.x + 7, aerial.y - 22);
  ctx.moveTo(aerial.x - 5, aerial.y - 17);
  ctx.lineTo(aerial.x + 5, aerial.y - 17);
  ctx.stroke();
}

// rooftop plant on the main block: two air-handling boxes with a grille and a stair head, so the roof
// is not an empty sheet
function drawRoofPlant(part) {
  const top = part.z + 6;
  const box = (x, y, w, h, rise) => {
    drawRaisedSlab(x, y, w, h, top + rise, rise, "#e8ebe9", "#aeb5b3", "#c9cecc");
    drawFacadeBandY(x + 0.1, y + h + 0.012, w - 0.2, top + rise * 0.25, top + rise * 0.75, "#8f9a98", Math.max(3, Math.round(w * 3)));
  };
  box(part.x + part.w - 3.1, part.y + 1.0, 1.9, 1.0, 9);
  box(part.x + part.w - 3.1, part.y + 2.6, 1.9, 1.0, 9);
  box(part.x + 1.0, part.y + 1.0, 1.2, 1.2, 14);
  const rail = isoPoint(part.x + part.w - 0.45, part.y + part.h - 0.45, top + 5);
  ctx.fillStyle = "#31545b";
  ctx.fillRect(rail.x - 1, rail.y - 8, 2, 8);
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
    if (wing.id === "dorm") drawDormRoofLife(part, t);
    else drawRoofLights(part.x + 0.7, part.y + 0.7, part.w - 1.4, part.h - 1.4, part.z + 6);
    if (wing.id === "nova") drawRoofPlant(part);
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
  return depthOf(b.x + b.w, b.y + b.h + 0.02); // just after the south wall (front line + 0.01)
};

// ---- everything of the Nova that is sorted with the rest of the scene -----------------------

// The walls and the canopy come from the building's data, which never changes while it runs; their draw
// functions read the roofs at the moment they draw. So they are built once, not every frame.
let built = { key: null, walls: [], canopy: [] };

// the building replaced, or its parts or walls replaced or changed in length: built again
const buildingKey = () => [world.nova, world.nova.parts, world.nova.walls, world.nova.parts.length, world.nova.walls.length];

function fixedActors() {
  const key = buildingKey();
  if (!built.key || key.some((part, i) => part !== built.key[i])) built = { key, walls: wallActors(), canopy: canopyActors() };
  return built;
}

export function novaActors(t) {
  const fixed = fixedActors();
  const actors = [...fixed.walls, ...fixed.canopy, ...roomActors(t)];
  // the sign hangs under the front edge of the canopy: drawn just after it
  actors.push({ depth: depthOf(COLUMNS[3], CANOPY_Y + CANOPY_DEPTH + 0.03), draw: drawNovaSign });
  for (const wing of world.nova.wings) actors.push({ depth: roofDepth(wing.id), draw: () => drawWingRoof(wing, t) });
  return actors;
}
