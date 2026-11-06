"""Skipping a shift: the time passes, nobody is served (specs/shop-process.md, Time)."""

import copy

import pytest

import app
import db
import logic


def started(coffee=30):
    state = logic.new_state()
    state["stock"]["coffee"] = coffee
    return logic.start_shift(state, "cafe")


def test_skipping_without_working_earns_nothing():
    state = logic.refill(started(), "coffee", 10)
    cash = state["cash"]
    state, result = logic.skip_shift(state)
    assert state["shift"] is None and state["day"] == 2
    assert result["revenue"] == 0 and result["gross_profit"] == 0 and state["cash"] == cash
    assert state["history"] == [result] and state["stock"]["coffee"] == 30


def test_skipping_keeps_what_was_sold_before():
    state = logic.sell(logic.refill(started(), "coffee", 10), "coffee")
    state, result = logic.skip_shift(state)
    assert result["revenue"] == 200 and result["lost"] == 9


def test_skip_is_refused_without_a_shift_and_after_the_last_day():
    for state in (logic.new_state(), {**started(), "day": logic.LAST_DAY + 1}):
        before = copy.deepcopy(state)
        with pytest.raises(logic.RejectedAction):
            logic.skip_shift(state)
        assert state == before


def test_trade_day_is_still_refused_during_a_shift():
    with pytest.raises(logic.RejectedAction):
        logic.trade_day(started())


def test_the_api_skips_the_day_and_a_second_skip_is_refused(tmp_path, monkeypatch):
    path = tmp_path / "run.db"
    db.save(logic.new_state(), path)
    real_save = db.save
    monkeypatch.setattr(app, "load_run", lambda: db.load(path))
    monkeypatch.setattr(app.db, "save", lambda state: real_save(state, path))
    client = app.app.test_client()
    assert client.post("/api/shift/skip").status_code == 400
    client.post("/api/shift/start", json={"shop": "cafe"})
    cash = db.load(path)["cash"]
    assert client.post("/api/shift/skip").status_code == 200
    saved = db.load(path)
    assert saved["shift"] is None and saved["day"] == 2 and saved["cash"] == cash
    assert client.post("/api/shift/skip").status_code == 400
    assert db.load(path) == saved


# ---- the day is opened first, the shift starts while it runs ----------------

def opened(coffee=30):
    state = logic.new_state()
    state["stock"]["coffee"] = coffee
    return logic.open_day(state)


def refused(action, state):
    before = copy.deepcopy(state)
    with pytest.raises(logic.RejectedAction):
        action(state)
    assert state == before


def test_an_open_day_has_a_clock_but_nobody_serving():
    state = opened()
    assert state["shift"]["shop"] is None and state["shift"]["tick"] == 0
    refused(lambda s: logic.refill(s, "coffee", 1), state)
    refused(lambda s: logic.sell(s, "coffee"), state)
    refused(lambda s: logic.open_day(s), state)
    refused(lambda s: logic.trade_day(s), state)
    refused(lambda s: logic.set_price(s, "coffee", 300), state)


def test_a_day_nobody_works_in_earns_nothing():
    state, result = logic.skip_shift(opened())
    assert state["day"] == 2 and state["shift"] is None
    assert result["revenue"] == 0 and result["lines"] == [] and state["cash"] == 10000


def ticks(state, n):
    for _ in range(n):
        state, result = logic.tick(state)
    return state, result


def test_the_shift_clock_starts_with_the_shift_not_with_the_day():
    state, _ = ticks(opened(), 40)
    state = logic.start_shift(state, "cafe")
    shift = state["shift"]
    assert shift["shop"] == "cafe" and shift["tick"] == 40
    assert shift["shift_end"] == 40 + logic.SHIFT_TICKS
    assert [c["arrives"] for c in shift["queue"]][:2] == [40, 49]  # customers come after the start
    refused(lambda s: logic.start_shift(s, "cafe"), state)


def test_when_the_shift_ends_the_day_goes_on_and_the_sales_stay_booked():
    state, _ = ticks(opened(), 40)
    state = logic.sell(logic.refill(logic.start_shift(state, "cafe"), "coffee", 10), "coffee")
    state, result = ticks(state, logic.SHIFT_TICKS)
    assert result is None and state["shift"] is not None and state["shift"]["over"]
    assert state["stock"]["coffee"] == 29  # the unsold counter units are back in the storeroom
    assert state["shift"]["sold"]["coffee"] == 1 and state["shift"]["queue"] == []
    refused(lambda s: logic.sell(s, "coffee"), state)
    refused(lambda s: logic.refill(s, "coffee", 1), state)
    refused(lambda s: logic.start_shift(s, "cafe"), state)  # one shift per day
    state, result = logic.skip_shift(state)  # the day ends later, at its own end
    assert state["day"] == 2 and result["revenue"] == 200 and state["shift"] is None


def test_an_opened_day_closes_at_its_own_end():
    state, result = ticks(opened(), logic.OPEN_DAY_TICKS - 1)
    assert result is None and state["shift"] is not None
    state, result = logic.tick(state)
    assert result is not None and state["day"] == 2


def test_the_api_opens_the_day_then_the_shift_then_skips(tmp_path, monkeypatch):
    path = tmp_path / "run.db"
    db.save(logic.new_state(), path)
    real_save = db.save
    monkeypatch.setattr(app, "load_run", lambda: db.load(path))
    monkeypatch.setattr(app.db, "save", lambda state: real_save(state, path))
    client = app.app.test_client()
    assert client.post("/api/day/open").status_code == 200
    assert client.post("/api/day/open").status_code == 400
    assert client.post("/api/shift/sell", json={"product": "coffee"}).status_code == 400
    assert client.post("/api/shift/start", json={"shop": "cafe"}).status_code == 200
    state = client.get("/api/state").get_json()
    assert state["shift"]["shop"] == "cafe"
    assert client.post("/api/shift/skip").status_code == 200
    assert db.load(path)["day"] == 2
