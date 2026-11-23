"""Checks from specs/persistent-runs.md: the runs of the public server in Postgres, checked and repaired
by the same SQLite code as a file, a copy in memory written through, and SQLite everywhere else.

The checks marked `needs_pg` talk to a real Postgres given by TEST_DATABASE_URL (CI starts one as a
service; on a laptop set it to a local Postgres). They never use DATABASE_URL from the environment."""

import copy
import os
import sqlite3
import sys
from pathlib import Path

import pytest

import app
import db
import logic
import pgstore
import scenarios

sys.path.insert(0, str(Path(__file__).parent))
from test_full_run import complete_run  # noqa: E402  (a whole 30-day season)

TEST_URL = os.environ.get("TEST_DATABASE_URL", "")
needs_pg = pytest.mark.skipif(not TEST_URL, reason="no test database (TEST_DATABASE_URL)")
CLOSED = "postgresql://nobody:secret-pw-123@127.0.0.1:1/none?sslmode=disable"  # nothing listens there


def file_roundtrip(state, tmp_path):
    path = tmp_path / f"run-{len(list(tmp_path.iterdir()))}.db"
    db.save(state, path=path)
    return db.load(path=path)


@pytest.fixture(autouse=True)
def clean_store(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)  # a variable in the shell must not reach a test
    pgstore.reset()
    yield
    pgstore.reset()


@pytest.fixture
def public(monkeypatch, tmp_path):
    monkeypatch.setenv("CT_PUBLIC", "1")
    monkeypatch.setattr(app, "PLAYERS_DIR", tmp_path / "players")
    app._hits.clear()
    return tmp_path / "players"


@pytest.fixture
def pg(monkeypatch):
    """A clean test database as the public server's DATABASE_URL."""
    import psycopg
    with psycopg.connect(TEST_URL, autocommit=True) as conn:
        conn.execute(f"DROP SCHEMA IF EXISTS {pgstore.SCHEMA} CASCADE")
        for role in pgstore.API_ROLES:  # Supabase's Data API roles, so the revoke can be checked
            if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,)).fetchone():
                conn.execute(f"CREATE ROLE {role} NOLOGIN")
    monkeypatch.setenv("DATABASE_URL", TEST_URL)
    pgstore.reset()
    return TEST_URL


def sql(query, params=()):
    import psycopg
    with psycopg.connect(TEST_URL, autocommit=True) as conn:
        return conn.execute(query, params).fetchall()


# ---- the same rules as SQLite (no database needed) -----------------------------------------------------


def staffed_run():
    return logic.buy_upgrade(logic.new_state(logic.new_seed()), "cafe", "staff_1")


def damaged_run():
    """A run saved by an older version: a product, a shop, a badge and a zone that no longer exist, a
    price far above the reference and an employee above the highest level."""
    state = staffed_run()
    state["stock"]["old_product"] = 4
    state["prices"]["old_product"] = 300
    state["prices"]["coffee"] = 50 * logic.CATALOGUE["coffee"]["ref_price"]
    state["shops"]["old_shop"] = {"unlocked": True, "level": 2, "products": [], "staff_places": 0}
    state["badges"] = [{"id": "old-badge", "day": 1}]
    state["player"] = {"zone": "old-zone", "x": 1.0, "y": 2.0}
    state["employees"][0]["level"] = logic.EMPLOYEE_MAX_LEVEL + 5
    return state


@pytest.mark.parametrize("make", [
    lambda: logic.new_state(logic.new_seed()),
    complete_run,
    staffed_run,
    lambda: scenarios.load_scenario("demo-day"),
    damaged_run,
], ids=["fresh", "full-season", "staff", "demo-scenario", "damaged"])
def test_through_sqlite_gives_exactly_what_a_file_gives(make, tmp_path):
    state = make()
    assert db.through_sqlite(copy.deepcopy(state)) == file_roundtrip(copy.deepcopy(state), tmp_path)


def test_through_sqlite_repairs_an_old_run():
    repaired = db.through_sqlite(damaged_run())
    assert "old_product" not in repaired["stock"] and "old_shop" not in repaired["shops"]
    assert repaired["prices"]["coffee"] == logic.CATALOGUE["coffee"]["ref_price"]
    assert repaired["badges"] == []
    assert repaired["player"] != {"zone": "old-zone", "x": 1.0, "y": 2.0}
    assert repaired["employees"][0]["level"] == logic.EMPLOYEE_MAX_LEVEL


@pytest.mark.parametrize("field, value", [("cash", -1), ("day", None)])
def test_a_state_that_breaks_a_check_raises_like_a_file(field, value, tmp_path):
    state = logic.new_state(logic.new_seed())
    state[field] = value
    with pytest.raises(sqlite3.IntegrityError):
        db.through_sqlite(state)
    with pytest.raises(sqlite3.IntegrityError):
        db.save(state, path=tmp_path / "x.db")


def test_postgres_only_for_a_player_of_the_public_server_with_a_database(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", CLOSED)
    with app.app.test_request_context():
        app.g.player = None  # local play: one run, no player id
        assert not app._in_postgres()
        app.g.player = "A" * 22
        assert app._in_postgres()
    monkeypatch.delenv("DATABASE_URL")
    with app.app.test_request_context():
        app.g.player = "A" * 22
        assert not app._in_postgres()  # public without a database: SQLite files as before


def test_tls_is_required_unless_the_string_says_otherwise():
    assert "sslmode=require" in pgstore.conninfo("postgresql://u:p@db.example:5432/postgres")
    strict = pgstore.conninfo("postgresql://u:p@db.example:5432/postgres?sslmode=verify-full")
    assert "sslmode=verify-full" in strict and "sslmode=require" not in strict
    assert "connect_timeout=5" in pgstore.conninfo("host=db.example user=u")


def test_an_unreachable_database_answers_503_and_never_shows_the_password(public, monkeypatch, caplog):
    monkeypatch.setenv("DATABASE_URL", CLOSED)
    monkeypatch.setattr(pgstore, "WAIT", 1)
    client = app.app.test_client()
    assert client.get("/").status_code == 200  # the page itself still loads
    response = client.get("/api/state")
    assert response.status_code == 503
    assert response.get_json() == {"error": app.STORAGE_DOWN}
    assert "secret-pw-123" not in response.get_data(as_text=True)
    assert "secret-pw-123" not in caplog.text
    assert not list(public.glob("*.db"))  # no SQLite file instead
    assert client.get("/healthz").status_code == 200  # the health check never asks the database


def test_a_broken_connection_string_answers_503_and_quotes_none_of_it(public, monkeypatch, caplog):
    monkeypatch.setenv("DATABASE_URL", "host=db.example password=pw-part-777 user")  # no "=" after "user"
    client = app.app.test_client()
    client.get("/")
    response = client.get("/api/state")
    assert response.status_code == 503 and response.get_json() == {"error": app.STORAGE_DOWN}
    assert "pw-part-777" not in caplog.text and "not a valid connection string" in caplog.text


def test_a_new_run_through_the_api_also_answers_503_when_the_database_is_gone(public, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", CLOSED)
    monkeypatch.setattr(pgstore, "WAIT", 1)
    client = app.app.test_client()
    client.get("/")
    response = client.post("/api/new-run", json={"confirm": True})
    assert response.status_code == 503 and response.get_json()["error"] == app.STORAGE_DOWN


# ---- against a real Postgres (TEST_DATABASE_URL) -----------------------------------------------------------


@needs_pg
def test_the_table_is_made_once_with_row_level_security(pg):
    assert pgstore.count() == 0
    pgstore.reset()  # a second start
    assert pgstore.count() == 0
    rows = sql("SELECT relrowsecurity FROM pg_class WHERE oid = %s::regclass", (f"{pgstore.SCHEMA}.runs",))
    assert rows == [(True,)]
    assert sql("SELECT count(*) FROM pg_policies WHERE schemaname = %s", (pgstore.SCHEMA,)) == [(0,)]


@needs_pg
@pytest.mark.parametrize("role", pgstore.API_ROLES)
def test_the_data_api_roles_cannot_read_the_runs(pg, role):
    import psycopg
    pgstore.save(logic.new_state(logic.new_seed()), "B" * 22)
    with psycopg.connect(TEST_URL) as conn:
        conn.execute(f"SET ROLE {role}")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(f"SELECT * FROM {pgstore.SCHEMA}.runs").fetchall()


@needs_pg
def test_save_and_load_give_the_state_as_sqlite_would(pg):
    state = complete_run()
    pgstore.save(state, "C" * 22)
    pgstore.reset()  # from the database, not from memory
    assert pgstore.load("C" * 22) == db.through_sqlite(state)
    assert pgstore.load("D" * 22) is None


@needs_pg
def test_a_new_run_replaces_the_old_one_with_its_days(pg):
    pgstore.save(complete_run(), "E" * 22)
    pgstore.save(logic.new_state(logic.new_seed()), "E" * 22)
    pgstore.reset()
    assert pgstore.load("E" * 22)["history"] == []
    assert pgstore.count() == 1


@needs_pg
def test_a_bad_player_id_is_refused_by_the_table(pg):
    import psycopg
    with pytest.raises(psycopg.errors.CheckViolation):
        pgstore.save(logic.new_state(logic.new_seed()), "../../etc")


@needs_pg
def test_two_players_have_two_rows_and_a_rejected_action_changes_nothing(pg, public):
    first, second = app.app.test_client(), app.app.test_client()
    first.get("/")
    second.get("/")
    assert first.post("/api/buy", json={"product": "coffee", "quantity": "5"}).status_code == 200
    assert second.get("/api/state").get_json()["products"][0]["stock"] == 0
    assert sql(f"SELECT count(*) FROM {pgstore.SCHEMA}.runs") == [(2,)]
    before = sql(f"SELECT player_id, state, updated_at FROM {pgstore.SCHEMA}.runs ORDER BY player_id")
    assert first.post("/api/buy", json={"product": "coffee", "quantity": "-3"}).status_code == 400
    assert sql(f"SELECT player_id, state, updated_at FROM {pgstore.SCHEMA}.runs ORDER BY player_id") == before
    assert not list(public.glob("*.db"))  # no SQLite files on the server


@needs_pg
def test_a_run_survives_a_restart_of_the_server(pg, public):
    client = app.app.test_client()
    client.get("/")
    client.post("/api/buy", json={"product": "coffee", "quantity": "4"})
    pgstore.reset()  # the server restarts: memory and connections gone, the database stays
    state = client.get("/api/state").get_json()
    assert state["products"][0]["stock"] == 4 and state["cash"] == 10_000 - 4 * logic.CATALOGUE["coffee"]["cost"]


@needs_pg
def test_the_cap_counts_the_rows(pg, public, monkeypatch):
    monkeypatch.setattr(app, "MAX_PLAYERS", 1)
    first, second = app.app.test_client(), app.app.test_client()
    first.get("/")
    assert first.get("/api/state").status_code == 200
    second.get("/")
    response = second.get("/api/state")
    assert response.status_code == 503 and "full" in response.get_json()["error"]


@needs_pg
def test_the_second_load_comes_from_memory(pg, monkeypatch):
    pgstore.save(logic.new_state(logic.new_seed()), "F" * 22)
    pgstore.reset()
    calls = []
    real = pgstore._run
    monkeypatch.setattr(pgstore, "_run", lambda work: calls.append(1) or real(work))
    pgstore.load("F" * 22)
    pgstore.load("F" * 22)
    assert len(calls) == 1


@needs_pg
def test_a_failed_write_leaves_the_copy_in_memory_as_it_was(pg, monkeypatch):
    saved = logic.new_state(logic.new_seed())
    pgstore.save(saved, "G" * 22)

    def unreachable(work):
        raise pgstore.Unavailable()

    monkeypatch.setattr(pgstore, "_run", unreachable)
    changed = logic.buy(saved, "coffee", 3)
    with pytest.raises(pgstore.Unavailable):
        pgstore.save(changed, "G" * 22)
    assert pgstore.load("G" * 22) == db.through_sqlite(saved)  # from memory: the old run


@needs_pg
def test_changing_a_loaded_run_does_not_change_the_copy_in_memory(pg):
    pgstore.save(logic.new_state(logic.new_seed()), "H" * 22)
    loaded = pgstore.load("H" * 22)
    loaded["cash"] = 1
    loaded["stock"]["coffee"] = 99
    again = pgstore.load("H" * 22)
    assert again["cash"] == 10_000 and again["stock"]["coffee"] == 0
