// The guests of the day (spec guests): they set off, walk to the shop they chose and queue there.
// Drawn only from what the server sent (state.guests): who, where they come from, which shop,
// when they set off and arrive (server ticks), their place in the line and their thought.
// No rule is decided here and nothing is random: a walk follows findPath and the server's clock,
// so a guest reaches the line on the tick the server says. A guest who is no longer in the list
// was served or gave up and walks back to where they came from.

import { findPath } from "./paths.js";
import { drawPersonFigure } from "./people.js";
import { nearestFreePoint } from "./physics.js";
import { roundedRect } from "./primitives.js";
import { wingsAt } from "./roofs.js";
import { PLAYER_RADIUS, ctx, depthOf, isoPoint, reducedMotion, scene, server, wingIsOpen, world } from "./scene.js";

// students in the campus colours, visitors in beach colours
const SHIRTS = {
  students: ["#64cbc8", "#9a7bc1", "#7fb0d8", "#f5c95e"],
  visitors: ["#ff8060", "#e6a769", "#f0e9dc", "#bce65f"],
};
const THOUGHT_MS = 4500; // a guest shows the thought this long after setting off
const SWITCH_THOUGHT_MS = 9000; // longer for one who changed their mind: that is the decision to see
const NEAR_PLAYER = 2.4; // tiles: next to the player a guest always shows the thought
const LEAVE_SPEED = 1.45; // tiles per second on the way back
const LEAVE_MS = 30000; // a guest who has not got home by then is gone anyway
const MAX_LEAVING = 8;
const LINE_SPOTS = 6; // places of a line that are drawn; whoever is further back waits at the last
const FACING_SHOP = { x: 0, y: -1 }; // every line faces north, to its counter

const routes = new Map(); // `${start}:${shop}` -> the walk from a start place to the line of a shop
const shown = new Map(); // id -> what is drawn now: { x, y, facing, moving, seenAt, guest }
const leaving = new Map(); // id -> { x, y, facing, route, at, until, guest }
let lastT = 0;

const campus = () => world.zones.campus;
const solid = () => world.colliders.campus;
const free = (point) => nearestFreePoint(point, campus(), solid(), PLAYER_RADIUS);

const spots = new Map();
function lineSpot(shop, index) {
  const key = `${shop}:${index}`;
  if (!spots.has(key)) {
    const line = world.guests.lines[shop];
    const i = Math.min(index, LINE_SPOTS - 1);
    spots.set(key, free({ x: line.x + line.dx * i, y: line.y + line.dy * i }));
  }
  return spots.get(key);
}

// a walk as a polyline with its length, from findPath (a straight line when no way was found)
function polyline(from, to) {
  const points = [from, ...(findPath(from, to, campus(), solid(), PLAYER_RADIUS) ?? [to])];
  const lengths = [0];
  for (let i = 1; i < points.length; i++) {
    lengths.push(lengths[i - 1] + Math.hypot(points[i].x - points[i - 1].x, points[i].y - points[i - 1].y));
  }
  return { points, lengths, total: lengths[lengths.length - 1] };
}

function routeOf(guest) {
  const key = `${guest.start}:${guest.shop}`; // the same for every guest with that start and shop
  if (!routes.has(key)) routes.set(key, polyline(free(world.guests.starts[guest.start]), lineSpot(guest.shop, 0)));
  return routes.get(key);
}

// the point a share (0..1) of the way along a polyline, and the direction there
function along(route, share) {
  const at = Math.max(0, Math.min(1, share)) * route.total;
  for (let i = 1; i < route.points.length; i++) {
    if (at <= route.lengths[i] || i === route.points.length - 1) {
      const a = route.points[i - 1];
      const b = route.points[i];
      const piece = route.lengths[i] - route.lengths[i - 1] || 1;
      const k = Math.max(0, Math.min(1, (at - route.lengths[i - 1]) / piece));
      return { x: a.x + (b.x - a.x) * k, y: a.y + (b.y - a.y) * k, facing: { x: (b.x - a.x) / piece, y: (b.y - a.y) / piece } };
    }
  }
  return { ...route.points[0], facing: { x: 0, y: 1 } };
}

// the server's tick now, between two answers (a tick is about a second)
function tickNow(t) {
  const data = server.guests;
  return data.tick + Math.min(1, Math.max(0, (t - (server.guestsAt ?? t)) / 1000));
}

// where a guest should be now: on the way (by the share of the walk the ticks say) or in the line
function target(guest, tick) {
  if (guest.line !== null || tick >= guest.arrives) {
    const spot = lineSpot(guest.shop, guest.line ?? 0);
    return { x: spot.x, y: spot.y, facing: FACING_SHOP, walking: false };
  }
  const point = along(routeOf(guest), (tick - guest.depart) / (guest.arrives - guest.depart));
  return { ...point, walking: true };
}

function startLeaving(id, view) {
  if (leaving.size >= MAX_LEAVING) return;
  const home = free(world.guests.starts[view.guest.start]);
  leaving.set(id, { ...view, route: polyline({ x: view.x, y: view.y }, home), at: 0, until: lastT + LEAVE_MS });
}

// One step of every guest: called once per frame from the drawing (dt from the frame times).
function step(t) {
  const dt = lastT ? Math.min(0.1, (t - lastT) / 1000) : 0;
  lastT = t;
  const data = server.guests;
  const now = new Set();
  if (data) {
    const tick = tickNow(t);
    for (const guest of data.walking) {
      now.add(guest.id);
      const goal = target(guest, tick);
      const view = shown.get(guest.id);
      if (!view) {
        shown.set(guest.id, { x: goal.x, y: goal.y, facing: goal.facing, moving: goal.walking, seenAt: t, guest });
        continue;
      }
      const ease = reducedMotion ? 1 : Math.min(1, dt * 8);
      const dx = (goal.x - view.x) * ease;
      const dy = (goal.y - view.y) * ease;
      view.x += dx;
      view.y += dy;
      view.moving = goal.walking || Math.hypot(dx, dy) > 0.004;
      view.facing = goal.walking ? goal.facing : FACING_SHOP;
      view.guest = guest;
    }
  }
  for (const [id, view] of shown) {
    if (now.has(id)) continue;
    shown.delete(id);
    startLeaving(id, view);
  }
  for (const [id, walk] of leaving) {
    walk.at += LEAVE_SPEED * dt;
    const point = along(walk.route, walk.route.total ? walk.at / walk.route.total : 1);
    Object.assign(walk, { x: point.x, y: point.y, facing: point.facing, moving: true });
    if (walk.at >= walk.route.total || t > walk.until) leaving.delete(id);
  }
}

// a guest inside a wing of the Nova shows only while its roof is gone, like the employees
function visible(point) {
  const wings = wingsAt(point, world.nova.parts);
  return !wings.length || wings.some(wingIsOpen);
}

function drawThought(view) {
  const text = view.guest.thought;
  // neighbours in a line think at three heights, so their bubbles can all be read
  const p = isoPoint(view.x, view.y, 66 + ((view.guest.line ?? view.guest.id) % 3) * 16);
  ctx.font = "700 7px system-ui, -apple-system, Segoe UI, sans-serif";
  const width = Math.min(190, ctx.measureText(text).width + 12);
  roundedRect(p.x - width / 2, p.y - 9, width, 15, 6, "rgba(255,255,255,.95)");
  ctx.fillStyle = "rgba(255,255,255,.95)";
  ctx.beginPath(); // the little tail of the bubble
  ctx.moveTo(p.x - 3.5, p.y + 6);
  ctx.lineTo(p.x + 3.5, p.y + 6);
  ctx.lineTo(p.x, p.y + 10);
  ctx.fill();
  // a guest who changed their mind thinks in the warm colour
  ctx.fillStyle = view.guest.switched ? "#c25a42" : "#183740";
  ctx.textAlign = "center";
  ctx.fillText(text, p.x, p.y + 1.5, width - 8);
}

function drawGuest(view, t, thinking) {
  const guest = view.guest;
  const shirts = SHIRTS[guest.kind] ?? SHIRTS.students;
  drawPersonFigure(view.x, view.y, t, guest.id + 50, {
    color: shirts[guest.id % shirts.length],
    phase: guest.id * 0.37,
    moving: view.moving,
    facing: view.facing,
    pose: view.moving ? "walk" : guest.id % 3 === 0 ? "phone" : "idle",
  });
  if (thinking) drawThought(view);
}

export function guestActors(t) {
  step(t);
  const actors = [];
  for (const view of [...shown.values(), ...leaving.values()]) {
    if (!visible(view)) continue;
    const near = Math.hypot(scene.player.x - view.x, scene.player.y - view.y) < NEAR_PLAYER;
    const long = view.guest.switched ? SWITCH_THOUGHT_MS : THOUGHT_MS;
    const thinking = shown.has(view.guest.id) && (near || t - view.seenAt < long);
    actors.push({ depth: depthOf(view.x, view.y) + 0.02, draw: () => drawGuest(view, t, thinking) });
  }
  return actors;
}

// are guests about today? (the passers-by step aside while they are)
export const guestsAbout = () => Boolean(server.guests);
