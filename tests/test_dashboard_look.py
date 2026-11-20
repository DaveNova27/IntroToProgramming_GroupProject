"""Checks from specs/dashboard-look.md ("Done when"): the dashboard in the campus look, shorter.

The grouping by shop and the profit per shop are pure functions in app.js; they are cut out whole and
run here with Node against app.view of real states (app.js is a classic script, it cannot be imported).
The page itself is checked in its source like the other page tests; the browser check is in the PR.
"""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

import app
import logic

STATIC = Path(app.__file__).parent / "static"
APP = (STATIC / "app.js").read_text(encoding="utf-8")
COMMON = (STATIC / "common.js").read_text(encoding="utf-8")
CSS = (STATIC / "style.css").read_text(encoding="utf-8")
HTML = (STATIC / "index.html").read_text(encoding="utf-8")
MAP_HTML = (STATIC / "map.html").read_text(encoding="utf-8")
NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="Node is not installed")


def body(source, name):
    """The text of a top-level function, up to the line that closes it."""
    match = re.search(rf"^(?:async )?function {name}\(.*?^}}$", source, re.S | re.M)
    assert match, f"function {name} not found"
    return match.group(0)


def run(expression, view):
    """Evaluate an expression over `view` with common.js and the pure functions of app.js, in Node."""
    accent = re.search(r"^const accentOf = .*$", APP, re.M).group(0)
    script = "\n".join([
        COMMON, accent, body(APP, "shopGroups"), body(APP, "profitByShop"),
        f"const view = {json.dumps(view)};",
        f"console.log(JSON.stringify({expression}));",
    ])
    done = subprocess.run([NODE, "-e", script], capture_output=True, text=True, timeout=60)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


def three_shops(days=2):
    """The Cafe with coffee and cake, the Beach Cafe and the Merchandise shop, `days` days traded."""
    state = logic.new_state(1)
    state["cash"] = 200_000
    for shop in ("beach_cafe", "merchandise"):
        state = logic.unlock_shop(state, shop)
    state = logic.buy_upgrade(state, "cafe", "cake")
    for product in logic.owned_products(state):
        state = logic.buy(state, product, 15)
    for _ in range(days):
        state, _ = logic.trade_day(state)
    return state


# ---- 1. the look ------------------------------------------------------------------------------

def test_the_campus_tokens_and_one_look_without_a_dark_mode():
    root = CSS[CSS.index(":root {"):CSS.index("}", CSS.index(":root {"))]
    for token in ("--petrol: #102f39;", "--lime: #bce65f;", "--surface: #f6f1e4;", "--page: #e9e3d2;",
                  "--radius: 4px;", "--shadow: 3px 3px", "--cash: var(--petrol);", "--mono:"):
        assert token in root, token
    assert "prefers-color-scheme" not in CSS  # the campus has no dark mode either
    for old in ("--sandwich", "--coffee", "--cookie", "radial-gradient"):
        assert old not in CSS, old
    assert "font: 600 9px var(--mono);" in CSS  # the small mono capitals of the campus HUD
    assert re.search(r"\.kpi-value \{ font: 700 26px/1\.15 var\(--mono\);", CSS)


def test_the_header_is_the_dark_campus_bar_with_the_ct_logo():
    assert '<span class="brand-mark" aria-hidden="true">CT</span>' in HTML
    assert '<p class="tagline">Carcavelos · Nova SBE · 30-day season</p>' in HTML
    for page in (HTML, MAP_HTML):
        assert "🥪" not in page and "snack stand" not in page
        icon = re.search(r'<link rel="icon" href="([^"]+)">', page).group(1)
        assert icon.startswith("data:image/svg+xml,") and ">CT</text>" in icon
    top = CSS[CSS.index(".topbar {"):CSS.index("}", CSS.index(".topbar {"))]
    assert "background: var(--petrol);" in top
    assert re.search(r"\.day-pips li \{[^}]*border-radius: var\(--radius-sm\);", CSS)  # square chips
    assert re.search(r"\.day-pips li\.done \{ background: var\(--lime\);", CSS)


# ---- 2. shorter --------------------------------------------------------------------------------

def test_the_stock_overview_card_is_gone_but_the_server_still_sends_it():
    assert 'id="stock-overview"' not in HTML and "stock-card" not in HTML
    assert "renderStockOverview" not in APP and "stock_overview" not in APP
    assert ".stock-grid" not in CSS and ".stock-card" not in CSS
    assert "stock_overview" in app.view(logic.new_state(1))  # nothing changed on the server


def test_from_900_px_popularity_beside_the_campus_and_products_beside_the_open_panel():
    wide = re.findall(r"@container dash \(min-width: 900px\) \{(.*?)\n\}", CSS, re.S)
    rules = "\n".join(wide)
    assert ".campus-card { grid-column: span 7; }" in rules
    assert ".pop-card { grid-column: span 5; }" in rules
    assert ".products { grid-column: span 8; }" in rules
    assert ".open-panel { grid-column: span 4;" in rules
    # review: two cards per row from 900 px, three only from 1100 px
    assert ".product-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }" in rules
    three = re.search(r"@container dash \(min-width: 1100px\) \{\n  \.product-grid \{ grid-template-columns: "
                      r"repeat\(3, minmax\(0, 1fr\)\); \}", CSS)
    assert three
    # review: the open panel starts with the head of "Your stand", no fixed offset that misses the card
    assert ".open-panel { grid-column: span 4; align-self: start; }" in rules
    assert "margin-top: 52px" not in CSS and "margin-top: 74px" not in CSS
    assert ".pop-grid { grid-template-columns: 1fr;" in rules
    # below 900 px every card takes the whole row
    assert re.search(r"\.campus-card, \.pop-card, \.products, \.open-panel, \.chart-card,\n"
                     r"\.result-card, \.history-card, \.badges-card, \.final-banner \{ grid-column: 1 / -1; \}", CSS)


def test_one_order_button_in_the_head_of_your_stand():
    assert '<span id="stand-order"></span>' in HTML
    head = HTML[HTML.index('<section class="products"'):HTML.index('id="product-grid"')]
    assert 'id="stand-order"' in head
    wire = body(APP, "wireProducts")
    assert wire.count("<button") == 1 and "data-go-order" in wire.split("<button")[1].split(">")[0]
    card = body(APP, "productCard")
    assert "data-go-order" not in card and "Buy stock" not in card and "order-note" not in card
    assert 'window.dispatchEvent(new CustomEvent("go-order"))' in wire  # the same message as before
    assert '$("#stand-order [data-go-order]").disabled = state.finished;' in body(APP, "renderProducts")


def test_the_price_curve_opens_with_why_this_number():
    card = body(APP, "productCard")
    details = card[card.index('<details class="why"'):card.index("</details>")]
    assert '<div class="curve">' in details and "curveSvg(" in details
    assert card.count("curveSvg(") == 1  # nowhere outside the details
    # review: on a complete run (no breakdown) the details stay, with the curve only
    assert "${p.breakdown ? `<details" not in card
    assert '<summary>${p.breakdown ? "Why this number?" : "Price curve"}</summary>' in details
    assert "${p.breakdown ? `<div class=\"why-body\">" in details


def test_under_a_shop_heading_the_product_names_are_one_level_lower():
    assert "productCard(p, g.heading ? 4 : 3)" in body(APP, "renderProducts")
    assert "<h${level}>${esc(p.name)}</h${level}>" in body(APP, "productCard")
    assert ".product-head h3, .product-head h4 {" in CSS


# ---- 3. grouped and per shop -------------------------------------------------------------------

@needs_node
def test_products_are_grouped_by_shop_in_shop_order():
    view = app.view(three_shops())
    groups = run("shopGroups(view.products, view.shops).map((g) => "
                 "({heading: g.heading, ids: g.products.map((p) => p.id)}))", view)
    assert groups == [
        {"heading": "Cafe", "ids": ["coffee", "cake"]},
        {"heading": "Beach Cafe", "ids": ["beer"]},
        {"heading": "Merchandise", "ids": ["hoodie"]},
    ]


@needs_node
def test_with_only_the_cafe_there_is_no_heading():
    view = app.view(logic.new_state(1))
    assert run("shopGroups(view.products, view.shops).map((g) => g.heading)", view) == [""]


@needs_node
def test_a_product_no_shop_names_is_kept_at_the_end():
    view = app.view(three_shops())
    view["products"].append({"id": "mystery", "name": "Mystery"})
    groups = run("shopGroups(view.products, view.shops).map((g) => [g.heading, g.products.length])", view)
    assert groups[-1] == ["", 1] and len(groups) == 4


@needs_node
def test_the_profit_chart_has_one_series_per_shop_that_adds_up_to_the_day():
    state = three_shops()
    view = app.view(state)
    series = run("profitByShop(view.history, view.shops, view.last_day)", view)
    assert [s["name"] for s in series] == ["Cafe", "Beach Cafe", "Merchandise"]
    # a shop's colour is the colour of its first product
    accent = run("[ACCENT.coffee, ACCENT.beer, ACCENT.hoodie]", view)
    assert [s["color"] for s in series] == accent
    for d, day in enumerate(state["history"]):
        assert sum(s["values"][d] for s in series) == day["gross_profit"]
    cafe = series[0]["values"]
    by_product = {l["product"]: l["gross_profit"] for l in state["history"][0]["lines"]}
    assert cafe[0] == by_product["coffee"] + by_product["cake"]
    assert all(s["values"][2:] == [None] * (view["last_day"] - 2) for s in series)  # days to come


def test_the_tooltip_and_the_legend_use_the_shop_series():
    charts = body(APP, "renderCharts")
    assert "profitByShop(days, state.shops, state.last_day)" in charts
    assert "series: perShop," in charts
    assert "esc(s.name)" in charts and "state.products\n    .map" not in charts
    assert '<span>Total</span><span>${fmt(day.gross_profit)}</span>' in charts


# ---- 4. phones and nothing lost -----------------------------------------------------------------

def test_the_kpi_numbers_fit_on_a_phone():
    phone = CSS[CSS.index("@container dash (max-width: 560px)"):]
    phone = phone[:phone.index("\n}\n")]
    assert ".kpi-value { font-size: 18px; }" in phone
    assert ".kpi-value.hero { font-size: 32px; }" in phone
    # review: three KPIs in a row below 900 px get a smaller number too
    middle = CSS[CSS.index("@container dash (max-width: 900px) {\n  .kpis"):]
    assert ".kpi-value { font-size: 22px; }" in middle[:middle.index("\n}\n")]
    assert re.search(r"\.kpi-value \{[^}]*white-space: nowrap;", CSS)


def test_names_stay_escaped_and_the_page_keeps_its_ids():
    assert '<h3 class="shop-heading">${esc(g.heading)}</h3>' in body(APP, "renderProducts")
    for part in ('id="pop-grid"', 'id="event-chip"', 'id="product-grid"', 'id="cash-chart"',
                 'id="profit-chart"', 'id="profit-legend"', 'id="kpi-cash"', 'id="open-panel"',
                 'id="campus-slot"', 'id="result-table"', 'id="history-table"', 'id="badge-grid"'):
        assert part in HTML, part


@needs_node
def test_the_dashboard_script_still_parses():
    for name in ("app.js", "common.js"):
        done = subprocess.run([NODE, "--check", str(STATIC / name)], capture_output=True, text=True, timeout=60)
        assert done.returncode == 0, (name, done.stderr)
