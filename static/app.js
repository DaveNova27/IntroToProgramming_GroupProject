// Campus Tycoon dashboard.
// The page only shows what the server sends and forwards clicks. Every rule
// (affordability, valid prices, demand, the day's result) is decided in
// logic.py; a rejected action comes back as an error and changes nothing.


let state = null;
let busy = false;
let shownDays = null; // history length on screen, to animate only when a day was added
const calm = window.matchMedia("(prefers-reduced-motion: reduce)");

// ---- helpers ---------------------------------------------------------------

// $, esc, fmt, fmtSigned and toast come from common.js
const fmtAxis = (cents) => `${cents < 0 ? "-" : ""}€${(Math.abs(cents) / 100).toLocaleString("en-US", { maximumFractionDigits: 0 })}`;

async function send(path, body) {
  if (busy) return null;
  busy = true;
  document.body.classList.add("busy");
  try {
    const res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    let data;
    try {
      data = await res.json();
    } catch {
      toast("The server hit an error. Nothing was saved.", "error");
      return null;
    }
    // what the player typed but has not sent yet survives the re-render;
    // only an accepted price replaces the typed price with the saved one
    const kept = path === "/api/new-run" ? {} : captureInputs();
    if (!data.error && path === "/api/price") delete kept[body.product]?.price;
    const before = state;
    state = data.state;
    render(kept);
    if (data.error) toast(data.error, "error");
    else {
      toast(data.message);
      // tell the campus map (views.js), so it can animate what just happened
      window.dispatchEvent(new CustomEvent("run-changed", {
        detail: { kind: path.split("/").pop(), product: body.product, before, after: data.state },
      }));
    }
    return data;
  } catch (err) {
    toast("Could not reach the server. Is app.py still running?", "error");
    return null;
  } finally {
    busy = false;
    document.body.classList.remove("busy");
  }
}

// ---- header and KPIs ---------------------------------------------------------

// Show a money value; when it changed, count up to it and flash once.
function setMoney(el, cents, format = fmt) {
  const from = el.dataset.value === undefined ? null : Number(el.dataset.value);
  el.dataset.value = cents;
  if (from === null || from === cents || calm.matches) {
    el.textContent = format(cents);
    return;
  }
  const start = performance.now();
  const duration = 500;
  const step = (now) => {
    const t = Math.min((now - start) / duration, 1);
    const eased = 1 - (1 - t) ** 3;
    el.textContent = format(Math.round(from + (cents - from) * eased));
    if (t < 1 && Number(el.dataset.value) === cents) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
  el.classList.remove("changed");
  void el.offsetWidth; // restart the flash animation
  el.classList.add("changed");
}

function renderHeader() {
  const pips = [];
  for (let d = 1; d <= state.last_day; d++) {
    const cls = d < state.day ? "done" : d === state.day ? "current" : "";
    const label = d < state.day ? `Day ${d}, traded` : `Day ${d}`;
    pips.push(`<li class="${cls}" aria-label="${label}">${d < state.day ? "✓" : d}</li>`);
  }
  $("#day-pips").innerHTML = pips.join("");
  $("#day-label").textContent = state.finished
    ? "Run complete"
    : `Day ${state.day} of ${state.last_day}`;
  showWeather($("#weather-chip"), state.weather);
}

function renderKpis() {
  const delta = state.cash - state.starting_cash;
  setMoney($("#kpi-cash"), state.cash);
  const deltaEl = $("#kpi-cash-delta");
  deltaEl.innerHTML = delta === 0
    ? "Same as the €100 start"
    : `<span class="${delta > 0 ? "delta-up" : "delta-down"}">${delta > 0 ? "▲" : "▼"} ${fmtSigned(delta)}</span> vs start`;

  const units = state.products.reduce((sum, p) => sum + p.stock, 0);
  setMoney($("#kpi-stock"), state.stock_value);
  $("#kpi-stock-units").textContent = `${units} unit${units === 1 ? "" : "s"} on the shelf`;

  const profit = state.history.reduce((sum, day) => sum + day.gross_profit, 0);
  const days = state.history.length;
  setMoney($("#kpi-profit"), profit);
  $("#kpi-profit-sub").textContent = days
    ? `over ${days} trading day${days === 1 ? "" : "s"}`
    : "No day traded yet";

  const gain = $("#kpi-gain");
  setMoney(gain, state.overall_gain, fmtSigned);
  gain.className = `kpi-value ${state.overall_gain > 0 ? "delta-up" : state.overall_gain < 0 ? "delta-down" : ""}`;
}

// ---- stock overview -------------------------------------------------------------

function renderStockOverview() {
  const overview = state.stock_overview;
  $("#stock-sub").textContent = `${overview.units} unit${overview.units === 1 ? "" : "s"} available · ${fmt(overview.value)} at cost`;
  // one scale for all products so the bars compare; at least one day of full demand
  const scale = Math.max(state.demand_levels.at_or_below_ref, ...overview.lines.map((l) => l.units));
  $("#stock-overview").innerHTML = overview.lines.map((line) => {
    const p = state.products.find((x) => x.id === line.product);
    const caption = line.units === 0
      ? "No stock"
      : state.finished
        ? `${line.units} left · trading is closed`
        : `sells ${line.sells_today} today · ${line.left_after_today} left after today`;
    return `
      <div class="stock-item" style="--accent: ${ACCENT[line.product]}">
        <div class="stock-top">
          <span class="dot" aria-hidden="true"></span>
          <span class="name">${esc(p.name)}</span>
          <span class="value">${fmt(line.value)} at cost</span>
        </div>
        <div class="stock-units"><strong>${line.units}</strong>unit${line.units === 1 ? "" : "s"} available</div>
        <div class="stock-bar" role="img" aria-label="${esc(p.name)}: ${caption}">
          ${line.sells_today ? `<span class="seg sell" style="width:${(line.sells_today / scale) * 100}%"></span>` : ""}
          ${line.left_after_today ? `<span class="seg left" style="width:${(line.left_after_today / scale) * 100}%"></span>` : ""}
        </div>
        <p class="stock-caption">${caption}</p>
      </div>`;
  }).join("");
}

// ---- product cards ---------------------------------------------------------

// Where a price sits on the demand meter: the scale runs from €0 to 2.5x the
// reference price, so the zone edges (1x and 2x) sit at 40% and 80%.
function meterPosition(price, ref) {
  return Math.max(0, Math.min(price / (2.5 * ref), 1)) * 100;
}
function zoneFor(price, ref) {
  if (price <= ref) return "z10";
  if (price <= 2 * ref) return "z5";
  return "z0";
}

function productCard(p) {
  const levels = state.demand_levels;
  const maxAffordable = Math.floor(state.cash / p.cost);
  const off = state.finished ? "disabled" : "";
  const zone = zoneFor(p.price, p.ref_price);
  return `
  <article class="card product" style="--accent: ${ACCENT[p.id]}" data-product="${p.id}">
    <div class="product-head">
      <span class="product-emoji" aria-hidden="true">${EMOJI[p.id] ?? "🛒"}</span>
      <div>
        <h3>${esc(p.name)}</h3>
        <p class="product-meta"><span>Cost ${fmt(p.cost)}</span><span>Ref. price ${fmt(p.ref_price)}</span></p>
      </div>
      <div class="stock-badge"><strong>${p.stock}</strong><span>in stock</span></div>
    </div>

    <div>
      <div class="block-label"><span>Selling price</span><span class="demand-text">sells up to ${p.demand}/day</span></div>
      <form class="field-row" data-form="price">
        <label class="input-wrap">
          <span class="prefix">€</span>
          <input name="price" inputmode="decimal" autocomplete="off" value="${(p.price / 100).toFixed(2)}"
                 aria-label="${esc(p.name)} selling price in euro" ${off}>
        </label>
        <button class="btn secondary" type="submit" ${off}>Save</button>
      </form>
      <div class="meter" aria-hidden="true">
        <div class="meter-track">
          <div class="zone z10 ${zone === "z10" ? "active" : ""}">${levels.at_or_below_ref}/day</div>
          <div class="zone z5 ${zone === "z5" ? "active" : ""}">${levels.up_to_double_ref}/day</div>
          <div class="zone z0 ${zone === "z0" ? "active" : ""}">0</div>
          <span class="meter-marker" style="left:${meterPosition(p.price, p.ref_price)}%"></span>
        </div>
        <div class="meter-scale">
          <span style="left:0">€0</span>
          <span style="left:40%">${fmt(p.ref_price)}</span>
          <span style="left:80%">${fmt(2 * p.ref_price)}</span>
        </div>
      </div>
      <p class="field-error" data-error="price"></p>
    </div>

    <div>
      <div class="block-label"><span>Buy stock</span><span>up to ${maxAffordable} affordable</span></div>
      <form class="field-row" data-form="buy">
        <div class="input-wrap">
          <button class="step-btn" type="button" data-step="-1" aria-label="One less" ${off}>−</button>
          <input name="quantity" inputmode="numeric" autocomplete="off" value="10"
                 style="text-align:center" aria-label="${esc(p.name)} quantity to buy" ${off}>
          <button class="step-btn" type="button" data-step="1" aria-label="One more" ${off}>+</button>
        </div>
        <button class="btn" type="submit" ${off}>Buy</button>
      </form>
      <div class="chips">
        <button class="chip" type="button" data-set="5" ${off}>5</button>
        <button class="chip" type="button" data-set="10" ${off}>10</button>
        <button class="chip" type="button" data-set="25" ${off}>25</button>
        <button class="chip" type="button" data-set="${maxAffordable}" ${off}>Max (${maxAffordable})</button>
      </div>
      <p class="buy-total"></p>
      <p class="field-error" data-error="buy"></p>
    </div>
  </article>`;
}

function updateBuyTotal(card) {
  const p = state.products.find((x) => x.id === card.dataset.product);
  const text = card.querySelector('[name="quantity"]').value.trim();
  const out = card.querySelector(".buy-total");
  if (!/^\d+$/.test(text)) {
    out.className = "buy-total";
    out.textContent = "Enter a whole number of units.";
    return;
  }
  const total = Number(text) * p.cost;
  const tooMuch = total > state.cash;
  out.className = `buy-total ${tooMuch ? "too-much" : ""}`;
  out.innerHTML = `Total <strong>${fmt(total)}</strong>${tooMuch ? " · more than your cash" : ""}`;
}

// Live preview while typing a price; the saved value only changes on "Save".
function previewPrice(card) {
  const p = state.products.find((x) => x.id === card.dataset.product);
  const text = card.querySelector('[name="price"]').value.trim().replace(",", ".");
  const value = Number(text);
  if (text === "" || !Number.isFinite(value) || value <= 0) return;
  const cents = Math.round(value * 100);
  const zone = zoneFor(cents, p.ref_price);
  card.querySelector(".meter-marker").style.left = `${meterPosition(cents, p.ref_price)}%`;
  card.querySelectorAll(".zone").forEach((z) => z.classList.toggle("active", z.classList.contains(zone)));
  const units = { z10: state.demand_levels.at_or_below_ref, z5: state.demand_levels.up_to_double_ref, z0: 0 }[zone];
  const label = card.querySelector(".demand-text");
  const unsaved = cents !== p.price;
  label.innerHTML = unsaved
    ? `<span class="unsaved">unsaved</span> · ${units}/day`
    : `sells up to ${units}/day`;
}

// Typed values per product: the quantity always, the price only if it was
// edited but not saved (otherwise the saved price is shown).
function captureInputs() {
  const kept = {};
  document.querySelectorAll(".product").forEach((card) => {
    const p = state.products.find((x) => x.id === card.dataset.product);
    const quantity = card.querySelector('[name="quantity"]').value;
    const price = card.querySelector('[name="price"]').value;
    kept[p.id] = { quantity };
    if (price !== (p.price / 100).toFixed(2)) kept[p.id].price = price;
  });
  return kept;
}

function renderProducts(kept = {}) {
  const grid = $("#product-grid");
  grid.innerHTML = state.products.map(productCard).join("");
  grid.querySelectorAll(".product").forEach((card) => {
    const typed = kept[card.dataset.product];
    if (typed && !state.finished) {
      card.querySelector('[name="quantity"]').value = typed.quantity;
      if (typed.price !== undefined) {
        card.querySelector('[name="price"]').value = typed.price;
        previewPrice(card);
      }
    }
    updateBuyTotal(card);
  });
}

// one set of listeners for all cards (cards are re-rendered after each action)
function wireProducts() {
  const grid = $("#product-grid");

  grid.addEventListener("input", (e) => {
    const card = e.target.closest(".product");
    if (!card) return;
    if (e.target.name === "quantity") updateBuyTotal(card);
    if (e.target.name === "price") previewPrice(card);
  });

  grid.addEventListener("click", (e) => {
    const card = e.target.closest(".product");
    if (!card) return;
    const input = card.querySelector('[name="quantity"]');
    const step = e.target.closest("[data-step]");
    const set = e.target.closest("[data-set]");
    if (step) {
      const current = /^\d+$/.test(input.value.trim()) ? Number(input.value) : 0;
      input.value = Math.max(1, current + Number(step.dataset.step));
    } else if (set) {
      input.value = set.dataset.set;
    } else {
      return;
    }
    updateBuyTotal(card);
  });

  grid.addEventListener("submit", async (e) => {
    e.preventDefault();
    const form = e.target;
    const card = form.closest(".product");
    const product = card.dataset.product;
    const kind = form.dataset.form;
    const data = kind === "buy"
      ? await send("/api/buy", { product, quantity: form.quantity.value })
      : await send("/api/price", { product, price: form.price.value });
    if (data?.error) {
      // the cards were re-rendered from the unchanged state; show why here too
      const fresh = $(`.product[data-product="${product}"]`);
      fresh.querySelector(`[data-error="${kind}"]`).textContent = data.error;
    }
  });
}

// ---- open the stand ----------------------------------------------------------

function renderOpenPanel() {
  const panel = $("#open-panel");
  if (state.finished) {
    const gain = state.overall_gain;
    panel.innerHTML = `
      <span class="badge">✓ Run complete</span>
      <p class="chart-sub" style="margin-top:16px">Overall result after ${state.last_day} days</p>
      <div class="final-hero ${gain > 0 ? "delta-up" : gain < 0 ? "delta-down" : ""}">${fmtSigned(gain)}</div>
      <dl class="sums">
        <div><dt>Final cash</dt><dd>${fmt(state.cash)}</dd></div>
        <div><dt>Remaining stock at cost</dt><dd>${fmt(state.stock_value)}</dd></div>
        <div><dt>Starting cash</dt><dd>−${fmt(state.starting_cash)}</dd></div>
        <div class="total"><dt>Overall result</dt><dd>${fmtSigned(gain)}</dd></div>
      </dl>
      <button class="btn open-btn" type="button" data-new-run>Start a new run</button>`;
    return;
  }

  const f = state.forecast;
  if (!f) {
    panel.innerHTML = `
      <h2>Shift running</h2>
      <p class="chart-sub">Day ${state.day} is being played in the shop. Finish it on the campus.</p>`;
    return;
  }
  const lines = f.lines.map((line) => {
    const p = state.products.find((x) => x.id === line.product);
    return `
      <li style="--accent: ${ACCENT[line.product]}">
        <span class="dot" aria-hidden="true"></span>
        <span class="name">${esc(p.name)}
          <span class="detail">sells ${line.sold} of ${p.stock} · demand ${line.demand} at ${fmt(line.price)}</span>
        </span>
        <span class="amount">${fmt(line.revenue)}<small>profit ${fmt(line.gross_profit)}</small></span>
      </li>`;
  }).join("");
  const sold = f.lines.reduce((sum, line) => sum + line.sold, 0);

  panel.innerHTML = `
    <h2>Open for day ${state.day}</h2>
    <p class="chart-sub">What a fully staffed day would bring (alone you only earn what you serve)</p>
    <ul class="forecast">${lines}</ul>
    <dl class="sums">
      <div><dt>Revenue</dt><dd>${fmt(f.revenue)}</dd></div>
      <div><dt>Cost of goods sold</dt><dd>${f.cogs ? "−" : ""}${fmt(f.cogs)}</dd></div>
      <div class="total"><dt>Gross profit</dt><dd>${fmt(f.gross_profit)}</dd></div>
      <div><dt>Cash after the day</dt><dd>${fmt(f.cash_after)}</dd></div>
    </dl>
    ${sold === 0 ? '<p class="notice"><span aria-hidden="true">⚠</span><span>Nothing will sell: your shelves are empty or every price is above twice the reference.</span></p>' : ""}
    <p class="notice"><span aria-hidden="true">ℹ</span><span>Without staff nothing sells by itself. Open day ${state.day} on the campus and serve the customers yourself.</span></p>`;
}

// ---- charts (hand-drawn SVG) -----------------------------------------------

const SVG_NS = "http://www.w3.org/2000/svg";

function niceTicks(min, max, count = 4) {
  if (min === max) max = min + 100;
  const raw = (max - min) / count;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw);
  const ticks = [];
  for (let v = Math.floor(min / step) * step; v <= max + step * 0.001; v += step) ticks.push(v);
  if (ticks[ticks.length - 1] < max) ticks.push(ticks[ticks.length - 1] + step);
  return ticks;
}

// A column with a 4px rounded data end and a square end at the baseline.
function barPath(x, w, yBase, yValue) {
  const h = Math.abs(yBase - yValue);
  const r = Math.min(4, w / 2, h);
  if (yValue <= yBase) {
    return `M${x},${yBase} L${x},${yValue + r} Q${x},${yValue} ${x + r},${yValue} `
      + `L${x + w - r},${yValue} Q${x + w},${yValue} ${x + w},${yValue + r} L${x + w},${yBase} Z`;
  }
  return `M${x},${yBase} L${x},${yValue - r} Q${x},${yValue} ${x + r},${yValue} `
    + `L${x + w - r},${yValue} Q${x + w},${yValue} ${x + w},${yValue - r} L${x + w},${yBase} Z`;
}

function el(name, attrs = {}, text) {
  const node = document.createElementNS(SVG_NS, name);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  if (text !== undefined) node.textContent = text;
  return node;
}

function showTooltip(evt, html) {
  const tip = $("#tooltip");
  tip.innerHTML = html;
  tip.hidden = false;
  const pad = 14;
  const { width, height } = tip.getBoundingClientRect();
  let x = evt.clientX + pad;
  let y = evt.clientY - height - pad;
  if (x + width > window.innerWidth - 8) x = evt.clientX - width - pad;
  if (y < 8) y = evt.clientY + pad;
  tip.style.left = `${x}px`;
  tip.style.top = `${y}px`;
}
const hideTooltip = () => { $("#tooltip").hidden = true; };

// categories: x labels; series: [{color, values: [cents|null]}];
// tooltip(i) -> html; label(i, s) -> text or null (selective direct labels)
function columnChart(container, { categories, series, tooltip, label, animate }) {
  container.innerHTML = "";
  const width = Math.max(container.clientWidth, 280);
  const height = 240;
  const m = { top: 22, right: 8, bottom: 28, left: 52 };
  const innerW = width - m.left - m.right;
  const innerH = height - m.top - m.bottom;

  const values = series.flatMap((s) => s.values).filter((v) => v !== null);
  const ticks = niceTicks(Math.min(0, ...values), Math.max(0, ...values));
  const lo = ticks[0];
  const hi = ticks[ticks.length - 1];
  const y = (v) => m.top + innerH - ((v - lo) / (hi - lo)) * innerH;

  const svg = el("svg", { viewBox: `0 0 ${width} ${height}`, role: "img" });

  for (const t of ticks) {
    svg.append(el("line", { class: t === 0 ? "baseline" : "gridline", x1: m.left, x2: width - m.right, y1: y(t), y2: y(t) }));
    svg.append(el("text", { class: "tick", x: m.left - 8, y: y(t) + 4, "text-anchor": "end" }, fmtAxis(t)));
  }

  const band = innerW / categories.length;
  const labelStep = Math.max(1, Math.ceil(46 / band)); // thin out x labels when bands are narrow
  const gap = 2;
  const barW = Math.min(24, (band * 0.7 - gap * (series.length - 1)) / series.length);
  const groupW = barW * series.length + gap * (series.length - 1);

  categories.forEach((cat, i) => {
    const bandX = m.left + band * i;
    const hasData = series.some((s) => s.values[i] !== null);

    // hover target bigger than the marks: the whole band
    const g = el("g");
    const hover = el("rect", { class: "hover-band", x: bandX + 2, y: m.top, width: band - 4, height: innerH, rx: 8 });
    g.append(hover);

    series.forEach((s, j) => {
      const v = s.values[i];
      if (v === null || v === 0) return;
      const x = bandX + (band - groupW) / 2 + j * (barW + gap);
      const cls = animate ? `bar grow ${v >= 0 ? "pos" : "neg"}` : "bar";
      g.append(el("path", { d: barPath(x, barW, y(0), y(v)), fill: s.color, class: cls, style: `animation-delay:${i * 50}ms` }));
      const text = label?.(i, j);
      if (text) {
        const ty = v >= 0 ? y(v) - 7 : y(v) + 15;
        g.append(el("text", { class: "value-label", x: x + barW / 2, y: ty, "text-anchor": "middle" }, text));
      }
    });

    if (i % labelStep === 0) {
      svg.append(el("text", { class: "tick", x: bandX + band / 2, y: height - 8, "text-anchor": "middle" }, cat));
    }

    if (hasData) {
      const hit = el("rect", { class: "hit", x: bandX, y: m.top, width: band, height: innerH });
      hit.addEventListener("mousemove", (e) => { hover.classList.add("on"); showTooltip(e, tooltip(i)); });
      hit.addEventListener("mouseleave", () => { hover.classList.remove("on"); hideTooltip(); });
      g.append(hit);
    }
    svg.append(g);
  });

  container.append(svg);
}

function renderCharts(animate = false) {
  const days = state.history;
  const cashBox = $("#cash-chart");
  const profitBox = $("#profit-chart");

  $("#profit-legend").innerHTML = state.products
    .map((p) => `<li style="--accent: ${ACCENT[p.id]}"><i></i>${esc(p.name)}</li>`)
    .join("");

  if (!days.length) {
    cashBox.innerHTML = `<div class="empty">Your cash curve starts after the first trading day.</div>`;
    profitBox.innerHTML = `<div class="empty">Open the stand to see profit per product here.</div>`;
    return;
  }

  // Cash: "Start" plus one column per day of the run; future days stay empty.
  const cashValues = [state.starting_cash];
  for (let d = 1; d <= state.last_day; d++) {
    cashValues.push(days[d - 1] ? days[d - 1].cash_after : null);
  }
  const lastIndex = days.length;
  columnChart(cashBox, {
    categories: ["Start", ...Array.from({ length: state.last_day }, (_, i) => `Day ${i + 1}`)],
    series: [{ color: "var(--cash)", values: cashValues }],
    animate,
    label: (i) => (i === lastIndex ? fmt(cashValues[i]) : null),
    tooltip: (i) => {
      if (i === 0) return `<strong>Start</strong><div class="row"><span>Cash</span><span>${fmt(state.starting_cash)}</span></div>`;
      const day = days[i - 1];
      return `<strong>Day ${day.day}</strong>
        <div class="row"><span>Cash at close</span><span>${fmt(day.cash_after)}</span></div>
        <div class="row"><span>Revenue</span><span>${fmt(day.revenue)}</span></div>
        <div class="row"><span>Gross profit</span><span>${fmt(day.gross_profit)}</span></div>`;
    },
  });

  // Gross profit per product and day (grouped, so a loss can dip below zero).
  columnChart(profitBox, {
    animate,
    categories: Array.from({ length: state.last_day }, (_, i) => `Day ${i + 1}`),
    series: state.products.map((p) => ({
      color: ACCENT[p.id],
      values: Array.from({ length: state.last_day }, (_, d) => {
        const line = days[d]?.lines.find((l) => l.product === p.id);
        return line ? line.gross_profit : null;
      }),
    })),
    tooltip: (i) => {
      const day = days[i];
      const rows = day.lines.map((line) => {
        const p = state.products.find((x) => x.id === line.product);
        return `<div class="row"><span><i style="--accent:${ACCENT[line.product]}"></i>${esc(p.name)}</span><span>${fmt(line.gross_profit)}</span></div>`;
      }).join("");
      return `<strong>Day ${day.day}</strong>${rows}
        <div class="row" style="margin-top:4px;font-weight:600"><span>Total</span><span>${fmt(day.gross_profit)}</span></div>`;
    },
  });
}

// ---- last day's result table ---------------------------------------------------

function renderResult() {
  const box = $("#result-table");
  const last = state.history[state.history.length - 1];
  if (!last) {
    $("#result-sub").textContent = "";
    box.innerHTML = `<div class="empty" style="min-height:120px">No trading day yet. Buy stock, set your prices and open the stand.</div>`;
    return;
  }
  $("#result-sub").textContent = `Day ${last.day} · cash after the day ${fmt(last.cash_after)}`;
  const money = (c) => `<span class="${c < 0 ? "neg" : ""}">${fmt(c)}</span>`;
  const rows = last.lines.map((line) => {
    const p = state.products.find((x) => x.id === line.product);
    return `<tr>
      <td><span class="swatch" style="--accent:${ACCENT[line.product]}"></span>${esc(p.name)}</td>
      <td>${fmt(line.price)}</td><td>${line.demand}</td><td>${line.sold}</td>
      <td>${fmt(line.revenue)}</td><td>${fmt(line.cogs)}</td><td>${money(line.gross_profit)}</td>
    </tr>`;
  }).join("");
  const sold = last.lines.reduce((sum, line) => sum + line.sold, 0);
  box.innerHTML = `
    <table>
      <thead><tr><th>Product</th><th>Price</th><th>Demand</th><th>Sold</th><th>Revenue</th><th>Cost of goods sold</th><th>Gross profit</th></tr></thead>
      <tbody>${rows}</tbody>
      <tfoot><tr><td>Total</td><td></td><td></td><td>${sold}</td>
        <td>${fmt(last.revenue)}</td><td>${fmt(last.cogs)}</td><td>${money(last.gross_profit)}</td></tr></tfoot>
    </table>${last.wages || (last.wages_unpaid || []).length ? `
    <p class="note">Wages paid ${fmt(last.wages)} · result after wages ${money(last.net)}${
      last.wages_unpaid.length ? ` · ${last.wages_unpaid.length} employee(s) stopped working: no money for the wage` : ""}</p>` : ""}`;
}

// ---- final result, history, new run ------------------------------------------

function renderFinalBanner() {
  const banner = $("#final-banner");
  banner.hidden = !state.finished;
  if (!state.finished) return;
  const profit = state.history.reduce((sum, day) => sum + day.gross_profit, 0);
  banner.innerHTML = `
    <div>
      <p class="eyebrow">✓ Run complete · ${state.history.length} days traded</p>
      <p class="headline">Overall result ${fmtSigned(state.overall_gain)}</p>
      <p class="breakdown">Final cash ${fmt(state.cash)} + stock at cost ${fmt(state.stock_value)} − ${fmt(state.starting_cash)} start · gross profit ${fmt(profit)}</p>
    </div>
    <button class="btn" type="button" data-new-run>Start a new run</button>`;
}

function renderHistory() {
  const box = $("#history-table");
  const days = state.history;
  if (!days.length) {
    box.innerHTML = `<div class="empty" style="min-height:96px">Completed days show up here.</div>`;
    return;
  }
  const sum = (key) => days.reduce((total, day) => total + day[key], 0);
  const soldOf = (day) => day.lines.reduce((total, line) => total + line.sold, 0);
  const money = (c) => `<span class="${c < 0 ? "neg" : ""}">${fmt(c)}</span>`;
  const rows = days.map((day) => `<tr>
      <td>Day ${day.day}</td><td>${soldOf(day)}</td><td>${fmt(day.revenue)}</td>
      <td>${fmt(day.cogs)}</td><td>${money(day.gross_profit)}</td><td>${fmt(day.cash_after)}</td>
    </tr>`).join("");
  box.innerHTML = `
    <table>
      <thead><tr><th>Day</th><th>Sold</th><th>Revenue</th><th>Cost of goods sold</th><th>Gross profit</th><th>Cash after</th></tr></thead>
      <tbody>${rows}</tbody>
      <tfoot><tr><td>Total</td><td>${days.reduce((t, d) => t + soldOf(d), 0)}</td>
        <td>${fmt(sum("revenue"))}</td><td>${fmt(sum("cogs"))}</td><td>${money(sum("gross_profit"))}</td>
        <td>${fmt(days[days.length - 1].cash_after)}</td></tr></tfoot>
    </table>`;
}

// CT01: ask first; only "Start new run" sends confirm=true to the server.
function askNewRun() {
  const days = state.history.length;
  $("#dialog-text").textContent = state.finished
    ? `Your completed run (overall result ${fmtSigned(state.overall_gain)}) is replaced by a fresh one: day 1, ${fmt(state.starting_cash)}, no stock. This cannot be undone.`
    : `This ends your current run on day ${state.day} with ${fmt(state.cash)} cash and ${days} traded day${days === 1 ? "" : "s"}. You start again on day 1 with ${fmt(state.starting_cash)} and no stock. This cannot be undone.`;
  const dialog = $("#new-run-dialog");
  dialog.returnValue = "";
  dialog.showModal();
}

function wireNewRun() {
  document.addEventListener("click", (e) => {
    if (e.target.closest("#new-run-btn, [data-new-run]") && state) askNewRun();
  });
  $("#new-run-dialog").addEventListener("close", (e) => {
    if (e.target.returnValue === "confirm") send("/api/new-run", { confirm: true });
  });
}

// The campus map changed the run: show its new state, keeping what was typed.
function applyExternalState(next) {
  if (!state) {
    state = next;
    return render();
  }
  const kept = captureInputs();
  state = next;
  render(kept);
}

// ---- boot --------------------------------------------------------------------

function render(kept) {
  const dayAdded = shownDays !== null && state.history.length > shownDays;
  const firstLoad = shownDays === null;
  shownDays = state.history.length;

  renderHeader();
  renderFinalBanner();
  renderKpis();
  renderStockOverview();
  renderProducts(kept);
  renderOpenPanel();
  renderCharts(!calm.matches && (firstLoad || dayAdded));
  renderResult();
  renderHistory();

  if (dayAdded && !calm.matches) {
    const card = $(".result-card");
    card.classList.remove("pulse");
    void card.offsetWidth;
    card.classList.add("pulse");
  }
}

async function boot() {
  wireProducts();
  wireNewRun();
  try {
    state = await (await fetch("/api/state")).json();
    render();
  } catch (err) {
    toast("Could not load the run. Start the server with: uv run python app.py", "error");
  }
  let resizeTimer;
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => state && renderCharts(), 150);
  });
}

boot();
