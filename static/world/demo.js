// The demo card (specs/demo-scenarios.md). It only shows what the server sends in state.demo and
// forwards clicks: which scenario runs, its text and whether its goal is reached are decided on the
// server (scenarios.py). The browser sends a scenario id from the server's list, never a state.
// $ comes from common.js. Every text goes in through textContent.

let folded = null; // the scenario whose text the presenter folded away ("Got it"); browser only
let actions = { getState: () => null, load: () => {}, finish: () => {} };
let shown = ""; // what the card shows now: it is redrawn only when that changes, not on every tick

// A saved scenario that no longer exists (a later version renamed it): only the way out is offered.
const STALE = { id: "", index: 0, count: 0, title: "Demo", text: "This demo scenario no longer exists. End it to play on.",
  goal: "End the demo", done: false, next: null };

export function renderDemo(state) {
  const card = $("#demo-card");
  const demo = state?.demo;
  const active = demo?.active ?? (demo?.stale ? STALE : null);
  $("#btn-demo").hidden = !demo?.scenarios?.length;
  const key = JSON.stringify([active, folded]);
  if (key === shown) return;
  shown = key;
  if (!active) {
    card.hidden = true;
    folded = null;
    return;
  }
  card.hidden = false;
  card.classList.toggle("done", active.done);
  card.classList.toggle("folded", folded === active.id);
  $("#demo-step").textContent = active.count ? `${active.index} of ${active.count}` : "";
  $("#demo-title").textContent = active.title;
  $("#demo-text").textContent = active.text;
  $("#demo-goal").textContent = active.goal;
  $("#demo-check").textContent = active.done ? "✓" : "○";
  const hide = $("#demo-hide");
  hide.textContent = folded === active.id ? "?" : "Got it";
  hide.setAttribute("aria-label", folded === active.id ? "Show the text again" : "Hide the text");
  const next = $("#demo-next");
  next.hidden = !active.next;
  next.textContent = active.done ? "Next ▶" : "Skip scenario";
  const free = $("#demo-free");
  free.textContent = active.next ? "End demo" : "Free play";
  free.classList.toggle("ghost", Boolean(active.next));
}

// How long one tick of the clock takes in the browser: as the scenario says (Decide 2; the server's
// tests keep it in scenarios.TICK_MS_RANGE). The server counts every tick as before; this only paces
// the requests. The floor only guards against a broken answer: below it the rate limit would bite.
export function tickMs(state) {
  const ms = state?.demo?.active?.tick_ms;
  return Number.isInteger(ms) && ms >= 400 ? ms : 1000;
}

function askStart() {
  const state = actions.getState();
  const list = state?.demo?.scenarios ?? [];
  if (!list.length) return;
  const pick = $("#demo-pick");
  pick.replaceChildren(...list.map((s, i) => {
    const option = document.createElement("option");
    option.value = s.id;
    option.textContent = `${i + 1}. ${s.title}`;
    return option;
  }));
  $("#demo-dialog-text").textContent = state.demo.active
    ? "The demo starts again from the scenario you pick."
    : `The demo replaces your run (day ${state.day}, ${fmt(state.cash)} cash) with prepared days. This cannot be undone.`;
  const dialog = $("#demo-dialog");
  dialog.returnValue = "";
  dialog.showModal();
}

export function demoDialogOpen() {
  return $("#demo-dialog").open;
}

export function wireDemo(given) {
  actions = given;
  $("#btn-demo").addEventListener("click", askStart);
  $("#demo-dialog").addEventListener("close", (e) => {
    if (e.target.returnValue === "confirm") actions.load($("#demo-pick").value);
  });
  $("#demo-hide").addEventListener("click", () => {
    const active = actions.getState()?.demo?.active;
    if (!active) return;
    folded = folded === active.id ? null : active.id;
    renderDemo(actions.getState());
  });
  $("#demo-next").addEventListener("click", () => {
    const next = actions.getState()?.demo?.active?.next;
    if (next) actions.load(next);
  });
  $("#demo-free").addEventListener("click", () => actions.finish());
  // a bookmark for the presenter: /?demo opens the start card (nothing changes before the click).
  // The campus runs inside the main page (views.js), so the address is the parent's.
  let address = location.search;
  try { address = window.parent.location.search || address; } catch { /* another origin: ours only */ }
  if (new URLSearchParams(address).has("demo") && !actions.getState()?.demo?.active) askStart();
}
