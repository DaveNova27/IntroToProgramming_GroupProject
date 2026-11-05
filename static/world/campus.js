// The outdoor campus: ground, public spaces and buildings.
// Drawing code taken from Felix Antes' Nova Beach Ventures
// (https://github.com/felix-anthes-png/nova-beach-ventures), reduced to what this game uses.

import { drawTree, drawWindFlag, environmentalProfile } from "./environment.js";
import {
  WORLD_MATERIALS,
  drawBladeSign,
  drawBlock,
  drawColumnLine,
  drawConcreteSeams,
  drawFacadeBandX,
  drawFacadeBandY,
  drawGroundSlab,
  drawLinearPlanter,
  drawPavingInlay,
  drawPlane,
  drawRaisedSlab,
  drawSoftShadow,
  drawSpaceCaption,
  drawTile,
  drawTimberScreen,
  drawWorldLabel,
  mixColor,
} from "./primitives.js";
import {
  TILE_H,
  TILE_W,
  activeZone,
  camera,
  canvas,
  ctx,
  isoPoint,
  reducedMotion,
  scene,
  world,
} from "./scene.js";

export function drawTerrain(t) {
  const zone = activeZone(),
    tiles = [],
    center = isoPoint(camera.x, camera.y),
    viewX = canvas.clientWidth / (2 * camera.zoom) + TILE_W * 2,
    viewY = canvas.clientHeight / (2 * camera.zoom) + TILE_H * 3;
  for (let y = 0; y < zone.height; y++)
    for (let x = 0; x < zone.width; x++) {
      const point = isoPoint(x, y);
      if (Math.abs(point.x - center.x) <= viewX && Math.abs(point.y - center.y) <= viewY)
        tiles.push({ x, y, d: x + y });
    }
  tiles.sort((a, b) => a.d - b.d);
  tiles.forEach(({ x, y }) => {
    let color = zone.floor || "#79aa67",
      depth = 4;
    if (zone.outdoor) {
      if (y >= 26) {
        color = x % 5 === 0 ? "#448fa0" : "#3f899b";
        depth = 0;
      } else if (y >= 23) color = x % 4 === 0 ? "#e4c986" : "#dec27e";
      else if ((y >= 8 && y < 18 && x >= 2 && x <= 39) || y >= 18)
        color = (Math.floor(x / 3) + Math.floor(y / 3)) % 2 ? "#d0d0c7" : "#ccccc3";
      else color = (Math.floor(x / 4) + Math.floor(y / 4)) % 2 ? "#7ca66b" : "#78a267";
    } else color = (x + y) % 2 ? zone.floor : mixColor(zone.floor, "#ffffff", 0.07);
    drawTile(x, y, color, depth);
    if (zone.outdoor && y === 25) {
      const p = isoPoint(x + 0.5, y + 0.5, 5);
      ctx.strokeStyle = "rgba(255,255,255,.55)";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(p.x - 24, p.y + Math.sin(t * 0.002 + x) * 2);
      ctx.lineTo(p.x + 24, p.y + Math.sin(t * 0.002 + x + 1) * 2);
      ctx.stroke();
    }
  });
}

export function drawCampusBench(x, y, rotation = 0, color = "#b98b59") {
  const horizontal = rotation % 2 === 0,
    w = horizontal ? 1.4 : 0.42,
    h = horizontal ? 0.42 : 1.4;
  drawRaisedSlab(x, y, w, h, 16, 5, color, "#76583e", "#96704c");
  const a = horizontal ? isoPoint(x + 0.12, y + h * 0.5, 0) : isoPoint(x + w * 0.5, y + 0.12, 0),
    b = horizontal ? isoPoint(x + w - 0.12, y + h * 0.5, 0) : isoPoint(x + w * 0.5, y + h - 0.12, 0);
  ctx.strokeStyle = "#274a52";
  ctx.lineWidth = 2.2;
  ctx.beginPath();
  ctx.moveTo(a.x, a.y);
  ctx.lineTo(a.x, a.y - 8);
  ctx.moveTo(b.x, b.y);
  ctx.lineTo(b.x, b.y - 8);
  ctx.stroke();
}

export function drawTerraceTable(x, y, accent = "#ed7458") {
  const p = isoPoint(x, y, 17);
  ctx.fillStyle = "#ede8da";
  ctx.beginPath();
  ctx.ellipse(p.x, p.y, 10, 5, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = "#31545b";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(p.x, p.y + 2);
  ctx.lineTo(p.x, p.y + 15);
  ctx.stroke();
  const environment = environmentalProfile(),
    canopy = isoPoint(x, y, 36),
    sway = reducedMotion ? 0 : Math.sin(scene.time * 0.0016 + x) * environment.wind * 2.2;
  ctx.fillStyle = accent;
  ctx.beginPath();
  ctx.moveTo(canopy.x - 13 + sway, canopy.y);
  ctx.lineTo(canopy.x + sway * 0.55, canopy.y - 7);
  ctx.lineTo(canopy.x + 13 + sway, canopy.y);
  ctx.closePath();
  ctx.fill();
  ctx.strokeStyle = "#31545b";
  ctx.beginPath();
  ctx.moveTo(canopy.x + sway * 0.35, canopy.y);
  ctx.lineTo(p.x, p.y);
  ctx.stroke();
}

export function drawPergola(x, y, w, h, accent = "#f5c95e") {
  const posts = [
    [x, y],
    [x + w, y],
    [x, y + h],
    [x + w, y + h],
  ];
  ctx.strokeStyle = "#31545b";
  ctx.lineWidth = 2.4;
  posts.forEach(([px, py]) => {
    const a = isoPoint(px, py, 4),
      b = isoPoint(px, py, 38);
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();
  });
  for (let i = 0; i < 5; i++) {
    const px = x + (w * i) / 4,
      a = isoPoint(px, y, 39),
      b = isoPoint(px, y + h, 39);
    ctx.strokeStyle = i % 2 ? accent : "#f5f1e6";
    ctx.lineWidth = 3.2;
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();
  }
}

export function drawArrivalPlaza() {
  drawPavingInlay(4.15, 14.1, 7.25, 3.05, "#e9e4d9", 1.05);
  drawGroundSlab(4.45, 14.38, 6.65, 0.28, WORLD_MATERIALS.coral, 6);
  const center = isoPoint(7.65, 15.65, 8);
  ctx.save();
  ctx.translate(center.x, center.y);
  ctx.scale(1, 0.5);
  ctx.strokeStyle = "#31545b";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.arc(0, 0, 24, 0, Math.PI * 2);
  ctx.stroke();
  ctx.fillStyle = WORLD_MATERIALS.coral;
  ctx.beginPath();
  ctx.arc(0, 0, 5, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
  drawCampusBench(5.05, 16.1);
  drawCampusBench(9.45, 14.72);
  drawLinearPlanter(10.55, 15.3, 0.55, 1.2, 13);
  drawSpaceCaption(4.45, 16.9, "Arrival Plaza", WORLD_MATERIALS.coral);
}

export function drawAcademicCourtyard(t) {
  drawPavingInlay(12.65, 9.25, 15.15, 5.15, "#f0ece3", 1.35);
  drawGroundSlab(14.7, 10.45, 6.8, 1.15, "#72bdc4", 4);
  const water = isoPoint(18.1, 11, 6);
  ctx.save();
  ctx.globalAlpha = 0.42;
  ctx.strokeStyle = "#f4ffff";
  ctx.lineWidth = 1.2;
  for (let i = 0; i < 4; i++) {
    ctx.beginPath();
    ctx.ellipse(
      water.x + i * 6 - 9,
      water.y + i * 3 - 4,
      32 + Math.sin(t * 0.002 + i) * 2,
      7,
      0,
      0,
      Math.PI * 2,
    );
    ctx.stroke();
  }
  ctx.globalAlpha = 0.68;
  for (let jet = 0; jet < 3; jet++) {
    const lift = 10 + Math.abs(Math.sin(t * 0.003 + jet * 1.2)) * 8;
    ctx.beginPath();
    ctx.moveTo(water.x - 18 + jet * 18, water.y);
    ctx.quadraticCurveTo(water.x - 15 + jet * 18, water.y - lift, water.x - 7 + jet * 18, water.y + 1);
    ctx.stroke();
  }
  ctx.restore();
  for (let i = 0; i < 4; i++) drawLinearPlanter(12.95 + i * 4.65, 12.94, 1.45, 0.68, 14);
  drawCampusBench(13.35, 11.8);
  drawCampusBench(24.8, 11.75);
  drawSpaceCaption(13.05, 9.75, "Academic Courtyard", "#31545b");
  const pulse = 2 + Math.sin(t * 0.002) * 0.7,
    p = isoPoint(20.1, 12.72, 9);
  ctx.fillStyle = `rgba(100,203,200,${0.12 + pulse * 0.015})`;
  ctx.beginPath();
  ctx.ellipse(p.x, p.y, 28, 10, 0, 0, Math.PI * 2);
  ctx.fill();
}

export function drawCafeTerrace() {
  drawGroundSlab(13.55, 14.05, 8.2, 2.35, "#d8cfbc", 5);
  drawPergola(14.05, 14.35, 2.25, 1.35, "#f2c85f");
  [
    [14.7, 14.95],
    [17.1, 14.7],
    [19.15, 15.25],
    [20.65, 14.55],
  ].forEach(([x, y], index) => drawTerraceTable(x, y, index % 2 ? "#f5c95e" : "#ed7458"));
  drawLinearPlanter(13.72, 15.88, 7.75, 0.42, 12);
  drawSpaceCaption(13.8, 16.25, "Shaded Terrace", "#8b6645");
}

export function drawServiceLane() {
  drawGroundSlab(2.15, 17.15, 12.35, 2.15, "#9da39e", 4);
  for (let i = 0; i < 8; i++) {
    const a = isoPoint(2.55 + i * 1.45, 18.22, 6),
      b = isoPoint(3.18 + i * 1.45, 18.22, 6);
    ctx.strokeStyle = "rgba(245,241,230,.62)";
    ctx.lineWidth = 2.2;
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();
  }
  for (let i = 0; i < 3; i++) {
    const x = 3.05 + i * 2.15;
    drawGroundSlab(x, 17.38, 1.3, 0.72, "#c5c6be", 5);
    const p = isoPoint(x + 0.65, 17.76, 7);
    ctx.strokeStyle = "#e8e5dc";
    ctx.lineWidth = 1;
    ctx.strokeRect(p.x - 15, p.y - 6, 30, 12);
  }
  drawSpaceCaption(2.55, 19.03, "Service & deliveries", "#5d6765");
}

export function drawFoodCourt() {
  drawPavingInlay(24.05, 17.25, 8.3, 4.45, "#dfd8ca", 1.2);
  drawPergola(24.65, 17.75, 3.05, 1.15, "#f5c95e");
  drawPergola(28.25, 17.75, 3.25, 1.15, "#64cbc8");
  [
    [25.35, 19.75],
    [27.2, 20.35],
    [29.25, 19.75],
    [31, 20.45],
  ].forEach(([x, y], index) => drawTerraceTable(x, y, index % 2 ? "#64cbc8" : "#f5c95e"));
  drawSpaceCaption(24.4, 21.35, "Food Court", "#8b6645");
}

export function drawStudentLawn() {
  drawGroundSlab(32.35, 17.15, 6.8, 5.1, "#83a774", 3);
  const patches = [
    [33.2, 18.2, "#e5c86f"],
    [35.2, 20.4, "#ed7458"],
    [37.25, 18.75, "#d8e8d0"],
    [33.8, 21.25, "#64cbc8"],
  ];
  patches.forEach(([x, y, color], index) => {
    const p = isoPoint(x, y, 5);
    ctx.fillStyle = color;
    ctx.globalAlpha = 0.72;
    ctx.beginPath();
    ctx.moveTo(p.x - 14, p.y);
    ctx.lineTo(p.x, p.y - 6);
    ctx.lineTo(p.x + 14, p.y);
    ctx.lineTo(p.x, p.y + 6);
    ctx.closePath();
    ctx.fill();
    ctx.globalAlpha = 1;
    if (index < 2) drawCampusBench(x + 0.35, y - 0.2, index);
  });
  drawLinearPlanter(38.4, 17.55, 0.48, 4.15, 13);
  drawSpaceCaption(32.75, 22.05, "Student Lawn", "#456549");
}

export function drawBeachPromenade(t) {
  drawGroundSlab(2.1, 21.62, 37.2, 1.38, "#c2b39a", 5);
  for (let x = 2.4; x < 39; x += 1.1) {
    const a = isoPoint(x, 21.72, 7),
      b = isoPoint(x, 22.88, 7);
    ctx.strokeStyle = "rgba(91,72,53,.18)";
    ctx.lineWidth = 0.8;
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();
  }
  for (let x = 5; x < 39; x += 5.4) {
    const base = isoPoint(x, 22.15, 7),
      top = isoPoint(x, 22.15, 35);
    ctx.strokeStyle = "#31545b";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(base.x, base.y);
    ctx.lineTo(top.x, top.y);
    ctx.stroke();
    ctx.fillStyle = "#f5c95e";
    ctx.beginPath();
    ctx.arc(top.x, top.y, 3 + Math.sin(t * 0.002 + x) * 0.3, 0, Math.PI * 2);
    ctx.fill();
  }
  const environment = environmentalProfile(scene.clock, scene.day, t);
  for (let x = 7.7, index = 0; x < 38; x += 7.6, index++)
    drawWindFlag(x, 21.9, 48, index % 2 ? "#64cbc8" : "#ed7458", t + index * 190, environment, 0.58);
  drawSpaceCaption(31.5, 22.8, "Beach Promenade", "#6d5944");
}

export function drawEventSquare() {
  drawPavingInlay(17.05, 19.55, 7, 4.15, "#d9d2c4", 0.95);
  const center = isoPoint(20.55, 21.45, 7);
  ctx.save();
  ctx.translate(center.x, center.y);
  ctx.scale(1, 0.5);
  for (let ring = 0; ring < 3; ring++) {
    ctx.strokeStyle = ring === 1 ? WORLD_MATERIALS.coral : "rgba(49,84,91,.28)";
    ctx.lineWidth = ring === 1 ? 2 : 1;
    ctx.beginPath();
    ctx.arc(0, 0, 28 + ring * 14, 0, Math.PI * 2);
    ctx.stroke();
  }
  ctx.restore();
  drawSpaceCaption(17.35, 23.3, "Event Square", WORLD_MATERIALS.coral);
}

export function drawCampusGroundPlan(t) {
  drawGroundSlab(1.8, 7.7, 37.4, 9.5, "#d8d8d1", 3);
  drawConcreteSeams(1.8, 7.7, 37.4, 9.5, 5, 2.1);
  drawArrivalPlaza();
  drawAcademicCourtyard(t);
  drawCafeTerrace();
  drawServiceLane();
  drawFoodCourt();
  drawStudentLawn();
  drawBeachPromenade(t);
  drawEventSquare();
  drawColumnLine(11.95, 8.75, 18.2, 12, 27, "x", "#365861");
  drawBladeSign(8.6, 16.15, 32, "NOVA", WORLD_MATERIALS.coral);
  drawBladeSign(33.2, 16.15, 32, "COAST", WORLD_MATERIALS.lime);
  const routeA = isoPoint(7.2, 15.25, 8),
    routeB = isoPoint(34.6, 15.25, 8);
  ctx.strokeStyle = WORLD_MATERIALS.coral;
  ctx.lineWidth = 2.5;
  ctx.beginPath();
  ctx.moveTo(routeA.x, routeA.y);
  ctx.lineTo(routeB.x, routeB.y);
  ctx.stroke();
}

export function drawRoofGarden(x, y, w, h, z) {
  drawRaisedSlab(x, y, w, h, z, 4, "#dce4d4", "#78877b", "#94a296");
  for (let i = 0; i < 4; i++) {
    const p = isoPoint(x + 0.7 + (i * (w - 1.4)) / 3, y + h * 0.55, z + 8);
    ctx.fillStyle = i % 2 ? "#5d8563" : "#77986d";
    ctx.beginPath();
    ctx.ellipse(p.x, p.y, 10, 5, 0, 0, Math.PI * 2);
    ctx.fill();
  }
}

export function drawRoofLights(x, y, w, h, z) {
  const rows = Math.max(1, Math.floor(h / 1.6)),
    cols = Math.max(2, Math.floor(w / 2));
  for (let row = 0; row < rows; row++)
    for (let col = 0; col < cols; col++) {
      const px = x + 0.45 + (col * (w - 0.9)) / cols,
        py = y + 0.38 + (row * (h - 0.7)) / rows,
        pw = ((w - 0.9) / cols) * 0.62,
        ph = ((h - 0.7) / rows) * 0.55;
      drawPlane(
        [
          isoPoint(px, py, z),
          isoPoint(px + pw, py, z),
          isoPoint(px + pw, py + ph, z),
          isoPoint(px, py + ph, z),
        ],
        (row + col) % 2 ? "#416b73" : "#315b65",
        "rgba(255,255,255,.22)",
      );
    }
}

export function drawCampusWing(x, y, w, h, z, options = {}) {
  const white = options.white || WORLD_MATERIALS.chalk,
    side = options.side || "#aebbb6",
    shadow = options.shadow || WORLD_MATERIALS.chalkShade;
  drawSoftShadow(x + w * 0.55, y + h * 0.62, Math.max(36, w * 12), Math.max(13, h * 5), 0.2);
  drawBlock(x - 0.16, y - 0.12, w + 0.32, h + 0.24, 8, "#d6d5ce", "#8d9b97", "#abb3ae");
  drawBlock(x, y, w, h, z, white, side, shadow);
  const levels = Math.max(1, Math.floor((z - 18) / 27));
  for (let level = 0; level < levels; level++) {
    const low = 14 + level * 27,
      high = Math.min(z - 9, low + 15);
    if (high > low) {
      drawFacadeBandY(
        x + 0.28,
        y + h + 0.015,
        w - 0.56,
        low,
        high,
        options.glass || "#285761",
        Math.max(3, Math.round(w)),
      );
      drawFacadeBandX(
        x + w + 0.015,
        y + 0.25,
        h - 0.5,
        low,
        high,
        options.glassDark || "#204650",
        Math.max(2, Math.round(h)),
      );
    }
  }
  drawRaisedSlab(x - 0.18, y - 0.18, w + 0.36, h + 0.36, z + 4, 5, "#fbf8ef", "#9eaaa6", "#bdc4bf");
  const capA = isoPoint(x - 0.18, y + h + 0.18, z + 5),
    capB = isoPoint(x + w + 0.18, y + h + 0.18, z + 5);
  ctx.strokeStyle = "rgba(255,255,255,.72)";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(capA.x, capA.y);
  ctx.lineTo(capB.x, capB.y);
  ctx.stroke();
  drawRoofLights(x + 0.45, y + 0.4, w - 0.9, h - 0.8, z + 4);
  if (options.slats)
    drawTimberScreen(
      x + 0.35,
      y + h + 0.04,
      w - 0.7,
      13,
      Math.min(z - 8, 72),
      Math.max(5, Math.round(w * 1.4)),
    );
  if (options.roofGarden)
    drawRoofGarden(x + 0.55, y + 0.45, Math.max(1, w - 1.1), Math.max(0.7, h - 1), z + 4);
  if (options.accent) {
    const a = isoPoint(x + w * 0.12, y + h + 0.05, Math.min(z - 7, 46)),
      b = isoPoint(x + w * 0.42, y + h + 0.05, Math.min(z - 7, 46));
    ctx.strokeStyle = options.accent;
    ctx.lineWidth = 5;
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();
  }
}

export function drawCanopy(x, y, w, h, z = 31, baseZ = 0) {
  drawRaisedSlab(x, y, w, h, z + 4, 5, "#f5f3ea", "#aeb9b5", "#c5cac5");
  const posts = [
    [x + 0.2, y + 0.2],
    [x + w - 0.2, y + 0.2],
    [x + 0.2, y + h - 0.2],
    [x + w - 0.2, y + h - 0.2],
  ];
  ctx.strokeStyle = "#31545b";
  ctx.lineWidth = 2;
  posts.forEach(([px, py]) => {
    const a = isoPoint(px, py, baseZ),
      b = isoPoint(px, py, z);
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();
  });
}

export function drawCampusWestWing(t) {
  const { x, y, w, h } = world.buildings.academicWest;
  drawCampusWing(x, y, w, h, 90, { glass: "#245761", roofGarden: true, slats: true });
  const environment = environmentalProfile(scene.clock, scene.day, t);
  drawWindFlag(13.25, 3.6, 112, "#ed7458", t, environment, 0.86);
}

export function drawCampusCentreWing(t) {
  const { x, y, w, h } = world.buildings.academicCentre;
  drawCampusWing(x, y, w, h, 70, { glass: "#2b6670", accent: "#f2c85f" });
  const environment = environmentalProfile(scene.clock, scene.day, t);
  drawWindFlag(24.8, 3.5, 133, "#f5c95e", t + 180, environment, 0.86);
}

export function drawCampusEastWing(t) {
  const { x, y, w, h } = world.buildings.academicEast;
  drawCampusWing(x, y, w, h, 111, { glass: "#214e5b", slats: true, roofGarden: true, accent: "#ed7458" });
  const environment = environmentalProfile(scene.clock, scene.day, t);
  drawWindFlag(29.1, 4.15, 119, "#64cbc8", t + 340, environment, 0.86);
}

export function drawCampusBridgeAndIdentity() {
  const bridgeA = isoPoint(17.8, 5.6, 60),
    bridgeB = isoPoint(24.25, 5.6, 60);
  ctx.strokeStyle = "#e8e8e2";
  ctx.lineWidth = 14;
  ctx.beginPath();
  ctx.moveTo(bridgeA.x, bridgeA.y);
  ctx.lineTo(bridgeB.x, bridgeB.y);
  ctx.stroke();
  ctx.strokeStyle = "#315c65";
  ctx.lineWidth = 8;
  ctx.stroke();
  drawWorldLabel(21.2, 8.55, 127, "NOVA COAST CAMPUS", "#f5c95e");
}

export function drawLibrary() {
  const { x, y, w, h } = world.buildings.library;
  drawCampusWing(x, y, w, h, 73, { glass: "#285d67", slats: true, roofGarden: true, accent: "#64cbc8" });
  drawWorldLabel(6.4, 8.05, 88, "LEARNING CENTER", "#64cbc8");
}

export function drawMercadoExterior() {
  const { x, y, w, h } = world.buildings.mercado;
  drawCampusWing(x, y, w, h, 58, { glass: "#2b555b", slats: true, accent: "#f5c95e" });
  drawWorldLabel(7.3, 13.15, 74, "MERCADO SUPPLY", "#f5c95e");
}

export function drawStudentHub() {
  const { x, y, w, h } = world.buildings.studentHub;
  drawCampusWing(x, y, w, h, 84, { glass: "#225762", roofGarden: true, accent: "#ff7458", slats: true });
  drawWorldLabel(34.65, 10.95, 100, "STUDENT HUB", "#ff7458");
}

export function architecturalForegroundActors() {
  const actors = [];
  const addCanopy = (x, y, w, h, z, maxSlice = 3) => {
    const slices = Math.max(1, Math.ceil(w / maxSlice)),
      slice = w / slices;
    for (let index = 0; index < slices; index++) {
      const sx = x + index * slice;
      actors.push({ depth: sx + slice + y + h + 0.015, draw: () => drawCanopy(sx, y, slice, h, z) });
    }
  };
  const addColumns = (x, y, length, count, z, axis = "x", color = "#244b54") => {
    for (let index = 0; index < count; index++) {
      const amount = count === 1 ? 0.5 : index / (count - 1),
        px = x + (axis === "x" ? length * amount : 0),
        py = y + (axis === "y" ? length * amount : 0);
      actors.push({ depth: px + py + 0.02, draw: () => drawColumnLine(px, py, 0, 1, z, axis, color) });
    }
  };
  const addPlanter = (x, y, w, h, z, maxSlice = 1.15) => {
    const slices = Math.max(1, Math.ceil(w / maxSlice)),
      slice = w / slices;
    for (let index = 0; index < slices; index++) {
      const sx = x + index * slice;
      actors.push({ depth: sx + slice + y + h + 0.025, draw: () => drawLinearPlanter(sx, y, slice, h, z) });
    }
  };
  addCanopy(12, 8.25, 18.3, 1.15, 31, 3.05);
  addColumns(12.3, 9.36, 17.7, 11, 30);
  addCanopy(9.8, 6.75, 3.1, 1.2, 28, 1.55);
  addColumns(2.55, 8.42, 7.7, 7, 27);
  addCanopy(10.75, 10.4, 2.1, 1.4, 26, 1.05);
  addColumns(3.45, 13.27, 7.55, 6, 25);
  addCanopy(29.25, 8.15, 2.2, 1.25, 29, 1.1);
  addColumns(30.35, 11.17, 8.45, 8, 28);
  world.planters.forEach((planter) => addPlanter(planter.x, planter.y, planter.w, planter.h, planter.z));
  return actors;
}

export function drawBeachStage(t) {
  drawRaisedSlab(18.35, 22.08, 4.3, 2.25, 10, 5, "#ddd0b3", "#776a59", "#a3937a");
  for (let i = 0; i < 3; i++)
    drawRaisedSlab(
      18.58 + i * 0.24,
      22.18 + i * 0.23,
      3.82 - i * 0.48,
      0.42,
      16 + i * 7,
      6,
      "#d2aa71",
      "#735b42",
      "#95724e",
    );
  drawRaisedSlab(19.28, 21.9, 2.46, 0.72, 18, 6, "#ece8dc", "#9aa5a0", "#bcc3be");
  const stage = isoPoint(20.5, 22.28, 25);
  ctx.save();
  ctx.translate(stage.x, stage.y);
  ctx.scale(1, 0.45);
  ctx.fillStyle = "#64cbc8";
  ctx.beginPath();
  ctx.ellipse(0, 0, 31, 17, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = "#eaf7f4";
  ctx.lineWidth = 4;
  ctx.stroke();
  ctx.restore();
  [-1.72, 1.72].forEach((offset, index) => {
    drawBlock(20.5 + offset - 0.25, 22.78 - 0.25, 0.5, 0.5, 24, "#e6e1d5", "#8e9690", "#aeb3ad");
    const plant = isoPoint(20.5 + offset, 22.78, 28);
    ctx.fillStyle = index ? "#4b9363" : "#5ca06d";
    for (let i = 0; i < 6; i++) {
      ctx.save();
      ctx.translate(plant.x, plant.y);
      ctx.rotate((i * Math.PI) / 3);
      ctx.beginPath();
      ctx.ellipse(0, -9, 3, 10, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    }
  });
  const railA = isoPoint(18.55, 22.13, 50),
    railB = isoPoint(22.45, 22.13, 50);
  ctx.strokeStyle = "#264d56";
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(railA.x, railA.y);
  ctx.lineTo(railB.x, railB.y);
  ctx.stroke();
  for (let i = 0; i < 7; i++) {
    const lamp = isoPoint(18.7 + i * 0.6, 22.13, 49);
    ctx.fillStyle = i % 2 ? "#ff8b66" : "#f5c95e";
    ctx.beginPath();
    ctx.arc(lamp.x, lamp.y + 4 + Math.sin(t * 0.002 + i), 2.7, 0, Math.PI * 2);
    ctx.fill();
  }
  drawWorldLabel(20.5, 23.05, 72, "SUNSET FORUM", "#64cbc8");
}

export function campusActors(t) {
  const environment = environmentalProfile(scene.clock, scene.day, t);
  const buildingDepth = (building) =>
    Math.max(building.x, Math.min(building.x + building.w, scene.player.x)) + building.y + building.h + 0.02;
  return [
    { depth: buildingDepth(world.buildings.library), draw: () => drawLibrary() },
    { depth: buildingDepth(world.buildings.mercado), draw: () => drawMercadoExterior() },
    { depth: buildingDepth(world.buildings.academicWest), draw: () => drawCampusWestWing(t) },
    { depth: 29.9, draw: () => drawCampusBridgeAndIdentity() },
    { depth: buildingDepth(world.buildings.academicCentre), draw: () => drawCampusCentreWing(t) },
    { depth: buildingDepth(world.buildings.academicEast), draw: () => drawCampusEastWing(t) },
    { depth: buildingDepth(world.buildings.studentHub), draw: () => drawStudentHub() },
    { depth: 46.98, draw: () => drawBeachStage(t) },
    ...architecturalForegroundActors(),
    ...world.trees.map((tree, i) => ({
      depth: tree[0] + tree[1],
      draw: () => drawTree(tree[0], tree[1], tree[2], t + i * 170, environment),
    })),
  ];
}
