// Campus map: the same run as the dashboard, drawn as a tycoon scene.
// Every action goes to the server first. Only an accepted action is animated,
// and the animation only shows what the server already decided and saved.

const SVG_NS = "http://www.w3.org/2000/svg";
const COLOR = { sandwich: "#2a78d6", coffee: "#eb6834", cookie: "#1baf7a" };
const DARK = { sandwich: "#1c5cab", coffee: "#b94d22", cookie: "#14855c" };
const STUDENTS = ["🧑‍🎓", "👩‍🎓", "👨‍🎓", "🧑", "👩", "👨", "🧕", "🧔"];

const UNITS_PER_CRATE = 5;
const MAX_CRATES = 5;          // per product column; more stock shows a "+"
const CRATE = { w: 36, h: 15 };
const SHED_COLUMN = { sandwich: 741, coffee: 785, cookie: 829 };
const SHED_FLOOR = 484;
const TRUCK_STOP = 710;        // cargo box lines up with the driveway
const MAX_CUSTOMERS = 24;      // more sales are grouped per student

let state = null;
let animating = false;
let dayRunning = null;         // the day being played while its animation runs
let fast = false;
let panelMode = null;          // "order" | "prices" | null
let orderProduct = "sandwich";
let finalSeen = false;
const calm = window.matchMedia("(prefers-reduced-motion: reduce)");

// ---- small helpers -----------------------------------------------------------

function svg(name, attrs = {}, text) {
  const node = document.createElementNS(SVG_NS, name);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  if (text !== undefined) node.textContent = text;
  return node;
}
const place = (node, x, y) => node.setAttribute("transform", `translate(${x} ${y})`);
const product = (pid) => state.products.find((p) => p.id === pid);
// units per product, e.g. { sandwich: 12, coffee: 0, cookie: 3 }
const stockOf = (run) => Object.fromEntries(run.products.map((p) => [p.id, p.stock]));

const linear = (t) => t;
const easeInOut = (t) => (t < 0.5 ? 2 * t * t : 1 - (-2 * t + 2) ** 2 / 2);
const easeOut = (t) => 1 - (1 - t) ** 3;
const easeIn = (t) => t ** 3;

// Run update(0..1) over `ms`. "Skip" (fast) or reduced motion jumps to the end.
function tween(ms, update, easing = easeInOut) {
  if (fast || calm.matches) {
    update(1);
    return Promise.resolve();
  }
  return new Promise((resolve) => {
    const start = performance.now();
    const frame = (now) => {
      const t = fast ? 1 : Math.min((now - start) / ms, 1);
      update(easing(t));
      if (t < 1) requestAnimationFrame(frame);
      else resolve();
    };
    requestAnimationFrame(frame);
  });
}
const wait = (ms) => tween(ms, () => {}, linear);

function lerpColor(a, b, t) {
  const pa = a.match(/\w\w/g).map((h) => parseInt(h, 16));
  const pb = b.match(/\w\w/g).map((h) => parseInt(h, 16));
  return "#" + pa.map((v, i) => Math.round(v + (pb[i] - v) * t).toString(16).padStart(2, "0")).join("");
}

// The demand tier a typed price would fall in (preview only; the server decides).
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

// ---- scene: kiosk, shed, HUD -----------------------------------------------------

function buildScallops() {
  const g = $("#scallops");
  for (let i = 0, x = 466; x <= 676; i++, x += 15) {
    g.append(svg("circle", { cx: x, cy: 372, r: 7.5, fill: i % 2 ? "#fff6e8" : "#e34948" }));
  }
}

function renderKiosk(stock) {
  const goods = $("#window-goods");
  goods.innerHTML = "";
  const menu = $("#menu");
  menu.innerHTML = "";
  state.products.forEach((p, i) => {
    goods.append(svg("text", { x: 526 + i * 44, y: 410, class: stock[p.id] ? "" : "empty" }, EMOJI[p.id]));

    const cx = 504 + i * 66;
    const tag = svg("g", { class: "menu-tag", "data-product": p.id });
    tag.append(svg("rect", { x: cx - 31, y: 451, width: 62, height: 31, rx: 5 }));
    tag.append(svg("text", { x: cx - 17, y: 466, class: "tag-emoji" }, EMOJI[p.id]));
    tag.append(svg("text", { x: cx + 10, y: 461, class: "tag-price" }, fmt(p.price)));
    tag.append(svg("text", { x: cx + 10, y: 477, class: "tag-demand" }, state.finished ? "closed" : `${p.demand}/day`));
    menu.append(tag);
  });
}

function crate(pid, x, y) {
  const g = svg("g", { class: "crate" });
  g.append(svg("rect", { class: "box", x, y, width: CRATE.w, height: CRATE.h, rx: 2, fill: COLOR[pid], stroke: DARK[pid] }));
  g.append(svg("line", { x1: x + 3, x2: x + CRATE.w - 3, y1: y + CRATE.h / 2, y2: y + CRATE.h / 2, stroke: DARK[pid], "stroke-width": 1.5 }));
  return g;
}
const crateTop = (index) => SHED_FLOOR - (index + 1) * (CRATE.h + 1);

function renderShed(stock) {
  const g = $("#crates");
  g.innerHTML = "";
  for (const p of state.products) {
    const units = stock[p.id];
    const cx = SHED_COLUMN[p.id];
    const crates = Math.min(Math.ceil(units / UNITS_PER_CRATE), MAX_CRATES);
    for (let i = 0; i < crates; i++) g.append(crate(p.id, cx - CRATE.w / 2, crateTop(i)));
    if (units > MAX_CRATES * UNITS_PER_CRATE) {
      g.append(svg("text", { class: "crate-more", x: cx, y: crateTop(MAX_CRATES - 1) - 3 }, "+"));
    }
    g.append(svg("text", { class: "crate-count", x: cx, y: 396 }, units));
  }
}

function renderStockRows(stock) {
  const forecast = Object.fromEntries(state.stock_overview.lines.map((l) => [l.product, l]));
  $("#hud-stock").innerHTML = `<h3>In storage</h3>` + state.products.map((p) => {
    const sub = dayRunning ? "on sale now" : state.finished ? "trading closed" : `sells ${forecast[p.id].sells_today} today`;
    return `<div class="stock-row" style="--accent:${COLOR[p.id]}">
      <span class="em" aria-hidden="true">${EMOJI[p.id]}</span>
      <span class="nm">${esc(p.name)}<small>${sub}</small></span>
      <span class="units" aria-label="${esc(p.name)} in stock">${stock[p.id]}</span>
    </div>`;
  }).join("");
}

function setCash(cents, bump = false) {
  const el = $("#hud-cash");
  el.textContent = fmt(cents);
  if (bump && !calm.matches) {
    el.classList.remove("bump");
    void el.getBoundingClientRect();
    el.classList.add("bump");
  }
}

function renderHud() {
  const pips = [];
  for (let d = 1; d <= state.last_day; d++) {
    const cls = d < state.day ? "done" : d === state.day ? "current" : "";
    pips.push(`<li class="${cls}">${d < state.day ? "✓" : d}</li>`);
  }
  $("#day-pips").innerHTML = pips.join("");
  $("#day-label").textContent = state.finished ? "Run complete" : `Day ${state.day} of ${state.last_day}`;
  setCash(state.cash);
  const gain = state.overall_gain;
  const gainEl = $("#hud-gain");
  gainEl.textContent = `${fmtSigned(gain)} overall`;
  gainEl.className = `sub ${gain > 0 ? "up" : gain < 0 ? "down" : ""}`;
}

function renderToolbar() {
  const locked = animating || state.finished;
  $("#btn-order").disabled = locked;
  $("#btn-prices").disabled = locked;
  $("#btn-open").disabled = locked;
  $("#open-label").textContent = dayRunning
    ? `Day ${dayRunning} is open…`
    : state.finished ? "Run complete" : `Open day ${state.day}`;
  $("#btn-fast").hidden = !animating;
  const empty = state.products.every((p) => p.stock === 0);
  $("#btn-order").classList.toggle("hint", empty && !locked);
}

function renderAll() {
  renderHud();
  renderStockRows(stockOf(state));
  renderShed(stockOf(state));
  renderKiosk(stockOf(state));
  renderToolbar();
  if (panelMode) renderPanel();
}

// ---- side panel: order stock and prices ------------------------------------------

function openPanel(mode) {
  if (animating || state.finished) return;
  panelMode = mode;
  $("#panel").hidden = false;
  renderPanel();
}
function closePanel() {
  panelMode = null;
  $("#panel").hidden = true;
}

function renderPanel() {
  const body = $("#panel-body");
  if (panelMode === "order") {
    $("#panel-title").textContent = "🚚 Order stock";
    const p = product(orderProduct);
    const max = Math.floor(state.cash / p.cost);
    body.innerHTML = `
      <div class="pick" role="group" aria-label="Product">
        ${state.products.map((x) => `
          <button type="button" data-pick="${x.id}" aria-pressed="${x.id === orderProduct}" style="--accent:${COLOR[x.id]}">
            <span class="em" aria-hidden="true">${EMOJI[x.id]}</span>
            <span class="nm">${esc(x.name)}</span>
            <small>${fmt(x.cost)} each · ${x.stock} in shed</small>
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
        <div class="total" id="order-total" style="margin-top:14px"></div>
        <p class="error" id="order-error"></p>
        <button class="btn wide" type="submit" style="margin-top:12px">Order delivery 🚚</button>
      </form>`;
    updateOrderTotal();
  } else if (panelMode === "prices") {
    $("#panel-title").textContent = "🏷️ Menu board";
    body.innerHTML = `
      <p class="note">Students buy ${state.demand_levels.at_or_below_ref} a day at or below the reference price, ${state.demand_levels.up_to_double_ref} up to twice it, none above.</p>
      ${state.products.map((p) => `
        <form class="price-row" data-price-form="${p.id}">
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
    const pick = e.target.closest("[data-pick]");
    if (pick) {
      const typed = $("#order-form")?.quantity.value;
      orderProduct = pick.dataset.pick;
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
    const label = form.querySelector("[data-demand]");
    if (!Number.isFinite(value) || value <= 0) return;
    const cents = Math.round(value * 100);
    label.innerHTML = cents === p.price
      ? `Sells up to <b>${p.demand}</b> a day`
      : `Sells up to <b>${previewDemand(cents, p.ref_price)}</b> a day · not saved yet`;
  });

  panel.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (e.target.id === "order-form") return order(orderProduct, e.target.quantity.value);
    const form = e.target.closest("[data-price-form]");
    if (form) savePrice(form);
  });
}

// ---- actions -------------------------------------------------------------------

async function run(sequence) {
  animating = true;
  renderToolbar();
  try {
    await sequence();
  } finally {
    animating = false;
    dayRunning = null;
    fast = false;
    renderAll();
  }
}

async function order(pid, quantityText) {
  if (animating) return;
  const before = state;
  const data = await send("/api/buy", { product: pid, quantity: quantityText });
  if (!data) return;
  state = data.state;
  if (data.error) {
    // nothing changed; keep the panel and what was typed, show why
    renderHud();
    renderToolbar();
    $("#order-error").textContent = data.error;
    return toast(data.error, "error");
  }
  closePanel();
  await run(() => playDelivery(pid, before));
  toast(data.message);
}

async function savePrice(form) {
  const pid = form.dataset.priceForm;
  const data = await send("/api/price", { product: pid, price: form.price.value });
  if (!data) return;
  state = data.state;
  if (data.error) {
    form.querySelector("[data-error]").textContent = data.error;
    return toast(data.error, "error");
  }
  form.querySelector("[data-error]").textContent = "";
  const p = product(pid);
  form.price.value = (p.price / 100).toFixed(2);
  form.querySelector("[data-demand]").innerHTML = `Sells up to <b>${p.demand}</b> a day`;
  renderKiosk(stockOf(state));
  renderStockRows(stockOf(state));
  const tag = $(`.menu-tag[data-product="${pid}"]`);
  tag?.classList.add("pop");
  toast(data.message);
}

async function openDay() {
  if (animating || state.finished) return;
  closePanel();
  const before = state;
  const data = await send("/api/open", { day: state.day });
  if (!data) return;
  state = data.state;
  if (data.error) {
    renderAll();
    return toast(data.error, "error");
  }
  const result = state.history[state.history.length - 1];
  dayRunning = result.day;
  await run(() => playDay(before, result));
  showDaySummary(result);
}

// ---- animation: delivery truck ---------------------------------------------------

function truck(pid) {
  const g = svg("g", { class: "truck" });
  g.append(svg("rect", { x: 0, y: -88, width: 150, height: 68, rx: 6, fill: "#f6f3ec", stroke: "#d8d1c2", "stroke-width": 2 }));
  g.append(svg("rect", { x: 0, y: -34, width: 150, height: 12, fill: COLOR[pid] }));
  g.append(svg("text", { x: 75, y: -72, "text-anchor": "middle", class: "truck-label", fill: "#6b6f76", style: "fill:#6b6f76" }, "CAMPUS SUPPLY"));
  g.append(svg("text", { x: 75, y: -40, "text-anchor": "middle", "font-size": 26 }, EMOJI[pid]));
  g.append(svg("path", { d: "M150 -66 H184 Q196 -66 202 -52 L212 -34 V-20 H150 Z", fill: COLOR[pid] }));
  g.append(svg("path", { d: "M158 -60 H182 Q190 -60 194 -50 L199 -40 H158 Z", fill: "#d6ecfa" }));
  g.append(svg("rect", { x: -4, y: -24, width: 220, height: 8, rx: 3, fill: "#3a3d44" }));
  const wheels = [34, 178].map((cx) => {
    const w = svg("g", { transform: `translate(${cx} -12)` });
    const spin = svg("g");
    spin.append(svg("circle", { r: 13, fill: "#25262b" }));
    spin.append(svg("circle", { r: 5.5, fill: "#c9c9c9" }));
    spin.append(svg("rect", { x: -1.5, y: -11, width: 3, height: 7, fill: "#c9c9c9" }));
    w.append(spin);
    g.append(w);
    return spin;
  });
  g.roll = (x) => wheels.forEach((spin) => spin.setAttribute("transform", `rotate(${(x / 13) * (180 / Math.PI)})`));
  return g;
}

async function drive(t, from, to, ms, easing) {
  await tween(ms, (k) => {
    const x = from + (to - from) * k;
    place(t, x, 612);
    t.roll(x);
  }, easing);
}

function floatText(x, y, text, cls, rise = 50, ms = 1100) {
  const node = svg("text", { x, y, class: cls }, text);
  $("#effects").append(node);
  tween(ms, (k) => {
    node.setAttribute("y", y - rise * k);
    node.setAttribute("opacity", k < 0.6 ? 1 : 1 - (k - 0.6) / 0.4);
  }, easeOut).then(() => node.remove());
}

async function flyCrate(pid, from, to) {
  const node = crate(pid, -CRATE.w / 2, -CRATE.h / 2);
  $("#effects").append(node);
  await tween(380, (k) => {
    const x = from.x + (to.x - from.x) * k;
    const y = from.y + (to.y - from.y) * k - Math.sin(Math.PI * k) * 60;
    place(node, x, y);
  }, easeInOut);
  node.remove();
}

async function playDelivery(pid, before) {
  const t = truck(pid);
  $("#actors").append(t);
  await drive(t, -260, TRUCK_STOP, 1700, easeOut);

  // pay on delivery: cash goes down by what the server charged
  const cost = before.cash - state.cash;
  floatText(785, 515, `−${fmt(cost)}`, "cost");
  setCash(state.cash, true);

  // unload: one flying crate per 5 units (at least one, at most six)
  const quantity = stockOf(state)[pid] - stockOf(before)[pid];
  const crates = Math.max(1, Math.min(Math.ceil(quantity / UNITS_PER_CRATE), 6));
  const shown = { ...stockOf(before) };
  for (let i = 0; i < crates; i++) {
    const after = stockOf(before)[pid] + Math.round((quantity * (i + 1)) / crates);
    const slot = Math.min(Math.ceil(after / UNITS_PER_CRATE), MAX_CRATES) - 1;
    await flyCrate(pid, { x: TRUCK_STOP + 75, y: 560 }, { x: SHED_COLUMN[pid], y: crateTop(Math.max(slot, 0)) + CRATE.h / 2 });
    shown[pid] = after;
    renderShed(shown);
    renderStockRows(shown);
  }
  renderKiosk(stockOf(state));
  await wait(250);
  await drive(t, TRUCK_STOP, 1320, 1300, easeIn);
  t.remove();
}

// ---- animation: a trading day ------------------------------------------------------

function setSky(k) {
  // k = 0 morning ... 1 evening
  $("#sky-top").setAttribute("stop-color", lerpColor("#6fb8ef", "#3d4f8e", Math.max(0, k - 0.6) / 0.4));
  $("#sky-bottom").setAttribute("stop-color", lerpColor("#cfeaff", "#f5a76c", Math.max(0, k - 0.6) / 0.4));
  $("#night").setAttribute("opacity", (Math.max(0, k - 0.75) / 0.25) * 0.28);
  const sun = $("#sun");
  sun.setAttribute("cx", 140 + 920 * k);
  sun.setAttribute("cy", 150 - Math.sin(Math.PI * k) * 100);
}

// Turn the day's result into students: one per sale (grouped if many),
// plus a few who leave because a product was sold out or too expensive.
function customersFor(before, result) {
  const total = result.lines.reduce((sum, l) => sum + l.sold, 0);
  const per = Math.max(1, Math.ceil(total / MAX_CUSTOMERS));
  const queues = result.lines.map((line) => {
    const q = [];
    for (let left = line.sold; left > 0; left -= per) {
      const units = Math.min(per, left);
      q.push({ pid: line.product, units, amount: units * line.price });
    }
    if (line.sold < line.demand) {
      for (let i = 0; i < Math.min(line.demand - line.sold, 3); i++) q.push({ pid: line.product, reason: "sold out" });
    } else if (line.demand === 0 && stockOf(before)[line.product] > 0) {
      for (let i = 0; i < 2; i++) q.push({ pid: line.product, reason: "too pricey" });
    }
    return q;
  });
  const order = [];
  while (queues.some((q) => q.length)) queues.forEach((q) => q.length && order.push(q.shift()));
  return order;
}

async function walk(node, path, ms) {
  const len = path.getTotalLength();
  await tween(ms, (k) => {
    const p = path.getPointAtLength(len * k);
    place(node, p.x, p.y - Math.abs(Math.sin(k * len / 14)) * 2);
  }, linear);
}

async function visit(customer, ledger) {
  const side = Math.random() < 0.5 ? "a" : "b";
  const node = svg("g");
  node.append(svg("text", { class: "actor", y: 0 }, STUDENTS[Math.floor(Math.random() * STUDENTS.length)]));
  $("#actors").append(node);
  await walk(node, $(`#route-${side}`), 1500);

  if (customer.reason) {
    const bubble = svg("g", { class: "bubble", transform: "translate(0 -46)" });
    bubble.append(svg("rect", { x: -40, y: -11, width: 80, height: 22, rx: 11 }));
    bubble.append(svg("text", { y: 0 }, `${EMOJI[customer.pid]} ${customer.reason}`));
    node.append(bubble);
    await wait(700);
    bubble.remove();
  } else {
    // the sale: coin over the kiosk, cash up, stock down
    ledger.cash += customer.amount;
    ledger.stock[customer.pid] -= customer.units;
    floatText(570 + (Math.random() * 80 - 40), 300, `+${fmt(customer.amount)}`, "coin", 46, 1000);
    setCash(ledger.cash, true);
    renderShed(ledger.stock);
    renderStockRows(ledger.stock);
    renderKiosk(ledger.stock);
    node.append(svg("text", { class: "actor-carry", x: 14, y: -6 }, EMOJI[customer.pid]));
    await wait(250);
  }
  await walk(node, $(`#exit-${side}`), 1700);
  node.remove();
}

async function playDay(before, result) {
  const ledger = { cash: before.cash, stock: { ...stockOf(before) } };
  const customers = customersFor(before, result);
  const spacing = 330;
  const dayLength = Math.max(customers.length * spacing + 3600, 4000);

  setSky(0);
  const sky = tween(dayLength, setSky, linear);
  const visits = [];
  for (const c of customers) {
    visits.push(visit(c, ledger));
    await wait(spacing);
  }
  await Promise.all(visits);
  await sky;
  await wait(300);
}

// ---- overlays: end of day, end of run, new run --------------------------------------

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
    <p class="eyebrow">🌇 Day ${result.day} closed</p>
    <p class="big ${gp > 0 ? "up" : gp < 0 ? "down" : ""}">${fmtSigned(gp)}</p>
    <p class="note">gross profit · cost of goods sold ${fmt(result.cogs)} · cash now ${fmt(result.cash_after)}</p>
    <table>
      <thead><tr><th>Product</th><th>Sold</th><th>Revenue</th><th>Profit</th></tr></thead>
      <tbody>${rows}</tbody>
      <tfoot><tr><td>Total</td><td>${sold}</td><td>${fmt(result.revenue)}</td><td>${fmt(gp)}</td></tr></tfoot>
    </table>
    <div class="actions">
      <button class="btn" type="button" data-next>${state.finished ? "See the final result" : `Start day ${state.day} ☀️`}</button>
    </div>`);
}

function showFinal() {
  finalSeen = true;
  const gain = state.overall_gain;
  showOverlay(`
    <p class="eyebrow">🏁 Run complete · ${state.history.length} days</p>
    <p class="big ${gain > 0 ? "up" : gain < 0 ? "down" : ""}">${fmtSigned(gain)}</p>
    <p class="note">overall result = final cash ${fmt(state.cash)} + stock at cost ${fmt(state.stock_value)} − ${fmt(state.starting_cash)} start</p>
    <div class="actions" style="margin-top:18px">
      <button class="btn" type="button" data-new-run>Start a new run</button>
      <a class="btn ghost" href="/">Dashboard</a>
    </div>
    <div class="actions"><button class="btn ghost" type="button" data-dismiss>Look around the campus</button></div>`);
}

function askNewRun() {
  $("#dialog-text").textContent = state.finished
    ? `Your completed run (${fmtSigned(state.overall_gain)}) is replaced by a fresh one: day 1, ${fmt(state.starting_cash)}, empty storage. This cannot be undone.`
    : `This ends your run on day ${state.day} with ${fmt(state.cash)} cash. You start again on day 1 with ${fmt(state.starting_cash)} and empty storage. This cannot be undone.`;
  const dialog = $("#new-run-dialog");
  dialog.returnValue = "";
  dialog.showModal();
}

function wireOverlay() {
  $("#overlay").addEventListener("click", (e) => {
    if (e.target.closest("[data-next]")) {
      hideOverlay();
      setSky(0);
      if (state.finished) showFinal();
    } else if (e.target.closest("[data-dismiss]")) {
      hideOverlay();
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
    hideOverlay();
    finalSeen = false;
    setSky(0);
    renderAll();
    toast(data.message);
  });
}

// ---- layout and boot ---------------------------------------------------------------

// Wide screens see the whole campus; narrower ones zoom to the kiosk and shed.
function fitScene() {
  const scene = $("#scene");
  const ratio = window.innerWidth / window.innerHeight;
  if (ratio >= 1.3) {
    scene.setAttribute("viewBox", "0 0 1200 680");
    scene.setAttribute("preserveAspectRatio", "xMidYMid slice");
  } else if (ratio >= 0.8) {
    scene.setAttribute("viewBox", "230 120 760 560");
    scene.setAttribute("preserveAspectRatio", "xMidYMid slice");
  } else {
    // portrait: show kiosk and shed whole; sky above and road below fill the rest
    scene.setAttribute("viewBox", "440 285 450 395");
    scene.setAttribute("preserveAspectRatio", "xMidYMid meet");
  }
}

function wireScene() {
  $("#btn-order").addEventListener("click", () => openPanel("order"));
  $("#btn-prices").addEventListener("click", () => openPanel("prices"));
  $("#btn-open").addEventListener("click", openDay);
  $("#btn-fast").addEventListener("click", () => { fast = true; });
  const hotspot = (id, mode) => {
    const el = $(id);
    el.addEventListener("click", () => openPanel(mode));
    el.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        openPanel(mode);
      }
    });
  };
  hotspot("#shed", "order");
  hotspot("#kiosk", "prices");
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && panelMode) closePanel();
  });
  window.addEventListener("resize", fitScene);
}

async function boot() {
  buildScallops();
  fitScene();
  wireScene();
  wirePanel();
  wireOverlay();
  try {
    state = await (await fetch("/api/state")).json();
  } catch {
    return toast("Could not load the run. Start the server with: uv run python app.py", "error");
  }
  setSky(0);
  renderAll();
  if (state.finished && !finalSeen) showFinal();
}

boot();
