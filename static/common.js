// Helpers shared by the dashboard (app.js) and the campus map (map.js).

const EMOJI = {
  coffee: "☕", cake: "🍰", bagel: "🥯",
  surfboard: "🏄", wetsuit: "🤿", surf_lesson: "🌊",
  hoodie: "🧥", tshirt: "👕", cap: "🧢",
  beer: "🍺", coke_zero: "🥤", sandwich: "🥪",
};
// one colour per product, used by the dashboard (ACCENT) and the campus display (COLOR)
const ACCENT = {
  coffee: "#eb6834", cake: "#d9487b", bagel: "#c98a3d",
  surfboard: "#3a6fd8", wetsuit: "#2f9e9e", surf_lesson: "#4fb3d9",
  hoodie: "#8e5bd6", tshirt: "#e8573a", cap: "#1baf7a",
  beer: "#e0a21b", coke_zero: "#444b57", sandwich: "#2a78d6",
};

const $ = (sel, root = document) => root.querySelector(sel);

function esc(text) {
  return String(text).replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

// cents -> "€12.50", the same format as logic.fmt
function fmt(cents) {
  const sign = cents < 0 ? "-" : "";
  const euros = (Math.abs(cents) / 100).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return `${sign}€${euros}`;
}
const fmtSigned = (cents) => (cents > 0 ? "+" : "") + fmt(cents);

// ---- badges (specs/badges.md): the medal markup, the same on the dashboard and the campus ----
const TIER_NAME = { bronze: "Bronze medal", silver: "Silver medal", gold: "Gold medal" };

// A badge from the server as a medal: its tier's metal, grey while not earned. Look in badges.css.
function medalHtml(badge) {
  const tier = badge.day === null ? "locked" : (TIER_NAME[badge.tier] ? badge.tier : "bronze");
  return `<span class="medal ${tier}" aria-hidden="true"><span class="coin"><span>${esc(badge.icon)}</span></span></span>`;
}

// The earned badges of a run as a grid of medals (the end of the season), or a short line.
function medalGridHtml(badges) {
  const earned = (badges || []).filter((b) => b.day !== null);
  if (!earned.length) return `<p class="note">No badges this run.</p>`;
  return `<ul class="medal-grid">${earned.map((b) => `
    <li>${medalHtml(b)}<b>${esc(b.name)}</b><small>Day ${esc(b.day)}</small></li>`).join("")}</ul>`;
}

// A short message in the corner; errors stay longer.
function toast(text, kind = "ok") {
  const el = document.createElement("div");
  el.className = `toast ${kind === "error" ? "error" : ""}`;
  el.innerHTML = `<span aria-hidden="true">${kind === "error" ? "✕" : "✓"}</span><span></span>`;
  el.lastChild.textContent = text;
  $("#toasts").append(el);
  setTimeout(() => el.remove(), kind === "error" ? 6000 : 3500);
}

// Today's weather: a small picture drawn here (no files) and the temperature as text.
const WEATHER_ICON = {
  sun: '<circle cx="12" cy="12" r="5" fill="#f5b82e"/><g stroke="#f5b82e" stroke-width="2" stroke-linecap="round"><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1L7 17M17 7l2.1-2.1"/></g>',
  heat: '<circle cx="12" cy="12" r="6" fill="#ee6a2c"/><g stroke="#ee6a2c" stroke-width="2" stroke-linecap="round"><path d="M12 1.5v3M12 19.5v3M1.5 12h3M19.5 12h3M4.6 4.6l2 2M17.4 17.4l2 2M4.6 19.4l2-2M17.4 6.6l2-2"/></g>',
  rain: '<path d="M7 15a4.5 4.5 0 0 1 .6-8.9A5.5 5.5 0 0 1 18 7.5 3.8 3.8 0 0 1 17.5 15z" fill="#9db0c4"/><g stroke="#3d82d6" stroke-width="2" stroke-linecap="round"><path d="M8 18l-1 3M12 18l-1 3M16 18l-1 3"/></g>',
  storm: '<path d="M7 14a4.5 4.5 0 0 1 .6-8.9A5.5 5.5 0 0 1 18 6.5 3.8 3.8 0 0 1 17.5 14z" fill="#6f7d90"/><path d="M12.5 13l-3 5h3l-1.5 4 5-6.5h-3.2l1.7-2.5z" fill="#f5c52e"/>',
};

// icon names come from the fixed list above, the text is set with textContent.
// Nothing is rebuilt while the weather is unchanged; no weather (run over) clears the chip.
function showWeather(el, weather) {
  if (!weather) return drawWeatherChip(el, null);
  drawWeatherChip(el, weather.id, ` ${weather.temperature} °C`, weather.name,
    `${weather.name}, ${weather.temperature} °C`);
}

// Tomorrow's forecast (outlook): the same picture with the forecast's temperature range.
// prefix: a word shown before the picture where no label says "tomorrow" already.
function showOutlook(el, outlook, prefix = "") {
  if (!outlook) return drawWeatherChip(el, null);
  const range = `${outlook.temp_low}–${outlook.temp_high} °C`;
  drawWeatherChip(el, outlook.id, ` ${range}`, `Forecast for day ${outlook.day}: ${outlook.name}`,
    `Forecast for day ${outlook.day}: ${outlook.name}, ${range}`, prefix);
}

// An event as short text ("Surf festival 2/3"); no event gives "". Shown only while the day is open.
function eventText(event) {
  if (!event) return "";
  return event.days > 1 ? `${event.name} ${event.day_of}/${event.days}` : event.name;
}

// The weather picture as an SVG element; only ids from the fixed list above give a picture.
function weatherIconEl(id, size) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("width", size);
  svg.setAttribute("height", size);
  svg.setAttribute("aria-hidden", "true");
  svg.style.verticalAlign = "middle";
  svg.innerHTML = Object.hasOwn(WEATHER_ICON, id) ? WEATHER_ICON[id] : "";
  return svg;
}

// The same picture as markup, for places built with a template (the evening report).
function weatherIconMarkup(id, size) {
  return weatherIconEl(id, size).outerHTML;
}

// The real weather of a day is shown once the day is opened (state.shift is set); before
// that the forecast stands in its place. The server sends both; this only picks what to show.
function dayIsOpen(state) {
  return Boolean(state.shift) && !state.finished;
}

// What the evening report says per shop. The advice itself comes from the server.
const TIP_TEXT = {
  more: (p) => `more customers expected (${p} %), stock up.`,
  less: (p) => `fewer customers expected (${p} %), buy less.`,
  normal: (p) => `about the usual customers (${p} %).`,
};

function drawWeatherChip(el, id, text, title, label, prefix = "") {
  const key = id ? `${prefix}:${id}:${text}:${title}:${label}` : "";
  if (el.dataset.weather === key) return;
  el.dataset.weather = key;
  // the label the page gave the chip stays the name of an empty chip
  el.dataset.baseLabel ??= el.getAttribute("aria-label") ?? "";
  if (!id) {
    el.replaceChildren();
    el.removeAttribute("title");
    el.removeAttribute("role");
    if (el.dataset.baseLabel) el.setAttribute("aria-label", el.dataset.baseLabel);
    else el.removeAttribute("aria-label");
    return;
  }
  const svg = weatherIconEl(id, 20);
  const span = document.createElement("span");
  span.textContent = text;
  el.replaceChildren(...(prefix ? [document.createTextNode(`${prefix} `)] : []), svg, span);
  el.title = title;
  el.setAttribute("role", "img");
  el.setAttribute("aria-label", label);
}

// ---- customers and the price curve (pricing) -------------------------------------------
// Every number comes from the server (state.products[].breakdown, state.price_curves,
// POST /api/price_preview). Nothing here decides a rule; this only draws and words it.

function customersText(n) {
  return n === 0 ? "no customers today" : n === 1 ? "about 1 customer today" : `about ${n} customers today`;
}

function splitText(split, segments) {
  return segments.map((seg) => `${esc(seg.name.toLowerCase())} ${split[seg.id] ?? 0}`).join(" · ");
}

// The "why" lines of one product: base, each step, the total and the expected profit.
function breakdownHtml(b, segments) {
  const keep = segments.map((seg) => `${esc(seg.name.toLowerCase())} ${b.keep[seg.id]} %`).join(", ");
  const lines = [`<li><span>Normal day</span><b>${b.base}</b></li>`];
  b.steps.forEach((step, i) => {
    lines.push(`<li><span>${esc(step.name)}</span><b>${step.customers}</b><small>${splitText(step.split, segments)}</small></li>`);
    if (i === 0) lines.push(`<li class="aside">At this price they still buy: ${keep} of their normal amount.</li>`);
  });
  const limited = b.sellable < b.customers ? ` · the stock of ${b.sellable} limits it` : "";
  lines.push(`<li class="total"><span>Customers today</span><b>${b.customers}</b><small>${splitText(b.split, segments)}</small></li>`);
  lines.push(`<li class="aside">Expected profit: ${b.sellable} × ${fmt(b.unit_profit)} = <b>${fmt(b.expected_profit)}</b>${limited}</li>`);
  return `<ul class="why-lines">${lines.join("")}</ul>`;
}

// A shop's curve on a normal day: price in percent of the reference price (0 to 250) across,
// customers up. points = [[percent, hundredths of a customer]] from the server.
const CURVE_TOP = 1700;
function curveSvg(points, pricePercent) {
  const h = 56;
  const y = (hundredths) => (h - (Math.min(hundredths, CURVE_TOP) / CURVE_TOP) * (h - 4)).toFixed(1);
  const line = [[0, points[0][1]], ...points].map(([x, v]) => `${x},${y(v)}`).join(" ");
  const at = Math.max(0, Math.min(pricePercent, 250));
  return `<svg class="curve-svg" viewBox="0 0 250 ${h}" preserveAspectRatio="none" role="img"
      aria-label="Customers at each price on a normal day">
    <polygon class="curve-area" points="0,${h} ${line} 250,${h}"/>
    <polyline class="curve-line" points="${line}" vector-effect="non-scaling-stroke"/>
    <line class="curve-ref" x1="100" x2="100" y1="0" y2="${h}" vector-effect="non-scaling-stroke"/>
    <line class="curve-marker" x1="${at}" x2="${at}" y1="0" y2="${h}" vector-effect="non-scaling-stroke"/>
  </svg>`;
}

function setCurveMarker(root, pricePercent) {
  const at = Math.max(0, Math.min(pricePercent, 250));
  const marker = root.querySelector(".curve-marker");
  if (marker) {
    marker.setAttribute("x1", at);
    marker.setAttribute("x2", at);
  }
}

// One live preview per price row (a dashboard card or a campus panel row): wait a moment after
// typing, ask the server, hand the answer to onAnswer. Typing again, an empty or invalid value,
// or saving cancels the one that is still waiting, so a late answer never overwrites the row.
function cancelPricePreview(row) {
  row.dataset.ask = String((Number(row.dataset.ask) || 0) + 1);
  clearTimeout(row.previewTimer);
}

function schedulePricePreview(row, product, text, onAnswer) {
  cancelPricePreview(row);
  const ask = row.dataset.ask;
  row.previewTimer = setTimeout(async () => {
    const b = await fetchPricePreview(product, text);
    if (b && row.isConnected && row.dataset.ask === ask) onAnswer(b);
  }, 200);
}

// What a typed price would bring, asked from the server (nothing is saved). null if refused.
async function fetchPricePreview(product, price) {
  try {
    const res = await fetch("/api/price_preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ product, price }),
    });
    const data = await res.json();
    return data.preview ?? null;
  } catch {
    return null;
  }
}
