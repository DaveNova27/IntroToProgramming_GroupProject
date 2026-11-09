"""Checks from specs/day-context.md ("Done when"). One test per check."""

import collections
import copy
import json

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
    real_new_run = db.save_new_run
    monkeypatch.setattr(app.db, "save_new_run", lambda state: real_new_run(state, path))
    return path


def refused(action, state):
    before = copy.deepcopy(state)
    with pytest.raises(logic.RejectedAction):
        action(state)
    assert state == before


# ---- Check 1: seed and day decide the weather ------------------------------

def test_the_same_seed_and_day_always_give_the_same_weather():
    forward = [logic.make_day_context(SEED, d) for d in range(1, 31)]
    backward = [logic.make_day_context(SEED, d) for d in range(30, 0, -1)][::-1]
    assert forward == backward
    other = [logic.make_day_context(SEED + 1, d) for d in range(1, 31)]
    assert forward != other


def test_a_new_state_has_the_seed_and_no_override():
    state = logic.new_state(SEED)
    assert state["seed"] == SEED and state["day_override"] is None
    assert logic.new_state() == logic.new_state()  # the default is the same every time
    assert 0 <= logic.new_seed() < 2 ** 32


# ---- Check 2: shares, temperatures ----------------------------------------

def test_sun_is_the_most_frequent_and_shares_follow_the_weights():
    days = [logic.make_day_context(seed, day) for seed in range(1, 201) for day in range(1, 31)]
    count = collections.Counter(c["weather"] for c in days)
    assert set(count) == set(logic.WEATHER)
    assert count.most_common(1)[0][0] == "sun"
    total = sum(w["weight"] for w in logic.WEATHER.values())
    for wid, w in logic.WEATHER.items():
        assert abs(count[wid] / len(days) - w["weight"] / total) < 0.03
    for c in days:
        low, high = logic.WEATHER[c["weather"]]["temp"]
        assert isinstance(c["temperature"], int) and low <= c["temperature"] <= high


def test_the_demand_percent_is_whole_numbers_for_every_shop():
    for w in logic.WEATHER.values():
        assert set(w["demand_percent"]) == set(logic.SHOPS)
        assert all(isinstance(v, int) and v > 0 for v in w["demand_percent"].values())


def test_the_weather_does_not_change_the_customers_yet():
    for override in (None, {"weather": "storm"}, {"weather": "heat"}):
        state = logic.new_state(SEED)
        state["day_override"] = override
        state["stock"]["coffee"] = 10
        assert logic.trade_day(state)[1]["lines"][0]["sold"] == 10


# ---- Check 3: override ----------------------------------------------------

def test_the_override_fixes_the_weather_and_clearing_it_brings_the_roll_back():
    state = logic.new_state(SEED)
    rolled = logic.day_context(state)
    other = next(w for w in logic.WEATHER if w != rolled["weather"])
    fixed = logic.set_day_override(state, other)
    assert logic.day_context(fixed)["weather"] == other
    low, high = logic.WEATHER[other]["temp"]
    assert low <= logic.day_context(fixed)["temperature"] <= high
    assert logic.day_context(logic.set_day_override(fixed, None)) == rolled


# ---- Check 4: refused actions ---------------------------------------------

@pytest.mark.parametrize("bad", ["fog", "", 5, 1.5, True, ["sun"], {"weather": "sun"}])
def test_an_unknown_weather_is_refused(bad):
    refused(lambda s: logic.set_day_override(s, bad), logic.new_state(SEED))


def test_the_endpoint_is_refused_without_the_switch(run_on_disk, monkeypatch):
    monkeypatch.delenv("CAMPUS_TYCOON_DEMO", raising=False)
    before = db.load(run_on_disk)
    response = app.app.test_client().post("/api/day-override", json={"weather": "storm"})
    assert response.status_code == 400
    assert db.load(run_on_disk) == before


def test_the_endpoint_is_refused_from_another_address(run_on_disk, monkeypatch):
    monkeypatch.setenv("CAMPUS_TYCOON_DEMO", "1")
    before = db.load(run_on_disk)
    client = app.app.test_client()
    response = client.post("/api/day-override", json={"weather": "storm"},
                           environ_overrides={"REMOTE_ADDR": "203.0.113.5"})
    assert response.status_code == 400
    assert db.load(run_on_disk) == before


def test_the_endpoint_works_with_the_switch_on_this_computer_and_refuses_bad_ids(run_on_disk, monkeypatch):
    monkeypatch.setenv("CAMPUS_TYCOON_DEMO", "1")
    client = app.app.test_client()
    ok = client.post("/api/day-override", json={"weather": "storm"})
    # the real weather is not sent before the day is open: the fixed one shows in the outlook
    assert ok.status_code == 200 and ok.get_json()["state"]["outlook"]["id"] == "storm"
    saved = db.load(run_on_disk)
    for bad in ({"weather": "fog"}, {"weather": 3}, {"weather": ["sun"]}):
        assert client.post("/api/day-override", json=bad).status_code == 400
        assert db.load(run_on_disk) == saved
    assert client.post("/api/day-override", json={"weather": None}).get_json()["state"]["outlook"]["id"] \
        == logic.make_outlook(SEED, 1)["weather"]


# ---- Check 5: the seed never leaves the server -----------------------------

def test_the_seed_is_in_no_answer(run_on_disk, monkeypatch):
    monkeypatch.setenv("CAMPUS_TYCOON_DEMO", "1")
    client = app.app.test_client()
    client.post("/api/buy", json={"product": "coffee", "quantity": 10})
    answers = [
        client.get("/api/state"),
        client.get("/api/world"),
        client.post("/api/buy", json={"product": "coffee", "quantity": 1}),
        client.post("/api/buy", json={"product": "coffee", "quantity": -1}),  # a refusal
        client.post("/api/day-override", json={"weather": "rain"}),
        client.post("/api/open", json={"day": 1}),
    ]
    for response in answers:
        text = response.get_data(as_text=True)
        assert str(SEED) not in text and '"seed"' not in text
    state = client.get("/api/state").get_json()
    # the day after /api/open is not open yet: no real weather, only the outlook
    assert state["weather"] is None


# ---- Check 6: saving -------------------------------------------------------

def test_the_seed_and_the_override_survive_a_restart(tmp_path):
    path = tmp_path / "run.db"
    state = logic.set_day_override(logic.new_state(SEED), "heat")
    db.save(state, path)
    loaded = db.load(path)
    assert loaded["seed"] == SEED and loaded["day_override"] == {"weather": "heat"}
    assert loaded == state


def test_a_save_from_before_this_spec_gets_one_seed_and_keeps_it(tmp_path):
    path = tmp_path / "old.db"
    db.save(logic.new_state(), path)
    with db.connect(path) as conn:
        conn.execute("DROP TABLE meta")
    first = db.load(path)
    assert isinstance(first["seed"], int) and first["day_override"] is None
    assert db.load(path)["seed"] == first["seed"]
    assert json.loads(json.dumps(first)) == first


def test_a_new_run_through_the_api_draws_a_fresh_seed(run_on_disk):
    client = app.app.test_client()
    assert client.post("/api/new-run", json={"confirm": True}).status_code == 200
    assert db.load(run_on_disk)["seed"] != SEED


# ---- review fixes ---------------------------------------------------------

def test_an_unknown_saved_override_falls_back_to_the_roll_and_does_not_crash():
    rolled = logic.make_day_context(SEED, 1)
    for bad in ({"weather": "fog"}, {"weather": ["sun"]}, {}, "storm", 5):
        assert logic.make_day_context(SEED, 1, bad) == rolled


def test_loading_a_save_does_not_change_the_file(tmp_path):
    path = tmp_path / "run.db"
    db.save(logic.new_state(SEED), path)
    before = path.read_bytes()
    db.load(path)
    assert path.read_bytes() == before


def test_the_weather_is_gone_when_the_season_is_over(monkeypatch):
    state = logic.new_state(SEED)
    state["day"] = logic.LAST_DAY + 1
    monkeypatch.setattr(app, "load_run", lambda: state)
    assert app.app.test_client().get("/api/state").get_json()["weather"] is None


def test_the_endpoint_is_refused_behind_a_proxy_and_accepts_ipv4_mapped_loopback(run_on_disk, monkeypatch):
    monkeypatch.setenv("CAMPUS_TYCOON_DEMO", "1")
    client = app.app.test_client()
    before = db.load(run_on_disk)
    proxied = client.post("/api/day-override", json={"weather": "rain"},
                          headers={"X-Forwarded-For": "203.0.113.5"})
    assert proxied.status_code == 400 and db.load(run_on_disk) == before
    mapped = client.post("/api/day-override", json={"weather": "rain"},
                         environ_overrides={"REMOTE_ADDR": "::ffff:127.0.0.1"})
    assert mapped.status_code == 200
