"""Checks from specs/day-cycle.md ("Done when"). The day cycle is drawn in the browser; the
server only holds the wake-up spot and keeps every rule as before."""

import math
from pathlib import Path

import pytest

import app
import db
import logic
import world

WORLD_JS = Path(__file__).resolve().parent.parent / "static" / "world"
PLAYER_RADIUS = 0.28  # static/world/scene.js
REACH = 1.65  # static/world/locations.js


@pytest.fixture
def run_on_disk(tmp_path, monkeypatch):
    """The real API on a temporary save, so the player's own run stays untouched."""
    path = tmp_path / "run.db"
    db.save(logic.new_state(), path)
    real_save = db.save
    monkeypatch.setattr(app, "load_run", lambda: db.load(path))
    monkeypatch.setattr(app.db, "save", lambda state: real_save(state, path))
    return path


def blocked(x, y, solid, radius=PLAYER_RADIUS):
    """The same check as pointBlocked in static/world/physics.js."""
    for item in solid:
        if item["shape"] == "circle":
            if math.hypot(x - item["x"], y - item["y"]) < item["radius"] + radius:
                return True
        else:
            nearest_x = min(max(x, item["x"]), item["x"] + item["width"])
            nearest_y = min(max(y, item["y"]), item["y"] + item["height"])
            if math.hypot(x - nearest_x, y - nearest_y) < radius:
                return True
    return False


# ---- Check 1: the wake-up spot ---------------------------------------------------------------------

def test_the_wake_up_spot_is_free_inside_the_dorm_and_next_to_the_bed():
    wake = world.DORM["wake"]
    assert wake["zone"] == "campus"
    zone = world.ZONES["campus"]
    assert zone["minX"] <= wake["x"] <= zone["maxX"] and zone["minY"] <= wake["y"] <= zone["maxY"]
    part = world.DORM["parts"][0]
    wall = world.DORM["wall"]
    assert part["x"] + wall < wake["x"] < part["x"] + part["w"] - wall
    assert part["y"] + wall < wake["y"] < part["y"] + part["h"] - wall
    assert not blocked(wake["x"], wake["y"], world.colliders("campus"))
    bed = world.DORM["bed"]
    assert math.hypot(wake["x"] - bed["x"], wake["y"] - bed["y"]) < REACH, "the bed is in reach on waking"


def test_the_wake_up_spot_is_sent_to_the_browser():
    assert world.world_view()["dorm"]["wake"] == world.DORM["wake"]


def test_the_wake_up_spot_is_saved_like_any_position(run_on_disk):
    wake = world.DORM["wake"]
    body = {"zone": wake["zone"], "x": wake["x"], "y": wake["y"]}
    response = app.app.test_client().post("/api/player", json=body)
    assert response.status_code == 200
    assert db.load(run_on_disk)["player"] == body


# ---- Check 3: no new endpoint, no new rule ---------------------------------------------------------

def test_the_day_cycle_adds_no_endpoint():
    rules = {rule.rule for rule in app.app.url_map.iter_rules()}
    assert not [r for r in rules if "sleep" in r or "wake" in r or "home" in r or "evening" in r]


def test_a_crafted_skip_without_an_open_day_is_refused_and_changes_nothing(run_on_disk):
    before = db.load(run_on_disk)
    response = app.app.test_client().post("/api/shift/skip", json={})
    assert response.status_code == 400
    assert db.load(run_on_disk) == before


def test_the_evening_hint_offers_go_home_and_skip_the_walk():
    page = (WORLD_JS.parent / "map.html").read_text()
    assert 'id="btn-go-home"' in page and 'id="btn-skip-walk"' in page


def test_ending_a_day_early_asks_first_and_then_sends_the_skip_that_exists():
    page = (WORLD_JS.parent / "map.html").read_text()
    assert 'id="end-day-dialog"' in page
    ui = (WORLD_JS / "ui.js").read_text()
    assert 'shiftAction("/api/shift/skip", {})' in ui  # the same request as before, no new one


def test_the_browser_draws_the_cycle_without_randomness_or_server_calls_from_the_figures():
    for name in ("main.js", "ui.js", "player.js", "people.js"):
        assert "Math.random" not in (WORLD_JS / name).read_text(), name
    people = (WORLD_JS / "people.js").read_text()
    assert '"lie"' in people, "the figure knows the pose for lying in bed"
