// Head-up display, stock and price panels, end-of-day cards. The screen only shows
// what the server answers and forwards clicks: every rule is decided in logic.py.
// $, esc, fmt, fmtSigned, toast and EMOJI come from common.js.

import { DAY_END, MORNING, reducedMotion, scene, server } from "./scene.js";

const COLOR = ACCENT; // from common.js: one colour per product

// The world runs embedded in the dashboard page (views.js): small or full screen.
const embedded = new URLSearchParams(location.search).has("embed");

let state = null;
let animating = false;
let dayRunning = null;
let fast = false;
let panelMode = null;
let armedFire = null; // the employee whose Dismiss was clicked once (the panel is redrawn every tick)
let orderProduct = "coffee";
let placePlayer = () => {};

// What happened plays one after another, wherever the action came from.
let chain = Promise.resolve();
function enqueue(job) {
  chain = chain.then(job).catch((err) => console.error(err));
  return chain;
}

function tellDashboard(message) {
  if (embedded) window.parent.postMessage(message, location.origin);
}

const product = (pid) => state.products.find((p) => p.id === pid);

function previewDemand(cents, ref) {
  if (cents <= ref) return state.demand_levels.at_or_below_ref;
  if (cents <= 2 * ref) return state.demand_levels.up_to_double_ref;
  return 0;
}

async function send(path, body) {
  try {
    const res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    try {
      return await res.json();
    } catch {
      toast("The server hit an error. Nothing was saved.", "error");
      return null;
    }
  } catch {
    toast("Could not reach the server. Is app.py still running?", "error");
    return null;
  }
}

// ---- the clock (only light) ----------------------------------------------------------

// Browsers pause animation frames in a hidden tab; keep going with a timer there.
const nextFrame = (cb) => (document.hidden ? setTimeout(() => cb(performance.now()), 100) : requestAnimationFrame(cb));

function tween(ms, update) {
  if (fast || reducedMotion || ms <= 0) {
    update(1);
    return Promise.resolve();
  }
  return new Promise((resolve) => {
    const start = performance.now();
    const frame = (now) => {
      const k = fast ? 1 : Math.max(0, Math.min((now - start) / ms, 1));
      update(k);
      if (k < 1) nextFrame(frame);
      else resolve();
    };
    nextFrame(frame);
  });
}

// A new run of the clock takes over from one still going.
let clockRun = 0;
function runClock(from, to, ms) {
  const run = ++clockRun;
  return tween(ms, (k) => {
    if (run === clockRun) scene.clock = from + (to - from) * k;
  });
}

// While a day runs the clock follows the server's ticks (display only, no rule reads it).
// A big gap, e.g. after loading the page in the middle of a day, is closed at once.
function followDay() {
  const sh = state.shift;
  if (!sh || animating) return;
  const target = MORNING + (DAY_END - MORNING) * Math.min(sh.tick / sh.day_ticks, 1);
  runClock(scene.clock, target, Math.abs(target - scene.clock) > 60 ? 0 : 1000);
}

// The day closed on the server: the clock goes on to the evening, not with a jump.
function dayEnded() {
  runClock(scene.clock, DAY_END, 900);
}

export function updateClock() {
  const minutes = Math.floor(scene.clock);
  const text = `${String(Math.floor(minutes / 60)).padStart(2, "0")}:${String(minutes % 60).padStart(2, "0")}`;
  const el = $("#stat-time");
  if (el.textContent !== text) el.textContent = text;
}

// ---- head-up display -----------------------------------------------------------------

function renderHud() {
  scene.day = Math.min(state.day, state.last_day);
  $("#stat-day").textContent = state.finished ? "Done" : `${state.day} / ${state.last_day}`;
  showWeather($("#stat-weather"), state.weather);
  $("#stat-cash").textContent = fmt(state.cash);
  $("#stat-stock").textContent = fmt(state.stock_value);
  const gain = $("#stat-gain");
  gain.textContent = fmtSigned(state.overall_gain);
  gain.className = state.overall_gain > 0 ? "up" : state.overall_gain < 0 ? "down" : "";
  $("#hud-stock").innerHTML = `<h3>Stock</h3>${state.products.map((p) => `
    <div class="stock-row" style="--accent:${COLOR[p.id]}">
      <span class="em" aria-hidden="true">${EMOJI[p.id]}</span>
      <span class="nm">${esc(p.name)}<small>sells up to ${p.demand} a day</small></span>
      <span class="units">${p.stock}</span>
    </div>`).join("")}`;
}

function renderToolbar() {
  const locked = animating || state.finished;
  $("#btn-order").disabled = locked;
  $("#btn-prices").disabled = locked || !!state.shift;
  $("#btn-shops").disabled = locked;
  $("#btn-shift").disabled = locked;
  $("#btn-shift").querySelector(".txt").textContent = "Shift";
  $("#btn-open").disabled = locked;
  $("#btn-editor").hidden = !state.editor;
  $("#btn-editor").disabled = animating;
  $("#open-label").textContent = dayRunning
    ? `Day ${dayRunning} is open…`
    : state.finished ? "Run complete"
    : dayButtonLabel();
  $("#btn-fast").hidden = !animating;
  const empty = state.products.every((p) => p.stock === 0);
  $("#btn-order").classList.toggle("hint", empty && !locked);
}

function renderAll() {
  server.staff = state.staff; // the figures in the Cafe are drawn from this (rooms.js)
  server.shift = state.shift;
  const open = state.shops.find((sh) => sh.id === state.shift?.shop);
  server.storeroom = open ? state.products.filter((p) => open.products.includes(p.id)).reduce((n, p) => n + p.stock, 0) : 0;
  renderHud();
  renderToolbar();
  if (panelMode) renderPanel();
  syncShiftTimer();
  followDay();
}

// ---- panels --------------------------------------------------------------------------

function openPanel(mode) {
  if (animating || (state.finished && mode !== "editor")) return;
  panelMode = mode;
  editorKey = "";
  $("#panel").hidden = false;
  tellDashboard({ type: "panel-open" }); // both use the right side of the screen
  renderPanel();
}

function closePanel() {
  if (panelMode === null) return;
  panelMode = null;
  $("#panel").hidden = true;
  tellDashboard({ type: "panel-closed" });
}

// The Dorm (spec nova-zones): what the server already knows about the day, as text, and one button
// that does what the Open button does. No rule here: the server decides, as before.
// what the Open button says: skip while a shift is on, otherwise open the day
const dayButtonLabel = () => (state.shift ? `Skip day ${state.day}` : `Open day ${state.day}`);

function renderDormPanel(body) {
  $("#panel-title").textContent = "Your room";
  const weather = state.weather ? `${esc(state.weather.name)}, ${esc(state.weather.temperature)} °C` : "—";
  const label = state.finished ? "The run is complete" : dayButtonLabel();
  body.innerHTML = `
    <p class="note">A quiet room with a view of the sea. The day starts and ends here.</p>
    <dl class="dorm-facts">
      <div><dt>Day</dt><dd>${state.finished ? "Done" : `${esc(state.day)} / ${esc(state.last_day)}`}</dd></div>
      <div><dt>Cash</dt><dd>${fmt(state.cash)}</dd></div>
      <div><dt>Weather</dt><dd>${weather}</dd></div>
    </dl>
    <button type="button" class="btn" data-dorm-open ${state.finished ? "disabled" : ""}>${esc(label)}</button>`;
}

function renderPanel() {
  const body = $("#panel-body");
  if (panelMode === "order") {
    $("#panel-title").textContent = "Order stock";
    const p = product(orderProduct);
    const max = Math.floor(state.cash / p.cost);
    body.innerHTML = `
      <div class="pick" role="group" aria-label="Product">
        ${state.products.map((x) => `
          <button type="button" data-pick="${esc(x.id)}" aria-pressed="${x.id === orderProduct}" style="--accent:${COLOR[x.id]}">
            <span class="em" aria-hidden="true">${EMOJI[x.id]}</span>
            <span class="nm">${esc(x.name)}</span>
            <small>${fmt(x.cost)} each · ${x.stock} in stock</small>
          </button>`).join("")}
      </div>
      <form id="order-form">
        <div class="field-label"><span>Quantity</span><span>up to ${max} affordable</span></div>
        <div class="stepper">
          <button type="button" data-step="-1" aria-label="One less">−</button>
          <input name="quantity" inputmode="numeric" autocomplete="off" value="10" aria-label="Quantity">
          <button type="button" data-step="1" aria-label="One more">+</button>
        </div>
        <div class="chips">
          ${[5, 10, 25].map((n) => `<button type="button" class="chip" data-set="${n}">${n}</button>`).join("")}
          <button type="button" class="chip" data-set="${max}">Max (${max})</button>
        </div>
        <div class="total" id="order-total"></div>
        <p class="error" id="order-error"></p>
        <button class="btn wide" type="submit">Order</button>
      </form>`;
    updateOrderTotal();
  } else if (panelMode === "editor") {
    $("#panel-title").textContent = "Editor";
    renderEditorPanel(body);
  } else if (panelMode === "shops") {
    $("#panel-title").textContent = "Shops";
    body.innerHTML = `
      <p class="note">Unlock shops and buy upgrades with cash. Every purchase raises the shop's level by 1.</p>
      <p class="error" id="shops-error"></p>
      ${state.shops.map((s) => `
        <section class="shop-card">
          <h3>${esc(s.name)} <small>${s.unlocked ? `Level ${s.level}` : "Locked"}</small></h3>
          ${s.unlocked ? `
            <p class="note">Sells ${s.products.map((id) => esc(product(id)?.name ?? id)).join(", ")} ·
              ${s.staff_places} employee place${s.staff_places === 1 ? "" : "s"} ·
              storeroom ${s.storage}, counter ${s.counter}</p>
            ${staffBlock(s)}
            ${s.offers.map((o) => `
              <div class="shop-offer">
                <span class="nm">${esc(o.name)}</span>
                ${o.bought
                  ? `<span class="owned">Owned</span>`
                  : `<button class="btn" type="button" data-upgrade-shop="${esc(s.id)}" data-upgrade-item="${esc(o.id)}"
                      ${!o.affordable || !o.available ? "disabled" : ""}
                      ${o.available ? "" : 'title="Buy the first employee place first"'}>${fmt(o.price)}</button>`}
              </div>`).join("")}`
          : `<div class="shop-offer">
              <span class="nm">Start with ${esc(s.start_product_name)}</span>
              <button class="btn" type="button" data-unlock="${esc(s.id)}"
                ${s.affordable ? "" : "disabled"}>Unlock ${fmt(s.unlock_price)}</button>
            </div>`}
        </section>`).join("")}`;
  } else if (panelMode === "dorm") {
    renderDormPanel(body);
  } else if (panelMode === "shift") {
    renderShiftPanel(body);
  } else if (panelMode === "prices") {
    $("#panel-title").textContent = "Prices";
    body.innerHTML = `
      <p class="note">Customers buy ${state.demand_levels.at_or_below_ref} a day at or below the reference price, ${state.demand_levels.up_to_double_ref} up to twice it, none above.</p>
      ${state.products.map((p) => `
        <form class="price-row" data-price-form="${esc(p.id)}">
          <span class="em" aria-hidden="true">${EMOJI[p.id]}</span>
          <span class="nm">${esc(p.name)}<small>Ref. ${fmt(p.ref_price)} · cost ${fmt(p.cost)}</small></span>
          <label class="euro"><span>€</span><input name="price" inputmode="decimal" autocomplete="off"
            value="${(p.price / 100).toFixed(2)}" aria-label="${esc(p.name)} price in euro"></label>
          <button class="btn" type="submit">Save</button>
          <span class="demand" data-demand>Sells up to <b>${p.demand}</b> a day</span>
          <p class="error" data-error></p>
        </form>`).join("")}`;
  }
}

// ---- editor mode (spec editor-mode) -------------------------------------------------
// Only shown when the server says editor:true. Every button sends one request; the server
// checks the switch and every value, and answers with the new state or the reason.

const centsOf = (text) => { // "12.5" or "12,50" euros -> whole cents, or NaN
  const m = /^(-?)(\d+)(?:[.,](\d{1,2}))?$/.exec(String(text).trim());
  return m ? Number(m[1] + m[2]) * 100 + (m[3] ? Number(m[1] + m[3].padEnd(2, "0")) : 0) : NaN;
};

let editorKey = "";
function renderEditorPanel(body) {
  const info = state.editor_info;
  if (!info) return;
  // do not redraw under the user's fingers while they type: only when the state changed
  const key = JSON.stringify([state.day, state.cash, state.finished, state.weather?.id, state.shops.map((s) => s.level), !!state.shift]);
  if (key === editorKey) return;
  editorKey = key;
  const busy = state.shift ? "disabled title=\"A day is open: finish or skip it first\"" : "";
  body.innerHTML = `
    <p class="note">Dev tools. Day ${state.day}, cash ${fmt(state.cash)}. The server only accepts them with CT_EDITOR=1 on this computer.</p>
    <p class="error" id="editor-error"></p>
    <section class="editor-block"><h3>Cash</h3>
      <form class="editor-row" data-editor="cash">
        <input name="euros" inputmode="decimal" aria-label="Amount in euro" value="1000">
        <button class="btn" type="submit" value="set">Set</button>
        <button class="btn ghost" type="submit" value="add">Add</button>
      </form></section>
    <section class="editor-block"><h3>Weather</h3>
      <form class="editor-row" data-editor="weather">
        <select name="weather" aria-label="Weather">
          <option value="">Seed's forecast</option>
          ${info.weather.map((w) => `<option value="${esc(w.id)}" ${state.weather?.id === w.id ? "selected" : ""}>${esc(w.name)}</option>`).join("")}
        </select>
        <button class="btn" type="submit">Fix</button>
      </form>
      <p class="note">Stays fixed for today and the days after, until set back to the forecast.</p></section>
    <section class="editor-block"><h3>Skip days</h3>
      <form class="editor-row" data-editor="skip">
        <input name="days" inputmode="numeric" aria-label="Days" value="5">
        <button class="btn" type="submit" ${busy}>Skip</button>
      </form></section>
    <section class="editor-block"><h3>Day</h3>
      <form class="editor-row" data-editor="day">
        <input name="day" inputmode="numeric" aria-label="Day" value="${state.day}">
        <button class="btn" type="submit" ${busy}>Set day</button>
      </form>
      <p class="note">Going back cuts the history from that day.</p></section>
    <section class="editor-block"><h3>Shops</h3>
      <form data-editor="shops">
        ${state.shops.map((s) => `<div class="editor-row"><label for="lvl-${esc(s.id)}">${esc(s.name)}</label>
          <select id="lvl-${esc(s.id)}" name="${esc(s.id)}">
            ${Array.from({ length: info.max_level[s.id] + 1 }, (_, n) => `<option value="${n}" ${n === s.level ? "selected" : ""}>${n === 0 ? "Locked" : `Level ${n}`}</option>`).join("")}
          </select></div>`).join("")}
        <button class="btn wide" type="submit" ${busy}>Set levels</button>
      </form>
      <div class="editor-row"><button class="btn ghost" type="button" data-editor-fill ${busy}>Fill storerooms</button></div></section>
    <section class="editor-block"><h3>Seed</h3>
      <form class="editor-row" data-editor="seed">
        <input name="seed" inputmode="numeric" aria-label="Seed" placeholder="0 to ${info.max_seed}">
        <button class="btn" type="submit" ${busy}>Set seed</button>
      </form></section>
    <section class="editor-block"><h3>Teleport (${esc(state.player.zone)})</h3>
      <form class="editor-row" data-editor="teleport">
        <input name="x" inputmode="decimal" aria-label="x" value="${Number(state.player.x).toFixed(1)}">
        <input name="y" inputmode="decimal" aria-label="y" value="${Number(state.player.y).toFixed(1)}">
        <button class="btn" type="submit" ${busy}>Go</button>
      </form></section>
    <section class="editor-block"><h3>Reset the run</h3>
      <form class="editor-row" data-editor="reset">
        <input name="seed" inputmode="numeric" aria-label="Seed (optional)" placeholder="seed (optional)">
        <button class="btn danger" type="submit">Reset</button>
      </form></section>`;
}

async function editorAction(path, body, { moved = false } = {}) {
  if (animating) return;
  const data = await send(path, body);
  if (!data) return;
  state = data.state;
  editorKey = ""; // the numbers changed: redraw the panel
  if (data.error) {
    renderAll();
    const el = $("#editor-error");
    if (el) el.textContent = data.error;
    return toast(data.error, "error");
  }
  if (moved) placePlayer(state.player);
  renderAll();
  tellDashboard({ type: "action", after: data.state });
  toast(data.message);
}

const wholeOrNull = (text) => (String(text).trim() === "" ? null : Number(text));

function wireEditor() {
  const panel = $("#panel");
  panel.addEventListener("submit", (e) => {
    const form = e.target.closest("[data-editor]");
    if (!form) return;
    e.preventDefault();
    const kind = form.dataset.editor;
    const f = form.elements;
    if (kind === "cash") {
      const mode = e.submitter?.value || "set";
      return editorAction("/api/editor/cash", { mode, cents: centsOf(f.euros.value) });
    }
    if (kind === "weather") return editorAction("/api/editor/weather", { weather: f.weather.value || null });
    if (kind === "skip") return editorAction("/api/editor/skip-days", { days: wholeOrNull(f.days.value) });
    if (kind === "day") return editorAction("/api/editor/state", { patch: { day: wholeOrNull(f.day.value) } });
    if (kind === "seed") return editorAction("/api/editor/state", { patch: { seed: wholeOrNull(f.seed.value) } });
    if (kind === "shops") {
      const shops = {};
      for (const s of state.shops) shops[s.id] = { level: Number(f[s.id].value) };
      return editorAction("/api/editor/state", { patch: { shops } });
    }
    if (kind === "teleport") {
      const player = { zone: state.player.zone, x: Number(f.x.value), y: Number(f.y.value) };
      return editorAction("/api/editor/state", { patch: { player } }, { moved: true });
    }
    if (kind === "reset") {
      if (!confirm("Reset the whole run to day 1?")) return;
      const seed = wholeOrNull(f.seed.value);
      return editorAction("/api/editor/reset", seed === null ? { confirm: true } : { confirm: true, seed }, { moved: true });
    }
  });
  panel.addEventListener("click", (e) => {
    if (!e.target.closest("[data-editor-fill]")) return;
    // an even share of each storeroom per product; the server checks the limits
    const stock = {};
    for (const s of state.shops) {
      if (s.unlocked && s.products.length) for (const id of s.products) stock[id] = Math.floor(s.storage / s.products.length);
    }
    editorAction("/api/editor/state", { patch: { stock } });
  });
}

// ---- employees in the shop window ----------------------------------------------------
// Only shows what the server sent (state.staff) and forwards the clicks. Names come from the
// server's fixed list and go through esc().

function staffBlock(shop) {
  const staff = state.staff;
  const places = staff.places.filter((p) => p.shop === shop.id);
  if (!places.length) return "";
  const rows = places.map((p) => {
    const e = staff.employees.find((x) => x.id === p.employee);
    if (e) {
      return `<div class="shop-offer staff-row">
        <span class="nm">${esc(e.name)} · ${esc(e.job_name)} · level ${e.level}
          <small>${e.working ? `wage ${fmt(e.wage)} a day` : "stopped working: no money for the wage"}</small></span>
        ${e.upgrade_price === null ? `<span class="owned">Top level</span>`
          : `<button class="btn" type="button" data-staff-upgrade="${e.id}"
              ${e.upgrade_price > state.cash ? "disabled" : ""}>Level up ${fmt(e.upgrade_price)}</button>`}
        <button class="btn ghost" type="button" data-staff-fire="${e.id}">${armedFire === e.id ? "Sure? Click again" : "Dismiss"}</button>
      </div>`;
    }
    if (!p.bought) {
      return `<div class="shop-offer staff-row"><span class="nm">${esc(p.job_name)}
        <small>buy "Employee place ${p.place}" below: it hires them</small></span></div>`;
    }
    return `<div class="shop-offer staff-row"><span class="nm">${esc(p.job_name)}
      <small>place ${p.place} is free</small></span>
      <button class="btn" type="button" data-hire-shop="${esc(p.shop)}" data-hire-place="${p.place}"
        ${staff.hire_price > state.cash ? "disabled" : ""}>Hire ${fmt(staff.hire_price)}</button></div>`;
  });
  const free = places.some((p) => p.bought && p.employee === null);
  return `<h4 class="staff-title">Employees</h4>${free ? `<p class="note">A free place is one you dismissed someone from. Hire a new employee for it (${fmt(staff.hire_price)}): they refill and sell on their own while the day runs.</p>` : ""}${rows.join("")}`;
}

// ---- a day played live in the Cafe ---------------------------------------------------
// The server holds the counter, the queue and the clock. This only shows them and sends
// each refill, sale and tick. Where the figure stands plays no part.

let shiftHtml = "";
let shiftTimer = null;
let shiftBusy = false;

function renderShiftPanel(body) {
  $("#panel-title").textContent = "Shift";
  const sh = state.shift;
  if (!sh) {
    shiftHtml = "";
    body.innerHTML = `<p class="note">Open the day first. Then start your shift here while the day runs.</p>`;
    return;
  }
  if (!$("#shift-clock")) {
    body.innerHTML = `<progress id="shift-clock"></progress><div id="shift-body"></div>`;
    shiftHtml = "";
  }
  // the bar shows the shift once it runs (its 90 seconds start with it), else the day
  const working = sh.shop && !sh.over;
  $("#shift-clock").max = working ? sh.shift_ticks : sh.day_ticks;
  $("#shift-clock").value = working ? sh.tick - (sh.shift_end - sh.shift_ticks) : sh.tick;
  if (sh.over) {
    const html = `<p class="note">Your shift is over: ${Object.values(sh.sold).reduce((a, b) => a + b, 0)} sold,
      ${sh.lost} customers left. The day is still running. Skip to its end.</p>`;
    if (html !== shiftHtml) {
      $("#shift-body").innerHTML = html;
      shiftHtml = html;
    }
    return;
  }
  if (!sh.shop) {
    const cafe = state.shops.find((s) => state.shift_shops.includes(s.id) && s.unlocked);
    const html = `
      <p class="note">Day ${state.day} is running, nobody is serving. The shift lasts ${sh.shift_ticks}
        seconds and starts when you press the button. Whoever does not work earns nothing.</p>
      <p class="error" id="shift-error"></p>
      <button class="btn wide" type="button" data-shift-start="${esc(cafe ? cafe.id : "")}"
        ${cafe ? "" : "disabled"}>Start shift in the ${esc(cafe ? cafe.name : "shop")}</button>`;
    if (html !== shiftHtml) {
      $("#shift-body").innerHTML = html;
      shiftHtml = html;
    }
    return;
  }
  const shop = state.shops.find((s) => s.id === sh.shop);
  const rows = shop.products.map((pid) => {
    const p = product(pid);
    const onCounter = sh.counter[pid] ?? 0;
    const waiting = sh.waiting[pid] ?? 0;
    const step = Math.min(5, p.stock, sh.counter_space);
    const fill = Math.min(p.stock, sh.counter_space);
    return `
      <div class="shift-row" style="--accent:${COLOR[pid]}">
        <span class="em" aria-hidden="true">${EMOJI[pid]}</span>
        <span class="nm">${esc(p.name)}<small>storeroom ${p.stock} · counter ${onCounter} · waiting ${waiting} · sold ${sh.sold[pid] ?? 0}</small></span>
        <button class="btn" type="button" data-refill="${esc(pid)}" data-qty="${step}" ${step > 0 ? "" : "disabled"}>+${step}</button>
        <button class="btn" type="button" data-refill="${esc(pid)}" data-qty="${fill}" ${fill > 0 ? "" : "disabled"}>Fill</button>
        <button class="btn" type="button" data-sell="${esc(pid)}" ${onCounter > 0 && waiting > 0 ? "" : "disabled"}>Sell ${fmt(p.price)}</button>
      </div>`;
  }).join("");
  const html = `
    <p class="note">Counter ${sh.counter_size - sh.counter_space} / ${sh.counter_size} · customers who left: ${sh.lost}</p>
    <p class="error" id="shift-error"></p>${rows}`;
  if (html !== shiftHtml) {
    $("#shift-body").innerHTML = html;
    shiftHtml = html;
  }
}

// One request, one tick: the server counts the day, never this clock.
function syncShiftTimer() {
  if (state.shift && !shiftTimer) shiftTimer = setInterval(shiftTick, 1000);
  if (!state.shift && shiftTimer) {
    clearInterval(shiftTimer);
    shiftTimer = null;
  }
}

async function shiftTick() {
  if (shiftBusy || !state.shift) return;
  shiftBusy = true;
  try {
    const data = await send("/api/shift/tick", {});
    if (!data) return;
    const before = state.day;
    state = data.state;
    renderAll();
    if (state.day !== before) {
      dayEnded();
      tellDashboard({ type: "action", after: data.state });
      showDaySummary(state.history[state.history.length - 1]);
    }
  } finally {
    shiftBusy = false;
  }
}

async function shiftAction(path, body) {
  if (shiftBusy) return;
  shiftBusy = true;
  try {
    const data = await send(path, body);
    if (!data) return;
    state = data.state;
    renderAll();
    if (data.error) {
      const el = $("#shift-error");
      if (el) el.textContent = data.error;
      return toast(data.error, "error");
    }
    tellDashboard({ type: "action", after: data.state });
    if (path.endsWith("/start") || path.endsWith("/open")) toast(data.message);
    if (path.endsWith("/skip")) {
      dayEnded();
      showDaySummary(state.history[state.history.length - 1]);
    }
  } finally {
    shiftBusy = false;
  }
}

function updateOrderTotal() {
  const out = $("#order-total");
  if (!out) return;
  const text = $("#order-form").quantity.value.trim();
  if (!/^\d+$/.test(text)) {
    out.className = "total";
    out.innerHTML = `<span>Enter a whole number</span><strong>—</strong>`;
    return;
  }
  const total = Number(text) * product(orderProduct).cost;
  const tooMuch = total > state.cash;
  out.className = `total ${tooMuch ? "too-much" : ""}`;
  out.innerHTML = `<span>${tooMuch ? "More than your cash" : "Total cost"}</span><strong>${fmt(total)}</strong>`;
}

function wirePanel() {
  const panel = $("#panel");
  panel.addEventListener("click", (e) => {
    if (e.target.closest("[data-close]")) return closePanel();
    if (e.target.closest("[data-dorm-open]")) {
      closePanel();
      return openDay();
    }
    const unlockBtn = e.target.closest("[data-unlock]");
    if (unlockBtn) return shopAction("/api/shop/unlock", { shop: unlockBtn.dataset.unlock });
    const upgradeBtn = e.target.closest("[data-upgrade-item]");
    if (upgradeBtn) {
      return shopAction("/api/shop/upgrade", {
        shop: upgradeBtn.dataset.upgradeShop,
        item: upgradeBtn.dataset.upgradeItem,
      });
    }
    const hireBtn = e.target.closest("[data-hire-shop]");
    if (hireBtn) {
      return shopAction("/api/staff/hire", {
        shop: hireBtn.dataset.hireShop, place: Number(hireBtn.dataset.hirePlace),
      });
    }
    const levelBtn = e.target.closest("[data-staff-upgrade]");
    if (levelBtn) return shopAction("/api/staff/upgrade", { employee_id: Number(levelBtn.dataset.staffUpgrade) });
    const fireBtn = e.target.closest("[data-staff-fire]");
    if (fireBtn) {
      const id = Number(fireBtn.dataset.staffFire);
      if (armedFire !== id) { // the level is lost, so ask once
        armedFire = id;
        return renderPanel();
      }
      armedFire = null;
      return shopAction("/api/staff/fire", { employee_id: id });
    }
    const startBtn = e.target.closest("[data-shift-start]");
    if (startBtn) return shiftAction("/api/shift/start", { shop: startBtn.dataset.shiftStart });
    const refillBtn = e.target.closest("[data-refill]");
    if (refillBtn) {
      return shiftAction("/api/shift/refill", {
        product: refillBtn.dataset.refill, quantity: Number(refillBtn.dataset.qty),
      });
    }
    const sellBtn = e.target.closest("[data-sell]");
    if (sellBtn) return shiftAction("/api/shift/sell", { product: sellBtn.dataset.sell });
    const pickBtn = e.target.closest("[data-pick]");
    if (pickBtn) {
      const typed = $("#order-form")?.quantity.value;
      orderProduct = pickBtn.dataset.pick;
      renderPanel();
      if (typed) $("#order-form").quantity.value = typed;
      return updateOrderTotal();
    }
    const input = $("#order-form")?.quantity;
    const step = e.target.closest("[data-step]");
    const set = e.target.closest("[data-set]");
    if (input && step) {
      const current = /^\d+$/.test(input.value.trim()) ? Number(input.value) : 0;
      input.value = Math.max(1, current + Number(step.dataset.step));
      updateOrderTotal();
    } else if (input && set) {
      input.value = set.dataset.set;
      updateOrderTotal();
    }
  });
  panel.addEventListener("input", (e) => {
    if (e.target.name === "quantity") return updateOrderTotal();
    const form = e.target.closest("[data-price-form]");
    if (!form) return;
    const p = product(form.dataset.priceForm);
    const value = Number(e.target.value.trim().replace(",", "."));
    if (!Number.isFinite(value) || value <= 0) return;
    const cents = Math.round(value * 100);
    form.querySelector("[data-demand]").innerHTML = cents === p.price
      ? `Sells up to <b>${p.demand}</b> a day`
      : `Sells up to <b>${previewDemand(cents, p.ref_price)}</b> a day · not saved yet`;
  });
  panel.addEventListener("submit", (e) => {
    e.preventDefault();
    if (e.target.id === "order-form") return order(orderProduct, e.target.quantity.value);
    const form = e.target.closest("[data-price-form]");
    if (form) savePrice(form);
  });
}

// ---- actions -------------------------------------------------------------------------

async function order(pid, quantityText) {
  if (animating) return;
  const data = await send("/api/buy", { product: pid, quantity: quantityText });
  if (!data) return;
  state = data.state;
  renderHud();
  if (data.error) {
    // nothing changed; keep the panel and what was typed, show why
    $("#order-error").textContent = data.error;
    return toast(data.error, "error");
  }
  closePanel();
  renderToolbar();
  tellDashboard({ type: "action", after: data.state });
  toast(data.message);
}

// Unlock a shop or buy from a window. The server decides; the panel stays open.
async function shopAction(path, body) {
  if (animating) return;
  const data = await send(path, body);
  if (!data) return;
  state = data.state;
  renderAll();
  if (data.error) {
    const el = $("#shops-error");
    if (el) el.textContent = data.error;
    return toast(data.error, "error");
  }
  tellDashboard({ type: "action", after: data.state });
  toast(data.message);
}

async function savePrice(form) {
  const pid = form.dataset.priceForm;
  const data = await send("/api/price", { product: pid, price: form.price.value });
  if (!data) return;
  state = data.state;
  renderHud();
  if (data.error) {
    form.querySelector("[data-error]").textContent = data.error;
    return toast(data.error, "error");
  }
  form.querySelector("[data-error]").textContent = "";
  const p = product(pid);
  form.price.value = (p.price / 100).toFixed(2);
  form.querySelector("[data-demand]").innerHTML = `Sells up to <b>${p.demand}</b> a day`;
  tellDashboard({ type: "action", after: data.state });
  toast(data.message);
}

// The numbers are final on the server already. They appear when the day has played.
async function playDay(after) {
  dayRunning = after.history[after.history.length - 1].day;
  animating = true;
  renderToolbar();
  try {
    await runClock(scene.clock, DAY_END, 3200);
  } finally {
    state = after;
    animating = false;
    dayRunning = null;
    fast = false;
    renderAll();
  }
}

// Open starts the day clock. The shift is started separately in the Shift panel while the
// day runs; while it runs this button lets the time pass without any sale.
async function openDay() {
  if (animating || state.finished) return;
  return shiftAction(state.shift ? "/api/shift/skip" : "/api/day/open", {});
}

// The dashboard did something: its own screen already shows the numbers.
function syncFromDashboard(msg) {
  enqueue(async () => {
    if (msg.kind === "open") {
      closePanel();
      hideOverlay();
      await playDay(msg.after);
      await runClock(DAY_END, MORNING, 900);
    } else {
      state = msg.after;
      if (msg.kind === "new-run") {
        closePanel();
        hideOverlay();
        scene.clock = MORNING;
        placePlayer(state.player);
      }
      renderAll();
    }
  });
}

// the desks in the world, by what their location says on the server
export function useLocation(action) {
  if (action === "stock") openPanel("order");
  if (action === "prices") openPanel("prices");
  if (action === "dorm") openPanel("dorm");
  if (action === "dashboard") tellDashboard({ type: "open-dashboard" });
}

// ---- end of day, end of run ----------------------------------------------------------

function showOverlay(html) {
  $("#overlay-card").innerHTML = html;
  $("#overlay").hidden = false;
  $("#overlay-card").querySelector("button, a")?.focus();
}

function hideOverlay() {
  $("#overlay").hidden = true;
}

function showDaySummary(result) {
  const gp = result.gross_profit;
  const rows = result.lines.map((line) => `
    <tr><td>${EMOJI[line.product]} ${esc(product(line.product).name)}</td><td>${line.sold}</td>
    <td>${fmt(line.revenue)}</td><td>${fmt(line.gross_profit)}</td></tr>`).join("");
  const sold = result.lines.reduce((sum, l) => sum + l.sold, 0);
  showOverlay(`
    <p class="eyebrow">Day ${result.day} closed</p>
    <p class="big ${gp > 0 ? "up" : gp < 0 ? "down" : ""}">${fmtSigned(gp)}</p>
    <p class="note">gross profit · cost of goods sold ${fmt(result.cogs)} · cash now ${fmt(result.cash_after)}</p>
    ${result.wages || result.wages_unpaid?.length ? `<p class="note">wages paid ${fmt(result.wages)} · result after wages ${fmtSigned(result.net)}${
      result.wages_unpaid.length ? ` · ${result.wages_unpaid.length} employee(s) stopped working: no money for the wage` : ""}</p>` : ""}
    <table>
      <thead><tr><th>Product</th><th>Sold</th><th>Revenue</th><th>Profit</th></tr></thead>
      <tbody>${rows}</tbody>
      <tfoot><tr><td>Total</td><td>${sold}</td><td>${fmt(result.revenue)}</td><td>${fmt(gp)}</td></tr></tfoot>
    </table>
    <div class="actions">
      <button class="btn" type="button" data-next>${state.finished ? "See the final result" : `Start day ${state.day}`}</button>
    </div>`);
}

function showFinal() {
  const gain = state.overall_gain;
  showOverlay(`
    <p class="eyebrow">Run complete · ${state.history.length} days</p>
    <p class="big ${gain > 0 ? "up" : gain < 0 ? "down" : ""}">${fmtSigned(gain)}</p>
    <p class="note">overall result = final cash ${fmt(state.cash)} + stock at cost ${fmt(state.stock_value)} − ${fmt(state.starting_cash)} start</p>
    <div class="actions">
      <button class="btn" type="button" data-new-run>Start a new run</button>
      <button class="btn ghost" type="button" data-dashboard>Dashboard</button>
    </div>
    <div class="actions"><button class="btn ghost" type="button" data-dismiss>Look around the campus</button></div>`);
}

function askNewRun() {
  $("#dialog-text").textContent = state.finished
    ? `Your completed run (${fmtSigned(state.overall_gain)}) is replaced by a fresh one: day 1, ${fmt(state.starting_cash)}, no stock. This cannot be undone.`
    : `This ends your run on day ${state.day} with ${fmt(state.cash)} cash. You start again on day 1 with ${fmt(state.starting_cash)} and no stock. This cannot be undone.`;
  const dialog = $("#new-run-dialog");
  dialog.returnValue = "";
  dialog.showModal();
}

function wireOverlay() {
  $("#overlay").addEventListener("click", (e) => {
    if (e.target.closest("[data-next]")) {
      hideOverlay();
      runClock(scene.clock, MORNING, 500);
      if (state.finished) showFinal();
    } else if (e.target.closest("[data-dismiss]")) {
      hideOverlay();
    } else if (e.target.closest("[data-dashboard]")) {
      tellDashboard({ type: "open-dashboard" });
    } else if (e.target.closest("[data-new-run]")) {
      askNewRun();
    }
  });
  $("#new-run-dialog").addEventListener("close", async (e) => {
    if (e.target.returnValue !== "confirm") return;
    const data = await send("/api/new-run", { confirm: true });
    if (!data) return;
    state = data.state;
    if (data.error) return toast(data.error, "error");
    closePanel();
    hideOverlay();
    scene.clock = MORNING;
    placePlayer(state.player);
    renderAll();
    tellDashboard({ type: "action", after: data.state });
    toast(data.message);
  });
}

// ---- start ---------------------------------------------------------------------------

function setMode(mode) {
  scene.preview = mode === "preview";
  document.body.classList.toggle("preview", scene.preview);
  if (scene.preview) closePanel();
}

// while a card or dialog is open, the figure stays where it is
export function inputBlocked() {
  return !$("#overlay").hidden || $("#new-run-dialog").open;
}

export function initUi(firstState, actions) {
  state = firstState;
  placePlayer = actions.placePlayer;
  wirePanel();
  wireEditor();
  wireOverlay();
  $("#btn-editor").addEventListener("click", () => openPanel("editor"));
  $("#btn-order").addEventListener("click", () => openPanel("order"));
  $("#btn-prices").addEventListener("click", () => openPanel("prices"));
  $("#btn-shops").addEventListener("click", () => openPanel("shops"));
  $("#btn-shift").addEventListener("click", () => openPanel("shift"));
  $("#btn-open").addEventListener("click", openDay);
  $("#btn-fast").addEventListener("click", () => { fast = true; });
  $("#btn-dashboard").addEventListener("click", () => tellDashboard({ type: "open-dashboard" }));
  $("#btn-new-run").addEventListener("click", askNewRun);
  window.addEventListener("message", (e) => {
    if (e.origin !== location.origin || e.source !== window.parent) return;
    const msg = e.data || {};
    if (msg.type === "mode") setMode(msg.mode);
    if (msg.type === "action") syncFromDashboard(msg);
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closePanel();
  });
  setMode(embedded ? "preview" : "main");
  renderAll();
  if (state.finished) showFinal();
  tellDashboard({ type: "ready" });
}
