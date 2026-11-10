// Basic shapes of the 2.5D world: tiles, blocks, slabs, signs. Everything is drawn on the canvas.
// Drawing code taken from Felix Antes' Nova Beach Ventures
// (https://github.com/felix-anthes-png/nova-beach-ventures), reduced to what this game uses.

import { DEPTH, TILE, ctx, isoPoint, scene } from "./scene.js";

export function roundedRect(x, y, w, h, r, fill) {
  ctx.beginPath();
  ctx.roundRect(x, y, w, h, r);
  ctx.fillStyle = fill;
  ctx.fill();
}

export function mixColor(a, b, amount) {
  const value = (color) => color.match(/\w\w/g).map((hex) => parseInt(hex, 16)),
    x = value(a),
    y = value(b);
  return `rgb(${x.map((channel, index) => Math.round(channel + (y[index] - channel) * amount)).join(",")})`;
}

export function drawTile(x, y, color, depth = 0) {
  const a = isoPoint(x, y),
    b = isoPoint(x + 1, y),
    c = isoPoint(x + 1, y + 1),
    d = isoPoint(x, y + 1);
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.moveTo(a.x, a.y);
  ctx.lineTo(b.x, b.y);
  ctx.lineTo(c.x, c.y);
  ctx.lineTo(d.x, d.y);
  ctx.closePath();
  ctx.fill();
  ctx.strokeStyle = "rgba(20,48,45,.035)";
  ctx.lineWidth = 0.65;
  ctx.stroke();
  if (depth) {
    ctx.fillStyle = "rgba(45,67,54,.16)";
    ctx.beginPath();
    ctx.moveTo(d.x, d.y);
    ctx.lineTo(c.x, c.y);
    ctx.lineTo(c.x, c.y + depth);
    ctx.lineTo(d.x, d.y + depth);
    ctx.closePath();
    ctx.fill();
  }
}

export function drawPlane(points, fill, stroke = "rgba(8,42,51,.13)", lineWidth = 0.8) {
  ctx.beginPath();
  points.forEach((point, index) => (index ? ctx.lineTo(point.x, point.y) : ctx.moveTo(point.x, point.y)));
  ctx.closePath();
  ctx.fillStyle = fill;
  ctx.fill();
  if (stroke) {
    ctx.strokeStyle = stroke;
    ctx.lineWidth = lineWidth;
    ctx.stroke();
  }
}

export function drawGroundSlab(x, y, w, h, color = "#e9e6db", depth = 3) {
  drawBlock(x, y, w, h, depth, color, mixColor(color, "#000000", 0.18), mixColor(color, "#000000", 0.1));
}

export function drawRaisedSlab(
  x,
  y,
  w,
  h,
  z,
  thickness = 4,
  top = "#f5f3eb",
  right = "#aeb8b4",
  left = "#c7ccc8",
) {
  const a = isoPoint(x, y, z),
    b = isoPoint(x + w, y, z),
    c = isoPoint(x + w, y + h, z),
    d = isoPoint(x, y + h, z),
    bb = isoPoint(x + w, y, z - thickness),
    bc = isoPoint(x + w, y + h, z - thickness),
    bd = isoPoint(x, y + h, z - thickness);
  drawPlane([d, c, bc, bd], left);
  drawPlane([b, c, bc, bb], right);
  drawPlane([a, b, c, d], top);
}

export const WORLD_MATERIALS = {
  chalk: "#f4f1e8",
  chalkShade: "#c8cec9",
  glass: "#174a58",
  glassLight: "#2c6972",
  timber: "#b78352",
  coral: "#ed7458",
  lime: "#bce65f",
  sand: "#dfc58c",
  ink: "#12343e",
};

// The shadow under a footprint of w × h tiles centred on (x, y), a little wider than the footprint.
export function drawFootprintShadow(x, y, w, h, alpha = 0.16, spread = 1.1) {
  drawSoftShadow(x, y, (w * TILE * spread) / 2, (h * DEPTH * spread) / 2, alpha);
}

export function drawSoftShadow(x, y, rx = 42, ry = 15, alpha = 0.16) {
  // One plain ellipse. It used a canvas blur filter (2px) before, which cost 66 to 160 ms a frame
  // on a big canvas (35 shadows); a second ellipse for a soft edge cost about 4 ms more.
  const p = isoPoint(x, y, 1);
  ctx.save();
  ctx.fillStyle = `rgba(8,32,37,${alpha})`;
  ctx.beginPath();
  ctx.ellipse(p.x + 4, p.y + 5, rx, ry, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
}

export function drawConcreteSeams(x, y, w, h, z = 6, step = 1.4) {
  ctx.save();
  ctx.strokeStyle = "rgba(20,61,66,.1)";
  ctx.lineWidth = 0.7;
  for (let px = x + step; px < x + w; px += step) {
    const a = isoPoint(px, y, z),
      b = isoPoint(px, y + h, z);
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();
  }
  for (let py = y + step; py < y + h; py += step) {
    const a = isoPoint(x, py, z),
      b = isoPoint(x + w, py, z);
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();
  }
  ctx.restore();
}

export function drawColumnLine(x, y, length, count, z = 28, axis = "x", color = "#244b54", baseZ = 3) {
  ctx.save();
  ctx.strokeStyle = color;
  ctx.lineWidth = 2.2;
  for (let i = 0; i < count; i++) {
    const amount = count === 1 ? 0.5 : i / (count - 1),
      px = x + (axis === "x" ? length * amount : 0),
      py = y + (axis === "y" ? length * amount : 0),
      a = isoPoint(px, py, baseZ),
      b = isoPoint(px, py, z);
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();
  }
  ctx.restore();
}

export function drawLinearPlanter(x, y, w, h, z = 13) {
  // it must stand on the ground, not hover over it: a contact shadow, a darker footing and soil on top
  const g = 0.3;
  drawPlane(
    [isoPoint(x, y + h, 0), isoPoint(x + w, y + h, 0), isoPoint(x + w + g, y + h + g, 0), isoPoint(x + g, y + h + g, 0)],
    "rgba(30,44,44,.2)",
    null,
  );
  drawPlane(
    [isoPoint(x + w, y, 0), isoPoint(x + w + g, y + g, 0), isoPoint(x + w + g, y + h + g, 0), isoPoint(x + w, y + h, 0)],
    "rgba(30,44,44,.2)",
    null,
  );
  drawBlock(x - 0.05, y - 0.05, w + 0.1, h + 0.1, 3.5, "#b3ad9f", "#6f7a76", "#8e9792");
  drawBlock(x, y, w, h, z, "#d9d3c6", "#8d9792", "#adb2ab");
  drawPlane(
    [isoPoint(x + 0.07, y + 0.07, z), isoPoint(x + w - 0.07, y + 0.07, z), isoPoint(x + w - 0.07, y + h - 0.07, z), isoPoint(x + 0.07, y + h - 0.07, z)],
    "#6b5a45",
    null,
  );
  const count = Math.max(2, Math.round(w * 1.5));
  for (let i = 0; i < count; i++) {
    const p = isoPoint(x + 0.25 + ((w - 0.5) * i) / (count - 1), y + h * 0.5, z + 5 + (i % 2) * 2);
    ctx.fillStyle = i % 2 ? "#668a67" : "#4d765c";
    ctx.beginPath();
    ctx.ellipse(p.x, p.y, 8, 4.5, -0.2, 0, Math.PI * 2);
    ctx.fill();
  }
}

export function drawBladeSign(x, y, z, label, accent) {
  const p = isoPoint(x, y, z);
  ctx.save();
  ctx.strokeStyle = WORLD_MATERIALS.ink;
  ctx.lineWidth = 2.4;
  ctx.beginPath();
  ctx.moveTo(p.x, p.y + 18);
  ctx.lineTo(p.x, p.y - 11);
  ctx.stroke();
  roundedRect(p.x - 6, p.y - 19, 50, 17, 3, WORLD_MATERIALS.ink);
  ctx.fillStyle = accent;
  ctx.textAlign = "center";
  ctx.font = "900 5px Menlo, Consolas, monospace";
  ctx.fillText(label, p.x + 19, p.y - 8);
  ctx.restore();
}

export function drawSpaceCaption(x, y, label, accent = "#31545b") {
  const p = isoPoint(x, y, 7);
  ctx.save();
  ctx.translate(p.x, p.y);
  ctx.textAlign = "left";
  ctx.font = "800 5px Menlo, Consolas, monospace";
  ctx.fillStyle = accent;
  ctx.globalAlpha = 0.72;
  ctx.fillText(label.toUpperCase(), 0, 0);
  ctx.restore();
}

export function drawPavingInlay(x, y, w, h, color = "#f1ede3", step = 1.25) {
  drawGroundSlab(x, y, w, h, color, 5);
  ctx.save();
  ctx.strokeStyle = "rgba(27,65,68,.11)";
  ctx.lineWidth = 0.75;
  for (let px = x + step; px < x + w; px += step) {
    const a = isoPoint(px, y, 7),
      b = isoPoint(px, y + h, 7);
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();
  }
  ctx.restore();
}

export function drawFacadeBandY(x, y, w, zBottom, zTop, color = "#244e58", mullions = 5) {
  drawPlane(
    [isoPoint(x, y, zTop), isoPoint(x + w, y, zTop), isoPoint(x + w, y, zBottom), isoPoint(x, y, zBottom)],
    color,
    "rgba(255,255,255,.2)",
  );
  ctx.strokeStyle = "rgba(222,244,244,.42)";
  ctx.lineWidth = 0.8;
  for (let i = 1; i < mullions; i++) {
    const px = x + (w * i) / mullions,
      a = isoPoint(px, y, zBottom + 2),
      b = isoPoint(px, y, zTop - 2);
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();
  }
}

// A band on a face that runs along y (an east or west face). The camera looks from the south
// (spec map-view), so such a face is seen edge-on and there is nothing to draw. The callers stay, so the
// buildings keep their full description.
export function drawFacadeBandX() {}

export function drawBlock(x, y, w, h, z, top, right, left) {
  const a = isoPoint(x, y, z),
    b = isoPoint(x + w, y, z),
    c = isoPoint(x + w, y + h, z),
    d = isoPoint(x, y + h, z),
    ba = isoPoint(x, y),
    bb = isoPoint(x + w, y),
    bc = isoPoint(x + w, y + h),
    bd = isoPoint(x, y + h);
  ctx.fillStyle = left;
  ctx.beginPath();
  ctx.moveTo(d.x, d.y);
  ctx.lineTo(c.x, c.y);
  ctx.lineTo(bc.x, bc.y);
  ctx.lineTo(bd.x, bd.y);
  ctx.closePath();
  ctx.fill();
  ctx.fillStyle = right;
  ctx.beginPath();
  ctx.moveTo(b.x, b.y);
  ctx.lineTo(c.x, c.y);
  ctx.lineTo(bc.x, bc.y);
  ctx.lineTo(bb.x, bb.y);
  ctx.closePath();
  ctx.fill();
  ctx.fillStyle = top;
  ctx.beginPath();
  ctx.moveTo(a.x, a.y);
  ctx.lineTo(b.x, b.y);
  ctx.lineTo(c.x, c.y);
  ctx.lineTo(d.x, d.y);
  ctx.closePath();
  ctx.fill();
  ctx.strokeStyle = "rgba(15,35,40,.22)";
  ctx.stroke();
}

export function drawWorldLabel(x, y, z, title, accent = "#bce65f") {
  if (scene.zoneId === "campus" && Math.hypot(scene.player.x - x, scene.player.y - y) > 5.4) return;
  const p = isoPoint(x, y, z);
  ctx.save();
  ctx.shadowColor = "rgba(3,22,28,.25)";
  ctx.shadowBlur = 12;
  roundedRect(p.x - 45, p.y - 9, 90, 18, 9, "rgba(7,29,37,.86)");
  ctx.shadowBlur = 0;
  ctx.fillStyle = accent;
  ctx.beginPath();
  ctx.arc(p.x - 35, p.y, 3, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = "#fff";
  ctx.textAlign = "center";
  ctx.font = "700 6px Menlo, Consolas, monospace";
  ctx.fillText(title, p.x + 4, p.y + 2);
  ctx.restore();
}
