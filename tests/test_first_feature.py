"""Checks from specs/first-feature.md ("Done when"). One test per check."""

import pytest

import db
import logic


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "test.db"


def bought_ten_sandwiches():
    return logic.buy(logic.new_state(), "sandwich", 10)


# ---- Check 1: accepted purchase and trade (A1, A3) -----------------------

def test_buying_ten_sandwiches_costs_twenty_euro():
    state = bought_ten_sandwiches()
    assert state["cash"] == 8_000
    assert state["stock"]["sandwich"] == 10


def test_trading_one_day_reconciles():
    state = logic.set_price(bought_ten_sandwiches(), "sandwich", 400)
    state, result = logic.trade_day(state)
    assert result["revenue"] == 4_000
    assert result["cogs"] == 2_000
    assert result["gross_profit"] == 2_000
    assert state["cash"] == 12_000
    assert state["stock"]["sandwich"] == 0
    assert state["day"] == 2


# ---- Check 2: rejected actions leave data unchanged (A1, A2) -------------

def test_unaffordable_purchase_is_rejected_and_nothing_changes(db_path):
    state = bought_ten_sandwiches()
    db.save(state, db_path)
    with pytest.raises(logic.RejectedAction):
        logic.buy(state, "sandwich", 41)  # 41 × €2 = €82 > €80
    assert state["cash"] == 8_000
    assert state["stock"]["sandwich"] == 10
    assert db.load(db_path) == state


@pytest.mark.parametrize("price", [0, -100])
def test_zero_or_negative_price_is_rejected(price):
    state = logic.new_state()
    with pytest.raises(logic.RejectedAction):
        logic.set_price(state, "sandwich", price)
    assert state["prices"]["sandwich"] == 400


@pytest.mark.parametrize("quantity", [0, -1, 2.5])
def test_quantity_must_be_a_positive_whole_number(quantity):
    with pytest.raises(logic.RejectedAction):
        logic.buy(logic.new_state(), "sandwich", quantity)


# ---- Check 3: restart restores the run without replay (A5) ---------------

def test_restart_restores_state_with_one_history_record(db_path):
    state = logic.set_price(bought_ten_sandwiches(), "sandwich", 400)
    state, _ = logic.trade_day(state)
    db.save(state, db_path)

    reopened = db.load(db_path)  # simulates stopping and reopening the app
    assert reopened["cash"] == 12_000
    assert reopened["stock"]["sandwich"] == 0
    assert reopened["day"] == 2
    assert reopened["prices"]["sandwich"] == 400
    assert len(reopened["history"]) == 1

    db.save(reopened, db_path)  # saving again must not duplicate day 1
    assert len(db.load(db_path)["history"]) == 1


# ---- Check 4: boundaries (A2, A4) ----------------------------------------

@pytest.mark.parametrize("price, expected", [(400, 10), (401, 5), (800, 5), (801, 0)])
def test_demand_boundaries(price, expected):
    assert logic.demand(price, 400) == expected


def test_stock_limits_sales():
    state = logic.buy(logic.new_state(), "sandwich", 3)
    state, result = logic.trade_day(state)
    sandwich = next(l for l in result["lines"] if l["product"] == "sandwich")
    assert sandwich["sold"] == 3
    assert state["stock"]["sandwich"] == 0

    state, result = logic.trade_day(state)  # zero stock sells zero
    sandwich = next(l for l in result["lines"] if l["product"] == "sandwich")
    assert sandwich["sold"] == 0
    assert state["stock"]["sandwich"] == 0


def test_more_than_two_decimals_is_rejected():
    assert logic.euros_to_cents("4,01") == 401
    with pytest.raises(logic.RejectedAction):
        logic.euros_to_cents("4.001")
