// The player on the map. A simple marker: `world-art` gives it a real figure.

import { ctx, isoPoint, scene } from "./scene.js";

export function drawPlayer() {
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
  ctx.fillStyle = "#bce65f";
  ctx.beginPath();
  ctx.roundRect(-7, -38, 14, 38, 7);
  ctx.fill();
  ctx.strokeStyle = "#173743";
  ctx.stroke();
  ctx.restore();
}
