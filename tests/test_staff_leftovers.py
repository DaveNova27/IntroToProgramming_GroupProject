"""Staff: the leftovers of the reviews of PR #54 and #57 (specs/staff.md)."""

import copy

import app as app_module
import db
import logic
from test_staff import staffed, with_places
from test_staff_all_shops import run, two_shops


def test_a_tick_does_not_change_the_state_it_was_given():
    state = logic.open_day(two_shops())
    for _ in range(30):
        before = copy.deepcopy(state)
        new, _ = logic.tick(state)
        assert state == before  # the work of every crew happens on the copy only
        state = new


def test_an_employee_tick_equals_the_players_own_refill_and_sell():
    state = logic.open_day(staffed(1))  # one refiller: carries 1 per tick (and sells every 4th)
    by_staff, _ = logic.tick(state)
    by_hand = copy.deepcopy(state)
    by_hand["shift"]["tick"] += 1
    by_hand = logic.refill(by_hand, "coffee", 1)  # the public rule the player uses
    for key in ("stock", "cash"):
        assert by_staff[key] == by_hand[key]
    assert by_staff["shift"]["counter"] == by_hand["shift"]["counter"]
    # a sale on the seller's tick (every 4th at level 1) equals the player's own sell()
    state = logic.open_day(staffed(1, 2))
    state["stock"]["coffee"] -= 5
    state["shift"]["counter"]["coffee"] = 5
    state["shift"]["tick"] = 3  # the next tick is 4: a seller of level 1 acts
    by_staff, _ = logic.tick(state)
    by_hand = copy.deepcopy(state)
    by_hand["shift"]["tick"] += 1
    by_hand = logic.sell(by_hand, "coffee")
    assert by_staff["cash"] == by_hand["cash"] > state["cash"]
    assert by_staff["shift"]["sold"] == by_hand["shift"]["sold"]


def test_the_day_result_always_lists_the_shops_that_ran():
    assert run(logic.open_day(two_shops()))[1]["shops"] == ["beach_cafe", "cafe"]
    assert run(logic.open_day(two_shops(cafe_staff=False)))[1]["shops"] == ["beach_cafe"]
    state, result = logic.skip_shift(logic.open_day(with_places()))
    assert result["shops"] == []  # nobody worked


def test_wages_today_counts_only_shops_that_run_on_an_open_day():
    before = app_module.staff_view(two_shops())["wages_today"]
    assert before == 4 * 800  # no day open: every unlocked shop would pay
    late = logic.open_day(two_shops(cafe_staff=False, beach_staff=False))
    late["shift"]["tick"] = late["shift"]["day_end"] - logic.SHIFT_TICKS + 1
    for item in ("staff_1", "staff_2"):
        late = logic.buy_upgrade(late, "beach_cafe", item)
    assert app_module.staff_view(late)["wages_today"] == 0  # no crew started, no wage due
    running = logic.open_day(two_shops(beach_staff=False))
    assert app_module.staff_view(running)["wages_today"] == 2 * 800


def test_a_level_above_the_maximum_in_a_save_is_kept_at_the_maximum(tmp_path):
    import sqlite3
    path = tmp_path / "run.db"
    db.save(staffed(1), path)
    with sqlite3.connect(path) as conn:
        conn.execute("UPDATE employees SET level = 9 WHERE id = 1")
    assert db.load(path)["employees"][0]["level"] == logic.EMPLOYEE_MAX_LEVEL
