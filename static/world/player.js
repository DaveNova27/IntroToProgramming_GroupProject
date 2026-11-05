// The player on the map: the same figure as everyone else, with a ring around it.

import { drawPersonFigure } from "./people.js";
import { ctx, isoPoint, scene } from "./scene.js";

export function drawPlayer(t) {
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
