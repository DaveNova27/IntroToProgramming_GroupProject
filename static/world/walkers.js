// People walking around the campus. Only decoration, so the campus looks alive:
// they buy nothing and no rule reads them. Real customers are the spec `guests` (guests.js):
// while a shift runs and they are about, only a few passers-by stay out.
// Everything comes from the walker's number, so it needs no random numbers.

import { guestsAbout } from "./guests.js";
import { findPath } from "./paths.js";
import { drawPersonFigure } from "./people.js";
import { nearestFreePoint } from "./physics.js";
import { PLAYER_RADIUS, depthOf, reducedMotion, world } from "./scene.js";

const COUNT = 14;
const COUNT_WITH_GUESTS = 10; // passers-by left while the guests of a running shift walk (the others make room)
const SPEED = 1.45; // tiles per second
const SHIRTS = ["#f5c95e", "#ff8060", "#64cbc8", "#9a7bc1", "#e6a769", "#f0e9dc", "#7fb0d8"];
const POSES = ["idle", "phone", "chat", "eat", "drink", "browse"];

const walkers = [];

// a number from 0 to 1 that always comes out the same for the same input
function dice(n) {
  const value = Math.sin((n + 1) * 91.733) * 43758.5453;
  return value - Math.floor(value);
}

function spot(walker) {
  const spaces = Object.values(world.spaces);
  const space = spaces[Math.floor(dice(walker.index * 31 + walker.trips) * spaces.length)];
  const wanted = {
    x: space.x + (dice(walker.index + walker.trips * 7) - 0.5) * 2.4,
    y: space.y + (dice(walker.index * 3 + walker.trips * 5) - 0.5) * 1.6,
  };
  return nearestFreePoint(wanted, world.zones.campus, world.colliders.campus, PLAYER_RADIUS);
}

function pause(walker) {
  walker.waiting = 2 + dice(walker.index * 13 + walker.trips) * 6;
  walker.pose = POSES[Math.floor(dice(walker.index * 17 + walker.trips) * POSES.length)];
}

export function createWalkers() {
  for (let index = 0; index < COUNT; index++) {
    const walker = { index, trips: 0, route: [], waiting: 0, pose: "idle", facing: { x: 0, y: 1 }, moving: false };
    Object.assign(walker, spot(walker));
    walker.trips = 1;
    pause(walker);
    walker.waiting *= dice(index * 19); // not all set off at the same moment
    walkers.push(walker);
  }
}

function setOff(walker) {
  walker.route = findPath(walker, spot(walker), world.zones.campus, world.colliders.campus, PLAYER_RADIUS) ?? [];
  walker.trips += 1;
}

export function updateWalkers(dt) {
  if (reducedMotion) return;
  for (const walker of walkers) {
    if (walker.waiting > 0) {
      walker.waiting -= dt;
      walker.moving = false;
      if (walker.waiting <= 0) setOff(walker);
      continue;
    }
    const next = walker.route[0];
    if (!next) {
      pause(walker);
      continue;
    }
    const dx = next.x - walker.x;
    const dy = next.y - walker.y;
    const distance = Math.hypot(dx, dy);
    walker.moving = true;
    if (distance <= SPEED * dt) {
      walker.x = next.x;
      walker.y = next.y;
      walker.route.shift();
    } else {
      walker.facing = { x: dx / distance, y: dy / distance };
      walker.x += walker.facing.x * SPEED * dt;
      walker.y += walker.facing.y * SPEED * dt;
    }
  }
}

export function walkerActors(t) {
  const count = guestsAbout() ? COUNT_WITH_GUESTS : COUNT;
  return walkers.slice(0, count).map((walker) => ({
    depth: depthOf(walker.x, walker.y),
    draw: () =>
      drawPersonFigure(walker.x, walker.y, t, walker.index + 1, {
        color: SHIRTS[walker.index % SHIRTS.length],
        phase: walker.index * 0.7,
        moving: walker.moving,
        facing: walker.facing,
        pose: walker.moving ? "walk" : walker.pose,
      }),
  }));
}
