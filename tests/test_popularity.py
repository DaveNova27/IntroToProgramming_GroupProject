"""Popularity of the shops (specs/popularity.md, issue #13)."""

import copy
import json
import sqlite3
from fractions import Fraction
from pathlib import Path

import pytest

import app
import db
import logic

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"


def line(product, price, demand, sold):
    return {"product": product, "price": price, "demand": demand, "sold": sold}


def play_whole_days(share, price_percent, days=logic.LAST_DAY, seed=1):
    """The Cafe only, the same every day: coffee at a percent of the reference price and stock for
    `share` of the day's customers. Returns the popularity of the Cafe after every day."""
    state, out = logic.new_state(seed), []
    ref = logic.CATALOGUE["coffee"]["ref_price"]
    while not logic.is_finished(state):
        state["prices"]["coffee"] = ref * price_percent // 100
        state["stock"]["coffee"] = int(logic.customers_today(state, "coffee") * share)
        state, _ = logic.trade_day(state)
        out.append(state["popularity"]["cafe"])
    assert len(out) == days
    return out


def play_cafe_shift(state):
    """A played day in the Cafe: every customer is served at once. Returns (state, result)."""
    state = logic.open_day(state)
    if state["shift"]["shop"] is None:
        state = logic.start_shift(state, "cafe")
    result = None
    while result is None:
        shift = state["shift"]
        if not shift["over"]:
            for pid in shift["counter"]:
                shift = state["shift"]
                waiting = sum(1 for c in shift["queue"] if c["product"] == pid)
                space = logic.SHOPS["cafe"]["counter"] - sum(shift["counter"].values())
                need = min(waiting - shift["counter"][pid], state["stock"][pid], space)
                if need > 0:
                    state = logic.refill(state, pid, need)
                while True:
                    try:
                        state = logic.sell(state, pid)
                    except logic.RejectedAction:
                        break
            state, result = logic.tick(state)
        else:
            state, result = logic.skip_shift(state)
    return state, result


# --- the start and the save ---------------------------------------------------------------

def test_a_new_run_starts_every_shop_at_the_normal_value():
    state = logic.new_state(3)
    assert state["popularity"] == {sid: 50 for sid in logic.SHOPS}
    assert logic.POPULARITY_START == 50


def test_a_state_without_the_entry_counts_as_normal():
    state = logic.new_state(3)
    del state["popularity"]
    assert all(logic.popularity_of(state, sid) == 50 for sid in logic.SHOPS)
    assert logic.popularity_of({}, "cafe") == 50


def test_a_saved_value_comes_back_from_the_database(tmp_path):
    path = tmp_path / "run.db"
    state = logic.new_state(3)
    state["popularity"] = {"cafe": 81, "beach_cafe": 0, "merchandise": 100, "surf_shop": 33}
    db.save(state, path)
    assert db.load(path)["popularity"] == state["popularity"]


def test_a_save_from_before_popularity_loads_with_the_normal_value(tmp_path):
    path = tmp_path / "run.db"
    db.save(logic.new_state(3), path)
    conn = sqlite3.connect(path)
    conn.execute("DELETE FROM meta WHERE key = 'popularity'")
    conn.commit()
    conn.close()
    assert db.load(path)["popularity"] == {sid: 50 for sid in logic.SHOPS}


@pytest.mark.parametrize("raw", ['"cafe"', "[1, 2]", "null", '{"cafe": 101, "surf_shop": -1}',
                                 '{"cafe": true, "surf_shop": 5.5, "merchandise": "9"}', "not json"])
def test_a_damaged_saved_value_falls_back_to_the_normal_value(tmp_path, raw):
    path = tmp_path / "run.db"
    db.save(logic.new_state(3), path)
    conn = sqlite3.connect(path)
    conn.execute("UPDATE meta SET value = ? WHERE key = 'popularity'", (raw,))
    conn.commit()
    conn.close()
    assert db.load(path)["popularity"] == {sid: 50 for sid in logic.SHOPS}


def test_a_new_run_resets_the_popularity(tmp_path):
    path = tmp_path / "run.db"
    state = logic.new_state(3)
    state["popularity"]["cafe"] = 90
    db.save(state, path)
    db.save_new_run(logic.new_state(4), path)
    assert db.load(path)["popularity"]["cafe"] == 50


# --- fairness, report card and walk -------------------------------------------------------------

@pytest.mark.parametrize("price, expected", [
    (1, 100), (199, 100), (200, 100),  # the reference price or less
    (201, 100),                         # 100.5 % is rounded down to 100 %
    (220, 80), (250, 50), (260, 40), (299, 2), (300, 0), (301, 0), (10_000, 0),
])
def test_fairness_at_the_edges(price, expected):
    assert logic.fairness(price, 200) == expected


def test_fairness_never_leaves_its_range():
    for ref in (150, 200, 1_450):
        for price in range(1, 4 * ref, 7):
            assert 0 <= logic.fairness(price, ref) <= 100


def test_the_report_card_of_the_worked_example_is_69():
    lines = [line("coffee", 220, 10, 10), line("cake", 400, 6, 3)]
    assert logic.day_score(lines) == 69  # (10*80 + 3*100 + 8) // 16


def test_everyone_served_at_the_reference_price_is_100_and_nobody_served_is_0():
    assert logic.day_score([line("coffee", 200, 10, 10), line("cake", 400, 6, 6)]) == 100
    assert logic.day_score([line("coffee", 200, 10, 0), line("cake", 400, 6, 0)]) == 0


def test_the_report_card_weighs_by_customers_not_by_product():
    # 30 customers served at a fair price against 1 served at a rip-off: the 30 decide
    lines = [line("coffee", 200, 30, 30), line("cake", 1_000, 1, 1)]
    assert logic.day_score(lines) == (30 * 100 + 0 + 15) // 31
    assert logic.day_score(lines) > 90


def test_no_customers_means_no_report_card():
    assert logic.day_score([]) is None
    assert logic.day_score([line("coffee", 200, 0, 0)]) is None


def test_the_report_card_stays_between_0_and_100():
    for demand in range(0, 31, 3):
        for sold in range(0, demand + 1, 2):
            for price in (1, 150, 200, 260, 400, 5_000):
                score = logic.day_score([line("coffee", price, demand, sold)])
                assert score is None or 0 <= score <= 100


def test_the_walk_of_the_worked_example():
    assert logic.walk(50, 69) == 54  # ceil(19 / 5) up
    assert logic.walk(54, 20) == 42  # ceil(34 / 3) down


def test_the_walk_arrives_and_never_passes_the_score():
    for popularity in range(0, 101):
        for score in range(0, 101):
            after = logic.walk(popularity, score)
            assert min(popularity, score) <= after <= max(popularity, score)
            gap = score - popularity
            if gap > 0:
                assert after - popularity == -(-gap // 5)  # a fifth, rounded up
            elif gap < 0:
                assert popularity - after == -(-(-gap) // 3)  # a third, rounded up
            else:
                assert after == popularity
            assert 0 <= after <= 100


def test_bad_news_travels_faster_than_good_news():
    assert 50 - logic.walk(50, 20) > logic.walk(50, 80) - 50


# --- booking a day ------------------------------------------------------------------------------

def test_a_day_with_everything_sold_at_the_reference_price_raises_the_popularity():
    state = logic.new_state(1)
    state["stock"]["coffee"] = 30
    new, _ = logic.trade_day(state)
    assert new["popularity"]["cafe"] > 50


def test_a_day_with_an_empty_shelf_lowers_it():
    new, result = logic.trade_day(logic.new_state(1))
    assert result["lines"][0]["demand"] > 0 and result["lines"][0]["sold"] == 0
    assert new["popularity"]["cafe"] < 50


def test_a_shop_without_customers_keeps_its_number_and_so_does_a_shop_that_was_closed():
    state = logic.new_state(1)
    state["popularity"] = {"cafe": 70, "beach_cafe": 33, "merchandise": 61, "surf_shop": 8}
    state["prices"]["coffee"] = 10 * logic.CATALOGUE["coffee"]["ref_price"]  # nobody buys at that price
    state["stock"]["coffee"] = 30
    new, result = logic.trade_day(state)
    assert result["lines"][0]["demand"] == 0
    assert new["popularity"] == state["popularity"]


def test_the_result_of_the_day_is_not_changed_by_popularity():
    state = logic.new_state(1)
    state["stock"]["coffee"] = 5
    _, result = logic.trade_day(state)
    assert not any("popular" in key for key in result)
    assert set(result["lines"][0]) == {"product", "price", "demand", "sold", "revenue", "cogs", "gross_profit"}


def test_the_update_works_on_a_state_without_the_entry_and_keeps_the_range():
    state = logic.new_state(1)
    del state["popularity"]
    logic.update_popularity(state, {"lines": [line("coffee", 200, 10, 10)]})
    assert state["popularity"] == {"cafe": 60}  # 50 + ceil(50 / 5)
    state["popularity"]["cafe"] = 100
    logic.update_popularity(state, {"lines": [line("coffee", 200, 10, 10)]})
    assert state["popularity"]["cafe"] == 100
    state["popularity"]["cafe"] = 0
    logic.update_popularity(state, {"lines": [line("coffee", 200, 10, 0)]})
    assert state["popularity"]["cafe"] == 0


def test_a_state_with_popularity_none_can_still_book_a_day():
    state = logic.new_state(1)
    state["popularity"] = None
    state["stock"]["coffee"] = 30
    new, _ = logic.trade_day(state)
    assert new["popularity"]["cafe"] == 60  # 50 + ceil(50 / 5)


def test_an_out_of_range_value_is_read_as_the_nearest_end():
    state = logic.new_state(1)
    state["popularity"]["cafe"] = 400
    assert logic.popularity_of(state, "cafe") == 100
    assert logic._popularity_factor(state, "cafe")[1]["students"] == 115
    state["popularity"]["cafe"] = -20
    assert logic.popularity_of(state, "cafe") == 0
    assert logic.popularity_word(400) == "Beloved"


def test_the_report_card_never_goes_above_100():
    assert logic.day_score([line("coffee", 200, 5, 9)]) == 100


def test_a_product_that_is_no_longer_in_the_catalogue_is_ignored():
    state = logic.new_state(1)
    logic.update_popularity(state, {"lines": [line("unicorn", 200, 10, 10)]})
    assert state["popularity"] == {sid: 50 for sid in logic.SHOPS}


def test_both_ways_of_booking_use_the_same_rule_for_the_same_lines():
    state = logic.new_state(1)
    state["stock"]["coffee"] = 30
    traded, whole = logic.trade_day(state)
    played, shift = play_cafe_shift(copy.deepcopy(state))
    assert traded["popularity"]["cafe"] == logic.walk(50, logic.day_score(whole["lines"]))
    assert played["popularity"]["cafe"] == logic.walk(50, logic.day_score(shift["lines"]))


def test_skipping_the_shift_costs_popularity():
    state = logic.new_state(1)
    state["stock"]["coffee"] = 30
    state = logic.start_shift(state, "cafe")
    after, result = logic.skip_shift(state)
    assert result["lines"][0]["sold"] == 0 and result["lines"][0]["demand"] > 0
    assert after["popularity"]["cafe"] < 50


# --- what popularity settles at -------------------------------------------------------------------

def test_full_shelves_at_the_reference_price_settle_at_the_top():
    assert play_whole_days(1, 100)[-1] >= 90


def test_a_rip_off_price_settles_low_even_with_full_shelves():
    assert play_whole_days(1, 140)[-1] <= 35


def test_empty_shelves_settle_at_the_bottom():
    assert play_whole_days(0, 100)[-1] <= 5


def test_half_the_customers_served_settles_in_the_middle():
    assert 40 <= play_whole_days(0.5, 100)[-1] <= 60


def test_a_slightly_higher_price_settles_between_the_two():
    fair, a_bit_more, greedy = (play_whole_days(1, p)[-1] for p in (100, 110, 140))
    assert fair > a_bit_more > greedy


def test_the_number_stays_between_0_and_100_every_day():
    for share, percent in ((1, 100), (0, 100), (1, 140), (0.5, 120)):
        assert all(0 <= p <= 100 for p in play_whole_days(share, percent))


# --- the factor ---------------------------------------------------------------------------------

def test_the_factor_is_85_100_and_115_percent():
    state = logic.new_state(1)
    for value, percent in ((0, 85), (50, 100), (100, 115), (54, Fraction(1012, 10))):
        state["popularity"]["cafe"] = value
        label, percents = logic._popularity_factor(state, "cafe")
        assert percents == {"students": percent, "visitors": percent}
        assert label == f"Popularity: {value}"


def test_the_popularity_factor_comes_after_weather_and_event():
    assert logic.FACTORS[:2] == (logic._weather_factor, logic._event_factor)
    assert logic.FACTORS[2] is logic._popularity_factor


def test_at_50_the_customers_are_what_they_were_and_away_from_it_they_follow_the_factor():
    state = logic.set_day_override(logic.new_state(1), "sun")
    base = logic.segment_percents(state, "cafe")
    state["popularity"]["cafe"] = 100
    high = logic.segment_percents(state, "cafe")
    state["popularity"]["cafe"] = 0
    low = logic.segment_percents(state, "cafe")
    for segment in base:
        assert high[segment] == base[segment] * Fraction(115, 100)
        assert low[segment] == base[segment] * Fraction(85, 100)


def test_popularity_changes_the_customers_in_the_expected_direction():
    state = logic.new_state(1)
    ref = logic.CATALOGUE["coffee"]["ref_price"]
    state["prices"]["coffee"] = ref
    state["popularity"]["cafe"] = 50
    normal = logic.customers_today(state, "coffee")
    state["popularity"]["cafe"] = 100
    more = logic.customers_today(state, "coffee")
    state["popularity"]["cafe"] = 0
    fewer = logic.customers_today(state, "coffee")
    assert fewer < normal < more


def test_the_cap_still_holds_with_full_popularity_and_a_huge_rush(monkeypatch):
    rush = lambda state, shop: ("Rush", {"students": 1_000, "visitors": 1_000})  # noqa: E731
    monkeypatch.setattr(logic, "FACTORS", (*logic.FACTORS, rush))
    state = logic.set_day_override(logic.new_state(1), "sun", "exam_period")
    state["popularity"]["cafe"] = 100
    assert logic.customers_today(state, "coffee") == logic.MAX_CUSTOMERS


def test_the_explanation_has_a_popularity_line_only_away_from_50():
    state = logic.new_state(1)
    names = [step["name"] for step in logic.customer_breakdown(state, "coffee")["steps"]]
    assert not any("Popularity" in name for name in names)
    state["popularity"]["cafe"] = 62
    steps = logic.customer_breakdown(state, "coffee")["steps"]
    assert steps[-1]["name"] == "Popularity: 62"
    assert steps[-1]["customers"] == logic.customers_today(state, "coffee")


def test_one_number_everywhere_also_with_a_popularity_that_is_not_50():
    state = logic.new_state(1)
    state["popularity"]["cafe"] = 80
    state["stock"]["coffee"] = 30
    wanted = logic.customers_today(state, "coffee")
    assert logic.customer_breakdown(state, "coffee")["customers"] == wanted
    _, result = logic.trade_day(state)
    assert result["lines"][0]["demand"] == wanted
    shift = logic.start_shift(state, "cafe")["shift"]
    assert shift["planned"]["coffee"] == wanted
    assert app.product_view(state, "coffee", False)["customers"] == wanted


# --- why it moved ---------------------------------------------------------------------------------

def test_the_report_is_the_card_of_the_last_booked_day():
    state = logic.new_state(1)
    assert logic.popularity_report(state, "cafe") is None  # nothing booked yet
    state["stock"]["coffee"] = 30
    state["prices"]["coffee"] = 220
    state, result = logic.trade_day(state)
    report = logic.popularity_report(state, "cafe")
    assert report == {"served": 100, "fair": 80, "score": logic.day_score(result["lines"])}
    assert report["score"] == 80
    assert logic.popularity_report(state, "surf_shop") is None  # no customers there


def test_the_report_of_a_day_with_nothing_sold_has_no_fairness():
    state, _ = logic.trade_day(logic.new_state(1))
    assert logic.popularity_report(state, "cafe") == {"served": 0, "fair": None, "score": 0}


def test_the_words_follow_the_value():
    assert [logic.popularity_word(v) for v in (0, 24, 25, 44, 45, 59, 60, 79, 80, 100)] == [
        "Avoided", "Avoided", "Unpopular", "Unpopular", "Known", "Known",
        "Popular", "Popular", "Beloved", "Beloved"]


# --- the editor ---------------------------------------------------------------------------------

def test_the_editor_sets_one_or_several_shops_and_leaves_the_rest():
    state = logic.new_state(1)
    state["popularity"]["surf_shop"] = 12
    one = logic.editor_set_state(state, {"popularity": {"cafe": 80}})
    assert one["popularity"] == {"cafe": 80, "beach_cafe": 50, "merchandise": 50, "surf_shop": 12}
    two = logic.editor_set_state(state, {"popularity": {"cafe": 0, "merchandise": 100}})
    assert (two["popularity"]["cafe"], two["popularity"]["merchandise"]) == (0, 100)
    assert two["popularity"]["surf_shop"] == 12
    assert state["popularity"]["cafe"] == 50  # the old state is not touched


@pytest.mark.parametrize("bad", [
    {}, [], "cafe", None, {"cafe": 101}, {"cafe": -1}, {"cafe": 5.5}, {"cafe": True},
    {"cafe": "80"}, {"cafe": None}, {"bakery": 50}, {1: 50}, {"cafe": 60, "bakery": 50},
])
def test_a_bad_popularity_patch_is_refused_and_changes_nothing(bad):
    state = logic.new_state(1)
    before = copy.deepcopy(state)
    with pytest.raises(logic.RejectedAction):
        logic.editor_set_state(state, {"popularity": bad})
    assert state == before


# --- the screen's answer and the endpoints ------------------------------------------------------------

@pytest.fixture
def api(tmp_path, monkeypatch):
    path = tmp_path / "run.db"
    db.save(logic.new_state(7), path)
    real_save, real_new = db.save, db.save_new_run
    monkeypatch.setattr(app, "load_run", lambda: db.load(path))
    monkeypatch.setattr(app.db, "save", lambda s: real_save(s, path))
    monkeypatch.setattr(app.db, "save_new_run", lambda s: real_new(s, path))
    monkeypatch.setenv("CT_EDITOR", "1")
    client = app.app.test_client()
    client.path = path
    return client


def test_the_state_shows_the_popularity_of_every_shop(api):
    shops = {s["id"]: s for s in api.get("/api/state").get_json()["shops"]}
    assert set(shops) == set(logic.SHOPS)
    for shop in shops.values():
        assert shop["popularity"] == {"value": 50, "word": "Known", "yesterday": None}


def test_the_state_explains_the_last_day(api):
    assert api.post("/api/open", json={"day": 1}).status_code == 200
    cafe = next(s for s in api.get("/api/state").get_json()["shops"] if s["id"] == "cafe")
    assert cafe["popularity"]["value"] < 50
    assert cafe["popularity"]["yesterday"] == {"served": 0, "fair": None, "score": 0}


def test_the_editor_endpoint_sets_the_popularity(api):
    response = api.post("/api/editor/state", json={"patch": {"popularity": {"cafe": 91}}})
    assert response.status_code == 200
    assert db.load(api.path)["popularity"]["cafe"] == 91
    cafe = next(s for s in api.get("/api/state").get_json()["shops"] if s["id"] == "cafe")
    assert cafe["popularity"]["word"] == "Beloved"


@pytest.mark.parametrize("bad", [{"cafe": 101}, {"cafe": 1.5}, {"cafe": True}, {"bakery": 5}, {}])
def test_a_bad_popularity_is_refused_by_the_endpoint_and_saves_nothing(api, bad):
    api.post("/api/editor/state", json={"patch": {"popularity": {"cafe": 70}}})
    before = db.load(api.path)
    response = api.post("/api/editor/state", json={"patch": {"popularity": bad}})
    assert response.status_code == 400 and response.get_json()["error"]
    assert db.load(api.path) == before


def test_a_request_cannot_set_the_popularity_through_the_normal_endpoints(api):
    before = db.load(api.path)
    api.post("/api/open", json={"day": 1, "popularity": {"cafe": 100}})
    api.post("/api/day-override", json={"popularity": {"cafe": 100}})
    assert db.load(api.path)["popularity"]["cafe"] <= before["popularity"]["cafe"]


def test_the_state_never_contains_the_seed(api):
    assert '"seed"' not in api.get("/api/state").get_data(as_text=True)


def test_the_editor_is_off_by_default(api, monkeypatch):
    monkeypatch.delenv("CT_EDITOR")
    response = api.post("/api/editor/state", json={"patch": {"popularity": {"cafe": 100}}})
    assert response.status_code == 400 and "editor is off" in response.get_json()["error"]
    assert db.load(api.path)["popularity"]["cafe"] == 50


# --- the pages ---------------------------------------------------------------------------------------

def test_the_shared_helper_writes_the_texts_through_esc_and_the_width_as_a_number():
    text = (STATIC / "common.js").read_text()
    body = text[text.index("function popularityHtml"):]
    body = body[:body.index("\n}\n")]
    assert "esc(pop.value)" in body and "esc(pop.word)" in body and "esc(why)" in body
    assert "Number(pop.value)" in body
    assert "${pop.word}" not in body and "${pop.value}" not in body.replace("esc(pop.value)", "")


def test_the_dashboard_and_the_campus_panel_show_it():
    assert 'id="pop-grid"' in (STATIC / "index.html").read_text()
    app_js = (STATIC / "app.js").read_text()
    assert "function renderPopularity" in app_js and "renderPopularity();" in app_js
    assert "popularityHtml(s.popularity)" in app_js
    assert "popularityHtml(s.popularity)" in (STATIC / "world" / "ui.js").read_text()
    for css in ("style.css", "map.css"):
        assert ".pop-bar" in (STATIC / css).read_text()


def test_the_page_loads_nothing_from_outside():
    for name in ("common.js", "index.html", "app.js"):
        assert "http://" not in (STATIC / name).read_text().replace("http://www.w3.org", "")
