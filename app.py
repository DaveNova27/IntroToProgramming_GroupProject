"""The screen: a small web server plus the dashboard in static/.

The browser never decides anything. Every click is sent here, the rule in
logic.py decides, and only an accepted action is saved by db.py. Each request
loads the run fresh from the database: the database is the truth, so a browser
refresh or a double click cannot repeat a day.

Run it with:  uv run python app.py   (then open http://127.0.0.1:8000)

Public mode (specs/deploy-ready.md): with CT_PUBLIC=1 every player gets a run of their own (a cookie),
the number of requests is limited, the dev switches are off and the cookie is signed and Secure. Without it
nothing changes: one run on this computer.
"""

import hashlib
import hmac
import os
import re
import secrets
import threading
import time
from collections import deque

from flask import Flask, abort, g, has_request_context, jsonify, redirect, request, send_from_directory
from werkzeug.exceptions import HTTPException

import db
import guests
import logic
import world

app = Flask(__name__, static_folder="static", static_url_path="/static")
# Let the browser re-check the page files on every load (a cheap "not modified"
# answer), so an updated dashboard or map is never served from an old cache.
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
_locks = [threading.Lock() for _ in range(64)]  # one change at a time per run: load -> rule -> save


def run_lock():
    """The lock of this player's run (a stripe of 64, so players hardly wait for each other). Without
    public mode there is one run and one lock."""
    player = getattr(g, "player", None)
    return _locks[0 if player is None else int.from_bytes(hashlib.sha256(player.encode()).digest()[:2], "big") % 64]

# ---- public mode (specs/deploy-ready.md) ---------------------------------------------------------
PLAYER_COOKIE = "ct_player"
PLAYER_ID = re.compile(r"[A-Za-z0-9_-]{22}")  # what secrets.token_urlsafe(16) gives: nothing else is a file name
PLAYERS_DIR = db.DEFAULT_PATH.parent / "players"
MAX_PLAYERS = 2000  # runs on disk; a new run beyond it is refused ("the game is full")
RATE_LIMIT = 240  # API requests per player and window (a played day needs about 60 a minute)
RATE_WINDOW = 60  # seconds
NEW_PLAYER_LIMIT = 60  # new players per address and window (a class on one network, a crawler)
MAX_KEYS = 20_000  # counters kept at once; beyond it a new key is refused until old ones have gone quiet
_hits = {}  # key -> recent request times
_hits_lock = threading.Lock()
_last_sweep = [0.0]
_create_lock = threading.Lock()  # a new run is made one at a time, so the cap is a hard one


class Busy(Exception):
    """Too many players are being counted at once: not this player's fault, try again later."""
_secret_cache = []


def public_mode():
    """The server is open to other people (CT_PUBLIC=1): one run per player, limits, no dev switches."""
    return os.environ.get("CT_PUBLIC") == "1"


def behind_proxy():
    """CT_PROXY=1: a proxy that we trust (and only it can reach us) says who the visitor is and
    whether it was HTTPS. Without it those headers are ignored: anybody can write them."""
    return os.environ.get("CT_PROXY") == "1"


def client_address():
    if behind_proxy():
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            return forwarded.split(",")[-1].strip()  # the address our proxy saw
    return request.remote_addr


def is_https():
    if behind_proxy():
        return request.headers.get("X-Forwarded-Proto", "").lower() == "https"
    return request.is_secure


_secret_lock = threading.Lock()


_dirs_made = set()


def _ensure_players_dir():
    if PLAYERS_DIR not in _dirs_made:  # once, not on every request
        PLAYERS_DIR.mkdir(parents=True, exist_ok=True)
        _dirs_made.add(PLAYERS_DIR)


def _secret():
    """The key that signs the player cookies: CT_SECRET, else a random one kept in the players folder.
    Made once, under a lock, and written whole before anybody can read it (never half a key)."""
    if os.environ.get("CT_SECRET"):
        return os.environ["CT_SECRET"].encode()
    with _secret_lock:
        if _secret_cache and _secret_cache[0][0] == PLAYERS_DIR:
            return _secret_cache[0][1]
        _ensure_players_dir()
        path = PLAYERS_DIR / ".secret"
        if not path.exists():
            temp = PLAYERS_DIR / f".secret.{secrets.token_hex(4)}"
            fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as handle:
                handle.write(secrets.token_bytes(32))
            try:
                os.link(temp, path)  # fails if another process was first: then its key stands
            except FileExistsError:
                pass
            finally:
                os.unlink(temp)
        _secret_cache[:] = [(PLAYERS_DIR, path.read_bytes())]
        return _secret_cache[0][1]


def _sign(player_id):
    return hmac.new(_secret(), player_id.encode(), hashlib.sha256).hexdigest()[:32]


def _player_from_cookie(cookie):
    """The player id of a cookie we issued ("<id>.<signature>"), else None. A forged or altered
    cookie is no cookie."""
    player_id, _, signature = cookie.partition(".")
    if PLAYER_ID.fullmatch(player_id) and hmac.compare_digest(signature, _sign(player_id)):
        return player_id
    return None


def _too_many(key, limit):
    """Count this request for the key; True when the limit of the window is used up (or too many
    keys are being counted at once)."""
    now = time.monotonic()
    with _hits_lock:
        if len(_hits) >= MAX_KEYS and key not in _hits:
            # sweep the quiet keys (at most once a second, the scan is long); if still full: busy
            if now - _last_sweep[0] >= 1:
                _last_sweep[0] = now
                for old in [k for k, v in _hits.items() if not v or now - v[-1] > RATE_WINDOW]:
                    del _hits[old]
            if len(_hits) >= MAX_KEYS:
                raise Busy()
        times = _hits.setdefault(key, deque())
        while times and now - times[0] > RATE_WINDOW:
            times.popleft()
        if len(times) >= limit:
            return True
        times.append(now)
        return False


def _player_file(player_id):
    return PLAYERS_DIR / f"{player_id}.db"


@app.before_request
def identify_player():
    try:
        return _identify_player()
    except Busy:
        return jsonify({"error": "The game is busy right now. Try again in a minute."}), 503


def _identify_player():
    """Public mode: who is this player (a cookie we signed, or a new one for a page), and is it too much."""
    g.player, g.new_player = None, False
    if not public_mode():
        return None
    _ensure_players_dir()
    g.player = _player_from_cookie(request.cookies.get(PLAYER_COOKIE, ""))
    if g.player is None:
        if request.path.startswith("/api/"):
            # an API call without our cookie is no browser of ours: no run is made for it
            return jsonify({"error": "Open the game page first (the game needs cookies)."}), 400
        if request.path not in ("/", "/map"):
            return None  # files, icons and probes get no player
        if _too_many(("new", client_address()), NEW_PLAYER_LIMIT):
            return jsonify({"error": "Too many new players from this address. Try again in a minute."}), 429
        g.player, g.new_player = secrets.token_urlsafe(16), True
    if request.path.startswith("/api/") and _too_many(("player", g.player), RATE_LIMIT):
        return jsonify({"error": "Too many requests. Slow down a little."}), 429
    return None


SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "SAMEORIGIN",  # the campus is an iframe of our own page
    "Referrer-Policy": "no-referrer",
    # only our own files; inline styles are used for colours (style="--accent: ..."), nothing else inline
    "Content-Security-Policy": (
        "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; "
        "frame-src 'self'; frame-ancestors 'self'; connect-src 'self'; object-src 'none'; "
        "base-uri 'none'; form-action 'self'"
    ),
}


@app.after_request
def add_headers(response):
    for name, value in SECURITY_HEADERS.items():
        response.headers.setdefault(name, value)
    if is_https():
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
    if getattr(g, "new_player", False):
        response.set_cookie(PLAYER_COOKIE, f"{g.player}.{_sign(g.player)}", max_age=365 * 24 * 3600,
                            httponly=True, samesite="Lax", secure=is_https() or None)
    return response


@app.errorhandler(Exception)
def unexpected_error(error):
    """Only our own words reach the player: never a path or a stack trace (roadmap 3a, point 6)."""
    if isinstance(error, HTTPException):
        if request.path.startswith("/api/") and error.code and error.code >= 400:
            # the screens read every API answer as JSON; the headers of the error (Allow, Retry-After) stay
            response = jsonify({"error": error.description or error.name})
            response.status_code = error.code
            for name, value in error.get_headers():
                if name.lower() not in ("content-type", "content-length"):
                    response.headers[name] = value
            return response
        return error
    app.logger.exception("unexpected error")
    return jsonify({"error": "The server hit an error. Nothing was saved."}), 500


def _db_kw():
    """The database of this player in public mode, the one run of this computer otherwise."""
    return {"path": _player_file(g.player)} if getattr(g, "player", None) else {}


def load_run():
    """Load the saved run, or start and save a fresh one (first start). In public mode a new run
    is refused (503) once MAX_PLAYERS runs exist."""
    if getattr(g, "player", None) and not _player_file(g.player).exists():
        with _create_lock:  # one new run at a time: the cap is a hard one
            if sum(1 for _ in PLAYERS_DIR.glob("*.db")) >= MAX_PLAYERS:
                abort(503, description="The game is full right now. Try again later.")
            state = logic.new_state(logic.new_seed())
            db.save(state, **_db_kw())  # the file exists before the lock is let go
            return state
    state = db.load(**_db_kw())
    if state is None:
        state = logic.new_state(logic.new_seed())
        db.save(state, **_db_kw())
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
            "unlock_warning": None if mine["unlocked"] else logic.purchase_warning(state, sid),
            "hint": logic.shop_hint(state, sid),
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
        "staffed": bool(shift.get("staffed")),
        "crews": [{"shop": sid, "counter": sub["counter"], "sold": sub["sold"], "lost": sub["lost"],
                   "over": bool(sub.get("over"))} for sid, sub in sorted(shift.get("extra", {}).items())],
        "counter": shift["counter"],
        "counter_space": size - sum(shift["counter"].values()),
        "counter_size": size,
        "waiting": waiting,
        "sold": shift["sold"],
        "lost": shift["lost"],
    }


def guests_view(state):
    """Today's guests for the screen (specs/guests.md): only while the day is open. Per running
    shop how many come and why, and the guests that are on their way or waiting now (at most
    guests.MAX_VISIBLE_GUESTS, by id). Never a guest who has not set off yet, never the seed."""
    shift = state["shift"]
    if logic.is_finished(state) or shift is None:
        return None
    tick = shift["tick"]
    parts = [part for part in [shift, *(shift.get("extra", {})[sid] for sid in sorted(shift.get("extra", {})))]
             if part["shop"]]
    # every running shop gets its share of the figures; within a shop the first to set off are
    # drawn, so a figure stays drawn until it is served or gives up
    share = guests.MAX_VISIBLE_GUESTS // max(1, len(parts))  # at most 4 shops: 3 or more each
    shops, walking = [], []
    for part in parts:
        shop, summary = part["shop"], part.get("guests")
        if summary:
            shops.append({"shop": shop, "name": logic.SHOPS[shop]["name"], "total": summary["total"],
                          "came": summary["came"], "left": summary["left"],
                          "thoughts": summary["thoughts"]})
        line, mine = 0, []
        for customer in part["queue"]:  # served guests and those who gave up are no longer in it
            guest = customer.get("guest")
            if guest is None or customer["arrives"] - guest["walk"] > tick:
                continue
            here = customer["arrives"] <= tick
            mine.append({
                "id": guest["id"], "kind": guest["kind"], "shop": shop, "start": guest["start"],
                "depart": customer["arrives"] - guest["walk"], "arrives": customer["arrives"],
                "until": customer["patience_until"], "line": line if here else None,
                "thought": guest["thought"], "switched": guest["wish"] != shop,
            })
            line += 1 if here else 0
        walking += sorted(mine, key=lambda g: (g["depart"], g["id"]))[:share]
    running = {part["shop"] for part in parts}
    return {"tick": tick, "shops": shops, "walking": walking[:guests.MAX_VISIBLE_GUESTS],
            # a shift is running: the map shows the guests (the passers-by step aside only then)
            "active": any(not part.get("over") for part in parts),
            # only the shops the player can start a shift in: for the others nothing is waited for
            "waiting_shops": [sid for sid in shift.get("guest_shops", [])
                              if sid not in running and sid in logic.SHIFT_SHOPS]}


def staff_view(state):
    """The employees and the places of the shops where they can work, prices from the rules."""
    employees = []
    for e in state["employees"]:
        level = e["level"]
        employees.append({
            "id": e["id"], "name": e["name"], "shop": e["shop"], "place": e["place"],
            "job": e["job"], "job_name": logic.JOBS[e["job"]]["name"],
            "level": level, "working": e["working"], "wage": logic.employee_wage(e),
            "upgrade_price": (logic.UPGRADE_PRICES[level + 1]
                              if level < logic.EMPLOYEE_MAX_LEVEL else None),
        })
    # an open day pays only the shops that run a shift; before it every unlocked shop would
    shift = state["shift"]
    paid_shops = ({s for s in [shift["shop"], *shift.get("extra", {})] if s} if shift
                  else {sid for sid, shop in state["shops"].items() if shop["unlocked"]})
    places = []
    for shop in logic.STAFF_SHOPS:
        taken = {e["place"]: e["id"] for e in state["employees"] if e["shop"] == shop}
        for place, job in enumerate(logic.SHOPS[shop]["jobs"], start=1):
            places.append({
                "shop": shop, "place": place, "job": job,
                "job_name": logic.JOBS[job]["name"],
                "bought": place <= state["shops"][shop]["staff_places"],
                "employee": taken.get(place),
            })
    return {
        "hire_price": logic.HIRE_PRICE,
        "max_level": logic.EMPLOYEE_MAX_LEVEL,
        "employees": employees,
        "places": places,
        "wages_today": sum(e["wage"] for e in employees
                           if e["working"] and e["shop"] in paid_shops),
    }


def weather_view(state):
    """Today's real weather for the screen: only once the day is open (before that the
    outlook is all the player gets) and none once the season is over.
    The seed itself never leaves the server."""
    if logic.is_finished(state) or state.get("shift") is None:
        return None
    context = logic.day_context(state)
    return {
        "id": context["weather"],
        "name": logic.WEATHER[context["weather"]]["name"],
        "temperature": context["temperature"],
        "demand_percent": context["demand_percent"],
    }


def event_view(state):
    """Today's event for the screen, with the weather's rule: only once the day is open and
    none once the season is over. None when there is no event."""
    if logic.is_finished(state) or state.get("shift") is None:
        return None
    return logic.day_context(state)["event"]


def outlook_view(state):
    """The forecast for the screen: today before the day is opened, tomorrow while it is
    open (none when there is no such day), with a tip per open shop.
    Only what the forecast shows: never whether it is right."""
    forecast = logic.outlook(state)
    if forecast is None:
        return None
    low, high = forecast["temp_range"]
    return {
        "day": forecast["day"],
        "id": forecast["weather"],
        "name": logic.WEATHER[forecast["weather"]]["name"],
        "temp_low": low,
        "temp_high": high,
        "miss_percent": forecast["miss_percent"],
        "tips": [dict(tip, name=logic.SHOPS[tip["shop"]]["name"])
                 for tip in logic.outlook_tips(state, forecast)],
    }


def editor_info(state):
    """What the editor panel offers (ids and limits from the rules, never from the screen)."""
    return {
        "weather": [{"id": wid, "name": w["name"]} for wid, w in logic.WEATHER.items()],
        # the fixed weather (none: the seed's), for the dropdown; the real weather of the
        # day is not in the answer before the day is open
        "weather_override": (state["day_override"] or {}).get("weather"),
        "events": [{"id": eid, "name": e["name"]} for eid, e in logic.EVENTS.items()],
        "event_override": (state["day_override"] or {}).get("event"),
        "max_level": {sid: 1 + len(shop["window"]) for sid, shop in logic.SHOPS.items()},
        "max_cash": logic.MAX_CASH,
        "max_seed": logic.MAX_SEED,
        "storage": logic.STORAGE_UNITS,
    }


def product_view(state, pid, finished):
    item = logic.CATALOGUE[pid]
    # why the product has the customers it has today (None once the season is over)
    breakdown = None if finished else logic.customer_breakdown(state, pid)
    return {
        "id": pid,
        "name": item["name"],
        "cost": item["cost"],
        "ref_price": item["ref_price"],
        "price": state["prices"][pid],
        "stock": state["stock"][pid],
        "shop": logic.shop_of_product(pid),
        "customers": 0 if finished else breakdown["customers"],
        "breakdown": breakdown,
    }


# Each shop's curve on a neutral day, for drawing the meter. Constant, so worked out once.
PRICE_CURVES = {sid: logic.shop_price_curve(sid) for sid in logic.SHOPS}


def view(state):
    """Everything the dashboard shows, calculated by the rules, never by the browser."""
    finished = logic.is_finished(state)
    editor_on = has_request_context() and editor_switch_on()
    owned = logic.owned_products(state)
    # the numbers of customers come from what the player may know: before the day is opened
    # that is the forecast, never the real weather (hidden-weather)
    known = logic.known_state(state)
    products = [product_view(known, pid, finished) for pid in logic.CATALOGUE if pid in owned]
    return {
        "day": state["day"],
        "last_day": logic.LAST_DAY,
        "finished": finished,
        "starting_cash": logic.STARTING_CASH,
        "cash": state["cash"],
        "stock_value": logic.stock_value(state),
        "stock_overview": logic.stock_overview(known),
        "overall_gain": logic.overall_gain(state),
        "products": products,
        "shops": shops_view(state),
        # trade_day returns a new state and leaves the saved one alone,
        # so it doubles as a preview of "what happens if I open now".
        "forecast": None if finished or logic.day_is_open(state) else logic.trade_day(known)[1],
        "weather": weather_view(state),
        "event": event_view(state),
        "outlook": outlook_view(state),
        "editor": editor_on,
        "editor_info": editor_info(state) if editor_on else None,
        "shift": shift_view(state),
        "guests": guests_view(state),
        "staff": staff_view(state),
        "shift_shops": list(logic.SHIFT_SHOPS),
        "history": state["history"],
        "badges": logic.badges_view(state),
        "player": state["player"],
        "base_customers": logic.BASE_CUSTOMERS,
        "segments": [{"id": sid, "name": seg["name"]} for sid, seg in logic.SEGMENTS.items()],
        "price_curves": PRICE_CURVES,
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
    with run_lock():
        state = load_run()
        try:
            new_state, message = action(state)
        except logic.RejectedAction as reason:
            # nothing is saved; the dashboard gets the unchanged run back
            return jsonify({"error": str(reason), "state": view(state)}), 400
        # a badge is reached the moment its condition is true, e.g. at the first sale
        # (specs/badges.md); only the server gives it, never from the request
        logic.award_badges(new_state)
        db.save(new_state, **_db_kw())
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
    with run_lock():
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


@app.post("/api/price_preview")
def price_preview():
    """What a price would bring today. Read-only: nothing is saved."""
    body = json_body()
    with run_lock():
        state = load_run()
        try:
            price = logic.euros_to_cents(body.get("price", ""))
            return jsonify({"preview": logic.price_preview(logic.known_state(state), body.get("product"), price)})
        except logic.RejectedAction as reason:
            return jsonify({"error": str(reason)}), 400


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


@app.post("/api/staff/hire")
def hire():
    body = json_body()

    def action(state):
        shop, place = body.get("shop"), body.get("place")
        new_state = logic.hire(state, shop, place)
        who = new_state["employees"][-1]
        return new_state, (f"{who['name']} hired as {logic.JOBS[who['job']]['name']} for "
                           f"{logic.fmt(state['cash'] - new_state['cash'])}.")

    return apply(action)


@app.post("/api/staff/upgrade")
def upgrade_employee():
    body = json_body()

    def action(state):
        employee_id = body.get("employee_id")
        new_state = logic.upgrade_employee(state, employee_id)
        who = next(e for e in new_state["employees"] if e["id"] == employee_id)
        return new_state, (f"{who['name']} is on level {who['level']} now for "
                           f"{logic.fmt(state['cash'] - new_state['cash'])}.")

    return apply(action)


@app.post("/api/staff/fire")
def fire_employee():
    body = json_body()

    def action(state):
        employee_id = body.get("employee_id")
        new_state = logic.fire_employee(state, employee_id)
        who = next(e for e in state["employees"] if e["id"] == employee_id)
        return new_state, f"{who['name']} was dismissed."

    return apply(action)


def local_request():
    """True only for a request from this computer, with no proxy in between."""
    # a proxy in front would make every client look local: refuse when one has been involved
    if request.headers.get("X-Forwarded-For") or request.headers.get("Forwarded"):
        return False
    if request.remote_addr not in ("127.0.0.1", "::1", "::ffff:127.0.0.1"):
        return False
    # DNS rebinding: a web page can point its own name at 127.0.0.1, so the Host must be local too
    host = request.host.rsplit(":", 1)[0] if not request.host.endswith("]") else request.host
    return host in ("127.0.0.1", "localhost", "[::1]")


def demo_switch_on():
    """The weather override is a demo hook: only with the switch on and from this computer."""
    return os.environ.get("CAMPUS_TYCOON_DEMO") == "1" and local_request() and not public_mode()


def editor_switch_on():
    """The editor mode (specs/editor-mode.md): CT_EDITOR=1 and a request from this computer."""
    return os.environ.get("CT_EDITOR") == "1" and local_request() and not public_mode()


def override_message(weather, event):
    """What the demo switch and the editor tell after fixing (or clearing) weather and event."""
    if weather is None and event is None:
        return "Weather and event back to the seed's."
    parts = []
    if weather is not None:
        parts.append(f"Weather fixed to {logic.WEATHER[weather]['name']}.")
    if event == "none":
        parts.append("No event.")
    elif event is not None:
        parts.append(f"Event fixed to {logic.EVENTS[event]['name']}.")
    else:
        parts.append("No event (only the weather is fixed).")
    return " ".join(parts)


@app.post("/api/day-override")
def day_override():
    body = json_body()

    def action(state):
        if not demo_switch_on():
            raise logic.RejectedAction("The weather override is a demo switch and is off.")
        weather, event = body.get("weather"), body.get("event")
        new_state = logic.set_day_override(state, weather, event)
        return new_state, override_message(weather, event)

    return apply(action)


def editor_action(rule):
    """Run an editor rule on the saved run: only with the switch on, saved with save_new_run
    (an edit may move the day back and cut the history). Nothing is saved when refused."""
    with run_lock():
        state = load_run()
        try:
            if not editor_switch_on():
                raise logic.RejectedAction("The editor is off.")
            new_state, message = rule(state)
        except logic.RejectedAction as reason:
            return jsonify({"error": str(reason), "state": view(state)}), 400
        logic.award_badges(new_state)  # e.g. cash set to 1,000 euro gives "Wealthy" at once
        db.save_new_run(new_state, **_db_kw())
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
        weather, event = body.get("weather"), body.get("event")
        new_state = logic.set_day_override(state, weather, event)
        return new_state, override_message(weather, event)

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
    with run_lock():
        state = load_run()
        # CT01: the page asks the player first and only then sends confirm=true
        if body.get("confirm") is not True:
            return jsonify({
                "error": "A new run starts only after you confirm it.",
                "state": view(state),
            }), 400
        fresh = logic.new_state(logic.new_seed())
        db.save_new_run(fresh, **_db_kw())
        return jsonify({
            "message": f"New run started: day 1, {logic.fmt(logic.STARTING_CASH)}, no stock.",
            "state": view(fresh),
        })


if __name__ == "__main__":
    # CT_HOST and CT_PORT are for the public mode behind a proxy; the default stays this computer only.
    # For people other than you use a production server, see specs/deploy-ready.md.
    app.run(host=os.environ.get("CT_HOST", "127.0.0.1"), port=int(os.environ.get("CT_PORT", "8000")), debug=False)
