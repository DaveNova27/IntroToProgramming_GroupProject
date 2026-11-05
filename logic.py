"""The rules of Campus Tycoon.

No screen and no database in this file: only the decisions.
All money is stored as integer cents (2.00 euro = 200) to avoid rounding errors.

Every function takes a state and returns a NEW state. The old one is never
changed, so a rejected action cannot damage the game (BRD: rejected actions
leave existing data unchanged).
"""

import copy
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
STORAGE_UNITS = 100  # storeroom space per shop (takes effect with shop-process)
COUNTER_UNITS = 20  # counter space per shop (takes effect with shop-process)
FIRST_SHOP = "cafe"


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


def new_state():
    """A fresh run: day 1, 100 euro, no stock, prices at the reference price."""
    return {
        "day": 1,
        "cash": STARTING_CASH,
        "stock": {pid: 0 for pid in CATALOGUE},
        "prices": {pid: item["ref_price"] for pid, item in CATALOGUE.items()},
        "shops": {sid: _new_shop(sid) for sid in SHOPS},
        "history": [],
        "player": world.start_player(),
    }


def _new_shop(shop_id):
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


def buy(state, product, quantity):
    """CT02: buy stock. Cash and stock change together, or not at all."""
    _check_product(state, product)
    if is_finished(state):
        raise RejectedAction("The run is complete. Buying is closed.")
    if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0:
        raise RejectedAction("Quantity must be a positive whole number.")
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
    """Remaining stock valued at purchase cost (CT R4)."""
    return sum(state["stock"][pid] * CATALOGUE[pid]["cost"] for pid in owned_products(state))


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
