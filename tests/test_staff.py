"""Employees: hire, level up, fire, work and wages (specs/staff.md)."""

import copy

import pytest

import db
import logic


def with_places(places=2, cash=100_000, coffee=100):
    """A cafe with bought employee places, plenty of cash and stock in the storeroom."""
    state = logic.new_state()
    state["cash"] = cash
    state["stock"]["coffee"] = coffee
    state["shops"]["cafe"]["staff_places"] = places
    return state


def staffed(*jobs, **kwargs):
    """A run with the given places hired (1 = refiller, 2 = seller)."""
    state = with_places(**kwargs)
    for place in jobs:
        state = logic.hire(state, "cafe", place)
    return state


def run_day(state):
    state = logic.open_day(state)
    result = None
    while result is None:
        state, result = logic.tick(state)
    return state, result


# --- hire / upgrade / fire -----------------------------------------------------

def test_hire_costs_the_price_and_takes_the_job_from_the_place():
    state = with_places()
    new = logic.hire(state, "cafe", 1)
    assert new["cash"] == state["cash"] - logic.HIRE_PRICE
    assert new["employees"] == [{"id": 1, "name": "Mia", "shop": "cafe", "place": 1,
                                 "job": "refiller", "level": 1, "working": True}]
    assert logic.hire(new, "cafe", 2)["employees"][1]["job"] == "seller"
    assert state["employees"] == []  # the old state is not changed


def test_upgrade_costs_the_price_raises_the_level_and_the_wage():
    state = staffed(1)
    wage1 = logic.employee_wage(state["employees"][0])
    up = logic.upgrade_employee(state, 1)
    assert up["employees"][0]["level"] == 2
    assert up["cash"] == state["cash"] - logic.UPGRADE_PRICES[2]
    assert logic.employee_wage(up["employees"][0]) > wage1
    top = logic.upgrade_employee(up, 1)
    assert top["employees"][0]["level"] == logic.EMPLOYEE_MAX_LEVEL
    assert top["cash"] == up["cash"] - logic.UPGRADE_PRICES[3]


def test_fire_frees_the_place_without_a_refund_and_the_level_is_lost():
    state = logic.upgrade_employee(staffed(1), 1)
    fired = logic.fire_employee(state, 1)
    assert fired["employees"] == [] and fired["cash"] == state["cash"]
    assert fired["shops"]["cafe"]["staff_places"] == 2
    again = logic.hire(fired, "cafe", 1)
    assert again["employees"][0]["level"] == 1 and again["employees"][0]["id"] == 2


def test_ids_are_never_used_twice_and_names_come_from_the_list():
    state = staffed(1, 2)
    assert [e["name"] for e in state["employees"]] == list(logic.EMPLOYEE_NAMES[:2])
    state = logic.fire_employee(state, 2)
    state = logic.hire(state, "cafe", 2)  # the highest id was dismissed: still a new id
    assert [e["id"] for e in state["employees"]] == [1, 3]
    stale = logic.fire_employee(state, 3)  # a stale request for the old id 2 hits nobody
    with pytest.raises(logic.RejectedAction):
        logic.fire_employee(stale, 2)
    assert logic.hire(stale, "cafe", 2)["employees"][-1]["id"] == 4


BAD_ACTIONS = [
    lambda s: logic.hire(s, "nowhere", 1),
    lambda s: logic.hire(s, 5, 1),
    lambda s: logic.hire(s, "beach_cafe", 1),     # locked and not a shift shop
    lambda s: logic.hire(s, "cafe", 0),
    lambda s: logic.hire(s, "cafe", 3),           # place not bought
    lambda s: logic.hire(s, "cafe", -1),
    lambda s: logic.hire(s, "cafe", True),
    lambda s: logic.hire(s, "cafe", 1.0),
    lambda s: logic.hire(s, "cafe", "1"),
    lambda s: logic.hire(s, "cafe", None),
    lambda s: logic.upgrade_employee(s, 99),
    lambda s: logic.upgrade_employee(s, True),
    lambda s: logic.upgrade_employee(s, "1"),
    lambda s: logic.upgrade_employee(s, 1.5),
    lambda s: logic.fire_employee(s, 99),
    lambda s: logic.fire_employee(s, 0),
    lambda s: logic.fire_employee(s, None),
]


@pytest.mark.parametrize("action", BAD_ACTIONS)
def test_bad_requests_are_refused_and_change_nothing(action):
    state = staffed(1)
    before = copy.deepcopy(state)
    with pytest.raises(logic.RejectedAction):
        action(state)
    assert state == before


def test_a_taken_place_and_a_maxed_level_are_refused():
    state = staffed(1)
    for action in (lambda s: logic.hire(s, "cafe", 1),
                   lambda s: logic.upgrade_employee(logic.upgrade_employee(
                       logic.upgrade_employee(s, 1), 1), 1)):
        before = copy.deepcopy(state)
        with pytest.raises(logic.RejectedAction):
            action(state)
        assert state == before


def test_too_little_cash_refuses_hire_and_upgrade_and_changes_nothing():
    for state, action in ((with_places(cash=logic.HIRE_PRICE - 1),
                           lambda s: logic.hire(s, "cafe", 1)),
                          (logic.hire(with_places(cash=logic.HIRE_PRICE), "cafe", 1),
                           lambda s: logic.upgrade_employee(s, 1))):
        before = copy.deepcopy(state)
        with pytest.raises(logic.RejectedAction):
            action(state)
        assert state == before


def test_nothing_works_after_the_last_day():
    state = staffed(1)
    state["day"] = logic.LAST_DAY + 1
    for action in (lambda s: logic.hire(s, "cafe", 2), lambda s: logic.upgrade_employee(s, 1),
                   lambda s: logic.fire_employee(s, 1)):
        before = copy.deepcopy(state)
        with pytest.raises(logic.RejectedAction):
            action(state)
        assert state == before


def test_a_new_run_has_no_employees():
    assert logic.new_state()["employees"] == []


# --- a day with staff ----------------------------------------------------------

def test_a_hired_team_runs_the_whole_day_alone_and_is_paid():
    state = staffed(1, 2)
    cash = state["cash"]
    state, result = run_day(state)
    assert result["revenue"] > 0 and state["cash"] > cash - 5_000
    wage = sum(logic.employee_wage(e) for e in state["employees"])
    assert result["wages"] == wage and result["net"] == result["gross_profit"] - wage
    assert result["wages_unpaid"] == []
    assert result["cash_after"] == state["cash"]
    assert state["day"] == 2 and state["shift"] is None
    assert state["stock"]["coffee"] < 100  # stock really went over the counter


def test_open_day_starts_the_shift_by_itself_only_with_a_working_employee():
    state = logic.open_day(staffed(1))
    assert state["shift"]["shop"] == "cafe" and state["shift"]["staffed"] is True
    assert state["shift"]["shift_end"] == logic.SHIFT_TICKS
    plain = logic.open_day(with_places())
    assert plain["shift"]["shop"] is None
    with pytest.raises(logic.RejectedAction):
        logic.start_shift(state, "cafe")


def test_the_player_can_work_next_to_the_staff_in_the_auto_shift():
    state = logic.open_day(staffed(2))
    state = logic.refill(state, "coffee", 5)
    assert state["shift"]["counter"]["coffee"] == 5


def test_skipping_with_a_team_sells_and_without_one_sells_nothing():
    state, result = logic.skip_shift(logic.open_day(staffed(1, 2)))
    assert result["revenue"] > 0
    state, result = logic.skip_shift(logic.open_day(with_places(cash=1_000)))
    assert result["revenue"] == 0 and result["wages"] == 0


def test_a_single_employee_does_both_jobs():
    for place in (1, 2):  # a lone refiller sells too, a lone seller refills too
        state, result = run_day(staffed(place))
        assert result["revenue"] > 0 and result["wages"] > 0


def test_staff_do_not_use_more_stock_than_the_storeroom_or_counter_holds():
    state = logic.open_day(staffed(1, 2, places=2, coffee=7))
    while state["shift"] is not None:
        shift = state["shift"]
        assert sum(shift["counter"].values()) <= logic.COUNTER_UNITS
        assert min(state["stock"].values()) >= 0
        state, _ = logic.tick(state)
    assert state["stock"]["coffee"] + sum(
        line["sold"] for line in state["history"][-1]["lines"]) == 7


def sold_after(state, ticks):
    state = logic.open_day(state)
    for _ in range(ticks):
        state, _ = logic.tick(state)
    return sum(state["shift"]["sold"].values())


def crowded(state):
    """An open day where 20 customers wait with much patience and the counter is full."""
    state = logic.open_day(state)
    state["stock"]["coffee"] = 100
    state["shift"]["counter"]["coffee"] = 20
    state["stock"]["coffee"] -= 20
    state["shift"]["queue"] = [{"product": "coffee", "arrives": 0, "patience_until": 80}
                               for _ in range(20)]
    return state


def test_higher_levels_carry_and_sell_faster():
    state = staffed(1, 2)
    top = state
    for _ in range(2):
        top = logic.upgrade_employee(logic.upgrade_employee(top, 1), 2)
    sold = {}
    for name, start in (("low", state), ("top", top)):
        run = crowded(start)
        for _ in range(12):
            run, _ = logic.tick(run)
        sold[name] = run["shift"]["sold"]["coffee"]
    assert sold == {"low": 3, "top": 6}  # every 4th tick against every 2nd tick


def test_a_refiller_carries_more_per_tick_on_a_higher_level():
    state = staffed(1)
    top = logic.upgrade_employee(logic.upgrade_employee(state, 1), 1)
    carried = []
    for start in (state, top):
        run = logic.open_day(start)
        before = run["stock"]["coffee"]
        for _ in range(4):
            run, _ = logic.tick(run)
        carried.append(before - run["stock"]["coffee"])
    assert carried == [4, 12]  # 1 unit per tick against 3 units per tick


def test_the_same_state_gives_the_same_day():
    assert run_day(staffed(1, 2)) == run_day(staffed(1, 2))


def test_a_fired_employee_earns_no_wage_and_the_other_covers_the_job():
    state = logic.open_day(staffed(1, 2))
    state = logic.fire_employee(state, 2)
    state, result = logic.skip_shift(state)
    assert result["revenue"] > 0  # the refiller sells now too
    assert result["wages"] == logic.employee_wage({"job": "refiller", "level": 1})
    state = logic.fire_employee(logic.open_day(staffed(1, 2)), 2)
    state = logic.fire_employee(state, 1)
    assert logic.skip_shift(state)[1]["revenue"] == 0  # nobody left


# --- wages: stopping and starting again ----------------------------------------

def test_without_cash_for_wages_an_employee_stops_working_but_stays_hired():
    state = staffed(1, 2, cash=100_000)
    state["cash"] = 0
    state["stock"]["coffee"] = 0
    state, result = run_day(state)
    assert state["cash"] == 0 and result["wages"] == 0
    assert result["wages_unpaid"] == [1, 2]
    assert [e["working"] for e in state["employees"]] == [False, False]
    assert len(state["employees"]) == 2 and state["shops"]["cafe"]["staff_places"] == 2


def test_only_the_first_can_be_paid_when_the_cash_covers_one_wage():
    state = staffed(1, 2, cash=100_000)
    wage = logic.employee_wage(state["employees"][0])
    state["cash"], state["stock"]["coffee"] = wage + 50, 0
    state, result = run_day(state)
    assert result["wages"] == wage and result["wages_unpaid"] == [2]
    assert [e["working"] for e in state["employees"]] == [True, False]
    assert state["cash"] == 50


def test_a_stopped_employee_does_not_work_and_costs_nothing():
    state = staffed(1, 2)
    state["employees"][1]["working"] = False
    state = logic.open_day(state)
    assert state["shift"]["shop"] == "cafe"  # the refiller still opens the shift
    state, result = logic.skip_shift(state)
    assert result["revenue"] > 0  # the refiller covers the selling
    assert result["wages"] == logic.employee_wage(state["employees"][0])
    state = staffed(1, 2)
    state["employees"][0]["working"] = state["employees"][1]["working"] = False
    assert logic.open_day(state)["shift"]["shop"] is None  # nobody works: no shift


def test_a_stopped_employee_starts_again_when_the_cash_covers_the_wage():
    state = staffed(1, 2)
    state["employees"][1]["working"] = False
    state, result = run_day(logic.set_day_override(state, "sun"))
    assert state["employees"][1]["working"] is True


def test_a_stopped_employee_stays_stopped_without_cash():
    state = staffed(1, 2, cash=100_000)
    state["employees"][1]["working"] = False
    state["cash"] = 0
    state["stock"]["coffee"] = 0
    state, _ = run_day(state)
    assert state["employees"][1]["working"] is False and state["cash"] == 0


def test_cash_never_goes_negative_over_a_whole_season():
    state = staffed(1, 2)
    state["cash"] = 5_000
    while not logic.is_finished(state):
        state, _ = run_day(state)
        assert state["cash"] >= 0


# --- unchanged behaviour -------------------------------------------------------

def test_trade_day_is_unchanged_and_pays_no_wages():
    state = staffed(1, 2)
    cash = state["cash"]
    new, result = logic.trade_day(state)
    assert "wages" not in result and new["employees"] == state["employees"]
    assert new["cash"] == cash + result["revenue"]


def test_a_shift_started_by_hand_gets_the_staff_too():
    state = logic.start_shift(staffed(1, 2), "cafe")
    assert "staffed" not in state["shift"]
    result = None
    while result is None:
        state, result = logic.tick(state)
    assert result["revenue"] > 0 and result["wages"] > 0


# --- saving ---------------------------------------------------------------------

def test_employees_survive_a_restart(tmp_path):
    path = tmp_path / "run.db"
    state = logic.upgrade_employee(staffed(1, 2), 2)
    state["employees"][0]["working"] = False
    db.save(state, path)
    assert db.load(path)["employees"] == state["employees"]


def test_a_save_from_before_staff_loads_with_no_employees(tmp_path):
    path = tmp_path / "run.db"
    db.save(logic.new_state(), path)
    import sqlite3
    with sqlite3.connect(path) as conn:
        conn.execute("DROP TABLE employees")
    assert db.load(path)["employees"] == []


def test_firing_is_saved(tmp_path):
    path = tmp_path / "run.db"
    state = staffed(1, 2)
    db.save(state, path)
    db.save(logic.fire_employee(state, 1), path)
    assert [e["id"] for e in db.load(path)["employees"]] == [2]


# --- the API ---------------------------------------------------------------------

@pytest.fixture
def client(tmp_path, monkeypatch):
    import app
    path = tmp_path / "run.db"
    state = with_places()
    db.save(state, path)
    real_save = db.save
    monkeypatch.setattr(app, "load_run", lambda: db.load(path))
    monkeypatch.setattr(app.db, "save", lambda s: real_save(s, path))
    test_client = app.app.test_client()
    test_client.path = path
    test_client.save = lambda s: real_save(s, path)
    return test_client


def test_the_api_hires_upgrades_and_fires(client):
    answer = client.post("/api/staff/hire", json={"shop": "cafe", "place": 1})
    assert answer.status_code == 200
    staff = answer.get_json()["state"]["staff"]
    assert staff["employees"][0]["name"] == "Mia" and staff["employees"][0]["wage"] == 800
    assert staff["employees"][0]["upgrade_price"] == logic.UPGRADE_PRICES[2]
    assert staff["places"][0]["employee"] == 1 and staff["places"][1]["employee"] is None
    answer = client.post("/api/staff/upgrade", json={"employee_id": 1})
    assert answer.get_json()["state"]["staff"]["employees"][0]["level"] == 2
    assert db.load(client.path)["employees"][0]["level"] == 2
    answer = client.post("/api/staff/fire", json={"employee_id": 1})
    assert answer.status_code == 200 and db.load(client.path)["employees"] == []


CRAFTED = [
    ("/api/staff/hire", {}),
    ("/api/staff/hire", {"shop": "cafe"}),
    ("/api/staff/hire", {"shop": "cafe", "place": 3}),
    ("/api/staff/hire", {"shop": "cafe", "place": "1"}),
    ("/api/staff/hire", {"shop": "cafe", "place": True}),
    ("/api/staff/hire", {"shop": "cafe", "place": 1.5}),
    ("/api/staff/hire", {"shop": "cafe", "place": -1}),
    ("/api/staff/hire", {"shop": "../etc", "place": 1}),
    ("/api/staff/hire", {"shop": ["cafe"], "place": 1}),
    ("/api/staff/hire", {"shop": "surf_shop", "place": 1}),
    ("/api/staff/upgrade", {"employee_id": 1}),
    ("/api/staff/upgrade", {"employee_id": "1"}),
    ("/api/staff/upgrade", {"employee_id": True}),
    ("/api/staff/upgrade", {"employee_id": None}),
    ("/api/staff/fire", {"employee_id": 7}),
    ("/api/staff/fire", {"employee_id": {"id": 1}}),
    ("/api/staff/fire", {}),
]


@pytest.mark.parametrize("url,body", CRAFTED)
def test_crafted_requests_are_refused_and_the_saved_run_stays_identical(client, url, body):
    before = db.load(client.path)
    answer = client.post(url, json=body)
    assert answer.status_code == 400
    assert "Traceback" not in answer.get_data(as_text=True)
    assert db.load(client.path) == before


def test_a_request_that_is_not_json_is_refused_and_changes_nothing(client):
    before = db.load(client.path)
    for url in ("/api/staff/hire", "/api/staff/upgrade", "/api/staff/fire"):
        assert client.post(url, data="not json", content_type="text/plain").status_code == 400
    assert db.load(client.path) == before


def test_a_crafted_request_cannot_hire_without_cash_or_above_the_bought_places(client):
    state = db.load(client.path)
    state["cash"] = logic.HIRE_PRICE - 1
    client.save(state)
    assert client.post("/api/staff/hire", json={"shop": "cafe", "place": 1}).status_code == 400
    state["cash"], state["shops"]["cafe"]["staff_places"] = 100_000, 1
    client.save(state)
    assert client.post("/api/staff/hire", json={"shop": "cafe", "place": 2}).status_code == 400
    assert db.load(client.path)["employees"] == []


def test_a_staffed_day_through_the_api_pays_the_wages(client):
    state = db.load(client.path)
    state["stock"]["coffee"] = 100
    client.save(state)
    client.post("/api/staff/hire", json={"shop": "cafe", "place": 1})
    client.post("/api/staff/hire", json={"shop": "cafe", "place": 2})
    shown = client.get("/api/state").get_json()
    assert shown["staff"]["wages_today"] == 1_600 and shown["shift"] is None
    opened = client.post("/api/day/open").get_json()["state"]
    assert opened["shift"]["shop"] == "cafe" and opened["shift"]["staffed"] is True
    assert client.post("/api/shift/start", json={"shop": "cafe"}).status_code == 400
    assert client.post("/api/shift/skip").status_code == 200
    saved = db.load(client.path)
    assert saved["day"] == 2 and saved["history"][-1]["wages"] == 1_600
    assert saved["history"][-1]["revenue"] > 0


# --- buying the place hires, and one employee covers the other job -------------------

def test_buying_a_place_hires_its_employee_without_a_second_fee():
    state = logic.new_state()
    state["cash"] = 20_000
    one = logic.buy_upgrade(state, "cafe", "staff_1")
    assert one["cash"] == 20_000 - 6_000  # the place price only, no hire fee
    assert one["employees"] == [{"id": 1, "name": "Mia", "shop": "cafe", "place": 1,
                                 "job": "refiller", "level": 1, "working": True}]
    two = logic.buy_upgrade(one, "cafe", "staff_2")
    assert [e["job"] for e in two["employees"]] == ["refiller", "seller"]
    assert two["shops"]["cafe"]["staff_places"] == 2 and two["shops"]["cafe"]["level"] == 3


def test_a_place_in_a_shop_without_staff_work_hires_nobody():
    state = logic.new_state()
    state["cash"] = 100_000
    state["shops"]["beach_cafe"] = logic.new_shop("cafe")
    state = logic.buy_upgrade(state, "beach_cafe", "staff_1")
    assert state["employees"] == [] and state["shops"]["beach_cafe"]["staff_places"] == 1


def test_a_dismissed_place_is_hired_again_for_the_hire_price():
    state = logic.new_state()
    state["cash"] = 20_000
    state = logic.fire_employee(logic.buy_upgrade(state, "cafe", "staff_1"), 1)
    cash = state["cash"]
    state = logic.hire(state, "cafe", 1)
    assert state["cash"] == cash - logic.HIRE_PRICE and len(state["employees"]) == 1


def test_a_lone_seller_refills_the_counter_himself():
    state = logic.open_day(staffed(2))
    for _ in range(3):
        state, _ = logic.tick(state)
    assert state["shift"]["counter"]["coffee"] == 3  # one unit per tick at level 1


def test_a_covering_employee_works_at_his_own_level():
    state = staffed(2)
    top = logic.upgrade_employee(logic.upgrade_employee(state, 1), 1)
    carried = []
    for start in (state, top):
        run = logic.open_day(start)
        before = run["stock"]["coffee"]
        for _ in range(2):
            run, _ = logic.tick(run)
        carried.append(before - run["stock"]["coffee"])
    assert carried == [2, 6]  # level 1 carries 1 a tick, level 3 carries 3 a tick


def test_with_two_employees_each_keeps_his_own_job():
    state = logic.open_day(staffed(1, 2))
    state, _ = logic.tick(state)
    assert state["shift"]["counter"]["coffee"] == 1  # only the refiller carried


# --- review fixes -----------------------------------------------------------------------

def test_a_refiller_does_not_carry_a_product_nobody_wants_at_its_price():
    state = with_places()
    state["shops"]["cafe"]["products"] = ["coffee", "cake", "bagel"]
    state["stock"].update(cake=50, bagel=50)
    state["prices"]["bagel"] = 3 * logic.CATALOGUE["bagel"]["ref_price"]  # demand 0
    state = logic.open_day(logic.hire(logic.hire(state, "cafe", 1), "cafe", 2))
    for _ in range(10):
        state, _ = logic.tick(state)
    counter = state["shift"]["counter"]
    assert counter["bagel"] == 0 and counter["coffee"] + counter["cake"] > 0
    assert state["stock"]["bagel"] == 50


def test_the_id_counter_and_a_bad_level_in_a_save(tmp_path):
    path = tmp_path / "run.db"
    state = logic.fire_employee(staffed(1, 2), 2)
    db.save(state, path)
    assert db.load(path)["employee_seq"] == 2
    import sqlite3
    with sqlite3.connect(path) as conn:  # a hand-edited save with a level that does not exist
        conn.execute("UPDATE employees SET level = 4 WHERE id = 1")
    assert db.load(path)["employees"] == []  # skipped, nothing crashes
    with sqlite3.connect(path) as conn:
        conn.execute("UPDATE employees SET level = 1 WHERE id = 1")
        conn.execute("UPDATE employees SET place = 9 WHERE id = 1")
    assert db.load(path)["employees"] == []
