// The signs sit above the fixtures. Text changes with an API response, position with the camera.
import { camera, isoPoint, roofOf, server, world } from "./scene.js";

const signs = new Map();

function makeSign(shopId) {
  const shelfId = { cafe: "cafe-shelf", merchandise: "merch-shelf" }[shopId];
  const fixture = shelfId
    ? world.interiors.campus.solid.find((item) => item.id === shelfId)
    : world.outdoorShops.find((item) => item.id.replace("-", "_") === shopId);
  if (!fixture) return null;
  const el = document.createElement("span");
  el.className = "shop-sign";
  el.hidden = true;
  document.querySelector("#shop-signs").append(el);
  const point = isoPoint(fixture.x + fixture.w / 2, fixture.y, shelfId ? 82 : 107);
  return { el, point, wing: fixture.wing };
}

export function updateShopSigns(shops) {
  for (const shop of shops) {
    server.shops[shop.id] = shop;
    const sign = signs.get(shop.id) ?? makeSign(shop.id);
    if (!sign) continue;
    signs.set(shop.id, sign);
    const status = shop.unlocked ? `Level ${shop.level}` : `Locked · ${fmt(shop.unlock_price)}`;
    const text = `${shop.name} · ${status}`;
    if (sign.el.textContent !== text) sign.el.textContent = text;
    sign.el.classList.toggle("locked", !shop.unlocked);
  }
}

export function positionShopSigns(center, width, height) {
  for (const sign of signs.values()) {
    const x = Math.round(width / 2 + (sign.point.x - center.x) * camera.zoom);
    const y = Math.round(height / 2 + (sign.point.y - center.y) * camera.zoom);
    const hidden = (sign.wing && roofOf(sign.wing) > 0.05) || x < -110 || x > width + 110 || y < 0 || y > height + 24;
    if (sign.el.hidden !== Boolean(hidden)) sign.el.hidden = Boolean(hidden);
    if (hidden || (x === sign.x && y === sign.y)) continue;
    sign.x = x;
    sign.y = y;
    sign.el.style.transform = `translate(${x}px,${y}px) translate(-50%,-100%)`;
  }
}
