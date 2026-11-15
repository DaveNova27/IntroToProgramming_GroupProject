// Capture Canvas calls at a fixed time. Different product purchases at the same level
// must produce different fixtures, while buying a staff place changes just the sign.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";

const data = JSON.parse(readFileSync(0, "utf8"));
let drawing;
const paints = new Set();
let fillStyle;
const styleStack = [];
// Sample an actual painted part of each fitting (not the sign, shutter, or browsing figures).
const fittingPaint = {
  cafe: { coffee: "#e9eae4", cake: "#aa6646", bagel: "#e6ac62" },
  merchandise: { hoodie: "#233f54", tshirt: "#385668", cap: "#526e78" },
  surf_shop: { surfboard: "#e8b265", wetsuit: "#192f3b", surf_lesson: "#20444a" },
  beach_cafe: { beer: "#597048", coke_zero: "#a94c40", sandwich: "#c48d53" },
};
const context = new Proxy({}, {
  get: (_, name) => (...args) => {
    drawing.update(JSON.stringify([name, args]));
    if (name === "save") styleStack.push(fillStyle);
    if (name === "restore") fillStyle = styleStack.pop();
    if (name === "fill" || name === "fillRect") paints.add(fillStyle);
    if (name === "measureText") return { width: 40 };
    if (name === "createLinearGradient" || name === "createRadialGradient") return { addColorStop() {} };
  },
  set: (_, name, value) => {
    if (name === "fillStyle") fillStyle = value;
    drawing.update(JSON.stringify([name, value]));
    return true;
  },
});
const signs = [];
globalThis.document = {
  querySelector: (id) => id === "#world" ? { getContext: () => context } : { append: el => signs.push(el) },
  createElement: () => ({ style: {}, classList: { toggle() {} } }),
};
globalThis.window = { matchMedia: () => ({ matches: true }) };
globalThis.Path2D = class { constructor(path) { this.path = path; } };
globalThis.fmt = cents => `€${(cents / 100).toFixed(2)}`;

const { world, scene } = await import("./world/scene.js");
const { updateShopSigns, positionShopSigns } = await import("./world/shop-signs.js");
const { roomActors } = await import("./world/rooms.js");
const { beachActors } = await import("./world/beach.js");
Object.assign(world, data.world);
scene.roofs.nova = 0;

function picture(shops, sid) {
  updateShopSigns(shops);
  paints.clear();
  drawing = createHash("sha256");
  const indoors = sid === "cafe" || sid === "merchandise";
  for (const actor of indoors ? roomActors(0) : beachActors(0)) actor.draw();
  const shop = shops.find(s => s.id === sid);
  for (const [product, color] of Object.entries(fittingPaint[sid])) {
    assert.equal(paints.has(color), shop.products.includes(product), sid + " fitting for " + product);
  }
  return drawing.digest("hex");
}

for (const [sid, states] of Object.entries(data.cases)) {
  const initial = picture(data.fresh, sid);
  const fresh = data.fresh.find(shop => shop.id === sid);
  const sign = signs.find(el => el.textContent.startsWith(fresh.name + " ·"));
  const base = picture(states.base, sid);
  assert.equal(sign.textContent, fresh.name + " · Level 1");
  if (!fresh.unlocked) assert.notEqual(initial, base, sid + " opens its shutter");
  const fittings = new Set([base]);
  for (const [item, shops] of Object.entries(states)) {
    if (item === "base") continue;
    const art = picture(shops, sid);
    assert.equal(sign.textContent, fresh.name + " · Level 2");
    if (item === "staff_1") assert.equal(art, base, sid + " staff place adds no product");
    else {
      assert(!fittings.has(art), sid + " distinctly displays " + item);
      fittings.add(art);
    }
  }
  assert.equal(picture(data.fresh, sid), initial, sid + " resets its fittings");
  if (!fresh.unlocked) assert.equal(sign.textContent, fresh.name + " · Locked · " + fmt(fresh.unlock_price));
}
assert.equal(signs.length, 4);
const indoorSign = signs.find(s => s.textContent.startsWith("Merchandise"));
positionShopSigns({ x: 1100, y: 0 }, 1600, 1000);
assert.equal(indoorSign.hidden, false);
scene.roofs.nova = 1;
positionShopSigns({ x: 1100, y: 0 }, 1600, 1000);
assert.equal(indoorSign.hidden, true);
