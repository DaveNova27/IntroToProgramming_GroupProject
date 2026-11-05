// Helpers shared by the dashboard (app.js) and the campus map (map.js).

const EMOJI = {
  coffee: "☕", cake: "🍰", bagel: "🥯",
  surfboard: "🏄", wetsuit: "🤿", surf_lesson: "🌊",
  hoodie: "🧥", tshirt: "👕", cap: "🧢",
  beer: "🍺", coke_zero: "🥤", sandwich: "🥪",
};
const ACCENT = {
  coffee: "var(--coffee)", cake: "#d9487b", bagel: "#c98a3d",
  surfboard: "#3a6fd8", wetsuit: "#2f9e9e", surf_lesson: "#4fb3d9",
  hoodie: "#8e5bd6", tshirt: "#e8573a", cap: "#1baf7a",
  beer: "#e0a21b", coke_zero: "#444b57", sandwich: "var(--sandwich)",
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
