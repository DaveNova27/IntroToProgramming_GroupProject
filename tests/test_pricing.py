"""Checks from specs/pricing.md ("Done when"). One test per check.

Part 1 (no weather yet): the segments, the shop mix, the curves, the cap, the factor slots,
the explanation and the preview endpoint."""

import copy
import json

import pytest

import app
import db
import logic

SEED = 424242
PRODUCT_SHOP = {pid: sid for sid in logic.SHOPS for pid in logic.shop_product_ids(sid)}

# The spec's table "what a shop sells at each price", in hundredths of a customer, at
# 50, 75, 100, 125, 150, 175, 200, 225 and 250 % of the reference price (neutral day).
SHOP_CURVES = {
    "cafe": [1590, 1294, 1000, 710, 394, 204, 100, 40, 0],
    "beach_cafe": [1480, 1238, 1000, 770, 508, 328, 200, 80, 0],
    "merchandise": [1425, 1210, 1000, 800, 565, 390, 250, 100, 0],
    "surf_shop": [1315, 1154, 1000, 860, 679, 514, 350, 140, 0],
}
POINTS = [50, 75, 100, 125, 150, 175, 200, 225, 250]


def rich(cash=10_000_000):
    state = logic.new_state(SEED)
    state["cash"] = cash
    for sid, shop in logic.SHOPS.items():
        if not state["shops"][sid]["unlocked"]:
            state = logic.unlock_shop(state, sid)
        for item, offer in shop["window"].items():
            if offer["kind"] == "product":
                state = logic.buy_upgrade(state, sid, item)
    return state


def refused(action, state):
    before = copy.deepcopy(state)
    with pytest.raises(logic.RejectedAction):
        action(state)
    assert state == before


def all_ints(value):
    """True if there is no float anywhere in a nested answer."""
    if isinstance(value, float):
        return False
    if isinstance(value, dict):
        return all(all_ints(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return all(all_ints(v) for v in value)
    return True


@pytest.fixture
def run_on_disk(tmp_path, monkeypatch):
    """The real API on a temporary save, so the player's own run stays untouched."""
    path = tmp_path / "run.db"
    db.save(logic.new_state(SEED), path)
    real_save = db.save
    monkeypatch.setattr(app, "load_run", lambda: db.load(path))
    monkeypatch.setattr(app.db, "save", lambda state: real_save(state, path))
    return path


# ---- Check 1: the curves and the function ------------------------------------

@pytest.mark.parametrize("shop", list(SHOP_CURVES))
def test_the_curve_of_every_shop_follows_the_table(shop):
    mix = logic.SHOP_MIX[shop]
    got = [logic._round_half_up(sum(logic.segment_amounts(x, 100, mix).values()) * 100) for x in POINTS]
    assert got == SHOP_CURVES[shop]
    assert logic.shop_price_curve(shop) == [[x, v] for x, v in zip(POINTS, SHOP_CURVES[shop])]


def test_between_the_points_it_is_a_straight_line_and_below_the_first_it_is_flat():
    mix = {"students": 1, "visitors": 0}
    amount = lambda pct: logic.segment_amounts(pct, 100, mix)["students"]
    assert amount(25) == amount(50) == logic.Fraction(17, 10)
    assert amount(60) == logic.Fraction(17, 10) + (logic.Fraction(135, 100) - logic.Fraction(17, 10)) * 10 / 25
    assert amount(200) == amount(1000) == 0


def test_customers_for_is_a_whole_number_rounded_half_up_and_capped():
    only_visitors = {"visitors": 1}
    assert logic.customers_for(200, 100, only_visitors) == 1  # 0.5 rounds up
    assert logic.customers_for(201, 100, only_visitors) == 0  # just below 0.5
    assert logic.customers_for(1, 100, {"students": 1000}) == logic.MAX_CUSTOMERS
    for shop, mix in logic.SHOP_MIX.items():
        for pct in range(1, 400):
            n = logic.customers_for(pct, 100, mix)
            assert type(n) is int and 0 <= n <= logic.MAX_CUSTOMERS


def test_a_call_with_two_arguments_still_works_with_the_neutral_mix():
    assert logic.customers_for(200, 200) == 10  # pinned by tests/test_shop_process.py
    assert sum(logic.DEFAULT_MIX.values()) == logic.BASE_CUSTOMERS


def test_bad_arguments_are_programming_errors_not_customers():
    with pytest.raises(ValueError):
        logic.customers_for(0, 200)
    with pytest.raises(ValueError):
        logic.customers_for(200, 0)
    with pytest.raises(ValueError):
        logic.customers_for(200, 200, percents={"students": -1})


# ---- Check 2: the shops --------------------------------------------------------

def test_every_shop_has_a_mix_that_adds_up_to_ten_and_sells_ten_at_the_reference_price():
    assert set(logic.SHOP_MIX) == set(logic.SHOPS)
    for shop, mix in logic.SHOP_MIX.items():
        assert sum(mix.values()) == logic.BASE_CUSTOMERS and set(mix) == set(logic.SEGMENTS)
        for pid in logic.shop_product_ids(shop):
            ref = logic.CATALOGUE[pid]["ref_price"]
            assert logic.customers_for(ref, ref, mix) == 10


def test_a_higher_price_never_sells_more_and_nobody_buys_at_250_percent():
    for pid, item in logic.CATALOGUE.items():
        ref, mix = item["ref_price"], logic.SHOP_MIX[PRODUCT_SHOP[pid]]
        previous = None
        for price in range(1, 3 * ref + 1):  # every cent up to three times the reference price
            n = logic.customers_for(price, ref, mix)
            assert previous is None or n <= previous, (pid, price)
            previous = n
            if price * 100 >= 250 * ref:
                assert n == 0, (pid, price)


def test_a_cake_at_225_percent_sells_nothing_in_the_cafe():
    assert logic.customers_for(900, 400, logic.SHOP_MIX["cafe"]) == 0


def test_the_shops_have_their_own_character():
    """The Cafe is a volume shop, the surf shop sells to visitors who hardly mind the price."""
    cafe, surf = logic.SHOP_MIX["cafe"], logic.SHOP_MIX["surf_shop"]
    assert logic.customers_for(300, 200, cafe) < logic.customers_for(300, 200, surf)
    assert logic.customers_for(100, 200, cafe) > logic.customers_for(100, 200, surf)


# ---- Check 3: the factor slots -------------------------------------------------

def test_the_percents_multiply_and_the_order_does_not_matter():
    mix = logic.SHOP_MIX["cafe"]
    base = logic.segment_amounts(250, 200, mix)
    both = logic.segment_amounts(250, 200, mix, {"students": 150, "visitors": 70})
    assert both["students"] == base["students"] * logic.Fraction(3, 2)
    assert both["visitors"] == base["visitors"] * logic.Fraction(7, 10)
    a = logic._combine({s: logic.Fraction(100) for s in mix}, {"students": 150})
    a = logic._combine(a, {"students": 50, "visitors": 120})
    b = logic._combine({s: logic.Fraction(100) for s in mix}, {"students": 50, "visitors": 120})
    b = logic._combine(b, {"students": 150})
    assert a == b == {"students": logic.Fraction(75), "visitors": logic.Fraction(120)}


def test_a_percent_of_zero_gives_zero_a_named_segment_leaves_the_other_and_unknown_is_ignored():
    mix = logic.SHOP_MIX["cafe"]
    assert logic.customers_for(200, 200, mix, {"students": 0, "visitors": 0}) == 0
    base = logic.segment_amounts(200, 200, mix)
    one = logic.segment_amounts(200, 200, mix, {"students": 0})
    assert one["students"] == 0 and one["visitors"] == base["visitors"]
    assert logic.customers_for(200, 200, mix, {"dragons": 900}) == logic.customers_for(200, 200, mix)


def test_a_registered_factor_is_used_everywhere_and_a_factor_at_100_percent_has_no_line(monkeypatch):
    def party(state, shop):
        return "Event: Party", {"students": 150, "visitors": 150}

    def quiet(state, shop):
        return "Event: Nothing", {"students": 100}

    monkeypatch.setattr(logic, "FACTORS", (party, quiet))
    state = logic.buy(logic.new_state(SEED), "coffee", 40)
    assert logic.customers_today(state, "coffee") == 15  # 10 x 1.5
    lines = logic.customer_breakdown(state, "coffee")["steps"]
    assert [s["name"] for s in lines] == [lines[0]["name"], "Event: Party"]
    assert lines[-1]["customers"] == 15


# ---- Check 4: one number in four places ----------------------------------------

@pytest.mark.parametrize("shop", list(logic.SHOPS))
def test_the_shift_the_day_the_overview_and_the_screen_agree(shop, monkeypatch):
    monkeypatch.setattr(logic, "SHIFT_SHOPS", tuple(logic.SHOPS))
    state = rich()
    for i, pid in enumerate(logic.shop_product_ids(shop)):
        ref = logic.CATALOGUE[pid]["ref_price"]
        state["prices"][pid] = ref * (100 + 25 * i) // 100  # 100 %, 125 %, 150 %
        state["stock"][pid] = 30
    expected = {pid: logic.customers_today(state, pid) for pid in logic.shop_product_ids(shop)}

    shift = logic.start_shift(state, shop)["shift"]
    assert {pid: shift["planned"][pid] for pid in expected} == expected
    assert {pid: sum(c["product"] == pid for c in shift["queue"]) for pid in expected} == expected

    lines = {l["product"]: l["demand"] for l in logic.trade_day(state)[1]["lines"]}
    assert {pid: lines[pid] for pid in expected} == expected

    overview = {l["product"]: l["sells_today"] for l in logic.stock_overview(state)["lines"]}
    assert {pid: overview[pid] for pid in expected} == {pid: min(n, 30) for pid, n in expected.items()}

    shown = {p["id"]: p["customers"] for p in app.view(state)["products"]}
    assert {pid: shown[pid] for pid in expected} == expected


# ---- Check 5: the balance guard ----------------------------------------------------

BANDS = {"cafe": (105, 125), "beach_cafe": (115, 135), "merchandise": (120, 140), "surf_shop": (130, 160)}


def test_the_best_price_of_every_product_sits_in_its_shops_band_and_is_never_the_cost():
    for pid, item in logic.CATALOGUE.items():
        shop, ref, cost = PRODUCT_SHOP[pid], item["ref_price"], item["cost"]
        mix = logic.SHOP_MIX[shop]
        step = max(1, ref // 100)
        best = max(range(1, 3 * ref, step), key=lambda p: (logic.customers_for(p, ref, mix) * (p - cost), -p))
        low, high = BANDS[shop]
        assert low <= best * 100 // ref <= high, (pid, best * 100 / ref)
        assert best > cost


# ---- Check 6: the explanation ------------------------------------------------------

def test_the_last_line_is_the_real_number_and_the_split_adds_up():
    state = rich()
    for pid in logic.CATALOGUE:
        for percent in (50, 80, 100, 125, 160, 190, 240):
            price = max(1, logic.CATALOGUE[pid]["ref_price"] * percent // 100)
            b = logic.customer_breakdown(state, pid, price)
            state2 = logic.set_price(state, pid, price)
            assert b["customers"] == logic.customers_today(state2, pid)
            assert b["steps"][-1]["customers"] == b["customers"] == sum(b["split"].values())
            assert all(sum(s["split"].values()) == s["customers"] for s in b["steps"])
            assert b["base"] == 10 and set(b["keep"]) == set(logic.SEGMENTS)
            assert all_ints(b)


def test_the_explanation_of_a_known_price():
    state = logic.buy(logic.set_day_override(logic.new_state(SEED), "storm"), "coffee", 12)  # normal day
    b = logic.customer_breakdown(state, "coffee", 250)  # 125 % in the Cafe
    assert b["price_percent"] == 125 and b["base"] == 10
    assert [(s["id"], s["customers"], s["split"]) for s in b["steps"]] == [
        ("price", 7, {"students": 5, "visitors": 2})]
    assert b["keep"] == {"students": 65, "visitors": 95}
    assert b["customers"] == 7 and b["split"] == {"students": 5, "visitors": 2}
    assert (b["unit_profit"], b["sellable"], b["expected_profit"]) == (170, 7, 7 * 170)


def test_the_stock_limits_the_expected_profit():
    state = logic.buy(logic.set_day_override(logic.new_state(SEED), "storm"), "coffee", 3)  # normal day
    b = logic.customer_breakdown(state, "coffee", 250)
    assert b["customers"] == 7 and b["sellable"] == 3 and b["expected_profit"] == 3 * 170


def test_the_cap_is_a_visible_step(monkeypatch):
    monkeypatch.setattr(logic, "FACTORS", (lambda state, shop: ("Event: Crowd", {"students": 900}),))
    b = logic.customer_breakdown(logic.new_state(SEED), "coffee")
    assert b["customers"] == logic.MAX_CUSTOMERS
    assert b["steps"][-1]["id"] == "cap" and sum(b["split"].values()) == logic.MAX_CUSTOMERS


def test_the_explanation_changes_nothing_and_is_the_same_every_time():
    state = rich()
    before = copy.deepcopy(state)
    first = logic.customer_breakdown(state, "wetsuit", 7000)
    assert logic.customer_breakdown(state, "wetsuit", 7000) == first
    assert logic.price_preview(state, "wetsuit", 7000) == first
    assert state == before


# ---- Check 7: the live preview ---------------------------------------------------------

@pytest.mark.parametrize("price", [0, -5, True, 1.5, "200", None, logic.MAX_PRICE + 1])
def test_a_bad_price_is_refused_by_the_rule(price):
    refused(lambda s: logic.price_preview(s, "coffee", price), logic.new_state(SEED))


@pytest.mark.parametrize("product", ["surfboard", "dragon", "", None, 5, ["coffee"]])
def test_an_unknown_or_not_yet_owned_product_is_refused(product):
    refused(lambda s: logic.price_preview(s, product, 200), logic.new_state(SEED))


def test_the_preview_is_refused_after_the_last_day():
    state = logic.new_state(SEED)
    state["day"] = logic.LAST_DAY + 1
    refused(lambda s: logic.price_preview(s, "coffee", 200), state)


def test_the_endpoint_answers_and_saves_nothing(run_on_disk):
    before = db.load(run_on_disk)
    client = app.app.test_client()
    response = client.post("/api/price_preview", json={"product": "coffee", "price": "2,50"})
    assert response.status_code == 200
    preview = response.get_json()["preview"]
    assert preview == json.loads(json.dumps(logic.customer_breakdown(before, "coffee", 250)))
    assert db.load(run_on_disk) == before


@pytest.mark.parametrize("body", [
    {"product": "coffee", "price": "abc"},
    {"product": "coffee", "price": "NaN"},
    {"product": "coffee", "price": "-Infinity"},
    {"product": "coffee", "price": "0"},
    {"product": "coffee", "price": "2.505"},
    {"product": "coffee", "price": "1e999999"},
    {"product": "coffee", "price": ["2"]},
    {"product": "coffee"},
    {"product": "surfboard", "price": "90"},
    {"product": "dragon", "price": "2"},
    {"price": "2"},
    {},
])
def test_the_endpoint_refuses_bad_input_and_saves_nothing(run_on_disk, body):
    before = db.load(run_on_disk)
    response = app.app.test_client().post("/api/price_preview", json=body)
    assert response.status_code == 400 and response.get_json()["error"]
    assert db.load(run_on_disk) == before


def test_the_endpoint_refuses_anything_that_is_not_a_json_object(run_on_disk):
    before = db.load(run_on_disk)
    client = app.app.test_client()
    for raw in ("[1, 2]", "null", "not json", ""):
        response = client.post("/api/price_preview", data=raw, content_type="application/json")
        assert response.status_code == 400
    assert db.load(run_on_disk) == before


# ---- Check 8: the screen's data ----------------------------------------------------------

def test_the_state_answer_carries_the_new_numbers_and_no_old_demand_levels(run_on_disk):
    state = app.app.test_client().get("/api/state").get_json()
    assert "demand_levels" not in state
    assert state["base_customers"] == 10
    assert [s["id"] for s in state["segments"]] == list(logic.SEGMENTS)
    assert set(state["price_curves"]) == set(logic.SHOPS)
    for product in state["products"]:
        assert "demand" not in product
        assert product["shop"] == PRODUCT_SHOP[product["id"]]
        assert product["customers"] == product["breakdown"]["customers"]
    assert all_ints(state["price_curves"]) and all_ints(state["products"])


def test_after_the_last_day_nothing_is_promised(run_on_disk):
    state = logic.new_state(SEED)
    state["day"] = logic.LAST_DAY + 1
    shown = app.view(state)
    assert all(p["customers"] == 0 and p["breakdown"] is None for p in shown["products"])


def test_no_state_was_added_and_old_saves_still_load(tmp_path):
    path = tmp_path / "run.db"
    state = logic.new_state(SEED)
    db.save(state, path)
    assert db.load(path) == state
    assert "customers" not in state and "mix" not in state


def test_the_old_demand_rule_is_still_there_but_the_game_does_not_use_it():
    assert logic.demand(400, 400) == 10 and logic.demand(800, 400) == 5 and logic.demand(801, 400) == 0
    state = logic.buy(logic.new_state(SEED), "coffee", 12)
    state = logic.set_price(state, "coffee", 400)  # 200 %: the old rule said 5, the new one 1
    assert logic.demand(400, 200) == 5 and logic.customers_today(state, "coffee") == 1


# ==== Part 2: the weather ===================================================

def on_a_day_with(weather, state=None):
    return logic.set_day_override(state or logic.new_state(SEED), weather)


# Customers of the first product of each shop at the reference price (neutral price, one day).
WEATHER_CUSTOMERS = {
    "cafe": {"sun": 8, "rain": 13, "heat": 6, "storm": 10},
    "merchandise": {"sun": 12, "rain": 10, "heat": 9, "storm": 10},
    "beach_cafe": {"sun": 17, "rain": 4, "heat": 19, "storm": 2},
    "surf_shop": {"sun": 16, "rain": 4, "heat": 14, "storm": 2},
}


@pytest.mark.parametrize("shop", list(logic.SHOPS))
@pytest.mark.parametrize("weather", list(logic.WEATHER))
def test_the_weather_decides_how_many_customers_come(shop, weather):
    state = rich()
    pid = logic.shop_product_ids(shop)[0]
    state = on_a_day_with(weather, state)
    assert logic.customers_today(state, pid) == WEATHER_CUSTOMERS[shop][weather]


@pytest.mark.parametrize("shop", list(logic.SHOPS))
@pytest.mark.parametrize("weather", list(logic.WEATHER))
def test_the_percents_are_the_shop_table_and_the_visitor_extra(shop, weather):
    state = on_a_day_with(weather)
    table = logic.WEATHER[weather]["demand_percent"][shop]
    got = logic.segment_percents(state, shop)
    assert got["students"] == table
    assert got["visitors"] == logic.Fraction(table * logic.VISITOR_WEATHER[weather], 100)


def test_the_percents_are_exact_fractions_never_cut_off():
    state = on_a_day_with("rain")  # cafe 140 x visitors 70 % = 98
    assert logic.segment_percents(state, "cafe")["visitors"] == logic.Fraction(98)
    state = on_a_day_with("sun")  # beach cafe 150 x 130 % = 195
    assert logic.segment_percents(state, "beach_cafe")["visitors"] == logic.Fraction(195)


def test_the_weather_table_is_still_the_one_source():
    """The outlook reads this table too: its numbers are not copied or changed here."""
    assert logic.WEATHER["heat"]["demand_percent"] == {
        "cafe": 60, "surf_shop": 120, "merchandise": 80, "beach_cafe": 180}
    assert logic.WEATHER["storm"]["demand_percent"]["cafe"] == 100
    assert logic.VISITOR_WEATHER["storm"] == 100  # a storm is 100 % for both kinds of customers
    assert logic.FACTORS[0] is logic._weather_factor  # the weather stays the first factor


def test_the_override_changes_the_customers_and_clearing_it_brings_the_roll_back():
    state = logic.buy(logic.new_state(SEED), "coffee", 30)
    rolled = logic.customers_today(state, "coffee")
    other = next(w for w in logic.WEATHER if WEATHER_CUSTOMERS["cafe"][w] != rolled)
    fixed = logic.set_day_override(state, other)
    assert logic.customers_today(fixed, "coffee") == WEATHER_CUSTOMERS["cafe"][other]
    assert logic.customers_today(logic.set_day_override(fixed, None), "coffee") == rolled


def test_the_shift_and_the_day_without_a_player_see_the_same_weather():
    state = logic.buy(on_a_day_with("heat"), "coffee", 30)
    assert logic.start_shift(state, "cafe")["shift"]["planned"] == {"coffee": 6}
    assert logic.trade_day(state)[1]["lines"][0]["demand"] == 6
    assert logic.stock_overview(state)["lines"][0]["sells_today"] == 6
    assert app.view(state)["forecast"]["lines"][0]["demand"] == 6
    assert app.view(state)["products"][0]["customers"] == 6


def test_the_weather_shows_as_a_line_of_the_explanation_with_its_name():
    state = logic.buy(on_a_day_with("heat"), "coffee", 12)
    b = logic.customer_breakdown(state, "coffee", 250)
    assert [(s["id"], s["name"], s["customers"]) for s in b["steps"]] == [
        ("price", "Your price (125 % of the reference price)", 7),
        ("factor", "Weather: Hot", 4)]
    assert b["customers"] == 4 and b["split"] == {"students": 3, "visitors": 1}
    assert b["expected_profit"] == 4 * 170


def test_a_weather_at_100_percent_has_no_line():
    state = logic.buy(on_a_day_with("storm"), "coffee", 12)  # Cafe: storm is 100 % for both
    assert [s["id"] for s in logic.customer_breakdown(state, "coffee")["steps"]] == ["price"]
    surf = logic.buy(on_a_day_with("storm", rich()), "surfboard", 1)  # 20 % there
    assert [s["id"] for s in logic.customer_breakdown(surf, "surfboard")["steps"]] == ["price", "factor"]


def test_the_preview_uses_todays_weather_too():
    state = logic.buy(on_a_day_with("rain"), "coffee", 30)
    assert logic.price_preview(state, "coffee", 200)["customers"] == 13
    assert logic.price_preview(state, "coffee", 200)["steps"][-1]["name"] == "Weather: Rainy"


def exact_best_price(state, pid, shop):
    """The price with the highest profit, on exact values (before the customers are rounded)."""
    item = logic.CATALOGUE[pid]
    ref, cost = item["ref_price"], item["cost"]
    percents = logic.segment_percents(state, shop)
    return max(range(cost + 1, 3 * ref, max(1, ref // 200)),
               key=lambda p: (sum(logic.segment_amounts(p, ref, logic.SHOP_MIX[shop], percents).values()) * (p - cost), -p))


def test_the_weather_moves_who_comes_and_so_the_best_price_of_a_visitor_shop():
    """Sun brings visitors who mind the price less: the surf shop can charge more than in rain."""
    surf_sun = exact_best_price(on_a_day_with("sun", rich()), "surfboard", "surf_shop")
    surf_rain = exact_best_price(on_a_day_with("rain", rich()), "surfboard", "surf_shop")
    assert surf_sun - surf_rain >= 0.08 * logic.CATALOGUE["surfboard"]["ref_price"]
    cafe_sun = exact_best_price(on_a_day_with("sun", rich()), "coffee", "cafe")
    cafe_rain = exact_best_price(on_a_day_with("rain", rich()), "coffee", "cafe")
    assert cafe_sun - cafe_rain <= 0.08 * logic.CATALOGUE["coffee"]["ref_price"]  # hardly moves


def test_the_largest_crowd_stays_under_the_cap_with_the_weather_alone():
    top = 0
    for weather in logic.WEATHER:
        state = on_a_day_with(weather, rich())
        for pid, item in logic.CATALOGUE.items():
            ref, mix = item["ref_price"], logic.SHOP_MIX[PRODUCT_SHOP[pid]]
            percents = logic.segment_percents(state, PRODUCT_SHOP[pid])
            top = max(top, max(logic.customers_for(p, ref, mix, percents)
                               for p in range(1, 2 * ref, max(1, ref // 50))))
    assert top == 28 < logic.MAX_CUSTOMERS


def test_the_weather_adds_no_state_and_a_save_round_trips():
    state = on_a_day_with("heat", logic.buy(logic.new_state(SEED), "coffee", 5))
    assert set(state) == set(logic.new_state(SEED))
    assert all_ints(logic.customer_breakdown(state, "coffee"))
