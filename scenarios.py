"""The demo day (specs/demo-day.md, built on specs/demo-scenarios.md): one continuous day of the live
demo, from the bed in the morning to the bed in the evening, in seven steps.

A step is pure data: a title, a text, the label of its button, where the button walks, a goal and, for
the start and the two "jumps", a prepared start state (a patch for logic.editor_set_state, the weather
in day_override). The rules are the functions below; nothing in the data is code. The server loads the
demo by its id into the player's own run and moves the steps on; the browser never sends a state.

The running demo lives in the state as state["scenario"] = {"id": "demo-day", "step": n}. No key (or
None) means no demo is running: a fresh run (logic.new_state) has no key, so old saves and old tests
stay exactly as they were.

Continuous steps (no state) count what the player really does; the server moves on to the next
continuous step by itself once the goal holds (advance). A jump (a step with a state) loads only when
the presenter presses its button (next_step), so a shift is never cut in the middle. Every step plays
on day 1, so it reads as one day.

Rules only: no HTTP, nothing saved. All randomness comes from the seed of the demo.
"""

import copy

import logic

# What a goal can ask for. Each kind is checked by _goal_reached; data never holds code.
GOAL_KINDS = ("manual", "outfit_worn", "stock_for_demand", "sold_for_demand", "shop_staffed",
              "shop_sold_at_least", "day_over")
OPENINGS = (None, "open", "shift:cafe")
# Where a step's button walks the figure. The browser takes each spot from /api/world: the wardrobe and
# the bed of the Dorm, the order PC ("supplier"), the Cafe's work spot, the Beach Cafe's queue.
TARGETS = (None, "wardrobe", "supplier", "cafe", "beach_cafe", "bed")
TICK_MS_RANGE = (400, 1000)  # below 400 ms the demo would run into app.RATE_LIMIT (demo-scenarios Decide 2)
MAX_TEXT = 25  # words in the text of a step
MAX_ID = 40  # characters of an id
NEED = "{need}"  # the one placeholder a text may hold: today's demand of the goal's product

# One demo seed: rehearsal and show are the same. The repository is public, so this seed is no secret;
# the server still never sends it.
DEMO_SEED = 39
DEMO_ID = "demo-day"
DAY = 1  # every step plays on this day

_RAIN = {"weather": "rain", "event": "none"}
_JACKET = {"owned": ["basic", "raincoat"], "worn": "raincoat"}
_CAFE = {"unlocked": True, "level": 2, "products": ["coffee", "cake"], "staff_places": 0}

STEPS = [
    {
        "id": "wake-up",
        "title": "Good morning",
        "text": "Day 1 starts in the Dorm. Forecast: rain. The plan: dress, order stock, run the Cafe, "
                "open the Beach Cafe, then home.",
        "goal_text": "Start the day",
        "button": "Start the day",
        "target": None,
        "open_day": False,
        "goal": {"kind": "manual", "value": None},
        # the start: 100 euro, no stock, the basic shirt, in bed in the Dorm
        "state": {"day": DAY, "cash": logic.STARTING_CASH, "day_override": _RAIN,
                  "player": {"zone": "campus", "x": 36.8, "y": 11.1}},
        "opening": None,
        "tick_ms": 500,
    },
    {
        "id": "get-dressed",
        "title": "Get dressed",
        "text": "Rain all day: buy the rain jacket at the wardrobe and put it on. The start money pays "
                "for it and the stock.",
        "goal_text": "Wear the rain jacket",
        "button": "Get dressed",
        "target": "wardrobe",
        "open_day": False,
        "goal": {"kind": "outfit_worn", "value": "raincoat"},
        "state": None,
        "opening": None,
        "tick_ms": 500,
    },
    {
        "id": "order-stock",
        "title": "Order stock",
        "text": "Rain sends the guests to the Cafe: it needs about {need} coffee today. Order them at the "
                "PC in the Supply Hall.",
        "goal_text": "{need} coffee in stock",
        "button": "Order stock",
        "target": "supplier",
        "open_day": False,
        "goal": {"kind": "stock_for_demand", "value": "coffee"},
        "state": None,
        "opening": None,
        "tick_ms": 500,
    },
    {
        "id": "cafe-shift",
        "title": "Cafe shift",
        "text": "The day opens. Start the shift, carry coffee to the counter with Fill and sell to the "
                "queue: {need} coffee.",
        "goal_text": "Sell {need} coffee",
        "button": "Cafe shift",
        "target": "cafe",
        "open_day": True,
        "goal": {"kind": "sold_for_demand", "value": "coffee"},
        "state": None,
        "opening": None,
        "tick_ms": 400,
    },
    {
        "id": "beach-cafe",
        "title": "Beach Cafe",
        "text": "Later the sun came out and the Cafe earned well. Guests head for the beach: buy the "
                "Beach Cafe and an employee.",
        "goal_text": "Beach Cafe with an employee",
        "button": "Beach Cafe",
        "target": "beach_cafe",
        "open_day": False,
        "goal": {"kind": "shop_staffed", "value": "beach_cafe"},
        # 400 euro: unlocking (200) and an employee place (60) fit, with room for a product
        "state": {"day": DAY, "cash": 40_000, "day_override": {"weather": "sun", "event": "none"},
                  # the Cafe runs itself now: one employee keeps serving while the player is at the beach
                  "shops": {"cafe": {**_CAFE, "level": 3, "staff_places": 1}},
                  "stock": {"coffee": 30, "cake": 20, "beer": 40},
                  "employees": [{"shop": "cafe", "place": 1}],
                  "outfits": _JACKET,
                  "player": {"zone": "campus", "x": 17.7, "y": 5.0}},
        "opening": "open",
        "tick_ms": 500,
    },
    {
        "id": "rain-again",
        "title": "Rain again",
        "text": "The rain is back: everyone goes inside for coffee or merchandise. Merchandise and Surf "
                "Shop are open. Sell 4 coffee in the Cafe.",
        "goal_text": "Sell 4 in the Cafe",
        "button": "Rain again",
        "target": "cafe",
        "open_day": False,
        "goal": {"kind": "shop_sold_at_least", "value": {"shop": "cafe", "units": 4}},
        # all four shops open; the three new ones each with a working employee
        "state": {"day": DAY, "cash": 30_000, "day_override": _RAIN,
                  "shops": {
                      # coffee only: one Fill and one Sell for the presenter in the short shift
                      "cafe": {"unlocked": True, "level": 1, "products": ["coffee"], "staff_places": 0},
                      "beach_cafe": {"unlocked": True, "level": 2, "products": ["beer"], "staff_places": 1},
                      "merchandise": {"unlocked": True, "level": 2, "products": ["hoodie"], "staff_places": 1},
                      "surf_shop": {"unlocked": True, "level": 2, "products": ["surfboard"], "staff_places": 1},
                  },
                  "stock": {"coffee": 40, "beer": 30, "hoodie": 30, "surfboard": 20},
                  "employees": [{"shop": "beach_cafe", "place": 1}, {"shop": "merchandise", "place": 1},
                                {"shop": "surf_shop", "place": 1}],
                  "outfits": _JACKET,
                  # at the Cafe already: its shift starts with the jump, no guest leaves during a walk
                  "player": {"zone": "campus", "x": 17.7, "y": 5.0}},
        "opening": "shift:cafe",
        "tick_ms": 400,
    },
    {
        "id": "end-the-day",
        "title": "End the day",
        "text": "Back to the Dorm: end the day at the bed, sleep, and read the evening report with "
                "tomorrow's forecast.",
        "goal_text": "Sleep: day 1 is booked",
        "button": "Go home",
        "target": "bed",
        "open_day": False,
        "goal": {"kind": "day_over", "value": DAY},
        "state": None,
        "opening": None,
        "tick_ms": 500,
    },
]

SCENARIOS = {
    DEMO_ID: {"title": "One day on campus", "seed": DEMO_SEED, "steps": STEPS},
}


def scenario_ids():
    """The ids of the demos (one: the demo day)."""
    return list(SCENARIOS)


def step_ids(scenario_id=DEMO_ID):
    """The ids of the steps in order."""
    return [step["id"] for step in SCENARIOS[_check_id(scenario_id)]["steps"]]


def _check_id(scenario_id):
    """The id if it names a demo, else a refusal. The type is checked first, so a list or a
    dictionary is refused and never looked up."""
    if not isinstance(scenario_id, str) or scenario_id not in SCENARIOS:
        raise logic.RejectedAction("Unknown demo scenario.")
    return scenario_id


def is_jump(step):
    """A step with a prepared start state: it replaces the run when it loads."""
    return step["state"] is not None


def _load_step(scenario_id, index):
    """A new, complete run for a step with a state: a fresh state from the seed, the patch applied by
    logic.editor_set_state (so every value is checked by the existing rules), the day opened as the
    step says (by the real open_day and start_shift), and state["scenario"] set. Builds only new objects."""
    entry = SCENARIOS[scenario_id]
    step = entry["steps"][index]
    state = logic.editor_set_state(logic.new_state(entry["seed"]), copy.deepcopy(step["state"]))
    if step["opening"] is not None:
        state = logic.open_day(state)
    if step["opening"] == "shift:cafe":
        state = logic.start_shift(state, "cafe")
    state["scenario"] = {"id": scenario_id, "step": index}
    return state


def load_scenario(scenario_id):
    """The demo from its first step. Refuses an unknown id; a refusal changes nothing."""
    return _load_step(_check_id(scenario_id), 0)


def load_step(index, scenario_id=DEMO_ID):
    """The prepared start state of a step that has one (the start and the jumps). For tests and the
    reference play; the server only reaches a jump through next_step."""
    steps = SCENARIOS[_check_id(scenario_id)]["steps"]
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < len(steps) \
            or not is_jump(steps[index]):
        raise logic.RejectedAction("That demo step has no start state.")
    return _load_step(scenario_id, index)


def _current(state):
    """(id, step index) of the running demo, or None (no key, None, an unknown id or step)."""
    current = state.get("scenario")
    if not isinstance(current, dict) or current.get("id") not in SCENARIOS:
        return None
    index = current.get("step")
    if isinstance(index, bool) or not isinstance(index, int):
        return None
    if not 0 <= index < len(SCENARIOS[current["id"]]["steps"]):
        return None
    return current["id"], index


def active(state):
    """The id of the running demo, or None."""
    current = _current(state)
    return current[0] if current else None


def need(state, product):
    """How many of a product the guests want today at its saved price: the day's demand, from the
    same rule the shift and the forecast use (logic.customers_today)."""
    return logic.customers_today(state, product)


def _sold_today(state, product=None, shop=None):
    """Units sold on the open day (0 without one), of one product or in one shop."""
    shift = state.get("shift")
    if not shift:
        return 0
    parts = [shift, *shift.get("extra", {}).values()]
    total = 0
    for part in parts:
        if shop is not None and part.get("shop") != shop:
            continue
        for pid, units in part.get("sold", {}).items():
            if product is None or pid == product:
                total += units
    return total


def _booked(state, day, product):
    """(sold, demand) of a product on a booked day, from its result: the demand as it was that day."""
    for result in state["history"]:
        if result["day"] == day:
            lines = [line for line in result["lines"] if line["product"] == product]
            return sum(line["sold"] for line in lines), sum(line["demand"] for line in lines)
    return 0, 0


def _goal_reached(state, step):
    goal = step["goal"]
    kind, value = goal["kind"], goal["value"]
    if kind == "manual":
        return False  # only the presenter's button moves on
    if kind == "outfit_worn":
        return logic.outfits_of(state)["worn"] == value
    if kind == "stock_for_demand":
        have = state["stock"][value] + logic.units_on_counter(state, value)
        return have >= need(state, value) or _sold_today(state, value) > 0 or state["day"] > DAY
    if kind == "sold_for_demand":
        if state["day"] == DAY:
            # all of the day's demand sold, or the player's own shift in that shop is over: the
            # shift has been shown, a guest who left must not stop the demo
            shift = state.get("shift") or {}
            own_over = shift.get("shop") == logic.shop_of_product(value) and shift.get("over") \
                and not shift.get("staffed")
            return _sold_today(state, value) >= need(state, value) or bool(own_over)
        sold, wanted = _booked(state, DAY, value)
        return sold > 0 and sold >= wanted
    if kind == "shop_staffed":
        return state["shops"][value]["unlocked"] and any(
            e["shop"] == value and e["working"] for e in state["employees"])
    if kind == "shop_sold_at_least":
        if state["day"] > DAY:
            return True  # the day is over: the step has been seen
        shift = state.get("shift") or {}
        if shift.get("shop") == value["shop"] and shift.get("over") and not shift.get("staffed"):
            return True  # the player's shift there is over: it has been shown
        return _sold_today(state, shop=value["shop"]) >= value["units"]
    if kind == "day_over":
        return state["day"] > value
    return False


def step_done(state):
    """True when the goal of the running step holds in this state. Pure: only reads the state."""
    current = _current(state)
    if current is None:
        return False
    scenario_id, index = current
    return _goal_reached(state, SCENARIOS[scenario_id]["steps"][index])


def scenario_done(state, scenario_id):
    """True when the running step of this demo is done (False when another or no demo runs)."""
    _check_id(scenario_id)
    return active(state) == scenario_id and step_done(state)


def advance(state):
    """Move on while the running step is done and the next step is continuous (no state of its own).
    Called by the server after every accepted action. A jump waits for its button. Returns the state
    itself when nothing moves, else a new one."""
    current = _current(state)
    if current is None:
        return state
    scenario_id, index = current
    steps = SCENARIOS[scenario_id]["steps"]
    start = index
    while index + 1 < len(steps) and not is_jump(steps[index + 1]) and _goal_reached(state, steps[index]):
        index += 1
    if index == start:
        return state
    new = copy.deepcopy(state)
    new["scenario"] = {"id": scenario_id, "step": index}
    return new


def next_step(state):
    """The presenter's button: the next step. A jump replaces the run with its prepared state; a
    continuous step keeps the run as it is. Allowed also when the step is not done (a skip). Refused
    without a demo and on the last step. Returns (state, jumped)."""
    current = _current(state)
    if current is None:
        raise logic.RejectedAction("No demo is running.")
    scenario_id, index = current
    steps = SCENARIOS[scenario_id]["steps"]
    if index + 1 >= len(steps):
        raise logic.RejectedAction("This is the last step of the demo: press Free play.")
    if is_jump(steps[index + 1]):
        return advance(_load_step(scenario_id, index + 1)), True
    new = copy.deepcopy(state)
    new["scenario"] = {"id": scenario_id, "step": index + 1}
    return advance(new), False


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


def _fill(text, state, step):
    """The text with {need} filled from today's demand of the goal's product."""
    if NEED not in text:
        return text
    return text.replace(NEED, str(need(state, step["goal"]["value"])))


def demo_view(state):
    """What the screen needs: the list of demos and, while one runs, the card of the step to show.

    The card shows the running step; when that step is done and the next one is a jump, it shows the
    jump (its button loads it). call_next: the button first asks the server for the next step (a
    manual step or a jump), then walks. Texts come from the data above; the seed and the patches are
    never sent."""
    current = _current(state)
    stale = current is None and state.get("scenario") is not None
    card = None
    if current is not None:
        scenario_id, index = current
        steps = SCENARIOS[scenario_id]["steps"]
        done = _goal_reached(state, steps[index])
        shown = index + 1 if done and index + 1 < len(steps) else index
        step = steps[shown]
        last = shown == len(steps) - 1
        card = {
            "id": step["id"], "index": shown + 1, "count": len(steps),
            "title": step["title"], "text": _fill(step["text"], state, step),
            "goal": _fill(step["goal_text"], state, step), "button": step["button"],
            "target": step["target"],
            # the day must be open before the shift: the button opens it first (the bed's request)
            "open_day": step["open_day"] and shown == index and state.get("shift") is None,
            "call_next": shown != index or step["goal"]["kind"] == "manual",
            "done": done and last, "last": last, "tick_ms": step["tick_ms"],
        }
    return {"scenarios": [{"id": sid, "title": SCENARIOS[sid]["title"]} for sid in scenario_ids()],
            "active": card, "stale": stale}
