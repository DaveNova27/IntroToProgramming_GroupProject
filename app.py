"""The screen: a small web server plus the dashboard in static/.

The browser never decides anything. Every click is sent here, the rule in
logic.py decides, and only an accepted action is saved by db.py. Each request
loads the run fresh from the database: the database is the truth, so a browser
refresh or a double click cannot repeat a day.

Run it with:  uv run python app.py   (then open http://127.0.0.1:8000)
"""

import threading

from flask import Flask, jsonify, request, send_from_directory

import db
import logic

app = Flask(__name__, static_folder="static", static_url_path="/static")
_lock = threading.Lock()  # one change at a time: load -> rule -> save


def load_run():
    """Load the saved run, or start and save a fresh one (first start)."""
    state = db.load()
    if state is None:
        state = logic.new_state()
        db.save(state)
    return state


def view(state):
    """Everything the dashboard shows, calculated by the rules, never by the browser."""
    finished = logic.is_finished(state)
    products = [{
        "id": pid,
        "name": item["name"],
        "cost": item["cost"],
        "ref_price": item["ref_price"],
        "price": state["prices"][pid],
        "stock": state["stock"][pid],
        "demand": logic.demand(state["prices"][pid], item["ref_price"]),
    } for pid, item in logic.CATALOGUE.items()]
    return {
        "day": state["day"],
        "last_day": logic.LAST_DAY,
        "finished": finished,
        "starting_cash": logic.STARTING_CASH,
        "cash": state["cash"],
        "stock_value": logic.stock_value(state),
        "overall_gain": logic.overall_gain(state),
        "products": products,
        # trade_day returns a new state and leaves the saved one alone,
        # so it doubles as a preview of "what happens if I open now".
        "forecast": None if finished else logic.trade_day(state)[1],
        "history": state["history"],
        "demand_levels": {
            "at_or_below_ref": logic.DEMAND_AT_OR_BELOW_REF,
            "up_to_double_ref": logic.DEMAND_UP_TO_DOUBLE_REF,
        },
    }


def parse_quantity(value):
    """Turn the typed quantity into a whole number, or refuse it (CT02)."""
    text = str(value).strip()
    if not text.lstrip("-").isdigit():
        raise logic.RejectedAction("Quantity must be a positive whole number.")
    return int(text)


def apply(action):
    """Run a rule on the saved run. Save only if it was accepted."""
    with _lock:
        state = load_run()
        try:
            new_state, message = action(state)
        except logic.RejectedAction as reason:
            # nothing is saved; the dashboard gets the unchanged run back
            return jsonify({"error": str(reason), "state": view(state)}), 400
        db.save(new_state)
        return jsonify({"message": message, "state": view(new_state)})


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/state")
def get_state():
    with _lock:
        return jsonify(view(load_run()))


@app.post("/api/buy")
def buy():
    body = request.get_json(silent=True) or {}

    def action(state):
        product = body.get("product")
        quantity = parse_quantity(body.get("quantity", ""))
        new_state = logic.buy(state, product, quantity)
        cost = state["cash"] - new_state["cash"]
        name = logic.CATALOGUE[product]["name"]
        return new_state, f"Bought {quantity} × {name} for {logic.fmt(cost)}."

    return apply(action)


@app.post("/api/price")
def set_price():
    body = request.get_json(silent=True) or {}

    def action(state):
        product = body.get("product")
        price = logic.euros_to_cents(body.get("price", ""))
        new_state = logic.set_price(state, product, price)
        name = logic.CATALOGUE[product]["name"]
        return new_state, f"{name} now sells for {logic.fmt(price)}."

    return apply(action)


@app.post("/api/open")
def open_day():
    body = request.get_json(silent=True) or {}

    def action(state):
        # The page says which day it meant to open. If that day is already
        # traded (second click, old tab), refuse instead of trading again.
        if body.get("day") != state["day"]:
            raise logic.RejectedAction(
                f"Day {body.get('day')} is already traded. The dashboard is now up to date."
            )
        new_state, result = logic.trade_day(state)
        return new_state, (
            f"Day {result['day']} closed: gross profit {logic.fmt(result['gross_profit'])}."
        )

    return apply(action)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=False)
