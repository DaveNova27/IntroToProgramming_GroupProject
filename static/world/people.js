// How a person looks: walking, facing, poses, hair and props. Used for the player and for everyone else.
// Drawing code taken from Felix Antes' Nova Beach Ventures
// (https://github.com/felix-anthes-png/nova-beach-ventures), reduced to what this game uses.

import { WORLD_MATERIALS, roundedRect } from "./primitives.js";
import { ctx, isoPoint } from "./scene.js";

export const personStyles = [
  {
    skin: "#8d5943",
    hair: "#211d1c",
    pants: "#243f4d",
    bag: "#e4b654",
    shoes: "#eee9dd",
    hairStyle: "crop",
    build: 0.96,
  },
  {
    skin: "#d69b73",
    hair: "#54362a",
    pants: "#385f68",
    bag: "#c7614e",
    shoes: "#183740",
    hairStyle: "wave",
    build: 1.04,
  },
  {
    skin: "#704532",
    hair: "#171b20",
    pants: "#383b55",
    bag: "#5c9b9d",
    shoes: "#f3eee5",
    hairStyle: "curls",
    build: 1.08,
  },
  {
    skin: "#efbd96",
    hair: "#ad6840",
    pants: "#315056",
    bag: "#8466a3",
    shoes: "#e8dfcf",
    hairStyle: "bun",
    build: 0.9,
  },
  {
    skin: "#b57655",
    hair: "#2c231f",
    pants: "#304652",
    bag: "#7e9e55",
    shoes: "#173743",
    hairStyle: "long",
    build: 1,
  },
  {
    skin: "#e1a77e",
    hair: "#483028",
    pants: "#4a485d",
    bag: "#d37b4d",
    shoes: "#f0ece3",
    hairStyle: "crop",
    build: 1.12,
  },
  {
    skin: "#5d382d",
    hair: "#101619",
    pants: "#274958",
    bag: "#d7a948",
    shoes: "#e8e4dc",
    hairStyle: "curls",
    build: 0.94,
  },
  {
    skin: "#c98966",
    hair: "#72513d",
    pants: "#40505d",
    bag: "#4f9094",
    shoes: "#182f38",
    hairStyle: "wave",
    build: 1.03,
  },
];

// Which side of a figure shows (spec map-view: the camera looks from the south). Facing north (y < 0)
// shows the back, south the front, east or west (also on a diagonal) the profile.
export function characterView(facing = { x: 0, y: 1 }) {
  const sx = facing.x || 0,
    sy = facing.y || 0,
    side = Math.abs(sx) > 0.6;
  return { side, back: !side && sy < -0.08, flip: sx < 0 ? -1 : 1 };
}

export function drawCharacterHair(style, index, view) {
  ctx.fillStyle = style.hair;
  if (style.hairStyle === "curls") {
    for (let i = 0; i < 6; i++) {
      ctx.beginPath();
      ctx.arc(-5 + i * 2, -48 + (i % 2) * 1.2, 2.7, 0, Math.PI * 2);
      ctx.fill();
    }
  } else if (style.hairStyle === "bun") {
    ctx.beginPath();
    ctx.arc(view.back ? 3 : -3, -52, 3.5, 0, Math.PI * 2);
    ctx.fill();
    ctx.beginPath();
    ctx.arc(0, -48, 6, Math.PI, Math.PI * 2);
    ctx.lineTo(5, -44);
    ctx.lineTo(-5, -44);
    ctx.closePath();
    ctx.fill();
  } else if (style.hairStyle === "long") {
    ctx.beginPath();
    ctx.ellipse(-1, -46, 6.4, 9.5, -0.08, Math.PI * 0.88, Math.PI * 2.08);
    ctx.lineTo(5, -40);
    ctx.lineTo(-6, -40);
    ctx.closePath();
    ctx.fill();
  } else if (style.hairStyle === "wave") {
    ctx.beginPath();
    ctx.arc(-0.5, -48, 6.3, Math.PI, Math.PI * 2);
    ctx.quadraticCurveTo(3, -54, 6, -47);
    ctx.lineTo(5, -44);
    ctx.lineTo(-5, -44);
    ctx.closePath();
    ctx.fill();
  } else {
    ctx.beginPath();
    ctx.ellipse(-0.8, -48, 6.2, 4.6, -0.15, Math.PI, Math.PI * 2);
    ctx.lineTo(5, -44);
    ctx.quadraticCurveTo(0, -51, -5, -49);
    ctx.closePath();
    ctx.fill();
  }
}

export function drawCharacterProp(pose, style, frame, role) {
  if (pose === "phone") {
    roundedRect(5, -29, 4, 7, 1, "#173743");
    ctx.fillStyle = "#bce65f";
    ctx.fillRect(6, -28, 2, 3);
  }
  if (pose === "eat" || pose === "drink") {
    ctx.fillStyle = pose === "drink" ? "#64cbc8" : "#f5c95e";
    ctx.beginPath();
    ctx.arc(7, -29, 3.3, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = "#173743";
    ctx.lineWidth = 1;
    ctx.stroke();
  }
  if (pose === "browse") {
    roundedRect(4, -31, 7, 10, 1, style.bag);
    ctx.strokeStyle = "#173743";
    ctx.lineWidth = 1;
    ctx.strokeRect(5, -30, 5, 7);
  }
  if (role === "caretaker") {
    ctx.strokeStyle = "#8c6845";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(8, -34);
    ctx.lineTo(-3, 2);
    ctx.stroke();
    ctx.fillStyle = "#64cbc8";
    ctx.beginPath();
    ctx.moveTo(-9, 1);
    ctx.lineTo(2, -2);
    ctx.lineTo(5, 3);
    ctx.closePath();
    ctx.fill();
  }
  if (role === "technician") {
    roundedRect(5, -22, 10, 7, 2, "#f5c95e");
    ctx.strokeStyle = "#173743";
    ctx.lineWidth = 1;
    ctx.strokeRect(7, -24, 6, 3);
  }
  if (role === "service") {
    ctx.fillStyle = "#e8e3d8";
    ctx.beginPath();
    ctx.ellipse(9, -25, 8, 3, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "#ff8060";
    ctx.beginPath();
    ctx.arc(9, -29, 2.5, 0, Math.PI * 2);
    ctx.fill();
  }
  if (role === "host") {
    roundedRect(5, -30, 7, 10, 1, "#e8e3d8");
    ctx.fillStyle = "#31545b";
    ctx.fillRect(7, -28, 3, 1);
    ctx.fillRect(7, -25, 3, 1);
  }
}

// Lying along the bed, head to the north wall. Seen from the front (spec map-view) north is up the
// screen, so the figure keeps its direction and is only pressed flat, as a body seen lying from above.
const LIE_SQUASH = 0.6;

export function drawPersonFigure(x, y, t, index, options = {}) {
  const style = personStyles[Math.abs(index) % personStyles.length],
    moving = Boolean(options.moving),
    pose = options.pose || (moving ? "walk" : "idle"),
    phase = (options.phase || 0) + index * 0.73,
    frame = moving ? Math.floor((t + phase * 120) / 130) % 6 : Math.floor((t + phase * 90) / 420) % 4,
    walkSteps = [-3, -1, 2, 3, 1, -2],
    step = moving ? walkSteps[frame] : 0,
    dance = pose === "dance" ? Math.sin(t * 0.009 + phase) * 3 : 0,
    bob = moving
      ? frame % 3 === 1
        ? 1.4
        : 0
      : pose === "dance"
        ? Math.abs(Math.sin(t * 0.009 + phase)) * 2
        : Math.sin(t * 0.002 + phase) * 0.35,
    view = characterView(options.facing || { x: options.direction || 1, y: 0 }),
    p = isoPoint(x, y, (options.z ?? 4) + (pose === "lie" ? 0 : bob)),
    scale = (options.player ? 1.2 : 1.02) * (style.build || 1),
    shirt = options.player ? WORLD_MATERIALS.lime : options.color || "#64cbc8",
    sit = pose === "sit",
    lie = pose === "lie", // in bed (spec day-cycle): the whole figure turned flat, eyes closed
    flip = view.side ? view.flip : 1;
  ctx.save();
  ctx.translate(p.x, p.y);
  if (lie) ctx.scale(1, LIE_SQUASH);
  ctx.scale(flip * scale, scale);
  ctx.lineJoin = "round";
  ctx.lineCap = "round";
  if (!lie) {
    ctx.fillStyle = "rgba(6,31,36,.2)";
    ctx.beginPath();
    ctx.ellipse(2 * flip, 4, sit ? 15 : 13.5, sit ? 5.5 : 4.7, 0, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.strokeStyle = "#183740";
  ctx.lineWidth = 1.15;
  ctx.fillStyle = style.pants;
  if (sit) {
    for (const side of [-1, 1]) {
      ctx.beginPath();
      ctx.moveTo(side * 1, -19);
      ctx.lineTo(side * 7, -15);
      ctx.lineTo(side * 8, -3);
      ctx.lineTo(side * 3, -2);
      ctx.lineTo(side * 1, -14);
      ctx.closePath();
      ctx.fill();
      ctx.stroke();
    }
  } else {
    ctx.beginPath();
    ctx.moveTo(-5, -18);
    ctx.lineTo(-1, -20);
    ctx.lineTo(-1 + step + dance, -2);
    ctx.lineTo(-6 + step + dance, -1);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(1, -20);
    ctx.lineTo(5, -18);
    ctx.lineTo(5 - step - dance, -1);
    ctx.lineTo(-step - dance, -2);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();
  }
  ctx.fillStyle = style.shoes;
  for (const side of [-1, 1]) {
    const shoe = sit ? side * 7 : side < 0 ? -5 + step + dance : 5 - step - dance;
    ctx.beginPath();
    ctx.ellipse(shoe, -0.2, 4.5, 2.1, -0.08, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
  }
  ctx.fillStyle = shirt;
  ctx.beginPath();
  ctx.moveTo(-7, -36);
  ctx.quadraticCurveTo(0, -40, 7, -35);
  ctx.lineTo(5, -18);
  ctx.quadraticCurveTo(0, -15, -5, -18);
  ctx.closePath();
  ctx.fill();
  ctx.stroke();
  const armSwing = moving ? step * 0.72 : 0;
  ctx.strokeStyle = style.skin;
  ctx.lineWidth = 4;
  ctx.beginPath();
  if (pose === "phone" || pose === "eat" || pose === "drink" || pose === "browse") {
    ctx.moveTo(-6, -32);
    ctx.lineTo(-2, -25);
    ctx.lineTo(5, -28);
    ctx.moveTo(6, -32);
    ctx.lineTo(8, -27);
  } else if (pose === "clean" || pose === "repair") {
    ctx.moveTo(-6, -32);
    ctx.lineTo(-2, -23);
    ctx.lineTo(6, -20);
    ctx.moveTo(6, -32);
    ctx.lineTo(9, -23);
  } else if (pose === "dance") {
    ctx.moveTo(-6, -32);
    ctx.lineTo(-11, -40 - dance);
    ctx.moveTo(6, -32);
    ctx.lineTo(12, -35 + dance);
  } else if (pose === "chat") {
    ctx.moveTo(-6, -32);
    ctx.lineTo(-10, -24);
    ctx.moveTo(6, -32);
    ctx.lineTo(11, -36);
  } else {
    ctx.moveTo(-6, -32);
    ctx.lineTo(-9 - armSwing, -20);
    ctx.moveTo(6, -32);
    ctx.lineTo(9 + armSwing, -21);
  }
  ctx.stroke();
  if ((moving || pose === "phone") && !options.role && !view.back) {
    ctx.fillStyle = style.bag;
    ctx.beginPath();
    ctx.roundRect(-10, -34, 5.5, 15, 2);
    ctx.fill();
    ctx.strokeStyle = "#173743";
    ctx.lineWidth = 1;
    ctx.stroke();
  }
  ctx.fillStyle = style.skin;
  ctx.beginPath();
  ctx.ellipse(0, -44, 6.2, 7, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = "#183740";
  ctx.lineWidth = 1.1;
  ctx.stroke();
  drawCharacterHair(style, index, view);
  if (lie) {
    // closed eyes: two small arcs
    ctx.strokeStyle = "#173743";
    ctx.lineWidth = 0.8;
    for (const eye of [-2.1, 2.1]) {
      ctx.beginPath();
      ctx.arc(eye, -44.8, 1, 0.15 * Math.PI, 0.85 * Math.PI);
      ctx.stroke();
    }
  } else if (!view.back) {
    ctx.fillStyle = "#173743";
    if (view.side) {
      ctx.beginPath();
      ctx.arc(3.2, -44, 1.05, 0, Math.PI * 2);
      ctx.fill();
    } else {
      for (const eye of [-2.1, 2.1]) {
        ctx.beginPath();
        ctx.arc(eye, -44.5, 0.8, 0, Math.PI * 2);
        ctx.fill();
      }
      if (pose === "chat" || pose === "dance") {
        ctx.strokeStyle = "#8c4f43";
        ctx.lineWidth = 0.8;
        ctx.beginPath();
        ctx.arc(0, -42, 2, 0, Math.PI);
        ctx.stroke();
      }
    }
  }
  drawCharacterProp(pose, style, frame, options.role);
  if (options.player) {
    ctx.strokeStyle = "#173743";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(-5, -35);
    ctx.lineTo(5, -32);
    ctx.stroke();
    roundedRect(-5.4, -34.5, 10.8, 3, 1, "#173743");
    if (!lie) {
      ctx.fillStyle = "#fff";
      ctx.beginPath();
      ctx.arc(view.side ? 3 : 2.2, -44, 1.1, 0, Math.PI * 2);
      ctx.fill();
    }
  }
  ctx.restore();
}
