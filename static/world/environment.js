// Light, sky, sea, wind and palm trees. All of it is only for the eye: no rule reads it.
// Drawing code taken from Felix Antes' Nova Beach Ventures
// (https://github.com/felix-anthes-png/nova-beach-ventures), reduced to what this game uses.

import { mixColor } from "./primitives.js";
import { DAY_END, DAY_START, ctx, isoPoint, reducedMotion, scene } from "./scene.js";

export function lightingProfile(minutes) {
  const stops = [
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
  const value = Math.max(DAY_START, Math.min(DAY_END, minutes)),
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
    progress: (value - DAY_START) / (DAY_END - DAY_START),
  };
}

export function environmentalProfile(minutes = scene.clock, day = scene.day, t = scene.time) {
  const daySeed = ((day * 37) % 17) / 17,
    afternoon = Math.max(0, Math.sin(((minutes - DAY_START) / (DAY_END - DAY_START)) * Math.PI));
  const baseWind = 0.38 + daySeed * 0.24 + afternoon * 0.22,
    gust = reducedMotion ? 0 : Math.sin(t * 0.00073 + day * 0.91) * 0.1 + Math.sin(t * 0.00191 + day) * 0.045;
  const wind = Math.max(0.18, Math.min(0.92, baseWind + gust)),
    sea = 0.42 + wind * 0.52,
    cloud = 0.12 + ((day * 11) % 9) / 30;
  const temperature = Math.round(20 + afternoon * 4 - daySeed * 1.4),
    label = wind > 0.72 ? "COASTAL WIND" : wind > 0.48 ? "ATLANTIC BREEZE" : "CALM SURF";
  return { wind, sea, cloud, temperature, label, direction: 1, phase: reducedMotion ? 0 : t * 0.001 };
}

export function drawSkyMotion(t, environment, w, h) {
  ctx.save();
  ctx.globalAlpha = 0.14 + environment.cloud * 0.2;
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
  ctx.globalAlpha = 0.34;
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

export function drawCoastalMotion(t, environment) {
  ctx.save();
  ctx.lineCap = "round";
  for (let band = 0; band < 5; band++) {
    const y = 27.55 + band * 0.78,
      amplitude = 2.2 + band * 0.7 + environment.sea * 2,
      alpha = 0.18 + band * 0.07;
    ctx.strokeStyle = `rgba(229,251,247,${alpha})`;
    ctx.lineWidth = 1.2 + band * 0.3;
    ctx.beginPath();
    for (let x = -1; x <= 58; x += 0.35) {
      const phase = x * 0.55 - (reducedMotion ? 0 : t * 0.0011 * (0.65 + environment.sea)) + band * 0.9,
        p = isoPoint(x, y + Math.sin(phase) * 0.075 * environment.sea, 5 + Math.sin(phase) * amplitude);
      if (x === -1) ctx.moveTo(p.x, p.y);
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
        p = isoPoint(x, 27.1 + ribbon * 0.16 + Math.sin(phase) * 0.09, 7);
      if (x === 0) ctx.moveTo(p.x, p.y);
      else ctx.lineTo(p.x, p.y);
    }
    ctx.stroke();
  }
  for (let i = 0; i < 11; i++) {
    const progress = reducedMotion ? i / 11 : (t * 0.000035 * (0.8 + environment.wind) + i / 11) % 1,
      p = isoPoint(2 + i * 5.1, 27.25 + progress * 3.9, 8);
    ctx.fillStyle = `rgba(240,255,250,${0.3 * (1 - progress)})`;
    ctx.beginPath();
    ctx.ellipse(p.x, p.y, 7 + progress * 5, 1.4, 0, 0, Math.PI * 2);
    ctx.fill();
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
  glow.addColorStop(0, light.stage === "sunset" ? "rgba(255,196,112,.3)" : "rgba(255,245,196,.2)");
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
