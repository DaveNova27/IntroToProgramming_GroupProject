// Switching between the campus and the dashboard.
// The campus is the game and opens first. It is one live page (an iframe) that is
// never reloaded: as the main view it fills the screen, on the dashboard it sits
// over the "Campus live" window. The address ends in #dashboard while the dashboard
// is the main view, so reload and the back button keep working.

const frame = $("#campus-frame");
const slot = $("#campus-slot");
const dash = $("#dash");
const handle = $("#drawer-handle");
let view = null;                 // "dashboard" | "map"
let moving = false;
let pushedDashboard = false;     // we added the #dashboard history entry ourselves
let mapReady = false;            // the map said "ready": it plays the run and sends its ticks

// ---- talking to the map -----------------------------------------------------------

function tellMap(message) {
  frame.contentWindow?.postMessage(message, location.origin);
}

// what the dashboard did goes to the map, which animates it
window.addEventListener("run-changed", (e) => tellMap({ type: "action", ...e.detail }));

// The dashboard's new run is sent by the map once it runs (spec stale-tick): from the queue of its
// ticks, so no tick of the old run reaches the server after it. Before that no tick runs.
window.addEventListener("new-run-wanted", (e) => {
  if (!mapReady) return;
  e.preventDefault();
  tellMap({ type: "new-run" });
});

window.addEventListener("message", (e) => {
  if (e.origin !== location.origin || e.source !== frame.contentWindow) return;
  const msg = e.data || {};
  if (msg.type === "ready") {
    mapReady = true;
    tellMap({ type: "mode", mode: view === "map" ? "main" : "preview" });
    if (view === "map") frame.focus();
  }
  if (msg.type === "action") applyExternalState(msg.after, msg.kind);
  if (msg.type === "new-run-done") toast(msg.error ?? msg.message, msg.error ? "error" : "ok");
  if (msg.type === "open-dashboard") openDrawer();
  if (msg.type === "panel-open") {
    closeDrawer();
    handle.hidden = true; // keep the map panel's close button unobstructed
  }
  if (msg.type === "panel-closed" && view === "map" && !dash.classList.contains("open")) handle.hidden = false;
});

// ---- the live window on the dashboard ------------------------------------------------

// Keep the frame exactly over the slot while the dashboard is the main view
// (cards above it can grow, e.g. when the final banner appears).
function followSlot() {
  if (view === "dashboard" && !moving) {
    const r = slot.getBoundingClientRect();
    const top = `${r.top + window.scrollY}px`;
    const left = `${r.left + window.scrollX}px`;
    if (frame.style.top !== top || frame.style.left !== left
      || frame.style.width !== `${r.width}px` || frame.style.height !== `${r.height}px`) {
      Object.assign(frame.style, { top, left, width: `${r.width}px`, height: `${r.height}px` });
    }
  }
  requestAnimationFrame(followSlot);
}

function setBox(r, radius) {
  Object.assign(frame.style, {
    top: `${r.top}px`, left: `${r.left}px`, width: `${r.width}px`, height: `${r.height}px`, borderRadius: radius,
  });
}

function afterMove(done) {
  const calm = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (calm) return done();
  let finished = false;
  const end = () => {
    if (finished) return;
    finished = true;
    frame.removeEventListener("transitionend", end);
    done();
  };
  frame.addEventListener("transitionend", end);
  setTimeout(end, 700); // in case no transition runs
}

// ---- switching the main view ---------------------------------------------------------

function showMap(animate) {
  view = "map";
  const from = slot.getBoundingClientRect();
  moving = true;
  frame.classList.add("main");
  setBox(from, "12px");
  void frame.getBoundingClientRect();
  if (animate) frame.classList.add("moving");
  setBox({ top: 0, left: 0, width: window.innerWidth, height: window.innerHeight }, "0px");
  const done = () => {
    frame.classList.remove("moving");
    Object.assign(frame.style, { top: "0", left: "0", width: "100vw", height: "100dvh" });
    document.body.classList.add("map-main");
    dash.classList.add("drawer");
    handle.hidden = false;
    moving = false;
    tellMap({ type: "mode", mode: "main" });
    frame.focus();
  };
  if (animate) afterMove(done);
  else done();
}

function showDashboard(animate) {
  view = "dashboard";
  tellMap({ type: "mode", mode: "preview" });
  closeDrawer();
  dash.classList.remove("drawer");
  document.body.classList.remove("map-main");
  handle.hidden = true;
  if (!animate || !frame.classList.contains("main")) {
    frame.classList.remove("main");
    frame.style.borderRadius = "12px";
    return;
  }
  // shrink the full-screen map back into its window
  moving = true;
  const card = slot.closest(".card");
  window.scrollTo({ top: Math.max(0, card.offsetTop - 80) });
  const to = slot.getBoundingClientRect();
  frame.classList.add("moving");
  setBox(to, "12px");
  afterMove(() => {
    frame.classList.remove("moving", "main");
    moving = false;
  });
}

function applyHash(animate) {
  const wanted = location.hash === "#dashboard" ? "dashboard" : "map";
  if (wanted === view) return;
  if (wanted === "map") showMap(animate);
  else showDashboard(animate);
}

// ---- the dashboard as a panel over the map -------------------------------------------

function openDrawer() {
  if (view !== "map") return;
  dash.classList.add("open");
  handle.hidden = true;
}
function closeDrawer() {
  dash.classList.remove("open");
  if (view === "map") {
    handle.hidden = false;
    frame.focus(); // the keys walk the figure again
  }
}

function goDashboard() {
  pushedDashboard = true;
  location.hash = "dashboard";
}
// back to the campus: undo our own history entry, or (opened with #dashboard) drop the hash
function goMap() {
  if (pushedDashboard) return history.back();
  history.replaceState(null, "", location.pathname + location.search);
  applyHash(true);
}

slot.addEventListener("click", goMap);
$("#show-map").addEventListener("click", goMap);
handle.addEventListener("click", openDrawer);
dash.addEventListener("click", (e) => {
  if (e.target.closest("[data-dash-close]")) closeDrawer();
  if (e.target.closest("[data-dash-main]")) goDashboard();
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && dash.classList.contains("open")) closeDrawer();
});
window.addEventListener("hashchange", () => {
  if (location.hash !== "#dashboard") pushedDashboard = false;
  applyHash(true);
});
window.addEventListener("resize", () => {
  if (view === "map" && !moving) Object.assign(frame.style, { width: "100vw", height: "100dvh" });
});

applyHash(false);
requestAnimationFrame(followSlot);
