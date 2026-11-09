"""Staff in every shop, not only in the Cafe (specs/staff.md)."""

import copy

import pytest

import logic


def run(state):
    result = None
    while result is None:
        state, result = logic.tick(state)
    return state, result


def two_shops(cafe_staff=True, beach_staff=True):
    """Cafe and Beach Cafe unlocked, stock in both storerooms, places bought (each buys its
    employee), plenty of cash."""
    state = logic.new_state()
    state["cash"] = 1_000_000
    state = logic.unlock_shop(state, "beach_cafe")
    state["stock"]["coffee"] = 60
    state["stock"]["beer"] = 60
    for shop, wanted in (("cafe", cafe_staff), ("beach_cafe", beach_staff)):
        if wanted:
            for item in ("staff_1", "staff_2"):
                state = logic.buy_upgrade(state, shop, item)
    return state


def test_every_shop_can_hire_and_buying_a_place_hires():
    state = two_shops()
    assert {e["shop"] for e in state["employees"]} == {"cafe", "beach_cafe"}
    assert logic.STAFF_SHOPS == tuple(logic.SHOPS)
    new = logic.fire_employee(state, 3)
    assert logic.hire(new, "beach_cafe", 1)["employees"][-1]["shop"] == "beach_cafe"


def test_locked_shops_and_unbought_places_stay_refused_and_change_nothing():
    state = logic.new_state()
    state["cash"] = 1_000_000
    before = copy.deepcopy(state)
    for shop in ("beach_cafe", "merchandise", "surf_shop"):
        with pytest.raises(logic.RejectedAction):
            logic.hire(state, shop, 1)
    unlocked = logic.unlock_shop(state, "surf_shop")
    with pytest.raises(logic.RejectedAction):
        logic.hire(unlocked, "surf_shop", 1)  # no place bought yet
    assert state == before


def test_two_staffed_shops_work_the_same_day():
    state = logic.open_day(two_shops())
    assert state["shift"]["shop"] == "cafe" and state["shift"]["staffed"]
    assert list(state["shift"]["extra"]) == ["beach_cafe"]
    state, result = run(state)
    assert result["shops"] == ["beach_cafe", "cafe"]
    sold = {line["product"]: line["sold"] for line in result["lines"]}
    assert sold["coffee"] > 0 and sold["beer"] > 0
    assert result["revenue"] == sum(line["revenue"] for line in result["lines"])
    assert result["wages"] > 0 and result["net"] == result["gross_profit"] - result["wages"]
    assert state["shift"] is None and state["day"] == 2


def test_the_other_shop_alone_leaves_the_players_shift_free():
    state = logic.open_day(two_shops(cafe_staff=False))
    assert state["shift"]["shop"] is None
    assert list(state["shift"]["extra"]) == ["beach_cafe"]
    state = logic.start_shift(state, "cafe")  # the player plays the Cafe, the crew goes on
    assert state["shift"]["shop"] == "cafe" and "beach_cafe" in state["shift"]["extra"]
    state, result = run(state)
    assert {line["product"] for line in result["lines"] if line["sold"]} == {"beer"}


def test_skip_sells_through_every_crew():
    state, result = logic.skip_shift(logic.open_day(two_shops(cafe_staff=False)))
    assert any(line["product"] == "beer" and line["sold"] > 0 for line in result["lines"])


def test_a_crew_uses_the_shared_stock_and_counter_units_return_to_it():
    state = logic.open_day(two_shops())
    stock_before = {p: state["stock"][p] for p in ("coffee", "beer")}
    state, result = run(state)
    for pid in ("coffee", "beer"):
        sold = next(line["sold"] for line in result["lines"] if line["product"] == pid)
        assert state["stock"][pid] == stock_before[pid] - sold  # the counter went back


def test_stock_value_counts_the_counter_of_every_crew():
    state = logic.open_day(two_shops())
    value = logic.stock_value(state)
    for _ in range(3):  # before the first customer arrives: nothing is sold, units only move
        state, _ = logic.tick(state)
    carried = sum(state["shift"]["extra"]["beach_cafe"]["counter"].values())
    assert carried > 0 and state["shift"]["sold"]["coffee"] == 0
    assert logic.stock_value(state) == value  # units on a counter still count

def test_hiring_later_on_the_open_day_starts_that_shops_crew():
    state = logic.open_day(two_shops(beach_staff=False))
    assert "extra" not in state["shift"]
    for item in ("staff_1", "staff_2"):
        state = logic.buy_upgrade(state, "beach_cafe", item)
    assert "beach_cafe" in state["shift"]["extra"]


def test_too_late_in_the_day_no_crew_starts_and_no_wage_is_due():
    state = logic.open_day(two_shops(cafe_staff=False, beach_staff=False))
    state["shift"]["tick"] = state["shift"]["day_end"] - logic.SHIFT_TICKS + 1
    for item in ("staff_1", "staff_2"):
        state = logic.buy_upgrade(state, "beach_cafe", item)
    assert "extra" not in state["shift"]
    cash = state["cash"]
    state, result = logic.skip_shift(state)
    assert result["wages"] == 0 and state["cash"] == cash


def test_the_same_state_gives_the_same_day_with_two_crews():
    assert run(logic.open_day(two_shops()))[1] == run(logic.open_day(two_shops()))[1]


def test_cash_never_goes_negative_with_several_crews():
    state = two_shops()
    state["cash"] = 1_000  # less than the wages of four employees
    state["stock"]["coffee"] = state["stock"]["beer"] = 0  # nothing to sell, no income
    state, result = run(logic.open_day(state))
    assert state["cash"] >= 0 and result["wages_unpaid"]


def test_a_single_shop_day_has_no_extra_key_and_lists_its_shop():
    state = logic.open_day(two_shops(beach_staff=False))
    assert "extra" not in state["shift"]
    assert run(state)[1]["shops"] == ["cafe"]
