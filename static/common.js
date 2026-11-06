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
    `Forecast for tomorrow: ${outlook.name}, ${range}`, prefix);
}

function drawWeatherChip(el, id, text, title, label, prefix = "") {
  const key = id ? `${id}:${text}:${title}` : "";
  if (el.dataset.weather === key) return;
  el.dataset.weather = key;
  if (!id) {
    el.replaceChildren();
    el.removeAttribute("title");
    el.removeAttribute("aria-label");
    el.removeAttribute("role");
    return;
  }
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("width", "20");
  svg.setAttribute("height", "20");
  svg.setAttribute("aria-hidden", "true");
  svg.style.verticalAlign = "middle";
  svg.innerHTML = WEATHER_ICON[id] ?? "";
  const span = document.createElement("span");
  span.textContent = text;
  el.replaceChildren(...(prefix ? [document.createTextNode(`${prefix} `)] : []), svg, span);
  el.title = title;
  el.setAttribute("role", "img");
  el.setAttribute("aria-label", label);
}
