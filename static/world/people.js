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

// How each outfit of the player looks (specs/outfits.md). The server decides which outfit is worn
// (state.outfit), the browser only draws it; an unknown id looks basic.
// shirt: the torso; pants: the legs; sleeves: "long" (in the shirt colour, hands bare) or "short"
// (a sleeve cap over a bare arm); hem: how much longer than a shirt the jacket hangs; hood: drawn
// behind the head; the rest names the details drawn by drawOutfitDetails.
export const OUTFIT_LOOKS = {
  basic: { shirt: WORLD_MATERIALS.lime },
  hawaii: { shirt: "#e8573f", pants: "#d9c49b", sleeves: "short", flowers: true, collar: "open" },
  raincoat: { shirt: "#f2c230", pants: "#26394d", sleeves: "long", hem: 3, hood: true, zip: "#b98d13",
    band: "#e3eaec", pockets: "#d4a51d" },
  tracksuit: { shirt: "#1f3b73", pants: "#1f3b73", sleeves: "long", zip: "#ffffff", stripes: "#ffffff",
    collar: "high" },
  blazer: { shirt: "#2b3445", pants: "#2b3445", sleeves: "long", hem: 1, collar: "suit" },
};
const OUTLINE = "#183740";

// The Merchandise goods a guest puts on right after buying them (spec merch-wear), in the colours of
// the products on the dashboard. torso: drawn like an outfit; cap: drawn on the head.
export const MERCH_LOOKS = {
  hoodie: { torso: { shirt: "#8e5bd6", sleeves: "long", hood: true, hem: 1, pouch: "#7446b8", strings: "#fff1dc", name: "#fff1dc" } },
  tshirt: { torso: { shirt: "#e8573a", sleeves: "short", name: "#fff1dc" } },
  cap: { cap: "#1baf7a", letter: "#fff1dc" },
};

// The torso of every figure; `hem` makes a jacket hang lower.
function torsoPath(hem = 0) {
  ctx.beginPath();
  ctx.moveTo(-7, -36);
  ctx.quadraticCurveTo(0, -40, 7, -35);
  ctx.lineTo(5 + hem * 0.25, -18 + hem);
  ctx.quadraticCurveTo(0, -15 + hem, -5 - hem * 0.25, -18 + hem);
  ctx.closePath();
}

// The two arms of a pose, each a line from the shoulder through its points to the hand.
function armPaths(pose, swing, dance) {
  if (pose === "phone" || pose === "eat" || pose === "drink" || pose === "browse") {
    return [[[-6, -32], [-2, -25], [5, -28]], [[6, -32], [8, -27]]];
  }
  if (pose === "clean" || pose === "repair") return [[[-6, -32], [-2, -23], [6, -20]], [[6, -32], [9, -23]]];
  if (pose === "dance") return [[[-6, -32], [-11, -40 - dance]], [[6, -32], [12, -35 + dance]]];
  // pulling something on over the head (spec merch-wear): both arms up, or one hand at the head
  if (pose === "dress") return [[[-6, -32], [-9, -42], [-4, -50]], [[6, -32], [9, -42], [4, -50]]];
  if (pose === "dress-cap") return [[[-6, -32], [-9, -20]], [[6, -32], [9, -41], [4, -50]]];
  if (pose === "chat") return [[[-6, -32], [-10, -24]], [[6, -32], [11, -36]]];
  return [[[-6, -32], [-9 - swing, -20]], [[6, -32], [9 + swing, -21]]];
}

function strokeLine(points, color, width) {
  ctx.strokeStyle = color;
  ctx.lineWidth = width;
  ctx.beginPath();
  points.forEach(([px, py], i) => (i ? ctx.lineTo(px, py) : ctx.moveTo(px, py)));
  ctx.stroke();
}

// Bare arms as before; a long sleeve with an outline and a bare hand; a short sleeve as a cap.
function drawArms(arms, skin, look) {
  for (const arm of arms) {
    if (look?.sleeves === "long") {
      strokeLine(arm, OUTLINE, 5.6);
      strokeLine(arm, look.shirt, 4.2);
      if (look.stripes) strokeLine(arm.map(([px, py]) => [px + 0.9, py]), look.stripes, 0.8);
      const [hx, hy] = arm[arm.length - 1];
      ctx.fillStyle = skin;
      ctx.beginPath();
      ctx.arc(hx, hy, 1.9, 0, Math.PI * 2);
      ctx.fill();
    } else {
      strokeLine(arm, skin, 4);
      if (look?.sleeves === "short") {
        const [[sx, sy], [nx, ny]] = arm;
        const cap = [[sx, sy], [sx + (nx - sx) * 0.42, sy + (ny - sy) * 0.42]];
        strokeLine(cap, OUTLINE, 6);
        strokeLine(cap, look.shirt, 4.8);
      }
    }
  }
}

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
    // what a guest just bought in the Merchandise shop, and how far it is on (0 to 1; spec merch-wear)
    wear = options.wear && Object.hasOwn(MERCH_LOOKS, options.wear) ? MERCH_LOOKS[options.wear] : null,
    dress = Math.max(0, Math.min(1, options.dress ?? 1)),
    look = options.player ? OUTFIT_LOOKS[options.outfit] ?? OUTFIT_LOOKS.basic
      : wear?.torso && dress >= 1 ? wear.torso : null,
    shirt = look ? look.shirt : options.color || "#64cbc8",
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
  ctx.fillStyle = look?.pants ?? style.pants;
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
  if (look?.stripes && !sit) {
    // the side stripes of the track trousers, along the outside of each leg
    strokeLine([[-4.6, -17.5], [-5.4 + step + dance, -2]], look.stripes, 0.8);
    strokeLine([[4.6, -17.5], [4.4 - step - dance, -2]], look.stripes, 0.8);
  }
  ctx.strokeStyle = OUTLINE;
  ctx.lineWidth = 1.15;
  ctx.fillStyle = shirt;
  torsoPath(look?.hem);
  ctx.fill();
  ctx.stroke();
  if (look) drawOutfitDetails(look, view.back, style.skin);
  if (wear?.torso && dress < 1) drawPullingOn(wear.torso, dress, view.back, style.skin);
  const armSwing = moving ? step * 0.72 : 0;
  drawArms(armPaths(pose, armSwing, dance), style.skin, look);
  // no bag in front of new merch: the NOVA on the chest stays in sight (spec merch-wear)
  if ((moving || pose === "phone") && !options.role && !view.back && !wear?.torso) {
    ctx.fillStyle = style.bag;
    ctx.beginPath();
    ctx.roundRect(-10, -34, 5.5, 15, 2);
    ctx.fill();
    ctx.strokeStyle = "#173743";
    ctx.lineWidth = 1;
    ctx.stroke();
  }
  const hooded = look?.hood ? look : wear?.torso?.hood && dress > 0.5 ? wear.torso : null;
  if (hooded && !lie) {
    // the hood lies around the neck and behind the head
    ctx.fillStyle = hooded.shirt;
    ctx.strokeStyle = OUTLINE;
    ctx.lineWidth = 1.1;
    ctx.beginPath();
    ctx.ellipse(0, -43, 8, 8.4, 0, 0, Math.PI * 2);
    ctx.fill();
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
  if (wear?.cap && !lie) drawCap(wear.cap, dress, view);
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
    if (!look || look === OUTFIT_LOOKS.basic) {
      // the band across the basic shirt; the other outfits show their own details instead
      ctx.strokeStyle = "#173743";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(-5, -35);
      ctx.lineTo(5, -32);
      ctx.stroke();
      roundedRect(-5.4, -34.5, 10.8, 3, 1, "#173743");
    }
    if (!lie) {
      ctx.fillStyle = "#fff";
      ctx.beginPath();
      ctx.arc(view.side ? 3 : 2.2, -44, 1.1, 0, Math.PI * 2);
      ctx.fill();
    }
  }
  ctx.restore();
}

// The details of an outfit on the torso drawn just before (same coordinates), cut to the torso so
// that nothing sticks out: hibiscus flowers, collars, zips, pockets, the reflective band, lapels and tie.
// Seen from behind only the pattern and the band show.
function drawOutfitDetails(look, back, skin) {
  ctx.save();
  torsoPath(look.hem);
  ctx.clip();
  if (look.flowers) {
    // hibiscus: five cream petals around a yellow middle, with a leaf
    for (const [fx, fy] of [[-4, -31.5], [3, -34.5], [0.5, -26], [-3.6, -21], [4, -21.5]]) {
      ctx.fillStyle = "#3f8f5a";
      ctx.beginPath();
      ctx.ellipse(fx + 1.6, fy + 1.2, 1.2, 0.6, 0.6, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = "#fff1dc";
      for (let k = 0; k < 5; k++) {
        const a = (k / 5) * Math.PI * 2;
        ctx.beginPath();
        ctx.arc(fx + Math.cos(a) * 1.1, fy + Math.sin(a) * 1.1, 0.75, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.fillStyle = "#ffd23f";
      ctx.beginPath();
      ctx.arc(fx, fy, 0.55, 0, Math.PI * 2);
      ctx.fill();
    }
  }
  if (look.pouch && !back) {
    // the kangaroo pocket of the hoodie
    ctx.fillStyle = look.pouch;
    ctx.beginPath();
    ctx.moveTo(-4.2, -25);
    ctx.lineTo(4.2, -25);
    ctx.lineTo(5, -19.5);
    ctx.lineTo(-5, -19.5);
    ctx.closePath();
    ctx.fill();
  }
  if (look.strings && !back) {
    ctx.strokeStyle = look.strings;
    ctx.lineWidth = 0.7;
    ctx.beginPath();
    ctx.moveTo(-1.6, -37.5);
    ctx.lineTo(-1.9, -32.5);
    ctx.moveTo(1.6, -37.5);
    ctx.lineTo(1.9, -32.5);
    ctx.stroke();
  }
  if (look.name) {
    // the campus merch: NOVA across the chest (seen from behind across the back)
    ctx.save();
    ctx.fillStyle = look.name;
    ctx.textAlign = "center";
    if (ctx.getTransform().a < 0) ctx.scale(-1, 1); // a figure turned to the left: the letters stay readable
    ctx.font = "900 3.6px system-ui, -apple-system, Segoe UI, sans-serif";
    ctx.fillText("NOVA", 0, look.pouch ? -27.6 : -28.4);
    if (!look.pouch) {
      ctx.font = "800 2.2px system-ui, -apple-system, Segoe UI, sans-serif";
      ctx.fillText("SBE", 0, -25.6);
    }
    ctx.restore();
  }
  if (look.print && !back) {
    // the campus print on the chest: a sun over a wave
    ctx.fillStyle = look.print;
    ctx.beginPath();
    ctx.arc(0, -31, 2.2, Math.PI, 0);
    ctx.fill();
    ctx.strokeStyle = look.print;
    ctx.lineWidth = 0.8;
    ctx.beginPath();
    ctx.moveTo(-3.2, -29.4);
    ctx.quadraticCurveTo(-1.6, -30.6, 0, -29.4);
    ctx.quadraticCurveTo(1.6, -28.2, 3.2, -29.4);
    ctx.stroke();
  }
  if (look.band) {
    ctx.fillStyle = look.band;
    ctx.fillRect(-8, -22.4, 16, 1.4);
  }
  if (!back) {
    if (look.collar === "open") {
      // an open camp collar: skin in the V, two flat collar wings, a row of buttons
      ctx.fillStyle = skin;
      ctx.beginPath();
      ctx.moveTo(-2.4, -38.5);
      ctx.lineTo(2.4, -38.5);
      ctx.lineTo(0, -33.5);
      ctx.closePath();
      ctx.fill();
      ctx.fillStyle = "#f07a62";
      for (const side of [-1, 1]) {
        ctx.beginPath();
        ctx.moveTo(side * 2.4, -38.2);
        ctx.lineTo(side * 4.6, -36.2);
        ctx.lineTo(side * 0.6, -33.6);
        ctx.closePath();
        ctx.fill();
      }
      ctx.fillStyle = "#fff1dc";
      for (const by of [-31, -27, -23, -19.5]) {
        ctx.beginPath();
        ctx.arc(0.4, by, 0.45, 0, Math.PI * 2);
        ctx.fill();
      }
    }
    if (look.collar === "suit") {
      // white shirt and burgundy tie in the V, lighter lapels, two buttons and a pocket square
      ctx.fillStyle = "#f6f3ec";
      ctx.beginPath();
      ctx.moveTo(-3.2, -38.6);
      ctx.lineTo(3.2, -38.6);
      ctx.lineTo(0, -26.5);
      ctx.closePath();
      ctx.fill();
      ctx.fillStyle = "#8c2639";
      ctx.beginPath();
      ctx.moveTo(-0.9, -37.4);
      ctx.lineTo(0.9, -37.4);
      ctx.lineTo(1.2, -29);
      ctx.lineTo(0, -27.4);
      ctx.lineTo(-1.2, -29);
      ctx.closePath();
      ctx.fill();
      ctx.fillStyle = "#3e4a61";
      for (const side of [-1, 1]) {
        ctx.beginPath();
        ctx.moveTo(side * 3.2, -38.6);
        ctx.lineTo(side * 5.2, -35.4);
        ctx.lineTo(side * 3, -33.8);
        ctx.lineTo(side * 0.4, -26.8);
        ctx.closePath();
        ctx.fill();
      }
      ctx.fillStyle = "#11161f";
      for (const by of [-24.3, -21.2]) {
        ctx.beginPath();
        ctx.arc(0, by, 0.55, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.fillStyle = "#f6f3ec";
      ctx.beginPath();
      ctx.moveTo(2.6, -31.6);
      ctx.lineTo(4.8, -31.6);
      ctx.lineTo(3.4, -30);
      ctx.closePath();
      ctx.fill();
    }
    if (look.zip) {
      ctx.strokeStyle = look.zip;
      ctx.lineWidth = 0.7;
      ctx.beginPath();
      ctx.moveTo(0, -38);
      ctx.lineTo(0, -12);
      ctx.stroke();
      ctx.fillStyle = look.zip;
      ctx.fillRect(-0.6, -36.6, 1.2, 1.8); // the zip pull
    }
    if (look.collar === "high") {
      // a stand-up collar with a white edge
      ctx.fillStyle = look.shirt;
      ctx.fillRect(-3.4, -39.5, 6.8, 2.6);
      ctx.fillStyle = look.zip;
      ctx.fillRect(-3.4, -37.2, 6.8, 0.5);
    }
    if (look.pockets) {
      ctx.fillStyle = look.pockets;
      ctx.fillRect(-5.2, -20, 3.6, 1.1);
      ctx.fillRect(1.6, -20, 3.6, 1.1);
    }
  }
  ctx.restore();
}

// The garment coming down over the body while it is pulled on (spec merch-wear): the torso in the
// new colour, shown from the neck down to `share` (0 to 1) of its length.
function drawPullingOn(garment, share, back, skin) {
  ctx.save();
  ctx.beginPath();
  ctx.rect(-10, -41, 20, (26 + (garment.hem ?? 0)) * share);
  ctx.clip();
  ctx.fillStyle = garment.shirt;
  ctx.strokeStyle = OUTLINE;
  ctx.lineWidth = 1.15;
  torsoPath(garment.hem);
  ctx.fill();
  ctx.stroke();
  drawOutfitDetails(garment, back, skin);
  ctx.restore();
}

// A cap on the head, its peak to the front (the figure is already turned with its view). While it is
// put on (share below 1) it comes down onto the head from above.
function drawCap(color, share, view) {
  const lift = (1 - share) * 12;
  ctx.save();
  ctx.translate(0, -lift);
  ctx.globalAlpha = Math.min(1, 0.35 + share);
  ctx.fillStyle = color;
  ctx.strokeStyle = OUTLINE;
  ctx.lineWidth = 1;
  ctx.beginPath(); // the crown, a half dome over the hair
  ctx.ellipse(0, -48.2, 6.6, 4.6, 0, Math.PI, 0);
  ctx.closePath();
  ctx.fill();
  ctx.stroke();
  if (!view.back) {
    ctx.beginPath(); // the peak: in front, or to the side the figure looks to
    if (view.side) ctx.ellipse(5.4, -48.3, 4.2, 1.3, 0.12, 0, Math.PI * 2);
    else ctx.ellipse(0, -47.6, 5.4, 1.7, 0, 0, Math.PI);
    ctx.fill();
    ctx.stroke();
  }
  ctx.fillStyle = "#fff1dc"; // the button on top
  ctx.beginPath();
  ctx.arc(0, -52.6, 0.8, 0, Math.PI * 2);
  ctx.fill();
  if (!view.back && !view.side) {
    // the N of NOVA on the front
    ctx.font = "900 4px system-ui, -apple-system, Segoe UI, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("N", 0, -48.6);
  }
  ctx.restore();
}
