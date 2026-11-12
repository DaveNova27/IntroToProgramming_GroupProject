"""Checks from specs/shift-any-shop.md: the player can take a shift in any unlocked shop, one
shift at a time and one per shop and day. New file; no old test is touched here."""

import copy

import pytest

import app
import db
import logic


def run(state):
    result = None
    while result is None:
        state, result = logic.tick(state)
    return state, result


def advance(state, ticks):
    for _ in range(ticks):
        state, result = logic.tick(state)
        assert result is None
    return state


def shops(beach_staff=False, cafe_staff=False):
    """Cafe and Beach Cafe unlocked, stock for both, plenty of cash."""
    state = logic.new_state()
    state["cash"] = 1_000_000
    state = logic.unlock_shop(state, "beach_cafe")
    state["stock"]["coffee"] = 60
    state["stock"]["beer"] = 60
    for shop, wanted in (("cafe", cafe_staff), ("beach_cafe", beach_staff)):
        if wanted:
            state = logic.buy_upgrade(logic.buy_upgrade(state, shop, "staff_1"), shop, "staff_2")
    return state


def refused(action, state):
    before = copy.deepcopy(state)
    with pytest.raises(logic.RejectedAction):
        action(state)
    assert state == before  # a rejected action changes nothing


def test_the_player_works_a_shop_without_an_employee():
    state = logic.start_shift(logic.open_day(shops()), "beach_cafe")
    assert state["shift"]["shop"] == "beach_cafe" and not state["shift"].get("staffed")
    assert sum(state["shift"]["planned"].values()) > 0  # its customers come: it plans its guests alone
    state = advance(state, 10)
    state = logic.refill(state, "beer", 10)
    state = logic.sell(advance(state, 8), "beer")
    state, result = run(state)
    assert any(line["product"] == "beer" and line["sold"] > 0 for line in result["lines"])
    assert result["played"] is True and "beach_cafe" in result["shops"]


def test_a_locked_shop_and_bad_ids_are_refused_and_change_nothing():
    state = logic.open_day(shops())
    for bad in ("surf_shop", "nowhere", None, 5, ["cafe"], {"a": 1}, True):
        refused(lambda s, b=bad: logic.start_shift(s, b), state)


def test_one_shift_at_a_time_and_one_per_shop_and_day():
    state = logic.start_shift(logic.open_day(shops()), "cafe")
    refused(lambda s: logic.start_shift(s, "beach_cafe"), state)  # the first one still runs
    refused(lambda s: logic.start_shift(s, "cafe"), state)
    state = advance(state, logic.SHIFT_TICKS)  # the Cafe shift is over
    assert state["shift"]["over"]
    refused(lambda s: logic.start_shift(s, "cafe"), state)  # not twice in the same shop
    state = logic.start_shift(state, "beach_cafe")
    assert state["shift"]["shop"] == "beach_cafe" and "cafe" in state["shift"]["extra"]
    assert state["shift"]["tick"] == logic.SHIFT_TICKS and state["shift"]["shift_end"] == 2 * logic.SHIFT_TICKS


def test_the_day_adds_up_over_two_shifts_and_the_first_one_is_booked():
    state = logic.start_shift(logic.open_day(shops()), "cafe")
    state = logic.refill(advance(state, 10), "coffee", 20)
    state = logic.sell(advance(state, 8), "coffee")
    cafe_sold = sum(state["shift"]["sold"].values())
    assert cafe_sold > 0
    state = logic.start_shift(advance(state, logic.SHIFT_TICKS), "beach_cafe")
    assert sum(state["shift"]["extra"]["cafe"]["sold"].values()) == cafe_sold  # kept beside the new shift
    state = logic.refill(advance(state, 5), "beer", 10)
    state = logic.sell(advance(state, 8), "beer")
    state, result = run(state)
    sold = {line["product"]: line["sold"] for line in result["lines"]}
    assert sold["coffee"] >= cafe_sold and sold["beer"] > 0
    assert sorted(result["shops"]) == ["beach_cafe", "cafe"] and result["played"] is True


def test_a_shift_must_still_fit_into_the_day():
    state = logic.open_day(shops())
    state = advance(state, logic.OPEN_DAY_TICKS - logic.SHIFT_TICKS + 1)
    refused(lambda s: logic.start_shift(s, "beach_cafe"), state)
    state = advance(logic.open_day(shops()), logic.OPEN_DAY_TICKS - logic.SHIFT_TICKS)
    assert logic.start_shift(state, "beach_cafe")["shift"]["shop"] == "beach_cafe"


def test_a_staffed_shift_holding_the_slot_moves_aside_and_goes_on():
    state = logic.open_day(shops(cafe_staff=True))
    assert state["shift"]["shop"] == "cafe" and state["shift"]["staffed"]
    state = logic.start_shift(state, "beach_cafe")  # the player works where nobody does
    assert state["shift"]["shop"] == "beach_cafe" and not state["shift"].get("staffed")
    crew = state["shift"]["extra"]["cafe"]
    assert crew["staffed"] and "guest_plan" not in crew
    assert "guest_plan" in state["shift"]  # the day's plan stays the day's
    state, result = run(state)
    assert any(line["product"] == "coffee" and line["sold"] > 0 for line in result["lines"])  # the crew sold


def test_the_player_can_take_over_a_staffed_shop():
    state = logic.open_day(shops(beach_staff=True))
    assert "beach_cafe" in state["shift"]["extra"] and state["shift"]["shop"] is None
    state = logic.start_shift(state, "beach_cafe")
    assert state["shift"]["shop"] == "beach_cafe" and state["shift"]["staffed"]  # the crew stays
    assert "beach_cafe" not in state.get("shift", {}).get("extra", {})
    assert state["shift"]["shift_end"] == logic.SHIFT_TICKS  # the same shift, not a new one
    state, result = run(state)
    assert result["played"] is False  # staff did the work, as in the Cafe today


def test_the_options_tell_where_the_player_can_work_and_why_not():
    state = logic.open_day(shops())
    options = {o["shop"]: o for o in logic.shift_options(state)}
    assert set(options) == {"cafe", "beach_cafe"} and all(o["can"] for o in options.values())
    state = logic.start_shift(state, "cafe")
    options = {o["shop"]: o for o in logic.shift_options(state)}
    assert not options["beach_cafe"]["can"] and "already running" in options["beach_cafe"]["why"]
    assert not options["cafe"]["can"]


def test_hints_say_that_the_player_can_work_there():
    state = logic.unlock_shop({**logic.new_state(), "cash": 100_000}, "beach_cafe")
    assert "take a shift here yourself" in logic.shop_hint(state, "beach_cafe")
    assert logic.shop_hint(logic.new_state(), "beach_cafe") is None  # locked: nothing to say yet
    assert logic.shop_hint(shops(beach_staff=True), "beach_cafe") is None


def test_stock_in_a_shop_without_staff_is_not_a_dead_end():
    state = shops()
    state["cash"], state["stock"]["coffee"], state["stock"]["beer"] = 0, 0, 50
    assert not logic.dead_end(state)  # the player can sell the beer in the Beach Cafe


def test_the_api_start_and_the_choices(tmp_path, monkeypatch):
    path = tmp_path / "run.db"
    db.save(logic.open_day(shops()), path)
    real_save = db.save
    monkeypatch.setattr(app, "load_run", lambda: db.load(path))
    monkeypatch.setattr(app.db, "save", lambda state: real_save(state, path))
    client = app.app.test_client()
    shift = client.get("/api/state").get_json()["shift"]
    assert [c["shop"] for c in shift["choices"] if c["can"]] == ["cafe", "beach_cafe"]
    answer = client.post("/api/shift/start", json={"shop": "beach_cafe"}).get_json()
    assert answer["state"]["shift"]["shop"] == "beach_cafe"
    assert client.post("/api/shift/start", json={"shop": "cafe"}).get_json()["error"]
    assert client.post("/api/shift/start", json={"shop": "surf_shop"}).get_json()["error"]
