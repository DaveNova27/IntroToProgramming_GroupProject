"""Checks from specs/bulk-order.md ("Done when"): several products in one order, all or nothing."""

import copy

import pytest

import logic


def two_shops(cash=1_000_000):
    """The Cafe with all three products and the Beach Cafe, plenty of cash."""
    state = logic.new_state()
    state["cash"] = 1_000_000
    state = logic.unlock_shop(state, "beach_cafe")
    for item in ("cake", "bagel"):
        state = logic.buy_upgrade(state, "cafe", item)
    state["cash"] = cash  # set after unlocking, so the test decides the cash
    return state


def refused(state, items):
    """The order must be refused and must leave the given state untouched."""
    before = copy.deepcopy(state)
    with pytest.raises(logic.RejectedAction) as info:
        logic.buy_many(state, items)
    assert state == before
    return str(info.value)


def line(product, quantity):
    return {"product": product, "quantity": quantity}


# ---- Check 1: the rule ----------------------------------------------------------------------

def test_several_products_are_bought_in_one_order():
    state = two_shops()
    order = [line("coffee", 10), line("cake", 5), line("beer", 7)]
    new = logic.buy_many(state, order)
    cost = sum(q * logic.CATALOGUE[p]["cost"] for p, q in (("coffee", 10), ("cake", 5), ("beer", 7)))
    assert new["cash"] == state["cash"] - cost
    assert (new["stock"]["coffee"], new["stock"]["cake"], new["stock"]["beer"]) == (10, 5, 7)
    assert state["stock"]["coffee"] == 0  # the old state is untouched


def test_one_order_is_the_same_as_buying_line_by_line():
    state = two_shops()
    order = [line("bagel", 3), line("coffee", 20)]
    one_by_one = logic.buy(logic.buy(state, "bagel", 3), "coffee", 20)
    assert logic.buy_many(state, order) == one_by_one


def test_exactly_enough_cash_for_the_total_is_enough():
    cost = 4 * logic.CATALOGUE["coffee"]["cost"] + 2 * logic.CATALOGUE["beer"]["cost"]
    state = two_shops(cash=cost)
    assert logic.buy_many(state, [line("coffee", 4), line("beer", 2)])["cash"] == 0


def test_too_little_cash_for_the_total_refuses_everything():
    cost = 4 * logic.CATALOGUE["coffee"]["cost"] + 2 * logic.CATALOGUE["beer"]["cost"]
    state = two_shops(cash=cost - 1)
    # each line alone would be affordable, the whole order is not
    logic.buy(state, "coffee", 4)
    logic.buy(state, "beer", 2)
    assert "Not enough cash" in refused(state, [line("coffee", 4), line("beer", 2)])


def test_the_storeroom_limit_counts_all_lines_of_one_shop_together():
    state = two_shops()
    room = logic.SHOPS["cafe"]["storage"]
    assert logic.buy_many(state, [line("coffee", room - 10), line("cake", 10)])
    message = refused(state, [line("coffee", room - 10), line("cake", 11)])
    assert message.startswith("Cake:") and "storeroom" in message
    # another shop has its own storeroom
    assert logic.buy_many(state, [line("coffee", room), line("beer", room)])


@pytest.mark.parametrize("items", [
    [line("hoodie", 1)],                      # not unlocked
    [line("pizza", 1)],                       # unknown
    [line(["coffee"], 1)],                    # not a product id
    [line("coffee", 0)],                      # nothing to order
    [line("coffee", -3)],
    [line("coffee", 2.5)],
    [line("coffee", "5")],
    [line("coffee", True)],
    [line("coffee", 2), line("coffee", 3)],   # twice
    [{"product": "coffee"}],                  # no quantity
    [{"product": "coffee", "quantity": 1, "price": 0}],
    ["coffee"],
    [],
    "coffee",
    None,
])
def test_a_bad_line_or_list_refuses_the_whole_order(items):
    state = two_shops()
    if isinstance(items, list) and items and isinstance(items[0], dict) and items[0].get("product") != "coffee":
        items = [line("beer", 3), *items]  # a good line before the bad one is not booked either
    refused(state, items)


def test_a_bad_line_after_good_ones_books_nothing():
    state = two_shops()
    refused(state, [line("coffee", 5), line("beer", 5), line("cake", 0)])


def test_more_lines_than_products_are_refused():
    state = two_shops()
    assert "more lines" in refused(state, [line("coffee", 1)] * (len(logic.CATALOGUE) + 1))


def test_nothing_is_bought_when_the_run_is_complete():
    state = two_shops()
    state["day"] = logic.LAST_DAY + 1
    refused(state, [line("coffee", 1)])


# ---- Check 2: the API -----------------------------------------------------------------------

import app  # noqa: E402
import db  # noqa: E402


@pytest.fixture
def run_on_disk(tmp_path, monkeypatch):
    """The real API on a temporary save with two shops, so the player's own run stays untouched."""
    path = tmp_path / "run.db"
    db.save(two_shops(cash=20_000), path)  # 200 euro
    real_save = db.save
    monkeypatch.setattr(app, "load_run", lambda: db.load(path))
    monkeypatch.setattr(app.db, "save", lambda state, *_, **__: real_save(state, path))
    return path


def test_an_order_through_the_api(run_on_disk):
    before = db.load(run_on_disk)
    response = app.app.test_client().post("/api/buy-many", json={"items": [
        {"product": "coffee", "quantity": "10"}, {"product": "beer", "quantity": 4}]})
    assert response.status_code == 200, response.get_json()
    after = db.load(run_on_disk)
    cost = 10 * logic.CATALOGUE["coffee"]["cost"] + 4 * logic.CATALOGUE["beer"]["cost"]
    assert after["cash"] == before["cash"] - cost
    assert (after["stock"]["coffee"], after["stock"]["beer"]) == (10, 4)
    assert response.get_json()["message"] == f"Ordered 10 × Coffee, 4 × Beer for {logic.fmt(cost)}."


@pytest.mark.parametrize("body", [
    {},
    {"items": []},
    {"items": "coffee"},
    {"items": {"product": "coffee", "quantity": 1}},
    {"items": [{"product": "coffee", "quantity": "ten"}]},
    {"items": [{"product": "coffee", "quantity": "2.5"}]},
    {"items": [{"product": "coffee", "quantity": "0"}]},
    {"items": [{"product": "coffee", "quantity": 1, "price": 0}]},
    {"items": [{"product": "coffee", "quantity": 5}, {"product": "hoodie", "quantity": 1}]},
    {"items": [{"product": "coffee", "quantity": 5}, {"product": "coffee", "quantity": 5}]},
    {"items": [{"product": "coffee", "quantity": 1}] * 13},
    {"items": [{"product": "coffee", "quantity": 400}, {"product": "beer", "quantity": 1}]},
    {"items": [{"product": "coffee", "quantity": 90}, {"product": "beer", "quantity": 90},
               {"product": "cake", "quantity": 10}]},  # 222 euro, more than the cash
])
def test_a_crafted_order_is_refused_and_changes_nothing(run_on_disk, body):
    before = db.load(run_on_disk)
    response = app.app.test_client().post("/api/buy-many", json=body)
    assert response.status_code == 400, response.get_json()
    assert response.get_json()["error"]
    assert db.load(run_on_disk) == before
