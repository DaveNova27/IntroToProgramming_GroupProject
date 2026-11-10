"""Campus events and trends (specs/events-and-disruptions.md, issue #14)."""

import copy
import re
from collections import Counter
from fractions import Fraction
from pathlib import Path

import pytest

import app
import db
import logic

SEEDS = range(1, 201)
DAYS = range(1, logic.LAST_DAY + 1)


def state_with(weather=None, event=None, seed=1):
    return logic.set_day_override(logic.new_state(seed), weather, event)


# --- the table ---------------------------------------------------------------

def test_the_table_has_the_four_events_with_sane_numbers():
    assert set(logic.EVENTS) == {"exam_period", "party", "career_fair", "surf_festival"}
    for event in logic.EVENTS.values():
        assert event["weight"] > 0
        assert event["days"] in (1, 2, 3)
        assert set(event["demand_percent"]) == set(logic.SHOPS)
        assert all(isinstance(p, int) and 0 <= p <= 300 for p in event["demand_percent"].values())
        assert isinstance(event["visitors_percent"], int) and 0 <= event["visitors_percent"] <= 300
    assert logic.MAX_EVENT_DAYS == 3


# --- the roll ----------------------------------------------------------------

def test_the_same_seed_gives_the_same_event_in_any_order():
    forward = {(s, d): logic.make_event(s, d) for s in range(1, 30) for d in DAYS}
    backward = {(s, d): logic.make_event(s, d) for s in range(29, 0, -1) for d in reversed(DAYS)}
    assert forward == backward


def test_the_first_two_days_are_quiet():
    assert logic.FIRST_EVENT_DAY == 3
    for seed in SEEDS:
        assert logic.make_event(seed, 1) is None and logic.make_event(seed, 2) is None
        assert logic.event_starting(seed, 1) is None and logic.event_starting(seed, 2) is None


def test_events_do_not_change_the_weather_or_the_temperature():
    for seed in range(1, 40):
        for day in DAYS:
            plain = logic.make_day_context(seed, day)
            named = logic.make_day_context(seed, day, {"event": "party"})
            assert (plain["weather"], plain["temperature"], plain["demand_percent"]) == (
                named["weather"], named["temperature"], named["demand_percent"])


def test_how_often_events_come_is_about_what_the_table_says():
    on = starts = 0
    kinds = Counter()
    for seed in SEEDS:
        for day in DAYS:
            on += logic.make_event(seed, day) is not None
            event = logic.event_starting(seed, day)
            if event:
                starts += 1
                kinds[event] += 1
    total_days = len(SEEDS) * len(DAYS)
    quiet_days = len(SEEDS) * (logic.FIRST_EVENT_DAY - 1)
    # starts: 30 % of the days from day 3 on (wide guard band)
    share = starts / (total_days - quiet_days)
    assert 0.25 <= share <= 0.35
    # an event is on during a good part of the season: not rare, not constant
    assert 0.25 <= on / total_days <= 0.55
    weights = {k: e["weight"] for k, e in logic.EVENTS.items()}
    for kind, weight in weights.items():
        expected = weight / sum(weights.values())
        assert abs(kinds[kind] / starts - expected) < 0.06, kind


def find_start(event_id, day):
    """A seed on which `event_id` starts on `day` and nothing newer starts during its run."""
    run = logic.EVENTS[event_id]["days"]
    for seed in range(1, 5000):
        if logic.event_starting(seed, day) == event_id and all(
                logic.event_starting(seed, day + k) is None for k in range(1, run)):
            return seed
    raise AssertionError("no such seed")


def test_a_three_day_event_runs_for_three_days_with_its_day_counted():
    seed = find_start("surf_festival", 5)
    for day_of, day in enumerate((5, 6, 7), start=1):
        assert logic.make_event(seed, day) == {
            "id": "surf_festival", "name": "Surf festival", "day_of": day_of, "days": 3}
    after = logic.make_event(seed, 8)
    assert after is None or after["id"] != "surf_festival" or after["day_of"] == 1


def test_a_newer_start_replaces_a_running_event():
    for seed in range(1, 5000):
        first, second = logic.event_starting(seed, 5), logic.event_starting(seed, 6)
        if first == "surf_festival" and second and second != "surf_festival":
            assert logic.make_event(seed, 5)["id"] == "surf_festival"
            assert logic.make_event(seed, 6) == {
                "id": second, "name": logic.EVENTS[second]["name"], "day_of": 1,
                "days": logic.EVENTS[second]["days"]}
            return
    raise AssertionError("no such seed")


# --- the override ------------------------------------------------------------

def test_a_weather_only_override_means_no_event():
    for seed in range(1, 60):
        state = state_with("rain", seed=seed)
        state["day"] = 10
        assert logic.day_context(state)["event"] is None


def test_an_override_can_name_an_event_or_none():
    state = state_with(None, "party")  # day 1 is quiet for the seed: the override still wins
    context = logic.day_context(state)
    assert context["event"] == {"id": "party", "name": "Party", "day_of": 1, "days": 1}
    assert context["weather"] == logic.make_day_context(state["seed"], 1)["weather"]
    assert logic.day_context(state_with("sun", "none"))["event"] is None
    assert logic.day_context(state_with(None, "none"))["event"] is None


def test_clearing_the_override_gives_the_seeds_event_back():
    for seed in range(1, 60):
        state = logic.set_day_override(state_with("sun", "party", seed), None)
        assert state["day_override"] is None
        state["day"] = 12
        assert logic.day_context(state)["event"] == logic.make_event(seed, 12)


def test_an_unknown_saved_event_counts_as_none():
    assert logic.make_event(1, 10, {"event": "dragon"}) is None
    assert logic.make_event(1, 10, {"event": 7}) is None
    assert logic.make_event(1, 10, "party") == logic.make_event(1, 10)  # not a dictionary: no override


@pytest.mark.parametrize("weather,event", [
    ("monsoon", None), (3, None), (None, "dragon"), (None, 7), (None, ["party"]), ("sun", "Party"),
    (None, True),
])
def test_bad_overrides_are_refused_and_change_nothing(weather, event):
    state = state_with("rain", "party")
    before = copy.deepcopy(state)
    with pytest.raises(logic.RejectedAction):
        logic.set_day_override(state, weather, event)
    assert state == before


def test_the_override_is_saved_in_the_shape_the_spec_names():
    assert logic.set_day_override(logic.new_state(), "sun")["day_override"] == {"weather": "sun"}
    assert logic.set_day_override(logic.new_state(), None, "party")["day_override"] == {"event": "party"}
    assert logic.set_day_override(logic.new_state(), "sun", "none")["day_override"] == {
        "weather": "sun", "event": "none"}
    assert logic.set_day_override(logic.new_state(), None)["day_override"] is None


# --- the customers -----------------------------------------------------------

def exact_customers(shop, weather_id, event_id=None):
    """The customers of a shop's product at its reference price, worked out by hand from the
    tables (not by the rule), as an exact number."""
    w = logic.WEATHER[weather_id]["demand_percent"][shop]
    mix = logic.SHOP_MIX[shop]
    students = Fraction(w, 100)
    visitors = Fraction(w * logic.VISITOR_WEATHER[weather_id], 10_000)
    if event_id:
        e = logic.EVENTS[event_id]
        students *= Fraction(e["demand_percent"][shop], 100)
        visitors *= Fraction(e["demand_percent"][shop] * e["visitors_percent"], 10_000)
    return mix["students"] * students + mix["visitors"] * visitors


@pytest.mark.parametrize("shop,product,weather,event", [
    ("cafe", "coffee", "rain", "exam_period"),
    ("cafe", "coffee", "sun", "career_fair"),
    ("surf_shop", "surfboard", "sun", "surf_festival"),
    ("merchandise", "hoodie", "rain", "career_fair"),
    ("beach_cafe", "beer", "storm", "party"),
])
def test_weather_and_event_multiply_exactly(shop, product, weather, event):
    state = state_with(weather, event)
    expected = min(logic.MAX_CUSTOMERS, int(exact_customers(shop, weather, event) + Fraction(1, 2)))
    assert logic.customers_today(state, product) == expected


def test_a_cafe_on_a_rainy_exam_day_has_more_customers_than_on_a_plain_rainy_day():
    assert logic.customers_today(state_with("rain", "exam_period"), "coffee") == 19
    assert logic.customers_today(state_with("rain"), "coffee") == 13


def test_a_hot_party_at_the_beach_cafe_is_stopped_by_the_cap():
    assert exact_customers("beach_cafe", "heat", "party") > logic.MAX_CUSTOMERS
    assert logic.customers_today(state_with("heat", "party"), "beer") == logic.MAX_CUSTOMERS


def test_no_event_changes_nothing_against_the_plain_weather_number():
    for weather in logic.WEATHER:
        assert logic.customers_today(state_with(weather), "coffee") == \
            logic.customers_today(state_with(weather, "none"), "coffee")


def test_every_shop_every_event_every_weather_stays_inside_the_cap():
    products = ("coffee", "surfboard", "hoodie", "beer")
    for weather in logic.WEATHER:
        for event in logic.EVENTS:
            state = state_with(weather, event)
            for product in products:
                assert 0 <= logic.customers_today(state, product) <= logic.MAX_CUSTOMERS


def test_the_explanation_names_the_event_only_on_an_event_day():
    steps = logic.customer_breakdown(state_with("rain", "exam_period"), "coffee")["steps"]
    assert "Event: Exam period" in [s["name"] for s in steps]
    plain = logic.customer_breakdown(state_with("rain"), "coffee")["steps"]
    assert not any(s["name"].startswith("Event") for s in plain)


def test_the_breakdown_total_is_the_number_everyone_uses():
    state = logic.buy(state_with("rain", "exam_period"), "coffee", 30)
    number = logic.customers_today(state, "coffee")
    assert logic.customer_breakdown(state, "coffee")["customers"] == number
    _after, result = logic.trade_day(state)
    line = next(item for item in result["lines"] if item["product"] == "coffee")
    assert line["demand"] == number
    assert logic.start_shift(state, "cafe")["shift"]["planned"]["coffee"] == number


# --- the screen's answer and the endpoints ------------------------------------

@pytest.fixture
def api(tmp_path, monkeypatch):
    path = tmp_path / "run.db"
    db.save(logic.new_state(7), path)
    real_save, real_new = db.save, db.save_new_run
    monkeypatch.setattr(app, "load_run", lambda: db.load(path))
    monkeypatch.setattr(app.db, "save", lambda s: real_save(s, path))
    monkeypatch.setattr(app.db, "save_new_run", lambda s: real_new(s, path))
    monkeypatch.setenv("CT_EDITOR", "1")
    monkeypatch.setenv("CAMPUS_TYCOON_DEMO", "1")
    client = app.app.test_client()
    client.path = path
    return client


def saved(client):
    return db.load(client.path)


def test_the_state_shows_the_event_only_once_the_day_is_open(api):
    assert api.post("/api/editor/weather", json={"weather": "rain", "event": "exam_period"}).status_code == 200
    assert api.get("/api/state").get_json()["event"] is None
    assert api.post("/api/day/open", json={}).status_code == 200
    opened = api.get("/api/state").get_json()
    assert opened["event"] == {"id": "exam_period", "name": "Exam period", "day_of": 1, "days": 2}


def test_the_state_never_contains_the_seed_or_the_table_internals(api):
    text = api.get("/api/state").get_data(as_text=True)
    assert '"seed"' not in text
    assert "visitors_percent" not in text


def test_the_demo_switch_takes_an_event(api):
    response = api.post("/api/day-override", json={"weather": "sun", "event": "party"})
    assert response.status_code == 200
    assert saved(api)["day_override"] == {"weather": "sun", "event": "party"}
    assert "Party" in response.get_json()["message"]
    cleared = api.post("/api/day-override", json={})
    assert cleared.status_code == 200 and saved(api)["day_override"] is None


def test_the_editor_takes_an_event_and_clears_it(api):
    assert api.post("/api/editor/weather", json={"weather": None, "event": "career_fair"}).status_code == 200
    assert saved(api)["day_override"] == {"event": "career_fair"}
    info = api.get("/api/state").get_json()["editor_info"]
    assert info["event_override"] == "career_fair"
    assert [e["id"] for e in info["events"]] == list(logic.EVENTS)
    assert api.post("/api/editor/weather", json={"weather": None, "event": None}).status_code == 200
    assert saved(api)["day_override"] is None


@pytest.mark.parametrize("body", [
    {"event": "dragon"}, {"event": 5}, {"event": ["party"]}, {"weather": "sun", "event": "PARTY"},
])
def test_a_bad_event_is_refused_by_both_endpoints_and_changes_nothing(api, body):
    api.post("/api/editor/weather", json={"weather": "rain", "event": "party"})
    before = saved(api)
    for url in ("/api/editor/weather", "/api/day-override"):
        response = api.post(url, json=body)
        assert response.status_code == 400 and response.get_json()["error"]
        assert saved(api) == before


def test_the_demo_endpoint_with_the_switch_off_refuses_an_event(api, monkeypatch):
    monkeypatch.delenv("CAMPUS_TYCOON_DEMO")
    before = saved(api)
    assert api.post("/api/day-override", json={"event": "party"}).status_code == 400
    assert saved(api) == before


def test_editor_state_patches_take_the_new_shape_and_refuse_the_rest(api):
    ok = api.post("/api/editor/state", json={"patch": {"day_override": {"weather": "heat", "event": "party"}}})
    assert ok.status_code == 200
    assert saved(api)["day_override"] == {"weather": "heat", "event": "party"}
    assert api.post("/api/editor/state", json={"patch": {"day_override": {"event": "none"}}}).status_code == 200
    assert saved(api)["day_override"] == {"event": "none"}
    before = saved(api)
    for bad in ({}, {"mood": "sad"}, {"weather": "sun", "mood": 1}, {"event": "dragon"}, "party", 5):
        response = api.post("/api/editor/state", json={"patch": {"day_override": bad}})
        assert response.status_code == 400, bad
        assert saved(api) == before
    assert api.post("/api/editor/state", json={"patch": {"day_override": None}}).status_code == 200
    assert saved(api)["day_override"] is None


def coffee_of(state):
    return next(p for p in state["products"] if p["id"] == "coffee")


def test_an_event_changes_the_number_the_screen_gets_once_the_day_is_open(api):
    assert api.post("/api/day/open", json={}).status_code == 200
    api.post("/api/editor/weather", json={"weather": "rain", "event": "none"})
    plain = api.get("/api/state").get_json()
    api.post("/api/editor/weather", json={"weather": "rain", "event": "exam_period"})
    exam = api.get("/api/state").get_json()
    assert coffee_of(plain)["customers"] == 13 and coffee_of(exam)["customers"] == 19
    assert any(step["name"] == "Event: Exam period" for step in coffee_of(exam)["breakdown"]["steps"])


def test_before_the_day_is_open_the_numbers_do_not_show_the_event(api):
    api.post("/api/editor/weather", json={"weather": "rain", "event": "exam_period"})
    closed = api.get("/api/state").get_json()
    assert closed["event"] is None
    assert coffee_of(closed)["customers"] == 13  # the forecast's weather, no event
    assert not any(step["name"].startswith("Event") for step in coffee_of(closed)["breakdown"]["steps"])


# --- the markup and the script that send and show it (read as files, like the other page tests) ----

STATIC = Path(__file__).resolve().parent.parent / "static"
UI = (STATIC / "world" / "ui.js").read_text()
MAP_HTML = (STATIC / "map.html").read_text()
INDEX_HTML = (STATIC / "index.html").read_text()
APP_JS = (STATIC / "app.js").read_text()


def test_the_editor_form_sends_both_fields_and_has_a_way_back_to_the_seed():
    assert re.search(r'<select name="event"', UI)
    assert 'value="clear"' in UI and 'value="fix"' in UI
    assert 'weather: f.weather.value || null, event: f.event.value' in UI
    assert 'weather: null, event: null' in UI  # "Seed's" clears both


def test_the_event_is_shown_only_while_the_day_is_open():
    assert 'id="stat-event"' in MAP_HTML and 'class="stat stat-event" hidden' in MAP_HTML
    assert re.search(r'const eventLine = open \? eventText\(state\.event\) : ""', UI)
    assert 'id="event-chip"' in INDEX_HTML and "hidden" in INDEX_HTML.split('id="event-chip"')[1].split(">")[0]
    assert re.search(r'dayIsOpen\(state\) \? eventText\(state\.event\) : ""', APP_JS)


def test_event_names_reach_the_page_only_through_text_or_escaping():
    assert 'esc(eventText(state.event))' in UI
    assert '$("#stat-event").textContent = eventLine' in UI
    assert '$("#event-chip").textContent = eventLine' in APP_JS
    assert "esc(ev.name)" in UI and "esc(ev.id)" in UI
