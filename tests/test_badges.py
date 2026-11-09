"""Checks from specs/badges.md ("Done when")."""

import copy
import sqlite3

import pytest

import app
import db
import logic

SEED = 7


def day_result(day, sold=0, demand=None, net=0, lost=0, played=False):
    """A booked day as the rules write it, with only the numbers the badges read."""
    return {
        "day": day,
        "lines": [{"product": "coffee", "price": 200, "demand": sold if demand is None else demand,
                   "sold": sold, "revenue": 0, "cogs": 0, "gross_profit": net}],
        "revenue": 0, "cogs": 0, "gross_profit": net, "wages": 0, "net": net,
        "lost": lost, "played": played, "cash_after": 0,
    }


def end_day(state, **kwargs):
    """Book one day the way _close_shift does: history, badges, then the next day."""
    result = day_result(state["day"], **kwargs)
    state["history"].append(result)
    logic.award_badges(state, result)
    state["day"] += 1
    return result["badges"]


def earned(state):
    return [b["id"] for b in state["badges"]]


def fresh():
    return logic.new_state(SEED)


# ---- 1. each badge, on the day its condition is first true, never twice --------------------

def test_there_are_twenty_badges_with_unique_ids():
    assert len(logic.BADGES) == 20
    assert len(set(logic.BADGE_IDS)) == 20
    assert logic.new_state(SEED)["badges"] == []


def test_every_badge_has_a_medal():
    assert set(logic.BADGE_TIER) == set(logic.BADGE_IDS)
    assert set(logic.BADGE_TIER.values()) <= set(logic.BADGE_TIERS)


def test_a_quiet_day_earns_nothing():
    state = fresh()
    assert end_day(state) == []
    assert state["badges"] == []


def test_first_sale_and_nobody_left():
    state = fresh()
    assert end_day(state, sold=3, demand=5, lost=2) == ["first-sale"]
    assert end_day(state, sold=3, lost=0) == ["no-one-left"]
    assert end_day(state, sold=3, lost=0) == []  # never twice
    assert state["badges"][:2] == [{"id": "first-sale", "day": 1}, {"id": "no-one-left", "day": 2}]


def test_own_shift():
    state = fresh()
    assert "own-shift" in end_day(state, played=True)


def test_good_day_and_record_day_thresholds():
    state = fresh()
    end_day(state, net=logic.GOOD_DAY_NET - 1)
    assert "good-day" not in earned(state)
    assert "good-day" in end_day(state, net=logic.GOOD_DAY_NET)
    end_day(state, net=logic.RECORD_DAY_NET - 1)
    assert "record-day" not in earned(state)
    assert "record-day" in end_day(state, net=logic.RECORD_DAY_NET)


def test_cash_badges():
    state = fresh()
    state["cash"] = logic.DOUBLED_CASH - 1
    assert "doubled" not in end_day(state)
    state["cash"] = logic.DOUBLED_CASH
    assert "doubled" in end_day(state)
    state["cash"] = logic.WEALTHY_CASH
    assert "wealthy" in end_day(state)


def hire(state, count):
    """Put `count` employees into the unlocked shops' places, without the cash rules."""
    for sid in state["shops"]:
        state["shops"][sid] = logic.shop_at_level(sid, 1 + len(logic.SHOPS[sid]["window"]))
    places = [(sid, p) for sid in logic.SHOPS for p in (1, 2)]
    for sid, place in places[:count]:
        logic._add_employee(state, sid, place)


def test_team_badges():
    state = fresh()
    hire(state, 1)
    assert "first-hire" in end_day(state)
    assert "team" not in earned(state)
    state = fresh()
    hire(state, logic.TEAM_SIZE)
    assert {"first-hire", "team"} <= set(end_day(state))
    assert "big-team" not in earned(state)
    state = fresh()
    hire(state, logic.BIG_TEAM_SIZE)
    assert "big-team" in end_day(state)


def test_pro_needs_the_highest_level():
    state = fresh()
    hire(state, 1)
    state["employees"][0]["level"] = logic.EMPLOYEE_MAX_LEVEL - 1
    end_day(state)
    assert "pro" not in earned(state)
    state["employees"][0]["level"] = logic.EMPLOYEE_MAX_LEVEL
    assert "pro" in end_day(state)


def test_expansion_upgrade_and_empire():
    state = fresh()
    end_day(state)
    assert not {"expansion", "upgrade", "empire"} & set(earned(state))
    state["shops"]["cafe"] = logic.shop_at_level("cafe", 2)
    assert end_day(state) == ["upgrade"]
    state["shops"]["beach_cafe"] = logic.shop_at_level("beach_cafe", 1)
    assert end_day(state) == ["expansion"]
    for sid in logic.SHOPS:
        state["shops"][sid] = logic.shop_at_level(sid, 1)
    assert end_day(state) == ["empire"]


def test_storm_proof_needs_a_stormy_day_with_a_profit():
    state = logic.set_day_override(fresh(), "rain")
    end_day(state, net=100)
    assert "storm-proof" not in earned(state)
    state = logic.set_day_override(state, "storm")
    end_day(state, net=0)
    assert "storm-proof" not in earned(state)
    assert "storm-proof" in end_day(state, net=100)


def test_season_winner_only_at_the_end_with_enough_cash():
    state = fresh()
    state["day"] = logic.LAST_DAY
    state["cash"] = logic.WINNER_CASH - 1
    end_day(state)
    assert "season-winner" not in earned(state)
    state = fresh()
    state["day"] = logic.LAST_DAY - 1
    state["cash"] = logic.WINNER_CASH
    end_day(state)
    assert "season-winner" not in earned(state)
    assert "season-winner" in end_day(state)


# ---- 2. streaks ---------------------------------------------------------------------------

def test_profit_streaks_start_again_after_a_day_without_profit():
    state = fresh()
    end_day(state, net=10)
    end_day(state, net=10)
    end_day(state, net=0)  # breaks the run
    end_day(state, net=10)
    end_day(state, net=10)
    assert "streak-3" not in earned(state)
    assert "streak-3" in end_day(state, net=10)
    for _ in range(logic.LONG_STREAK - logic.SHORT_STREAK - 1):
        end_day(state, net=10)
    assert "streak-7" not in earned(state)
    assert "streak-7" in end_day(state, net=10)
    for _ in range(logic.LONGEST_STREAK - logic.LONG_STREAK - 1):
        end_day(state, net=10)
    assert "streak-14" not in earned(state)
    assert "streak-14" in end_day(state, net=10)


def test_a_loss_counts_as_no_profit():
    state = fresh()
    end_day(state, net=10)
    end_day(state, net=-5)
    end_day(state, net=10)
    end_day(state, net=10)
    assert "streak-3" not in earned(state)


def test_hard_worker_needs_five_played_days_in_a_row():
    state = fresh()
    for _ in range(logic.WORK_STREAK - 1):
        end_day(state, played=True)
    end_day(state, played=False)
    for _ in range(logic.WORK_STREAK - 1):
        end_day(state, played=True)
    assert "hard-worker" not in earned(state)
    assert "hard-worker" in end_day(state, played=True)


def test_a_gap_in_the_days_breaks_a_streak():
    state = fresh()
    end_day(state, net=10)
    end_day(state, net=10)
    state["day"] += 1  # a day missing from the history
    end_day(state, net=10)
    assert "streak-3" not in earned(state)


# ---- the real day rules award badges ------------------------------------------------------

def test_trade_day_awards_and_lists_the_day_s_badges():
    state = logic.buy(fresh(), "coffee", 20)
    state, result = logic.trade_day(state)
    assert result["played"] is False
    assert "first-sale" in result["badges"]
    assert {"id": "first-sale", "day": 1} in state["badges"]


def test_a_played_shift_earns_behind_the_counter():
    state = logic.set_day_override(fresh(), "storm")
    state["stock"]["coffee"] = 30
    state = logic.start_shift(state, "cafe")
    state, result = logic.skip_shift(state)
    assert result["played"] is True
    assert "own-shift" in result["badges"]


def test_a_skipped_open_day_is_not_a_played_shift():
    state = logic.open_day(fresh())
    state, result = logic.skip_shift(state)
    assert result["played"] is False
    assert "own-shift" not in earned(state)


def test_the_preview_does_not_change_the_saved_badges():
    state = logic.buy(fresh(), "coffee", 20)
    before = copy.deepcopy(state)
    logic.trade_day(state)
    assert state == before


# ---- 4. no request can add a badge --------------------------------------------------------

@pytest.fixture
def api(tmp_path, monkeypatch):
    path = tmp_path / "run.db"
    db.save(logic.new_state(SEED), path)
    real_save, real_new = db.save, db.save_new_run
    monkeypatch.setattr(app, "load_run", lambda: db.load(path))
    monkeypatch.setattr(app.db, "save", lambda s: real_save(s, path))
    monkeypatch.setattr(app.db, "save_new_run", lambda s: real_new(s, path))
    client = app.app.test_client()
    client.path = path
    client.write = lambda state: real_save(state, path)
    return client


FAKE = {"badges": [{"id": "season-winner", "day": 1}], "badge": "season-winner"}
CALLS = ["/api/buy", "/api/price", "/api/shop/unlock", "/api/shop/upgrade", "/api/staff/hire",
         "/api/staff/upgrade", "/api/staff/fire", "/api/day/open", "/api/shift/start",
         "/api/shift/refill", "/api/shift/sell", "/api/shift/tick", "/api/shift/skip",
         "/api/player", "/api/new-run", "/api/editor/cash", "/api/editor/skip-days"]


@pytest.mark.parametrize("url", CALLS)
def test_no_endpoint_takes_a_badge_from_the_request(api, url):
    api.post(url, json=FAKE)
    assert "season-winner" not in earned(db.load(api.path))


def test_the_state_answer_lists_every_badge(api):
    data = api.get("/api/state").get_json()
    assert [b["id"] for b in data["badges"]] == list(logic.BADGE_IDS)
    assert all(set(b) == {"id", "name", "icon", "text", "tier", "day"} for b in data["badges"])
    assert all(b["day"] is None for b in data["badges"])


# ---- badges are given the moment they are reached --------------------------------------------

def badge_days(client):
    return {b["id"]: b["day"] for b in db.load(client.path)["badges"]}


def test_the_first_sale_pops_at_the_sale_not_at_the_end_of_the_day(api):
    state = logic.set_day_override(logic.new_state(SEED), "storm")
    state["stock"]["coffee"] = 30
    api.write(state)
    assert api.post("/api/shift/start", json={"shop": "cafe"}).status_code == 200
    assert badge_days(api) == {"own-shift": 1}  # the shift is played from its start
    api.post("/api/shift/refill", json={"product": "coffee", "quantity": 5})
    sold = False
    for _ in range(40):  # wait for a customer, then sell
        if api.post("/api/shift/sell", json={"product": "coffee"}).status_code == 200:
            sold = True
            break
        api.post("/api/shift/tick", json={})
    assert sold
    saved = db.load(api.path)
    assert saved["shift"] is not None  # the day is still open
    assert {"id": "first-sale", "day": 1} in saved["badges"]
    data = api.get("/api/state").get_json()
    assert next(b for b in data["badges"] if b["id"] == "first-sale")["day"] == 1


def test_a_hire_and_an_unlock_give_their_badge_at_once(api):
    state = logic.new_state(SEED)
    state["cash"] = 500_000
    api.write(state)
    assert api.post("/api/shop/upgrade", json={"shop": "cafe", "item": "staff_1"}).status_code == 200
    # buying the first employee place puts a person on it: both badges at once, on day 1
    assert badge_days(api)["upgrade"] == 1 and badge_days(api)["first-hire"] == 1
    assert api.post("/api/shop/unlock", json={"shop": "beach_cafe"}).status_code == 200
    assert badge_days(api)["expansion"] == 1


def test_the_editor_gives_state_badges_at_once(api, monkeypatch):
    monkeypatch.setenv("CT_EDITOR", "1")
    body = {"mode": "set", "cents": logic.WEALTHY_CASH}
    assert api.post("/api/editor/cash", json=body).status_code == 200
    assert badge_days(api) == {"doubled": 1, "wealthy": 1}


def test_day_badges_wait_for_the_end_of_the_day():
    state = fresh()
    state["cash"] = logic.WEALTHY_CASH
    given = logic.award_badges(state)
    assert set(given) == {"doubled", "wealthy"}
    assert not any(b["id"] in {"good-day", "streak-3", "season-winner"} for b in state["badges"])


def test_the_day_s_list_has_the_badges_given_during_the_day():
    state = logic.set_day_override(fresh(), "sun")
    state["cash"] = logic.DOUBLED_CASH
    logic.award_badges(state)  # during day 1
    listed = end_day(state, net=logic.GOOD_DAY_NET)
    assert listed == ["doubled", "good-day"]
    assert end_day(state) == []  # the next day lists only its own


def test_no_badge_after_the_season():
    state = fresh()
    state["day"] = logic.LAST_DAY + 1
    state["cash"] = logic.WEALTHY_CASH
    assert logic.award_badges(state) == []


# ---- 5. editor ----------------------------------------------------------------------------

def test_an_earlier_day_cuts_the_badges_with_the_history():
    state = logic.buy(fresh(), "coffee", 60)
    for _ in range(4):
        state, _ = logic.trade_day(state)
    assert state["badges"]
    cut = logic.editor_set_state(state, {"day": 2})
    assert all(b["day"] < 2 for b in cut["badges"])
    assert [r["day"] for r in cut["history"]] == [1]


def test_the_editor_can_set_badges():
    state = logic.editor_set_state(fresh(), {"day": 5, "badges": [{"id": "good-day", "day": 3}]})
    assert state["badges"] == [{"id": "good-day", "day": 3}]


@pytest.mark.parametrize("badges", [
    "good-day",
    [{"id": "nope", "day": 1}],
    [{"id": "good-day", "day": 1}, {"id": "good-day", "day": 2}],
    [{"id": "good-day", "day": 5}],   # not before the current day
    [{"id": "good-day", "day": 0}],
    [{"id": "good-day"}],
    [{"id": "good-day", "day": True}],
])
def test_a_bad_badges_patch_is_refused_and_changes_nothing(badges):
    state = logic.editor_set_state(fresh(), {"day": 5})
    before = copy.deepcopy(state)
    with pytest.raises(logic.RejectedAction):
        logic.editor_set_state(state, {"badges": badges})
    assert state == before


# ---- 6. saved and loaded ------------------------------------------------------------------

def test_badges_are_saved_and_loaded(tmp_path):
    path = tmp_path / "run.db"
    state = logic.buy(fresh(), "coffee", 20)
    state, _ = logic.trade_day(state)
    db.save(state, path)
    assert db.load(path) == state
    db.save_new_run(logic.new_state(SEED), path)
    assert db.load(path)["badges"] == []


def test_an_old_save_without_the_table_loads_with_no_badges(tmp_path):
    path = tmp_path / "run.db"
    db.save(fresh(), path)
    with sqlite3.connect(path) as conn:
        conn.execute("DROP TABLE badges")
    assert db.load(path)["badges"] == []
