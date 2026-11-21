"""Checks from specs/player-cap.md ("Done when"): a full public game replaces the run changed longest ago
once it has been idle for IDLE_BEFORE_REPLACE, one for one under the lock of new runs; with no idle run the
answer stays 503. SQLite files here; the same rules on Postgres rows run with TEST_DATABASE_URL (CI)."""

import logging
import os
import threading
import time

import pytest

import app
import pgstore

TEST_URL = os.environ.get("TEST_DATABASE_URL", "")
needs_pg = pytest.mark.skipif(not TEST_URL, reason="no test database (TEST_DATABASE_URL)")
IDLE = app.IDLE_BEFORE_REPLACE


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


def new_client():
    """A browser with a signed cookie and no run yet; returns (client, player id)."""
    client = app.app.test_client()
    assert client.get("/").status_code == 200
    return client, client.get_cookie(app.PLAYER_COOKIE).value.split(".")[0]


def new_player():
    """A player whose run now exists (the first API call makes it)."""
    client, player = new_client()
    assert client.get("/api/state").status_code == 200
    return client, player


def age(player, seconds):
    """Make a SQLite run look last saved `seconds` ago."""
    path = app._player_file(player)
    then = time.time() - seconds
    os.utime(path, (then, then))


def stored(public_dir):
    return sorted(p.stem for p in public_dir.glob("*.db"))


def test_a_full_game_replaces_the_run_idle_longest(public, monkeypatch):
    monkeypatch.setattr(app, "MAX_PLAYERS", 3)
    players = [new_player()[1] for _ in range(3)]
    for player, minutes in zip(players, (30, 90, 15)):  # the second one is idle longest
        age(player, minutes * 60)
    others = {p: app._player_file(p).read_bytes() for p in (players[0], players[2])}
    client, newcomer = new_client()
    assert client.get("/api/state").status_code == 200
    assert stored(public) == sorted([players[0], players[2], newcomer])
    for player, raw in others.items():
        assert app._player_file(player).read_bytes() == raw  # untouched


def test_no_idle_run_means_the_game_stays_full(public, monkeypatch):
    monkeypatch.setattr(app, "MAX_PLAYERS", 3)
    players = [new_player()[1] for _ in range(3)]
    age(players[0], IDLE - 60)  # nine minutes: not idle enough
    client, _ = new_client()
    full = client.get("/api/state")
    assert full.status_code == 503 and "full" in full.get_json()["error"]
    assert stored(public) == sorted(players)


def test_only_idle_runs_make_room(public, monkeypatch):
    monkeypatch.setattr(app, "MAX_PLAYERS", 3)
    players = [new_player()[1] for _ in range(3)]
    age(players[1], IDLE + 1)
    first, newcomer = new_client()
    assert first.get("/api/state").status_code == 200
    assert players[1] not in stored(public) and newcomer in stored(public)
    second, _ = new_client()
    assert second.get("/api/state").status_code == 503  # the rest are fresh


def test_the_cap_stays_hard_with_many_new_players_at_once(public, monkeypatch):
    monkeypatch.setattr(app, "MAX_PLAYERS", 3)
    old = [new_player()[1] for _ in range(3)]
    for player in old:
        age(player, 2 * IDLE)
    clients = [new_client()[0] for _ in range(8)]
    codes = []
    threads = [threading.Thread(target=lambda c=c: codes.append(c.get("/api/state").status_code)) for c in clients]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert sorted(codes) == [200] * 3 + [503] * 5
    assert len(stored(public)) == 3 and not set(old) & set(stored(public))


def test_a_replaced_player_starts_again_on_day_one(public, monkeypatch):
    monkeypatch.setattr(app, "MAX_PLAYERS", 2)
    gone, gone_id = new_player()
    assert gone.post("/api/buy", json={"product": "coffee", "quantity": "5"}).status_code == 200
    _, kept = new_player()
    age(gone_id, 2 * IDLE)
    age(kept, IDLE + 5)
    newcomer, _ = new_client()
    assert newcomer.get("/api/state").status_code == 200  # replaced the run idle longest: `gone`
    back = gone.get("/api/state")  # needs room like any new player: the other idle run makes it
    assert back.status_code == 200
    state = back.get_json()
    assert state["day"] == 1 and state["history"] == [] and state["products"][0]["stock"] == 0
    assert kept not in stored(public) and gone_id in stored(public)


def test_looking_does_not_count_as_a_change_but_a_save_does(public):
    client, player = new_player()
    age(player, 3600)
    before = app._player_file(player).stat().st_mtime
    assert client.get("/api/state").status_code == 200
    assert app._player_file(player).stat().st_mtime == before
    assert client.post("/api/buy", json={"product": "coffee", "quantity": "1"}).status_code == 200
    assert time.time() - app._player_file(player).stat().st_mtime < 60


class Holder:
    """Holds a run lock in another thread, like a request of that player that is running right now (the
    locks are reentrant, so the test's own thread would simply take it again)."""

    def __init__(self, lock):
        self.lock, self.taken, self.done = lock, threading.Event(), threading.Event()
        self.thread = threading.Thread(target=self._hold)

    def _hold(self):
        with self.lock:
            self.taken.set()
            self.done.wait(10)

    def __enter__(self):
        self.thread.start()
        assert self.taken.wait(10)
        return self

    def __exit__(self, *_):
        self.done.set()
        self.thread.join(10)


def newcomer_off(*players):
    """A new browser whose stripe differs from these players' stripes."""
    while True:
        client, newcomer = new_client()
        if all(app._lock_of(newcomer) is not app._lock_of(p) for p in players):
            return client, newcomer


def test_a_run_whose_player_is_busy_is_not_taken(public, monkeypatch):
    monkeypatch.setattr(app, "MAX_PLAYERS", 1)
    _, busy = new_player()
    age(busy, 2 * IDLE)
    client, newcomer = newcomer_off(busy)
    with Holder(app._lock_of(busy)):  # a request of the idle player is running right now
        assert client.get("/api/state").status_code == 503
        assert stored(public) == [busy]
    assert client.get("/api/state").status_code == 200
    assert stored(public) == [newcomer]


def test_a_busy_stripe_moves_on_to_the_next_idle_run(public, monkeypatch):
    # review finding: a stripe is often held by somebody else entirely (a player waiting for the lock of
    # new runs); that must not answer "full" while another idle run is free
    monkeypatch.setattr(app, "MAX_PLAYERS", 2)
    _, oldest = new_player()
    while True:
        _, second = new_player()
        if app._lock_of(second) is not app._lock_of(oldest):
            break
        app._player_file(second).unlink()
    age(oldest, 3 * IDLE)
    age(second, 2 * IDLE)
    client, newcomer = newcomer_off(oldest, second)
    with Holder(app._lock_of(oldest)):
        assert client.get("/api/state").status_code == 200
    assert stored(public) == sorted([oldest, newcomer])  # the next idle run made room


def test_a_run_saved_after_it_was_picked_is_kept(public):
    # review finding: the SQLite twin of the Postgres check below
    _, player = new_player()
    age(player, 2 * IDLE)
    with app.app.test_request_context("/"):
        assert app._oldest_idle_runs()[0][0] == player
        age(player, 0)  # saved meanwhile
        assert app._remove_if_idle(player) is False
    assert stored(public) == [player]


def test_the_log_says_it_but_names_no_player(public, monkeypatch, caplog):
    monkeypatch.setattr(app, "MAX_PLAYERS", 1)
    _, idle = new_player()
    age(idle, 25 * 60)
    client, newcomer = new_client()
    with caplog.at_level(logging.WARNING, logger=app.app.logger.name):
        assert client.get("/api/state").status_code == 200
    # WARNING: Flask writes from WARNING on in production, an INFO line would never reach the log
    assert any(r.levelno == logging.WARNING and "replaced a run idle for 25 minutes" in r.getMessage()
               for r in caplog.records)
    assert app.app.logger.getEffectiveLevel() <= logging.WARNING
    assert idle not in caplog.text and newcomer not in caplog.text


def test_the_local_game_has_no_cap(monkeypatch):
    import logic
    monkeypatch.delenv("CT_PUBLIC", raising=False)
    monkeypatch.setattr(app, "MAX_PLAYERS", 0)  # would be full at once if the cap applied

    def never(*_):
        raise AssertionError("the local game must not count or replace runs")

    for name in ("_run_count", "_make_room", "_oldest_idle_runs"):
        monkeypatch.setattr(app, name, never)
    monkeypatch.setattr(app, "_load_stored", lambda: logic.new_state(7))  # the one run of this computer
    assert app.app.test_client().get("/api/state").status_code == 200


# ---- the same rules on Postgres rows (TEST_DATABASE_URL, CI) ---------------------------------------------


@pytest.fixture
def pg(monkeypatch):
    import psycopg
    with psycopg.connect(TEST_URL, autocommit=True) as conn:
        conn.execute(f"DROP SCHEMA IF EXISTS {pgstore.SCHEMA} CASCADE")
    monkeypatch.setenv("DATABASE_URL", TEST_URL)
    pgstore.reset()
    yield
    pgstore.reset()


def pg_age(player, seconds):
    import psycopg
    with psycopg.connect(TEST_URL, autocommit=True) as conn:
        conn.execute(f"UPDATE {pgstore.SCHEMA}.runs SET updated_at = now() - make_interval(secs => %s) "
                     "WHERE player_id = %s", (seconds, player))


@needs_pg
def test_postgres_replaces_the_row_idle_longest_and_forgets_its_copy(pg, public, monkeypatch):
    monkeypatch.setattr(app, "MAX_PLAYERS", 2)
    a = new_player()[1]
    b = new_player()[1]
    pg_age(a, 3 * IDLE)
    pg_age(b, 2 * IDLE)
    assert a in pgstore._cache  # the copy in memory of the run about to go
    client, newcomer = new_client()
    assert client.get("/api/state").status_code == 200
    assert pgstore.count() == 2
    assert not pgstore.exists(a) and pgstore.exists(b) and pgstore.exists(newcomer)
    assert a not in pgstore._cache
    assert not list(public.glob("*.db"))  # no SQLite file instead


@needs_pg
def test_postgres_keeps_a_fresh_row_and_answers_full(pg, public, monkeypatch):
    monkeypatch.setattr(app, "MAX_PLAYERS", 1)
    a = new_player()[1]
    pg_age(a, IDLE - 30)
    client, _ = new_client()
    assert client.get("/api/state").status_code == 503
    assert pgstore.exists(a) and pgstore.count() == 1


@needs_pg
def test_postgres_does_not_delete_a_row_saved_after_it_was_picked(pg):
    import logic
    pgstore.save(logic.new_state(logic.new_seed()), "R" * 22)
    pg_age("R" * 22, 2 * IDLE)
    assert pgstore.oldest_idle(IDLE)[0][0] == "R" * 22
    pgstore.save(logic.new_state(logic.new_seed()), "R" * 22)  # saved meanwhile
    assert pgstore.delete_if_idle("R" * 22, IDLE) is False
    assert pgstore.exists("R" * 22)
