"""Checks from specs/merch-wear.md ("Done when"): a guest who buys clothes in the Merchandise shop
puts them on and leaves wearing exactly that item.

The server keeps a note of who bought which item; the map only draws from that note.
"""

import copy
from pathlib import Path

import app
import db
import logic

STATIC = Path(app.__file__).parent / "static"


def merch_shift(seed=7):
    """The Merchandise shop with all three products, stock on the counter, its shift running."""
    state = logic.new_state(seed)
    state["cash"] = 10_000_000
    state = logic.unlock_shop(state, "merchandise")
    for item in ("tshirt", "cap"):
        state = logic.buy_upgrade(state, "merchandise", item)
    for pid in logic.owned_products(state):
        state["stock"][pid] = 60
    state = logic.set_day_override(state, "sun")
    state = logic.start_shift(logic.open_day(state), "merchandise")
    for pid in logic.WEARABLE:
        state = logic.refill(state, pid, 5)
    return state


def sell_everything(state, ticks=40):
    """Tick and sell whatever somebody waits for, like a player at the counter."""
    for _ in range(ticks):
        state, _result = logic.tick(state)
        if state["shift"] is None or state["shift"].get("over"):
            break
        for pid in logic.WEARABLE:
            try:
                state = logic.sell(state, pid)
            except logic.RejectedAction:
                pass
    return state


def first_customer_here(state, product):
    """Tick until a guest who wants `product` waits at the counter."""
    for _ in range(40):
        try:
            logic.sell(state, product)
            return state
        except logic.RejectedAction:
            state, _result = logic.tick(state)
    raise AssertionError(f"nobody came for {product}")


# ---- Check 1: the note --------------------------------------------------------------------

def test_the_wearable_goods_are_the_merchandise_products():
    assert set(logic.WEARABLE) == set(logic.shop_product_ids("merchandise"))


def test_selling_clothes_to_a_guest_notes_who_bought_what():
    state = first_customer_here(merch_shift(), "hoodie")
    tick = state["shift"]["tick"]
    i = logic._check_sale(state, "hoodie")
    guest = state["shift"]["queue"][i]["guest"]["id"]
    after = logic.sell(state, "hoodie")
    assert after["shift"]["dressed"][-1] == {"guest": guest, "product": "hoodie", "tick": tick}
    assert "dressed" not in state["shift"] or state["shift"]["dressed"] == []  # the old state is untouched


def test_the_note_changes_no_number_of_the_sale():
    state = first_customer_here(merch_shift(), "tshirt")
    after = logic.sell(state, "tshirt")
    without = copy.deepcopy(after)
    without["shift"].pop("dressed")
    plain = copy.deepcopy(state)
    i = logic._check_sale(plain, "tshirt")
    plain["shift"]["queue"].pop(i)
    plain["shift"]["counter"]["tshirt"] -= 1
    plain["shift"]["sold"]["tshirt"] += 1
    plain["cash"] += plain["prices"]["tshirt"]
    assert without == plain


def test_food_and_customers_without_a_guest_get_no_note():
    state = logic.new_state(3)
    state["stock"]["coffee"] = 20
    state = logic.set_day_override(state, "rain")
    state = logic.start_shift(logic.open_day(state), "cafe")
    state = logic.refill(state, "coffee", 5)
    state = sell_everything(state, ticks=30)
    assert not state["shift"].get("dressed")
    # a customer without a guest (an old save, a staffed shop without the plan) is served without a note
    shift = {"queue": [{"product": "cap", "arrives": 0, "patience_until": 9}], "counter": {"cap": 1},
             "sold": {"cap": 0}, "tick": 1}
    bare = {"shift": shift, "cash": 0, "prices": {"cap": 430}}
    logic._serve(bare, 0, "cap")
    assert "dressed" not in shift and shift["sold"]["cap"] == 1


def test_only_the_newest_notes_are_kept_and_they_are_saved(tmp_path):
    state = sell_everything(merch_shift(), ticks=80)
    dressed = state["shift"]["dressed"]
    assert 0 < len(dressed) <= logic.DRESSED_KEEP
    assert all(d["product"] in logic.WEARABLE for d in dressed)
    path = tmp_path / "run.db"
    db.save(state, path)
    assert db.load(path) == state


def test_staff_selling_clothes_also_leaves_a_note():
    state = logic.new_state(7)
    state["cash"] = 10_000_000
    state = logic.unlock_shop(state, "merchandise")
    state = logic.buy_upgrade(state, "merchandise", "staff_1")
    state = logic.buy_upgrade(state, "merchandise", "staff_2")
    state["stock"]["hoodie"] = 60
    state = logic.open_day(logic.set_day_override(state, "sun"))
    for _ in range(60):
        state, _result = logic.tick(state)
    parts = [state["shift"], *state["shift"].get("extra", {}).values()]
    merch = next(p for p in parts if p.get("shop") == "merchandise")
    assert merch.get("dressed"), "the employees sold hoodies to guests"


# ---- Check 2: the view ----------------------------------------------------------------------

def test_the_view_lists_the_fresh_notes_only():
    state = first_customer_here(merch_shift(), "cap")
    state = logic.sell(state, "cap")
    note = state["shift"]["dressed"][-1]
    view = app.guests_view(state)
    assert {"id": note["guest"], "product": "cap"} in view["dressed"]
    # the guest is no longer walking: the map lets them dress and leave
    assert note["guest"] not in [g["id"] for g in view["walking"]]
    later = copy.deepcopy(state)
    later["shift"]["tick"] = note["tick"] + app.DRESSED_SHOW_TICKS + 1
    assert {"id": note["guest"], "product": "cap"} not in app.guests_view(later)["dressed"]


# ---- Check 3: the map draws it --------------------------------------------------------------

def test_the_map_dresses_the_guest_from_the_note():
    guests = (STATIC / "world" / "guests.js").read_text()
    people = (STATIC / "world" / "people.js").read_text()
    assert "server.guests?.dressed" in guests and "DRESS_MS" in guests
    assert "wear: view.wear" in guests and "reducedMotion" in guests
    for pid in logic.WEARABLE:
        assert f"  {pid}: {{" in people, f"no look for {pid}"
    assert 'pose === "dress"' in people and "function drawCap" in people and "function drawPullingOn" in people
    assert "Math.random" not in guests and "Math.random" not in people
