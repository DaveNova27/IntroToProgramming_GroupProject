"""The screen: a small web server plus the dashboard in static/.

The browser never decides anything. Every click is sent here, the rule in
logic.py decides, and only an accepted action is saved by db.py. Each request
loads the run fresh from the database: the database is the truth, so a browser
refresh or a double click cannot repeat a day.

Run it with:  uv run python app.py   (then open http://127.0.0.1:8000)
"""

import os
import threading

from flask import Flask, has_request_context, jsonify, redirect, request, send_from_directory

import db
import logic
import world

app = Flask(__name__, static_folder="static", static_url_path="/static")
# Let the browser re-check the page files on every load (a cheap "not modified"
# answer), so an updated dashboard or map is never served from an old cache.
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
_lock = threading.Lock()  # one change at a time: load -> rule -> save


def load_run():
    """Load the saved run, or start and save a fresh one (first start)."""
    state = db.load()
    if state is None:
        state = logic.new_state(logic.new_seed())
        db.save(state)
    return state


def shops_view(state):
    """Each shop with its level and what its window offers, prices from the rules."""
    out = []
    for sid, shop in logic.SHOPS.items():
        mine = state["shops"][sid]
        out.append({
            "id": sid,
            "name": shop["name"],
            "start_product_name": logic.CATALOGUE[shop["start_product"]]["name"],
            "unlocked": mine["unlocked"],
            "unlock_price": shop["unlock_price"],
            "affordable": shop["unlock_price"] <= state["cash"],
            "level": mine["level"],
            "products": mine["products"],
            "staff_places": mine["staff_places"],
            "storage": shop["storage"],
            "counter": shop["counter"],
            "offers": logic.shop_offers(state, sid),
        })
    return out


def shift_view(state):
    """The running shift as the screen needs it (or None). Only counts, no future customers."""
    shift = state["shift"]
    if shift is None:
        return None
    tick = shift["tick"]
    waiting = {}
    for c in shift["queue"]:
        if c["arrives"] <= tick:
            waiting[c["product"]] = waiting.get(c["product"], 0) + 1
    size = logic.SHOPS[shift["shop"]]["counter"] if shift["shop"] else 0
    return {
        "shop": shift["shop"],
        "tick": tick,
        "day_ticks": shift.get("day_end", logic.DAY_TICKS),
        "shift_end": shift.get("shift_end", logic.DAY_TICKS) if shift["shop"] else None,
        "shift_ticks": logic.SHIFT_TICKS,
        "over": bool(shift.get("over")),
        "counter": shift["counter"],
        "counter_space": size - sum(shift["counter"].values()),
        "counter_size": size,
        "waiting": waiting,
        "sold": shift["sold"],
        "lost": shift["lost"],
    }


def weather_view(state):
    """Today's weather for the screen (none once the season is over).
    The seed itself never leaves the server."""
    if logic.is_finished(state):
        return None
    context = logic.day_context(state)
    return {
        "id": context["weather"],
        "name": logic.WEATHER[context["weather"]]["name"],
        "temperature": context["temperature"],
        "demand_percent": context["demand_percent"],
    }


def editor_info():
    """What the editor panel offers (ids and limits from the rules, never from the screen)."""
    return {
        "weather": [{"id": wid, "name": w["name"]} for wid, w in logic.WEATHER.items()],
        "max_level": {sid: 1 + len(shop["window"]) for sid, shop in logic.SHOPS.items()},
        "max_cash": logic.MAX_CASH,
        "max_seed": logic.MAX_SEED,
        "storage": logic.STORAGE_UNITS,
    }


def view(state):
    """Everything the dashboard shows, calculated by the rules, never by the browser."""
    finished = logic.is_finished(state)
    editor_on = has_request_context() and editor_switch_on()
    owned = logic.owned_products(state)
    products = [{
        "id": pid,
        "name": item["name"],
        "cost": item["cost"],
        "ref_price": item["ref_price"],
        "price": state["prices"][pid],
        "stock": state["stock"][pid],
        "demand": logic.demand(state["prices"][pid], item["ref_price"]),
    } for pid, item in logic.CATALOGUE.items() if pid in owned]
    return {
        "day": state["day"],
        "last_day": logic.LAST_DAY,
        "finished": finished,
        "starting_cash": logic.STARTING_CASH,
        "cash": state["cash"],
        "stock_value": logic.stock_value(state),
        "stock_overview": logic.stock_overview(state),
        "overall_gain": logic.overall_gain(state),
        "products": products,
        "shops": shops_view(state),
        # trade_day returns a new state and leaves the saved one alone,
        # so it doubles as a preview of "what happens if I open now".
        "forecast": None if finished or state["shift"] else logic.trade_day(state)[1],
        "weather": weather_view(state),
        "editor": editor_on,
        "editor_info": editor_info() if editor_on else None,
        "shift": shift_view(state),
        "shift_shops": list(logic.SHIFT_SHOPS),
        "shift_day_ticks": logic.DAY_TICKS,
        "history": state["history"],
        "player": state["player"],
        "demand_levels": {
            "at_or_below_ref": logic.DEMAND_AT_OR_BELOW_REF,
            "up_to_double_ref": logic.DEMAND_UP_TO_DOUBLE_REF,
        },
    }


def json_body():
    """The request as a dictionary. Anything else counts as empty, so the rules refuse it."""
    body = request.get_json(silent=True)
    return body if isinstance(body, dict) else {}


def parse_quantity(value):
    """Turn the typed quantity into a whole number, or refuse it (CT02)."""
    text = str(value).strip()
    if not text.lstrip("-").isdigit():
        raise logic.RejectedAction("Quantity must be a positive whole number.")
    try:
        return int(text)
    except ValueError:  # "--5", "²" or thousands of digits
        raise logic.RejectedAction("Quantity must be a positive whole number.")


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


@app.get("/map")
def campus_map():
    # The campus lives inside the main page (full screen or as a live window);
    # only the embedded copy is served here directly.
    if "embed" not in request.args:
        return redirect("/")
    return send_from_directory(app.static_folder, "map.html")


@app.get("/api/state")
def get_state():
    with _lock:
        return jsonify(view(load_run()))


@app.get("/api/world")
def get_world():
    return jsonify(world.world_view())


@app.post("/api/player")
def move_player():
    body = json_body()

    def action(state):
        return logic.move_player(state, body.get("zone"), body.get("x"), body.get("y")), ""

    return apply(action)


@app.post("/api/buy")
def buy():
    body = json_body()

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
    body = json_body()

    def action(state):
        product = body.get("product")
        price = logic.euros_to_cents(body.get("price", ""))
        new_state = logic.set_price(state, product, price)
        name = logic.CATALOGUE[product]["name"]
        return new_state, f"{name} now sells for {logic.fmt(price)}."

    return apply(action)


@app.post("/api/shop/unlock")
def unlock_shop():
    body = json_body()

    def action(state):
        shop = body.get("shop")
        new_state = logic.unlock_shop(state, shop)
        cost = state["cash"] - new_state["cash"]
        return new_state, f"{logic.SHOPS[shop]['name']} unlocked for {logic.fmt(cost)}."

    return apply(action)


@app.post("/api/shop/upgrade")
def buy_upgrade():
    body = json_body()

    def action(state):
        shop, item = body.get("shop"), body.get("item")
        new_state = logic.buy_upgrade(state, shop, item)
        cost = state["cash"] - new_state["cash"]
        name = logic.SHOPS[shop]["name"]
        return new_state, f"Bought {logic.offer_name(shop, item)} for {name}: {logic.fmt(cost)}."

    return apply(action)


def local_request():
    """True only for a request from this computer, with no proxy in between."""
    # a proxy in front would make every client look local: refuse when one has been involved
    if request.headers.get("X-Forwarded-For") or request.headers.get("Forwarded"):
        return False
    return request.remote_addr in ("127.0.0.1", "::1", "::ffff:127.0.0.1")


def demo_switch_on():
    """The weather override is a demo hook: only with the switch on and from this computer."""
    return os.environ.get("CAMPUS_TYCOON_DEMO") == "1" and local_request()


def editor_switch_on():
    """The editor mode (specs/editor-mode.md): CT_EDITOR=1 and a request from this computer."""
    return os.environ.get("CT_EDITOR") == "1" and local_request()


@app.post("/api/day-override")
def day_override():
    body = json_body()

    def action(state):
        if not demo_switch_on():
            raise logic.RejectedAction("The weather override is a demo switch and is off.")
        weather = body.get("weather")
        new_state = logic.set_day_override(state, weather)
        if weather is None:
            return new_state, "Weather back to the seed's forecast."
        return new_state, f"Weather fixed to {logic.WEATHER[weather]['name']}."

    return apply(action)


def editor_action(rule):
    """Run an editor rule on the saved run: only with the switch on, saved with save_new_run
    (an edit may move the day back and cut the history). Nothing is saved when refused."""
    with _lock:
        state = load_run()
        try:
            if not editor_switch_on():
                raise logic.RejectedAction("The editor is off.")
            new_state, message = rule(state)
        except logic.RejectedAction as reason:
            return jsonify({"error": str(reason), "state": view(state)}), 400
        db.save_new_run(new_state)
        return jsonify({"message": message, "state": view(new_state)})


@app.post("/api/editor/cash")
def editor_cash():
    body = json_body()
    return editor_action(lambda state: (
        logic.editor_cash(state, body.get("mode"), body.get("cents")), "Cash changed."))


@app.post("/api/editor/weather")
def editor_weather():
    body = json_body()

    def rule(state):
        weather = body.get("weather")
        new_state = logic.set_day_override(state, weather)
        return new_state, ("Weather back to the seed's forecast." if weather is None
                           else f"Weather fixed to {logic.WEATHER[weather]['name']}.")

    return editor_action(rule)


@app.post("/api/editor/skip-days")
def editor_skip_days():
    body = json_body()

    def rule(state):
        days = body.get("days")
        new_state = logic.editor_skip_days(state, days)
        return new_state, f"Skipped {days} day(s). It is day {new_state['day']}."

    return editor_action(rule)


@app.post("/api/editor/state")
def editor_state():
    body = json_body()
    return editor_action(lambda state: (
        logic.editor_set_state(state, body.get("patch")), "State set."))


@app.post("/api/editor/reset")
def editor_reset():
    body = json_body()

    def rule(state):
        if body.get("confirm") is not True:
            raise logic.RejectedAction("A reset needs confirm: true.")
        seed = body["seed"] if body.get("seed") is not None else logic.new_seed()
        logic.check_seed(seed)
        return logic.new_state(seed), "Run reset to day 1."

    return editor_action(rule)


@app.post("/api/day/open")
def day_open():
    def action(state):
        return logic.open_day(state), f"Day {state['day']} is open."

    return apply(action)


@app.post("/api/shift/start")
def start_shift():
    body = json_body()

    def action(state):
        shop = body.get("shop")
        new_state = logic.start_shift(state, shop)
        return new_state, f"Shift started in the {logic.SHOPS[shop]['name']}."

    return apply(action)


@app.post("/api/shift/refill")
def refill():
    body = json_body()

    def action(state):
        product, quantity = body.get("product"), body.get("quantity")
        new_state = logic.refill(state, product, quantity)
        return new_state, f"Put {quantity} × {logic.CATALOGUE[product]['name']} on the counter."

    return apply(action)


@app.post("/api/shift/sell")
def sell():
    body = json_body()

    def action(state):
        product = body.get("product")
        new_state = logic.sell(state, product)
        name = logic.CATALOGUE[product]["name"]
        return new_state, f"Sold 1 × {name} for {logic.fmt(state['prices'][product])}."

    return apply(action)


@app.post("/api/shift/tick")
def shift_tick():
    def action(state):
        new_state, result = logic.tick(state)
        if result is None:
            return new_state, ""
        return new_state, (
            f"Day {result['day']} closed: gross profit {logic.fmt(result['gross_profit'])}."
        )

    return apply(action)


@app.post("/api/shift/skip")
def shift_skip():
    def action(state):
        new_state, result = logic.skip_shift(state)
        return new_state, (
            f"Day {result['day']} skipped: gross profit {logic.fmt(result['gross_profit'])}."
        )

    return apply(action)


@app.post("/api/open")
def open_day():
    body = json_body()

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


@app.post("/api/new-run")
def new_run():
    body = json_body()
    with _lock:
        state = load_run()
        # CT01: the page asks the player first and only then sends confirm=true
        if body.get("confirm") is not True:
            return jsonify({
                "error": "A new run starts only after you confirm it.",
                "state": view(state),
            }), 400
        fresh = logic.new_state(logic.new_seed())
        db.save_new_run(fresh)
        return jsonify({
            "message": f"New run started: day 1, {logic.fmt(logic.STARTING_CASH)}, no stock.",
            "state": view(fresh),
        })


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=False)
