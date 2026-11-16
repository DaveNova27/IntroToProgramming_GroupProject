"""Checks from specs/outfits.md ("Done when"): clothes for the player's figure, bought in the Dorm.

Only the look changes. The server decides every purchase; a refused one changes nothing.
"""

import copy
import sqlite3
from pathlib import Path

import pytest

import app
import db
import logic

STATIC = Path(app.__file__).parent / "static"


def rich(cash=100_000):
    state = logic.new_state()
    state["cash"] = cash
    return state


def refused(action, state):
    """The action must be refused and must leave the given state untouched."""
    before = copy.deepcopy(state)
    with pytest.raises(logic.RejectedAction):
        action(state)
    assert state == before


@pytest.fixture
def run_on_disk(tmp_path, monkeypatch):
    """The real API on a temporary save, so the player's own run stays untouched."""
    path = tmp_path / "run.db"
    db.save(rich(), path)
    real_save = db.save
    monkeypatch.setattr(app, "load_run", lambda: db.load(path))
    monkeypatch.setattr(app.db, "save", lambda state, *_, **__: real_save(state, path))
    return path


# ---- Check 1: the list of outfits ----------------------------------------------------------

def test_a_new_run_wears_the_free_basic_shirt_and_owns_nothing_else():
    state = logic.new_state()
    assert state["outfits"] == {"owned": ["basic"], "worn": "basic"}
    assert logic.OUTFITS["basic"][1] == 0


def test_prices_are_whole_cents_and_no_outfit_is_sold_in_the_merchandise_shop():
    for name, price, suits, text in logic.OUTFITS.values():
        assert isinstance(price, int) and price >= 0
        assert suits and set(suits) <= set(logic.WEATHER) and text
    merch = {logic.CATALOGUE[p]["name"].lower() for p in logic.shop_product_ids("merchandise")}
    for oid, (name, *_rest) in logic.OUTFITS.items():
        assert oid not in logic.CATALOGUE
        assert not any(word in name.lower() for word in ("hoodie", "t-shirt", "cap")), name
        assert name.lower() not in merch


# ---- Check 2: buying -------------------------------------------------------------------------

def test_buying_takes_the_price_owns_the_outfit_and_puts_it_on():
    state = rich(10_000)
    new = logic.buy_outfit(state, "blazer")
    assert new["cash"] == 10_000 - logic.OUTFITS["blazer"][1]
    assert new["outfits"] == {"owned": ["basic", "blazer"], "worn": "blazer"}
    assert state["outfits"] == {"owned": ["basic"], "worn": "basic"}  # the old state is untouched


def test_owned_outfits_stay_in_the_order_of_the_list():
    state = logic.buy_outfit(logic.buy_outfit(rich(), "blazer"), "hawaii")
    assert state["outfits"]["owned"] == ["basic", "hawaii", "blazer"]


def test_exactly_enough_cash_is_enough():
    price = logic.OUTFITS["tracksuit"][1]
    assert logic.buy_outfit(rich(price), "tracksuit")["cash"] == 0


@pytest.mark.parametrize("outfit", ["suit", "", None, 5, ["blazer"], {"id": "blazer"}, "Blazer", "hoodie"])
def test_an_unknown_outfit_is_refused(outfit):
    refused(lambda s: logic.buy_outfit(s, outfit), rich())
    refused(lambda s: logic.wear_outfit(s, outfit), rich())


def test_not_enough_cash_is_refused():
    refused(lambda s: logic.buy_outfit(s, "blazer"), rich(logic.OUTFITS["blazer"][1] - 1))


def test_an_owned_outfit_cannot_be_bought_twice():
    refused(lambda s: logic.buy_outfit(s, "basic"), rich())
    refused(lambda s: logic.buy_outfit(s, "hawaii"), logic.buy_outfit(rich(), "hawaii"))


def test_nothing_can_be_bought_when_the_run_is_complete():
    state = rich()
    state["day"] = logic.LAST_DAY + 1
    refused(lambda s: logic.buy_outfit(s, "hawaii"), state)


# ---- Check 3: wearing ------------------------------------------------------------------------

def test_an_owned_outfit_can_be_put_on_again_for_free():
    state = logic.buy_outfit(rich(), "raincoat")
    back = logic.wear_outfit(state, "basic")
    assert back["outfits"] == {"owned": ["basic", "raincoat"], "worn": "basic"}
    assert back["cash"] == state["cash"]
    assert logic.wear_outfit(back, "raincoat")["outfits"]["worn"] == "raincoat"


def test_an_outfit_not_owned_or_already_worn_is_refused():
    refused(lambda s: logic.wear_outfit(s, "blazer"), rich())
    refused(lambda s: logic.wear_outfit(s, "basic"), rich())


def test_an_outfit_changes_nothing_but_the_look():
    state = rich()
    dressed = logic.buy_outfit(state, "hawaii")
    dressed["cash"] = state["cash"]
    for pid in logic.CATALOGUE:
        shop = next(s for s in logic.SHOPS if pid in logic.shop_product_ids(s))
        assert logic.customer_breakdown(dressed, pid) == logic.customer_breakdown(state, pid), shop
    assert logic.trade_day(dressed)[1] == logic.trade_day(state)[1]


# ---- Check 4: saved and loaded -------------------------------------------------------------

def test_the_outfits_survive_a_save(tmp_path):
    state = logic.wear_outfit(logic.buy_outfit(logic.buy_outfit(rich(), "blazer"), "hawaii"), "blazer")
    path = tmp_path / "run.db"
    db.save(state, path)
    assert db.load(path) == state
    assert db.through_sqlite(state) == state


def test_a_save_from_before_outfits_loads_with_the_basic_shirt(tmp_path):
    state = rich()
    path = tmp_path / "run.db"
    db.save(state, path)
    with sqlite3.connect(path) as conn:
        conn.execute("DELETE FROM meta WHERE key = 'outfits'")
    loaded = db.load(path)
    assert loaded["outfits"] == {"owned": ["basic"], "worn": "basic"}


@pytest.mark.parametrize("raw", [
    "not json", "[]", '{"owned": "blazer", "worn": "blazer"}',
    '{"owned": ["blazer", "gone"], "worn": "gone"}', '{"owned": [1, null], "worn": 7}',
])
def test_a_broken_or_old_entry_loads_as_something_valid(tmp_path, raw):
    path = tmp_path / "run.db"
    db.save(rich(), path)
    with sqlite3.connect(path) as conn:
        conn.execute("UPDATE meta SET value = ? WHERE key = 'outfits'", (raw,))
    outfits = db.load(path)["outfits"]
    assert outfits["owned"][0] == "basic" and set(outfits["owned"]) <= set(logic.OUTFITS)
    assert outfits["worn"] in outfits["owned"]


# ---- Check 5: the API ------------------------------------------------------------------------

def test_buy_and_wear_through_the_api(run_on_disk):
    client = app.app.test_client()
    response = client.post("/api/outfit/buy", json={"outfit": "hawaii"})
    assert response.status_code == 200, response.get_json()
    data = response.get_json()["state"]
    assert data["outfit"] == "hawaii"
    assert data["cash"] == 100_000 - logic.OUTFITS["hawaii"][1]
    assert {o["id"]: o["owned"] for o in data["outfits"]}["hawaii"] is True
    response = client.post("/api/outfit/wear", json={"outfit": "basic"})
    assert response.status_code == 200
    assert db.load(run_on_disk)["outfits"] == {"owned": ["basic", "hawaii"], "worn": "basic"}


@pytest.mark.parametrize("path, body", [
    ("/api/outfit/buy", {"outfit": "suit"}),
    ("/api/outfit/buy", {"outfit": "basic"}),
    ("/api/outfit/buy", {}),
    ("/api/outfit/buy", {"outfit": "blazer", "price": 0}),
    ("/api/outfit/wear", {"outfit": "blazer"}),
    ("/api/outfit/wear", {"outfit": ["basic"]}),
])
def test_a_crafted_request_is_refused_and_changes_nothing(run_on_disk, path, body):
    client = app.app.test_client()
    if body.get("price") == 0:  # a price from the browser is ignored: the blazer costs its price
        before = db.load(run_on_disk)
        response = client.post(path, json=body)
        assert response.status_code == 200
        assert db.load(run_on_disk)["cash"] == before["cash"] - logic.OUTFITS["blazer"][1]
        return
    before = db.load(run_on_disk)
    response = client.post(path, json=body)
    assert response.status_code == 400
    assert response.get_json()["error"]
    assert db.load(run_on_disk) == before


def test_not_enough_cash_through_the_api_changes_nothing(run_on_disk):
    state = db.load(run_on_disk)
    state["cash"] = 100
    db.save(state, run_on_disk)
    response = app.app.test_client().post("/api/outfit/buy", json={"outfit": "blazer"})
    assert response.status_code == 400
    assert db.load(run_on_disk) == state


def test_the_view_lists_every_outfit_with_its_state():
    view = app.view(logic.buy_outfit(rich(3_000), "hawaii"))
    assert [o["id"] for o in view["outfits"]] == list(logic.OUTFITS)
    by_id = {o["id"]: o for o in view["outfits"]}
    assert by_id["hawaii"]["worn"] and by_id["hawaii"]["owned"]
    assert by_id["basic"]["owned"] and not by_id["basic"]["worn"]
    assert by_id["raincoat"]["affordable"] is False  # 10 euro left, the jacket costs 25
    assert view["outfit"] == "hawaii"


# ---- Check 6: the editor and the demo can set it --------------------------------------------

def test_the_editor_sets_the_outfits_and_checks_them():
    state = logic.editor_set_state(rich(), {"outfits": {"owned": ["blazer"], "worn": "blazer"}})
    assert state["outfits"] == {"owned": ["basic", "blazer"], "worn": "blazer"}
    for bad in ({"owned": ["suit"], "worn": "basic"}, {"owned": [], "worn": "blazer"},
                {"owned": ["basic"]}, ["basic"], {"owned": "basic", "worn": "basic"}):
        refused(lambda s: logic.editor_set_state(s, {"outfits": bad}), rich())


# ---- Check 7: the screen only draws what the server sent ------------------------------------

def test_the_figure_draws_the_outfit_the_server_sent():
    ui = (STATIC / "world" / "ui.js").read_text()
    player = (STATIC / "world" / "player.js").read_text()
    people = (STATIC / "world" / "people.js").read_text()
    assert 'server.outfit = state.outfit' in ui
    assert 'data-outfit-buy' in ui and '"/api/outfit/buy"' in ui and '"/api/outfit/wear"' in ui
    assert player.count("outfit: server.outfit") == 2  # walking and asleep in bed
    for oid in logic.OUTFITS:
        assert f"{oid}:" in people, f"no look for {oid}"
    assert "Math.random" not in people
    # the room has the button, the wardrobe window a picture and the weather of every outfit
    wardrobe = (STATIC / "world" / "wardrobe.js").read_text()
    assert "Change your clothes" in ui and "data-wardrobe-open" in ui and 'panelMode === "wardrobe"' in ui
    for oid in logic.OUTFITS:
        assert f"  {oid}: () =>" in wardrobe, f"no picture for {oid}"
    assert "Math.random" not in wardrobe and "http" not in wardrobe


def test_the_view_says_which_weather_an_outfit_suits():
    view = app.view(rich())
    raincoat = next(o for o in view["outfits"] if o["id"] == "raincoat")
    assert [w["id"] for w in raincoat["suits"]] == ["rain", "storm"]
    assert all(w["name"] == logic.WEATHER[w["id"]]["name"] for o in view["outfits"] for w in o["suits"])
    assert all(o["text"] for o in view["outfits"])


# ---- Check 8: the wardrobe in the Dorm is a place to use ------------------------------------

def test_the_wardrobe_is_a_use_point_in_the_dorm_in_front_of_the_wardrobe():
    import world
    spot = world.DORM["wardrobe"]
    assert spot["action"] == "wardrobe" and spot["wing"] == "dorm" and spot["zone"] == "campus"
    assert spot["label"] == "Change your clothes"
    wardrobe = next(s for s in world.DORM["interior"]["solid"] if s["id"] == "dorm-wardrobe")
    # in front of it (east), inside the room, not inside any solid object of the room
    assert wardrobe["x"] + wardrobe["w"] < spot["x"] < wardrobe["x"] + wardrobe["w"] + 1.0
    part = world.DORM["parts"][0]
    assert part["x"] < spot["x"] < part["x"] + part["w"] and part["y"] < spot["y"] < part["y"] + part["h"]
    for s in world.DORM["interior"]["solid"]:
        if "w" in s:
            assert not (s["x"] <= spot["x"] <= s["x"] + s["w"] and s["y"] <= spot["y"] <= s["y"] + s["h"]), s["id"]
    zones = (STATIC / "world" / "zones.js").read_text()
    ui = (STATIC / "world" / "ui.js").read_text()
    assert "wardrobe: dorm.wardrobe" in zones
    assert 'if (action === "wardrobe") openPanel("wardrobe");' in ui
