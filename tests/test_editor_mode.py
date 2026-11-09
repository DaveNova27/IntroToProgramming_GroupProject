"""Editor mode: dev tools behind a local switch (specs/editor-mode.md)."""

import copy
import json

import pytest

import app
import db
import logic


@pytest.fixture
def api(tmp_path, monkeypatch):
    """A test client on a temporary database, with the editor switched on."""
    path = tmp_path / "run.db"
    db.save(logic.new_state(7), path)
    real_save, real_new = db.save, db.save_new_run
    monkeypatch.setattr(app, "load_run", lambda: db.load(path))
    monkeypatch.setattr(app.db, "save", lambda s: real_save(s, path))
    monkeypatch.setattr(app.db, "save_new_run", lambda s: real_new(s, path))
    monkeypatch.setenv("CT_EDITOR", "1")
    client = app.app.test_client()
    client.path = path
    client.write = lambda state: real_save(state, path)
    return client


def post(client, url, body, **kw):
    return client.post(url, json=body, **kw)


def saved(client):
    return db.load(client.path)


# --- the switch -------------------------------------------------------------

EDITOR_CALLS = [
    ("/api/editor/cash", {"mode": "set", "cents": 5}),
    ("/api/editor/weather", {"weather": "rain"}),
    ("/api/editor/skip-days", {"days": 1}),
    ("/api/editor/state", {"patch": {"cash": 5}}),
    ("/api/editor/reset", {"confirm": True}),
]


@pytest.mark.parametrize("url,body", EDITOR_CALLS)
def test_everything_is_refused_without_the_switch(api, monkeypatch, url, body):
    monkeypatch.delenv("CT_EDITOR")
    before = saved(api)
    response = post(api, url, body)
    assert response.status_code == 400 and response.get_json()["error"] == "The editor is off."
    assert saved(api) == before


@pytest.mark.parametrize("url,body", EDITOR_CALLS)
def test_refused_from_another_address_or_behind_a_proxy(api, url, body):
    before = saved(api)
    assert post(api, url, body, environ_overrides={"REMOTE_ADDR": "10.0.0.5"}).status_code == 400
    assert post(api, url, body, headers={"X-Forwarded-For": "1.2.3.4"}).status_code == 400
    assert post(api, url, body, headers={"Forwarded": "for=1.2.3.4"}).status_code == 400
    assert saved(api) == before


def test_the_state_says_whether_the_editor_is_on(api, monkeypatch):
    assert api.get("/api/state").get_json()["editor"] is True
    monkeypatch.setenv("CT_EDITOR", "0")
    assert api.get("/api/state").get_json()["editor"] is False
    monkeypatch.setenv("CT_EDITOR", "1")
    assert api.get("/api/state", environ_overrides={"REMOTE_ADDR": "8.8.8.8"}
                   ).get_json()["editor"] is False


# --- cash -------------------------------------------------------------------

def test_set_and_add_cash(api):
    assert post(api, "/api/editor/cash", {"mode": "set", "cents": 123_456}).status_code == 200
    assert saved(api)["cash"] == 123_456
    assert post(api, "/api/editor/cash", {"mode": "add", "cents": 44}).status_code == 200
    assert saved(api)["cash"] == 123_500
    assert post(api, "/api/editor/cash", {"mode": "add", "cents": -500}).status_code == 200
    assert saved(api)["cash"] == 123_000


@pytest.mark.parametrize("mode,cents", [
    ("set", True), ("set", 1.5), ("set", "100"), ("set", None), ("set", -1),
    ("set", logic.MAX_CASH + 1), ("add", -(10**9)), ("add", logic.MAX_CASH),
    ("steal", 5), (None, 5), (5, 5),
])
def test_bad_cash_is_refused_and_changes_nothing(api, mode, cents):
    before = saved(api)
    with pytest.raises(logic.RejectedAction):
        logic.editor_cash(before, mode, cents)
    assert post(api, "/api/editor/cash", {"mode": mode, "cents": cents}).status_code == 400
    assert saved(api) == before


# --- weather ----------------------------------------------------------------

def test_fix_and_clear_the_weather(api):
    assert post(api, "/api/editor/weather", {"weather": "storm"}).status_code == 200
    assert saved(api)["day_override"] == {"weather": "storm"}
    assert api.get("/api/state").get_json()["outlook"]["id"] == "storm"
    assert post(api, "/api/editor/weather", {"weather": None}).status_code == 200
    assert saved(api)["day_override"] is None


@pytest.mark.parametrize("weather", ["snow", 5, True, ["sun"], {"weather": "sun"}])
def test_unknown_weather_is_refused(api, weather):
    before = saved(api)
    assert post(api, "/api/editor/weather", {"weather": weather}).status_code == 400
    assert saved(api) == before


# --- skipping days ----------------------------------------------------------

def test_skipping_days_equals_trade_day_that_many_times(api):
    state = db.load(api.path)
    state["stock"]["coffee"] = 50
    api.write(state)
    expected = db.load(api.path)
    for _ in range(3):
        expected, _result = logic.trade_day(expected)
    assert post(api, "/api/editor/skip-days", {"days": 3}).status_code == 200
    now = saved(api)
    assert now["day"] == 4 and len(now["history"]) == 3
    assert now == expected


@pytest.mark.parametrize("days", [0, -1, 31, True, 1.0, "2", None])
def test_bad_day_counts_are_refused(api, days):
    before = saved(api)
    assert post(api, "/api/editor/skip-days", {"days": days}).status_code == 400
    assert saved(api) == before


def test_skip_to_the_end_then_nothing_more(api):
    assert post(api, "/api/editor/skip-days", {"days": logic.LAST_DAY}).status_code == 200
    assert saved(api)["day"] == logic.LAST_DAY + 1
    before = saved(api)
    assert post(api, "/api/editor/skip-days", {"days": 1}).status_code == 400
    assert saved(api) == before


def test_skip_is_refused_while_a_day_is_open(api):
    post(api, "/api/shift/start", {"shop": "cafe"})
    before = saved(api)
    assert before["shift"] is not None
    assert post(api, "/api/editor/skip-days", {"days": 1}).status_code == 400
    assert saved(api) == before


# --- the state patch --------------------------------------------------------

def test_every_field_can_be_set_and_survives_save_and_load(api):
    zone_id = logic.world.start_player()["zone"]
    zone = logic.world.ZONES[zone_id]
    patch = {
        "day": 12,
        "cash": 777_700,
        "seed": 4242,
        "day_override": {"weather": "heat"},
        "stock": {"coffee": 40, "hoodie": 10},
        "prices": {"coffee": 350},
        "shops": {"cafe": {"level": 3}, "surf_shop": {"level": 5}, "merchandise": {"level": 1}},
        "player": {"zone": zone_id, "x": zone["minX"] + 1, "y": zone["minY"] + 1},
    }
    assert post(api, "/api/editor/state", {"patch": patch}).status_code == 200
    now = saved(api)
    assert (now["day"], now["cash"], now["seed"]) == (12, 777_700, 4242)
    assert now["day_override"] == {"weather": "heat"}
    assert now["stock"]["coffee"] == 40 and now["stock"]["hoodie"] == 10
    assert now["prices"]["coffee"] == 350
    assert now["shops"]["cafe"] == {"unlocked": True, "level": 3,
                                    "products": ["coffee", "cake", "bagel"], "staff_places": 0}
    assert now["shops"]["surf_shop"]["staff_places"] == 2
    assert now["shops"]["surf_shop"]["products"] == ["surfboard", "wetsuit", "surf_lesson"]
    assert now["shops"]["merchandise"]["products"] == ["hoodie"]
    assert now["player"] == {"zone": zone_id, "x": zone["minX"] + 1, "y": zone["minY"] + 1}
    assert logic.day_context(now)["weather"] == "heat"


def test_a_full_state_can_be_rebuilt_from_a_patch():
    """The base for demo scenarios: a patch of every field gives back the same state."""
    source = logic.new_state(99)
    source.update(day=9, cash=55_555, day_override={"weather": "rain"})
    source["stock"]["coffee"] = 30
    source["prices"]["coffee"] = 250
    source["shops"]["beach_cafe"] = logic.shop_at_level("beach_cafe", 4)
    patch = {k: copy.deepcopy(source[k]) for k in
             ("day", "cash", "seed", "day_override", "stock", "prices", "shops", "player")}
    assert logic.editor_set_state(logic.new_state(), patch) == {**source, "history": []}


def test_setting_an_earlier_day_cuts_the_history(api):
    post(api, "/api/editor/skip-days", {"days": 5})
    assert [r["day"] for r in saved(api)["history"]] == [1, 2, 3, 4, 5]
    assert post(api, "/api/editor/state", {"patch": {"day": 3}}).status_code == 200
    assert saved(api)["day"] == 3 and [r["day"] for r in saved(api)["history"]] == [1, 2]
    # playing on writes day 3 again, nothing clashes with the old record
    assert post(api, "/api/editor/skip-days", {"days": 1}).status_code == 200
    assert [r["day"] for r in saved(api)["history"]] == [1, 2, 3]


START_ZONE = logic.world.start_player()["zone"]
BAD_PATCHES = [
    {}, [], "cash", None, {"cash": True}, {"cash": 1.5}, {"cash": -1}, {"cash": logic.MAX_CASH + 1},
    {"cash": float("inf")}, {"day": 0}, {"day": logic.LAST_DAY + 2}, {"day": "3"},
    {"seed": -1}, {"seed": 2**32}, {"seed": 1.0}, {"seed": True},
    {"day_override": {"weather": "ice"}}, {"day_override": "rain"},
    {"day_override": {"weather": "sun", "x": 1}},
    {"stock": {"coffee": -1}}, {"stock": {"coffee": 101}}, {"stock": {"lava": 1}},
    {"stock": {"coffee": 60, "cake": 60}}, {"stock": []}, {"stock": {"coffee": 1.5}},
    {"prices": {"coffee": 0}}, {"prices": {"coffee": logic.MAX_PRICE + 1}},
    {"prices": {"coffee": True}}, {"prices": {"nope": 5}},
    {"shops": {"mall": {"level": 1}}}, {"shops": {"cafe": {"level": 6}}},
    {"shops": {"cafe": {"level": -1}}}, {"shops": {"cafe": {"level": 1.5}}},
    {"shops": {"cafe": {"unlocked": True, "level": 2, "products": ["coffee"],
                        "staff_places": 0}}},
    {"shops": {"cafe": {"unlocked": True, "level": 1, "products": ["beer"],
                        "staff_places": 0}}},
    {"shops": {"cafe": {"unlocked": False, "level": 1, "products": [], "staff_places": 0}}},
    {"shops": {"cafe": {"unlocked": True, "level": 1, "products": ["coffee"],
                        "staff_places": 0, "extra": 1}}},
    {"shops": {"cafe": {"unlocked": 1, "level": 1, "products": ["coffee"],
                        "staff_places": 0}}},
    {"shops": []}, {"shops": {"cafe": 3}}, {"shops": {"cafe": {"level": 0}}},
    {"player": {"zone": "mars", "x": 1, "y": 1}}, {"player": {"zone": "x"}},
    {"player": {"zone": START_ZONE, "x": float("nan"), "y": 1}},
    {"player": {"zone": START_ZONE, "x": 10**9, "y": 1}},
    {"player": [1, 2]}, {"nonsense": 1}, {"history": []}, {"shift": None},
    # valid first, invalid later: nothing may be half applied
    {"cash": 500, "stock": {"coffee": -1}}, {"day": 4, "seed": "x"},
]


@pytest.mark.parametrize("patch", BAD_PATCHES, ids=range(len(BAD_PATCHES)))
def test_a_bad_patch_is_refused_and_changes_nothing(api, patch):
    before = saved(api)
    state_in = copy.deepcopy(before)
    with pytest.raises(logic.RejectedAction):
        logic.editor_set_state(state_in, patch)
    assert state_in == before
    # the API refuses it as well (NaN and infinity are not valid JSON, Python's dumps still sends them)
    response = api.post("/api/editor/state", data=json.dumps({"patch": patch}),
                        content_type="application/json")
    assert response.status_code == 400
    assert saved(api) == before


def test_the_patch_is_refused_while_a_day_is_open(api):
    post(api, "/api/shift/start", {"shop": "cafe"})
    before = saved(api)
    assert post(api, "/api/editor/state", {"patch": {"cash": 5}}).status_code == 400
    assert saved(api) == before


def test_shop_levels_follow_the_window_order():
    assert logic.shop_at_level("cafe", 0)["unlocked"] is False
    assert logic.shop_at_level("cafe", 1)["products"] == ["coffee"]
    top = logic.shop_at_level("cafe", 5)
    assert top == {"unlocked": True, "level": 5, "products": ["coffee", "cake", "bagel"],
                   "staff_places": 2}
    for sid in logic.SHOPS:
        for level in range(0, 6):
            entry = logic.shop_at_level(sid, level)
            assert entry == logic._check_shop_entry(sid, entry)


# --- reset ------------------------------------------------------------------

def test_reset_needs_confirm_and_takes_a_seed(api):
    post(api, "/api/editor/skip-days", {"days": 3})
    before = saved(api)
    assert post(api, "/api/editor/reset", {}).status_code == 400
    assert post(api, "/api/editor/reset", {"confirm": "yes"}).status_code == 400
    assert post(api, "/api/editor/reset", {"confirm": True, "seed": -3}).status_code == 400
    assert post(api, "/api/editor/reset", {"confirm": True, "seed": True}).status_code == 400
    assert saved(api) == before
    assert post(api, "/api/editor/reset", {"confirm": True, "seed": 31}).status_code == 200
    assert saved(api) == logic.new_state(31)
    assert post(api, "/api/editor/reset", {"confirm": True}).status_code == 200
    assert saved(api)["day"] == 1 and saved(api)["history"] == []


# --- the seed stays on the server -------------------------------------------

def test_no_answer_contains_the_seed(api):
    post(api, "/api/editor/state", {"patch": {"seed": 987_654_321}})
    answers = [api.get("/api/state")]
    answers += [post(api, u, b) for u, b in EDITOR_CALLS[:-1]]
    answers.append(post(api, "/api/editor/state", {"patch": {"seed": -1}}))
    for answer in answers:
        body = answer.get_json()
        assert "seed" not in body.get("state", body)
        assert "987654321" not in answer.get_data(as_text=True)


def test_refused_with_a_foreign_host_header(api):
    before = saved(api)
    for host in ("evil.example", "evil.example:8000", "127.0.0.1.evil.example"):
        assert post(api, "/api/editor/cash", {"mode": "set", "cents": 5},
                    headers={"Host": host}).status_code == 400
    assert saved(api) == before
    assert post(api, "/api/editor/cash", {"mode": "set", "cents": 5},
                headers={"Host": "127.0.0.1:8000"}).status_code == 200


def test_lowering_a_shop_dismisses_the_employees_without_a_place():
    state = logic.editor_set_state(logic.new_state(), {"shops": {"cafe": {"level": 3}}, "cash": 90_000})
    state = logic.editor_set_state(state, {"shops": {"cafe": {"level": 5}}})
    state = logic.hire(state, "cafe", 1)
    state = logic.hire(state, "cafe", 2)
    assert len(state["employees"]) == 2
    state = logic.editor_set_state(state, {"shops": {"cafe": {"level": 4}}})
    assert [e["place"] for e in state["employees"]] == [1]
    state = logic.editor_set_state(state, {"shops": {"cafe": {"level": 2}}})
    assert state["employees"] == []
