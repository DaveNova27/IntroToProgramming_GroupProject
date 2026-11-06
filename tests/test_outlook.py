"""Checks from specs/outlook.md ("Done when"). One test per check."""

import copy

import pytest

import app
import db
import logic

SEED = 987654321  # distinctive, so a leak into an answer is easy to see


@pytest.fixture
def run_on_disk(tmp_path, monkeypatch):
    """The real API on a temporary save, so the player's own run stays untouched."""
    path = tmp_path / "run.db"
    db.save(logic.new_state(SEED), path)
    real_save = db.save
    monkeypatch.setattr(app, "load_run", lambda: db.load(path))
    monkeypatch.setattr(app.db, "save", lambda state: real_save(state, path))
    return path


def is_miss(seed, day, override=None):
    """True when the forecast for `day` shows another weather than the real one."""
    forecast = logic.make_outlook(seed, day, override)
    return forecast["weather"] != logic.make_day_context(seed, day, override)["weather"]


def a_seed_whose_forecast_for_day_1_is_wrong():
    return next(seed for seed in range(1, 1000) if is_miss(seed, 1))


OUTLOOK_FIELDS = {"day", "id", "name", "temp_low", "temp_high", "miss_percent", "tips"}


# ---- Check 1: the same seed and day give the same forecast -----------------

def test_the_same_seed_and_day_always_give_the_same_forecast():
    forward = [logic.make_outlook(SEED, d) for d in range(2, 31)]
    backward = [logic.make_outlook(SEED, d) for d in range(30, 1, -1)][::-1]
    assert forward == backward
    other = [logic.make_outlook(SEED + 1, d) for d in range(2, 31)]
    assert forward != other


def test_the_forecast_does_not_change_the_real_weather():
    before = [logic.make_day_context(SEED, d) for d in range(1, 31)]
    for d in range(2, 31):
        logic.make_outlook(SEED, d)
    assert [logic.make_day_context(SEED, d) for d in range(1, 31)] == before


def test_before_opening_the_forecast_is_for_today_and_while_open_for_tomorrow():
    state = logic.new_state(SEED)
    state["day"] = 7
    assert logic.outlook(state) == logic.make_outlook(SEED, 7)
    opened = logic.open_day(state)
    assert logic.outlook(opened) == logic.make_outlook(SEED, 8)


# ---- Check 2: wrong about OUTLOOK_MISS_PERCENT of the time ------------------

def test_the_forecast_is_wrong_about_the_miss_percent_of_the_time():
    days = [(seed, day) for seed in range(1, 201) for day in range(2, 31)]
    misses = sum(is_miss(seed, day) for seed, day in days)
    share = 100 * misses / len(days)
    assert logic.OUTLOOK_MISS_PERCENT - 5 <= share <= logic.OUTLOOK_MISS_PERCENT + 5


def test_a_wrong_forecast_shows_a_neighbour_and_a_right_one_the_real_weather():
    for seed in range(1, 101):
        for day in range(2, 31):
            real = logic.make_day_context(seed, day)["weather"]
            shown = logic.make_outlook(seed, day)["weather"]
            assert shown == real or shown in logic.OUTLOOK_MISS[real]


def test_the_miss_table_names_only_other_known_weathers():
    assert set(logic.OUTLOOK_MISS) == set(logic.WEATHER)
    for real, shown in logic.OUTLOOK_MISS.items():
        assert shown and real not in shown and set(shown) <= set(logic.WEATHER)


def test_the_forecast_shows_the_range_of_its_weather_in_whole_degrees():
    for day in range(2, 31):
        forecast = logic.make_outlook(SEED, day)
        assert forecast["temp_range"] == logic.WEATHER[forecast["weather"]]["temp"]
        assert all(isinstance(t, int) for t in forecast["temp_range"])


# ---- Check 3: an override makes the forecast right -------------------------

@pytest.mark.parametrize("weather", list(logic.WEATHER))
def test_with_an_override_the_forecast_is_that_weather(weather):
    state = logic.set_day_override(logic.new_state(SEED), weather)
    for day in range(1, logic.LAST_DAY + 1):
        state["day"] = day
        assert logic.outlook(state)["weather"] == weather
        assert not is_miss(SEED, day, state["day_override"])


# ---- Check 4: when there is a forecast -------------------------------------

def test_the_last_day_has_a_forecast_until_it_is_opened_and_none_after_the_season():
    state = logic.new_state(SEED)
    state["day"] = logic.LAST_DAY
    assert logic.outlook(state) == logic.make_outlook(SEED, logic.LAST_DAY)
    assert logic.outlook(logic.open_day(state)) is None
    state["day"] = logic.LAST_DAY + 1
    assert logic.outlook(state) is None


def test_there_is_a_forecast_while_a_day_is_open():
    state = logic.open_day(logic.new_state(SEED))
    assert logic.outlook(state) == logic.make_outlook(SEED, 2)


# ---- Check 5: the tips -----------------------------------------------------

def expected_advice(percent):
    if percent >= logic.OUTLOOK_MORE_AT:
        return "more"
    if percent <= logic.OUTLOOK_LESS_AT:
        return "less"
    return "normal"


@pytest.mark.parametrize("weather", list(logic.WEATHER))
def test_the_tips_name_every_unlocked_shop_with_the_forecast_factor(weather):
    state = logic.set_day_override(logic.new_state(SEED), weather)
    state["cash"] = 1_000_000
    state = logic.unlock_shop(state, "surf_shop")
    tips = logic.outlook_tips(state)
    assert [t["shop"] for t in tips] == ["cafe", "surf_shop"]  # in the order of SHOPS
    for tip in tips:
        percent = logic.WEATHER[weather]["demand_percent"][tip["shop"]]
        assert tip == {"shop": tip["shop"], "percent": percent, "advice": expected_advice(percent)}


@pytest.mark.parametrize("percent, advice", [
    (logic.OUTLOOK_MORE_AT, "more"), (logic.OUTLOOK_MORE_AT + 1, "more"),
    (logic.OUTLOOK_MORE_AT - 1, "normal"), (100, "normal"), (logic.OUTLOOK_LESS_AT + 1, "normal"),
    (logic.OUTLOOK_LESS_AT, "less"), (logic.OUTLOOK_LESS_AT - 1, "less"),
])
def test_the_thresholds_give_more_less_and_normal(monkeypatch, percent, advice):
    # its own factor, so balancing the placeholder table later does not break this test
    monkeypatch.setitem(logic.WEATHER["rain"]["demand_percent"], "cafe", percent)
    state = logic.set_day_override(logic.new_state(SEED), "rain")
    assert logic.outlook_tips(state) == [{"shop": "cafe", "percent": percent, "advice": advice}]


def test_tips_from_a_given_forecast_match_the_tips_rolled_from_the_state():
    state = logic.new_state(SEED)
    assert logic.outlook_tips(state, logic.outlook(state)) == logic.outlook_tips(state)


def test_the_forecast_names_its_miss_rate_and_none_with_an_override():
    state = logic.new_state(SEED)
    assert logic.outlook(state)["miss_percent"] == logic.OUTLOOK_MISS_PERCENT
    assert logic.outlook(logic.set_day_override(state, "heat"))["miss_percent"] == 0


def test_no_tips_without_a_forecast():
    state = logic.new_state(SEED)
    state["day"] = logic.LAST_DAY + 1
    assert logic.outlook_tips(state) == []


# ---- Check 5: nothing secret leaves the server -----------------------------

def test_the_answer_has_the_forecast_and_its_tips(monkeypatch):
    seed = a_seed_whose_forecast_for_day_1_is_wrong()
    state = logic.new_state(seed)
    monkeypatch.setattr(app, "load_run", lambda: copy.deepcopy(state))
    shown = app.app.test_client().get("/api/state").get_json()["outlook"]
    forecast = logic.make_outlook(seed, 1)
    low, high = forecast["temp_range"]
    assert shown == {
        "day": 1, "id": forecast["weather"],
        "name": logic.WEATHER[forecast["weather"]]["name"],
        "temp_low": low, "temp_high": high,
        "miss_percent": logic.OUTLOOK_MISS_PERCENT,
        "tips": [dict(tip, name=logic.SHOPS[tip["shop"]]["name"])
                 for tip in logic.outlook_tips(state)],
    }
    assert shown["id"] != logic.make_day_context(seed, 1)["weather"]  # it is a wrong one


def test_neither_the_seed_nor_a_right_or_wrong_flag_is_in_any_answer(run_on_disk, monkeypatch):
    monkeypatch.setenv("CAMPUS_TYCOON_DEMO", "1")
    client = app.app.test_client()
    answers = [
        client.get("/api/state"),
        client.post("/api/buy", json={"product": "coffee", "quantity": 5}),
        client.post("/api/buy", json={"product": "coffee", "quantity": -1}),  # a refusal
        client.post("/api/day-override", json={"weather": "rain"}),
        client.post("/api/day-override", json={"weather": None}),
        client.post("/api/day/open", json={}),
        client.post("/api/shift/skip", json={}),
    ]
    for response in answers:
        text = response.get_data(as_text=True)
        assert str(SEED) not in text and '"seed"' not in text
        body = response.get_json()
        outlook = body.get("state", body)["outlook"]
        assert outlook is None or set(outlook) == OUTLOOK_FIELDS
        for tip in (outlook or {}).get("tips", []):
            assert set(tip) == {"shop", "name", "percent", "advice"}


def test_no_forecast_in_the_answer_once_the_last_day_is_open(monkeypatch):
    state = logic.new_state(SEED)
    state["day"] = logic.LAST_DAY
    state = logic.open_day(state)
    monkeypatch.setattr(app, "load_run", lambda: copy.deepcopy(state))
    assert app.app.test_client().get("/api/state").get_json()["outlook"] is None


# ---- Check 6: whole numbers, state unchanged ------------------------------

def test_the_state_shape_is_unchanged():
    state = logic.new_state(SEED)
    before = copy.deepcopy(state)
    logic.outlook(state)
    assert state == before
    assert "outlook" not in state
