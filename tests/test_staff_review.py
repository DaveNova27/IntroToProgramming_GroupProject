"""Staff: the fixes after the AI review of PR #54 (specs/staff.md)."""

import logic
from test_staff import staffed, with_places


def test_hiring_on_an_open_day_starts_the_staffed_shift():
    # the day opens before anyone is hired (the player bought the place later, at nothing)
    state = logic.open_day(with_places())
    assert state["shift"]["shop"] is None
    state = logic.hire(state, "cafe", 1)
    state = logic.hire(state, "cafe", 2)
    # hiring on the open day starts the staffed shift: they work, so they are paid
    assert state["shift"]["shop"] == "cafe" and state["shift"]["staffed"]


def test_hiring_late_in_the_day_starts_no_shift_and_costs_no_wage():
    state = logic.open_day(with_places())
    state["shift"]["tick"] = state["shift"]["day_end"] - logic.SHIFT_TICKS + 1  # too late
    state = logic.hire(state, "cafe", 1)
    assert state["shift"]["shop"] is None
    cash = state["cash"]
    state, result = logic.skip_shift(state)
    assert result["wages"] == 0 and result["wages_unpaid"] == []
    assert state["cash"] == cash  # nobody worked, nobody was paid
    assert state["employees"][0]["working"]


def test_buying_a_place_on_an_open_day_starts_the_staffed_shift():
    state = logic.open_day(with_places(places=0))
    state = logic.buy_upgrade(state, "cafe", "staff_1")
    assert state["shift"]["shop"] == "cafe" and state["shift"]["staffed"]


def test_hire_leaves_a_running_shift_alone():
    state = logic.open_day(staffed(1))
    before = state["shift"]
    state = logic.hire(state, "cafe", 2)
    assert state["shift"] == before


def test_stopped_employees_restart_only_within_one_budget():
    state = staffed(1, 2, cash=100_000)
    wage = logic.employee_wage(state["employees"][0])
    for employee in state["employees"]:
        employee["working"] = False
    # the cash after the day covers one wage, not two
    state["cash"] = wage + wage // 2
    paid, stopped = logic._pay_wages(state, "cafe")
    assert (paid, stopped) == (0, [])
    assert [e["working"] for e in state["employees"]] == [True, False]
    assert state["cash"] == wage + wage // 2  # restarting costs nothing today
