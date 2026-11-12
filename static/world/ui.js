// Head-up display, stock and price panels, end-of-day cards. The screen only shows
// what the server answers and forwards clicks: every rule is decided in logic.py.
// $, esc, fmt, fmtSigned, toast and EMOJI come from common.js.

import { demoDialogOpen, renderDemo, tickMs, wireDemo } from "./demo.js";
import { inReach } from "./locations.js";
import { createSerial } from "./serial.js";
import { DAWN, DAY_END, MORNING, reducedMotion, scene, server, world } from "./scene.js";

const COLOR = ACCENT; // from common.js: one colour per product

// The world runs embedded in the dashboard page (views.js): small or full screen.
const embedded = new URLSearchParams(location.search).has("embed");

let state = null;
let panelMode = null;
let armedFire = null; // the employee whose Dismiss was clicked once (the panel is redrawn every tick)
let orderProduct = "coffee";
let placePlayer = () => {};
let goHome = () => false;
let jumpHome = () => false;
let wakeAt = () => {};
// The day cycle (spec day-cycle): after a day closed it is evening until the player has slept.
// Kept only here, in the browser: it decides no rule, and after a reload it is simply morning.
let evening = false;
let fading = false;

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

const openWhy = new Set(); // products whose "why" lines are open, kept over re-renders

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
  if (reducedMotion || ms <= 0) {
    update(1);
    return Promise.resolve();
  }
  return new Promise((resolve) => {
    const start = performance.now();
    const frame = (now) => {
      const k = Math.max(0, Math.min((now - start) / ms, 1));
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
  if (!sh) return;
  const target = MORNING + (DAY_END - MORNING) * Math.min(sh.tick / sh.day_ticks, 1);
  runClock(scene.clock, target, Math.abs(target - scene.clock) > 60 ? 0 : tickMs(state));
}

// The day closed on the server: the clock goes on to the evening, not with a jump.
function dayEnded() {
  runClock(scene.clock, DAY_END, 900);
}

// The day closed (clock ran out, skipped, or ended at the bed): no summary on the map; it waits in
// the Dorm. Standing at the bed already (End the day), the player goes straight to bed.
function startEvening() {
  dayEnded();
  evening = true; // an open panel stays open (a typed order is not lost); the hint shows beside it
  renderAll();
  const bed = world.locations?.bed;
  if (bed && inReach(bed)) goToBed();
}

function walkHome() {
  if (!evening || scene.sleeping) return;
  closePanel();
  if (!goHome()) toast("No way home from here. Walk to the Dorm yourself.", "error");
}

// Skip the walk: black for a moment, then the player lies in the bed (the report opens there).
async function skipWalk() {
  if (!evening || scene.sleeping || fading) return;
  closePanel();
  fading = true;
  renderEvening();
  $("#night-fade").classList.add("on");
  try {
    await pause(450);
    if (!jumpHome()) toast("The Dorm could not be found. Walk there yourself.", "error");
  } finally {
    fading = false;
    $("#night-fade").classList.remove("on");
    renderEvening();
  }
}

function renderEvening() {
  const hint = $("#evening-hint");
  const hidden = !evening || scene.sleeping || fading || !$("#overlay").hidden || scene.preview;
  if (hint.hidden !== hidden) hint.hidden = hidden;
  const last = state.history[state.history.length - 1];
  const text = last ? `Day ${last.day} is over. Time to go home.` : "Time to go home.";
  const el = $("#evening-text");
  if (el.textContent !== text) el.textContent = text;
}

// At the bed in the evening: lie down, then the day summary and the evening report.
function goToBed() {
  closePanel();
  scene.sleeping = true;
  scene.walking = false;
  renderEvening();
  showDaySummary(state.history[state.history.length - 1]);
}

const pause = (ms) => new Promise((resolve) => setTimeout(resolve, reducedMotion ? 0 : ms));

// Sleep: the screen goes black, then the dark night with the player asleep, then the sun rises
// (the clock runs from DAWN, 05:00, to the morning), and the player stands up beside the bed.
async function sleep() {
  hideOverlay();
  evening = false;
  fading = true;
  $("#night-fade").classList.add("on");
  try {
    await pause(800);
    clockRun++; // stops a clock still running to the evening
    scene.clock = DAWN; // the dark night before the morning
    renderAll();
    const fade = $("#night-fade");
    fade.classList.add("night"); // from black to a deep night, the player asleep (Zzz)
    fade.classList.remove("on");
    await pause(1900);
    fade.classList.add("sunrise"); // the dark lifts as slowly as the sun rises
    fade.classList.remove("night");
    await runClock(DAWN, MORNING, 3600); // the sunrise
    scene.sleeping = false;
    const wake = world.dorm?.wake;
    if (wake) wakeAt(wake);
  } finally {
    clockRun++;
    scene.clock = MORNING;
    scene.sleeping = false;
    fading = false;
    $("#night-fade").classList.remove("on", "night", "sunrise");
    renderAll();
  }
  if (state.finished) showFinal();
  else showMorning();
}

// The morning card: the day, the forecast with the tips, the stock and what to do. Everything in
// it comes from the server's state; the card decides nothing.
function showMorning() {
  const stock = state.products.map((p) => `${EMOJI[p.id] ?? ""} ${esc(p.name)} ${esc(p.stock)}`).join(" · ");
  const crews = state.staff?.employees?.length ?? 0;
  showOverlay(`
    <p class="eyebrow">Good morning · Day ${esc(state.day)} of ${esc(state.last_day)}</p>
    <p class="big">☀ ${esc(state.day)}</p>
    <p class="note">Cash ${fmt(state.cash)} · in stock: ${stock}</p>
    ${eveningReport()}
    <ol class="todo">
      <li>Buy stock with the forecast in mind (<b>Stock</b>).</li>
      <li>Check your prices (<b>Prices</b>).</li>
      <li>Open the day, then start your shift (<b>Shift</b>)${crews ? "" : ": without a shift or staff nothing is sold"}.</li>
    </ol>
    <div class="actions"><button class="btn" type="button" data-dismiss>Let's go</button></div>`);
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
  // before the day is opened only the forecast is shown; once open, the real weather and
  // the forecast for tomorrow (none once the last day is open)
  const open = dayIsOpen(state);
  $("#stat-weather-label").textContent = open || state.finished ? "WEATHER" : "FORECAST";
  if (open) showWeather($("#stat-weather"), state.weather);
  else showOutlook($("#stat-weather"), state.outlook);
  const eventLine = open ? eventText(state.event) : "";
  $("#stat-event").textContent = eventLine;
  $("#stat-event").closest(".stat").hidden = !eventLine;
  showOutlook($("#stat-outlook"), open ? state.outlook : null);
  $("#stat-outlook").closest(".stat").hidden = !(open && state.outlook);
  $("#stat-cash").textContent = fmt(state.cash);
  $("#stat-stock").textContent = fmt(state.stock_value);
  const gain = $("#stat-gain");
  gain.textContent = fmtSigned(state.overall_gain);
  gain.className = state.overall_gain > 0 ? "up" : state.overall_gain < 0 ? "down" : "";
  $("#hud-stock").innerHTML = `${state.products.map((p) => `
    <div class="stock-row" style="--accent:${COLOR[p.id]}">
      <span class="em" aria-hidden="true">${EMOJI[p.id]}</span>
      <span class="nm">${esc(p.name)}<small>${p.breakdown ? customersText(p.customers) : "trading is closed"}</small></span>
      <span class="units">${p.stock}</span>
    </div>`).join("")}`;
}

function renderToolbar() {
  const locked = state.finished;
  $("#btn-order").disabled = locked;
  $("#btn-prices").disabled = locked || !!state.shift;
  $("#btn-shops").disabled = locked;
  $("#btn-shift").disabled = locked;
  $("#btn-shift").querySelector(".txt").textContent = "Shift";
  $("#btn-open").disabled = locked;
  $("#btn-editor").hidden = !state.editor;
  $("#open-label").textContent = evening ? "Go home"
    : state.finished ? "Run complete"
    : dayButtonLabel();
  if (evening) $("#btn-open").disabled = scene.sleeping || fading;
  const empty = state.products.every((p) => p.stock === 0);
  $("#btn-order").classList.toggle("hint", empty && !locked);
}

function renderAll() {
  if (state.shift) evening = false; // a day is open again (also when opened elsewhere)
  server.staff = state.staff; // the figures in the Cafe are drawn from this (rooms.js)
  server.shift = state.shift;
  server.guests = state.guests ?? null; // the guests on the map are drawn from this (guests.js)
  server.guestsAt = performance.now();
  const open = state.shops.find((sh) => sh.id === state.shift?.shop);
  server.storeroom = open ? state.products.filter((p) => open.products.includes(p.id)).reduce((n, p) => n + p.stock, 0) : 0;
  renderHud();
  renderToolbar();
  renderEvening();
  if (panelMode) renderPanel();
  syncShiftTimer();
  followDay();
  noticeBadges();
  placeBadge();
  renderDemo(state);
}

// ---- panels --------------------------------------------------------------------------

function openPanel(mode) {
  if (state.finished && mode !== "editor") return;
  panelMode = mode;
  panelHtml = "";
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
  // the real weather once the day is open, before that only the forecast
  const o = state.outlook;
  const weather = state.weather ? `${esc(state.weather.name)}, ${esc(state.weather.temperature)} °C`
    : o ? `Forecast: ${esc(o.name)}, ${esc(o.temp_low)}–${esc(o.temp_high)} °C` : "—";
  const label = state.finished ? "The run is complete" : state.shift ? "End the day" : dayButtonLabel();
  setPanelHtml(body, `
    <p class="note">A quiet room with a view of the sea. The day starts and ends here.</p>
    <dl class="dorm-facts">
      <div><dt>Day</dt><dd>${state.finished ? "Done" : `${esc(state.day)} / ${esc(state.last_day)}`}</dd></div>
      <div><dt>Cash</dt><dd>${fmt(state.cash)}</dd></div>
      <div><dt>Weather</dt><dd>${weather}</dd></div>
      ${state.event ? `<div><dt>Event</dt><dd>${esc(eventText(state.event))}</dd></div>` : ""}
    </dl>
    <button type="button" class="btn" data-dorm-open ${state.finished ? "disabled" : ""}>${esc(label)}</button>`);
}

// A panel is redrawn only when its content changed (it is asked again every second while a day
// runs). When it did change, what the player typed and the focus stay (spec calm-panels).
let panelHtml = "";

function fieldKey(el) {
  const form = el.closest("form, [data-price-form]");
  return `${form ? form.id || form.dataset.priceForm || form.dataset.editor || "form" : ""}:${el.name}`;
}

// A field counts as typed when the player changed it (the "input" event, or a step or chip on it),
// not when the program set it: a saved price is the server's, not a typed one.
const markTyped = (el) => { el.dataset.typed = "1"; };

// a button has no name: it is found again by its first data- attribute (data-sell="coffee")
function buttonSelector(el) {
  const attr = [...el.attributes].find((a) => a.name.startsWith("data-") && a.name !== "data-typed");
  return attr ? `[${attr.name}="${CSS.escape(attr.value)}"]` : null;
}

function setPanelHtml(body, html) {
  if (html === panelHtml) return;
  panelHtml = html;
  const typed = new Map();
  for (const el of body.querySelectorAll("input[name], select[name]")) {
    if (el.dataset.typed) typed.set(fieldKey(el), el.value);
  }
  const focus = document.activeElement;
  const active = body.contains(focus)
    ? (focus.name ? { key: fieldKey(focus), start: focus.selectionStart, end: focus.selectionEnd } : { selector: buttonSelector(focus) })
    : null;
  body.innerHTML = html;
  for (const el of body.querySelectorAll("input[name], select[name]")) {
    const key = fieldKey(el);
    if (typed.has(key)) {
      el.value = typed.get(key);
      markTyped(el);
      // the redraw dropped the live preview: ask for it again
      if (el.name === "price") el.dispatchEvent(new Event("input", { bubbles: true }));
    }
    if (active?.key === key) {
      el.focus();
      try { el.setSelectionRange(active.start, active.end); } catch { /* a field without a cursor */ }
    }
  }
  if (active?.selector) body.querySelector(active.selector)?.focus();
}

function renderPanel() {
  const body = $("#panel-body");
  if (panelMode === "order") {
    $("#panel-title").textContent = "Order stock";
    const p = product(orderProduct);
    const max = Math.floor(state.cash / p.cost);
    setPanelHtml(body, `
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
      </form>`);
    updateOrderTotal();
  } else if (panelMode === "editor") {
    $("#panel-title").textContent = "Editor";
    renderEditorPanel(body);
  } else if (panelMode === "shops") {
    $("#panel-title").textContent = "Shops";
    setPanelHtml(body, `
      <p class="note">Unlock shops and buy upgrades with cash. Every purchase raises the shop's level by 1.</p>
      <p class="error" id="shops-error"></p>
      ${state.shops.map((s) => `
        <section class="shop-card">
          <h3>${esc(s.name)} <small>${s.unlocked ? `Level ${s.level}` : "Locked"}</small></h3>
          ${s.unlocked ? `
            <p class="note">Sells ${s.products.map((id) => esc(product(id)?.name ?? id)).join(", ")} ·
              ${s.staff_places} employee place${s.staff_places === 1 ? "" : "s"} ·
              storeroom ${s.storage}, counter ${s.counter}</p>
            ${s.hint ? `<p class="note hint">${esc(s.hint)}</p>` : ""}
            ${staffBlock(s)}
            ${s.offers.map((o) => `
              <div class="shop-offer">
                <span class="nm">${esc(o.name)}</span>
                ${o.bought
                  ? `<span class="owned">Owned</span>`
                  : `<button class="btn" type="button" data-upgrade-shop="${esc(s.id)}" data-upgrade-item="${esc(o.id)}"
                      ${!o.affordable || !o.available ? "disabled" : ""}
                      ${o.available ? "" : 'title="Buy the first employee place first"'}>${fmt(o.price)}</button>`}
              </div>
              ${o.warning ? `<p class="note warning" role="status">⚠ ${esc(o.warning)}</p>` : ""}`).join("")}`
          : `<div class="shop-offer">
              <span class="nm">Start with ${esc(s.start_product_name)}</span>
              <button class="btn" type="button" data-unlock="${esc(s.id)}"
                ${s.affordable ? "" : "disabled"}>Unlock ${fmt(s.unlock_price)}</button>
            </div>
            ${s.hint ? `<p class="note hint">${esc(s.hint)}</p>` : ""}
            ${s.unlock_warning ? `<p class="note warning" role="status">⚠ ${esc(s.unlock_warning)}</p>` : ""}`}
        </section>`).join("")}`);
  } else if (panelMode === "dorm") {
    renderDormPanel(body);
  } else if (panelMode === "shift") {
    renderShiftPanel(body);
  } else if (panelMode === "prices") {
    $("#panel-title").textContent = "Prices";
    setPanelHtml(body, `
      <p class="note">Students and visitors react to the price in different ways, and today's weather moves them. Open "Why this number?" to see how a price becomes customers.</p>
      ${state.products.map((p) => `
        <form class="price-row" data-price-form="${esc(p.id)}">
          <span class="em" aria-hidden="true">${EMOJI[p.id]}</span>
          <span class="nm">${esc(p.name)}<small>Ref. ${fmt(p.ref_price)} · cost ${fmt(p.cost)}</small></span>
          <label class="euro"><span>€</span><input name="price" inputmode="decimal" autocomplete="off"
            value="${(p.price / 100).toFixed(2)}" aria-label="${esc(p.name)} price in euro"></label>
          <button class="btn" type="submit">Save</button>
          <span class="demand" data-demand>${p.breakdown ? customersText(p.customers) : "Trading is closed"}</span>
          ${p.breakdown ? `<details class="why" data-why="${esc(p.id)}" ${openWhy.has(p.id) ? "open" : ""}>
            <summary>Why this number?</summary>
            <div class="why-body">${breakdownHtml(p.breakdown, state.segments)}</div>
          </details>` : ""}
          <p class="error" data-error></p>
        </form>`).join("")}`);
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
  const key = JSON.stringify([state.day, state.cash, state.finished, info.weather_override, info.event_override, state.shops.map((s) => s.level), !!state.shift]);
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
    <section class="editor-block"><h3>Weather and event</h3>
      <form class="editor-row" data-editor="weather">
        <select name="weather" aria-label="Weather">
          <option value="">Seed's forecast</option>
          ${info.weather.map((w) => `<option value="${esc(w.id)}" ${info.weather_override === w.id ? "selected" : ""}>${esc(w.name)}</option>`).join("")}
        </select>
        <select name="event" aria-label="Event">
          <option value="none">No event</option>
          ${info.events.map((ev) => `<option value="${esc(ev.id)}" ${info.event_override === ev.id ? "selected" : ""}>${esc(ev.name)}</option>`).join("")}
        </select>
        <button class="btn" type="submit" value="fix">Fix</button>
        <button class="btn ghost" type="submit" value="clear">Seed's</button>
      </form>
      <p class="note">Stays fixed for today and the days after, until set back to the seed's. A fixed weather without an event means no event.</p></section>
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
    <section class="editor-block"><h3>Staff</h3>
      <div class="editor-row">
        <button class="btn ghost" type="button" data-editor-staff="fill" ${busy}>Fill empty places</button>
        <button class="btn ghost" type="button" data-editor-staff="top" ${busy}>All on top level</button>
        <button class="btn ghost" type="button" data-editor-staff="none" ${busy}>Dismiss all</button></div>
      <p class="note">Fill keeps the employees you have and puts a level 1 employee on every free bought place. Top level and Dismiss all change everybody.</p></section>
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
  if (moved) {
    evening = false; // a reset or a moved day starts in the morning
    scene.sleeping = false;
    placePlayer(state.player);
  }
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
    if (kind === "weather") {
      if (e.submitter?.value === "clear") return editorAction("/api/editor/weather", { weather: null, event: null });
      return editorAction("/api/editor/weather", { weather: f.weather.value || null, event: f.event.value });
    }
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
    const staffBtn = e.target.closest("[data-editor-staff]");
    if (staffBtn) {
      // the server checks places and levels; an employee who is there stays the same person
      const mode = staffBtn.dataset.editorStaff;
      const mine = state.staff.employees;
      const employees = mode === "none" ? [] : state.staff.places.filter((p) => p.bought).map((p) => {
        const who = mine.find((x) => x.id === p.employee);
        if (mode === "top") return { shop: p.shop, place: p.place, level: state.staff.max_level, working: who ? who.working : true };
        return who ? { shop: p.shop, place: p.place, level: who.level, working: who.working } : { shop: p.shop, place: p.place };
      });
      return editorAction("/api/editor/state", { patch: { employees } });
    }
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
// Refill, sell and tick go one after the other, and so does every request that replaces the run
// (a new run, a demo scenario, the end of the demo; spec stale-tick): a tick never overtakes it.
// Once such a request worked, requests.renew() drops the ticks and clicks queued for the old run.
const requests = createSerial();

// Today's guests (spec guests): per running shop how many come, where guests went instead, and
// what they think most. All of it from the server's answer; written only when it changes.
let guestsHtml = "";
function renderGuests() {
  const data = state.guests;
  const name = (sid) => state.shops.find((s) => s.id === sid)?.name ?? sid;
  const moves = (counts, word) => Object.entries(counts)
    .map(([sid, n]) => `${n} ${word} ${esc(name(sid))}`).join(" · ");
  const rows = (data?.shops ?? []).map((s) => {
    const came = moves(s.came, "from the");
    const left = moves(s.left, "went to the");
    const top = s.thoughts[0];
    return `
      <li><b>${esc(s.name)}</b>: ${s.total} guests${came ? ` · ${came}` : ""}${left ? ` · ${left}` : ""}
        ${top ? `<small>Most think: “${esc(top.text)}” (${top.count})</small>` : ""}</li>`;
  });
  for (const sid of data?.waiting_shops ?? []) {
    rows.push(`<li><b>${esc(name(sid))}</b>: its guests come when your shift starts</li>`);
  }
  const html = rows.length ? `<h3 class="guests-title">Today's guests</h3><ul class="guest-list">${rows.join("")}</ul>` : "";
  if (html !== guestsHtml) {
    $("#shift-guests").innerHTML = html;
    guestsHtml = html;
  }
}

function renderShiftPanel(body) {
  $("#panel-title").textContent = "Shift";
  const sh = state.shift;
  if (!sh) {
    shiftHtml = "";
    body.innerHTML = `<p class="note">Open the day first. Then start your shift here while the day runs.</p>`;
    return;
  }
  if (!$("#shift-clock")) {
    body.innerHTML = `<progress id="shift-clock"></progress><div id="shift-body"></div><div id="shift-guests"></div>`;
    shiftHtml = "";
    guestsHtml = "";
  }
  renderGuests();
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

// One request, one tick: the server counts the day, never this clock. A demo scenario may ask for
// a faster pace (demo.js, tickMs); the server counts the ticks the same way.
let shiftTimerMs = 0;
function syncShiftTimer() {
  const ms = tickMs(state);
  if (shiftTimer && (!state.shift || ms !== shiftTimerMs)) {
    clearInterval(shiftTimer);
    shiftTimer = null;
  }
  if (state.shift && !shiftTimer) {
    shiftTimer = setInterval(shiftTick, ms);
    shiftTimerMs = ms;
  }
}

// the tick is skipped while the last one still waits; a click waits for the request before it
function shiftTick() {
  if (!state.shift) return;
  return requests.once("tick", async (stale) => {
    if (!state.shift) return;
    const data = await send("/api/shift/tick", {});
    if (!data || stale()) return; // the dashboard replaced the run meanwhile: its state counts
    const before = state.day;
    state = data.state;
    renderAll();
    if (state.day !== before) {
      tellDashboard({ type: "action", after: data.state });
      startEvening();
    }
  }).catch((err) => console.error(err));
}

function shiftAction(path, body) {
  // a click waits for the request before it; the same click again while it still waits is one click
  return requests.once(`${path}:${JSON.stringify(body)}`, async (stale) => {
    const data = await send(path, body);
    if (!data || stale()) return;
    state = data.state;
    renderAll();
    if (data.error) {
      const el = $("#shift-error");
      if (el) el.textContent = data.error;
      return toast(data.error, "error");
    }
    tellDashboard({ type: "action", after: data.state });
    if (path.endsWith("/start") || path.endsWith("/open")) toast(data.message);
    if (path.endsWith("/skip")) startEvening();
  }).catch((err) => console.error(err));
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
      if (typed) { $("#order-form").quantity.value = typed; markTyped($("#order-form").quantity); }
      return updateOrderTotal();
    }
    const input = $("#order-form")?.quantity;
    const step = e.target.closest("[data-step]");
    const set = e.target.closest("[data-set]");
    if (input && step) {
      const current = /^\d+$/.test(input.value.trim()) ? Number(input.value) : 0;
      input.value = Math.max(1, current + Number(step.dataset.step));
      markTyped(input);
      updateOrderTotal();
    } else if (input && set) {
      input.value = set.dataset.set;
      markTyped(input);
      updateOrderTotal();
    }
  });
  panel.addEventListener("input", (e) => {
    markTyped(e.target);
    if (e.target.name === "quantity") return updateOrderTotal();
    const form = e.target.closest("[data-price-form]");
    if (!form) return;
    const p = product(form.dataset.priceForm);
    const text = e.target.value.trim().replace(",", ".");
    const value = Number(text);
    if (!/^(?:\d+\.?\d*|\.\d+)$/.test(text) || !Number.isFinite(value) || value <= 0 || state.finished) return cancelPricePreview(form);
    const unsaved = Math.round(value * 100) !== p.price;
    schedulePricePreview(form, p.id, text, (b) => {
      form.querySelector("[data-demand]").innerHTML =
        `${customersText(b.customers)}${unsaved ? " · not saved yet" : ""}`;
      const body = form.querySelector(".why-body");
      if (body) body.innerHTML = breakdownHtml(b, state.segments);
    });
  });
  // remember which "why" lines are open (the toggle event does not bubble, so capture it)
  panel.addEventListener("toggle", (e) => {
    const why = e.target.closest?.(".why");
    if (!why) return;
    if (why.open) openWhy.add(why.dataset.why);
    else openWhy.delete(why.dataset.why);
  }, true);
  panel.addEventListener("submit", (e) => {
    e.preventDefault();
    if (e.target.id === "order-form") return order(orderProduct, e.target.quantity.value);
    const form = e.target.closest("[data-price-form]");
    if (form) savePrice(form);
  });
}

// ---- actions -------------------------------------------------------------------------

async function order(pid, quantityText) {
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
  cancelPricePreview(form); // a preview still waiting must not overwrite the saved state
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
  delete form.price.dataset.typed; // the saved price is the server's, not a typed one
  form.querySelector("[data-demand]").innerHTML = customersText(p.customers);
  const why = form.querySelector(".why-body");
  if (why && p.breakdown) why.innerHTML = breakdownHtml(p.breakdown, state.segments);
  tellDashboard({ type: "action", after: data.state });
  toast(data.message);
}

// Open starts the day clock. The shift is started separately in the Shift panel while the
// day runs; while it runs this button lets the time pass without any sale.
async function openDay() {
  if (evening) return walkHome();
  if (state.finished) return;
  if (state.shift) {
    const warning = endDayWarning();
    if (warning) return askEndDay(warning);
  }
  return shiftAction(state.shift ? "/api/shift/skip" : "/api/day/open", {});
}

// Ending a day early lets the rest pass without the player serving (skip_shift on the server).
// Ask first when that costs sales: nobody works today, or the player's own shift still runs.
// Only a question in the browser; the server decides the skip as before.
function endDayWarning() {
  const sh = state.shift;
  if (!sh) return "";
  if (!sh.shop && !(sh.crews?.length)) {
    return "Nobody works today: no shift has started and no staff are on duty. If you end the day now, nothing is sold.";
  }
  if (sh.shop && !sh.over && !sh.staffed) { // a staffed shift runs on without the player
    const name = state.shops.find((shop) => shop.id === sh.shop)?.name ?? "shop";
    return `Your shift in the ${name} is still running. If you end the day now, the customers still to come are lost.`;
  }
  return "";
}

function askEndDay(text) {
  $("#end-day-text").textContent = text;
  const dialog = $("#end-day-dialog");
  dialog.returnValue = "";
  dialog.showModal();
}

function endDayConfirmed() {
  if (!state.shift) return;
  return shiftAction("/api/shift/skip", {});
}

// The dashboard did something: its own screen already shows the numbers.
function syncFromDashboard(msg) {
  if (msg.kind === "new-run") requests.renew(); // the dashboard replaced the run: no tick of the old one after it
  enqueue(async () => {
    state = msg.after;
    if (msg.kind === "new-run") {
      closePanel();
      hideOverlay();
      evening = false;
      scene.sleeping = false;
      scene.clock = MORNING;
      placePlayer(state.player);
    }
    renderAll();
  });
}

// the desks in the world, by what their location says on the server
export function useLocation(action) {
  if (action === "stock") openPanel("order");
  if (action === "prices") openPanel("prices");
  if (action === "dorm") {
    if (evening) return goToBed();
    openPanel("dorm");
  }
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
    <tr><td>${EMOJI[line.product] ?? ""} ${esc(product(line.product)?.name ?? line.product)}</td><td>${line.sold}</td>
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
    </table>${newBadges(result)}${eveningReport()}
    <div class="actions">
      <button class="btn" type="button" data-next>${state.finished ? "Sleep · see the final result" : "Sleep"}</button>
    </div>`);
}

// Every badge earned on this day (specs/badges.md), also those that popped up during it, as
// medals. The list comes from the server (result.badges).
function newBadges(result) {
  const ids = result.badges || [];
  if (!ids.length) return "";
  const badges = ids.map((id) => (state.badges || []).find((b) => b.id === id)).filter(Boolean);
  return `
    <div class="evening-report day-badges">
      <p class="eyebrow">Badges today · ${badges.length}</p>
      ${medalGridHtml(badges)}
    </div>`;
}

// The forecast for the next day and one tip per open shop (outlook). Shown in the day
// summary and on the morning card; the tips and the forecast come from the server.
function eveningReport() {
  const o = state.outlook;
  if (!o || state.finished) return "";
  const tips = o.tips.map((t) => `
    <li><b>${esc(t.name)}:</b> ${esc(TIP_TEXT[t.advice]?.(t.percent) ?? "")}</li>`).join("");
  // with a fixed weather (demo override) the server sends miss_percent 0: no warning then
  const miss = o.miss_percent > 0
    ? `<p class="note">Forecasts are wrong about ${esc(o.miss_percent)} % of the time.</p>` : "";
  return `
    <div class="evening-report">
      <p class="eyebrow">Forecast for day ${esc(o.day)}</p>
      <p class="forecast"><span class="icon" aria-hidden="true">${weatherIconMarkup(o.id, 22)}</span>
        <b>${esc(o.name)}</b>, ${esc(o.temp_low)}–${esc(o.temp_high)} °C</p>
      <ul class="tips">${tips}</ul>${miss}
    </div>`;
}

function showFinal() {
  const gain = state.overall_gain;
  showOverlay(`
    <p class="eyebrow">Run complete · ${state.history.length} days</p>
    <p class="big ${gain > 0 ? "up" : gain < 0 ? "down" : ""}">${fmtSigned(gain)}</p>
    <p class="note">overall result = final cash ${fmt(state.cash)} + stock at cost ${fmt(state.stock_value)} − ${fmt(state.starting_cash)} start</p>
    <div class="evening-report final-badges">
      <p class="eyebrow">Your badges · ${earnedBadges().length} / ${(state.badges || []).length}</p>
      ${medalGridHtml(state.badges)}
    </div>
    <div class="actions">
      <button class="btn" type="button" data-new-run>Start a new run</button>
      <button class="btn ghost" type="button" data-dashboard>Dashboard</button>
    </div>
    <div class="actions"><button class="btn ghost" type="button" data-dismiss>Look around the campus</button></div>`);
}

// ---- badges (specs/badges.md) ---------------------------------------------------------------
// The server gives a badge the moment it is reached. Every badge that shows up in the state and
// was not earned before appears as a card at the top left, one after the other, and leaves by
// itself: the game keeps running, nothing has to be clicked. The page decides nothing.
const BADGE_SHOW_MS = 4500;
const BADGE_LEAVE_MS = 260;
const SPARK_COLORS = ["#f2bf2e", "#e86f55", "#2a78d6", "#1baf7a", "#d9487b", "#bce65f"];
const SPARKS = 12;
let seenBadges = null; // the ids earned when the state was last looked at
const badgeQueue = [];
let badgeTimer = null;
let badgeShowing = false;
let badgeOnScreen = null; // the id of the badge whose card is shown now

const earnedBadges = () => (state.badges || []).filter((b) => b.day !== null);

function noticeBadges() {
  const earned = earnedBadges();
  const ids = new Set(earned.map((b) => b.id));
  if (seenBadges) {
    for (const b of earned) if (!seenBadges.has(b.id) && !badgeQueue.includes(b.id)) badgeQueue.push(b.id);
  }
  seenBadges = ids;
  // a badge that is gone again (a new run, an earlier day set in the editor) is not shown,
  // and its card goes at once if it is on screen
  for (let i = badgeQueue.length - 1; i >= 0; i--) if (!ids.has(badgeQueue[i])) badgeQueue.splice(i, 1);
  if (badgeOnScreen && !ids.has(badgeOnScreen)) endBadges();
  // in the small preview on the dashboard the badge waits until the campus is shown again
  if (!scene.preview && !badgeShowing && badgeQueue.length) showNextBadge();
}

// Sparks fly out of the medal: direction and colour from the piece's number, no randomness.
function sparksHtml() {
  let pieces = "";
  for (let i = 0; i < SPARKS; i++) {
    const angle = (i / SPARKS) * Math.PI * 2;
    const reach = 30 + (i % 3) * 7;
    const style = [
      `--tx:${Math.round(Math.cos(angle) * reach)}px`,
      `--ty:${Math.round(Math.sin(angle) * reach)}px`,
      `--r:${(i * 67) % 360}deg`,
      `--delay:${0.1 + (i % 4) * 0.04}s`,
      `--c:${SPARK_COLORS[i % SPARK_COLORS.length]}`,
    ].join(";");
    pieces += `<i style="${style}"></i>`;
  }
  return `<span class="sparks" aria-hidden="true">${pieces}</span>`;
}

// Below whatever stands at the top left: the stock card (wide screens) or the place label
// (phones), never on top of it.
function badgeTop() {
  const bar = $(".topbar")?.getBoundingClientRect().bottom ?? 56;
  const bottoms = [".hud-stock", ".zone-banner"]
    .map((sel) => $(sel))
    .filter((el) => el && el.getClientRects().length)
    .map((el) => el.getBoundingClientRect())
    .filter((r) => r.left < 60 && r.top < bar + 80)
    .map((r) => r.bottom);
  return Math.round(Math.max(bar, ...bottoms) + 8);
}

function showNextBadge() {
  const badge = (state.badges || []).find((b) => b.id === badgeQueue[0]);
  badgeQueue.shift();
  if (!badge) return badgeQueue.length ? showNextBadge() : endBadges();
  badgeShowing = true;
  badgeOnScreen = badge.id;
  const area = $("#badge-pop");
  area.innerHTML = `
    <div class="badge-toast">
      <div class="badge-toast-medal">${medalHtml(badge)}${sparksHtml()}</div>
      <div class="badge-toast-text">
        <p class="eyebrow">Badge earned</p>
        <p class="name">${esc(badge.name)}</p>
        <p class="meta">${esc(TIER_NAME[badge.tier] ?? "")} · ${earnedBadges().length} / ${state.badges.length}</p>
        <p class="what">${esc(badge.text)}</p>
      </div>
      <button class="close" type="button" aria-label="Close" title="Close">×</button>
      <span class="timer" style="--show:${BADGE_SHOW_MS}ms" aria-hidden="true"></span>
    </div>`;
  area.hidden = false;
  placeBadge();
  clearTimeout(badgeTimer);
  badgeTimer = setTimeout(leaveBadge, BADGE_SHOW_MS);
}

// The short messages (toasts) stand at the top centre. While a badge card is shown they move
// into the space right of it, or below it where that space is too narrow (phones), so the two
// never overlap. Only positions are set here (badges.css), nothing else.
const TOAST_ROOM = 240; // px a toast needs beside the card

// Where the card stands and where the toasts go. Run again whenever what is above it may have
// changed size: every redraw (the stock card gains rows), a fold of the stock card, a resize.
function placeBadge() {
  if (!badgeShowing) return;
  const area = $("#badge-pop");
  const top = `${badgeTop()}px`;
  if (area.style.top !== top) area.style.top = top;
  makeRoomForBadge(area);
}

function makeRoomForBadge(area) {
  const box = area.getBoundingClientRect();
  const body = document.body;
  body.style.setProperty("--badge-right", `${Math.round(box.right)}px`);
  body.style.setProperty("--badge-bottom", `${Math.round(box.bottom)}px`);
  const beside = window.innerWidth - box.right >= TOAST_ROOM;
  body.classList.toggle("badge-beside", beside);
  body.classList.toggle("badge-below", !beside);
}

// The card slides out; the next badge follows, or the corner is empty again.
function leaveBadge() {
  const card = $("#badge-pop .badge-toast");
  if (card?.classList.contains("leaving")) return; // already on its way out: keep its timer
  clearTimeout(badgeTimer);
  if (!card) return endBadges();
  card.classList.add("leaving");
  badgeTimer = setTimeout(() => {
    if (badgeQueue.length && !scene.preview) showNextBadge();
    else endBadges();
  }, reducedMotion ? 0 : BADGE_LEAVE_MS);
}

function endBadges() {
  clearTimeout(badgeTimer);
  badgeShowing = false;
  badgeOnScreen = null;
  document.body.classList.remove("badge-beside", "badge-below");
  const area = $("#badge-pop");
  area.hidden = true;
  area.innerHTML = "";
}

function wireBadgePop() {
  $("#badge-pop").addEventListener("click", (e) => {
    if (e.target.closest(".close")) leaveBadge();
  });
  window.addEventListener("resize", placeBadge);
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
      if (scene.sleeping) return sleep();
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
  $("#new-run-dialog").addEventListener("close", (e) => {
    if (e.target.returnValue !== "confirm") return;
    requests.run(async () => {
      const data = await send("/api/new-run", { confirm: true });
      if (!data) return;
      state = data.state;
      if (data.error) return toast(data.error, "error");
      freshRun(data);
    }).catch((err) => console.error(err));
  });
}

// A new run arrived (a new run, or a demo scenario that replaces the run): start over on the map.
function freshRun(data) {
  requests.renew(); // ticks and clicks queued for the old run are not sent
  closePanel();
  hideOverlay();
  evening = false;
  scene.sleeping = false;
  scene.clock = MORNING;
  placePlayer(state.player);
  renderAll();
  tellDashboard({ type: "action", kind: "new-run", after: data.state });
  toast(data.message);
}

// The demo (specs/demo-scenarios.md): the server loads a scenario by its id into this run.
function wireDemoActions() {
  wireDemo({
    getState: () => state,
    // an answer without a state (too many requests, the server is busy) changes nothing here
    // the scenario replaces the run: it waits in the queue of the ticks, none overtakes it
    load: (id) => enqueue(() => requests.run(async () => {
      const data = await send("/api/demo/load", { id, confirm: true });
      if (!data) return;
      if (data.state) state = data.state;
      if (data.error) {
        renderAll();
        return toast(data.error, "error");
      }
      freshRun(data);
      const panel = state.demo?.active?.panel; // which panel the scenario needs: from the server's data
      if (panel === "shift" || panel === "shops") openPanel(panel);
    })),
    // the end of the demo books an open day: a tick after it would find no open day
    finish: () => enqueue(() => requests.run(async () => {
      const data = await send("/api/demo/finish", {});
      if (!data) return;
      const before = state.day;
      if (data.state) state = data.state;
      if (!data.error) requests.renew(); // a tick queued for the booked day is not sent
      renderAll();
      if (data.error) return toast(data.error, "error");
      tellDashboard({ type: "action", after: data.state });
      toast(data.message);
      if (state.day !== before) startEvening(); // an open day was booked first: the evening follows
    })),
  });
}

// ---- start ---------------------------------------------------------------------------

function setMode(mode) {
  scene.preview = mode === "preview";
  document.body.classList.toggle("preview", scene.preview);
  if (scene.preview) closePanel();
  else noticeBadges(); // a badge earned while the dashboard was in front pops up now
}

// while a card or dialog is open, the figure stays where it is
export function inputBlocked() {
  return !$("#overlay").hidden || $("#new-run-dialog").open || $("#end-day-dialog").open || demoDialogOpen()
    || scene.sleeping || fading;
}

// The stock card can be folded away. The toggle sits outside #hud-stock, which is redrawn on
// every update, so the choice survives a redraw. Remembered per browser (the storage may be
// blocked: then the card simply starts open).
const STOCK_FOLDED_KEY = "ct-stock-folded";

function setStockFolded(folded) {
  $("#hud-stock-card").classList.toggle("collapsed", folded);
  const toggle = $("#stock-toggle");
  toggle.setAttribute("aria-expanded", String(!folded));
  toggle.title = folded ? "Show the stock" : "Hide the stock";
}

function wireStockToggle() {
  let folded = false;
  try { folded = localStorage.getItem(STOCK_FOLDED_KEY) === "1"; } catch { /* blocked: stay open */ }
  setStockFolded(folded);
  $("#stock-toggle").addEventListener("click", () => {
    folded = !$("#hud-stock-card").classList.contains("collapsed");
    setStockFolded(folded);
    try { localStorage.setItem(STOCK_FOLDED_KEY, folded ? "1" : "0"); } catch { /* not remembered */ }
    placeBadge(); // the badge card stands below the stock card
  });
}

export function initUi(firstState, actions) {
  state = firstState;
  seenBadges = new Set(earnedBadges().map((b) => b.id)); // badges from before the page loaded do not pop up
  placePlayer = actions.placePlayer;
  goHome = actions.goHome;
  jumpHome = actions.jumpHome;
  wakeAt = actions.wakeAt;
  wirePanel();
  wireEditor();
  wireOverlay();
  wireBadgePop();
  wireStockToggle();
  wireDemoActions();
  $("#btn-editor").addEventListener("click", () => openPanel("editor"));
  $("#btn-order").addEventListener("click", () => openPanel("order"));
  $("#btn-prices").addEventListener("click", () => openPanel("prices"));
  $("#btn-shops").addEventListener("click", () => openPanel("shops"));
  $("#btn-shift").addEventListener("click", () => openPanel("shift"));
  $("#btn-open").addEventListener("click", openDay);
  $("#btn-dashboard").addEventListener("click", () => tellDashboard({ type: "open-dashboard" }));
  $("#btn-new-run").addEventListener("click", askNewRun);
  $("#btn-go-home").addEventListener("click", walkHome);
  $("#btn-skip-walk").addEventListener("click", skipWalk);
  $("#end-day-dialog").addEventListener("close", (e) => {
    if (e.target.returnValue === "confirm") endDayConfirmed();
  });
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
