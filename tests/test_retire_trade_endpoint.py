"""Checks from specs/retire-trade-endpoint.md ("Done when"): POST /api/open is always refused, the
stored run stays as it was, and logic.trade_day keeps its two uses (the dashboard's forecast and the
editor's Skip days)."""

import inspect
import re
from pathlib import Path

import pytest

import app
import db
import logic

STATIC = Path(app.__file__).parent / "static"
SENTENCE = "A day is played on the campus: open the day and take a shift."


@pytest.fixture
def run_on_disk(tmp_path, monkeypatch):
    """The app's run in a file of its own (like tests/test_shop_process.py)."""
    path = tmp_path / "run.db"
    db.save(logic.new_state(7), path)
    real_save = db.save
    monkeypatch.setattr(app, "load_run", lambda: db.load(path))
    monkeypatch.setattr(app.db, "save", lambda state, *_, **__: real_save(state, path))
    return path


def stocked_with_staff():
    """Day 1 with coffee in stock, the Beach Cafe unlocked and an employee there: a day /api/open would
    have paid well for."""
    state = logic.new_state(7)
    state["cash"] = 100_000
    state = logic.unlock_shop(state, "beach_cafe")
    state = logic.buy_upgrade(state, "beach_cafe", "staff_1")
    state = logic.buy(state, "coffee", 30)
    return logic.buy(state, "beer", 30)


def refused_unchanged(client, path, **post):
    before = db.load(path)
    raw = path.read_bytes()
    response = client.post("/api/open", **post)
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"] == SENTENCE
    assert data["state"]["day"] == before["day"] and data["state"]["cash"] == before["cash"]
    assert db.load(path) == before
    assert path.read_bytes() == raw  # nothing was written at all
    return data


BODIES = [
    {"json": {"day": 1}},  # the current day: what the old dashboard sent
    {"json": {"day": 0}},
    {"json": {"day": 2}},
    {"json": {}},
    {"json": {"day": "1"}},
    {"json": {"day": 1, "popularity": {"cafe": 100}}},
    {"data": "{not json", "content_type": "application/json"},
    {"data": "[1, 2]", "content_type": "application/json"},
    {"data": "day=1", "content_type": "application/x-www-form-urlencoded"},
]


@pytest.mark.parametrize("post", BODIES)
def test_every_body_is_refused_on_a_fresh_run(run_on_disk, post):
    refused_unchanged(app.app.test_client(), run_on_disk, **post)


def test_a_run_with_stock_and_staff_earns_nothing_from_it(run_on_disk):
    db.save_new_run(stocked_with_staff(), run_on_disk)
    before = db.load(run_on_disk)
    for _ in range(3):  # sent again and again: still nothing
        refused_unchanged(app.app.test_client(), run_on_disk, json={"day": before["day"]})
    assert db.load(run_on_disk)["history"] == []


def test_it_is_refused_while_a_day_is_open(run_on_disk):
    db.save_new_run(logic.open_day(stocked_with_staff()), run_on_disk)
    refused_unchanged(app.app.test_client(), run_on_disk, json={"day": 1})


def test_it_is_refused_after_the_last_day(run_on_disk):
    state = logic.new_state(7)
    state["day"] = logic.LAST_DAY + 1
    db.save_new_run(state, run_on_disk)
    refused_unchanged(app.app.test_client(), run_on_disk, json={"day": logic.LAST_DAY + 1})


def test_the_public_server_refuses_it_for_a_player_too(monkeypatch, tmp_path):
    monkeypatch.setenv("CT_PUBLIC", "1")
    monkeypatch.setattr(app, "PLAYERS_DIR", tmp_path / "players")
    app._hits.clear()
    client = app.app.test_client()
    assert client.get("/").status_code == 200  # the page gives the player a cookie
    player = client.get_cookie(app.PLAYER_COOKIE).value.split(".")[0]
    assert client.get("/api/state").status_code == 200  # the run exists now
    path = app._player_file(player)
    db.save_new_run(stocked_with_staff(), path)
    refused_unchanged(client, path, json={"day": 1})


def test_the_rule_itself_stays_for_the_forecast_and_the_editor():
    state = stocked_with_staff()
    # the dashboard's "Open for day N" is still trade_day on what the player may know, on a copy
    with app.app.test_request_context("/api/state"):
        forecast = app.view(state)["forecast"]
    assert forecast == logic.trade_day(logic.known_state(state))[1]
    assert forecast["revenue"] > 0
    # the editor's Skip days still books days with it
    skipped = logic.editor_skip_days(state, 2)
    assert skipped["day"] == 3 and len(skipped["history"]) == 2


def test_the_endpoint_says_why_and_no_screen_calls_it():
    # the route's own source, whatever the blank lines around it (review finding)
    route = inspect.getsource(app.open_day)
    assert '@app.post("/api/open")' in route
    assert "raise logic.RejectedAction(TRADE_RETIRED)" in route
    assert "trade_day" not in route.split('"""')[-1]  # the body books nothing any more
    assert app.TRADE_RETIRED == SENTENCE
    # no screen file names the path in any spelling: quotes, backticks or built from "api/" + "open"
    # (review finding); /api/open_... would be another path, so a letter, digit, _ or - may not follow
    for path in STATIC.rglob("*"):
        if path.suffix in (".js", ".html"):
            text = path.read_text(encoding="utf-8")
            assert not re.search(r"api/open(?![\w-])", text), path.name
            assert not re.search(r"""["'`]api/["'`]\s*\+\s*["'`]open["'`]""", text), path.name
