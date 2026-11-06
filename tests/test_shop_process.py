"""Checks from specs/shop-process.md ("Done when"). One test per check."""

import copy

import pytest

import app
import db
import logic


@pytest.fixture
def run_on_disk(tmp_path, monkeypatch):
    """The real API on a temporary save, so the player's own run stays untouched."""
    path = tmp_path / "run.db"
    db.save(logic.new_state(), path)
    real_save = db.save
    monkeypatch.setattr(app, "load_run", lambda: db.load(path))
    monkeypatch.setattr(app.db, "save", lambda state: real_save(state, path))
    return path


def stocked(coffee=30):
    state = logic.new_state()
    state["stock"]["coffee"] = coffee
    return state


def started(coffee=30):
    return logic.start_shift(stocked(coffee), "cafe")


def refused(action, state):
    """The action must be refused and must leave the given state untouched."""
    before = copy.deepcopy(state)
    with pytest.raises(logic.RejectedAction):
        action(state)
    assert state == before


def run_ticks(state, n):
    for _ in range(n):
        state, _ = logic.tick(state)
    return state


# ---- Check 1: where a shift can start -------------------------------------

def test_a_shift_starts_in_the_cafe_with_an_even_queue_and_an_empty_counter():
    state = started()
    shift = state["shift"]
    assert shift["shop"] == "cafe" and shift["tick"] == 0
    assert shift["counter"] == {"coffee": 0}
    assert len(shift["queue"]) == logic.customers_for(200, 200) == 10
    assert [c["arrives"] for c in shift["queue"]] == [i * 9 for i in range(10)]
    assert all(c["patience_until"] - c["arrives"] == logic.PATIENCE_TICKS for c in shift["queue"])


def test_the_queue_is_the_same_every_time_no_randomness():
    assert started()["shift"] == started()["shift"]


def test_other_shops_unknown_ids_and_a_second_shift_are_refused():
    state = stocked()
    state["cash"] = 1_000_000
    state = logic.unlock_shop(state, "beach_cafe")
    refused(lambda s: logic.start_shift(s, "beach_cafe"), state)
    for bad in ("nowhere", None, 5, ["cafe"], {"a": 1}, True):
        refused(lambda s, b=bad: logic.start_shift(s, b), state)
    running = logic.start_shift(state, "cafe")
    refused(lambda s: logic.start_shift(s, "cafe"), running)


# ---- Check 2: refill and sell ---------------------------------------------

def test_refill_moves_units_from_the_storeroom_to_the_counter():
    state = logic.refill(started(30), "coffee", 12)
    assert state["stock"]["coffee"] == 18
    assert state["shift"]["counter"]["coffee"] == 12


def test_selling_takes_one_unit_and_pays_the_price_in_cents():
    state = logic.refill(started(30), "coffee", 5)
    cash = state["cash"]
    state = logic.sell(state, "coffee")  # the first customer waits at tick 0
    assert state["cash"] == cash + 200 and isinstance(state["cash"], int)
    assert state["shift"]["counter"]["coffee"] == 4
    assert state["shift"]["sold"]["coffee"] == 1
    assert len(state["shift"]["queue"]) == 9


def test_the_counter_never_holds_more_than_its_space():
    state = logic.refill(started(50), "coffee", 20)
    refused(lambda s: logic.refill(s, "coffee", 1), state)
    assert sum(state["shift"]["counter"].values()) == logic.COUNTER_UNITS


# ---- Check 3: refused actions change nothing ------------------------------

@pytest.mark.parametrize("bad", [0, -3, 2.0, "5", None, True, [1]])
def test_bad_quantities_are_refused(bad):
    refused(lambda s: logic.refill(s, "coffee", bad), started())


def test_refill_beyond_the_storeroom_or_for_a_wrong_product_is_refused():
    state = started(5)
    refused(lambda s: logic.refill(s, "coffee", 6), state)
    for bad in ("beer", "cake", "nothing", None, 3, ["coffee"]):
        refused(lambda s, b=bad: logic.refill(s, b, 1), state)  # cake: not owned yet


def test_selling_what_is_not_on_the_counter_or_without_a_customer_is_refused():
    state = started()
    refused(lambda s: logic.sell(s, "coffee"), state)  # nothing on the counter
    state = logic.refill(state, "coffee", 20)
    for bad in ("beer", None, 7, ["coffee"]):
        refused(lambda s, b=bad: logic.sell(s, b), state)
    state = logic.sell(state, "coffee")  # tick 0: the only customer is served
    refused(lambda s: logic.sell(s, "coffee"), state)  # nobody else waits yet


def test_actions_without_a_shift_and_trade_day_during_a_shift_are_refused():
    state = stocked()
    refused(lambda s: logic.refill(s, "coffee", 1), state)
    refused(lambda s: logic.sell(s, "coffee"), state)
    refused(logic.tick, state)
    running = logic.start_shift(state, "cafe")
    refused(logic.trade_day, running)
    refused(lambda s: logic.set_price(s, "coffee", 300), running)


def test_nothing_works_after_the_last_day():
    state = stocked()
    state["day"] = logic.LAST_DAY + 1
    refused(lambda s: logic.start_shift(s, "cafe"), state)
    state["shift"] = started()["shift"]  # a crafted state with a shift left over
    refused(lambda s: logic.refill(s, "coffee", 1), state)
    refused(lambda s: logic.sell(s, "coffee"), state)
    refused(logic.tick, state)


# ---- Check 4: crafted requests -------------------------------------------

def test_a_crafted_run_of_sales_cannot_sell_more_than_the_counter_holds():
    state = logic.refill(started(30), "coffee", 3)
    sold = 0
    for t in range(logic.DAY_TICKS - 1):
        while True:
            try:
                state = logic.sell(state, "coffee")
                sold += 1
            except logic.RejectedAction:
                break
        state, result = logic.tick(state)
    assert sold == 3 and state["shift"]["sold"]["coffee"] == 3


def test_a_sale_after_the_day_ended_is_refused():
    state = logic.refill(started(30), "coffee", 20)
    state = run_ticks(state, logic.DAY_TICKS - 1)
    state, result = logic.tick(state)
    assert result is not None and state["shift"] is None
    refused(lambda s: logic.sell(s, "coffee"), state)
    refused(lambda s: logic.refill(s, "coffee", 1), state)


def test_the_api_refuses_crafted_requests_and_keeps_the_save_identical(run_on_disk):
    client = app.app.test_client()
    client.post("/api/buy", json={"product": "coffee", "quantity": 10})
    assert client.post("/api/shift/start", json={"shop": "cafe"}).status_code == 200
    before = db.load(run_on_disk)
    crafted = [
        ("/api/shift/refill", {"product": "coffee", "quantity": 999}),
        ("/api/shift/refill", {"product": "coffee", "quantity": -1}),
        ("/api/shift/refill", {"product": "coffee", "quantity": "5"}),
        ("/api/shift/refill", {"product": "beer", "quantity": 1}),
        ("/api/shift/sell", {"product": "coffee"}),  # counter is empty
        ("/api/shift/sell", {"product": {"x": 1}}),
        ("/api/shift/start", {"shop": "cafe"}),
        ("/api/shift/start", {"shop": "surf_shop"}),
        ("/api/open", {"day": 1}),
    ]
    for url, body in crafted:
        response = client.post(url, json=body)
        assert response.status_code == 400, (url, body)
        assert "Traceback" not in response.get_data(as_text=True)
        assert db.load(run_on_disk) == before, (url, body)


def test_the_api_closes_the_day_and_refuses_a_sale_afterwards(run_on_disk):
    client = app.app.test_client()
    client.post("/api/buy", json={"product": "coffee", "quantity": 10})
    client.post("/api/shift/start", json={"shop": "cafe"})
    client.post("/api/shift/refill", json={"product": "coffee", "quantity": 10})
    assert client.post("/api/shift/sell", json={"product": "coffee"}).status_code == 200
    for _ in range(logic.DAY_TICKS):
        assert client.post("/api/shift/tick").status_code == 200
    state = db.load(run_on_disk)
    assert state["shift"] is None and state["day"] == 2
    assert state["history"][-1]["lines"][0]["sold"] == 1
    assert state["stock"]["coffee"] == 9  # the 9 unsold units went back to the storeroom
    saved = copy.deepcopy(state)
    assert client.post("/api/shift/sell", json={"product": "coffee"}).status_code == 400
    assert client.post("/api/shift/tick").status_code == 400
    assert db.load(run_on_disk) == saved


# ---- Check 5: no position ------------------------------------------------

def test_no_shift_rule_reads_the_players_position():
    state = logic.refill(started(30), "coffee", 5)
    moved = copy.deepcopy(state)
    moved["player"] = {"zone": "campus", "x": 0.0, "y": 0.0}
    assert logic.sell(moved, "coffee")["shift"] == logic.sell(state, "coffee")["shift"]


# ---- Check 6: saving -----------------------------------------------------

def test_a_running_shift_survives_a_restart(tmp_path):
    path = tmp_path / "run.db"
    state = logic.refill(started(30), "coffee", 5)
    db.save(state, path)
    assert db.load(path) == state


def test_a_save_from_before_this_spec_loads_with_no_shift(tmp_path):
    path = tmp_path / "old.db"
    db.save(logic.new_state(), path)
    with db.connect(path) as conn:
        conn.execute("DROP TABLE shift")
    assert db.load(path)["shift"] is None


# ---- Check 7 and 8: the day books like trade_day, money stays whole -------

def test_the_closed_day_is_booked_in_the_history_like_trade_day():
    state = logic.refill(started(30), "coffee", 10)
    state = logic.sell(state, "coffee")
    cash = state["cash"]
    state = run_ticks(state, logic.DAY_TICKS - 1)
    state, result = logic.tick(state)
    assert state["day"] == 2 and state["shift"] is None
    assert state["history"] == [result] and state["cash"] == cash
    line = result["lines"][0]
    assert (line["product"], line["sold"], line["revenue"], line["cogs"]) == ("coffee", 1, 200, 80)
    assert result["gross_profit"] == 120 and result["lost"] == 9
    assert all(isinstance(v, int) for v in (result["revenue"], result["cogs"], result["cash_after"]))
    assert state["stock"]["coffee"] == 30 - 10 + 9


def test_waiting_customers_leave_after_their_patience():
    state = run_ticks(started(), logic.PATIENCE_TICKS)
    assert state["shift"]["lost"] == 1  # only the customer from tick 0 ran out of patience
    assert len(state["shift"]["queue"]) == 9
    state = logic.sell(logic.refill(state, "coffee", 5), "coffee")  # the customer from tick 9 waits
    assert state["shift"]["sold"]["coffee"] == 1
    refused(lambda s: logic.sell(s, "coffee"), state)  # the next one arrives at tick 18
