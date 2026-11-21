"""Stored state on the public server: every player's run in Postgres (specs/persistent-runs.md).

Used only when the server is public (CT_PUBLIC=1) and DATABASE_URL is set; otherwise db.py stores the
runs in SQLite files as before. A run is one JSON document, the same state dict that logic.py works
with. On its way in and out every state goes through db.through_sqlite(), so the SQLite tables'
CHECKs and repairs apply here too and no rule is written twice.

The server keeps the runs it has loaded in memory and writes every change through to Postgres first.
That is safe only because exactly one process serves the game (one gunicorn worker, one instance:
render.yaml) and every change of a run happens under that player's lock (app.run_lock()).
"""

import copy
import json
import os
import threading
from collections import OrderedDict

import db

SCHEMA = "campus_tycoon"
CACHE_SIZE = 500  # runs kept in memory; the least recently used one is dropped and loaded again
POOL_MIN, POOL_MAX = 1, 4  # one worker with 8 threads needs only a few connections
WAIT = 5  # seconds a request waits for a connection before the storage counts as unreachable
SCHEMA_LOCK_KEY = 4_770_093  # a fixed number for pg_advisory_xact_lock while the table is made

SCHEMA_SQL = [
    f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}",
    f"""CREATE TABLE IF NOT EXISTS {SCHEMA}.runs (
        player_id  text PRIMARY KEY CHECK (player_id ~ '^[A-Za-z0-9_-]{{22}}$'),
        state      jsonb NOT NULL,
        updated_at timestamptz NOT NULL DEFAULT now()
    )""",
    # Supabase's Data API must never see the runs: own schema, RLS without any policy, no grants
    f"ALTER TABLE {SCHEMA}.runs ENABLE ROW LEVEL SECURITY",
    f"REVOKE ALL ON SCHEMA {SCHEMA} FROM PUBLIC",
    f"REVOKE ALL ON ALL TABLES IN SCHEMA {SCHEMA} FROM PUBLIC",
]
API_ROLES = ("anon", "authenticated")  # Supabase's Data API roles (they exist only on Supabase)


class Unavailable(Exception):
    """The database cannot be reached (paused, network, password): nothing was saved."""


_lock = threading.Lock()  # guards the pool, the schema flag and the copies in memory
_pool = None  # (url, pool) of the current DATABASE_URL
_schema_ready = False
_cache = OrderedDict()  # player id -> state, most recently used last


def url():
    return os.environ.get("DATABASE_URL", "")


def enabled():
    """A database is configured (the caller decides whether the server is public)."""
    return bool(url())


def conninfo(raw):
    """The connection string with TLS required when it does not say otherwise (Supabase: most
    drivers default to "prefer", which falls back to plain text)."""
    from psycopg.conninfo import conninfo_to_dict, make_conninfo
    params = conninfo_to_dict(raw)
    params.setdefault("sslmode", "require")
    params.setdefault("connect_timeout", WAIT)
    return make_conninfo(**params)


def _get_pool():
    global _pool, _schema_ready
    from psycopg_pool import ConnectionPool
    with _lock:
        current = url()
        if _pool is None or _pool[0] != current:
            if _pool is not None:  # another database (tests): start clean
                _pool[1].close()
                _schema_ready = False
                _cache.clear()
            try:
                info = conninfo(current)
            except Exception:  # psycopg quotes a piece of the string, which may be part of the password
                raise Unavailable("DATABASE_URL is not a valid connection string") from None
            pool = ConnectionPool(info, min_size=POOL_MIN, max_size=POOL_MAX, timeout=WAIT,
                                  check=ConnectionPool.check_connection, open=False,
                                  name="campus-tycoon")
            pool.open(wait=False)  # never block the start of the server on the database
            _pool = (current, pool)
        return _pool[1]


def _run(work):
    """Run work(conn) in one transaction (committed on success, rolled back on any error). An
    unreachable database raises Unavailable; any other error stays what it is."""
    import psycopg
    from psycopg_pool import PoolTimeout
    try:
        with _get_pool().connection() as conn:
            _ensure_schema(conn)
            return work(conn)
    except (psycopg.OperationalError, psycopg.InterfaceError, PoolTimeout) as error:
        raise Unavailable() from error


def _ensure_schema(conn):
    """Make the schema and the table once per process; a second start changes nothing."""
    global _schema_ready
    if _schema_ready:
        return
    with conn.transaction():
        conn.execute("SELECT pg_advisory_xact_lock(%s)", (SCHEMA_LOCK_KEY,))  # one maker at a time
        for statement in SCHEMA_SQL:
            conn.execute(statement)
        for role in API_ROLES:
            if conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,)).fetchone():
                conn.execute(f"REVOKE ALL ON SCHEMA {SCHEMA} FROM {role}")
                conn.execute(f"REVOKE ALL ON ALL TABLES IN SCHEMA {SCHEMA} FROM {role}")
    _schema_ready = True


def _remember(player_id, state):
    with _lock:
        _cache[player_id] = copy.deepcopy(state)
        _cache.move_to_end(player_id)
        while len(_cache) > CACHE_SIZE:
            _cache.popitem(last=False)


def _recall(player_id):
    with _lock:
        if player_id not in _cache:
            return None
        _cache.move_to_end(player_id)
        return copy.deepcopy(_cache[player_id])  # the caller may change it; the copy stays as saved


def load(player_id):
    """This player's run, or None if there is none."""
    state = _recall(player_id)
    if state is not None:
        return state
    row = _run(lambda conn: conn.execute(
        f"SELECT state FROM {SCHEMA}.runs WHERE player_id = %s", (player_id,)).fetchone())
    if row is None:
        return None
    state = db.through_sqlite(row[0])  # repaired like an old SQLite file (removed products, shops...)
    _remember(player_id, state)
    return copy.deepcopy(state)


def save(state, player_id):
    """Write the whole run in one statement; the copy in memory changes only after it worked. A new run
    is the same call: the document is always written whole, so the old days go with it."""
    clean = db.through_sqlite(state)  # a state that breaks a CHECK raises here: nothing is sent
    document = json.dumps(clean)
    _run(lambda conn: conn.execute(
        f"INSERT INTO {SCHEMA}.runs (player_id, state, updated_at) VALUES (%s, %s::jsonb, now()) "
        "ON CONFLICT (player_id) DO UPDATE SET state = excluded.state, updated_at = now()",
        (player_id, document)))
    _remember(player_id, clean)


def exists(player_id):
    with _lock:
        if player_id in _cache:
            return True
    return _run(lambda conn: conn.execute(
        f"SELECT 1 FROM {SCHEMA}.runs WHERE player_id = %s", (player_id,)).fetchone()) is not None


def count():
    return _run(lambda conn: conn.execute(f"SELECT count(*) FROM {SCHEMA}.runs").fetchone()[0])


def oldest_idle(seconds, limit=1):
    """[(player id, idle seconds)] of the runs saved longest ago that were not saved for `seconds`, oldest
    first, at most `limit`. For a full game (specs/player-cap.md)."""
    rows = _run(lambda conn: conn.execute(
        f"SELECT player_id, EXTRACT(EPOCH FROM now() - updated_at) FROM {SCHEMA}.runs "
        "WHERE updated_at <= now() - make_interval(secs => %s) ORDER BY updated_at, player_id LIMIT %s",
        (seconds, limit)).fetchall())
    return [(player_id, float(idle)) for player_id, idle in rows]


def delete_if_idle(player_id, seconds):
    """Delete that run in one statement if it is still not saved for `seconds` (it may have been saved
    since it was picked), and forget the copy in memory. True if it was deleted."""
    row = _run(lambda conn: conn.execute(
        f"DELETE FROM {SCHEMA}.runs WHERE player_id = %s AND updated_at <= now() - make_interval(secs => %s) "
        "RETURNING player_id", (player_id, seconds)).fetchone())
    if row is not None:
        with _lock:
            _cache.pop(player_id, None)
    return row is not None


def reset():
    """Forget the pool, the schema flag and the copies in memory (tests; a "restart")."""
    global _pool, _schema_ready
    with _lock:
        if _pool is not None:
            _pool[1].close()
        _pool, _schema_ready = None, False
        _cache.clear()
