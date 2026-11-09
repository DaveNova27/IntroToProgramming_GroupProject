// The outdoor campus: ground, public spaces and buildings.
// Drawing code taken from Felix Antes' Nova Beach Ventures
// (https://github.com/felix-anthes-png/nova-beach-ventures), reduced to what this game uses.

import { drawTree, drawWindFlag, environmentalProfile } from "./environment.js";
import {
  WORLD_MATERIALS,
  drawBladeSign,
  drawBlock,
  drawConcreteSeams,
  drawGroundSlab,
  drawLinearPlanter,
  drawPavingInlay,
  drawPlane,
  drawRaisedSlab,
  drawSpaceCaption,
  drawTile,
  drawWorldLabel,
  mixColor,
} from "./primitives.js";
import {
  DEPTH,
  TILE,
  depthOf,
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
    viewX = canvas.clientWidth / (2 * camera.zoom) + TILE * 2,
    viewY = canvas.clientHeight / (2 * camera.zoom) + DEPTH * 3;
  // the ground also runs a little west of the map, so no void shows beside the beach
  for (let y = 0; y < zone.height; y++)
    for (let x = -14; x < zone.width; x++) {
      const point = isoPoint(x, y);
      if (Math.abs(point.x - center.x) <= viewX && Math.abs(point.y - center.y) <= viewY)
        tiles.push({ x, y, d: depthOf(x, y) });
    }
  tiles.sort((a, b) => a.d - b.d);
  tiles.forEach(({ x, y }) => {
    let color = zone.floor || "#79aa67",
      depth = 4;
    if (zone.outdoor) {
      if (y >= 35) {
        // shallow, light water along the shore, deeper and darker further out
        const deep = ["#78cbc4", "#5cb6b9", "#4aa0b0", "#448fa0", "#3f899b", "#397f93", "#33758b", "#2e6b83"][Math.min(y - 35, 7)];
        color = x % 5 === 0 ? mixColor(deep, "#ffffff", 0.05) : deep;
        depth = 0;
      } else if (y >= 25) color = y >= 34 ? "#d3b575" : y >= 33 ? "#d9bc7b" : x % 4 === 0 ? "#e4c986" : "#dec27e";
      else if ((y >= 8 && y < 18 && x >= 2 && x <= 39) || y >= 18) {
        color = (Math.floor(x / 3) + Math.floor(y / 3)) % 2 ? "#d0d0c7" : "#ccccc3";
        // the paving turns warm and sandy towards the beach, so the two do not meet on a line
        if (y >= 20) color = mixColor(color, "#e6d3a2", Math.min(0.72, (y - 19.5) * 0.15));
      } else {
        // lawn: soft drifting patches of two greens, not a chessboard
        const f = 0.5 + 0.25 * Math.sin(x * 0.43 + y * 0.21) + 0.25 * Math.sin(y * 0.57 - x * 0.17 + 1.3);
        color = mixColor("#78a267", "#82ad70", f * 0.9 + ((x * 7 + y * 13) % 5) * 0.02);
      }
    } else color = (x + y) % 2 ? zone.floor : mixColor(zone.floor, "#ffffff", 0.07);
    drawTile(x, y, color, depth);
    if (zone.outdoor && y === 34) {
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
  drawSpaceCaption(22.3, 10.95, "Academic Courtyard", "#31545b");
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

// The delivery lane runs along the west side of the Mercado and stops where the building stops,
// so lorries never cross the plaza: asphalt, a kerb against the wall, centre dashes, a barrier at the south end.
export function drawServiceLane() {
  const y0 = 8.0, y1 = 13.5;
  drawGroundSlab(-1.4, y0, 4.3, y1 - y0, "#9da39e", 4);
  drawGroundSlab(2.9, y0, 0.25, y1 - y0, "#c9c9c0", 5);
  drawGroundSlab(-1.4, y1 - 0.12, 4.3, 0.12, "#c9c9c0", 5); // a kerb closes the lane at the south end
  for (let j = 0; j < 5; j++) {
    const a = isoPoint(0.95, 8.5 + j * 1.0, 6),
      b = isoPoint(0.95, 8.9 + j * 1.0, 6);
    ctx.strokeStyle = "rgba(245,241,230,.62)";
    ctx.lineWidth = 2.2;
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();
  }
  // loading bay marks in front of the dock, and pallets with boxes
  for (const y of [9.0, 12.2]) {
    const a = isoPoint(1.3, y, 6),
      b = isoPoint(2.8, y, 6);
    ctx.strokeStyle = "rgba(245,241,230,.55)";
    ctx.lineWidth = 1.6;
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();
  }
  drawGroundSlab(2.05, 9.5, 0.75, 0.95, "#b98b59", 5);
  drawGroundSlab(2.1, 9.55, 0.65, 0.85, "#d8c59c", 7);
  drawGroundSlab(2.05, 10.9, 0.75, 0.95, "#b98b59", 5);
  drawGroundSlab(2.1, 10.95, 0.65, 0.85, "#c9a878", 8);
  // the barrier at the gate: a post at the building's corner with a red and white arm, lifted
  const bx = 2.7, by = 13.2;
  const post = isoPoint(bx, by, 5),
    top = isoPoint(bx, by, 30);
  ctx.strokeStyle = "#31545b";
  ctx.lineWidth = 4;
  ctx.beginPath();
  ctx.moveTo(post.x, post.y);
  ctx.lineTo(top.x, top.y);
  ctx.stroke();
  for (let i = 0; i < 6; i++) {
    const a = isoPoint(bx - i * 0.33, by, 30 + i * 9),
      b = isoPoint(bx - (i + 1) * 0.33, by, 30 + (i + 1) * 9);
    ctx.strokeStyle = i % 2 ? "#ffffff" : "#e24d3f";
    ctx.lineWidth = 3.2;
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();
  }
  drawSpaceCaption(0.0, 13.0, "Service & deliveries", "#5d6765");
}

export function drawStudentLawn() {
  drawGroundSlab(32.35, 17.15, 6.8, 2.7, "#83a774", 3);
  const patches = [
    [33.2, 18.2, "#e5c86f"],
    [35.2, 18.9, "#ed7458"],
    [37.25, 18.75, "#d8e8d0"],
    [33.8, 19.0, "#64cbc8"],
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
  drawLinearPlanter(38.4, 17.55, 0.48, 2.1, 13);
  drawSpaceCaption(32.75, 19.75, "Student Lawn", "#456549");
}

export function drawCampusGroundPlan(t) {
  drawGroundSlab(1.8, 7.7, 37.4, 9.5, "#d8d8d1", 3);
  drawConcreteSeams(1.8, 7.7, 37.4, 9.5, 5, 2.1);
  drawArrivalPlaza();
  drawAcademicCourtyard(t);
  drawCafeTerrace();
  drawServiceLane();
  drawStudentLawn();
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

// the low planters along the facades (the Learning Center, the Mercado and the Hub draw their own fronts)
export function architecturalForegroundActors() {
  const actors = [];
  const addPlanter = (x, y, w, h, z, maxSlice = 1.15) => {
    const slices = Math.max(1, Math.ceil(w / maxSlice)),
      slice = w / slices;
    for (let index = 0; index < slices; index++) {
      const sx = x + index * slice;
      actors.push({ depth: depthOf(sx + slice / 2, y + h + 0.025), draw: () => drawLinearPlanter(sx, y, slice, h, z) });
    }
  };
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
  return [
    { depth: depthOf(20.5, 24.33), draw: () => drawBeachStage(t) }, // the front edge of the stage
    ...architecturalForegroundActors(),
    ...world.trees.map((tree, i) => ({
      depth: depthOf(tree[0], tree[1]),
      draw: () => drawTree(tree[0], tree[1], tree[2], t + i * 170, environment),
    })),
  ];
}
