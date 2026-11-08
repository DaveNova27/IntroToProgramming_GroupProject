"""Checks from specs/world-api.md ("Done when"). One test per check."""

import math

import pytest

import app
import db
import logic
import world


@pytest.fixture
def run_on_disk(tmp_path, monkeypatch):
    """The real API on a temporary save, so the player's own run stays untouched."""
    path = tmp_path / "run.db"
    db.save(logic.new_state(), path)
    real_save = db.save
    monkeypatch.setattr(app, "load_run", lambda: db.load(path))
    monkeypatch.setattr(app.db, "save", lambda state: real_save(state, path))
    return path


def is_blocked(x, y, solid, radius=0.28):
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


# ---- Check 1: the world is complete, and every door leads somewhere ---------

def test_the_api_serves_the_whole_world():
    data = app.app.test_client().get("/api/world").get_json()
    assert set(data["zones"]) == {"campus"}  # spec walk-in: one zone, the Nova is a building on it
    assert set(data["colliders"]) == set(data["zones"])
    assert set(data["interiors"]) == {"campus"}  # the rooms are inside the Nova, on the campus
    assert data["buildings"] and data["planters"] and data["trees"] and data["spaces"]


def test_every_location_is_inside_its_zone():
    for loc in world.LOCATIONS.values():
        zone = world.ZONES[loc["zone"]]
        assert zone["minX"] <= loc["x"] <= zone["maxX"]
        assert zone["minY"] <= loc["y"] <= zone["maxY"]


def test_every_door_leads_to_a_zone_with_a_free_place_to_stand():
    # spec walk-in: the six doors are gone. The same check for the new way in: the spawn is free,
    # and every entrance of the Nova leads to free ground in the doorway, outside and inside.
    assert not [loc for loc in world.LOCATIONS.values() if loc["kind"] == "door"]
    zone = world.ZONES["campus"]
    solid = world.colliders("campus")
    spawn = zone["spawn"]
    assert zone["minX"] <= spawn["x"] <= zone["maxX"]
    assert zone["minY"] <= spawn["y"] <= zone["maxY"]
    assert not is_blocked(spawn["x"], spawn["y"], solid)
    assert world.NOVA["entrances"]
    for entrance in world.NOVA["entrances"]:
        x = entrance["x"] + entrance["width"] / 2
        for y in (entrance["y"] - 0.6, entrance["y"] + world.NOVA["wall"] / 2, entrance["y"] + world.NOVA["wall"] + 0.6):
            assert zone["minX"] <= x <= zone["maxX"]
            assert zone["minY"] <= y <= zone["maxY"]
            assert not is_blocked(x, y, solid)


def test_every_room_has_a_way_out():
    # spec walk-in: the rooms are inside the Nova on the campus; the way out is an entrance
    for zone_id in world.INTERIORS:
        assert zone_id in world.ZONES
        assert any(entrance["width"] >= 2 for entrance in world.NOVA["entrances"])


def test_the_only_desks_are_stock_prices_and_dashboard():
    actions = {loc["action"] for loc in world.LOCATIONS.values() if loc["kind"] == "panel"}
    assert actions == {"stock", "prices", "dashboard"}


# ---- Check 2: the position is part of the state and survives a restart -------

def test_a_new_run_starts_at_the_spawn():
    assert logic.new_state()["player"] == {"zone": "campus", "x": 21.0, "y": 18.0}
    assert not is_blocked(21.0, 18.0, world.colliders("campus"))


def test_the_position_survives_a_restart(tmp_path):
    path = tmp_path / "run.db"
    state = logic.move_player(logic.new_state(), "campus", 23.25, 5.5)
    db.save(state, path)
    assert db.load(path) == state
    assert db.load(path)["player"] == {"zone": "campus", "x": 23.25, "y": 5.5}


def test_a_save_from_before_the_world_still_loads(tmp_path):
    path = tmp_path / "old.db"
    db.save(logic.new_state(), path)
    with db.connect(path) as conn:
        conn.execute("DELETE FROM player")
    assert db.load(path)["player"] == world.start_player()


def test_the_api_saves_the_position(run_on_disk):
    response = app.app.test_client().post("/api/player", json={"zone": "campus", "x": 23.5, "y": 7.25})
    assert response.status_code == 200
    assert response.get_json()["state"]["player"] == {"zone": "campus", "x": 23.5, "y": 7.25}
    assert db.load(run_on_disk)["player"] == {"zone": "campus", "x": 23.5, "y": 7.25}


def test_a_new_run_puts_the_player_back_at_the_spawn(run_on_disk, monkeypatch):
    real_save_new_run = db.save_new_run
    monkeypatch.setattr(app.db, "save_new_run", lambda state: real_save_new_run(state, run_on_disk))
    client = app.app.test_client()
    client.post("/api/player", json={"zone": "campus", "x": 23.5, "y": 7.25})
    assert db.load(run_on_disk)["player"] == {"zone": "campus", "x": 23.5, "y": 7.25}  # it really moved
    client.post("/api/new-run", json={"confirm": True})
    assert db.load(run_on_disk)["player"] == world.start_player()


def test_a_saved_zone_that_no_longer_exists_starts_at_the_spawn(tmp_path):
    path = tmp_path / "run.db"
    db.save(logic.new_state(), path)
    with db.connect(path) as conn:
        conn.execute("UPDATE player SET zone = 'removed-zone'")
    assert db.load(path)["player"] == world.start_player()


def test_moving_changes_nothing_but_the_position():
    state = logic.buy(logic.new_state(), "coffee", 5)
    moved = logic.move_player(state, "campus", 23.5, 7.25)
    assert {k: v for k, v in moved.items() if k != "player"} == {k: v for k, v in state.items() if k != "player"}
    assert state["player"] == world.start_player()


def test_the_position_can_move_after_the_last_day():
    state = logic.new_state()
    state["day"] = logic.LAST_DAY + 1
    assert logic.is_finished(state)
    assert logic.move_player(state, "campus", 23.5, 7.25)["player"] == {"zone": "campus", "x": 23.5, "y": 7.25}


# ---- Check 3: a crafted position is refused and changes nothing ---------------

@pytest.mark.parametrize("body", [
    {"zone": "nowhere", "x": 21, "y": 18},
    {"zone": ["campus"], "x": 21, "y": 18},
    {"zone": None, "x": 21, "y": 18},
    {"zone": "campus", "x": 500, "y": 18},
    {"zone": "campus", "x": 21, "y": -3},
    {"zone": "campus", "x": "21", "y": 18},
    {"zone": "campus", "x": True, "y": 18},
    {"zone": "campus", "x": None, "y": 18},
    {"zone": "campus"},
    {},
])
def test_a_bad_position_is_refused(run_on_disk, body):
    before = db.load(run_on_disk)
    response = app.app.test_client().post("/api/player", json=body)
    assert response.status_code == 400
    assert response.get_json()["error"]
    assert db.load(run_on_disk) == before


@pytest.mark.parametrize("number", ["NaN", "Infinity", "-Infinity", "1e999", "1" + "0" * 400])
def test_a_position_that_is_not_finite_is_refused(run_on_disk, number):
    before = db.load(run_on_disk)
    response = app.app.test_client().post(
        "/api/player",
        data='{"zone": "campus", "x": %s, "y": 18}' % number,
        content_type="application/json",
    )
    assert response.status_code == 400
    assert db.load(run_on_disk) == before


@pytest.mark.parametrize("path", ["/api/player", "/api/buy", "/api/price", "/api/open", "/api/new-run"])
@pytest.mark.parametrize("raw", ["[1, 2]", '"text"', "7", "{not json"])
def test_a_body_that_is_not_an_object_is_refused(run_on_disk, path, raw):
    before = db.load(run_on_disk)
    response = app.app.test_client().post(path, data=raw, content_type="application/json")
    assert response.status_code == 400
    assert db.load(run_on_disk) == before


@pytest.mark.parametrize("quantity", ["--5", "-", "²", "9" * 5000])
def test_a_quantity_that_is_no_number_is_refused(run_on_disk, quantity):
    before = db.load(run_on_disk)
    response = app.app.test_client().post("/api/buy", json={"product": "coffee", "quantity": quantity})
    assert response.status_code == 400
    assert db.load(run_on_disk) == before


@pytest.mark.parametrize("price", ["1e20", "1000000.01"])
def test_a_price_too_high_to_store_is_refused(run_on_disk, price):
    before = db.load(run_on_disk)
    response = app.app.test_client().post("/api/price", json={"product": "coffee", "price": price})
    assert response.status_code == 400
    assert db.load(run_on_disk) == before


def test_the_highest_price_is_accepted():
    assert logic.set_price(logic.new_state(), "coffee", logic.MAX_PRICE)["prices"]["coffee"] == logic.MAX_PRICE


def test_a_product_that_is_not_text_is_refused(run_on_disk):
    before = db.load(run_on_disk)
    client = app.app.test_client()
    assert client.post("/api/buy", json={"product": ["coffee"], "quantity": 1}).status_code == 400
    assert client.post("/api/price", json={"product": {"a": 1}, "price": "4"}).status_code == 400
    assert db.load(run_on_disk) == before
