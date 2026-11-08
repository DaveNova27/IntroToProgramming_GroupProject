// The places the player can use: desks that open a screen.
// Which places exist comes from the server (world.py).

import { roundedRect } from "./primitives.js";
import { ctx, isoPoint, scene, world } from "./scene.js";

const MONO = "Menlo, Consolas, monospace";
const REACH = 1.65; // tiles

const distanceToPlayer = (loc) => Math.hypot(scene.player.x - loc.x, scene.player.y - loc.y);

export const locationsHere = () => Object.entries(world.locations).filter(([, loc]) => loc.zone === scene.zoneId);

export const inReach = (loc) => distanceToPlayer(loc) < REACH;

export function nearestLocation() {
  const near = locationsHere().filter(([, loc]) => inReach(loc));
  near.sort((a, b) => distanceToPlayer(a[1]) - distanceToPlayer(b[1]));
  return near[0] ?? null;
}

function drawTag(loc, height, text) {
  const tag = isoPoint(loc.x, loc.y, height);
  roundedRect(tag.x - 50, tag.y - 10, 100, 20, 4, "rgba(10,37,46,.92)");
  ctx.fillStyle = loc.color;
  ctx.beginPath();
  ctx.arc(tag.x - 40, tag.y, 3, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = "#fff";
  ctx.textAlign = "center";
  ctx.font = `700 6px ${MONO}`;
  ctx.fillText(text, tag.x + 4, tag.y + 2);
}

function drawDesk(loc, near) {
  const p = isoPoint(loc.x, loc.y, 8);
  ctx.save();
  ctx.globalAlpha = 0.92;
  ctx.strokeStyle = loc.color;
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.ellipse(p.x, p.y, 30, 11, 0, 0, Math.PI * 2);
  ctx.stroke();
  ctx.fillStyle = "rgba(255,255,255,.82)";
  ctx.beginPath();
  ctx.ellipse(p.x, p.y, 24, 8, 0, 0, Math.PI * 2);
  ctx.fill();
  const badge = isoPoint(loc.x, loc.y, 47);
  roundedRect(badge.x - 30, badge.y - 7, 60, 14, 6, "#173743");
  ctx.fillStyle = loc.color;
  ctx.textAlign = "center";
  ctx.font = `900 5px ${MONO}`;
  ctx.fillText(loc.sub, badge.x, badge.y + 2);
  ctx.restore();
  if (near) {
    const q = isoPoint(loc.x, loc.y, 3);
    ctx.strokeStyle = "#ffd454";
    ctx.lineWidth = 3;
    ctx.setLineDash([7, 5]);
    ctx.beginPath();
    ctx.ellipse(q.x, q.y, 55 + Math.sin(scene.time * 0.004) * 2, 20, 0, 0, Math.PI * 2);
    ctx.stroke();
    ctx.setLineDash([]);
    drawTag(loc, 76, loc.title);
  }
}

export function drawLocation(id) {
  const loc = world.locations[id];
  drawDesk(loc, inReach(loc));
}
