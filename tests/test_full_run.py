"""Checks from specs/full-run.md ("Done when"). One test per check."""

import pytest

import db
import logic


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "test.db"


def complete_run():
    """The scenario from the spec: 15 Sandwiches, day 1 at €4, all later days at €9."""
    state = logic.buy(logic.new_state(), "sandwich", 15)
    state = logic.set_price(state, "sandwich", 400)
    state, _ = logic.trade_day(state)
    state = logic.set_price(state, "sandwich", 900)  # above 2x reference: demand 0
    for _ in range(logic.LAST_DAY - 1):
        state, _ = logic.trade_day(state)
    return state


# ---- Check 1: full run and final result (CT05, CT R4) --------------------

def test_full_run_gives_the_final_result():
    state = complete_run()
    assert logic.is_finished(state)
    assert state["cash"] == 11_000
    assert state["stock"]["sandwich"] == 5
    assert logic.stock_value(state) == 1_000
    assert logic.overall_gain(state) == 2_000
    assert [day["day"] for day in state["history"]] == list(range(1, logic.LAST_DAY + 1))


# ---- Check 2: everything is locked after day 5 (A6) ----------------------

@pytest.mark.parametrize("action", [
    lambda s: logic.buy(s, "sandwich", 1),
    lambda s: logic.set_price(s, "sandwich", 400),
    lambda s: logic.trade_day(s),
])
def test_actions_after_day_five_are_rejected_and_nothing_changes(db_path, action):
    state = complete_run()
    db.save(state, db_path)
    with pytest.raises(logic.RejectedAction):
        action(state)
    assert db.load(db_path) == state


# ---- Check 3: a confirmed new run replaces the old one (CT01) ------------

def test_new_run_replaces_the_saved_run(db_path):
    db.save(complete_run(), db_path)

    db.save_new_run(logic.new_state(), db_path)

    reloaded = db.load(db_path)
    assert reloaded == logic.new_state()
    assert reloaded["history"] == []


def test_first_day_of_a_new_run_is_stored_fresh(db_path):
    db.save(complete_run(), db_path)
    db.save_new_run(logic.new_state(), db_path)

    state = logic.buy(db.load(db_path), "coffee", 10)
    state, result = logic.trade_day(state)
    db.save(state, db_path)

    history = db.load(db_path)["history"]
    assert history == [result]  # the old day 1 (Sandwiches) is gone


# ---- Check 4: a complete run survives a restart --------------------------

def test_complete_run_survives_a_restart(db_path):
    state = complete_run()
    db.save(state, db_path)

    reopened = db.load(db_path)
    assert logic.is_finished(reopened)
    assert logic.overall_gain(reopened) == 2_000
    assert len(reopened["history"]) == logic.LAST_DAY
