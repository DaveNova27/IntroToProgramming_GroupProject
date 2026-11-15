// Light, sky, sea, wind and palm trees. All of it is only for the eye: no rule reads it.
// Drawing code taken from Felix Antes' Nova Beach Ventures
// (https://github.com/felix-anthes-png/nova-beach-ventures), reduced to what this game uses.

import { mixColor } from "./primitives.js";
import { DAWN, DAY_END, DAY_START, TILE, DEPTH, camera, ctx, isoPoint, reducedMotion, scene, world } from "./scene.js";
import { flashAt, rainStreaks, shelters } from "./weather.js";

// `progress` is how far the light has gone towards the dark: 0 in the morning, 1 at dusk. Before
// DAY_START (the dawn after sleeping, spec day-cycle) it runs from 1 at DAWN back to 0, so the lamps,
// the shade and the sun's path fade out while the sun rises, the same way they came in the evening.
export function lightingProfile(minutes) {
  const stops = [
    { minute: DAWN, top: "#203e58", bottom: "#80606a", overlay: "#173747", alpha: 0.24, stage: "night" },
    { minute: 390, top: "#6d91ae", bottom: "#efb177", overlay: "#ef795f", alpha: 0.1, stage: "dawn" },
    {
      minute: DAY_START,
      top: "#79aebd",
      bottom: "#efd39c",
      overlay: "#f2aa67",
      alpha: 0.08,
      stage: "morning",
    },
    { minute: 660, top: "#8dc8d5", bottom: "#d6e4c0", overlay: "#ffffff", alpha: 0, stage: "day" },
    { minute: 930, top: "#82bfd1", bottom: "#dce4bc", overlay: "#f5c96c", alpha: 0.025, stage: "day" },
    { minute: 1050, top: "#6d91ae", bottom: "#efb177", overlay: "#ef795f", alpha: 0.1, stage: "sunset" },
    { minute: DAY_END, top: "#203e58", bottom: "#80606a", overlay: "#173747", alpha: 0.24, stage: "dusk" },
  ];
  const value = Math.max(DAWN, Math.min(DAY_END, minutes)),
    right = stops.find((stop) => stop.minute >= value) || stops.at(-1),
    left = stops[Math.max(0, stops.indexOf(right) - 1)] || right,
    span = Math.max(1, right.minute - left.minute),
    mix = Math.max(0, Math.min(1, (value - left.minute) / span));
  return {
    top: mixColor(left.top, right.top, mix),
    bottom: mixColor(left.bottom, right.bottom, mix),
    overlay: mixColor(left.overlay, right.overlay, mix),
    alpha: left.alpha + (right.alpha - left.alpha) * mix,
    stage: mix > 0.55 ? right.stage : left.stage,
    progress: value >= DAY_START
      ? (value - DAY_START) / (DAY_END - DAY_START)
      : 1 - (value - DAWN) / (DAY_START - DAWN),
  };
}

export function environmentalProfile(minutes = scene.clock, day = scene.day, t = scene.time) {
  const daySeed = ((day * 37) % 17) / 17,
    afternoon = Math.max(0, Math.sin(((minutes - DAY_START) / (DAY_END - DAY_START)) * Math.PI));
  const baseWind = 0.38 + daySeed * 0.24 + afternoon * 0.22,
    gust = reducedMotion ? 0 : Math.sin(t * 0.00073 + day * 0.91) * 0.1 + Math.sin(t * 0.00191 + day) * 0.045;
  // the weather of the opened day moves the wind and the sea (spec weather-visuals); without one, or on a
  // sunny day, both stay as the day made them
  const look = scene.look;
  const wind = Math.max(0.1, Math.min(1.2, Math.max(0.18, Math.min(0.92, baseWind + gust)) * look.windScale + look.windAdd)),
    sea = Math.max(0.2, (0.42 + wind * 0.52) * look.seaScale + look.seaAdd),
    cloud = 0.12 + ((day * 11) % 9) / 30;
  const temperature = Math.round(20 + afternoon * 4 - daySeed * 1.4),
    label = wind > 0.72 ? "COASTAL WIND" : wind > 0.48 ? "ATLANTIC BREEZE" : "CALM SURF";
  return { wind, sea, cloud, temperature, label, direction: 1, phase: reducedMotion ? 0 : t * 0.001 };
}

export function drawSkyMotion(t, environment, w, h) {
  const look = scene.look;
  ctx.save();
  ctx.globalAlpha = (0.14 + environment.cloud * 0.2) * look.cloudScale;
  for (let i = 0; i < 4; i++) {
    const drift = reducedMotion ? (i * w) / 4 : (t * 0.006 * (0.35 + environment.wind) + i * 211) % (w + 280),
      x = drift - 150,
      y = 55 + i * 47 + (i % 2) * 18,
      scale = 0.7 + i * 0.12;
    ctx.fillStyle = i % 2 ? "#f4eee1" : "#edf4ed";
    ctx.beginPath();
    ctx.ellipse(x, y, 58 * scale, 12 * scale, 0, 0, Math.PI * 2);
    ctx.ellipse(x + 38 * scale, y - 7 * scale, 42 * scale, 15 * scale, 0, 0, Math.PI * 2);
    ctx.ellipse(x - 35 * scale, y + 2 * scale, 35 * scale, 10 * scale, 0, 0, Math.PI * 2);
    ctx.fill();
  }
  if (look.cloudExtra > 0.01) drawCloudBank(t, environment, look, w, h);
  ctx.globalAlpha = 0.34 * Math.max(0, 1 - look.cloudExtra); // the gulls stay down in bad weather
  ctx.strokeStyle = "#173743";
  ctx.lineWidth = 1.2;
  for (let i = 0; i < 3; i++) {
    const x = reducedMotion
        ? w * (0.3 + i * 0.2)
        : ((t * 0.018 * (0.55 + environment.wind) + i * 260) % (w + 120)) - 60,
      y = 86 + i * 31;
    ctx.beginPath();
    ctx.arc(x, y, 6, Math.PI * 1.08, Math.PI * 1.82);
    ctx.arc(x + 12, y, 6, Math.PI * 1.18, Math.PI * 1.92);
    ctx.stroke();
  }
  ctx.restore();
}

// A rainy or stormy sky (spec weather-visuals): a bank of big grey clouds over the top of the picture.
// Places, sizes and speeds are fixed per cloud; the wind only moves them along.
function drawCloudBank(t, environment, look, w, h) {
  const [r, g, b] = look.cloudColor.map(Math.round);
  for (let i = 0; i < 9; i++) {
    const scale = 1.5 + (i % 4) * 0.45,
      span = w + 520,
      drift = reducedMotion ? (i * span) / 9 : (t * 0.011 * (0.4 + environment.wind) * (0.7 + (i % 3) * 0.22) + i * 197) % span,
      x = drift - 260,
      y = 34 + (i % 5) * 36 + (i % 2) * 14;
    ctx.globalAlpha = look.cloudExtra * (0.4 + (i % 3) * 0.1);
    ctx.fillStyle = `rgb(${r - (i % 3) * 8},${g - (i % 3) * 8},${b - (i % 3) * 7})`;
    ctx.beginPath();
    ctx.ellipse(x, y, 96 * scale, 20 * scale, 0, 0, Math.PI * 2);
    ctx.ellipse(x + 62 * scale, y - 10 * scale, 68 * scale, 22 * scale, 0, 0, Math.PI * 2);
    ctx.ellipse(x - 58 * scale, y + 4 * scale, 60 * scale, 16 * scale, 0, 0, Math.PI * 2);
    ctx.fill();
  }
}

// ---- the weather over the scene (spec weather-visuals) ------------------------------------------
// Drawn in canvas pixels after the scene: the shade or the tint, then the haze and the rain, at the
// very end the flash. All of it comes from scene.look, which is neutral while no day is open.

const rgb = (color) => `rgb(${color.map(Math.round).join(",")})`;

// the grey of a wet day (a multiply) and the warm colour of a hot one, over the whole picture
export function drawWeatherShade(w, h) {
  const look = scene.look;
  if (look.shade > 0.01) {
    ctx.save();
    ctx.globalCompositeOperation = "multiply";
    ctx.fillStyle = rgb(look.shadeColor.map((channel) => 255 + (channel - 255) * look.shade));
    ctx.fillRect(0, 0, w, h);
    ctx.restore();
  }
  if (look.tint > 0.005) {
    ctx.save();
    ctx.globalAlpha = look.tint;
    ctx.fillStyle = rgb(look.tintColor);
    ctx.fillRect(0, 0, w, h);
    ctx.restore();
  }
}

// The dry places in canvas pixels: the rooms of every wing whose roof has faded out, from the floor's
// front edge up to the top of its back wall (weather.js: shelters). It does not rain indoors.
function dryBoxes(w, h) {
  const center = isoPoint(camera.x, camera.y);
  const px = (x) => (x * TILE - center.x) * camera.zoom + w / 2;
  const py = (y, z = 0) => (y * DEPTH - z - center.y) * camera.zoom + h / 2;
  return shelters(world.nova?.parts, scene.roofs).map((part) => ({
    x: px(part.x), y: py(part.y, part.z), w: part.w * TILE * camera.zoom, h: py(part.y + part.h) - py(part.y, part.z), dry: part.dry,
  }));
}

// Draws `paint` outdoors at full strength and, over a wing whose roof is still fading, as far as
// that roof is still there. Nothing is drawn over rooms whose roof is gone.
function outdoors(w, h, alpha, paint) {
  const boxes = dryBoxes(w, h);
  ctx.save();
  // one clip per dry place, each cutting its box out of what is left: two boxes that overlap (the back
  // wall of one wing in front of the floor of another) stay dry where they overlap
  for (const box of boxes) {
    const outside = new Path2D();
    outside.rect(0, 0, w, h);
    outside.rect(box.x, box.y, box.w, box.h);
    ctx.clip(outside, "evenodd");
  }
  ctx.globalAlpha = alpha;
  paint();
  ctx.restore();
  for (const box of boxes) {
    if (box.dry > 0.99) continue;
    ctx.save();
    ctx.beginPath();
    ctx.rect(box.x, box.y, box.w, box.h);
    ctx.clip();
    ctx.globalAlpha = alpha * (1 - box.dry);
    paint();
    ctx.restore();
  }
}

// rain: two layers of streaks, each one path
function drawRain(t, w, h) {
  const look = scene.look;
  if (look.rain <= 0.01) return;
  const streaks = rainStreaks(look, reducedMotion ? 0 : t, w, h);
  const path = (list) => {
    const line = new Path2D();
    for (let i = 0; i < list.length; i += 4) {
      line.moveTo(list[i], list[i + 1]);
      line.lineTo(list[i + 2], list[i + 3]);
    }
    return line;
  };
  const far = path(streaks.far), near = path(streaks.near);
  ctx.save();
  ctx.lineCap = "round";
  outdoors(w, h, 1, () => {
    ctx.strokeStyle = "rgba(214,228,240,.34)";
    ctx.lineWidth = 1;
    ctx.stroke(far);
    ctx.strokeStyle = "rgba(232,241,250,.5)";
    ctx.lineWidth = 1.5;
    ctx.stroke(near);
  });
  ctx.restore();
}

// heat: slow pale bands that waver over the lower part of the picture
function drawHaze(t, w, h) {
  const look = scene.look;
  if (look.haze <= 0.01) return;
  const time = reducedMotion ? 0 : t;
  ctx.save();
  ctx.lineCap = "round";
  outdoors(w, h, look.haze, () => {
    for (let band = 0; band < 7; band++) {
      const y = h * (0.42 + band * 0.085) + Math.sin(time * 0.0004 + band * 1.9) * 6;
      ctx.strokeStyle = `rgba(255,244,214,${0.032 + (band % 3) * 0.012})`;
      ctx.lineWidth = 9 + (band % 3) * 5;
      ctx.beginPath();
      for (let x = -20; x <= w + 20; x += 24) {
        const wave = Math.sin(x * 0.021 + time * 0.0016 + band * 2.3) * 3.2 + Math.sin(x * 0.047 - time * 0.0011 + band) * 1.6;
        if (x === -20) ctx.moveTo(x, y + wave);
        else ctx.lineTo(x, y + wave);
      }
      ctx.stroke();
    }
  });
  ctx.restore();
}

export function drawWeatherFall(t, w, h) {
  drawHaze(t, w, h);
  drawRain(t, w, h);
}

// lightning: a soft white wash over everything, rare and short; none with reduced motion
export function drawWeatherFlash(t, w, h) {
  if (reducedMotion) return;
  const flash = flashAt(scene.look, t, scene.day);
  if (flash <= 0) return;
  ctx.save();
  ctx.globalAlpha = flash;
  ctx.fillStyle = "#f4f7ff";
  ctx.fillRect(0, 0, w, h);
  ctx.restore();
}

export function drawCoastalMotion(t, environment) {
  ctx.save();
  ctx.lineCap = "round";
  for (let band = 0; band < 11; band++) {
    const y = 34.55 + band * 0.9,
      amplitude = 2.2 + Math.min(band, 5) * 0.7 + environment.sea * 2,
      alpha = 0.18 + Math.min(band, 5) * 0.07 - Math.max(0, band - 6) * 0.03;
    ctx.strokeStyle = `rgba(229,251,247,${alpha})`;
    ctx.lineWidth = 1.2 + Math.min(band, 5) * 0.3;
    ctx.beginPath();
    for (let x = -14; x <= 58; x += 0.35) {
      const phase = x * 0.55 - (reducedMotion ? 0 : t * 0.0011 * (0.65 + environment.sea)) + band * 0.9,
        p = isoPoint(x, y + Math.sin(phase) * 0.075 * environment.sea, 5 + Math.sin(phase) * amplitude);
      if (x === -14) ctx.moveTo(p.x, p.y);
      else ctx.lineTo(p.x, p.y);
    }
    ctx.stroke();
  }
  for (let ribbon = 0; ribbon < 3; ribbon++) {
    ctx.strokeStyle = `rgba(255,255,245,${0.34 - ribbon * 0.07})`;
    ctx.lineWidth = 2.4 - ribbon * 0.35;
    ctx.beginPath();
    for (let x = 0; x <= 58; x += 0.3) {
      const phase = x * 0.48 - (reducedMotion ? 0 : t * 0.0015 * (0.8 + environment.sea)) + ribbon * 1.7,
        p = isoPoint(x, 34.1 + ribbon * 0.16 + Math.sin(phase) * 0.09, 7);
      if (x === 0) ctx.moveTo(p.x, p.y);
      else ctx.lineTo(p.x, p.y);
    }
    ctx.stroke();
  }
  for (let i = 0; i < 11; i++) {
    const progress = reducedMotion ? i / 11 : (t * 0.000035 * (0.8 + environment.wind) + i / 11) % 1,
      p = isoPoint(2 + i * 5.1, 34.25 + progress * 3.9, 8);
    ctx.fillStyle = `rgba(240,255,250,${0.3 * (1 - progress)})`;
    ctx.beginPath();
    ctx.ellipse(p.x, p.y, 7 + progress * 5, 1.4, 0, 0, Math.PI * 2);
    ctx.fill();
  }
  // wave sets rolling in: a crest that rises, turns white and breaks on the shore, a shaded face behind it
  for (let k = 0; k < 6; k++) {
    const progress = reducedMotion ? k / 6 : (t * 0.000052 * (0.75 + environment.sea) + k / 6) % 1;
    const y = 43 - progress * 8.2; // far to the shore (the sea starts at y 35)
    const rise = Math.sin(Math.min(1, progress * 1.15) * Math.PI);
    ctx.lineCap = "round";
    for (const [dy, alpha, width, color] of [[0.42, 0.1 + 0.1 * progress, 5 + progress * 5, "20,70,90"], [0, 0.18 + 0.55 * progress * progress, 1.3 + progress * 2.8, "255,255,255"]]) {
      ctx.strokeStyle = `rgba(${color},${alpha})`;
      ctx.lineWidth = width;
      ctx.beginPath();
      for (let x = -14; x <= 58; x += 0.4) {
        const yy = y + dy + 0.28 * Math.sin(x * 0.42 + k * 2.3) + 0.12 * Math.sin(x * 1.3 + k);
        const lift = 4 + 9 * rise * (0.7 + 0.3 * Math.sin(x * 0.33 + k * 1.7));
        const p = isoPoint(x, yy, lift);
        if (x === -14) ctx.moveTo(p.x, p.y);
        else ctx.lineTo(p.x, p.y);
      }
      ctx.stroke();
    }
  }
  // the sun's path on the water at sunset: orange dashes in a column, brighter the lower the sun
  const dusk = Math.max(0, Math.min(1, (lightingProfile(scene.clock).progress - 0.5) / 0.4));
  if (dusk > 0.02) {
    // bright dashes along a column under the sun
    for (let i = 0; i < 140; i++) {
      const row = (i * 0.37) % 9;
      const spread = 0.5 + row * 0.5;
      const flick = reducedMotion ? 0.7 : 0.4 + 0.6 * Math.sin(t * 0.003 + i * 2.1);
      const p = isoPoint(26 + Math.sin(i * 2.3) * spread, 35.3 + row, 7);
      ctx.strokeStyle = `rgba(255,${170 + (i % 4) * 14},${100 + (i % 3) * 25},${0.9 * dusk * Math.max(0.1, flick)})`;
      ctx.lineWidth = 2.6;
      ctx.beginPath();
      ctx.moveTo(p.x - 10 - spread * 5, p.y);
      ctx.lineTo(p.x + 10 + spread * 5, p.y);
      ctx.stroke();
    }
  }
  // sun glitter: short bright dashes that twinkle in turn (fixed places, nothing random)
  for (let i = 0; i < 60; i++) {
    const twinkle = reducedMotion ? 0.5 : Math.max(0, Math.sin(t * 0.0026 + i * 1.7)) * Math.max(0, Math.sin(t * 0.0011 + i * 0.6));
    if (twinkle < 0.05) continue;
    const p = isoPoint(-8 + ((i * 7.3) % 58), 36 + ((i * 3.7) % 9), 7);
    ctx.strokeStyle = `rgba(255,255,240,${0.65 * twinkle})`;
    ctx.lineWidth = 1.3;
    ctx.beginPath();
    ctx.moveTo(p.x - 3 - twinkle * 2, p.y);
    ctx.lineTo(p.x + 3 + twinkle * 2, p.y);
    ctx.stroke();
  }
  ctx.restore();
}

export function drawWindFlag(x, y, z, color, t, environment, scale = 1) {
  const pole = isoPoint(x, y, z);
  ctx.save();
  ctx.strokeStyle = "#173743";
  ctx.lineWidth = 2.5 * scale;
  ctx.beginPath();
  ctx.moveTo(pole.x, pole.y + 23 * scale);
  ctx.lineTo(pole.x, pole.y - 25 * scale);
  ctx.stroke();
  const flutter = (reducedMotion ? 0 : Math.sin(t * 0.008 + x * 1.7 + y)) * 3.2 * environment.wind;
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.moveTo(pole.x, pole.y - 24 * scale);
  ctx.quadraticCurveTo(
    pole.x + 12 * scale,
    pole.y - 22 * scale + flutter,
    pole.x + 25 * scale,
    pole.y - 16 * scale,
  );
  ctx.quadraticCurveTo(pole.x + 12 * scale, pole.y - 10 * scale - flutter * 0.45, pole.x, pole.y - 9 * scale);
  ctx.closePath();
  ctx.fill();
  ctx.restore();
}

export function drawAmbientLighting(light, w, h) {
  const sunX = w * (0.13 + light.progress * 0.75),
    sunY = h * (0.16 + Math.pow(Math.abs(light.progress - 0.48), 1.7) * 0.35);
  ctx.save();
  const glow = ctx.createRadialGradient(sunX, sunY, 4, sunX, sunY, Math.max(w, h) * 0.32);
  // the sun glows less under clouds and more on a hot day (spec weather-visuals); 1 = as always
  const strength = scene.look.glow;
  glow.addColorStop(0, light.stage === "sunset" ? `rgba(255,196,112,${Math.min(0.6, 0.3 * strength)})` : `rgba(255,245,196,${Math.min(0.6, 0.2 * strength)})`);
  glow.addColorStop(1, "rgba(255,255,255,0)");
  ctx.fillStyle = glow;
  ctx.fillRect(0, 0, w, h);
  if (light.alpha > 0) {
    ctx.fillStyle = light.overlay;
    ctx.globalAlpha = light.alpha;
    ctx.fillRect(0, 0, w, h);
  }
  ctx.restore();
}

export function drawTree(x, y, scale, t, environment = environmentalProfile()) {
  const gust = reducedMotion ? 0 : Math.sin(t * 0.0012 + x * 0.37) + Math.sin(t * 0.0031 + y) * 0.35,
    sway = gust * (1.4 + environment.wind * 3.4),
    p = isoPoint(x, y, 4);
  ctx.save();
  ctx.translate(p.x, p.y);
  ctx.scale(scale, scale);
  ctx.fillStyle = "rgba(10,45,38,.16)";
  ctx.beginPath();
  ctx.ellipse(7, 4, 27, 8, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = "#76563b";
  ctx.lineWidth = 7;
  ctx.lineCap = "round";
  ctx.beginPath();
  ctx.moveTo(0, 0);
  ctx.quadraticCurveTo(-2, -30, sway, -64);
  ctx.stroke();
  ctx.strokeStyle = "rgba(255,210,145,.34)";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(-2, -3);
  ctx.quadraticCurveTo(-4, -31, sway - 2, -61);
  ctx.stroke();
  ctx.translate(sway, -65);
  for (let a = 0; a < 7; a++) {
    ctx.save();
    ctx.rotate((a * Math.PI * 2) / 7 + gust * 0.025 + Math.sin(t * 0.0017 + a) * 0.035 * environment.wind);
    ctx.scale(1 + environment.wind * 0.06, 1);
    ctx.fillStyle = a % 2 ? "#2f8358" : "#3d9668";
    ctx.beginPath();
    ctx.moveTo(0, 0);
    ctx.quadraticCurveTo(18, -7, 37, 0);
    ctx.quadraticCurveTo(19, 8, 0, 3);
    ctx.closePath();
    ctx.fill();
    ctx.restore();
  }
  ctx.fillStyle = "#87633f";
  ctx.beginPath();
  ctx.arc(0, 0, 5, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
}
