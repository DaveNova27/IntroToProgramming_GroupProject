"""Checks from specs/guests.md: guests that choose a shop (the small version).

The crowd of a day is the price logic's (customers_today). Guests only spread it over the shops
that are served today, by the walk, the queue they would find and their own taste."""

import collections
import json

import pytest

import app
import db
import guests
import logic
import world


def two_shops(seed=7, weather="heat", beach_items=("coke_zero", "sandwich")):
    """The Cafe and a staffed Beach Cafe with all its products, plenty of stock and cash."""
    state = logic.new_state(seed)
    state["cash"] = 10_000_000
    state = logic.unlock_shop(state, "beach_cafe")
    state = logic.buy_upgrade(state, "beach_cafe", "staff_1")  # hires the first employee
    for item in beach_items:
        state = logic.buy_upgrade(state, "beach_cafe", item)
    for pid in logic.owned_products(state):
        state["stock"][pid] = 60
    return logic.set_day_override(state, weather) if weather else state


def crowd(state, shops):
    return sum(logic.customers_today(state, pid) for shop in shops for pid in state["shops"][shop]["products"])


def everyone(plan):
    return [g for shop_guests in plan.values() for g in shop_guests]


def refused(action, state):
    before = json.dumps(state, sort_keys=True)
    with pytest.raises(logic.RejectedAction):
        action(state)
    assert json.dumps(state, sort_keys=True) == before


# ---- who may be chosen ---------------------------------------------------------------------


def test_guests_choose_only_from_shops_that_are_served_today():
    state = logic.new_state()
    assert guests.guest_shops(state) == ["cafe"]
    state["cash"] = 10_000_000
    state = logic.unlock_shop(state, "beach_cafe")
    assert guests.guest_shops(state) == ["cafe"]  # unlocked, but nobody serves there
    state = logic.buy_upgrade(state, "beach_cafe", "staff_1")
    assert guests.guest_shops(state) == ["cafe", "beach_cafe"]
    state["employees"][0]["working"] = False  # an employee who does not work serves nobody
    assert guests.guest_shops(state) == ["cafe"]
    assert "surf_shop" not in guests.plan_day(two_shops())  # a locked shop gets no guests


def test_the_choice_is_fixed_when_the_day_opens():
    state = logic.open_day(two_shops())
    assert state["shift"]["guest_shops"] == ["cafe", "beach_cafe"]
    assert logic.start_shift(state, "cafe")["shift"]["guest_shops"] == ["cafe", "beach_cafe"]


# ---- the crowd stays the same --------------------------------------------------------------


@pytest.mark.parametrize("weather", ["sun", "rain", "heat", "storm"])
@pytest.mark.parametrize("seed", [1, 7, 42])
def test_the_crowd_keeps_its_size_and_every_product_stays_in_the_spread(seed, weather):
    state = two_shops(seed, weather)
    plan = guests.plan_day(state)
    assert sum(len(v) for v in plan.values()) == crowd(state, plan)
    assert sorted(g["id"] for g in everyone(plan)) == list(range(crowd(state, plan)))
    got = collections.Counter(g["product"] for g in everyone(plan))
    for pid in logic.owned_products(state):
        wanted = logic.customers_today(state, pid)
        low = wanted - wanted * guests.CHOOSER_PERCENT // 100
        high = min(logic.MAX_CUSTOMERS, wanted + wanted * guests.MAX_SPREAD // 100)
        assert low <= got[pid] <= high, (pid, wanted, got[pid])
    for shop, mine in plan.items():
        assert all(g["shop"] == shop and g["product"] in state["shops"][shop]["products"] for g in mine)


def test_the_same_state_gives_the_same_guests_and_another_seed_others():
    assert guests.plan_day(two_shops()) == guests.plan_day(two_shops())
    assert guests.plan_day(two_shops(seed=7)) != guests.plan_day(two_shops(seed=8))
    state = logic.open_day(two_shops())
    assert logic.start_shift(state, "cafe") == logic.start_shift(state, "cafe")


def test_a_shop_that_runs_alone_keeps_the_old_queue():
    state = logic.start_shift(logic.set_day_override(logic.new_state(), "storm"), "cafe")
    queue = state["shift"]["queue"]
    assert [c["arrives"] for c in queue] == [i * 9 for i in range(10)]
    assert all(c["guest"]["wish"] == "cafe" for c in queue)
    plan = guests.plan_day(state, ["cafe"])
    assert all(g["wish"] == g["shop"] == "cafe" for g in plan["cafe"])


def test_some_guests_really_change_their_shop():
    moved = 0
    for seed in range(1, 6):
        for weather in ("sun", "heat", "rain"):
            moved += sum(g["wish"] != g["shop"] for g in everyone(guests.plan_day(two_shops(seed, weather))))
    assert moved >= 10


# ---- what a guest weighs -------------------------------------------------------------------


def test_a_long_queue_sends_guests_elsewhere():
    """A hot day with the whole Beach Cafe: its queue is long, so some guests take the Cafe."""
    def long_queue_moves(state):
        return [g for g in everyone(guests.plan_day(state))
                if g["wish"] == "beach_cafe" and g["shop"] == "cafe"
                and g["thought"] == "Long queue at the Beach Cafe: the Cafe instead"]
    moves = sum(len(long_queue_moves(two_shops(seed, "heat"))) for seed in range(1, 6))
    assert moves >= 1


def test_without_the_queue_nobody_leaves_because_of_it(monkeypatch):
    monkeypatch.setattr(guests, "QUEUE_LOSS", 0)
    thoughts = [g["thought"] for seed in range(1, 6) for g in everyone(guests.plan_day(two_shops(seed, "heat")))]
    assert not any(t.startswith("Long queue") for t in thoughts)


def test_a_product_nobody_buys_at_its_price_gets_no_guests():
    state = two_shops(weather="sun")
    state["prices"]["coffee"] = logic.CATALOGUE["coffee"]["ref_price"] * 3  # above every curve
    assert logic.customers_today(state, "coffee") == 0
    assert guests.plan_day(state)["cafe"] == []  # not even a guest who looks around comes


def test_the_weather_moves_the_guests_as_the_demo_shows():
    heat = guests.plan_day(two_shops(weather="heat"))
    rain = guests.plan_day(two_shops(weather="rain"))
    assert len(heat["beach_cafe"]) > len(rain["beach_cafe"])
    assert len(heat["cafe"]) < len(rain["cafe"])
    assert any(g["thought"] == "Rainy: good day for the Cafe" for g in rain["cafe"])
    assert any(g["thought"] == "Hot: good day for the Beach Cafe" for g in heat["beach_cafe"])


def thoughts_that_can_be():
    names = list(guests.CALLED.values())
    out = {f"My usual {n[4:]}" for n in names} | {f"Off to {n}" for n in names}
    out |= {f"{logic.CATALOGUE[pid]['name']} is cheap today" for pid in logic.CATALOGUE}
    out |= {f"{w['name']}: good day for {n}" for w in logic.WEATHER.values() for n in names}
    out |= {f"{e['name']}: off to {n}" for e in logic.EVENTS.values() for n in names}
    for wish in names:
        for to in names:
            for text in [*guests.SWITCH_THOUGHTS.values(), *guests.STAY_THOUGHTS.values()]:
                said = text.format(wish=wish, to=to)
                out.add(said[0].upper() + said[1:])
    return out


def test_every_thought_comes_from_the_fixed_list():
    possible = thoughts_that_can_be()
    for seed in range(1, 4):
        for weather in logic.WEATHER:
            for g in everyone(guests.plan_day(two_shops(seed, weather))):
                assert g["thought"] in possible, g["thought"]


# ---- the day with guests -------------------------------------------------------------------


def test_every_guest_of_the_day_is_booked():
    state = logic.open_day(two_shops())
    state = logic.start_shift(state, "cafe")
    parts = [state["shift"], *state["shift"]["extra"].values()]
    planned = sum(sum(part["planned"].values()) for part in parts)
    assert planned == sum(len(part["queue"]) for part in parts) == crowd(state, ["cafe", "beach_cafe"])
    for part in parts:
        assert part["guests"]["total"] == len(part["queue"])
    state, result = logic.skip_shift(state)
    sold = sum(line["sold"] for line in result["lines"])
    assert result["lost"] + sold == planned


def test_a_shop_staffed_later_in_the_day_plans_alone():
    state = logic.new_state()
    state["cash"] = 10_000_000
    state = logic.open_day(state)
    assert state["shift"]["guest_shops"] == ["cafe"]
    state = logic.unlock_shop(state, "beach_cafe")
    state = logic.buy_upgrade(state, "beach_cafe", "staff_1")  # opens its staffed shift now
    beach = state["shift"]["extra"]["beach_cafe"]
    assert len(beach["queue"]) == logic.customers_today(state, "beer")
    assert all(c["guest"]["wish"] == "beach_cafe" for c in beach["queue"])


def test_guests_are_not_stored_beside_the_queue_and_survive_a_restart(tmp_path):
    state = logic.start_shift(logic.open_day(two_shops()), "cafe")
    assert set(state) == set(logic.new_state())  # no new field in the state
    path = tmp_path / "run.db"
    db.save(state, path)
    assert db.load(path) == state


def test_a_rejected_action_still_changes_nothing_with_guests():
    state = logic.start_shift(logic.open_day(two_shops()), "cafe")
    refused(lambda s: logic.start_shift(s, "cafe"), state)
    refused(lambda s: logic.sell(s, "surfboard"), state)
    refused(lambda s: logic.set_price(s, "coffee", 300), state)


# ---- the screen ----------------------------------------------------------------------------


def view_of(state):
    with app.app.test_request_context():
        return app.view(state)


def test_the_screen_gets_guests_only_while_the_day_is_open():
    state = two_shops()
    assert view_of(state)["guests"] is None
    opened = logic.open_day(state)
    data = view_of(opened)["guests"]
    assert [s["shop"] for s in data["shops"]] == ["beach_cafe"] and data["waiting_shops"] == ["cafe"]


def test_the_screen_shows_only_guests_on_their_way_and_never_the_seed():
    state = logic.start_shift(logic.open_day(two_shops()), "cafe")
    for _ in range(20):
        state, _ = logic.tick(state)
        data = view_of(state)["guests"]
        assert len(data["walking"]) <= guests.MAX_VISIBLE_GUESTS
        assert all(g["depart"] <= data["tick"] for g in data["walking"])
        assert all(g["line"] is None or g["arrives"] <= data["tick"] for g in data["walking"])
        assert "seed" not in json.dumps(data)
    shops = {s["shop"]: s for s in data["shops"]}
    assert set(shops) == {"cafe", "beach_cafe"}
    assert sum(s["total"] for s in shops.values()) == crowd(state, shops)


REAL_SAVE = db.save  # the API's save is patched to a file per test below


def start_through_the_api(tmp_path, monkeypatch, name, body):
    path = tmp_path / name
    REAL_SAVE(logic.open_day(two_shops()), path)
    monkeypatch.setattr(app, "load_run", lambda: db.load(path))
    monkeypatch.setattr(app.db, "save", lambda state: REAL_SAVE(state, path))
    assert app.app.test_client().post("/api/shift/start", json=body).status_code == 200
    return db.load(path)


def test_a_crafted_request_cannot_send_guests(tmp_path, monkeypatch):
    plain = start_through_the_api(tmp_path, monkeypatch, "plain.db", {"shop": "cafe"})
    crafted = start_through_the_api(tmp_path, monkeypatch, "crafted.db", {
        "shop": "cafe", "guests": [{"shop": "cafe"}] * 99, "guest_shops": ["surf_shop"]})
    assert crafted == plain
    assert plain["shift"]["guest_shops"] == ["cafe", "beach_cafe"]


# ---- the places on the map -----------------------------------------------------------------


def blocked(point, colliders, radius=0.28):
    for c in colliders:
        if c["shape"] == "circle":
            if ((point[0] - c["x"]) ** 2 + (point[1] - c["y"]) ** 2) ** 0.5 < c["radius"] + radius:
                return c["id"]
            continue
        nx = min(max(point[0], c["x"]), c["x"] + c["width"])
        ny = min(max(point[1], c["y"]), c["y"] + c["height"])
        if ((point[0] - nx) ** 2 + (point[1] - ny) ** 2) ** 0.5 < radius:
            return c["id"]
    return None


def test_the_starts_and_the_lines_are_free_places_on_the_campus():
    zone, colliders = world.ZONES["campus"], world.colliders("campus")
    for weights in guests.START_WEIGHTS.values():
        assert set(weights) <= set(world.GUESTS["starts"])
    assert set(world.GUESTS["lines"]) == set(logic.SHOPS) == set(guests.CALLED)
    places = [(p["x"], p["y"]) for p in world.GUESTS["starts"].values()]
    for line in world.GUESTS["lines"].values():
        places += [(line["x"] + line["dx"] * i, line["y"] + line["dy"] * i) for i in range(6)]
    for x, y in places:
        assert zone["minX"] <= x <= zone["maxX"] and zone["minY"] <= y <= zone["maxY"]
        assert blocked((x, y), colliders) is None, (x, y)


def test_every_walk_takes_a_few_ticks_and_fits_into_a_shift():
    for start in world.GUESTS["starts"]:
        for shop in logic.SHOPS:
            assert 3 <= world.guest_walk_ticks(start, shop) < logic.SHIFT_TICKS
    assert world.world_view()["guests"] == world.GUESTS
