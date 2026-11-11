"""Demo scenarios (specs/demo-scenarios.md, issue #23): prepared days for the 3-minute live demo.

A scenario is pure data: a seed, a patch for logic.editor_set_state (the run as it should be),
how far the day is opened, a text for the overlay and a goal. The rules are the functions below;
nothing in the data is code. The server loads a scenario by its id into the player's own run; the
browser never sends a state.

The active scenario lives in the state as state["scenario"] = {"id": ...}. No key (or None) means
no demo is running: a fresh run (logic.new_state) has no key, so old saves and old tests stay
exactly as they were.

Rules only: no HTTP, nothing saved. All randomness comes from the seed of the scenario.
"""

import copy

import logic

# What a goal can ask for. Each kind is checked by _goal_reached; data never holds code.
GOAL_KINDS = ("sold_at_least", "tick_at_least", "shop_unlocked")
OPENINGS = (None, "open", "shift:cafe")
PANELS = (None, "shift", "shops")  # the panel the screen opens when the scenario loads
TICK_MS_RANGE = (400, 1000)  # below 400 ms a scenario would run into app.RATE_LIMIT (Decide 2)
MAX_TEXT = 25  # words in the overlay text of a scenario
MAX_ID = 40  # characters of an id

# One demo seed for all: rehearsal and show are the same (Decide 6). The repository is public, so
# this seed is no secret; the server still never sends it.
DEMO_SEED = 39

# Two shops with one working employee each: guests who look around can go both ways (guests,
# Decide 4: the Cafe without an employee never receives a guest).
_TWO_STAFFED_SHOPS = {
    "shops": {
        "cafe": {"unlocked": True, "level": 3, "products": ["coffee", "cake"], "staff_places": 1},
        "beach_cafe": {"unlocked": True, "level": 3, "products": ["beer", "coke_zero"], "staff_places": 1},
    },
    "stock": {"coffee": 45, "cake": 45, "beer": 45, "coke_zero": 45},
    "employees": [{"shop": "cafe", "place": 1}, {"shop": "beach_cafe", "place": 1}],
    "cash": 20_000,
    "player": {"zone": "campus", "x": 22.0, "y": 17.0},
}

SCENARIOS = {
    "serve-the-cafe": {
        "title": "Run the Cafe",
        "text": "Carry coffee to the counter with Fill, then sell to the queue. Sell 5 cups.",
        "goal_text": "Sell 5 units",
        "seed": DEMO_SEED,
        "state": {
            "day": 1,
            "cash": logic.STARTING_CASH,
            "day_override": {"weather": "rain", "event": "none"},
            "stock": {"coffee": 40},
            "player": {"zone": "campus", "x": 17.0, "y": 7.0},
        },
        "opening": "shift:cafe",
        "panel": "shift",  # the goal is selling: the Shift panel is where it happens
        "goal": {"kind": "sold_at_least", "value": 5},
        "tick_ms": 500,
    },
    "guests-decide": {
        "title": "Guests decide",
        "text": "Hot day, one employee in each shop. Watch the guests: bubbles say why they pick a shop. Red: they changed their mind.",
        "goal_text": "Watch until tick 60",
        "seed": DEMO_SEED,
        "state": {**_TWO_STAFFED_SHOPS, "day": 8,
                  "day_override": {"weather": "heat", "event": "none"}},
        "opening": "open",
        "panel": None,
        "goal": {"kind": "tick_at_least", "value": 60},
        "tick_ms": 500,
    },
    "other-day-other-choice": {
        "title": "Weather and events",
        "text": "Same shops, other day: rain and the exam period. Now the crowd goes to the Cafe.",
        "goal_text": "Watch until tick 60",
        "seed": DEMO_SEED,
        # the player stands in the Nova: its roof is gone and the Cafe's long queue is in sight
        "state": {**_TWO_STAFFED_SHOPS, "day": 9,
                  "day_override": {"weather": "rain", "event": "exam_period"},
                  "player": {"zone": "campus", "x": 17.0, "y": 7.0}},
        "opening": "open",
        "panel": None,
        "goal": {"kind": "tick_at_least", "value": 60},
        "tick_ms": 500,
    },
    "grow": {
        "title": "Grow",
        "text": "You have 300 euro. Open the Shops window and unlock the Beach Cafe. Then the run is yours.",
        "goal_text": "Unlock the Beach Cafe",
        "seed": DEMO_SEED,
        "state": {
            "day": 12,
            "cash": 30_000,
            "day_override": {"weather": "sun", "event": "none"},
            "shops": {"cafe": {"unlocked": True, "level": 3, "products": ["coffee", "cake"], "staff_places": 1}},
            "stock": {"coffee": 40, "cake": 40},
            "employees": [{"shop": "cafe", "place": 1}],
            "player": {"zone": "campus", "x": 22.0, "y": 17.0},
        },
        "opening": None,
        "panel": None,  # the presenter opens the Shops window: that click is part of the show
        "goal": {"kind": "shop_unlocked", "value": "beach_cafe"},
        "tick_ms": 1000,
    },
}


def scenario_ids():
    """The ids in the order of the demo."""
    return list(SCENARIOS)


def _check_id(scenario_id):
    """The id if it names a scenario, else a refusal. The type is checked first, so a list or a
    dictionary is refused and never looked up."""
    if not isinstance(scenario_id, str) or scenario_id not in SCENARIOS:
        raise logic.RejectedAction("Unknown demo scenario.")
    return scenario_id


def load_scenario(scenario_id):
    """A new, complete run for the scenario: a fresh state from its seed, its patch applied by
    logic.editor_set_state (so every value is checked by the existing rules), the day opened as
    the scenario says (by the real open_day and start_shift), and state["scenario"] set.
    Refuses an unknown id; builds only new objects, so a refusal changes nothing."""
    entry = SCENARIOS[_check_id(scenario_id)]
    state = logic.editor_set_state(logic.new_state(entry["seed"]), copy.deepcopy(entry["state"]))
    if entry["opening"] is not None:
        state = logic.open_day(state)
    if entry["opening"] == "shift:cafe":
        state = logic.start_shift(state, "cafe")
    state["scenario"] = {"id": scenario_id}
    return state


def active(state):
    """The id of the running scenario, or None (no key, None, or an id that no longer exists)."""
    current = state.get("scenario")
    if isinstance(current, dict) and isinstance(current.get("id"), str) and current["id"] in SCENARIOS:
        return current["id"]
    return None


def _goal_reached(state, entry):
    goal = entry["goal"]
    day = entry["state"].get("day", 1)
    over = state["day"] > day  # the scenario's day is booked: a watched day was fully seen
    if goal["kind"] == "sold_at_least":
        # a scenario starts with an empty history: everything sold in this run is the scenario's
        return logic._sold_so_far(state) >= goal["value"]
    if goal["kind"] == "tick_at_least":
        shift = state.get("shift")
        return over or (shift is not None and shift["tick"] >= goal["value"])
    if goal["kind"] == "shop_unlocked":
        return state["shops"][goal["value"]]["unlocked"]
    return False


def scenario_done(state, scenario_id):
    """True when the goal of the scenario holds in this state. Pure: only reads the state."""
    return _goal_reached(state, SCENARIOS[_check_id(scenario_id)])


def finish_demo(state):
    """Leave the demo: the scenario and the fixed weather and event are cleared, so the next days
    come from the seed again. The run itself goes on as it is. Refused when no demo runs.

    On an open day the rest of the day passes first (logic.skip_shift: the staff go on selling, the
    day is booked under the weather it was planned with), so no day is half one weather and half
    another. Returns (state, the booked day's result or None)."""
    if state.get("scenario") is None:
        raise logic.RejectedAction("No demo is running.")
    result = None
    if logic.day_is_open(state):
        state, result = logic.skip_shift(state)
    new = copy.deepcopy(state)
    del new["scenario"]
    new["day_override"] = None
    return new, result


def demo_view(state):
    """What the screen needs: the list of scenarios and, while one runs, its card. Texts come from
    the data above; the seed and the patch are never sent."""
    ids = scenario_ids()
    current = active(state)
    # a saved id that no longer exists (renamed in a later version): the demo can still be left
    stale = current is None and state.get("scenario") is not None
    card = None
    if current is not None:
        entry = SCENARIOS[current]
        index = ids.index(current)
        card = {
            "id": current, "index": index + 1, "count": len(ids),
            "title": entry["title"], "text": entry["text"], "goal": entry["goal_text"],
            "done": scenario_done(state, current), "tick_ms": entry["tick_ms"],
            "next": ids[index + 1] if index + 1 < len(ids) else None,
            "panel": entry["panel"],
        }
    return {"scenarios": [{"id": sid, "title": SCENARIOS[sid]["title"]} for sid in ids],
            "active": card, "stale": stale}
