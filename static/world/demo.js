// The demo card (specs/demo-scenarios.md, specs/demo-day.md). It only shows what the server sends in
// state.demo and forwards clicks: which step runs, its text and whether its goal is reached are decided
// on the server (scenarios.py). The browser sends the demo's id from the server's list, or {} for the
// next step, never a state. $ comes from common.js. Every text goes in through textContent.

let folded = null; // the step whose text the presenter folded away ("Got it"); browser only
let actions = { getState: () => null, load: () => {}, next: () => {}, go: () => {}, finish: () => {} };
let shown = ""; // what the card shows now: it is redrawn only when that changes, not on every tick
let busy = false; // a click of the card is on its way: a second click (a double click) is ignored

// A saved demo that no longer exists (a later version renamed it): only the way out is offered.
const STALE = { id: "", index: 0, count: 0, title: "Demo", text: "This demo no longer exists. End it to play on.",
  goal: "End the demo", button: "", done: false, last: true, call_next: false };

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
  // the one big button: the next thing to do. It walks the figure there (and asks the server for the
  // step first when the step is a jump or waits for the presenter).
  const go = $("#demo-go");
  go.hidden = !active.button || active.done;
  go.textContent = `Next step: ${active.button}`;
  // a skip for the rehearsal: the next step without waiting for the goal
  $("#demo-skip").hidden = active.last || active.call_next || !active.count;
  const free = $("#demo-free");
  free.textContent = active.last ? "Free play" : "End demo";
  free.classList.toggle("ghost", !active.done);
}

// How long one tick of the clock takes in the browser: as the step says (the server's tests keep it in
// scenarios.TICK_MS_RANGE). The server counts every tick as before; this only paces the requests. The
// floor only guards against a broken answer: below it the rate limit would bite.
export function tickMs(state) {
  const ms = state?.demo?.active?.tick_ms;
  return Number.isInteger(ms) && ms >= 400 ? ms : 1000;
}

function askStart() {
  const state = actions.getState();
  const list = state?.demo?.scenarios ?? [];
  if (!list.length) return;
  $("#demo-dialog-text").textContent = state.demo.active
    ? "The demo day starts again from the morning."
    : `The demo replaces your run (day ${state.day}, ${fmt(state.cash)} cash) with one prepared day. This cannot be undone.`;
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
    const first = actions.getState()?.demo?.scenarios?.[0]?.id;
    if (e.target.returnValue === "confirm" && first) actions.load(first);
  });
  $("#demo-hide").addEventListener("click", () => {
    const active = actions.getState()?.demo?.active;
    if (!active) return;
    folded = folded === active.id ? null : active.id;
    renderDemo(actions.getState());
  });
  // review finding: a double click sent two requests for the next step and skipped a whole step.
  // While one click is on its way (the request and the start of the walk) the buttons do nothing.
  const once = (job) => async () => {
    if (busy) return;
    busy = true;
    try {
      await job();
    } finally {
      busy = false;
    }
  };
  $("#demo-go").addEventListener("click", once(async () => {
    const active = actions.getState()?.demo?.active;
    if (!active) return;
    if (active.call_next && !(await actions.next())) return;
    await actions.go(actions.getState()?.demo?.active);
  }));
  $("#demo-skip").addEventListener("click", once(async () => {
    if (await actions.next()) await actions.go(actions.getState()?.demo?.active);
  }));
  $("#demo-free").addEventListener("click", () => actions.finish());
  // a bookmark for the presenter: /?demo opens the start card (nothing changes before the click).
  // The campus runs inside the main page (views.js), so the address is the parent's.
  let address = location.search;
  try { address = window.parent.location.search || address; } catch { /* another origin: ours only */ }
  if (new URLSearchParams(address).has("demo") && !actions.getState()?.demo?.active) askStart();
}
