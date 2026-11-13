"""Checks from specs/balance-pass.md. The season guard bands are wide on purpose and will move when
popularity, events or the staff numbers change the sales: whoever changes them confirms it with the
owner (AGENTS.md). The season is balanced, the dead end warns, the hint and the
storeroom limit. The simulation plays whole seasons with the real rules on fixed seeds."""

import collections

import pytest

import app
import logic

# ---- the tables: no shop earns far more than another ----------------------------------------


def best_profit_per_day(shop):
    """What a full shop (all its products) earns on a neutral day at its best prices, in cents."""
    mix, total = logic.SHOP_MIX[shop], 0
    for pid in logic.shop_product_ids(shop):
        ref, cost = logic.CATALOGUE[pid]["ref_price"], logic.CATALOGUE[pid]["cost"]
        total += max(logic.customers_for(p, ref, mix) * (p - cost) for p in range(cost + 1, 3 * ref))
    return total


def test_no_shop_earns_far_more_than_the_others_on_a_day():
    profit = {shop: best_profit_per_day(shop) for shop in logic.SHOPS}
    assert max(profit.values()) <= 5 * min(profit.values()), profit  # before: 1,376 against 60 euro
    assert max(profit.values()) <= 0.5 * sum(profit.values()), profit  # no shop makes half of it


# ---- a whole season ----------------------------------------------------------------------------

SEEDS = (1, 2)
CAFE_PLAN = [("up", "cafe", "cake"), ("up", "cafe", "bagel")]


def shop_plan(shop):
    window = logic.SHOPS[shop]["window"]
    return ([("unlock", shop), ("up", shop, "staff_1")]
            + [("up", shop, item) for item, offer in window.items() if offer["kind"] == "product"])


def best_price(state, pid):
    """The price (5 % steps of the reference) with the best profit for today's customers."""
    item, shop = logic.CATALOGUE[pid], logic.shop_of_product(pid)
    percents = logic.segment_percents(state, shop)
    return max((item["ref_price"] * pct // 100 for pct in range(50, 251, 5)),
               key=lambda p: logic.customers_for(p, item["ref_price"], logic.SHOP_MIX[shop], percents)
               * (p - item["cost"]))


def sold_products(state):
    """The products of the shops that sell today: the Cafe (the player serves it) and every shop
    with a working employee."""
    return [pid for sid, shop in state["shops"].items() if shop["unlocked"]
            and (sid in logic.SHIFT_SHOPS or any(e["shop"] == sid and e["working"] for e in state["employees"]))
            for pid in shop["products"]]


def stock_needed(state):
    """Cents the stock for today's customers would cost."""
    return sum(max(0, logic.customers_today(state, pid) - state["stock"][pid]) * logic.CATALOGUE[pid]["cost"]
               for pid in sold_products(state))


def play_season(seed, plan):
    """A player who serves the Cafe without a mistake, sets the best price every morning, buys the
    next step of the plan when the cash still pays the stock of the day, and then the stock the
    customers of the day will want. Returns the final state and the gross profit per shop."""
    state, todo, profit = logic.new_state(seed), list(plan), collections.Counter()
    while not logic.is_finished(state):
        while todo:
            step = todo[0]
            try:
                after = (logic.unlock_shop(state, step[1]) if step[0] == "unlock"
                         else logic.buy_upgrade(state, step[1], step[2]))
            except logic.RejectedAction:
                break
            if after["cash"] < stock_needed(after):
                break
            state = after
            todo.pop(0)
        for pid in logic.owned_products(state):
            state = logic.set_price(state, pid, best_price(state, pid))
        by_margin = sorted(sold_products(state), key=lambda pid: -(state["prices"][pid] - logic.CATALOGUE[pid]["cost"])
                           / logic.CATALOGUE[pid]["cost"])
        for pid in by_margin:
            want = min(logic.customers_today(state, pid) - state["stock"][pid],
                       state["cash"] // logic.CATALOGUE[pid]["cost"])
            while want > 0:
                try:
                    state = logic.buy(state, pid, want)
                    break
                except logic.RejectedAction:
                    want -= 1
        state = logic.open_day(state)
        if state["shift"]["shop"] is None:
            state = logic.start_shift(state, "cafe")
        result = None
        while result is None:
            shift = state["shift"]
            if shift["shop"] and not shift["over"]:
                for pid in shift["counter"]:
                    shift = state["shift"]  # the counter changes with every refill and sale
                    waiting = sum(1 for c in shift["queue"] if c["product"] == pid)
                    space = logic.SHOPS[shift["shop"]]["counter"] - sum(shift["counter"].values())
                    need = min(waiting - shift["counter"][pid], state["stock"][pid], space)
                    if need > 0:
                        state = logic.refill(state, pid, need)
                    while True:
                        try:
                            state = logic.sell(state, pid)
                        except logic.RejectedAction:
                            break
                state, result = logic.tick(state)
            else:
                state, result = logic.skip_shift(state)
        for line in result["lines"]:
            profit[logic.shop_of_product(line["product"])] += line["gross_profit"]
    return state, profit


@pytest.fixture(scope="module")
def seasons():
    """Cafe only, and the Cafe followed by every other shop (the best order: the Surf Shop first)."""
    every_shop = CAFE_PLAN + shop_plan("surf_shop") + shop_plan("merchandise") + shop_plan("beach_cafe")
    return {
        "cafe": [play_season(seed, CAFE_PLAN) for seed in SEEDS],
        "all": [play_season(seed, every_shop) for seed in SEEDS],
    }


def mean_gain(runs):
    return sum(logic.overall_gain(state) for state, _ in runs) / len(runs) / 100


def test_a_good_season_ends_between_3000_and_8000_euro(seasons):
    gain = mean_gain(seasons["all"])
    assert 3_000 <= gain <= 8_000, gain  # before: about 25,000
    assert gain >= 2 * mean_gain(seasons["cafe"])  # more shops are worth it


def test_the_cafe_alone_still_earns_something_but_less(seasons):
    assert 800 <= mean_gain(seasons["cafe"]) <= 2_500


def test_no_shop_makes_half_of_the_profit(seasons):
    for _, profit in seasons["all"]:
        total = sum(profit.values())
        assert all(v <= 0.5 * total for v in profit.values()), dict(profit)


def test_the_first_days_stay_tight(seasons):
    for state, _ in seasons["all"]:
        assert state["history"][9]["cash_after"] < 100_000  # under 1,000 euro on day 10


# ---- the dead end (B2): a warning, never a refusal ------------------------------------------------


def poor_state():
    state = logic.new_state(1)
    state["cash"] = 10_000  # the 100 euro start
    return state


def test_a_purchase_that_leaves_nothing_to_buy_warns_but_is_allowed():
    state = poor_state()
    # the cake (40 euro) and then the first employee place (60 euro) leave 0 cash and no stock
    state = logic.buy_upgrade(state, "cafe", "cake")
    offers = {o["id"]: o for o in logic.shop_offers(state, "cafe")}
    assert offers["staff_1"]["warning"] is not None and "nothing in stock" in offers["staff_1"]["warning"]
    assert offers["bagel"]["warning"] is None  # 30 euro: 30 left, coffee costs 0.80
    after = logic.buy_upgrade(state, "cafe", "staff_1")  # allowed
    assert after["cash"] == 0 and logic.dead_end(after)


def test_no_warning_with_stock_or_cash_left():
    state = poor_state()
    assert all(o["warning"] is None for o in logic.shop_offers(state, "cafe"))
    state["stock"]["coffee"] = 5
    state["cash"] = 6_000
    assert {o["id"]: o for o in logic.shop_offers(state, "cafe")}["staff_1"]["warning"] is None


def test_the_unlock_of_a_shop_warns_when_it_leaves_nothing():
    state = poor_state()
    state["cash"] = 20_000
    assert logic.purchase_warning(state, "beach_cafe") is not None  # 0 left, no stock
    state["cash"] = 20_050  # 50 cent left: the cheapest product the player owns (coffee) costs 80
    assert logic.purchase_warning(state, "beach_cafe") is not None
    state["cash"] = 20_100  # 1 euro buys a coffee: no dead end
    assert logic.purchase_warning(state, "beach_cafe") is None
    state["cash"] = 21_000
    assert logic.purchase_warning(state, "beach_cafe") is None


def test_the_warning_changes_nothing_and_reaches_the_screen():
    state = poor_state()
    state = logic.buy_upgrade(state, "cafe", "cake")
    before = repr(state)
    view = app.view(state)
    assert repr(state) == before
    cafe = next(s for s in view["shops"] if s["id"] == "cafe")
    assert any(o["warning"] for o in cafe["offers"])
    assert all("unlock_warning" in s and "hint" in s for s in view["shops"])


# ---- the trap (B3): a hint for a shop the player cannot play -------------------------------------------


def test_a_shop_without_an_employee_says_the_player_can_take_the_shift_until_it_has_one():
    state = logic.new_state(1)
    state["cash"] = 100_000
    assert logic.shop_hint(state, "cafe") is None  # the player plays the Cafe
    assert logic.shop_hint(state, "beach_cafe") is None  # locked: nothing to say yet
    state = logic.unlock_shop(state, "beach_cafe")
    assert "take a shift here yourself" in logic.shop_hint(state, "beach_cafe")
    state = logic.buy_upgrade(state, "beach_cafe", "staff_1")
    assert logic.shop_hint(state, "beach_cafe") is None


# ---- the storeroom limit (B4) ------------------------------------------------------------------------------


def test_units_on_the_counter_count_against_the_storeroom():
    state = logic.new_state(1)
    state["cash"] = 1_000_000
    state = logic.buy(state, "coffee", 100)
    state = logic.start_shift(logic.open_day(state), "cafe")
    state = logic.refill(state, "coffee", 20)  # 80 in the storeroom, 20 on the counter
    with pytest.raises(logic.RejectedAction):
        logic.buy(state, "coffee", 1)  # 80 + 20 on the counter + 1 > 100
    after, _ = logic.skip_shift(state)
    assert after["stock"]["coffee"] == 100  # the counter goes back: 100 in all, the limit holds


def test_stock_in_a_shop_without_an_employee_is_no_dead_end_because_the_player_can_sell_it():
    state = logic.new_state(1)
    state["cash"] = 100_000
    state = logic.unlock_shop(state, "beach_cafe")
    state = logic.buy(state, "beer", 50)  # the Beach Cafe has no employee, the player takes the shift
    state["cash"], state["stock"]["coffee"] = 0, 0
    assert not logic.dead_end(state)
    state["stock"]["beer"] = 0
    assert logic.dead_end(state)  # nothing left to sell and no cash for more


def test_the_hint_tells_a_stopped_employee_from_a_missing_place():
    state = logic.new_state(1)
    state["cash"] = 100_000
    state = logic.buy_upgrade(logic.unlock_shop(state, "beach_cafe"), "beach_cafe", "staff_1")
    state["employees"][0]["working"] = False  # no money for the wage
    assert "Nobody works" in logic.shop_hint(state, "beach_cafe")
    unlocked = logic.unlock_shop({**logic.new_state(1), "cash": 100_000}, "beach_cafe")
    assert "buy an employee place" in logic.shop_hint(unlocked, "beach_cafe")


def test_a_save_with_an_old_absurd_price_starts_at_the_reference_price(tmp_path):
    import db
    path = tmp_path / "old.db"
    state = logic.new_state(1)
    state["prices"]["surfboard"] = 9_000  # the reference price before this spec
    state["prices"]["coffee"] = 250
    db.save(state, path)
    loaded = db.load(path)
    assert loaded["prices"]["surfboard"] == logic.CATALOGUE["surfboard"]["ref_price"]
    assert loaded["prices"]["coffee"] == 250


def test_wages_due_do_not_make_a_dead_end_the_player_earns_them_back():
    state = logic.new_state(1)
    state["cash"] = 100_000
    state = logic.buy_upgrade(state, "cafe", "staff_1")  # an employee, wage 8 euro a day
    state["cash"] = 200  # 2 euro: less than the wage, but enough for stock
    assert not logic.dead_end(state) and logic.purchase_warning(state, "cafe", "bagel") is None
    state = logic.buy(state, "coffee", 2)
    state = logic.open_day(state)
    state, _ = logic.skip_shift(state)  # the employee sells, the wage may not be paid in full
    assert state["cash"] > 0 or any(h["revenue"] > 0 for h in state["history"])  # money came in
    assert not logic.dead_end({**state, "cash": state["cash"] + 100})
