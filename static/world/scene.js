// What all parts of the 2.5D world share: the canvas, the camera, the projection
// from map tiles to screen, and the data from the server.
// Nothing here decides a rule. The player's position and the clock are only for showing.

export const TILE_W = 76;
export const TILE_H = 38;
export const PLAYER_RADIUS = 0.28;
export const WALK_SPEED = 3.5; // tiles per second

// The clock only moves the light (minutes since midnight). It rests in the morning
// and runs through the day while a trading day plays. The result comes from the server.
export const DAY_START = 450;
export const DAY_END = 1170;
export const MORNING = 540;
// The night before the morning (spec day-cycle): after sleeping the light starts dark at 05:00 and the
// sun rises until DAY_START. Only the light; no rule reads it.
export const DAWN = 300;

export const canvas = document.querySelector("#world");
export const ctx = canvas.getContext("2d");
export const reducedMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches ?? false;

export const camera = { x: 21, y: 18, zoom: 1 };

// filled once from GET /api/world (see world.py)
export const world = {};

// The staff and the shift as the server last sent them. ui.js sets it, rooms.js only reads it
// to draw the employees: what a figure does comes from here, never from a rule in the browser.
export const server = { staff: null, shift: null, storeroom: 0 }; // storeroom: units of the shift shop's products

export const scene = {
  time: 0, // milliseconds, from requestAnimationFrame
  clock: MORNING,
  day: 1,
  zoneId: "campus",
  player: { x: 21, y: 18 },
  facing: { x: 0, y: 1 },
  walking: false,
  preview: false, // the small live window on the dashboard
  roofs: {}, // opacity of the roof of each wing of the Nova: 1 = closed, 0 = gone (see roofs.js)
  wing: null, // the wing the player is in, or null outside
  inNova: false, // the player stands under the roof of any wing
  sleeping: false, // the player lies in the Dorm's bed (spec day-cycle): only drawn, no rule
};

// A wing without an entry is closed. The rooms of a wing are drawn while its roof is thinner than this.
export const roofOf = (wingId) => scene.roofs[wingId] ?? 1;
export const wingIsOpen = (wingId) => roofOf(wingId) < 0.98;

export const activeZone = () => world.zones[scene.zoneId];

export function isoPoint(x, y, z = 0) {
  return { x: ((x - y) * TILE_W) / 2, y: ((x + y) * TILE_H) / 2 - z };
}

// from a click on the canvas back to map tiles
export function canvasWorldPoint(event) {
  const rect = canvas.getBoundingClientRect();
  const center = isoPoint(camera.x, camera.y);
  const ix = (event.clientX - rect.left - canvas.clientWidth / 2) / camera.zoom + center.x;
  const iy = (event.clientY - rect.top - canvas.clientHeight / 2) / camera.zoom + center.y;
  return { x: iy / TILE_H + ix / TILE_W, y: iy / TILE_H - ix / TILE_W };
}
