"""New checks from specs/demo-day.md: one continuous demo day. The card moves on by itself for a
continuous step and waits for the button at a jump; /api/demo/next takes no fields and a refusal changes
nothing; the texts carry today's demand; every target can be walked to; the start money pays the jacket
and the stock; the jumps keep the jacket; the whole day plays through the real API."""

import copy
import pathlib
import re

import pytest

import app
import db
import logic
import scenarios
import world

ROOT = pathlib.Path(__file__).resolve().parent.parent
UI = (ROOT / "static/world/ui.js").read_text(encoding="utf-8")
DEMO_JS = (ROOT / "static/world/demo.js").read_text(encoding="utf-8")
DEMO = scenarios.DEMO_ID


def at_step(index):
    """The demo moved on to a step without playing it (the presenter's skip)."""
    state = scenarios.load_scenario(DEMO)
    while state["scenario"]["step"] < index:
        state, _jumped = scenarios.next_step(state)
    return state


# ---- the start ------------------------------------------------------------------------------------


def test_the_day_starts_in_bed_with_rain_and_the_start_money():
    state = scenarios.load_scenario(DEMO)
    assert state["day"] == 1 and state["shift"] is None and state["cash"] == logic.STARTING_CASH
    assert state["day_override"] == {"weather": "rain", "event": "none"}
    wake = world.DORM["wake"]
    assert (state["player"]["x"], state["player"]["y"]) == (wake["x"], wake["y"])
    assert logic.outfits_of(state) == logic.new_outfits()
    assert all(units == 0 for units in state["stock"].values())
    # the forecast of the day shows the rain the card speaks of (the override makes it always right)
    assert logic.outlook(state)["weather"] == "rain" and "rain" in scenarios.STEPS[0]["text"]


def test_the_start_money_pays_the_jacket_and_the_stock_with_money_left():
    state = logic.buy_outfit(scenarios.load_scenario(DEMO), "raincoat")
    need = scenarios.need(state, "coffee")
    assert need > 0
    after = logic.buy(state, "coffee", need)
    assert after["cash"] > 0 and isinstance(after["cash"], int)


# ---- moving on -------------------------------------------------------------------------------------


def test_a_manual_step_waits_for_the_button():
    state = scenarios.load_scenario(DEMO)
    assert scenarios.advance(state) is state and not scenarios.step_done(state)
    card = scenarios.demo_view(state)["active"]
    assert card["id"] == "wake-up" and card["call_next"] is True and card["target"] is None
    moved, jumped = scenarios.next_step(state)
    assert not jumped and moved["scenario"]["step"] == 1 and moved["cash"] == state["cash"]


def test_continuous_steps_move_on_by_themselves():
    state = at_step(1)
    dressed = logic.buy_outfit(state, "raincoat")
    before = copy.deepcopy(dressed)
    moved = scenarios.advance(dressed)
    assert dressed == before  # advance builds a new state
    assert moved["scenario"]["step"] == 2
    ordered = scenarios.advance(logic.buy(moved, "coffee", scenarios.need(moved, "coffee")))
    assert ordered["scenario"]["step"] == 3
    # not enough coffee: the card stays
    short = scenarios.advance(logic.buy(moved, "coffee", 1))
    assert short["scenario"]["step"] == 2


def test_a_jump_waits_for_its_button_and_the_card_shows_it():
    state = at_step(3)
    state = logic.open_day(state)
    state["shift"]["sold"] = {"coffee": scenarios.need(state, "coffee")}  # as if the shift sold it all
    assert scenarios.step_done(state)
    assert scenarios.advance(state) is state  # the next step is a jump: no automatic load
    card = scenarios.demo_view(state)["active"]
    assert card["id"] == "beach-cafe" and card["call_next"] is True and card["button"] == "Beach Cafe"
    jumped, did = scenarios.next_step(state)
    assert did and jumped == scenarios.load_step(4)


def test_the_jumps_keep_the_jacket_and_the_day():
    for index in (4, 5):
        state = scenarios.load_step(index)
        assert logic.outfits_of(state)["worn"] == "raincoat" and state["day"] == 1
        assert state["shift"] is not None  # the day is open: guests are on their way


def test_the_cafe_shift_opens_the_day_first():
    state = at_step(3)
    assert scenarios.demo_view(state)["active"]["open_day"] is True
    assert scenarios.demo_view(logic.open_day(state))["active"]["open_day"] is False


def test_the_texts_carry_today_s_demand():
    state = at_step(2)
    need = scenarios.need(state, "coffee")
    card = scenarios.demo_view(state)["active"]
    assert f"{need} coffee" in card["text"] and f"{need} coffee" in card["goal"]
    assert scenarios.NEED not in card["text"] and scenarios.NEED not in card["goal"]


def test_the_last_step_cannot_go_further():
    state = at_step(len(scenarios.STEPS) - 1)
    with pytest.raises(logic.RejectedAction):
        scenarios.next_step(state)
    with pytest.raises(logic.RejectedAction):
        scenarios.next_step(logic.new_state(1))


@pytest.mark.parametrize("bad", [None, -1, 1, 2, 3, 6, 7, True, "4", [4], 4.0])
def test_only_the_start_and_the_jumps_can_be_loaded(bad):
    with pytest.raises(logic.RejectedAction):
        scenarios.load_step(bad)


# ---- the screen ------------------------------------------------------------------------------------


def test_every_target_has_a_spot_on_the_screen():
    spots = re.search(r"const DEMO_SPOTS = \{(.*?)\n\};", UI, re.S).group(1)
    for target in scenarios.TARGETS:
        if target is not None:
            assert re.search(rf"^\s*{target}:", spots, re.M), target
    view = world.world_view()
    assert {"supplier"} <= set(view["locations"]) and "wardrobe" in view["dorm"] and "bed" in view["dorm"]
    assert "cafe" in view["work_spots"] and "beach_cafe" in view["guests"]["lines"]


def test_the_card_sends_no_state_and_writes_text_only():
    assert "innerHTML" not in DEMO_JS and "Math.random" not in DEMO_JS
    assert 'send("/api/demo/next", {})' in UI
    for path in (ROOT / "static/world").glob("*.js"):
        assert "Math.random" not in path.read_text(encoding="utf-8"), path.name


def test_next_waits_in_the_queue_of_the_ticks_and_is_kept():
    at = UI.index('send("/api/demo/next"')
    start = UI.rindex("requests.run(", 0, at)
    assert "\n\n" not in UI[start:at]
    end = UI.index("{ keep: true }", at)
    assert "requests.run(" not in UI[at:end]
    assert "freshRun(data)" in UI[at:end]  # a jump starts over on the map like a load


# ---- the endpoint ----------------------------------------------------------------------------------


@pytest.fixture
def run_on_disk(tmp_path, monkeypatch):
    path = tmp_path / "run.db"
    db.save(logic.buy(logic.new_state(7), "coffee", 10), path)
    real_save, real_new_run = db.save, db.save_new_run
    monkeypatch.setattr(app, "load_run", lambda: db.load(path))
    monkeypatch.setattr(app.db, "save", lambda s: real_save(s, path))
    monkeypatch.setattr(app.db, "save_new_run", lambda s: real_new_run(s, path))
    return path


def test_next_without_a_demo_is_refused_and_changes_nothing(run_on_disk):
    before, raw = db.load(run_on_disk), run_on_disk.read_bytes()
    response = app.app.test_client().post("/api/demo/next", json={})
    assert response.status_code == 400
    assert db.load(run_on_disk) == before and run_on_disk.read_bytes() == raw


@pytest.mark.parametrize("body", [{"step": 5}, {"id": DEMO}, {"state": {"cash": 1}}, {"confirm": True}])
def test_next_takes_no_fields(run_on_disk, body):
    client = app.app.test_client()
    client.post("/api/demo/load", json={"id": DEMO, "confirm": True})
    before, raw = db.load(run_on_disk), run_on_disk.read_bytes()
    response = client.post("/api/demo/next", json=body)
    assert response.status_code == 400
    text = response.get_data(as_text=True)
    assert "Traceback" not in text and ".py" not in text
    assert db.load(run_on_disk) == before and run_on_disk.read_bytes() == raw


def test_the_last_next_is_refused_and_changes_nothing(run_on_disk):
    client = app.app.test_client()
    client.post("/api/demo/load", json={"id": DEMO, "confirm": True})
    for _ in range(len(scenarios.STEPS) - 1):
        assert client.post("/api/demo/next", json={}).status_code == 200
    before = db.load(run_on_disk)
    assert client.post("/api/demo/next", json={}).status_code == 400
    assert db.load(run_on_disk) == before


def test_the_whole_day_plays_through_the_api(run_on_disk):
    client = app.app.test_client()

    def card(response):
        assert response.status_code == 200, response.get_json()
        return response.get_json()["state"]["demo"]["active"]

    assert card(client.post("/api/demo/load", json={"id": DEMO, "confirm": True}))["id"] == "wake-up"
    assert card(client.post("/api/demo/next", json={}))["id"] == "get-dressed"
    assert card(client.post("/api/outfit/buy", json={"outfit": "raincoat"}))["id"] == "order-stock"
    need = scenarios.need(db.load(run_on_disk), "coffee")
    assert card(client.post("/api/buy", json={"product": "coffee", "quantity": str(need)}))["id"] == "cafe-shift"
    client.post("/api/day/open", json={})
    client.post("/api/shift/start", json={"shop": "cafe"})
    shown = None
    for _ in range(120):
        state = db.load(run_on_disk)
        space = logic.SHOPS["cafe"]["counter"] - sum(state["shift"]["counter"].values())
        carry = min(space, state["stock"]["coffee"])
        if carry:
            client.post("/api/shift/refill", json={"product": "coffee", "quantity": carry})
        while client.post("/api/shift/sell", json={"product": "coffee"}).status_code == 200:
            pass
        shown = card(client.post("/api/shift/tick", json={}))
        if shown["id"] == "beach-cafe":
            break
    assert shown["id"] == "beach-cafe" and shown["call_next"]
    # the demand of the day is really gone: nobody waits, nobody left
    state = db.load(run_on_disk)
    assert state["shift"]["lost"] == 0
    jump = client.post("/api/demo/next", json={})
    assert jump.get_json()["jumped"] is True and card(jump)["id"] == "beach-cafe"
    client.post("/api/shop/unlock", json={"shop": "beach_cafe"})
    shown = card(client.post("/api/shop/upgrade", json={"shop": "beach_cafe", "item": "staff_1"}))
    assert shown["id"] == "rain-again" and shown["call_next"]
    assert card(client.post("/api/demo/next", json={}))["id"] == "rain-again"
    for _ in range(60):
        while client.post("/api/shift/sell", json={"product": "coffee"}).status_code == 200:
            pass
        state = db.load(run_on_disk)
        if state["shift"]["counter"].get("coffee", 0) < 5:
            client.post("/api/shift/refill", json={"product": "coffee", "quantity": 10})
        shown = card(client.post("/api/shift/tick", json={}))
        if shown["id"] == "end-the-day":
            break
    assert shown["id"] == "end-the-day" and not shown["done"]
    shown = card(client.post("/api/shift/skip", json={}))
    assert shown["id"] == "end-the-day" and shown["done"] and shown["last"]
    saved = db.load(run_on_disk)
    assert saved["day"] == 2 and saved["history"][-1]["day"] == 1
    finish = client.post("/api/demo/finish", json={})
    assert finish.status_code == 200 and finish.get_json()["state"]["demo"]["active"] is None


def test_public_next_changes_only_the_own_run(monkeypatch, tmp_path):
    monkeypatch.setenv("CT_PUBLIC", "1")
    monkeypatch.setattr(app, "PLAYERS_DIR", tmp_path / "players")
    app._hits.clear()
    try:
        first, second = app.app.test_client(), app.app.test_client()
        first.get("/")
        second.get("/")
        first.post("/api/demo/load", json={"id": DEMO, "confirm": True})
        second.get("/api/state")
        files = sorted((tmp_path / "players").glob("*.db"))
        other = {f: db.load(f) for f in files}
        response = first.post("/api/demo/next", json={})
        assert response.status_code == 200 and "Content-Security-Policy" in response.headers
        assert "seed" not in response.get_json()["state"]
        assert len([f for f in files if db.load(f) != other[f]]) == 1
        assert second.post("/api/demo/next", json={}).status_code == 400  # no demo in the other run
    finally:
        app._hits.clear()


@pytest.mark.parametrize("index", [3, 5])
def test_a_guest_who_left_does_not_stop_the_demo(index):
    """The live run showed it: a guest who leaves unserved must not leave the card stuck. Once the
    player's own shift is over, the shift has been shown and the card goes on."""
    state = at_step(index)
    if state["shift"] is None:
        state = logic.open_day(state)
    if state["shift"]["shop"] is None:
        state = logic.start_shift(state, "cafe")
    for _ in range(logic.SHIFT_TICKS):  # nobody served: every guest leaves
        state, _result = logic.tick(state)
    assert state["shift"]["over"] and not state["shift"].get("staffed")
    assert scenarios.step_done(state)


# ---- checks moved here from test_demo_scenarios.py (review finding: new checks go in new files) ---------

LOADED = [i for i, step in enumerate(scenarios.STEPS) if step["state"] is not None]


def test_only_the_start_and_the_two_jumps_have_a_state():
    assert LOADED == [0, 4, 5]
    assert scenarios.load_scenario(DEMO) == scenarios.load_step(0)
    weathers = [scenarios.load_step(i)["day_override"]["weather"] for i in LOADED]
    assert weathers == ["rain", "sun", "rain"]  # the jumps bring the other weather


@pytest.mark.parametrize("index", range(len(scenarios.STEPS)))
def test_every_step_plays_on_day_1_and_has_one_placeholder_at_most(index):
    step = scenarios.STEPS[index]
    for field in ("title", "text", "goal_text", "button"):
        assert "{" not in step[field].replace(scenarios.NEED, "")  # only the one placeholder
    if step["state"] is not None:
        assert step["state"]["day"] == scenarios.DAY
        assert "outfits" in scenarios.load_step(index)


def test_loading_does_not_change_the_outfits_in_the_data():
    before = copy.deepcopy(scenarios.SCENARIOS)
    for index in LOADED:
        scenarios.load_step(index)["outfits"]["owned"].append("x")
    assert scenarios.SCENARIOS == before


@pytest.mark.parametrize("bad", ["grow", "serve-the-cafe", "guests-decide", "other-day-other-choice"])
def test_the_old_scenarios_are_gone(bad):
    with pytest.raises(logic.RejectedAction):
        scenarios.load_scenario(bad)


@pytest.mark.parametrize("saved", [{"id": "grow"}, {"id": DEMO}, {"id": DEMO, "step": 99}, {"id": DEMO, "step": -1},
                                   {"id": DEMO, "step": "1"}, {"id": DEMO, "step": True},
                                   {"id": ["demo-day"], "step": 0}, {"id": {"x": 1}, "step": 0}])
def test_a_damaged_saved_demo_counts_as_none_and_never_raises(saved):
    """Review finding: an id that is a list or a dict raised in the lookup and broke every request."""
    state = logic.new_state(1)
    state["scenario"] = saved
    assert scenarios.active(state) is None and not scenarios.step_done(state)
    view = scenarios.demo_view(state)
    assert view["active"] is None and view["stale"] is True
    assert scenarios.advance(state) is state
    with pytest.raises(logic.RejectedAction):
        scenarios.next_step(state)


def test_a_watched_rainy_step_is_not_done_at_its_start():
    assert not scenarios.step_done(scenarios.load_step(5))


def test_the_card_never_sends_the_seed():
    for index in range(len(scenarios.STEPS)):
        assert "seed" not in repr(scenarios.demo_view(at_step(index)))


def test_the_card_keeps_the_pace_of_the_running_step():
    """Review finding: once the Cafe shift is done the card shows the jump, but the open day still runs
    at the Cafe shift's pace."""
    state = logic.open_day(at_step(3))
    state["shift"]["sold"] = {"coffee": scenarios.need(state, "coffee")}
    card = scenarios.demo_view(state)["active"]
    assert card["id"] == "beach-cafe" and card["tick_ms"] == scenarios.STEPS[3]["tick_ms"]


@pytest.mark.parametrize("body", [{"id": "grow", "confirm": True}, {"id": DEMO, "confirm": True, "step": 5}])
def test_a_load_of_an_old_scenario_or_a_step_is_refused(run_on_disk, body):
    before, raw = db.load(run_on_disk), run_on_disk.read_bytes()
    assert app.app.test_client().post("/api/demo/load", json=body).status_code == 400
    assert db.load(run_on_disk) == before and run_on_disk.read_bytes() == raw


def test_the_card_ignores_a_second_click_while_one_is_on_its_way():
    """Review finding: a double click on the big button skipped a whole step."""
    assert "let busy = false;" in DEMO_JS and "if (busy) return;" in DEMO_JS
    assert '$("#demo-go").addEventListener("click", once(' in DEMO_JS
    assert '$("#demo-skip").addEventListener("click", once(' in DEMO_JS


def test_the_walk_waits_for_the_sunrise_and_other_walks_clear_a_demo_spot():
    assert "await demoNight;" in UI and "demoNight = nightToMorning()" in UI
    main = (ROOT / "static/world/main.js").read_text(encoding="utf-8")
    for name in ("goHome", "walkToPlace", "wakeAt"):
        body = re.search(rf"^function {name}\(.*?^}}$", main, re.S | re.M).group(0)
        assert "pendingSpot = null;" in body, name
