"""Whole-day scenarios for specs/shop-process.md across all four shops and all products.

A shift can only start in the Cafe for now, so these runs widen SHIFT_SHOPS for the test.
A greedy player refills what is waited for and sells at once; each day is checked for
money, stock and customer bookkeeping."""

import pytest

import logic


@pytest.fixture(autouse=True)
def all_shops(monkeypatch):
    monkeypatch.setattr(logic, "SHIFT_SHOPS", tuple(logic.SHOPS))


def rich(cash=10_000_000):
    state = logic.new_state()
    state["cash"] = cash
    for sid, shop in logic.SHOPS.items():
        if not state["shops"][sid]["unlocked"]:
            state = logic.unlock_shop(state, sid)
        for item, offer in shop["window"].items():
            if offer["kind"] == "product":
                state = logic.buy_upgrade(state, sid, item)
    return state


def waiting_now(shift):
    waiting = {}
    for c in shift["queue"]:
        if c["arrives"] <= shift["tick"] < c["patience_until"]:
            waiting[c["product"]] = waiting.get(c["product"], 0) + 1
    return waiting


def play_day(state, shop):
    """Play one day with a greedy player and check the books. Returns (state, result)."""
    cash0, stock0 = state["cash"], dict(state["stock"])
    state = logic.start_shift(state, shop)
    planned = dict(state["shift"]["planned"])
    pids = list(state["shift"]["counter"])
    result = None
    while state["shift"]:
        waiting = waiting_now(state["shift"])
        for pid in pids:
            shift = state["shift"]
            if waiting.get(pid) and shift["counter"][pid] == 0 and state["stock"][pid] > 0:
                space = logic.SHOPS[shop]["counter"] - sum(shift["counter"].values())
                n = min(state["stock"][pid], space, waiting[pid] + 2)
                if n > 0:
                    state = logic.refill(state, pid, n)
            while state["shift"]["counter"][pid] > 0 and waiting.get(pid):
                state = logic.sell(state, pid)
                waiting[pid] -= 1
        state, result = logic.tick(state)
    revenue = sum(line["revenue"] for line in result["lines"])
    sold = {line["product"]: line["sold"] for line in result["lines"]}
    assert state["cash"] == cash0 + revenue
    assert all(isinstance(v, int) for v in (state["cash"], revenue, result["cogs"]))
    for pid in pids:
        assert state["stock"][pid] == stock0[pid] - sold[pid]
        assert sold[pid] <= planned[pid]
    assert result["lost"] + sum(sold.values()) == sum(planned.values())
    return state, result


@pytest.mark.parametrize("shop", list(logic.SHOPS))
def test_every_shop_sells_every_product_in_a_full_day(shop):
    state = rich()
    for pid in logic.shop_product_ids(shop):
        state["stock"][pid] = 30
    state, result = play_day(state, shop)
    assert [line["product"] for line in result["lines"]] == logic.shop_product_ids(shop)
    assert all(line["sold"] == line["demand"] == 10 for line in result["lines"])
    assert result["lost"] == 0 and result["shop"] == shop and state["day"] == 2


@pytest.mark.parametrize("shop", list(logic.SHOPS))
def test_a_day_without_stock_loses_every_customer(shop):
    state, result = play_day(rich(), shop)
    assert result["revenue"] == 0
    assert result["lost"] == sum(line["demand"] for line in result["lines"]) == 30


@pytest.mark.parametrize("factor, customers", [(1.0, 10), (1.5, 5), (3.0, 0)])
def test_the_price_decides_how_many_customers_come(factor, customers):
    state = rich()
    for pid in logic.CATALOGUE:
        state["stock"][pid] = 30
        state["prices"][pid] = int(logic.CATALOGUE[pid]["ref_price"] * factor)
    state, result = play_day(state, "beach_cafe")
    assert [line["demand"] for line in result["lines"]] == [customers] * 3
    assert [line["sold"] for line in result["lines"]] == [customers] * 3


def test_the_counter_limit_is_shared_by_all_products_of_a_shop():
    state = rich()
    for pid in logic.shop_product_ids("merchandise"):
        state["stock"][pid] = 50
    state = logic.start_shift(state, "merchandise")
    state = logic.refill(logic.refill(state, "hoodie", 12), "tshirt", 8)
    for pid in ("cap", "hoodie", "tshirt"):
        with pytest.raises(logic.RejectedAction):
            logic.refill(state, pid, 1)
    for pid in ("beer", "surfboard", "coffee"):  # products of other shops
        with pytest.raises(logic.RejectedAction):
            logic.refill(state, pid, 1)
    with pytest.raises(logic.RejectedAction):
        logic.start_shift(state, "cafe")


def test_a_whole_season_rotating_over_the_four_shops():
    state = rich(5_000_000)
    order = list(logic.SHOPS)
    day = 0
    while not logic.is_finished(state):
        shop = order[day % 4]
        day += 1
        for pid in logic.shop_product_ids(shop):
            if state["stock"][pid] < 10:
                state = logic.buy(state, pid, 8)
        state, _ = play_day(state, shop)
    assert len(state["history"]) == logic.LAST_DAY and state["day"] == logic.LAST_DAY + 1
    assert state["cash"] > 0
    for action in (lambda: logic.start_shift(state, "cafe"),
                   lambda: logic.sell(state, "coffee"),
                   lambda: logic.tick(state)):
        with pytest.raises(logic.RejectedAction):
            action()
