"""The rules of Campus Tycoon.

No screen and no database in this file: only the decisions.
All money is stored as integer cents (2.00 euro = 200) to avoid rounding errors.

Every function takes a state and returns a NEW state. The old one is never
changed, so a rejected action cannot damage the game (BRD: rejected actions
leave existing data unchanged).
"""

import copy
import random
import secrets
from decimal import Decimal, InvalidOperation
from fractions import Fraction

import world

STARTING_CASH = 10_000  # cents = 100.00 euro
LAST_DAY = 30  # length of a season in days (specs/longer-run.md)
DEMAND_AT_OR_BELOW_REF = 10
DEMAND_UP_TO_DOUBLE_REF = 5
MAX_PRICE = 100_000_000  # cents = 1,000,000 euro, far above any useful price

# The fixed catalogue: unit purchase cost and reference selling price, in cents.
CATALOGUE = {
    "coffee": {"name": "Coffee", "cost": 80, "ref_price": 200},
    "cake": {"name": "Cake", "cost": 150, "ref_price": 400},
    "bagel": {"name": "Bagel", "cost": 100, "ref_price": 300},
    "surfboard": {"name": "Surfboard rental", "cost": 650, "ref_price": 1_450},
    "wetsuit": {"name": "Wetsuit rental", "cost": 400, "ref_price": 950},
    "surf_lesson": {"name": "Surf lesson", "cost": 130, "ref_price": 400},
    "hoodie": {"name": "Hoodie", "cost": 650, "ref_price": 1_250},
    "tshirt": {"name": "T-shirt", "cost": 220, "ref_price": 540},
    "cap": {"name": "Cap", "cost": 150, "ref_price": 430},
    "beer": {"name": "Beer", "cost": 150, "ref_price": 400},
    "coke_zero": {"name": "Coke Zero", "cost": 80, "ref_price": 250},
    "sandwich": {"name": "Sandwich", "cost": 200, "ref_price": 400},
}

STAFF_PLACE_PRICE = 6_000  # cents = 60 euro, the same in every shop
STORAGE_UNITS = 100  # storeroom space per shop, checked when buying stock
COUNTER_UNITS = 20  # counter space per shop (limits refills in a shift)
FIRST_SHOP = "cafe"
MAX_CASH = 100_000_000  # cents, the most the editor can give (editor-mode)
MAX_SEED = 2**32 - 1  # new_seed() draws 32 bits
DEFAULT_SEED = 1  # only for tests and the demo; real runs draw one with new_seed()

# The weather (day-context, issue #10). weight: how often it appears, in percent.
# temp: range in whole degrees Celsius. demand_percent: the demand factor per shop in
# whole percent (100 = normal), from the roadmap's table B2. The customers use it through
# FACTORS (the price logic, specs/pricing.md).
# All numbers are placeholders to balance.
WEATHER = {
    "sun": {"name": "Sunny", "weight": 40, "temp": (22, 28),
            "demand_percent": {"cafe": 80, "surf_shop": 130, "merchandise": 100, "beach_cafe": 150}},
    "rain": {"name": "Rainy", "weight": 25, "temp": (14, 19),
             "demand_percent": {"cafe": 140, "surf_shop": 50, "merchandise": 120, "beach_cafe": 40}},
    "heat": {"name": "Hot", "weight": 20, "temp": (31, 38),
             "demand_percent": {"cafe": 60, "surf_shop": 120, "merchandise": 80, "beach_cafe": 180}},
    "storm": {"name": "Stormy", "weight": 15, "temp": (12, 17),
              "demand_percent": {"cafe": 100, "surf_shop": 20, "merchandise": 100, "beach_cafe": 20}},
}

# The outlook (issue #12): the forecast of tomorrow's weather is wrong this often, in whole
# percent. A wrong forecast shows a weather next to the real one, never any weather.
# Placeholders to balance.
OUTLOOK_MISS_PERCENT = 20
OUTLOOK_MISS = {
    "sun": ("heat", "rain"),
    "heat": ("sun",),
    "rain": ("sun", "storm"),
    "storm": ("rain",),
}
# Tips in the evening report (roadmap B2): a shop's demand factor at or above MORE_AT means
# more customers, at or below LESS_AT fewer. Placeholders to balance.
OUTLOOK_MORE_AT = 115
OUTLOOK_LESS_AT = 85
SHIFT_SHOPS = ("cafe",)  # shops where a day can be played live (shop-process: one first)
DAY_TICKS = 90  # a played day is 90 ticks, the server counts them (about 90 seconds)
SHIFT_TICKS = 90       # how long one shift lasts, counted from its start
OPEN_DAY_TICKS = 300   # how long an opened day lasts (placeholder; the shift is a part of it)
PATIENCE_TICKS = 15  # a customer leaves this many ticks after arriving

# Employees (specs/staff.md). All numbers are placeholders to balance.
# A place of a shop (bought in its window) has the job SHOPS[shop]["jobs"][place - 1].
# Per level (index 0 = level 1): refiller carries "per_tick" units from the storeroom to the
# counter each tick; seller sells one unit every "every" ticks; "wage" in cents per day.
HIRE_PRICE = 3_000  # cents = 30 euro, once per hire
EMPLOYEE_MAX_LEVEL = 3
UPGRADE_PRICES = {2: 5_000, 3: 8_000}  # cents, the price to reach that level
JOBS = {
    "refiller": {"name": "Refiller", "per_tick": (1, 2, 3), "wage": (800, 1_200, 1_800)},
    "seller": {"name": "Seller", "every": (4, 3, 2), "wage": (800, 1_200, 1_800)},
}
# Names are taken by employee id, so the same state always gives the same people.
EMPLOYEE_NAMES = ("Mia", "Leo", "Nora", "Ben", "Ines", "Tom", "Lara", "Rui")


def _window(product_offers):
    """What a shop's window sells: its extra products, then two employee places."""
    items = {
        pid: {"kind": "product", "product": pid, "price": price}
        for pid, price in product_offers
    }
    items["staff_1"] = {"kind": "staff", "place": 1, "price": STAFF_PLACE_PRICE}
    items["staff_2"] = {"kind": "staff", "place": 2, "price": STAFF_PLACE_PRICE}
    return items


# The shops (the team's list). Prices in cents. All numbers except the product names
# are placeholders to balance later. The first shop is open from the start
# (unlock_price 0); every shop starts with one product and sells more through its window.
SHOPS = {
    "cafe": {
        "name": "Cafe", "unlock_price": 0, "start_product": "coffee",
        "storage": STORAGE_UNITS, "counter": COUNTER_UNITS, "jobs": ["refiller", "seller"],
        "window": _window([("cake", 4_000), ("bagel", 3_000)]),
    },
    "beach_cafe": {
        "name": "Beach Cafe", "unlock_price": 20_000, "start_product": "beer",
        "storage": STORAGE_UNITS, "counter": COUNTER_UNITS, "jobs": ["refiller", "seller"],
        "window": _window([("coke_zero", 6_000), ("sandwich", 8_000)]),
    },
    "merchandise": {
        "name": "Merchandise", "unlock_price": 35_000, "start_product": "hoodie",
        "storage": STORAGE_UNITS, "counter": COUNTER_UNITS, "jobs": ["refiller", "seller"],
        "window": _window([("tshirt", 8_000), ("cap", 6_000)]),
    },
    "surf_shop": {
        "name": "Surf Shop", "unlock_price": 50_000, "start_product": "surfboard",
        "storage": STORAGE_UNITS, "counter": COUNTER_UNITS, "jobs": ["refiller", "seller"],
        "window": _window([("wetsuit", 12_000), ("surf_lesson", 15_000)]),
    },
}


# Shops where employees can work: all of them. SHIFT_SHOPS is where the PLAYER can play a
# shift (the live walk comes with shop-walk); the staff of the other shops work on their own.
STAFF_SHOPS = tuple(SHOPS)


def shop_product_ids(shop_id):
    """Every product a shop can ever have: its starting product and its window products."""
    shop = SHOPS[shop_id]
    return [shop["start_product"]] + [
        o["product"] for o in shop["window"].values() if o["kind"] == "product"
    ]


class RejectedAction(Exception):
    """Raised when a rule refuses an action. The message is shown to the player."""


def new_seed():
    """Draw a seed for a real run. The only place where randomness is created."""
    return secrets.randbits(32)


def new_state(seed=DEFAULT_SEED):
    """A fresh run: day 1, 100 euro, no stock, prices at the reference price.

    The state is the same every time for the same seed. The app draws a real seed with
    new_seed() when a run starts; tests and the demo mode pass their own."""
    return {
        "seed": seed,
        "day_override": None,
        "day": 1,
        "cash": STARTING_CASH,
        "stock": {pid: 0 for pid in CATALOGUE},
        "prices": {pid: item["ref_price"] for pid, item in CATALOGUE.items()},
        "shops": {sid: new_shop(sid) for sid in SHOPS},
        "shift": None,
        "employees": [],
        "employee_seq": 0,  # the last employee id given out: ids are never used twice
        "history": [],
        "badges": [],  # earned badges, {"id", "day"}, in the order earned (specs/badges.md)
        "player": world.start_player(),
    }


def new_shop(shop_id):
    """The Snack Stand is open on level 1 with its first product; the others are locked."""
    if shop_id == FIRST_SHOP:
        return {
            "unlocked": True,
            "level": 1,
            "products": [SHOPS[shop_id]["start_product"]],
            "staff_places": 0,
        }
    return {"unlocked": False, "level": 0, "products": [], "staff_places": 0}


def owned_products(state):
    """The products the player has: those of every unlocked shop, in catalogue order."""
    have = {
        pid
        for shop in state["shops"].values() if shop["unlocked"]
        for pid in shop["products"]
    }
    return [pid for pid in CATALOGUE if pid in have]


def euros_to_cents(text):
    """Turn '4', '4.5' or '4,01' into cents. Reject more than two decimals (CT R3)."""
    try:
        value = Decimal(str(text).strip().replace(",", "."))
        if not value.is_finite():
            raise RejectedAction("Enter a finite euro amount.")
        rounded = value.quantize(Decimal("0.01"))
    except InvalidOperation:
        raise RejectedAction(f"'{text}' is not a valid euro amount.")
    if value != rounded:
        raise RejectedAction("Use at most two decimal places.")
    return int(value * 100)


def fmt(cents):
    """Show cents as a euro amount, e.g. 1250 -> '€12.50'."""
    sign = "-" if cents < 0 else ""
    return f"{sign}€{abs(cents) / 100:,.2f}"


def is_finished(state):
    """After the last day of the season the run is complete (CT05)."""
    return state["day"] > LAST_DAY


def _check_product(state, product):
    if not isinstance(product, str) or product not in CATALOGUE:
        raise RejectedAction(f"Unknown product '{product}'.")
    if product not in owned_products(state):
        raise RejectedAction(f"You do not have {CATALOGUE[product]['name']} yet.")


def _counter_units(state, shop):
    """Units of a shop that stand on its counter in a running shift (they came from the storeroom
    and go back to it at the end of the shift, so they count against its space)."""
    return sum(sum(part["counter"].values()) for part in _shift_parts(state) if part["shop"] == shop)


def _check_storeroom_space(state, product, quantity):
    """The storeroom of the product's shop holds at most SHOPS[shop]["storage"] units."""
    shop = shop_of_product(product)
    held = sum(state["stock"][pid] for pid in shop_product_ids(shop)) + _counter_units(state, shop)
    room = SHOPS[shop]["storage"] - held
    if quantity > room:
        raise RejectedAction(
            f"The {SHOPS[shop]['name']} storeroom has room for only {max(room, 0)} more units.")


def buy(state, product, quantity):
    """CT02: buy stock. Cash and stock change together, or not at all."""
    _check_product(state, product)
    if is_finished(state):
        raise RejectedAction("The run is complete. Buying is closed.")
    if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0:
        raise RejectedAction("Quantity must be a positive whole number.")
    _check_storeroom_space(state, product, quantity)
    total = quantity * CATALOGUE[product]["cost"]
    if total > state["cash"]:
        raise RejectedAction(
            f"Not enough cash: {quantity} × {CATALOGUE[product]['name']} costs "
            f"{fmt(total)}, you have {fmt(state['cash'])}."
        )
    new = copy.deepcopy(state)
    new["cash"] -= total
    new["stock"][product] += quantity
    return new


def set_price(state, product, price_cents):
    """CT03: set a positive selling price."""
    _check_product(state, product)
    if is_finished(state):
        raise RejectedAction("The run is complete. Prices are locked.")
    if state.get("shift") is not None:
        raise RejectedAction("Prices are fixed while a shift is running.")
    _check_price(price_cents)
    new = copy.deepcopy(state)
    new["prices"][product] = price_cents
    return new


def _check_price(price_cents):
    """A selling price is a whole number of cents, more than 0 and not absurdly high."""
    if isinstance(price_cents, bool) or not isinstance(price_cents, int):
        raise RejectedAction("The selling price must be a whole number of cents.")
    if price_cents <= 0:
        raise RejectedAction("The selling price must be more than €0.")
    if price_cents > MAX_PRICE:
        raise RejectedAction(f"The selling price can be at most {fmt(MAX_PRICE)}.")


def _check_shop(shop):
    if not isinstance(shop, str) or shop not in SHOPS:
        raise RejectedAction(f"Unknown shop '{shop}'.")


def unlock_shop(state, shop):
    """Open a locked shop for its unlock price. It starts on level 1 with one product."""
    _check_shop(shop)
    if is_finished(state):
        raise RejectedAction("The run is complete. Shops can no longer be unlocked.")
    name = SHOPS[shop]["name"]
    if state["shops"][shop]["unlocked"]:
        raise RejectedAction(f"{name} is already unlocked.")
    price = SHOPS[shop]["unlock_price"]
    if price > state["cash"]:
        raise RejectedAction(
            f"Not enough cash: unlocking {name} costs {fmt(price)}, "
            f"you have {fmt(state['cash'])}."
        )
    new = copy.deepcopy(state)
    new["cash"] -= price
    new["shops"][shop] = {
        "unlocked": True,
        "level": 1,
        "products": [SHOPS[shop]["start_product"]],
        "staff_places": 0,
    }
    return new


def offer_name(shop, item):
    """The name of a window offer as the player reads it."""
    offer = SHOPS[shop]["window"][item]
    if offer["kind"] == "product":
        return CATALOGUE[offer["product"]]["name"]
    return f"Employee place {offer['place']}"


def _runs(state, shop):
    """Does anybody sell in this shop: the player (a shop of SHIFT_SHOPS) or a working employee."""
    return state["shops"][shop]["unlocked"] and (
        shop in SHIFT_SHOPS or any(e["shop"] == shop and e["working"] for e in state["employees"]))


def dead_end(state):
    """True when nothing can be bought or sold any more: no stock that somebody can sell (storeroom
    and counters of the shops that run) and not enough cash for one unit of the cheapest product the
    player has. Wages are paid at the end of the day, after the sales, and the player can buy stock
    in the morning: they do not make a dead end (an employee may stop for lack of money, the player
    still earns by serving the Cafe)."""
    owned = owned_products(state)
    if not owned:
        return False
    sellable = sum(state["stock"][pid] for sid in SHOPS if _runs(state, sid)
                   for pid in state["shops"][sid]["products"]) + sum(
        _counter_units(state, sid) for sid in SHOPS if state["shops"][sid]["unlocked"])
    return sellable == 0 and state["cash"] < min(CATALOGUE[pid]["cost"] for pid in owned)


def purchase_warning(state, shop, item=None):
    """A warning for a purchase (a window offer, or the unlock of the shop when item is None) that
    would leave the player in a dead end, else None. Only a warning: the purchase stays allowed,
    and a purchase that is refused anyway (cash, order) has none."""
    price = SHOPS[shop]["unlock_price"] if item is None else SHOPS[shop]["window"].get(item, {}).get("price")
    owned = owned_products(state)
    # cash enough for a unit of the cheapest product afterwards: no dead end, no copy of the state
    if price is None or (owned and state["cash"] - price >= min(CATALOGUE[pid]["cost"] for pid in owned)):
        return None
    try:
        after = unlock_shop(state, shop) if item is None else buy_upgrade(state, shop, item)
    except RejectedAction:
        return None
    if not dead_end(after):
        return None
    return (f"After this you have {fmt(after['cash'])} and nothing in stock, so you could not buy "
            "any stock. Keep some cash for stock.")


def shop_hint(state, shop):
    """What the player should know about a shop that sells nothing on its own: the player can play
    a shift only in SHIFT_SHOPS, so every other shop sells only through its employees. None when
    the shop is fine (or is played by the player)."""
    _check_shop(shop)
    if shop in SHIFT_SHOPS:
        return None
    entry = state["shops"][shop]
    if entry["unlocked"] and any(e["shop"] == shop and e["working"] for e in state["employees"]):
        return None
    if entry["unlocked"] and entry["staff_places"] > 0:
        return ("Nobody works in this shop: the place is free, or the employee stopped for lack of "
                "money for the wage. It earns nothing until somebody works.")
    return ("This shop sells only through employees: you cannot play a shift here yet. "
            "Buy an employee place first, or it earns nothing.")


def shop_offers(state, shop):
    """What a shop's window offers right now. The rules answer, so no screen has to guess:
    `bought`, `available` (employee place 2 waits for place 1) and `affordable` (cash)."""
    _check_shop(shop)
    entry = state["shops"][shop]
    offers = []
    for item_id, offer in SHOPS[shop]["window"].items():
        if offer["kind"] == "product":
            bought = offer["product"] in entry["products"]
            available = True
        else:
            bought = entry["staff_places"] >= offer["place"]
            available = entry["staff_places"] >= offer["place"] - 1
        offers.append({
            "id": item_id,
            "kind": offer["kind"],
            "name": offer_name(shop, item_id),
            "price": offer["price"],
            "bought": bought,
            "available": available,
            "affordable": offer["price"] <= state["cash"],
            "warning": None if bought or not available else purchase_warning(state, shop, item_id),
        })
    return offers


def buy_upgrade(state, shop, item):
    """Buy one thing from a shop's window: a product or an employee place.

    Every purchase raises the shop's level by 1. Employee places are bought in order
    (staff_1, then staff_2) so that staff_places always counts what was bought.
    """
    _check_shop(shop)
    window = SHOPS[shop]["window"]
    if not isinstance(item, str) or item not in window:
        raise RejectedAction(f"{SHOPS[shop]['name']} does not offer '{item}'.")
    if is_finished(state):
        raise RejectedAction("The run is complete. The window is closed.")
    entry = state["shops"][shop]
    if not entry["unlocked"]:
        raise RejectedAction(f"{SHOPS[shop]['name']} is not unlocked yet.")
    offer = window[item]
    if offer["kind"] == "product":
        if offer["product"] in entry["products"]:
            raise RejectedAction(f"{CATALOGUE[offer['product']]['name']} is already bought.")
    else:
        if entry["staff_places"] >= offer["place"]:
            raise RejectedAction("That employee place is already bought.")
        if entry["staff_places"] < offer["place"] - 1:
            raise RejectedAction("Buy the first employee place before the second.")
    if offer["price"] > state["cash"]:
        raise RejectedAction(
            f"Not enough cash: this costs {fmt(offer['price'])}, "
            f"you have {fmt(state['cash'])}."
        )
    new = copy.deepcopy(state)
    new["cash"] -= offer["price"]
    new_entry = new["shops"][shop]
    if offer["kind"] == "product":
        new_entry["products"].append(offer["product"])
    else:
        new_entry["staff_places"] += 1
        # the bought place comes with its employee (if the shop has a job for that place)
        if offer["place"] <= len(SHOPS[shop]["jobs"]):
            _add_employee(new, shop, offer["place"])
    new_entry["level"] += 1
    # only a new employee can start a crew on an open day, not a new product
    return _open_staffed_shift(new) if offer["kind"] == "staff" else new


def _add_employee(new, shop, place):
    """Put a new level 1 employee on a place. The job comes from the shop's data."""
    employee_id = max(new.get("employee_seq", 0), max((e["id"] for e in new["employees"]), default=0)) + 1
    new["employee_seq"] = employee_id
    new["employees"].append({
        "id": employee_id, "name": EMPLOYEE_NAMES[(employee_id - 1) % len(EMPLOYEE_NAMES)],
        "shop": shop, "place": place, "job": SHOPS[shop]["jobs"][place - 1],
        "level": 1, "working": True,
    })


def employee_wage(employee):
    """The daily wage of one employee in cents, from the job and the level."""
    return JOBS[employee["job"]]["wage"][employee["level"] - 1]


def _check_whole(value, what):
    if isinstance(value, bool) or not isinstance(value, int):
        raise RejectedAction(f"{what} must be a whole number.")


def _find_employee(state, employee_id):
    _check_whole(employee_id, "The employee id")
    for employee in state["employees"]:
        if employee["id"] == employee_id:
            return employee
    raise RejectedAction(f"Unknown employee '{employee_id}'.")


def hire(state, shop, place):
    """Hire an employee on a free bought place of a shop (a place that was emptied by
    dismissing someone: buying a place hires its employee already)."""
    _check_shop(shop)
    if is_finished(state):
        raise RejectedAction("The run is complete. Nobody can be hired.")
    name = SHOPS[shop]["name"]
    if not state["shops"][shop]["unlocked"]:
        raise RejectedAction(f"The {name} is not unlocked.")
    _check_whole(place, "The place")
    jobs = SHOPS[shop]["jobs"]
    if place < 1 or place > state["shops"][shop]["staff_places"] or place > len(jobs):
        raise RejectedAction(f"The {name} has no employee place {place} yet.")
    if any(e["shop"] == shop and e["place"] == place for e in state["employees"]):
        raise RejectedAction(f"Place {place} of the {name} is already taken.")
    if HIRE_PRICE > state["cash"]:
        raise RejectedAction(
            f"Not enough cash: hiring costs {fmt(HIRE_PRICE)}, you have {fmt(state['cash'])}.")
    new = copy.deepcopy(state)
    new["cash"] -= HIRE_PRICE
    _add_employee(new, shop, place)
    return _open_staffed_shift(new)


def upgrade_employee(state, employee_id):
    """Raise an employee by one level. They work faster and cost a higher wage."""
    employee = _find_employee(state, employee_id)
    if is_finished(state):
        raise RejectedAction("The run is complete. Nobody can be upgraded.")
    if employee["level"] >= EMPLOYEE_MAX_LEVEL:
        raise RejectedAction(f"{employee['name']} is already on the highest level.")
    price = UPGRADE_PRICES[employee["level"] + 1]
    if price > state["cash"]:
        raise RejectedAction(
            f"Not enough cash: the upgrade costs {fmt(price)}, you have {fmt(state['cash'])}.")
    new = copy.deepcopy(state)
    new["cash"] -= price
    _find_employee(new, employee_id)["level"] += 1
    return new


def fire_employee(state, employee_id):
    """Dismiss an employee. The place stays bought and is free again; nothing is refunded."""
    employee = _find_employee(state, employee_id)
    if is_finished(state):
        raise RejectedAction("The run is complete. Nobody can be dismissed.")
    new = copy.deepcopy(state)
    new["employees"] = [e for e in new["employees"] if e["id"] != employee["id"]]
    return new


def demand(price_cents, ref_price_cents):
    """CT R1: 10 units up to the reference price, 5 up to twice it, 0 above.

    The solo project's rule. The game no longer uses it (customers_for does, specs/pricing.md);
    it stays because tests/test_first_feature.py pins it."""
    if price_cents <= ref_price_cents:
        return DEMAND_AT_OR_BELOW_REF
    if price_cents <= 2 * ref_price_cents:
        return DEMAND_UP_TO_DOUBLE_REF
    return 0


def trade_day(state):
    """CT04: run one trading day. Returns (new_state, result_of_the_day)."""
    if is_finished(state):
        raise RejectedAction("The run is complete. Trading is closed.")
    if state.get("shift") is not None:
        raise RejectedAction("A shift is running. Finish the day in the shop first.")

    new = copy.deepcopy(state)
    lines = []
    for pid in owned_products(new):
        item = CATALOGUE[pid]
        price = new["prices"][pid]
        wanted = customers_today(state, pid)
        sold = min(wanted, new["stock"][pid])  # CT R2: stock limits sales
        revenue = sold * price
        cogs = sold * item["cost"]  # CT R4: purchase cost of the units sold
        new["stock"][pid] -= sold
        new["cash"] += revenue  # purchases were already paid when buying
        lines.append({
            "product": pid,
            "price": price,
            "demand": wanted,
            "sold": sold,
            "revenue": revenue,
            "cogs": cogs,
            "gross_profit": revenue - cogs,
        })

    result = {
        "day": new["day"],
        "lines": lines,
        "revenue": sum(line["revenue"] for line in lines),
        "cogs": sum(line["cogs"] for line in lines),
        "gross_profit": sum(line["gross_profit"] for line in lines),
        "cash_after": new["cash"],
        "played": False,  # nobody stood in a shop: the day was traded as a whole
    }
    new["history"].append(result)
    award_badges(new, result)
    new["day"] += 1  # CT R5: exactly one day per trade action
    return new, result


def _override_weather(override):
    """The weather an override fixes, or None. An unknown saved id must not crash every
    request: it counts as no override, so the seed's roll is used."""
    if isinstance(override, dict) and isinstance(override.get("weather"), str) \
            and override["weather"] in WEATHER:
        return override["weather"]
    return None


def _roll_weather(rng, override):
    """The weather of a day: the override if it is valid, otherwise rolled by the weights.
    Always rolls first, so the generator is at the same point for the temperature."""
    rolled = rng.choices(list(WEATHER), weights=[w["weight"] for w in WEATHER.values()])[0]
    return _override_weather(override) or rolled


def make_day_context(seed, day, override=None):
    """The weather of one day, from the seed and the day only (same input, same answer).

    override: None, or {"weather": id} to fix the weather (demo mode); the temperature is
    still rolled from the seed. Returns {"day", "weather", "temperature", "demand_percent"}."""
    rng = random.Random(f"{seed}:{day}")
    weather = _roll_weather(rng, override)
    low, high = WEATHER[weather]["temp"]
    return {
        "day": day,
        "weather": weather,
        "temperature": rng.randint(low, high),
        "demand_percent": dict(WEATHER[weather]["demand_percent"]),
    }


def day_context(state):
    """Today's context of the run."""
    return make_day_context(state["seed"], state["day"], state["day_override"])


def make_outlook(seed, day, override=None):
    """The forecast for `day`, from the seed and the day only (same input, same answer).

    Rolls with its own generator, so the real weather of make_day_context stays the same.
    With an override the forecast is always right, as long as the override stays set.
    Returns {"day", "weather", "temp_range"}: the weather the forecast shows and that
    weather's range in whole degrees Celsius."""
    real = _roll_weather(random.Random(f"{seed}:{day}"), override)
    shown = real
    rng = random.Random(f"{seed}:{day}:outlook")
    misses = rng.randrange(100) < OUTLOOK_MISS_PERCENT
    fixed = _override_weather(override) is not None
    if misses and not fixed:
        shown = rng.choice(OUTLOOK_MISS[real])
    return {"day": day, "weather": shown, "temp_range": WEATHER[shown]["temp"],
            "miss_percent": 0 if fixed else OUTLOOK_MISS_PERCENT}


def outlook(state):
    """The forecast for the next day whose real weather is not shown yet: today while the
    day is not opened, tomorrow while it is open. None when there is no such day."""
    day = state["day"] + (1 if state.get("shift") is not None else 0)
    if day > LAST_DAY:
        return None
    return make_outlook(state["seed"], day, state["day_override"])


def outlook_tips(state, forecast=None):
    """Per unlocked shop: the forecast's demand factor and whether to expect more, fewer or
    the usual customers. Empty without a forecast. Advice about stock only, no prices.

    forecast: outlook(state) if the caller has it already, so it is not rolled twice."""
    forecast = forecast or outlook(state)
    if forecast is None:
        return []
    factors = WEATHER[forecast["weather"]]["demand_percent"]
    tips = []
    for sid in SHOPS:
        if not state["shops"][sid]["unlocked"]:
            continue
        percent = factors[sid]
        if percent >= OUTLOOK_MORE_AT:
            advice = "more"
        elif percent <= OUTLOOK_LESS_AT:
            advice = "less"
        else:
            advice = "normal"
        tips.append({"shop": sid, "percent": percent, "advice": advice})
    return tips


def known_state(state):
    """The state as the player may reason about it: before the day is opened the weather is
    only the forecast, so a number shown from this state cannot reveal the real weather.

    For showing only (the screens' customers, the overview, the preview); the rules that book
    a day always use the real state. An open day or a finished run returns the state itself."""
    forecast = None if day_is_open(state) else outlook(state)
    if forecast is None:
        return state
    # a shallow copy is enough: the readers of the shown numbers copy before they change anything
    return {**state, "day_override": {"weather": forecast["weather"]}}


def day_is_open(state):
    """True while the day is open (the clock runs). The one place that says so."""
    return state.get("shift") is not None


def set_day_override(state, weather):
    """Fix the weather (a demo switch) or clear it with None."""
    if weather is not None and (not isinstance(weather, str) or weather not in WEATHER):
        raise RejectedAction(f"Unknown weather '{weather}'.")
    new = copy.deepcopy(state)
    new["day_override"] = None if weather is None else {"weather": weather}
    return new


# --- Editor mode (specs/editor-mode.md): rules for the dev tools. The server decides
# whether the editor is on; these functions only check the values and never change a state
# they refuse. ---

def _whole(value, low, high, what):
    """A whole number (no bool, no float) from low to high, or a refusal."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise RejectedAction(f"{what} must be a whole number.")
    if not low <= value <= high:
        raise RejectedAction(f"{what} must be from {low} to {high}.")
    return value


def check_seed(seed):
    return _whole(seed, 0, MAX_SEED, "The seed")


def _check_no_open_day(state):
    if state.get("shift") is not None:
        raise RejectedAction("A day is open. Finish or skip it first.")


def editor_cash(state, mode, cents):
    """Set the cash to an amount ("set") or add to it ("add"), in whole cents."""
    if mode not in ("set", "add"):
        raise RejectedAction("The mode must be 'set' or 'add'.")
    if isinstance(cents, bool) or not isinstance(cents, int):
        raise RejectedAction("The amount must be a whole number of cents.")
    total = cents if mode == "set" else state["cash"] + cents
    if not 0 <= total <= MAX_CASH:
        raise RejectedAction(f"The cash must stay between {fmt(0)} and {fmt(MAX_CASH)}.")
    new = copy.deepcopy(state)
    new["cash"] = total
    return new


def editor_skip_days(state, days):
    """Let several days pass with trade_day (current prices and stock). All or nothing."""
    if is_finished(state):
        raise RejectedAction("The run is complete. Trading is closed.")
    _check_no_open_day(state)
    _whole(days, 1, LAST_DAY - state["day"] + 1, "The number of days")
    for _ in range(days):
        state, _result = trade_day(state)
    return state


def shop_at_level(shop_id, level):
    """The entry of a shop on a level: 0 is locked, level n has the start product and the
    first n - 1 offers of its window (in window order)."""
    _check_shop(shop_id)
    offers = list(SHOPS[shop_id]["window"].values())
    _whole(level, 0, 1 + len(offers), "The level")
    if level == 0:
        return {"unlocked": False, "level": 0, "products": [], "staff_places": 0}
    bought = offers[:level - 1]
    return {
        "unlocked": True,
        "level": level,
        "products": [SHOPS[shop_id]["start_product"]]
                    + [o["product"] for o in bought if o["kind"] == "product"],
        "staff_places": sum(1 for o in bought if o["kind"] == "staff"),
    }


def _check_shop_entry(shop_id, entry):
    """A shop entry that could have come from play, or a refusal. Returns the clean entry."""
    if isinstance(entry, dict) and set(entry) == {"level"}:
        return shop_at_level(shop_id, entry["level"])
    keys = {"unlocked", "level", "products", "staff_places"}
    if not isinstance(entry, dict) or set(entry) != keys:
        raise RejectedAction(f"A shop needs exactly: {', '.join(sorted(keys))} (or just a level).")
    if not isinstance(entry["unlocked"], bool):
        raise RejectedAction("'unlocked' must be true or false.")
    products = entry["products"]
    if not isinstance(products, list) or any(not isinstance(p, str) for p in products) \
            or len(set(products)) != len(products):
        raise RejectedAction("'products' must be a list of different product ids.")
    allowed = shop_product_ids(shop_id)
    if any(p not in allowed for p in products):
        raise RejectedAction(f"{SHOPS[shop_id]['name']} does not sell those products.")
    _whole(entry["staff_places"], 0, 2, "The employee places")
    _whole(entry["level"], 0, 1 + len(SHOPS[shop_id]["window"]), "The level")
    if entry["unlocked"]:
        if SHOPS[shop_id]["start_product"] not in products:
            raise RejectedAction("An unlocked shop always has its first product.")
        if entry["level"] != len(products) + entry["staff_places"]:
            raise RejectedAction("The level must equal the products plus the employee places.")
    elif entry["level"] or products or entry["staff_places"]:
        raise RejectedAction("A locked shop has level 0 and nothing in it.")
    return {"unlocked": entry["unlocked"], "level": entry["level"],
            "products": [p for p in allowed if p in products],
            "staff_places": entry["staff_places"]}


def _check_player(player):
    if not isinstance(player, dict) or set(player) != {"zone", "x", "y"}:
        raise RejectedAction("A position needs zone, x and y.")
    return move_player({"player": None}, player["zone"], player["x"], player["y"])["player"]


def editor_set_state(state, patch):
    """Set any part of the run from a patch. Everything is checked first; a refused patch
    changes nothing. Keys not in the patch stay as they are.

    The keys: day, cash, seed, day_override, stock, prices, shops, player, badges. Setting an
    earlier day cuts the history and the badges to the days before it. Refused while a day
    is open."""
    keys = {"day", "cash", "seed", "day_override", "stock", "prices", "shops", "player", "badges"}
    if not isinstance(patch, dict) or not patch:
        raise RejectedAction("The patch must be a dictionary with at least one field.")
    unknown = sorted(str(k) for k in patch if k not in keys)
    if unknown:
        raise RejectedAction(f"Unknown field: {', '.join(unknown)}.")
    _check_no_open_day(state)
    new = copy.deepcopy(state)
    if "day" in patch:
        new["day"] = _whole(patch["day"], 1, LAST_DAY + 1, "The day")
        new["history"] = [r for r in new["history"] if r["day"] < new["day"]]
        new["badges"] = [b for b in new.get("badges", []) if b["day"] < new["day"]]
    if "cash" in patch:
        new["cash"] = _whole(patch["cash"], 0, MAX_CASH, "The cash")
    if "seed" in patch:
        new["seed"] = check_seed(patch["seed"])
    if "day_override" in patch:
        override = patch["day_override"]
        if override is None:
            weather = None
        elif isinstance(override, dict) and set(override) == {"weather"}:
            weather = override["weather"]
        else:
            raise RejectedAction("'day_override' must be null or {\"weather\": id}.")
        new["day_override"] = set_day_override(new, weather)["day_override"]
    for field in ("stock", "prices"):
        if field in patch:
            if not isinstance(patch[field], dict):
                raise RejectedAction(f"'{field}' must map products to numbers.")
            for pid, value in patch[field].items():
                if not isinstance(pid, str) or pid not in CATALOGUE:
                    raise RejectedAction(f"Unknown product '{pid}'.")
                if field == "prices":
                    new[field][pid] = _whole(value, 1, MAX_PRICE, f"The price of {pid}")
                else:
                    new[field][pid] = _whole(value, 0, STORAGE_UNITS, f"The stock of {pid}")
    if "shops" in patch:
        if not isinstance(patch["shops"], dict):
            raise RejectedAction("'shops' must map shop ids to entries.")
        for sid, entry in patch["shops"].items():
            _check_shop(sid)
            new["shops"][sid] = _check_shop_entry(sid, entry)
            if sid == FIRST_SHOP and not new["shops"][sid]["unlocked"]:
                raise RejectedAction(f"{SHOPS[sid]['name']} is open from the start and stays open.")
        # an employee needs the place he works on: those whose place is gone are dismissed
        new["employees"] = [e for e in new["employees"]
                            if new["shops"][e["shop"]]["unlocked"]
                            and e["place"] <= new["shops"][e["shop"]]["staff_places"]]
    if "player" in patch:
        new["player"] = _check_player(patch["player"])
    if "badges" in patch:
        new["badges"] = _check_badges(patch["badges"], new["day"])
    # the storeroom limit is per shop: check it for the stock as a whole
    touched = {sid for sid in SHOPS for pid in patch.get("stock", {})
               if pid in shop_product_ids(sid)}
    for sid in touched:
        if sum(new["stock"][p] for p in shop_product_ids(sid)) > SHOPS[sid]["storage"]:
            raise RejectedAction(f"The {SHOPS[sid]['name']} storeroom holds at most "
                                 f"{SHOPS[sid]['storage']} units.")
    return new




# ---- customers: the price logic (specs/pricing.md, issue #38) ----------------------------
# Two kinds of customers react to the price in different ways, every shop has its own mix of
# them, and the day's conditions (FACTORS) move each kind. A curve says how much of a
# segment's base amount still buys at a price given in percent of the reference price, in
# percent; straight lines between the points, flat below the first point, 0 above the last.
# All numbers below are placeholders to balance. Everything is calculated with exact fractions.
SEGMENTS = {
    "students": {"name": "Students", "curve": (
        (50, 170), (75, 135), (100, 100), (125, 65), (150, 28), (175, 8), (200, 0))},
    "visitors": {"name": "Visitors", "curve": (
        (50, 115), (75, 107), (100, 100), (125, 95), (150, 85), (175, 70), (200, 50),
        (225, 20), (250, 0))},
}
# Customers per product and day at the reference price on a neutral day, per shop and segment.
# Every shop adds up to BASE_CUSTOMERS, so nothing changes at the reference price.
BASE_CUSTOMERS = 10
SHOP_MIX = {
    "cafe": {"students": 8, "visitors": 2},
    "beach_cafe": {"students": 6, "visitors": 4},
    "merchandise": {"students": 5, "visitors": 5},
    "surf_shop": {"students": 3, "visitors": 7},
}
DEFAULT_MIX = {"students": 6, "visitors": 4}  # for a call without a shop
MAX_CUSTOMERS = 30  # most customers of one product in one shift or day: a safety net
CURVE_POINTS = sorted({x for segment in SEGMENTS.values() for x, _ in segment["curve"]})

# Visitors react to the weather more than students (in percent, on top of the shop's weather
# percent). Storm is 100: the shop table already holds the whole storm effect.
VISITOR_WEATHER = {"sun": 130, "rain": 70, "heat": 120, "storm": 100}


def _weather_factor(state, shop):
    """Today's weather: the shop's percent for both segments, extra for the visitors."""
    context = day_context(state)
    percent = context["demand_percent"][shop]
    visitors = Fraction(percent * VISITOR_WEATHER[context["weather"]], 100)
    return f"Weather: {WEATHER[context['weather']]['name']}", {"students": percent, "visitors": visitors}


# The day's conditions. Each factor is a function (state, shop) -> (label, {segment: percent}).
# Percents of all factors multiply; a segment a factor does not name stays at 100.
# Weather is the first; events, trend, popularity and outfit add theirs here.
FACTORS = (_weather_factor,)


def _round_half_up(value):
    return int(value + Fraction(1, 2))


def _curve_percent(curve, price_percent):
    """How many percent of its base a segment buys at this price (percent of the reference)."""
    if price_percent <= curve[0][0]:
        return Fraction(curve[0][1])
    for (x0, y0), (x1, y1) in zip(curve, curve[1:]):
        if price_percent <= x1:
            return y0 + Fraction(y1 - y0) * (price_percent - x0) / (x1 - x0)
    return Fraction(0)


def segment_amounts(price_cents, ref_price_cents, mix=DEFAULT_MIX, percents=None):
    """The exact (not rounded) customers of each segment: base x curve x the day's percent."""
    if price_cents <= 0 or ref_price_cents <= 0:
        raise ValueError("price and reference price must be more than 0")
    x = Fraction(price_cents * 100, ref_price_cents)
    amounts = {}
    for segment, base in mix.items():
        percent = Fraction((percents or {}).get(segment, 100))
        if percent < 0:
            raise ValueError("a percent cannot be negative")
        amounts[segment] = base * _curve_percent(SEGMENTS[segment]["curve"], x) / 100 * percent / 100
    return amounts


def customers_for(price_cents, ref_price_cents, mix=DEFAULT_MIX, percents=None):
    """How many customers want one product on a played day.

    The one place that turns a price into customers (price curves of the segments, the shop's
    mix, the day's percents per segment). Whole number, half up, at most MAX_CUSTOMERS."""
    total = sum(segment_amounts(price_cents, ref_price_cents, mix, percents).values())
    return min(MAX_CUSTOMERS, _round_half_up(total))


def shop_of_product(product):
    return next(sid for sid in SHOPS if product in shop_product_ids(sid))


def _active_factors(state, shop):
    """The factors of today that change something: [(label, {segment: percent})]."""
    out = []
    for factor in FACTORS:
        label, percents = factor(state, shop)
        if any(Fraction(p) != 100 for p in percents.values()):
            out.append((label, percents))
    return out


def _combine(combined, percents):
    for segment, percent in percents.items():
        if segment in combined:
            combined[segment] = combined[segment] * Fraction(percent) / 100
    return combined


def segment_percents(state, shop):
    """Today's combined percent per segment for a shop (100 = normal)."""
    combined = {segment: Fraction(100) for segment in SEGMENTS}
    for _label, percents in _active_factors(state, shop):
        _combine(combined, percents)
    return combined


def customers_today(state, product):
    """Customers of one product today at its saved price: shift, trade_day, overview, screen."""
    shop = shop_of_product(product)
    return customers_for(state["prices"][product], CATALOGUE[product]["ref_price"],
                         SHOP_MIX[shop], segment_percents(state, shop))


def _split(amounts, total):
    """Spread a whole total over the segments (largest remainder, ties to the first)."""
    weight = sum(amounts.values())
    if weight == 0:
        return {segment: 0 for segment in amounts}
    exact = {segment: a * total / weight for segment, a in amounts.items()}
    split = {segment: int(value) for segment, value in exact.items()}
    order = sorted(amounts, key=lambda sg: (-(exact[sg] - split[sg]), list(amounts).index(sg)))
    for segment in order[:total - sum(split.values())]:
        split[segment] += 1
    return split


def customer_breakdown(state, product, price_cents=None):
    """Why a product has the customers it has today, step by step, in whole numbers.

    Each step is the running total after it (rounded from the exact value); the last one is
    exactly customers_today. price_cents tries another price without saving it."""
    item = CATALOGUE[product]
    shop = shop_of_product(product)
    mix = SHOP_MIX[shop]
    price = state["prices"][product] if price_cents is None else price_cents
    ref = item["ref_price"]
    price_percent = _round_half_up(Fraction(price * 100, ref))

    amounts = segment_amounts(price, ref, mix)
    steps = [{"id": "price", "name": f"Your price ({price_percent} % of the reference price)",
              "customers": _round_half_up(sum(amounts.values())),
              "split": _split(amounts, _round_half_up(sum(amounts.values())))}]
    combined = {segment: Fraction(100) for segment in mix}
    for label, percents in _active_factors(state, shop):
        amounts = segment_amounts(price, ref, mix, _combine(combined, percents))
        total = _round_half_up(sum(amounts.values()))
        steps.append({"id": "factor", "name": label, "customers": total,
                      "split": _split(amounts, total)})
    total = _round_half_up(sum(amounts.values()))
    customers = min(MAX_CUSTOMERS, total)
    if customers < total:
        steps.append({"id": "cap", "name": f"At most {MAX_CUSTOMERS} customers of one product",
                      "customers": customers, "split": _split(amounts, customers)})
    x = Fraction(price * 100, ref)
    sellable = min(customers, state["stock"][product])
    return {
        "product": product, "shop": shop, "price": price, "price_percent": price_percent,
        "base": sum(mix.values()), "steps": steps,
        "keep": {segment: _round_half_up(_curve_percent(SEGMENTS[segment]["curve"], x))
                 for segment in mix},
        "customers": customers, "split": steps[-1]["split"],
        "unit_profit": price - item["cost"], "sellable": sellable,
        "expected_profit": sellable * (price - item["cost"]),
    }


def price_preview(state, product, price_cents):
    """The customers a price would bring today, without saving it (the screen's live preview)."""
    _check_product(state, product)
    if is_finished(state):
        raise RejectedAction("The run is complete. Prices are locked.")
    _check_price(price_cents)
    return customer_breakdown(state, product, price_cents)


def shop_price_curve(shop):
    """A shop's curve on a neutral day for drawing the meter: [[price %, hundredths of a customer]]."""
    mix = SHOP_MIX[shop]
    return [[x, _round_half_up(sum(segment_amounts(x, 100, mix).values()) * 100)]
            for x in CURVE_POINTS]


def _check_open_shift(state):
    """The open shift, or a refusal. Also refuses everything after the last day."""
    if is_finished(state):
        raise RejectedAction("The run is complete. The shop is closed.")
    shift = state.get("shift")
    if shift is None:
        raise RejectedAction("No shift is running. Start the day in a shop first.")
    return shift


def _shift_running(shift):
    """True while somebody works: the shift has started and is not over yet."""
    return shift["shop"] is not None and not shift.get("over")


def _check_shift_product(state, shift, product):
    if shift["shop"] is None:
        raise RejectedAction("Start your shift in a shop first.")
    if not _shift_running(shift):
        raise RejectedAction("Your shift is over. The day is still running.")
    if not isinstance(product, str) or product not in CATALOGUE:
        raise RejectedAction(f"Unknown product '{product}'.")
    if product not in shift["counter"]:  # the products the shift started with
        raise RejectedAction(f"{CATALOGUE[product]['name']} is not sold in this shop.")


def _open_staffed_shift(new):
    """On an open day, every shop with a working employee and no shift yet opens a staffed
    shift by itself (specs/staff.md), if a whole shift still fits into the rest of the day.

    The state holds the player's shift in state["shift"] (one shop, the first of SHIFT_SHOPS
    when it is free) and every other staffed shop in state["shift"]["extra"][shop]: the same
    fields, run by the same rules, only by their employees."""
    shift = new.get("shift")
    if shift is None or shift["day_end"] - shift["tick"] < SHIFT_TICKS:
        return new
    for shop in STAFF_SHOPS:
        if (not new["shops"][shop]["unlocked"] or shop == shift["shop"]
                or shop in shift.get("extra", {})
                or not any(e["shop"] == shop and e["working"] for e in new["employees"])):
            continue
        if shift["shop"] is None and shop in SHIFT_SHOPS:  # the player's own shift is free
            extra = shift.get("extra")
            new = start_shift(new, shop)
            new["shift"]["staffed"] = True
            if extra:
                new["shift"]["extra"] = extra
            shift = new["shift"]
        else:
            sub = _new_shift(new, shop, shift["tick"], shift["day_end"])
            sub["staffed"] = True
            shift.setdefault("extra", {})[shop] = sub
    return new


def open_day(state):
    """Open the day: the clock starts running. Nobody is serving yet. The player starts a
    shift in a shop while the day runs (start_shift), or lets the day pass and earns nothing."""
    if is_finished(state):
        raise RejectedAction("The run is complete. The shop is closed.")
    if state.get("shift") is not None:
        raise RejectedAction("The day is already open.")
    new = copy.deepcopy(state)
    new["shift"] = {"shop": None, "tick": 0, "counter": {}, "queue": [],
                    "planned": {}, "sold": {}, "lost": 0,
                    "day_end": OPEN_DAY_TICKS, "shift_end": None, "over": False}
    return _open_staffed_shift(new)


def start_shift(state, shop):
    """Start the shift in a shop. Builds the queue of customers, no randomness.

    Works on the open day (the shift clock and the customers start now, and the whole shift
    must fit into the rest of the day) or, without an open day, opens both together."""
    if is_finished(state):
        raise RejectedAction("The run is complete. The shop is closed.")
    _check_shop(shop)
    if shop not in SHIFT_SHOPS:
        raise RejectedAction(f"A day cannot be played in the {SHOPS[shop]['name']} yet.")
    if not state["shops"][shop]["unlocked"]:
        raise RejectedAction(f"The {SHOPS[shop]['name']} is not unlocked.")
    open_shift = state.get("shift")
    if open_shift is not None and open_shift["shop"] is not None:
        raise RejectedAction("A shift is already running.")
    start = open_shift["tick"] if open_shift else 0  # the shift clock starts now
    if open_shift and open_shift["day_end"] - start < SHIFT_TICKS:
        raise RejectedAction("Too late for a shift: the day ends before it could be played.")
    new = copy.deepcopy(state)
    new["shift"] = _new_shift(state, shop, start, open_shift["day_end"] if open_shift else DAY_TICKS)
    if open_shift and open_shift.get("extra"):  # the staffed shops of this day keep running
        new["shift"]["extra"] = copy.deepcopy(open_shift["extra"])
    return new


def _new_shift(state, shop, start, day_end):
    """A shift of one shop from tick `start`: the counter, the queue of customers (no
    randomness) and the clock. Used for the player's shift and for the staffed shops."""
    products = state["shops"][shop]["products"]
    planned, queue = {}, []
    for k, pid in enumerate(products):
        count = customers_today(state, pid)
        planned[pid] = count
        for j in range(count):
            arrives = start + min((j * SHIFT_TICKS) // count + k, SHIFT_TICKS - 1)
            queue.append({"product": pid, "arrives": arrives,
                          "patience_until": arrives + PATIENCE_TICKS})
    queue.sort(key=lambda c: c["arrives"])  # stable: products keep their order per tick
    return {
        "shop": shop, "tick": start,
        "counter": {pid: 0 for pid in products},
        "queue": queue, "planned": planned,
        "sold": {pid: 0 for pid in products}, "lost": 0,
        "day_end": day_end, "shift_end": start + SHIFT_TICKS, "over": False,
    }


def _check_refill(state, product, quantity):
    """All the checks of a refill, or a refusal. Changes nothing."""
    shift = _check_open_shift(state)
    _check_shift_product(state, shift, product)
    if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0:
        raise RejectedAction("Quantity must be a positive whole number.")
    name = CATALOGUE[product]["name"]
    if quantity > state["stock"][product]:
        raise RejectedAction(
            f"The storeroom holds only {state['stock'][product]} × {name}.")
    space = SHOPS[shift["shop"]]["counter"] - sum(shift["counter"].values())
    if quantity > space:
        raise RejectedAction(f"The counter has room for only {space} more units.")


def _carry(state, product, quantity):
    """Move units from the storeroom to the counter in this very state (already checked)."""
    state["stock"][product] -= quantity
    state["shift"]["counter"][product] += quantity


def refill(state, product, quantity):
    """Carry units from the storeroom to the counter. The counter space is limited."""
    _check_refill(state, product, quantity)
    new = copy.deepcopy(state)
    _carry(new, product, quantity)
    return new


def _check_sale(state, product):
    """All the checks of a sale. Returns the index of the customer who is served."""
    shift = _check_open_shift(state)
    _check_shift_product(state, shift, product)
    name = CATALOGUE[product]["name"]
    if shift["counter"][product] <= 0:
        raise RejectedAction(f"There is no {name} on the counter.")
    tick = shift["tick"]
    for i, customer in enumerate(shift["queue"]):
        if (customer["product"] == product
                and customer["arrives"] <= tick < customer["patience_until"]):
            return i
    raise RejectedAction(f"Nobody is waiting for {name}.")


def _serve(state, i, product):
    """Sell one unit to customer i of the queue in this very state (already checked)."""
    state["shift"]["queue"].pop(i)
    state["shift"]["counter"][product] -= 1
    state["shift"]["sold"][product] += 1
    state["cash"] += state["prices"][product]


def sell(state, product):
    """Sell one unit from the counter to the first customer waiting for it."""
    i = _check_sale(state, product)
    new = copy.deepcopy(state)
    _serve(new, i, product)
    return new


def tick(state):
    """One tick of the day. Impatient customers leave; the last tick closes the shift.

    Returns (new_state, result) where result is the day's result when the shift closed,
    otherwise None."""
    _check_open_shift(state)
    new = copy.deepcopy(state)
    new["shift"]["tick"] += 1
    _employees_work(new)  # same rules as the player's refill and sell
    shift = new["shift"]
    _expire_customers(shift)
    _tick_staffed_shops(new)
    if _shift_running(shift) and shift["tick"] >= shift.get("shift_end", DAY_TICKS):
        _end_shift(new)
    if shift["tick"] < shift.get("day_end", DAY_TICKS):
        return new, None
    return _close_shift(new)


def _expire_customers(shift):
    """Customers past their patience go home."""
    waiting = []
    for customer in shift["queue"]:
        if customer["patience_until"] <= shift["tick"]:
            shift["lost"] += 1
        else:
            waiting.append(customer)
    shift["queue"] = waiting


def _tick_staffed_shops(new):
    """One tick for the other staffed shops of the day: their employees act on the shared
    stock and cash through the very same rules (a view of the state whose shift is theirs)."""
    shift = new["shift"]
    for shop in sorted(shift.get("extra", {})):
        sub = shift["extra"][shop]
        sub["tick"] = shift["tick"]
        view = {**new, "shift": sub}  # shares stock and the crew's shift with `new`
        _employees_work(view)
        new.update({key: value for key, value in view.items() if key != "shift"})  # cash etc.
        _expire_customers(sub)
        if _shift_running(sub) and sub["tick"] >= sub["shift_end"]:
            _end_shift(new, sub)


def _employees_work(state):
    """Every working employee of the running shift's shop acts once, in a fixed order:
    refilling first, then selling, each by id. No randomness. An action that is not
    possible (nothing to carry, nobody waiting) is simply skipped. Works on this very state
    (the caller owns the copy) with the same checks as the player's refill and sell.

    If the shop has nobody for one of the two jobs, the employees it has do that job too,
    at the speed of their own level, so a single employee runs the counter alone."""
    shift = state["shift"]
    if not _shift_running(shift):
        return
    team = sorted((e for e in state["employees"] if e["shop"] == shift["shop"] and e["working"]),
                  key=lambda e: e["id"])
    refillers = [e for e in team if e["job"] == "refiller"] or team
    sellers = [e for e in team if e["job"] == "seller"] or team
    order = {pid: i for i, pid in enumerate(CATALOGUE)}
    for employee in refillers:
        for _ in range(JOBS["refiller"]["per_tick"][employee["level"] - 1]):
            # only products somebody wants at today's price (planned customers), with stock
            wanted = [pid for pid in shift["counter"]
                      if state["stock"][pid] > 0 and shift["planned"].get(pid, 0) > 0]
            if not wanted:
                break
            wanted.sort(key=lambda pid: (shift["counter"][pid], order[pid]))
            try:
                _check_refill(state, wanted[0], 1)
            except RejectedAction:  # the counter is full
                break
            _carry(state, wanted[0], 1)
    for employee in sellers:
        if shift["tick"] % JOBS["seller"]["every"][employee["level"] - 1] != 0:
            continue
        for customer in shift["queue"]:  # the first customer who can be served now
            try:
                i = _check_sale(state, customer["product"])
            except RejectedAction:  # nothing of it on the counter, or he is not here yet
                continue
            _serve(state, i, customer["product"])
            break


def _end_shift(new, shift=None):
    """The shift is over, the day goes on: whoever still waits goes home, the counter is
    cleared back into the storeroom. What was sold stays booked for the day."""
    shift = shift or new["shift"]
    shift["lost"] += len(shift["queue"])
    shift["queue"] = []
    for pid in shift["counter"]:
        new["stock"][pid] += shift["counter"][pid]
        shift["counter"][pid] = 0
    shift["over"] = True


def skip_shift(state):
    """Let the rest of the day pass without any sales. Whoever did not work earns nothing.

    Only runs the ticks (the same rule as the clock), so no customer is served."""
    _check_open_shift(state)
    result = None
    while result is None:
        state, result = tick(state)
    return state, result


def _pay_wages(new, shops):
    """End of the day: every working employee of a shop that ran today (`shops`: one id or
    several) is paid, by id, as far as the cash goes. Who cannot be paid stops working (stays hired). Employees of a shop
    where no shift ran earn nothing and cost nothing. Afterwards, whoever stopped earlier
    restarts tomorrow if the cash left covers all the wages of those restarting (by id).
    Cash never goes below 0. Returns (cents paid, ids who stopped today)."""
    shops = {shops} if isinstance(shops, str) or shops is None else set(shops)
    paid, stopped = 0, []
    by_id = sorted(new["employees"], key=lambda e: e["id"])
    for employee in by_id:
        if not employee["working"] or employee["shop"] not in shops:
            continue
        wage = employee_wage(employee)
        if wage <= new["cash"]:
            new["cash"] -= wage
            paid += wage
        else:
            employee["working"] = False
            stopped.append(employee["id"])
    budget = new["cash"]
    for employee in by_id:
        if employee["working"] or employee["id"] in stopped:
            continue
        wage = employee_wage(employee)
        if wage <= budget:
            budget -= wage
            employee["working"] = True
    return paid, stopped


def _close_shift(new):
    """Book the day like trade_day does; unsold counter units go back to the storeroom."""
    shift = new["shift"]
    shift["lost"] += len(shift["queue"])  # whoever is still in the queue goes home
    shift["queue"] = []
    lines = []
    ran = {shift["shop"]} if shift["shop"] else set()
    lost = 0
    # the player's shift (or the open day) and the other staffed shops, booked the same way
    for sub in [shift, *(shift["extra"][sid] for sid in sorted(shift.get("extra", {})))]:
        if sub is not shift:
            ran.add(sub["shop"])
        lost += sub["lost"] + (len(sub["queue"]) if sub is not shift else 0)
        for pid, sold in sub["sold"].items():
            item = CATALOGUE[pid]
            price = new["prices"][pid]
            lines.append({
                "product": pid, "price": price, "demand": sub["planned"][pid],
                "sold": sold, "revenue": sold * price, "cogs": sold * item["cost"],
                "gross_profit": sold * (price - item["cost"]),
            })
            new["stock"][pid] += sub["counter"][pid]
    wages, stopped = _pay_wages(new, ran)
    gross_profit = sum(line["gross_profit"] for line in lines)
    result = {
        "day": new["day"],
        "shop": shift["shop"],
        "lines": lines,
        "revenue": sum(line["revenue"] for line in lines),
        "cogs": sum(line["cogs"] for line in lines),
        "gross_profit": gross_profit,
        "wages": wages,
        "wages_unpaid": stopped,
        "net": gross_profit - wages,
        "lost": lost,
        "cash_after": new["cash"],
    }
    result["shops"] = sorted(ran)  # always: the shops that ran (shop is only the player's)
    # the player worked the shift: a shop was chosen and staff did not take the place over
    result["played"] = shift["shop"] is not None and not shift.get("staffed", False)
    new["history"].append(result)
    award_badges(new, result)
    new["day"] += 1
    new["shift"] = None
    return new, result


def move_player(state, zone, x, y):
    """Save where the player stands. Only for showing the world: no rule depends on it."""
    if not isinstance(zone, str) or zone not in world.ZONES:
        raise RejectedAction(f"Unknown zone '{zone}'.")
    bounds = world.ZONES[zone]
    for value in (x, y):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise RejectedAction("A position needs two numbers.")
    # this also refuses NaN and infinity: every comparison with them fails or is out of range
    if not (bounds["minX"] <= x <= bounds["maxX"] and bounds["minY"] <= y <= bounds["maxY"]):
        raise RejectedAction(f"That position is outside {bounds['name']}.")
    new = copy.deepcopy(state)
    new["player"] = {"zone": zone, "x": round(float(x), 2), "y": round(float(y), 2)}
    return new


def stock_value(state):
    """Remaining stock valued at purchase cost (CT R4), counter units included."""
    shift = state.get("shift") or {}
    counters = [shift.get("counter", {})] + [s["counter"] for s in shift.get("extra", {}).values()]
    return sum((state["stock"][pid] + sum(c.get(pid, 0) for c in counters)) * CATALOGUE[pid]["cost"]
               for pid in owned_products(state))


def stock_overview(state):
    """Per product: units, value at cost, and what today's price would sell.

    Only reads the run. Sells today follows the trading rules (CT R1, CT R2);
    after the last day nothing sells any more, so everything counts as left.
    """
    lines = []
    for pid in owned_products(state):
        item = CATALOGUE[pid]
        units = state["stock"][pid]
        wanted = 0 if is_finished(state) else customers_today(state, pid)
        sells = min(wanted, units)
        lines.append({
            "product": pid,
            "units": units,
            "value": units * item["cost"],
            "sells_today": sells,
            "left_after_today": units - sells,
        })
    return {
        "lines": lines,
        "units": sum(line["units"] for line in lines),
        "value": sum(line["value"] for line in lines),
    }


def overall_gain(state):
    """CT R4: final cash + stock at cost - initial 100 euro."""
    return state["cash"] + stock_value(state) - STARTING_CASH


# ---- badges (specs/badges.md, issue #15) --------------------------------------------------
# Awards for what the player reached. Only award_badges() gives one, at the end of a day, on
# the server; no request can add a badge. A badge changes no rule and gives no money.
# All thresholds are placeholders to balance once pricing (#38) is in.
GOOD_DAY_NET = 5_000      # cents = 50 euro profit in one day
RECORD_DAY_NET = 15_000   # cents = 150 euro
DOUBLED_CASH = 20_000     # cents = 200 euro, twice the start
WEALTHY_CASH = 100_000    # cents = 1,000 euro
WINNER_CASH = 200_000     # cents = 2,000 euro when the season ends
TEAM_SIZE = 3
BIG_TEAM_SIZE = 6
SHORT_STREAK = 3          # days in a row with a profit
LONG_STREAK = 7
LONGEST_STREAK = 14
WORK_STREAK = 5           # days in a row the player played the shift


def day_net(result):
    """The profit of a booked day: gross profit minus wages (a traded day has no wages)."""
    return result.get("net", result["gross_profit"])


def day_sold(result):
    """Units sold on a booked day."""
    return sum(line["sold"] for line in result["lines"])


def day_lost(result):
    """Customers who left without buying. A traded day has no queue: whoever wanted more
    than the stock gave counts."""
    if "lost" in result:
        return result["lost"]
    return sum(max(line["demand"] - line["sold"], 0) for line in result["lines"])


def _streak(state, days, test):
    """True when the last `days` booked days are days in a row up to the latest one and all
    pass `test`."""
    last = state["history"][-days:]
    if len(last) < days:
        return False
    in_a_row = [r["day"] for r in last] == list(range(last[-1]["day"] - days + 1, last[-1]["day"] + 1))
    return in_a_row and all(test(r) for r in last)


def _shift_parts(state):
    """The open day's shift and the staffed shops running beside it (none without an open day)."""
    shift = state.get("shift")
    if not shift:
        return []
    return [shift, *shift.get("extra", {}).values()]


def _sold_so_far(state):
    """Units sold in this run: the booked days and the day that is open now."""
    booked = sum(day_sold(r) for r in state["history"])
    return booked + sum(sum(part.get("sold", {}).values()) for part in _shift_parts(state))


def _played_so_far(state):
    """The player has worked a shift: on a booked day, or the shift running now."""
    shift = state.get("shift")
    playing = bool(shift and shift.get("shop") is not None and not shift.get("staffed", False))
    return playing or any(r.get("played", False) for r in state["history"])


def _stormy(state, result):
    weather = make_day_context(state["seed"], result["day"], state["day_override"])["weather"]
    return weather == "storm"


# Each badge: id, name, icon, medal (bronze for the start, silver for the middle, gold for the
# late game; the profit streaks climb with their length), the condition for the screen, when it
# is checked, and its check.
# "now" badges depend on the state only: they are checked after every accepted action, so a
# first sale is awarded at the sale. "day" badges need a booked day: they are checked when a day
# closes (the result is then the last entry of the history and is passed as the second argument).
BADGES = (
    ("first-sale", "First sale", "☕", "bronze", "Sell something.", "now",
     lambda s, r: _sold_so_far(s) > 0),
    ("own-shift", "Behind the counter", "🧑‍🍳", "bronze", "Play a shift yourself.", "now",
     lambda s, r: _played_so_far(s)),
    ("first-hire", "The boss", "👤", "bronze", "Hire your first employee.", "now",
     lambda s, r: len(s["employees"]) >= 1),
    ("good-day", "Good day", "💰", "bronze", f"Make {fmt(GOOD_DAY_NET)} profit in one day.", "day",
     lambda s, r: day_net(r) >= GOOD_DAY_NET),
    ("no-one-left", "Nobody leaves empty-handed", "😊", "silver",
     "Sell something on a day no customer leaves without buying.", "day",
     lambda s, r: day_sold(r) > 0 and day_lost(r) == 0),
    ("expansion", "Expansion", "🏪", "silver", "Unlock a second shop.", "now",
     lambda s, r: sum(shop["unlocked"] for shop in s["shops"].values()) >= 2),
    ("doubled", "Doubled", "📈", "silver", f"Have {fmt(DOUBLED_CASH)} in cash.", "now",
     lambda s, r: s["cash"] >= DOUBLED_CASH),
    ("team", "A whole team", "👥", "silver", f"Have {TEAM_SIZE} employees at once.", "now",
     lambda s, r: len(s["employees"]) >= TEAM_SIZE),
    ("upgrade", "Upgrade", "🔧", "silver", "Buy an upgrade in a shop's window.", "now",
     lambda s, r: any(shop["level"] > 1 for shop in s["shops"].values())),
    ("pro", "Pro", "⭐", "silver", f"Train an employee to level {EMPLOYEE_MAX_LEVEL}.", "now",
     lambda s, r: any(e["level"] >= EMPLOYEE_MAX_LEVEL for e in s["employees"])),
    ("streak-3", "On track", "🔥", "bronze", f"Make a profit {SHORT_STREAK} days in a row.", "day",
     lambda s, r: _streak(s, SHORT_STREAK, lambda d: day_net(d) > 0)),
    ("streak-7", "On a roll", "🔥", "silver", f"Make a profit {LONG_STREAK} days in a row.", "day",
     lambda s, r: _streak(s, LONG_STREAK, lambda d: day_net(d) > 0)),
    ("hard-worker", "Hard worker", "💪", "silver", f"Play the shift yourself {WORK_STREAK} days in a row.", "day",
     lambda s, r: _streak(s, WORK_STREAK, lambda d: d.get("played", False))),
    ("streak-14", "Unstoppable", "🔥", "gold", f"Make a profit {LONGEST_STREAK} days in a row.", "day",
     lambda s, r: _streak(s, LONGEST_STREAK, lambda d: day_net(d) > 0)),
    ("empire", "Empire", "🌍", "gold", "Unlock every shop.", "now",
     lambda s, r: all(shop["unlocked"] for shop in s["shops"].values())),
    ("big-team", "Big team", "🏢", "gold", f"Have {BIG_TEAM_SIZE} employees at once.", "now",
     lambda s, r: len(s["employees"]) >= BIG_TEAM_SIZE),
    ("record-day", "Record day", "🚀", "gold", f"Make {fmt(RECORD_DAY_NET)} profit in one day.", "day",
     lambda s, r: day_net(r) >= RECORD_DAY_NET),
    ("storm-proof", "Storm-proof", "⛈️", "gold", "Make a profit on a stormy day.", "day",
     lambda s, r: day_net(r) > 0 and _stormy(s, r)),
    ("wealthy", "Wealthy", "💎", "gold", f"Have {fmt(WEALTHY_CASH)} in cash.", "now",
     lambda s, r: s["cash"] >= WEALTHY_CASH),
    ("season-winner", "Season winner", "👑", "gold",
     f"End day {LAST_DAY} with at least {fmt(WINNER_CASH)} in cash.", "day",
     lambda s, r: r["day"] >= LAST_DAY and s["cash"] >= WINNER_CASH),
)
BADGE_IDS = tuple(b[0] for b in BADGES)
BADGE_TIERS = ("bronze", "silver", "gold")
BADGE_TIER = {b[0]: b[3] for b in BADGES}  # the medal of each badge, by id


def award_badges(new, result=None):
    """Give every badge whose condition is true now and that was not earned yet. Changes `new`
    in place (called on the copy a rule works on) and returns the ids it gave.

    Without a result (after any accepted action) only the "now" badges are checked, stamped
    with the open day. With the result of a day that just closed, the "day" badges are checked
    too, and result["badges"] lists every badge earned on that day, also those that were given
    during it (the evening report shows them all). No randomness, nothing from the browser."""
    new.setdefault("badges", [])
    earned = {b["id"] for b in new["badges"]}
    day = result["day"] if result is not None else new["day"]
    given = []
    if day > LAST_DAY:  # the season is over: nothing more to earn
        return given
    for badge_id, _name, _icon, _tier, _text, when, check in BADGES:
        if badge_id in earned or (when == "day" and result is None):
            continue
        if check(new, result):
            new["badges"].append({"id": badge_id, "day": day})
            given.append(badge_id)
    if result is not None:
        result["badges"] = [b["id"] for b in new["badges"] if b["day"] == result["day"]]
    return given


def badges_view(state):
    """Every badge in BADGES order for the screen: day is None while not earned."""
    days = {b["id"]: b["day"] for b in state.get("badges", [])}
    return [{"id": badge_id, "name": name, "icon": icon, "text": text, "tier": tier,
             "day": days.get(badge_id)}
            for badge_id, name, icon, tier, text, _when, _check in BADGES]


def _check_badges(value, day):
    """An editor list of earned badges: known ids, each once, earned on a day before `day`."""
    if not isinstance(value, list):
        raise RejectedAction("'badges' must be a list of {\"id\", \"day\"}.")
    seen = set()
    out = []
    for entry in value:
        if not isinstance(entry, dict) or set(entry) != {"id", "day"}:
            raise RejectedAction("Each badge must be {\"id\", \"day\"}.")
        if not isinstance(entry["id"], str) or entry["id"] not in BADGE_IDS:
            raise RejectedAction(f"Unknown badge '{entry['id']}'.")
        if entry["id"] in seen:
            raise RejectedAction(f"The badge '{entry['id']}' is in the list twice.")
        seen.add(entry["id"])
        out.append({"id": entry["id"], "day": _whole(entry["day"], 1, max(day - 1, 1),
                                                      "The day of a badge")})
    if out and day <= 1:
        raise RejectedAction("On day 1 no badge can be earned yet.")
    return out
