// The rooms inside the buildings.
// Drawing code taken from Felix Antes' Nova Beach Ventures
// (https://github.com/felix-anthes-png/nova-beach-ventures), reduced to what this game uses.

import { drawCampusWing } from "./campus.js";
import {
  WORLD_MATERIALS,
  drawBlock,
  drawConcreteSeams,
  drawFacadeBandX,
  drawFacadeBandY,
  drawGroundSlab,
  drawLinearPlanter,
  drawRaisedSlab,
  drawSoftShadow,
  drawTimberScreen,
  mixColor,
  roundedRect,
} from "./primitives.js";
import { TILE_H, TILE_W, activeZone, ctx, isoPoint, world } from "./scene.js";

export function drawInteriorFloor(zone) {
  const base = zone.id === "academy" ? "#e9e5da" : zone.id === "mercado" ? "#e2ddd0" : "#dfe7e2";
  drawGroundSlab(1.1, 1.1, 12.8, 9.15, base, 4);
  drawConcreteSeams(1.1, 1.1, 12.8, 9.15, 5, 1.25);
  const accent = zone.id === "academy" ? "#d7e7dd" : zone.id === "mercado" ? "#ead9b8" : "#cae0dc";
  drawGroundSlab(2.1, 2.05, 10.8, 1.15, accent, 5);
  for (let i = 0; i < 6; i++) {
    const p = isoPoint(2.6 + i * 1.75, 2.6, 6);
    ctx.strokeStyle = i % 2 ? "rgba(255,255,255,.62)" : "rgba(25,72,75,.12)";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(p.x - 22, p.y - 10);
    ctx.lineTo(p.x + 22, p.y + 10);
    ctx.stroke();
  }
  if (zone.id === "academy") {
    drawGroundSlab(1.7, 6.5, 11.6, 1.35, "#d6c19a", 5);
  } else if (zone.id === "mercado") {
    drawGroundSlab(1.65, 5.6, 11.7, 0.65, "#c9d4cd", 5);
  } else {
    drawGroundSlab(6.55, 3.7, 1.3, 5.7, "#b8d6d3", 5);
  }
  drawInteriorWayfinding(zone.id);
}

export function drawInteriorWayfinding(zoneId) {
  const layout = world.interiors[zoneId];
  if (!layout) return;
  ctx.save();
  for (const area of layout.areas) {
    const a = isoPoint(area.x, area.y + area.h, 6),
      b = isoPoint(area.x + area.w, area.y + area.h, 6);
    ctx.strokeStyle = area.color;
    ctx.globalAlpha = 0.72;
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();
    const label = isoPoint(area.x + 0.18, area.y + area.h - 0.1, 7);
    ctx.fillStyle = "#173743";
    ctx.font = "800 5px Menlo, Consolas, monospace";
    ctx.textAlign = "left";
    ctx.fillText(area.label.toUpperCase(), label.x, label.y);
  }
  ctx.globalAlpha = 0.46;
  ctx.strokeStyle = "#31545b";
  ctx.lineWidth = 3;
  ctx.setLineDash([7, 6]);
  for (let index = 1; index < layout.route.length; index++) {
    const a = isoPoint(layout.route[index - 1].x, layout.route[index - 1].y, 7),
      b = isoPoint(layout.route[index].x, layout.route[index].y, 7);
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();
  }
  ctx.setLineDash([]);
  const entry = isoPoint(layout.route[0].x, layout.route[0].y, 7);
  ctx.fillStyle = activeZone().accent;
  ctx.globalAlpha = 0.9;
  ctx.beginPath();
  ctx.ellipse(entry.x, entry.y, 30, 10, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = "#173743";
  ctx.font = "900 5px Menlo, Consolas, monospace";
  ctx.textAlign = "center";
  ctx.fillText("ENTRANCE", entry.x, entry.y + 2);
  ctx.restore();
}

export function drawIndoorPlant(x, y, scale = 1) {
  drawBlock(x - 0.32, y - 0.32, 0.64, 0.64, 18, "#d7cfc1", "#8e8f87", "#aaa99f");
  const p = isoPoint(x, y, 20);
  ctx.save();
  ctx.translate(p.x, p.y);
  ctx.scale(scale, scale);
  ctx.strokeStyle = "#4c7654";
  ctx.lineWidth = 2;
  for (let i = 0; i < 6; i++) {
    ctx.save();
    ctx.rotate((i * Math.PI) / 3);
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.quadraticCurveTo(8, -9, 4, -19);
    ctx.stroke();
    ctx.restore();
  }
  ctx.restore();
}

export function drawCommunalTable(x, y, w = 3.2, color = "#cfa670") {
  drawRaisedSlab(
    x,
    y,
    w,
    0.75,
    29,
    6,
    color,
    mixColor(color, "#000000", 0.32),
    mixColor(color, "#000000", 0.19),
  );
  ctx.strokeStyle = "#274a52";
  ctx.lineWidth = 3;
  [x + 0.3, x + w - 0.3].forEach((px) => {
    const a = isoPoint(px, y + 0.36, 0),
      b = isoPoint(px, y + 0.36, 23);
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();
  });
  for (let i = 0; i < 3; i++) {
    const px = x + 0.55 + (i * (w - 1.1)) / 2;
    drawBlock(px - 0.22, y - 0.55, 0.44, 0.42, 13, "#31545b", "#223e45", "#29484f");
    drawBlock(px - 0.22, y + 0.88, 0.44, 0.42, 13, "#31545b", "#223e45", "#29484f");
  }
}

export function drawCafeWorkshop() {
  drawRaisedSlab(5.65, 2.15, 4.3, 0.85, 38, 8, "#d5b37b", "#82694b", "#9f8159");
  drawFacadeBandY(5.8, 3.01, 4, 10, 31, "#244e58", 5);
  const machine = isoPoint(8.7, 2.7, 49);
  ctx.fillStyle = "#ecede7";
  roundedRect(machine.x - 17, machine.y - 16, 34, 19, 4, "#ecede7");
  ctx.fillStyle = "#173743";
  ctx.fillRect(machine.x - 10, machine.y - 11, 20, 5);
  ctx.fillStyle = "#ff7458";
  ctx.beginPath();
  ctx.arc(machine.x + 11, machine.y - 8, 2, 0, Math.PI * 2);
  ctx.fill();
  const shelf = isoPoint(8, 1.6, 47);
  ctx.strokeStyle = "#b48a56";
  ctx.lineWidth = 5;
  ctx.beginPath();
  ctx.moveTo(shelf.x - 64, shelf.y);
  ctx.lineTo(shelf.x + 64, shelf.y + 32);
  ctx.stroke();
  for (let i = 0; i < 6; i++) {
    ctx.fillStyle = i % 2 ? "#f5c95e" : "#64cbc8";
    ctx.beginPath();
    ctx.arc(shelf.x - 47 + i * 18, shelf.y + 7 + i * 4, 4, 0, Math.PI * 2);
    ctx.fill();
  }
  drawRaisedSlab(5.8, 3.05, 1.15, 0.65, 31, 6, "#f0ece1", "#788c8c", "#a8b3af");
  const display = isoPoint(6.38, 3.38, 34);
  ctx.fillStyle = "rgba(171,224,220,.72)";
  ctx.beginPath();
  ctx.moveTo(display.x - 23, display.y - 9);
  ctx.lineTo(display.x + 23, display.y + 2);
  ctx.lineTo(display.x + 23, display.y - 13);
  ctx.lineTo(display.x - 23, display.y - 24);
  ctx.closePath();
  ctx.fill();
  for (let i = 0; i < 4; i++) {
    ctx.fillStyle = i % 2 ? "#e6a953" : "#c9874e";
    ctx.beginPath();
    ctx.ellipse(display.x - 14 + i * 9, display.y - 10 + i * 2, 4, 2, 0, 0, Math.PI * 2);
    ctx.fill();
  }
  const menu = isoPoint(6.2, 1.12, 68);
  ctx.save();
  ctx.translate(menu.x, menu.y);
  ctx.rotate(Math.atan2(TILE_H / 2, TILE_W / 2));
  roundedRect(-46, -19, 92, 38, 3, "#173743");
  ctx.fillStyle = "#f5c95e";
  ctx.font = "900 6px Menlo, Consolas, monospace";
  ctx.fillText("SNACK STAND", -37, -7);
  ctx.fillStyle = "#e5efeb";
  for (let i = 0; i < 3; i++) {
    ctx.fillRect(-36, 2 + i * 7, 34 + i * 7, 2);
  }
  ctx.restore();
}

export function drawMercadoShelf(x, y, w = 3.1) {
  drawBlock(x, y, w, 0.62, 58, "#f1efe7", "#8e9996", "#b8bfba");
  for (let z = 15; z < 55; z += 17) {
    drawFacadeBandY(x + 0.15, y + 0.63, w - 0.3, z, z + 6, "#31545b", Math.max(3, Math.round(w)));
  }
  const colors = ["#f5c95e", "#ff7458", "#64cbc8", "#bce65f"];
  for (let i = 0; i < 4; i++) {
    const p = isoPoint(x + 0.5 + (i * (w - 1)) / 3, y + 0.68, 31);
    ctx.fillStyle = colors[i];
    ctx.fillRect(p.x - 4, p.y - 5, 8, 9);
  }
}

export function drawMercadoDispatch() {
  drawRaisedSlab(6.4, 3.78, 2.2, 0.82, 32, 7, "#d9bb83", "#745e46", "#947657");
  const scanner = isoPoint(7.55, 4.05, 39);
  roundedRect(scanner.x - 8, scanner.y - 13, 16, 17, 3, "#173743");
  ctx.fillStyle = "#bce65f";
  ctx.fillRect(scanner.x - 4, scanner.y - 9, 8, 5);
  for (const [x, y, color] of [
    [6.1, 5.2, "#d0a05e"],
    [8.8, 6.5, "#c98b55"],
    [5.3, 7.25, "#e0b978"],
  ]) {
    drawBlock(
      x - 0.35,
      y - 0.3,
      0.7,
      0.6,
      24,
      color,
      mixColor(color, "#000000", 0.35),
      mixColor(color, "#000000", 0.2),
    );
    const p = isoPoint(x, y, 26);
    ctx.strokeStyle = "rgba(69,51,35,.45)";
    ctx.beginPath();
    ctx.moveTo(p.x - 10, p.y - 4);
    ctx.lineTo(p.x + 10, p.y + 6);
    ctx.stroke();
  }
}

export function drawColdRoom() {
  drawCampusWing(9.7, 2.05, 3.15, 2.25, 65, { glass: "#326a74", accent: "#64cbc8" });
  const p = isoPoint(11.3, 4.32, 37);
  roundedRect(p.x - 26, p.y - 8, 52, 16, 3, "#173743");
  ctx.fillStyle = "#d8fbff";
  ctx.textAlign = "center";
  ctx.font = "800 6px Menlo, Consolas, monospace";
  ctx.fillText("COLD STORE", p.x, p.y + 2);
}

export function drawLounge(x, y, color = "#6f9294") {
  drawBlock(
    x,
    y,
    2.5,
    0.8,
    19,
    mixColor(color, "#ffffff", 0.2),
    mixColor(color, "#000000", 0.35),
    mixColor(color, "#000000", 0.2),
  );
  drawRaisedSlab(
    x - 0.1,
    y - 0.04,
    2.7,
    0.28,
    37,
    8,
    mixColor(color, "#ffffff", 0.1),
    mixColor(color, "#000000", 0.38),
    mixColor(color, "#000000", 0.22),
  );
  drawBlock(x + 0.85, y + 1.05, 0.75, 0.75, 14, "#d5b170", "#846944", "#9d7c50");
}

export function drawVentureDesk() {
  drawRaisedSlab(9.55, 4.78, 1.9, 0.82, 31, 7, "#d5b271", "#745d42", "#95754e");
  const screens = [
    [10, 4.8],
    [10.55, 5.12],
    [11, 4.88],
  ];
  for (const [x, y] of screens) {
    const p = isoPoint(x, y, 48);
    roundedRect(p.x - 9, p.y - 9, 18, 13, 2, "#173743");
    ctx.fillStyle = "#bce65f";
    ctx.fillRect(p.x - 5, p.y - 5, 10, 2);
    ctx.fillStyle = "#64cbc8";
    ctx.fillRect(p.x - 5, p.y - 1, 7, 2);
  }
}

export function drawVentureWall() {
  const p = isoPoint(10.8, 1.08, 63);
  ctx.save();
  ctx.translate(p.x, p.y);
  ctx.rotate(Math.atan2(TILE_H / 2, TILE_W / 2));
  roundedRect(-64, -27, 128, 54, 4, "#173743");
  ctx.fillStyle = "#bce65f";
  ctx.font = "800 7px Menlo, Consolas, monospace";
  ctx.fillText("VENTURE BOARD", -52, -11);
  ctx.fillStyle = "#d9e5e1";
  for (let i = 0; i < 4; i++) {
    ctx.fillRect(-50, -1 + i * 8, 32 + i * 8, 3);
  }
  ctx.restore();
}

export function drawRoomShell(zone) {
  drawSoftShadow(zone.width * 0.55, 1.4, 150, 20, 0.2);
  drawBlock(0, 0, zone.width, 1, 105, WORLD_MATERIALS.chalk, "#a7b5b0", "#c7cdc8");
  drawBlock(0, 0, 1, zone.height, 88, "#f7f3e9", "#95a6a2", "#bec7c2");
  drawFacadeBandY(1.1, 1.02, zone.width - 1.3, 18, 72, "#2c5c65", 9);
  drawFacadeBandX(1.02, 1.1, zone.height - 1.3, 17, 65, "#244e58", 7);
  drawTimberScreen(1.35, 1.04, zone.width - 1.8, 76, 101, 14);
  for (let i = 0; i < 5; i++) {
    const a = isoPoint(2 + i * 2.6, 1.18, 82),
      b = isoPoint(2.9 + i * 2.6, 1.18, 82);
    ctx.strokeStyle = i % 2 ? "#f5c95e" : "#d9f4ee";
    ctx.lineWidth = 3.5;
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();
  }
  drawLinearPlanter(1.35, 1.45, 2.55, 0.5, 12);
  drawLinearPlanter(11.15, 1.45, 2.1, 0.5, 12);
  const p = isoPoint(zone.width / 2, 0.75, 91);
  roundedRect(p.x - 72, p.y - 10, 144, 20, 4, "#173743");
  ctx.fillStyle = zone.accent;
  ctx.fillRect(p.x - 64, p.y - 10, 5, 20);
  ctx.fillStyle = "#fff";
  ctx.textAlign = "center";
  ctx.font = "800 8px Menlo, Consolas, monospace";
  ctx.fillText(zone.name.toUpperCase(), p.x + 4, p.y + 3);
}

export function roomActors() {
  const zone = activeZone();
  const actors = [
    { depth: 0.1, draw: () => drawInteriorFloor(zone) },
    { depth: 1, draw: () => drawRoomShell(zone) },
  ];
  if (zone.id === "academy") {
    actors.push(
      { depth: 4.7, draw: drawCafeWorkshop },
      { depth: 8.1, draw: () => drawCommunalTable(2.1, 5.65, 3.5, "#d2a66c") },
      { depth: 14.1, draw: () => drawCommunalTable(9.9, 4.2, 3, "#d2a66c") },
      { depth: 10.5, draw: () => drawLounge(2.2, 7.25, "#608a8b") },
      { depth: 12.9, draw: () => drawIndoorPlant(11.8, 7.2, 1.2) },
    );
  } else if (zone.id === "mercado") {
    actors.push(
      { depth: 5.1, draw: () => drawMercadoShelf(2.05, 2.45, 4) },
      { depth: 9.3, draw: () => drawMercadoShelf(2.1, 6.55, 3.6) },
      { depth: 12, draw: drawColdRoom },
      { depth: 8.9, draw: drawMercadoDispatch },
      { depth: 16.2, draw: () => drawMercadoShelf(10.1, 6.1, 2.8) },
      { depth: 10, draw: () => drawIndoorPlant(7.6, 7.7, 0.9) },
    );
  } else {
    actors.push(
      { depth: 15.3, draw: drawVentureDesk },
      { depth: 11.8, draw: () => drawLounge(2.15, 7, "#7c70a2") },
      { depth: 15.2, draw: () => drawLounge(9.8, 6.1, "#568c8c") },
      { depth: 12, draw: drawVentureWall },
      { depth: 10.7, draw: () => drawIndoorPlant(7.8, 6.9, 1.1) },
    );
  }
  return actors;
}
