"""Checks from specs/demo-scenarios.md, changed for specs/demo-day.md (David confirmed the change on
2026-11-23, see "Decide 6" there): the demo is one day of seven steps now. The steps are complete and
valid data, the loader is deterministic and gives a complete run, every step can be solved in its time
by the real rules, the demo ends in free play, and the endpoints load only an id from the fixed list
into the player's own run (a bad request changes nothing, locally and in public mode)."""

import copy
import re

import pytest

import app
import db
import logic
import scenarios

DEMO = "demo-day"
STEPS = scenarios.STEPS
STEP_IDS = scenarios.step_ids()
LOADED = [i for i, step in enumerate(STEPS) if step["state"] is not None]  # the start and the jumps


# ---- the data -------------------------------------------------------------------------------------


def test_the_demo_has_its_seven_steps_in_order():
    assert scenarios.scenario_ids() == [DEMO]
    assert STEP_IDS == ["wake-up", "get-dressed", "order-stock", "cafe-shift", "beach-cafe", "rain-again",
                        "end-the-day"]


@pytest.mark.parametrize("index", range(len(STEPS)))
def test_every_entry_is_complete_and_valid(index):
    step = STEPS[index]
    assert set(step) == {"id", "title", "text", "goal_text", "button", "target", "open_day", "goal",
                         "state", "opening", "tick_ms"}
    assert re.fullmatch(r"[a-z-]+", step["id"]) and len(step["id"]) <= scenarios.MAX_ID
    for field in ("title", "text", "goal_text", "button"):
        assert isinstance(step[field], str) and step[field] and "<" not in step[field]
    assert len(step["text"].split()) <= scenarios.MAX_TEXT
    assert step["target"] in scenarios.TARGETS and isinstance(step["open_day"], bool)
    assert step["opening"] in scenarios.OPENINGS
    assert step["goal"]["kind"] in scenarios.GOAL_KINDS and set(step["goal"]) == {"kind", "value"}
    low, high = scenarios.TICK_MS_RANGE
    assert isinstance(step["tick_ms"], int) and low <= step["tick_ms"] <= high
    if step["state"] is None:
        assert step["opening"] is None  # a continuous step loads nothing
        return
    # the patch is a run the existing rules accept, and money is whole cents
    state = logic.editor_set_state(logic.new_state(scenarios.DEMO_SEED), copy.deepcopy(step["state"]))
    assert isinstance(state["cash"], int) and not isinstance(state["cash"], bool)


def test_no_scenario_ticks_into_the_rate_limit():
    for step in STEPS:
        per_minute = 60_000 // step["tick_ms"]
        assert per_minute + 60 <= app.RATE_LIMIT  # ticks plus a click a second


# ---- the loader ------------------------------------------------------------------------------------


@pytest.mark.parametrize("index", LOADED)
def test_load_scenario_is_deterministic_and_complete(index):
    first, second = scenarios.load_step(index), scenarios.load_step(index)
    assert first == second
    step = STEPS[index]
    for key in ("day", "cash", "shops", "stock", "prices", "employees", "player", "day_override",
                "seed", "history", "badges", "shift"):
        assert key in first
    assert first["scenario"] == {"id": DEMO, "step": index}
    assert first["seed"] == scenarios.DEMO_SEED and first["day"] == step["state"]["day"]
    assert first["history"] == [] and first["badges"] == []
    assert (first["shift"] is None) == (step["opening"] is None)
    # the day context shows the fixed weather and event (make_day_context with the override)
    context = logic.make_day_context(first["seed"], first["day"], first["day_override"])
    fixed = step["state"]["day_override"]
    assert context["weather"] == fixed["weather"]
    assert (context["event"] or {}).get("id", "none") == fixed["event"]
    assert scenarios.active(first) == DEMO


def test_different_ids_give_different_runs():
    states = [scenarios.load_step(i) for i in LOADED]
    assert len({repr(s) for s in states}) == len(LOADED)


def test_the_loaded_run_survives_save_and_load(tmp_path):
    path = tmp_path / "run.db"
    state = scenarios.load_step(5)
    db.save_new_run(state, path)
    assert db.load(path) == state


def test_a_save_without_a_scenario_loads_without_one(tmp_path):
    path = tmp_path / "run.db"
    state = logic.new_state(5)
    db.save(state, path)
    loaded = db.load(path)
    assert loaded == state and "scenario" not in loaded and scenarios.active(loaded) is None


@pytest.mark.parametrize("bad", [None, 3, 3.5, True, [], ["demo-day"], {}, {"id": "demo-day"}, "", "nope",
                                 "DEMO-DAY", "demo-day ", "../demo-day", "demo-day/../x", "x" * 10_000])
def test_load_scenario_refuses_anything_but_a_known_id(bad):
    with pytest.raises(logic.RejectedAction):
        scenarios.load_scenario(bad)
    with pytest.raises(logic.RejectedAction):
        scenarios.scenario_done(logic.new_state(1), bad)


def test_the_data_is_not_changed_by_loading():
    before = copy.deepcopy(scenarios.SCENARIOS)
    for index in LOADED:
        state = scenarios.load_step(index)
        state["stock"]["coffee"] = 0
        state["shops"]["cafe"]["products"].append("x")
    assert scenarios.SCENARIOS == before


# ---- guests in the jumps (they depend on specs/guests.md) ---------------------------------------------


def _plan(state):
    return state["shift"]["guest_plan"]


def _switched(state):
    return [g for part in _plan(state).values() for g in part["guests"] if g["wish"] != g["shop"]]


def _beach_staffed():
    """Jump 4 played as the card asks: the Beach Cafe bought with its employee."""
    state = logic.unlock_shop(scenarios.load_step(4), "beach_cafe")
    return logic.buy_upgrade(state, "beach_cafe", "staff_1")


@pytest.mark.parametrize("index", [4, 5])
def test_both_shops_have_a_working_employee(index):
    state = _beach_staffed() if index == 4 else scenarios.load_step(index)
    staffed = ["cafe", "beach_cafe"] if index == 4 else ["beach_cafe", "merchandise", "surf_shop"]
    for shop in staffed:
        assert any(e["shop"] == shop and e["working"] for e in state["employees"]), shop
    assert state["shift"]["shop"] == "cafe" and "beach_cafe" in state["shift"]["extra"]
    if index == 5:
        assert set(_plan(state)) == {"cafe", "beach_cafe", "merchandise", "surf_shop"}
        assert set(state["shift"]["extra"]) == {"beach_cafe", "merchandise", "surf_shop"}


def test_guests_change_their_mind_early_in_scenario_2():
    state = scenarios.load_step(5)
    early = [g for g in _switched(state) if g["offset"] <= 45]
    assert len(early) >= 2  # seen in the short Cafe shift of the step
    assert {g["shop"] for g in early} >= {"merchandise"}  # rain: inside, the Merch shop receives
    totals = {shop: part["summary"]["total"] for shop, part in _plan(state).items()}
    assert totals["cafe"] > totals["beach_cafe"] and totals["merchandise"] > totals["beach_cafe"]  # rain: inside


def test_without_the_cafe_employee_the_cafe_receives_no_guest():
    # jump 5: the Cafe is the player's own shift, no employee: guests leave it but never come to it
    assert not [g for g in _switched(scenarios.load_step(5)) if g["shop"] == "cafe"]
    # jump 4 with the Cafe employee removed and the beach staffed from the start: the same
    patch = copy.deepcopy(STEPS[4]["state"])
    patch["shops"]["cafe"] = {**patch["shops"]["cafe"], "level": 2, "staff_places": 0}
    patch["shops"]["beach_cafe"] = {"unlocked": True, "level": 2, "products": ["beer"], "staff_places": 1}
    patch["employees"] = [{"shop": "beach_cafe", "place": 1}]
    state = logic.open_day(logic.editor_set_state(logic.new_state(scenarios.DEMO_SEED), patch))
    assert not [g for g in _switched(state) if g["shop"] == "cafe"]


def test_scenario_3_turns_the_crowd_round_and_names_the_event():
    sun = _beach_staffed()
    sun_cafe = _plan(sun)["cafe"]["summary"]["total"]
    sun_beach = sum(sun["shift"]["extra"]["beach_cafe"]["planned"].values())
    rain = {s: p["summary"]["total"] for s, p in _plan(scenarios.load_step(5)).items()}
    assert sun_beach > sun_cafe and rain["cafe"] > rain["beach_cafe"]  # the crowd turns round
    assert sun_beach > rain["beach_cafe"]
    # the Cafe's guests from the guest plans, as before (review finding); per product, because jump 5's
    # Cafe sells coffee only: rain brings more coffee guests to the Cafe than sun
    def coffee_guests(state):
        return len([g for g in _plan(state)["cafe"]["guests"] if g["shop"] == "cafe" and g["product"] == "coffee"])
    assert coffee_guests(scenarios.load_step(5)) > coffee_guests(sun)
    thoughts = [t["text"] for t in _plan(scenarios.load_step(5))["cafe"]["summary"]["thoughts"]]
    assert any(t.startswith("Rainy") for t in thoughts)


# ---- goals and reference solutions ------------------------------------------------------------------


def _serve(state, shop="cafe"):
    """The presenter in a shift: keep the counter filled and serve whoever waits."""
    shift = state["shift"]
    if shift["shop"] != shop or shift["over"]:
        return state
    products = state["shops"][shop]["products"]
    for product in products:  # an even share of the counter for every product
        share = logic.SHOPS[shop]["counter"] // len(products) - shift["counter"].get(product, 0)
        carry = min(share, state["stock"][product])
        if carry > 0:
            state = logic.refill(state, product, carry)
            shift = state["shift"]
    sold = True
    while sold:  # serve the queue in turn, whatever the guest in front wants
        sold = False
        for product in products:
            try:
                state = logic.sell(state, product)
                sold = True
            except logic.RejectedAction:
                pass
    return state


def play_step(state, ticks=120):
    """A scripted play of the real rules for the running step, as the card asks. Returns the state
    when the step is done (or the ticks are used up) and the ticks it took."""
    step = STEPS[state["scenario"]["step"]]
    kind = step["goal"]["kind"]
    if kind == "manual":
        return state, 0
    if kind == "outfit_worn":
        return logic.buy_outfit(state, step["goal"]["value"]), 0
    if kind == "stock_for_demand":
        product = step["goal"]["value"]
        return logic.buy(state, product, scenarios.need(state, product)), 0
    if kind == "shop_staffed":
        state = logic.unlock_shop(state, step["goal"]["value"])
        return logic.buy_upgrade(state, step["goal"]["value"], "staff_1"), 0
    if kind == "day_over":
        return logic.skip_shift(state)[0], 0
    if step["open_day"] and state["shift"] is None:
        state = logic.open_day(state)
    if state["shift"]["shop"] is None:
        state = logic.start_shift(state, "cafe")
    for tick in range(ticks):
        state = _serve(state)
        if scenarios.step_done(state):
            return state, tick
        state, _result = logic.tick(state)
    return state, ticks


def demo_until(index):
    """The demo played by the reference solution up to the start of a step."""
    state = scenarios.load_scenario(DEMO)
    while state["scenario"]["step"] < index:
        state, _ticks = play_step(state)
        state = scenarios.advance(state)
        if state["scenario"]["step"] < index and (scenarios.step_done(state) or STEPS[state["scenario"]["step"]]["goal"]["kind"] == "manual"):
            state, _jumped = scenarios.next_step(state)
    return state


# the ticks each step may take: the action part of the timing in the spec (400 to 500 ms a tick)
TIME = {"get-dressed": 0, "order-stock": 0, "cafe-shift": 90, "beach-cafe": 0, "rain-again": 40, "end-the-day": 0}


@pytest.mark.parametrize("index", range(1, len(STEPS)))
def test_every_scenario_is_solved_in_its_time(index):
    start = demo_until(index)
    assert start["scenario"]["step"] == index
    assert scenarios.step_done(start) is False
    before = copy.deepcopy(start)
    scenarios.step_done(start)
    scenarios.demo_view(start)
    assert start == before  # the check only reads
    end, ticks = play_step(start)
    assert scenarios.step_done(end) is True and scenarios.scenario_done(end, DEMO) is True
    assert ticks <= TIME[STEP_IDS[index]]


def test_a_watched_day_that_is_over_counts_as_seen():
    state = scenarios.load_step(5)
    state, _result = logic.skip_shift(state)
    assert state["day"] == 2 and scenarios.step_done(state)


def test_selling_on_a_skipped_day_is_booked_from_the_history():
    state, _ticks = play_step(demo_until(3))
    assert scenarios.step_done(state)
    state, _result = logic.skip_shift(state)
    assert scenarios.step_done(state)  # what was sold is booked in the history
    start = demo_until(3)
    nothing, _result = logic.skip_shift(logic.open_day(start))
    assert not scenarios.step_done(nothing)


def test_the_whole_demo_ends_in_free_play():
    state = demo_until(len(STEPS) - 1)
    state, _ticks = play_step(state)
    assert scenarios.step_done(state) and scenarios.demo_view(state)["active"]["done"]
    free, booked = scenarios.finish_demo(state)
    assert booked is None  # the last step booked the day already
    assert "scenario" not in free and free["day_override"] is None
    assert free["shops"]["beach_cafe"]["unlocked"] and free["cash"] == state["cash"]
    # the next day comes from the seed again
    assert logic.day_context(free) == logic.make_day_context(free["seed"], free["day"])
    with pytest.raises(logic.RejectedAction):
        scenarios.finish_demo(free)


def test_finish_on_an_open_day_books_it_under_the_fixed_weather_first():
    state = scenarios.load_step(5)
    for _ in range(10):
        state, _result = logic.tick(state)
    free, booked = scenarios.finish_demo(state)
    assert booked is not None and booked["day"] == 1 and free["day"] == 2 and free["shift"] is None
    assert free["history"][-1] == booked
    # the whole day was booked with the step's rain: the same as letting it pass in the demo
    in_demo, result = logic.skip_shift(state)
    assert result == booked
    assert logic.day_context(free) == logic.make_day_context(free["seed"], 2)


def test_a_stale_scenario_can_still_be_left():
    state = scenarios.load_step(4)
    state["scenario"] = {"id": "renamed-later", "step": 0}
    view = scenarios.demo_view(state)
    assert view["active"] is None and view["stale"] is True
    free, _booked = scenarios.finish_demo(state)
    assert "scenario" not in free and free["day_override"] is None
    assert scenarios.demo_view(free)["stale"] is False


def test_demo_view_sends_texts_but_never_the_seed_or_the_patch():
    view = scenarios.demo_view(demo_until(2))
    card = view["active"]
    assert card["id"] == "order-stock" and card["index"] == 3 and card["count"] == 7
    assert card["done"] is False and card["tick_ms"] == 500 and card["target"] == "supplier"
    assert set(card) == {"id", "index", "count", "title", "text", "goal", "button", "target", "open_day",
                         "call_next", "done", "last", "tick_ms"}
    assert scenarios.demo_view(scenarios.load_scenario(DEMO))["active"]["call_next"] is True
    assert scenarios.demo_view(demo_until(len(STEPS) - 1))["active"]["last"] is True
    assert scenarios.demo_view(logic.new_state(1))["active"] is None
    assert [s["id"] for s in view["scenarios"]] == [DEMO]
    assert "state" not in card


def test_an_unknown_saved_scenario_counts_as_none():
    state = logic.new_state(1)
    for saved in ({"id": "gone"}, {"id": 3}, "grow", 7):
        state["scenario"] = saved
        assert scenarios.active(state) is None and scenarios.demo_view(state)["active"] is None


# ---- the endpoints, locally ---------------------------------------------------------------------------


@pytest.fixture
def run_on_disk(tmp_path, monkeypatch):
    """The real API on a temporary save, so the player's own run stays untouched."""
    path = tmp_path / "run.db"
    state = logic.buy(logic.new_state(7), "coffee", 10)
    db.save(state, path)
    real_save, real_new_run = db.save, db.save_new_run
    monkeypatch.setattr(app, "load_run", lambda: db.load(path))
    monkeypatch.setattr(app.db, "save", lambda s: real_save(s, path))
    monkeypatch.setattr(app.db, "save_new_run", lambda s: real_new_run(s, path))
    return path


def test_load_replaces_the_run_and_the_screen_gets_the_card(run_on_disk):
    client = app.app.test_client()
    response = client.post("/api/demo/load", json={"id": DEMO, "confirm": True})
    assert response.status_code == 200
    data = response.get_json()
    assert data["state"]["demo"]["active"]["id"] == "wake-up"
    assert data["state"]["day"] == 1 and data["state"]["shift"] is None  # in bed, the day still closed
    expected = scenarios.load_scenario(DEMO)
    logic.award_badges(expected)  # given at once, like the editor does
    assert db.load(run_on_disk) == expected
    assert "seed" not in data["state"] and "seed" not in data["state"]["demo"]["active"]
    assert "state" not in data["state"]["demo"]["active"]  # the patch stays on the server
    # skipping on to the last jump: the prepared run replaces the run, badges given at once
    for _ in range(5):
        assert client.post("/api/demo/next", json={}).status_code == 200
    jumped = scenarios.load_step(5)
    logic.award_badges(jumped)
    assert db.load(run_on_disk) == jumped
    assert {b["id"] for b in jumped["badges"]} >= {"first-hire", "expansion"}


@pytest.mark.parametrize("body", [
    {"id": DEMO},  # no confirm
    {"id": DEMO, "confirm": "true"},
    {"id": DEMO, "confirm": 1},
    {"confirm": True},
    {"id": None, "confirm": True},
    {"id": 2, "confirm": True},
    {"id": [DEMO], "confirm": True},
    {"id": {"id": DEMO}, "confirm": True},
    {"id": "", "confirm": True},
    {"id": "x" * 5000, "confirm": True},
    {"id": "../../etc/passwd", "confirm": True},
    {"id": DEMO, "confirm": True, "state": {"cash": 99_999_999}},
    {"id": DEMO, "confirm": True, "patch": {"cash": 1}},
])
def test_a_bad_load_is_refused_and_changes_nothing(run_on_disk, body):
    before, raw = db.load(run_on_disk), run_on_disk.read_bytes()
    response = app.app.test_client().post("/api/demo/load", json=body)
    assert response.status_code == 400
    text = response.get_data(as_text=True)
    assert "Traceback" not in text and "/home" not in text and ".py" not in text
    assert db.load(run_on_disk) == before and run_on_disk.read_bytes() == raw


def test_a_body_that_is_not_json_is_refused(run_on_disk):
    before = db.load(run_on_disk)
    client = app.app.test_client()
    for data in (b"demo-day", b"[\"demo-day\"]", b"{"):
        response = client.post("/api/demo/load", data=data, content_type="application/json")
        assert response.status_code == 400
    assert db.load(run_on_disk) == before


def test_finish_without_a_demo_is_refused_and_changes_nothing(run_on_disk):
    before = db.load(run_on_disk)
    response = app.app.test_client().post("/api/demo/finish", json={})
    assert response.status_code == 400 and db.load(run_on_disk) == before


def test_finish_leaves_the_demo_and_keeps_the_run(run_on_disk):
    client = app.app.test_client()
    client.post("/api/demo/load", json={"id": DEMO, "confirm": True})
    client.post("/api/demo/next", json={})
    assert client.post("/api/outfit/buy", json={"outfit": "raincoat"}).status_code == 200
    assert client.post("/api/demo/finish", json={"id": "x"}).status_code == 400  # takes no fields
    assert scenarios.active(db.load(run_on_disk)) == DEMO
    response = client.post("/api/demo/finish", json={})
    assert response.status_code == 200 and response.get_json()["state"]["demo"]["active"] is None
    assert "closed" not in response.get_json()["message"]  # no open day to book
    saved = db.load(run_on_disk)
    assert "scenario" not in saved and saved["day_override"] is None
    assert "raincoat" in saved["outfits"]["owned"]


def test_the_demo_needs_no_switch_and_the_editor_stays_off(run_on_disk, monkeypatch):
    monkeypatch.delenv("CT_EDITOR", raising=False)
    monkeypatch.delenv("CAMPUS_TYCOON_DEMO", raising=False)
    client = app.app.test_client()
    assert client.post("/api/demo/load", json={"id": DEMO, "confirm": True}).status_code == 200
    assert client.post("/api/editor/state", json={"patch": {"cash": 1}}).status_code == 400
    assert client.post("/api/day-override", json={"weather": "sun"}).status_code == 400


def test_a_new_run_ends_the_demo(run_on_disk):
    client = app.app.test_client()
    client.post("/api/demo/load", json={"id": DEMO, "confirm": True})
    client.post("/api/new-run", json={"confirm": True})
    assert scenarios.active(db.load(run_on_disk)) is None


# ---- the endpoints in public mode ---------------------------------------------------------------------


@pytest.fixture
def public(monkeypatch, tmp_path):
    monkeypatch.setenv("CT_PUBLIC", "1")
    monkeypatch.setenv("CT_EDITOR", "1")  # even switched on, the editor stays off in public mode
    monkeypatch.setattr(app, "PLAYERS_DIR", tmp_path / "players")
    app._hits.clear()
    yield tmp_path / "players"
    app._hits.clear()


def test_public_players_load_into_their_own_run_only(public):
    first, second = app.app.test_client(), app.app.test_client()
    first.get("/")
    second.get("/")
    assert second.post("/api/buy", json={"product": "coffee", "quantity": "5"}).status_code == 200
    first.get("/api/state")  # the first player's run exists before the load
    files = sorted(public.glob("*.db"))
    assert len(files) == 2
    other = {f: db.load(f) for f in files}
    response = first.post("/api/demo/load", json={"id": DEMO, "confirm": True})
    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "Content-Security-Policy" in response.headers
    assert response.get_json()["state"]["demo"]["active"]["id"] == "wake-up"
    changed = [f for f in files if db.load(f) != other[f]]
    assert len(changed) == 1  # the first player's file only
    assert second.get("/api/state").get_json()["demo"]["active"] is None
    assert first.post("/api/editor/state", json={"patch": {"cash": 1}}).status_code == 400
    assert "seed" not in response.get_json()["state"]


def test_public_demo_without_a_cookie_makes_no_run(public):
    response = app.app.test_client().post("/api/demo/load", json={"id": DEMO, "confirm": True})
    assert response.status_code == 400 and not list(public.glob("*.db"))


def test_public_demo_counts_against_the_rate_limit(public, monkeypatch):
    monkeypatch.setattr(app, "RATE_LIMIT", 3)
    client = app.app.test_client()
    client.get("/")
    codes = [client.post("/api/demo/load", json={"id": DEMO, "confirm": True}).status_code for _ in range(4)]
    assert codes[:3] == [200, 200, 200] and codes[3] == 429


def test_finish_on_an_open_day_answers_with_the_booked_day(run_on_disk):
    client = app.app.test_client()
    client.post("/api/demo/load", json={"id": DEMO, "confirm": True})
    for _ in range(5):
        client.post("/api/demo/next", json={})  # to the rainy jump: the day is open
    response = client.post("/api/demo/finish", json={})
    assert response.status_code == 200 and "Day 1 closed" in response.get_json()["message"]
    saved = db.load(run_on_disk)
    assert saved["day"] == 2 and saved["shift"] is None and "scenario" not in saved
