"""Stored state: what is written to disk and loaded again after a restart.

A Python variable disappears when the app stops. This file saves the run in a
small SQLite database (one file, built into Python, no server needed).

Each save happens in ONE transaction: either everything is written, or nothing.
That is how cash, stock and the day's result always stay consistent.
"""

import json
import sqlite3
from pathlib import Path

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
    return {
        "day": day,
        "cash": cash,
        "stock": {p: s for p, s, _ in products},
        "prices": {p: pr for p, _, pr in products},
        "history": [json.loads(r) for (r,) in history],
    }


def save(state, path=DEFAULT_PATH):
    """Write the whole run in one transaction."""
    conn = connect(path)
    try:
        with conn:  # commits on success, rolls back on any error
            conn.execute(
                "INSERT INTO run (id, day, cash) VALUES (1, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET day = excluded.day, cash = excluded.cash",
                (state["day"], state["cash"]),
            )
            for pid in state["stock"]:
                conn.execute(
                    "INSERT INTO products (product, stock, price) VALUES (?, ?, ?) "
                    "ON CONFLICT(product) DO UPDATE SET stock = excluded.stock, "
                    "price = excluded.price",
                    (pid, state["stock"][pid], state["prices"][pid]),
                )
            for result in state["history"]:
                # INSERT OR IGNORE: an already stored day is never written twice
                conn.execute(
                    "INSERT OR IGNORE INTO history (day, result) VALUES (?, ?)",
                    (result["day"], json.dumps(result)),
                )
    finally:
        conn.close()
