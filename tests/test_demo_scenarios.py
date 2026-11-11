"""Checks from specs/demo-scenarios.md: the scenarios are complete and valid data, the loader is
deterministic and gives a complete run, every scenario can be solved in its time by the real
rules, the demo ends in free play, and the endpoints load only an id from the fixed list into the
player's own run (a bad request changes nothing, locally and in public mode)."""

import copy
import re

import pytest

import app
import db
import logic
import scenarios

IDS = scenarios.scenario_ids()


# ---- the data -------------------------------------------------------------------------------------


def test_the_demo_has_four_scenarios_in_order():
    assert IDS == ["serve-the-cafe", "guests-decide", "other-day-other-choice", "grow"]


@pytest.mark.parametrize("sid", IDS)
def test_every_entry_is_complete_and_valid(sid):
    entry = scenarios.SCENARIOS[sid]
    assert set(entry) == {"title", "text", "goal_text", "seed", "state", "opening", "goal", "tick_ms"}
    assert re.fullmatch(r"[a-z-]+", sid) and len(sid) <= scenarios.MAX_ID
    for field in ("title", "text", "goal_text"):
        assert isinstance(entry[field], str) and entry[field] and "<" not in entry[field]
    assert len(entry["text"].split()) <= scenarios.MAX_TEXT
    assert entry["opening"] in scenarios.OPENINGS
    assert entry["goal"]["kind"] in scenarios.GOAL_KINDS and set(entry["goal"]) == {"kind", "value"}
    low, high = scenarios.TICK_MS_RANGE
    assert isinstance(entry["tick_ms"], int) and low <= entry["tick_ms"] <= high
    # the patch is a run the existing rules accept, and money is whole cents
    state = logic.editor_set_state(logic.new_state(entry["seed"]), copy.deepcopy(entry["state"]))
    assert isinstance(state["cash"], int) and not isinstance(state["cash"], bool)


def test_no_scenario_ticks_into_the_rate_limit():
    for entry in scenarios.SCENARIOS.values():
        per_minute = 60_000 // entry["tick_ms"]
        assert per_minute + 60 <= app.RATE_LIMIT  # ticks plus a click a second


# ---- the loader ------------------------------------------------------------------------------------


@pytest.mark.parametrize("sid", IDS)
def test_load_scenario_is_deterministic_and_complete(sid):
    first, second = scenarios.load_scenario(sid), scenarios.load_scenario(sid)
    assert first == second
    entry = scenarios.SCENARIOS[sid]
    for key in ("day", "cash", "shops", "stock", "prices", "employees", "player", "day_override",
                "seed", "history", "badges", "shift"):
        assert key in first
    assert first["scenario"] == {"id": sid}
    assert first["seed"] == entry["seed"] and first["day"] == entry["state"]["day"]
    assert first["history"] == [] and first["badges"] == []
    assert (first["shift"] is None) == (entry["opening"] is None)
    # the day context shows the fixed weather and event (make_day_context with the override)
    context = logic.make_day_context(first["seed"], first["day"], first["day_override"])
    fixed = entry["state"]["day_override"]
    assert context["weather"] == fixed["weather"]
    assert (context["event"] or {}).get("id", "none") == fixed["event"]
    # the state survives save and load with the scenario in it
    assert scenarios.active(first) == sid


def test_different_ids_give_different_runs():
    states = [scenarios.load_scenario(sid) for sid in IDS]
    assert len({repr(s) for s in states}) == len(IDS)


def test_the_loaded_run_survives_save_and_load(tmp_path):
    path = tmp_path / "run.db"
    state = scenarios.load_scenario("guests-decide")
    db.save_new_run(state, path)
    assert db.load(path) == state


def test_a_save_without_a_scenario_loads_without_one(tmp_path):
    path = tmp_path / "run.db"
    state = logic.new_state(5)
    db.save(state, path)
    loaded = db.load(path)
    assert loaded == state and "scenario" not in loaded and scenarios.active(loaded) is None


@pytest.mark.parametrize("bad", [None, 3, 3.5, True, [], ["grow"], {}, {"id": "grow"}, "", "nope",
                                 "GROW", "grow ", "../grow", "grow/../x", "x" * 10_000])
def test_load_scenario_refuses_anything_but_a_known_id(bad):
    with pytest.raises(logic.RejectedAction):
        scenarios.load_scenario(bad)
    with pytest.raises(logic.RejectedAction):
        scenarios.scenario_done(logic.new_state(1), bad)


def test_the_data_is_not_changed_by_loading():
    before = copy.deepcopy(scenarios.SCENARIOS)
    for sid in IDS:
        state = scenarios.load_scenario(sid)
        state["stock"]["coffee"] = 0
        state["shops"]["cafe"]["products"].append("x")
    assert scenarios.SCENARIOS == before


# ---- guests in scenarios 2 and 3 (they depend on specs/guests.md) ------------------------------------


def _plan(state):
    return state["shift"]["guest_plan"]


def _switched(state):
    return [g for part in _plan(state).values() for g in part["guests"] if g["wish"] != g["shop"]]


@pytest.mark.parametrize("sid", ["guests-decide", "other-day-other-choice"])
def test_both_shops_have_a_working_employee(sid):
    state = scenarios.load_scenario(sid)
    for shop in ("cafe", "beach_cafe"):
        assert any(e["shop"] == shop and e["working"] for e in state["employees"]), shop
    assert set(_plan(state)) == {"cafe", "beach_cafe"}
    assert state["shift"]["shop"] == "cafe" and "beach_cafe" in state["shift"]["extra"]


def test_guests_change_their_mind_early_in_scenario_2():
    state = scenarios.load_scenario("guests-decide")
    early = [g for g in _switched(state) if g["offset"] <= 45]
    assert len(early) >= 2  # seen before the goal at tick 60
    assert {g["shop"] for g in early} >= {"cafe"}  # the Cafe receives: it has an employee
    totals = {shop: part["summary"]["total"] for shop, part in _plan(state).items()}
    assert totals["beach_cafe"] > totals["cafe"]  # hot: the beach wins


def test_without_the_cafe_employee_the_cafe_receives_no_guest():
    entry = copy.deepcopy(scenarios.SCENARIOS["guests-decide"])
    entry["state"]["employees"] = [{"shop": "beach_cafe", "place": 1}]
    state = logic.open_day(logic.editor_set_state(logic.new_state(entry["seed"]), entry["state"]))
    assert not [g for g in _switched(state) if g["shop"] == "cafe"]


def test_scenario_3_turns_the_crowd_round_and_names_the_event():
    hot = {s: p["summary"]["total"] for s, p in _plan(scenarios.load_scenario("guests-decide")).items()}
    state = scenarios.load_scenario("other-day-other-choice")
    exam = {s: p["summary"]["total"] for s, p in _plan(state).items()}
    assert hot["beach_cafe"] > hot["cafe"] and exam["cafe"] > exam["beach_cafe"]
    thoughts = [t["text"] for t in _plan(state)["cafe"]["summary"]["thoughts"]]
    assert any(t.startswith("Exam period") for t in thoughts)


# ---- goals and reference solutions ------------------------------------------------------------------


def _play_cafe_tick(state):
    """The presenter in scenario 1: keep the counter filled and serve whoever waits, then a tick."""
    shift = state["shift"]
    if shift["shop"] == "cafe" and not shift["over"]:
        space = logic.SHOPS["cafe"]["counter"] - sum(shift["counter"].values())
        carry = min(space, state["stock"]["coffee"])
        if carry > 0:
            state = logic.refill(state, "coffee", carry)
        while True:
            try:
                state = logic.sell(state, "coffee")
            except logic.RejectedAction:
                break
    state, _result = logic.tick(state)
    return state


def solve(sid, ticks):
    """A scripted play of the real rules that should reach the goal within `ticks`."""
    state = scenarios.load_scenario(sid)
    if sid == "grow":
        return logic.unlock_shop(state, "beach_cafe")
    for _ in range(ticks):
        if scenarios.scenario_done(state, sid):
            break
        state = _play_cafe_tick(state) if sid == "serve-the-cafe" else logic.tick(state)[0]
    return state


@pytest.mark.parametrize("sid,ticks", [("serve-the-cafe", 60), ("guests-decide", 60),
                                       ("other-day-other-choice", 60), ("grow", 0)])
def test_every_scenario_is_solved_in_its_time(sid, ticks):
    start = scenarios.load_scenario(sid)
    assert scenarios.scenario_done(start, sid) is False
    before = copy.deepcopy(start)
    scenarios.scenario_done(start, sid)
    assert start == before  # the check only reads
    end = solve(sid, ticks)
    assert scenarios.scenario_done(end, sid) is True
    # at two ticks a second this is the action part of the timetable (about 33 seconds)
    if end.get("shift"):
        assert end["shift"]["tick"] <= ticks


def test_a_watched_day_that_is_over_counts_as_seen():
    state, _result = logic.skip_shift(scenarios.load_scenario("guests-decide"))
    assert state["day"] == 9 and scenarios.scenario_done(state, "guests-decide")


def test_selling_on_a_skipped_day_is_booked_from_the_history():
    state = solve("serve-the-cafe", 60)
    state, _result = logic.skip_shift(state)
    assert scenarios.scenario_done(state, "serve-the-cafe")
    nothing, _result = logic.skip_shift(scenarios.load_scenario("serve-the-cafe"))
    assert not scenarios.scenario_done(nothing, "serve-the-cafe")


def test_the_whole_demo_ends_in_free_play():
    for sid in IDS:
        state = solve(sid, 60)
        assert scenarios.scenario_done(state, sid)
    free = scenarios.finish_demo(state)
    assert "scenario" not in free and free["day_override"] is None
    assert free["shops"]["beach_cafe"]["unlocked"] and free["cash"] == state["cash"]
    # the next day comes from the seed again
    assert logic.day_context(free) == logic.make_day_context(free["seed"], free["day"])
    with pytest.raises(logic.RejectedAction):
        scenarios.finish_demo(free)


def test_demo_view_sends_texts_but_never_the_seed_or_the_patch():
    view = scenarios.demo_view(scenarios.load_scenario("guests-decide"))
    card = view["active"]
    assert card["index"] == 2 and card["count"] == 4 and card["next"] == "other-day-other-choice"
    assert card["done"] is False and card["tick_ms"] == 500
    assert set(card) == {"id", "index", "count", "title", "text", "goal", "done", "tick_ms", "next"}
    assert scenarios.demo_view(scenarios.load_scenario("grow"))["active"]["next"] is None
    assert scenarios.demo_view(logic.new_state(1))["active"] is None
    assert [s["id"] for s in view["scenarios"]] == IDS


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
    response = app.app.test_client().post("/api/demo/load", json={"id": "guests-decide", "confirm": True})
    assert response.status_code == 200
    data = response.get_json()
    assert data["state"]["demo"]["active"]["id"] == "guests-decide"
    assert data["state"]["day"] == 8 and data["state"]["shift"] is not None
    assert db.load(run_on_disk) == scenarios.load_scenario("guests-decide")
    assert "seed" not in data["state"] and "seed" not in data["state"]["demo"]["active"]
    assert "state" not in data["state"]["demo"]["active"]  # the patch stays on the server


@pytest.mark.parametrize("body", [
    {"id": "grow"},  # no confirm
    {"id": "grow", "confirm": "true"},
    {"id": "grow", "confirm": 1},
    {"confirm": True},
    {"id": None, "confirm": True},
    {"id": 2, "confirm": True},
    {"id": ["grow"], "confirm": True},
    {"id": {"id": "grow"}, "confirm": True},
    {"id": "", "confirm": True},
    {"id": "x" * 5000, "confirm": True},
    {"id": "../../etc/passwd", "confirm": True},
    {"id": "grow", "confirm": True, "state": {"cash": 99_999_999}},
    {"id": "grow", "confirm": True, "patch": {"cash": 1}},
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
    for data in (b"grow", b"[\"grow\"]", b"{"):
        response = client.post("/api/demo/load", data=data, content_type="application/json")
        assert response.status_code == 400
    assert db.load(run_on_disk) == before


def test_finish_without_a_demo_is_refused_and_changes_nothing(run_on_disk):
    before = db.load(run_on_disk)
    response = app.app.test_client().post("/api/demo/finish", json={})
    assert response.status_code == 400 and db.load(run_on_disk) == before


def test_finish_leaves_the_demo_and_keeps_the_run(run_on_disk):
    client = app.app.test_client()
    client.post("/api/demo/load", json={"id": "grow", "confirm": True})
    client.post("/api/shop/unlock", json={"shop": "beach_cafe"})
    assert client.post("/api/demo/finish", json={"id": "x"}).status_code == 400  # takes no fields
    assert scenarios.active(db.load(run_on_disk)) == "grow"
    response = client.post("/api/demo/finish", json={})
    assert response.status_code == 200 and response.get_json()["state"]["demo"]["active"] is None
    saved = db.load(run_on_disk)
    assert "scenario" not in saved and saved["day_override"] is None
    assert saved["shops"]["beach_cafe"]["unlocked"]


def test_the_demo_needs_no_switch_and_the_editor_stays_off(run_on_disk, monkeypatch):
    monkeypatch.delenv("CT_EDITOR", raising=False)
    monkeypatch.delenv("CAMPUS_TYCOON_DEMO", raising=False)
    client = app.app.test_client()
    assert client.post("/api/demo/load", json={"id": "grow", "confirm": True}).status_code == 200
    assert client.post("/api/editor/state", json={"patch": {"cash": 1}}).status_code == 400
    assert client.post("/api/day-override", json={"weather": "sun"}).status_code == 400


def test_a_new_run_ends_the_demo(run_on_disk):
    client = app.app.test_client()
    client.post("/api/demo/load", json={"id": "grow", "confirm": True})
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
    response = first.post("/api/demo/load", json={"id": "serve-the-cafe", "confirm": True})
    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "Content-Security-Policy" in response.headers
    assert response.get_json()["state"]["demo"]["active"]["id"] == "serve-the-cafe"
    changed = [f for f in files if db.load(f) != other[f]]
    assert len(changed) == 1  # the first player's file only
    assert second.get("/api/state").get_json()["demo"]["active"] is None
    assert first.post("/api/editor/state", json={"patch": {"cash": 1}}).status_code == 400
    assert "seed" not in response.get_json()["state"]


def test_public_demo_without_a_cookie_makes_no_run(public):
    response = app.app.test_client().post("/api/demo/load", json={"id": "grow", "confirm": True})
    assert response.status_code == 400 and not list(public.glob("*.db"))


def test_public_demo_counts_against_the_rate_limit(public, monkeypatch):
    monkeypatch.setattr(app, "RATE_LIMIT", 3)
    client = app.app.test_client()
    client.get("/")
    codes = [client.post("/api/demo/load", json={"id": "grow", "confirm": True}).status_code for _ in range(4)]
    assert codes[:3] == [200, 200, 200] and codes[3] == 429
