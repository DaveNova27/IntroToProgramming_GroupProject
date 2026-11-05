"""Stored state: what is written to disk and loaded again after a restart.

A Python variable disappears when the app stops. This file saves the run in a
small SQLite database (one file, built into Python, no server needed).

Each save happens in ONE transaction: either everything is written, or nothing.
That is how cash, stock and the day's result always stay consistent.
"""

import json
import sqlite3
from pathlib import Path

import logic
import world

DEFAULT_PATH = Path(__file__).parent / "data" / "campus_tycoon.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS run (
    id   INTEGER PRIMARY KEY CHECK (id = 1),   -- only one run at a time
    day  INTEGER NOT NULL,
    cash INTEGER NOT NULL CHECK (cash >= 0)    -- cents, never negative
);
CREATE TABLE IF NOT EXISTS products (
    product TEXT PRIMARY KEY,
    stock   INTEGER NOT NULL CHECK (stock >= 0),
    price   INTEGER NOT NULL CHECK (price > 0)
);
CREATE TABLE IF NOT EXISTS history (
    day    INTEGER PRIMARY KEY,                -- a day can only be stored once
    result TEXT NOT NULL                       -- the day's result as JSON
);
CREATE TABLE IF NOT EXISTS player (
    id   INTEGER PRIMARY KEY CHECK (id = 1),   -- one figure, in map tiles
    zone TEXT NOT NULL,
    x    REAL NOT NULL,
    y    REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS shops (
    shop         TEXT PRIMARY KEY,
    unlocked     INTEGER NOT NULL CHECK (unlocked IN (0, 1)),
    level        INTEGER NOT NULL CHECK (level >= 0),
    staff_places INTEGER NOT NULL CHECK (staff_places >= 0)
);
CREATE TABLE IF NOT EXISTS shop_products (    -- the products a shop has, one row each
    shop    TEXT NOT NULL,
    product TEXT NOT NULL,
    PRIMARY KEY (shop, product)
);
"""


def connect(path=DEFAULT_PATH):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    return conn


def load(path=DEFAULT_PATH):
    """Return the saved run, or None if there is no save yet."""
    with connect(path) as conn:
        row = conn.execute("SELECT day, cash FROM run WHERE id = 1").fetchone()
        if row is None:
            return None
        day, cash = row
        products = conn.execute("SELECT product, stock, price FROM products").fetchall()
        history = conn.execute("SELECT result FROM history ORDER BY day").fetchall()
        player = conn.execute("SELECT zone, x, y FROM player WHERE id = 1").fetchone()
        shop_rows = conn.execute(
            "SELECT shop, unlocked, level, staff_places FROM shops").fetchall()
        shop_products = conn.execute("SELECT shop, product FROM shop_products").fetchall()
    # products added to the catalogue after the save was made start with stock 0
    stock = {pid: 0 for pid in logic.CATALOGUE}
    prices = {pid: item["ref_price"] for pid, item in logic.CATALOGUE.items()}
    for p, s, pr in products:
        if p in logic.CATALOGUE:
            stock[p], prices[p] = s, pr
    return {
        "day": day,
        "cash": cash,
        "stock": stock,
        "prices": prices,
        "shops": _shops(shop_rows, shop_products, [p for p, _, _ in products]),
        "history": [json.loads(r) for (r,) in history],
        "player": _player(player),
    }


def _shops(rows, shop_products, saved_products):
    """The shops of the run. A save from before shops existed (no rows) becomes a run
    where every shop that fits the products that save already had is open with them."""
    shops = {sid: logic._new_shop(sid) for sid in logic.SHOPS}
    if not rows:
        # Every shop that can hold a product the old save had is opened with those
        # products; the first shop is always open. Products that no longer exist are dropped.
        for sid in logic.SHOPS:
            have = [p for p in logic.CATALOGUE
                    if p in saved_products and p in logic.shop_product_ids(sid)]
            if have:
                shops[sid] = {"unlocked": True, "level": len(have),
                              "products": have, "staff_places": 0}
        return shops
    for sid, unlocked, level, staff in rows:
        if sid in shops:
            shops[sid] = {
                "unlocked": bool(unlocked),
                "level": level,
                "products": [p for p in logic.CATALOGUE
                             if (sid, p) in set(shop_products)],
                "staff_places": staff,
            }
    return shops


def _player(row):
    """Where the player stands. A save from before the world existed has no position,
    and a zone may be gone after the map changed: then start at the spawn."""
    if row is None or row[0] not in world.ZONES:
        return world.start_player()
    return {"zone": row[0], "x": row[1], "y": row[2]}


def save(state, path=DEFAULT_PATH):
    """Write the whole run in one transaction."""
    conn = connect(path)
    try:
        with conn:  # commits on success, rolls back on any error
            _write(conn, state)
    finally:
        conn.close()


def save_new_run(state, path=DEFAULT_PATH):
    """Replace the saved run with a new one (CT01).

    save() never removes a stored day, so the old history is deleted here,
    in the same transaction: either the new run is saved completely, or the
    old run stays exactly as it was.
    """
    conn = connect(path)
    try:
        with conn:
            conn.execute("DELETE FROM history")
            _write(conn, state)
    finally:
        conn.close()


def _write(conn, state):
    """Write day, cash, stock, prices, shops, player and new history records (inside a transaction)."""
    conn.execute(
        "INSERT INTO run (id, day, cash) VALUES (1, ?, ?) "
        "ON CONFLICT(id) DO UPDATE SET day = excluded.day, cash = excluded.cash",
        (state["day"], state["cash"]),
    )
    conn.execute(
        "INSERT INTO player (id, zone, x, y) VALUES (1, ?, ?, ?) "
        "ON CONFLICT(id) DO UPDATE SET zone = excluded.zone, x = excluded.x, y = excluded.y",
        (state["player"]["zone"], state["player"]["x"], state["player"]["y"]),
    )
    for pid in state["stock"]:
        conn.execute(
            "INSERT INTO products (product, stock, price) VALUES (?, ?, ?) "
            "ON CONFLICT(product) DO UPDATE SET stock = excluded.stock, "
            "price = excluded.price",
            (pid, state["stock"][pid], state["prices"][pid]),
        )
    conn.execute("DELETE FROM shop_products")
    for sid, shop in state["shops"].items():
        conn.execute(
            "INSERT INTO shops (shop, unlocked, level, staff_places) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(shop) DO UPDATE SET unlocked = excluded.unlocked, "
            "level = excluded.level, staff_places = excluded.staff_places",
            (sid, int(shop["unlocked"]), shop["level"], shop["staff_places"]),
        )
        for pid in shop["products"]:
            conn.execute(
                "INSERT INTO shop_products (shop, product) VALUES (?, ?)", (sid, pid))
    for result in state["history"]:
        # INSERT OR IGNORE: an already stored day is never written twice
        conn.execute(
            "INSERT OR IGNORE INTO history (day, result) VALUES (?, ?)",
            (result["day"], json.dumps(result)),
        )
