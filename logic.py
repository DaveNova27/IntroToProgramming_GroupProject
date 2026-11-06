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
    "surfboard": {"name": "Surfboard", "cost": 4_000, "ref_price": 9_000},
    "wetsuit": {"name": "Wetsuit", "cost": 2_500, "ref_price": 6_000},
    "surf_lesson": {"name": "Surf lesson", "cost": 800, "ref_price": 2_500},
    "hoodie": {"name": "Hoodie", "cost": 1_800, "ref_price": 3_500},
    "tshirt": {"name": "T-shirt", "cost": 600, "ref_price": 1_500},
    "cap": {"name": "Cap", "cost": 400, "ref_price": 1_200},
    "beer": {"name": "Beer", "cost": 150, "ref_price": 400},
    "coke_zero": {"name": "Coke Zero", "cost": 80, "ref_price": 250},
    "sandwich": {"name": "Sandwich", "cost": 200, "ref_price": 400},
}

STAFF_PLACE_PRICE = 6_000  # cents = 60 euro, the same in every shop
STORAGE_UNITS = 100  # storeroom space per shop, checked when buying stock
COUNTER_UNITS = 20  # counter space per shop (limits refills in a shift)
FIRST_SHOP = "cafe"
DEFAULT_SEED = 1  # only for tests and the demo; real runs draw one with new_seed()

# The weather (day-context, issue #10). weight: how often it appears, in percent.
# temp: range in whole degrees Celsius. demand_percent: the demand factor per shop in
# whole percent (100 = normal), from the roadmap's table B2. Calculated and shown only:
# the customers are not changed by it yet (the price logic, issue #38, applies it).
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
SHIFT_SHOPS = ("cafe",)  # shops where a day can be played live (shop-process: one first)
DAY_TICKS = 90  # a played day is 90 ticks, the server counts them (about 90 seconds)
PATIENCE_TICKS = 15  # a customer leaves this many ticks after arriving


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
        "storage": STORAGE_UNITS, "counter": COUNTER_UNITS,
        "window": _window([("cake", 4_000), ("bagel", 3_000)]),
    },
    "beach_cafe": {
        "name": "Beach Cafe", "unlock_price": 20_000, "start_product": "beer",
        "storage": STORAGE_UNITS, "counter": COUNTER_UNITS,
        "window": _window([("coke_zero", 6_000), ("sandwich", 8_000)]),
    },
    "merchandise": {
        "name": "Merchandise", "unlock_price": 35_000, "start_product": "hoodie",
        "storage": STORAGE_UNITS, "counter": COUNTER_UNITS,
        "window": _window([("tshirt", 8_000), ("cap", 6_000)]),
    },
    "surf_shop": {
        "name": "Surf Shop", "unlock_price": 50_000, "start_product": "surfboard",
        "storage": STORAGE_UNITS, "counter": COUNTER_UNITS,
        "window": _window([("wetsuit", 12_000), ("surf_lesson", 15_000)]),
    },
}


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
        "history": [],
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


def _check_storeroom_space(state, product, quantity):
    """The storeroom of the product's shop holds at most SHOPS[shop]["storage"] units."""
    shop = next(sid for sid in SHOPS if product in shop_product_ids(sid))
    held = sum(state["stock"][pid] for pid in shop_product_ids(shop))
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
    if isinstance(price_cents, bool) or not isinstance(price_cents, int):
        raise RejectedAction("The selling price must be a whole number of cents.")
    if price_cents <= 0:
        raise RejectedAction("The selling price must be more than €0.")
    if price_cents > MAX_PRICE:
        raise RejectedAction(f"The selling price can be at most {fmt(MAX_PRICE)}.")
    new = copy.deepcopy(state)
    new["prices"][product] = price_cents
    return new


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
    new_entry["level"] += 1
    return new


def demand(price_cents, ref_price_cents):
    """CT R1: 10 units up to the reference price, 5 up to twice it, 0 above."""
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
        wanted = demand(price, item["ref_price"])
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
    }
    new["history"].append(result)
    new["day"] += 1  # CT R5: exactly one day per trade action
    return new, result


def make_day_context(seed, day, override=None):
    """The weather of one day, from the seed and the day only (same input, same answer).

    override: None, or {"weather": id} to fix the weather (demo mode); the temperature is
    still rolled from the seed. Returns {"day", "weather", "temperature", "demand_percent"}."""
    rng = random.Random(f"{seed}:{day}")
    roll = rng.randrange(sum(w["weight"] for w in WEATHER.values()))
    weather = next(iter(WEATHER))
    for wid, w in WEATHER.items():
        if roll < w["weight"]:
            weather = wid
            break
        roll -= w["weight"]
    if override is not None:
        weather = override["weather"]
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


def set_day_override(state, weather):
    """Fix the weather (a demo switch) or clear it with None."""
    if weather is not None and (not isinstance(weather, str) or weather not in WEATHER):
        raise RejectedAction(f"Unknown weather '{weather}'.")
    new = copy.deepcopy(state)
    new["day_override"] = None if weather is None else {"weather": weather}
    return new


def customers_for(price_cents, ref_price_cents):
    """How many customers want one product on a played day.

    The one place that turns a price into customers. It is the old demand() for now;
    the new price logic (issue #38) replaces only this function."""
    return demand(price_cents, ref_price_cents)


def _check_open_shift(state):
    """The open shift, or a refusal. Also refuses everything after the last day."""
    if is_finished(state):
        raise RejectedAction("The run is complete. The shop is closed.")
    shift = state.get("shift")
    if shift is None:
        raise RejectedAction("No shift is running. Start the day in a shop first.")
    return shift


def _check_shift_product(state, shift, product):
    if not isinstance(product, str) or product not in CATALOGUE:
        raise RejectedAction(f"Unknown product '{product}'.")
    if product not in shift["counter"]:  # the products the shift started with
        raise RejectedAction(f"{CATALOGUE[product]['name']} is not sold in this shop.")


def start_shift(state, shop):
    """Start playing the day in a shop. Builds the queue of customers, no randomness."""
    if is_finished(state):
        raise RejectedAction("The run is complete. The shop is closed.")
    _check_shop(shop)
    if shop not in SHIFT_SHOPS:
        raise RejectedAction(f"A day cannot be played in the {SHOPS[shop]['name']} yet.")
    if not state["shops"][shop]["unlocked"]:
        raise RejectedAction(f"The {SHOPS[shop]['name']} is not unlocked.")
    if state.get("shift") is not None:
        raise RejectedAction("A shift is already running.")
    products = state["shops"][shop]["products"]
    planned, queue = {}, []
    for k, pid in enumerate(products):
        count = customers_for(state["prices"][pid], CATALOGUE[pid]["ref_price"])
        planned[pid] = count
        for j in range(count):
            arrives = min((j * DAY_TICKS) // count + k, DAY_TICKS - 1)
            queue.append({"product": pid, "arrives": arrives,
                          "patience_until": arrives + PATIENCE_TICKS})
    queue.sort(key=lambda c: c["arrives"])  # stable: products keep their order per tick
    new = copy.deepcopy(state)
    new["shift"] = {
        "shop": shop, "tick": 0,
        "counter": {pid: 0 for pid in products},
        "queue": queue, "planned": planned,
        "sold": {pid: 0 for pid in products}, "lost": 0,
    }
    return new


def refill(state, product, quantity):
    """Carry units from the storeroom to the counter. The counter space is limited."""
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
    new = copy.deepcopy(state)
    new["stock"][product] -= quantity
    new["shift"]["counter"][product] += quantity
    return new


def sell(state, product):
    """Sell one unit from the counter to the first customer waiting for it."""
    shift = _check_open_shift(state)
    _check_shift_product(state, shift, product)
    name = CATALOGUE[product]["name"]
    if shift["counter"][product] <= 0:
        raise RejectedAction(f"There is no {name} on the counter.")
    tick = shift["tick"]
    for i, customer in enumerate(shift["queue"]):
        if (customer["product"] == product
                and customer["arrives"] <= tick < customer["patience_until"]):
            break
    else:
        raise RejectedAction(f"Nobody is waiting for {name}.")
    new = copy.deepcopy(state)
    new["shift"]["queue"].pop(i)
    new["shift"]["counter"][product] -= 1
    new["shift"]["sold"][product] += 1
    new["cash"] += new["prices"][product]
    return new


def tick(state):
    """One tick of the day. Impatient customers leave; the last tick closes the shift.

    Returns (new_state, result) where result is the day's result when the shift closed,
    otherwise None."""
    _check_open_shift(state)
    new = copy.deepcopy(state)
    shift = new["shift"]
    shift["tick"] += 1
    waiting = []
    for customer in shift["queue"]:
        if customer["patience_until"] <= shift["tick"]:
            shift["lost"] += 1
        else:
            waiting.append(customer)
    shift["queue"] = waiting
    if shift["tick"] < DAY_TICKS:
        return new, None
    return _close_shift(new)


def _close_shift(new):
    """Book the day like trade_day does; unsold counter units go back to the storeroom."""
    shift = new["shift"]
    shift["lost"] += len(shift["queue"])  # whoever is still in the queue goes home
    shift["queue"] = []
    lines = []
    for pid, sold in shift["sold"].items():
        item = CATALOGUE[pid]
        price = new["prices"][pid]
        lines.append({
            "product": pid, "price": price, "demand": shift["planned"][pid],
            "sold": sold, "revenue": sold * price, "cogs": sold * item["cost"],
            "gross_profit": sold * (price - item["cost"]),
        })
        new["stock"][pid] += shift["counter"][pid]
    result = {
        "day": new["day"],
        "shop": shift["shop"],
        "lines": lines,
        "revenue": sum(line["revenue"] for line in lines),
        "cogs": sum(line["cogs"] for line in lines),
        "gross_profit": sum(line["gross_profit"] for line in lines),
        "lost": shift["lost"],
        "cash_after": new["cash"],
    }
    new["history"].append(result)
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
    counter = (state.get("shift") or {}).get("counter", {})
    return sum((state["stock"][pid] + counter.get(pid, 0)) * CATALOGUE[pid]["cost"]
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
        wanted = 0 if is_finished(state) else demand(state["prices"][pid], item["ref_price"])
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
