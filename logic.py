"""The rules of Campus Tycoon.

No screen and no database in this file: only the decisions.
All money is stored as integer cents (2.00 euro = 200) to avoid rounding errors.

Every function takes a state and returns a NEW state. The old one is never
changed, so a rejected action cannot damage the game (BRD: rejected actions
leave existing data unchanged).
"""

import copy
from decimal import Decimal, InvalidOperation

STARTING_CASH = 10_000  # cents = 100.00 euro
LAST_DAY = 5
DEMAND_AT_OR_BELOW_REF = 10
DEMAND_UP_TO_DOUBLE_REF = 5

# The fixed catalogue: unit purchase cost and reference selling price, in cents.
CATALOGUE = {
    "sandwich": {"name": "Sandwich", "cost": 200, "ref_price": 400},
    "coffee": {"name": "Coffee", "cost": 80, "ref_price": 200},
    "cookie": {"name": "Cookie", "cost": 50, "ref_price": 150},
}


class RejectedAction(Exception):
    """Raised when a rule refuses an action. The message is shown to the player."""


def new_state():
    """A fresh run: day 1, 100 euro, no stock, prices at the reference price."""
    return {
        "day": 1,
        "cash": STARTING_CASH,
        "stock": {pid: 0 for pid in CATALOGUE},
        "prices": {pid: item["ref_price"] for pid, item in CATALOGUE.items()},
        "history": [],
    }


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
    """After day 5 the run is complete (CT05)."""
    return state["day"] > LAST_DAY


def _check_product(product):
    if product not in CATALOGUE:
        raise RejectedAction(f"Unknown product '{product}'.")


def buy(state, product, quantity):
    """CT02: buy stock. Cash and stock change together, or not at all."""
    _check_product(product)
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


def buy_many(state, quantities):
    """Buy several products as one all-or-nothing stock order."""
    if is_finished(state):
        raise RejectedAction("The run is complete. Buying is closed.")
    if not isinstance(quantities, dict):
        raise RejectedAction("Quantities must be provided for the stock order.")

    unknown = set(quantities) - set(CATALOGUE)
    if unknown:
        raise RejectedAction(f"Unknown product '{sorted(unknown)[0]}'.")

    total = 0
    units = 0
    for product, item in CATALOGUE.items():
        quantity = quantities.get(product, 0)
        if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 0:
            raise RejectedAction("Quantities must be positive whole numbers or zero.")
        units += quantity
        total += quantity * item["cost"]

    if units == 0:
        raise RejectedAction("Choose at least one item to order.")
    if total > state["cash"]:
        raise RejectedAction(
            f"Not enough cash: the combined order costs {fmt(total)}, "
            f"you have {fmt(state['cash'])}."
        )

    new = copy.deepcopy(state)
    new["cash"] -= total
    for product, quantity in quantities.items():
        new["stock"][product] += quantity
    return new


def set_price(state, product, price_cents):
    """CT03: set a positive selling price."""
    _check_product(product)
    if is_finished(state):
        raise RejectedAction("The run is complete. Prices are locked.")
    if price_cents <= 0:
        raise RejectedAction("The selling price must be more than €0.")
    new = copy.deepcopy(state)
    new["prices"][product] = price_cents
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
    for pid, item in CATALOGUE.items():
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


def stock_value(state):
    """Remaining stock valued at purchase cost (CT R4)."""
    return sum(qty * CATALOGUE[pid]["cost"] for pid, qty in state["stock"].items())


def stock_overview(state):
    """Per product: units, value at cost, and what today's price would sell.

    Only reads the run. Sells today follows the trading rules (CT R1, CT R2);
    after day 5 nothing sells any more, so everything counts as left.
    """
    lines = []
    for pid, item in CATALOGUE.items():
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
