"""Checks from specs/stock-on-counter.md ("Done when"): the server counts what stands on the counters
of the open day (`on_counter`), the stock card shows storeroom plus counter, and the Shift panel draws
no "+0" button. The page is drawn in a browser, so like the other page tests the screen checks read
the files. New file; no old test is touched here."""

import re
from pathlib import Path

import app
import logic

UI = (Path(__file__).resolve().parent.parent / "static" / "world" / "ui.js").read_text()
DASHBOARD = (Path(__file__).resolve().parent.parent / "static" / "app.js").read_text()


def product(state, pid):
    (p,) = [p for p in app.view(state)["products"] if p["id"] == pid]
    return p


def cafe_with_coffee(units=60):
    state = logic.new_state()
    state["cash"] = 1_000_000
    state["stock"]["coffee"] = units
    return state


# ---- Check 1 to 3: the server counts the counter -------------------------------------------------

def test_without_an_open_day_nothing_is_on_the_counter():
    state = cafe_with_coffee()
    assert all(p["on_counter"] == 0 for p in app.view(state)["products"])
    assert product(state, "coffee")["stock"] == 60


def test_units_moved_to_the_counter_are_counted_there():
    state = logic.start_shift(logic.open_day(cafe_with_coffee()), "cafe")
    state = logic.refill(state, "coffee", 16)
    coffee = product(state, "coffee")
    assert coffee["stock"] == 44 and coffee["on_counter"] == 16
    assert coffee["stock"] + coffee["on_counter"] == 60  # nothing sold yet: the player holds all 60


def test_a_crews_counter_beside_the_players_shift_counts_too():
    state = cafe_with_coffee()
    state["stock"]["beer"] = 60
    state = logic.unlock_shop(state, "beach_cafe")
    state = logic.buy_upgrade(logic.buy_upgrade(state, "beach_cafe", "staff_1"), "beach_cafe", "staff_2")
    state = logic.open_day(state)
    assert "beach_cafe" in state["shift"]["extra"]
    for _ in range(logic.SHIFT_TICKS - 1):  # the crew fills its counter as it works
        if state["shift"]["extra"]["beach_cafe"]["counter"].get("beer", 0):
            break
        state, result = logic.tick(state)
        assert result is None
    on_beach_counter = state["shift"]["extra"]["beach_cafe"]["counter"].get("beer", 0)
    assert on_beach_counter > 0
    assert product(state, "beer")["on_counter"] == on_beach_counter


def test_after_the_day_the_counter_is_back_in_the_storeroom():
    state = logic.start_shift(logic.open_day(cafe_with_coffee()), "cafe")
    state = logic.refill(state, "coffee", 16)
    result = None
    while result is None:
        state, result = logic.tick(state)
    coffee = product(state, "coffee")
    assert coffee["on_counter"] == 0
    assert coffee["stock"] == 60 - result_sold(result, "coffee")


def result_sold(result, pid):
    return sum(line["sold"] for line in result["lines"] if line["product"] == pid)


# ---- Check 4: the card, the order hint and the order window show the total -----------------------

def function_body(name):
    match = re.search(rf"function {name}\(p\) {{(.*?)\n}}", UI, re.S)
    assert match, f"{name} is missing"
    return match.group(1)


def test_the_card_shows_storeroom_plus_counter():
    assert "p.stock + (p.on_counter ?? 0)" in function_body("held")
    row = function_body("stockRow")
    assert '<span class="units">${held(p)}</span>' in row
    assert "on the counter" in row and "(p.on_counter ?? 0) > 0" in row  # only when there is some


def test_the_dashboard_product_card_shows_the_same_total():
    assert '<strong>${p.stock + (p.on_counter ?? 0)}</strong><span>in stock</span>' in DASHBOARD


def test_the_rule_counts_the_counters_and_the_view_only_passes_it_on():
    state = logic.refill(logic.start_shift(logic.open_day(cafe_with_coffee()), "cafe"), "coffee", 7)
    assert logic.units_on_counter(state, "coffee") == 7 == product(state, "coffee")["on_counter"]
    assert logic.units_on_counter(logic.new_state(), "coffee") == 0


def test_the_dashboard_stock_tile_counts_the_counter_too():
    assert "sum + p.stock + (p.on_counter ?? 0)" in DASHBOARD
    assert 'unit${units === 1 ? "" : "s"} in stock`' in DASHBOARD
    assert "on the shelf" not in DASHBOARD


def test_the_order_hint_uses_the_same_total():
    assert "state.products.every((p) => held(p) === 0)" in UI


# ---- Check 5: no "+0" ----------------------------------------------------------------------------

def test_the_shift_panel_draws_no_plus_zero_button():
    assert '${step > 0 ? "" : "disabled"}>+${step}' not in UI  # the old disabled "+0"
    refill = re.search(r'\$\{step > 0 // no "\+0"(.*?)refill-none', UI, re.S)
    assert refill, "the +N button is drawn only when it can move something"
    assert '? `<button class="btn" type="button" data-refill="${esc(pid)}" data-qty="${step}">+${step}</button>`' in refill.group(1)
    assert '<span class="refill-none" aria-hidden="true"></span>' in UI  # the column stays
