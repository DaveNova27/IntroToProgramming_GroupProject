"""Checks from specs/stock-overview.md ("Done when"). One test per check."""

import copy

import logic


def example_state():
    """12 Sandwiches at €4, 3 Coffees at €5 (above 2x reference), no Cookies."""
    state = logic.buy(logic.new_state(), "sandwich", 12)
    state = logic.buy(state, "coffee", 3)
    return logic.set_price(state, "coffee", 500)


def line(overview, product):
    return next(l for l in overview["lines"] if l["product"] == product)


# ---- Check 1: the overview shows the right numbers (CT R1, CT R2, CT R4) --

def test_overview_shows_units_value_and_todays_sales():
    state = example_state()
    overview = logic.stock_overview(state)

    sandwich = line(overview, "sandwich")
    assert sandwich == {"product": "sandwich", "units": 12, "value": 2_400,
                        "sells_today": 10, "left_after_today": 2}
    coffee = line(overview, "coffee")
    assert coffee == {"product": "coffee", "units": 3, "value": 240,
                      "sells_today": 0, "left_after_today": 3}
    cookie = line(overview, "cookie")
    assert cookie == {"product": "cookie", "units": 0, "value": 0,
                      "sells_today": 0, "left_after_today": 0}

    assert overview["units"] == 15
    assert overview["value"] == 2_640
    assert overview["value"] == logic.stock_value(state)


# ---- Check 2: the overview only reads the run ----------------------------

def test_overview_leaves_the_run_unchanged():
    state = example_state()
    before = copy.deepcopy(state)
    logic.stock_overview(state)
    assert state == before


# ---- Check 3: stock limits what sells today (CT R2) ----------------------

def test_stock_limits_todays_sales():
    state = logic.buy(logic.new_state(), "sandwich", 3)
    sandwich = line(logic.stock_overview(state), "sandwich")
    assert sandwich["sells_today"] == 3
    assert sandwich["left_after_today"] == 0


# ---- Check 4: nothing sells after day 5 -----------------------------------

def test_nothing_sells_on_a_complete_run():
    # Cookies at the reference price sell 10 a day. Buy 10 before every day and
    # 20 before the last one: 10 are left after the last day, and at this price
    # they would sell on an open run.
    state = logic.new_state()
    for day in range(1, logic.LAST_DAY + 1):
        state = logic.buy(state, "cookie", 20 if day == logic.LAST_DAY else 10)
        state, _ = logic.trade_day(state)
    assert logic.is_finished(state)

    overview = logic.stock_overview(state)
    for l in overview["lines"]:
        assert l["sells_today"] == 0
        assert l["left_after_today"] == l["units"]
    assert line(overview, "cookie")["units"] == 10
