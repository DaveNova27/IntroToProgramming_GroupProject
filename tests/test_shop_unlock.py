"""Checks from specs/shop-unlock.md ("Done when"). One test per check."""

import copy
import sqlite3

import pytest

import app
import db
import logic


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "test.db"


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


# ---- Check 1: a new run ---------------------------------------------------

def test_a_new_run_has_the_cafe_on_level_one_with_the_coffee():
    state = logic.new_state()
    assert state["cash"] == 10_000
    assert state["shops"]["cafe"] == {
        "unlocked": True, "level": 1, "products": ["coffee"], "staff_places": 0,
    }
    for shop in ("beach_cafe", "merchandise", "surf_shop"):
        assert state["shops"][shop]["unlocked"] is False
    assert logic.owned_products(state) == ["coffee"]


def test_the_shop_table_matches_the_team_list_and_uses_integer_cents():
    assert list(logic.SHOPS) == ["cafe", "beach_cafe", "merchandise", "surf_shop"]
    assert logic.SHOPS["cafe"]["unlock_price"] == 0
    assert {sid: logic.shop_product_ids(sid) for sid in logic.SHOPS} == {
        "cafe": ["coffee", "cake", "bagel"],
        "surf_shop": ["surfboard", "wetsuit", "surf_lesson"],
        "merchandise": ["hoodie", "tshirt", "cap"],
        "beach_cafe": ["beer", "coke_zero", "sandwich"],
    }
    # every product belongs to exactly one shop
    assert sorted(p for sid in logic.SHOPS for p in logic.shop_product_ids(sid)) == sorted(logic.CATALOGUE)
    for shop in logic.SHOPS.values():
        assert shop["storage"] == 100 and shop["counter"] == 20
        assert shop["window"]["staff_1"]["price"] == shop["window"]["staff_2"]["price"] == 6_000
        for offer in shop["window"].values():
            assert isinstance(offer["price"], int) and offer["price"] > 0
        assert isinstance(shop["unlock_price"], int)
    for item in logic.CATALOGUE.values():
        assert isinstance(item["cost"], int) and isinstance(item["ref_price"], int)


# ---- Check 2: exact prices, level +1 --------------------------------------

def test_unlocking_a_shop_costs_the_listed_price():
    state = logic.unlock_shop(rich(), "beach_cafe")
    assert state["cash"] == 100_000 - 20_000
    assert state["shops"]["beach_cafe"] == {
        "unlocked": True, "level": 1, "products": ["beer"], "staff_places": 0,
    }
    assert "beer" in logic.owned_products(state)


def test_every_window_purchase_costs_its_price_and_raises_the_level():
    state = rich()
    cash = state["cash"]
    for level, (item, price) in enumerate(
        [("cake", 4_000), ("bagel", 3_000), ("staff_1", 6_000), ("staff_2", 6_000)], start=2
    ):
        state = logic.buy_upgrade(state, "cafe", item)
        cash -= price
        assert state["cash"] == cash
        assert state["shops"]["cafe"]["level"] == level
    assert state["shops"]["cafe"]["products"] == ["coffee", "cake", "bagel"]
    assert state["shops"]["cafe"]["staff_places"] == 2


def test_a_bought_product_can_be_stocked_priced_and_traded():
    state = logic.buy_upgrade(rich(), "cafe", "cake")
    state = logic.buy(state, "cake", 5)
    state = logic.set_price(state, "cake", 350)
    state, result = logic.trade_day(state)
    assert {line["product"] for line in result["lines"]} == {"coffee", "cake"}
    assert state["stock"]["cake"] == 0


# ---- Check 3: refusals change nothing -------------------------------------

def test_too_little_cash_is_refused():
    refused(lambda s: logic.unlock_shop(s, "beach_cafe"), logic.new_state())  # €100 < €200
    state = rich()
    state["cash"] = 3_999
    refused(lambda s: logic.buy_upgrade(s, "cafe", "cake"), state)


def test_a_shop_already_unlocked_is_refused():
    refused(lambda s: logic.unlock_shop(s, "cafe"), rich())
    refused(lambda s: logic.unlock_shop(s, "beach_cafe"), logic.unlock_shop(rich(), "beach_cafe"))


def test_an_item_already_bought_is_refused():
    state = logic.buy_upgrade(rich(), "cafe", "cake")
    refused(lambda s: logic.buy_upgrade(s, "cafe", "cake"), state)
    state = logic.buy_upgrade(state, "cafe", "staff_1")
    refused(lambda s: logic.buy_upgrade(s, "cafe", "staff_1"), state)


def test_the_second_employee_place_needs_the_first():
    refused(lambda s: logic.buy_upgrade(s, "cafe", "staff_2"), rich())


def test_a_locked_shop_has_no_window():
    refused(lambda s: logic.buy_upgrade(s, "beach_cafe", "sandwich"), rich())


@pytest.mark.parametrize("shop", ["mall", "", None, 3, ["cafe"], {"a": 1}, True, "CAFE", "snack_stand"])
def test_an_unknown_or_wrongly_typed_shop_is_refused(shop):
    refused(lambda s: logic.unlock_shop(s, shop), rich())
    refused(lambda s: logic.buy_upgrade(s, shop, "staff_1"), rich())


@pytest.mark.parametrize("item", ["gold", "", None, 3, ["cake"], {"a": 1}, "beer", "coffee"])
def test_an_unknown_wrongly_typed_or_foreign_item_is_refused(item):
    # "beer" is a real product but not in the Cafe's window; "coffee" is its start product
    refused(lambda s: logic.buy_upgrade(s, "cafe", item), rich())


def test_a_product_not_yet_owned_cannot_be_bought_or_priced():
    refused(lambda s: logic.buy(s, "cake", 1), rich())
    refused(lambda s: logic.set_price(s, "cake", 350), rich())
    # a locked shop's starting product is not owned either
    refused(lambda s: logic.buy(s, "beer", 1), rich())


def test_nothing_can_be_bought_after_the_last_day():
    state = rich()
    state["day"] = logic.LAST_DAY + 1
    refused(lambda s: logic.unlock_shop(s, "beach_cafe"), state)
    refused(lambda s: logic.buy_upgrade(s, "cafe", "cake"), state)


def test_only_owned_products_count_in_the_overview_and_stock_value():
    state = logic.buy(logic.new_state(), "coffee", 3)
    state["stock"]["cake"] = 50  # set directly, but the player does not have cake
    assert [l["product"] for l in logic.stock_overview(state)["lines"]] == ["coffee"]
    assert logic.stock_value(state) == 3 * 80
    _, result = logic.trade_day(state)
    assert [l["product"] for l in result["lines"]] == ["coffee"]


# ---- Check 4: saving ------------------------------------------------------

def test_shops_and_purchases_survive_a_restart(db_path):
    state = logic.unlock_shop(rich(), "beach_cafe")
    state = logic.buy_upgrade(state, "beach_cafe", "sandwich")
    state = logic.buy_upgrade(state, "cafe", "staff_1")
    db.save(state, db_path)
    assert db.load(db_path) == state


def test_a_save_from_before_this_spec_still_loads(db_path):
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE run (id INTEGER PRIMARY KEY, day INTEGER, cash INTEGER);
        CREATE TABLE products (product TEXT PRIMARY KEY, stock INTEGER, price INTEGER);
        CREATE TABLE history (day INTEGER PRIMARY KEY, result TEXT);
        INSERT INTO run VALUES (1, 4, 5000);
        INSERT INTO products VALUES ('sandwich', 7, 400), ('coffee', 2, 250), ('cookie', 3, 150);
    """)
    conn.commit()
    conn.close()

    state = db.load(db_path)
    assert state["cash"] == 5_000 and state["day"] == 4
    # the old sandwich and coffee find their shops; the cookie no longer exists
    assert state["shops"]["cafe"]["unlocked"] is True
    assert state["shops"]["cafe"]["products"] == ["coffee"]
    assert state["shops"]["beach_cafe"]["unlocked"] is True
    assert state["shops"]["beach_cafe"]["products"] == ["sandwich"]
    assert state["shops"]["surf_shop"]["unlocked"] is False
    assert "cookie" not in state["stock"]
    assert state["stock"]["sandwich"] == 7 and state["prices"]["coffee"] == 250
    assert state["stock"]["beer"] == 0  # a new product starts with no stock
    assert logic.owned_products(state) == ["coffee", "sandwich"]
    db.save(state, db_path)  # and it can be saved and loaded again
    assert db.load(db_path) == state


# ---- the server -----------------------------------------------------------

@pytest.fixture
def client(db_path, monkeypatch):
    real_load, real_save = db.load, db.save
    monkeypatch.setattr(db, "load", lambda path=db_path: real_load(path))
    monkeypatch.setattr(db, "save", lambda state, path=db_path: real_save(state, path))
    state = logic.new_state()
    state["cash"] = 40_000
    real_save(state, db_path)
    return app.app.test_client(), db_path


def test_the_api_unlocks_and_upgrades_and_shows_the_shops(client):
    c, path = client
    r = c.post("/api/shop/unlock", json={"shop": "beach_cafe"})
    assert r.status_code == 200
    r = c.post("/api/shop/upgrade", json={"shop": "beach_cafe", "item": "sandwich"})
    assert r.status_code == 200
    view = r.get_json()["state"]
    assert view["cash"] == 40_000 - 20_000 - 8_000
    beach = next(s for s in view["shops"] if s["id"] == "beach_cafe")
    assert beach["level"] == 2 and beach["unlocked"] is True
    assert {p["id"] for p in view["products"]} == {"coffee", "beer", "sandwich"}
    assert db.load(path)["shops"]["beach_cafe"]["products"] == ["beer", "sandwich"]


@pytest.mark.parametrize("path, body", [
    ("/api/shop/unlock", {"shop": "surf_shop"}),          # too little cash
    ("/api/shop/unlock", {"shop": "cafe"}),               # already unlocked
    ("/api/shop/unlock", {"shop": ["cafe"]}),             # wrong type
    ("/api/shop/unlock", {"shop": "mall"}),               # unknown
    ("/api/shop/unlock", {}),                             # missing
    ("/api/shop/unlock", [1, 2]),                         # not an object
    ("/api/shop/upgrade", {"shop": "beach_cafe", "item": "sandwich"}),  # locked shop
    ("/api/shop/upgrade", {"shop": "cafe", "item": "gold"}),            # unknown item
    ("/api/shop/upgrade", {"shop": "cafe", "item": {"a": 1}}),          # wrong type
    ("/api/shop/upgrade", {"shop": "cafe"}),                            # missing item
])
def test_a_crafted_request_is_refused_and_the_saved_run_stays_identical(client, path, body):
    c, db_path = client
    before = db.load(db_path)
    r = c.post(path, json=body)
    assert r.status_code == 400
    assert "error" in r.get_json()
    assert db.load(db_path) == before
