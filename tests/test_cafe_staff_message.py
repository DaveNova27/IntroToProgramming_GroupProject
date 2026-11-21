"""Checks from specs/cafe-staff-message.md ("Done when"): when employees run the Cafe in the player's
slot, the reason says so, and the player can still serve there beside them. New file; no old test is
touched here."""

import copy

import pytest

import logic

RUNNING = "Employees run the Cafe. You can serve here beside them."
OVER = "The shift in the Cafe is over for today."


def cafe(staff):
    """The Cafe with coffee in the storeroom and, if asked, two employees."""
    state = logic.new_state()
    state["cash"] = 1_000_000
    state["stock"]["coffee"] = 60
    state["stock"]["beer"] = 60
    if staff:
        state = logic.buy_upgrade(logic.buy_upgrade(state, "cafe", "staff_1"), "cafe", "staff_2")
    return state


def advance(state, ticks):
    for _ in range(ticks):
        state, result = logic.tick(state)
        assert result is None
    return state


def refused_with(state, text):
    before = copy.deepcopy(state)
    with pytest.raises(logic.RejectedAction) as err:
        logic.start_shift(state, "cafe")
    assert str(err.value) == text
    assert state == before  # a rejected action changes nothing


def cafe_option(state):
    (option,) = [o for o in logic.shift_options(state) if o["shop"] == "cafe"]
    return option


def test_a_staffed_cafe_says_the_employees_run_it():
    state = logic.open_day(cafe(staff=True))
    assert state["shift"]["shop"] == "cafe" and state["shift"]["staffed"]
    assert cafe_option(state) == {"shop": "cafe", "can": False, "done": True, "why": RUNNING}
    refused_with(state, RUNNING)


def test_the_player_serves_in_the_staffed_cafe_beside_the_crew():
    state = logic.open_day(cafe(staff=True))
    state = logic.refill(state, "coffee", 5)
    assert state["shift"]["counter"]["coffee"] >= 5
    for _ in range(logic.SHIFT_TICKS - 1):
        sold = state["shift"]["sold"].get("coffee", 0)
        try:
            state = logic.sell(state, "coffee")  # the player serves a waiting customer
        except logic.RejectedAction:  # nobody waiting this tick (the crew was faster)
            state, result = logic.tick(state)
            assert result is None
            continue
        assert state["shift"]["sold"]["coffee"] == sold + 1
        break
    else:
        pytest.fail("the player never got to serve in the staffed Cafe")


def test_a_staffed_cafe_whose_shift_is_over_says_so():
    state = advance(logic.open_day(cafe(staff=True)), logic.SHIFT_TICKS)
    assert state["shift"]["over"] and state["shift"]["staffed"]
    assert cafe_option(state)["why"] == OVER
    refused_with(state, OVER)


def test_the_players_own_cafe_shift_keeps_its_messages():
    state = logic.start_shift(logic.open_day(cafe(staff=False)), "cafe")
    assert not state["shift"].get("staffed")
    refused_with(state, "You are working in the Cafe already.")
    state = advance(state, logic.SHIFT_TICKS)
    refused_with(state, "You already worked in the Cafe today.")


def test_a_crew_shift_that_moved_aside_and_ended_says_it_is_over():
    """The Cafe crew moves aside when the player starts another shop; once both have ended, the
    Cafe's reason is that its shift is over, not that the player worked there."""
    state = logic.unlock_shop(cafe(staff=True), "beach_cafe")
    state = logic.start_shift(logic.open_day(state), "beach_cafe")
    assert state["shift"]["extra"]["cafe"]["staffed"]
    state = advance(state, logic.SHIFT_TICKS)
    assert state["shift"]["extra"]["cafe"]["over"]
    assert cafe_option(state)["why"] == OVER
    refused_with(state, OVER)
