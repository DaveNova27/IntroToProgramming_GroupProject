"""Checks from specs/hidden-weather.md: before the day is opened nothing the server sends
depends on the real weather, only on the forecast."""

import app
import db
import logic


def _same_forecast_other_weather():
    """Two seeds whose forecast for day 1 is the same weather but whose real weather differs."""
    seen = {}
    for seed in range(1, 500):
        forecast = logic.make_outlook(seed, 1)["weather"]
        real = logic.make_day_context(seed, 1)["weather"]
        for other_seed, other_real in seen.get(forecast, []):
            if other_real != real:
                return other_seed, seed
        seen.setdefault(forecast, []).append((seed, real))
    raise AssertionError("no such pair of seeds")


def _stocked(seed):
    state = logic.new_state(seed)
    state["cash"] = 100_000
    state = logic.buy_upgrade(state, "cafe", "cake")
    return logic.buy(logic.buy(state, "coffee", 30), "cake", 30)


def _shown(state):
    v = app.view(state)
    return {key: v[key] for key in ("products", "stock_overview", "forecast")}


def test_view_before_open_does_not_depend_on_the_real_weather():
    a, b = _same_forecast_other_weather()
    assert logic.day_context(logic.new_state(a))["weather"] != logic.day_context(logic.new_state(b))["weather"]
    assert _shown(_stocked(a)) == _shown(_stocked(b))


def test_price_preview_before_open_does_not_depend_on_the_real_weather(tmp_path, monkeypatch):
    a, b = _same_forecast_other_weather()
    answers = []
    for seed in (a, b):
        path = tmp_path / f"{seed}.db"
        db.save(_stocked(seed), path)
        monkeypatch.setattr(app, "load_run", lambda path=path: db.load(path))
        answers.append(app.app.test_client().post(
            "/api/price_preview", json={"product": "coffee", "price": "2.50"}).get_json())
    assert answers[0] == answers[1]


def test_open_day_uses_the_real_weather():
    # once the day is open the real weather counts again (and is shown)
    for seed in range(1, 200):
        if logic.make_outlook(seed, 1)["weather"] != logic.make_day_context(seed, 1)["weather"]:
            break
    state = logic.open_day(_stocked(seed))
    assert logic.known_state(state) is state
    real = logic.day_context(state)["weather"]
    assert app.view(state)["weather"]["id"] == real
    assert any(step["name"] == f"Weather: {logic.WEATHER[real]['name']}" or logic.WEATHER[real]["demand_percent"]["cafe"] == 100
               for step in app.view(state)["products"][0]["breakdown"]["steps"] + [{"name": ""}])


def test_known_state_leaves_the_saved_state_alone():
    state = _stocked(7)
    before = repr(state)
    logic.known_state(state)
    assert repr(state) == before
