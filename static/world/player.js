// The player on the map: the same figure as everyone else, with a ring around it.
// At night (spec day-cycle) the player lies in the Dorm's bed under the blanket instead.

import { drawPersonFigure } from "./people.js";
import { drawRaisedSlab } from "./primitives.js";
import { ctx, isoPoint, scene, world } from "./scene.js";

const bedOf = () => world.dorm?.interior.solid.find((item) => item.id === "dorm-bed");

// drawn right after the bed while sleeping, so nothing in front of the bed covers the sleeper wrongly
export function playerDepth() {
  const bed = scene.sleeping && bedOf();
  if (bed) return bed.x + bed.w / 2 + bed.y + bed.h + 0.02;
  return scene.player.x + scene.player.y;
}

function drawSleeper(t, bed) {
  const x = bed.x + bed.w / 2;
  // the feet near the foot of the bed, the head on the pillows at the north wall
  drawPersonFigure(x, bed.y + bed.h - 0.3, t, 0, { pose: "lie", facing: { x: 0, y: 1 }, player: true, z: 23 });
  // the blanket pulled up to the chest, in the colours of the bed's blanket (rooms.js)
  const top = bed.y + 0.95;
  drawRaisedSlab(bed.x + 0.04, top, bed.w - 0.08, bed.y + bed.h - top - 0.01, 25, 4, "#ff8a6e", "#c25a42", "#e06d52");
}

export function drawPlayer(t) {
  const bed = scene.sleeping && bedOf();
  if (bed) return drawSleeper(t, bed);
  const p = isoPoint(scene.player.x, scene.player.y, 4);
  ctx.save();
  ctx.translate(p.x, p.y);
  ctx.fillStyle = "rgba(7,29,37,.22)";
  ctx.beginPath();
  ctx.ellipse(0, 3, 18, 7, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = "rgba(255,255,255,.9)";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.ellipse(0, 2, 23, 9, 0, 0, Math.PI * 2);
  ctx.stroke();
  ctx.restore();
  drawPersonFigure(scene.player.x, scene.player.y, t, 0, {
    phase: 0,
    moving: scene.walking,
    facing: scene.facing,
    pose: scene.walking ? "walk" : "idle",
    player: true,
  });
}
