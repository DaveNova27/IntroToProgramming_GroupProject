"""Checks from specs/request-limits.md ("Done when"): a body over MAX_REQUEST_BYTES is refused with 413
and a JSON error before any rule, nothing saved; behind a trusted proxy the first page request logs the
proxy chain once, with names and counts and never an address."""

import json
import logging

import pytest

import app
import db
import logic
import pgstore

LIMIT = app.MAX_REQUEST_BYTES


@pytest.fixture
def run_on_disk(tmp_path, monkeypatch):
    """The real API on a temporary save (local mode), so the player's own run stays untouched."""
    path = tmp_path / "run.db"
    db.save(logic.new_state(), path)
    real_save = db.save
    monkeypatch.setattr(app, "load_run", lambda: db.load(path))
    monkeypatch.setattr(app.db, "save", lambda state: real_save(state, path))
    return path


@pytest.fixture
def public(monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    pgstore.reset()
    monkeypatch.setenv("CT_PUBLIC", "1")
    monkeypatch.setattr(app, "PLAYERS_DIR", tmp_path / "players")
    app._hits.clear()
    monkeypatch.setattr(app, "_chain_logged", [False])
    yield
    pgstore.reset()


def body_of(size):
    """A JSON order whose product name makes the whole body exactly `size` bytes."""
    empty = json.dumps({"product": "", "quantity": "1"})
    return json.dumps({"product": "x" * (size - len(empty)), "quantity": "1"})


def post_raw(client, url, data):
    return client.post(url, data=data, content_type="application/json")


# ---- Check 1: too large is refused with JSON, nothing saved ---------------------------------------

def test_a_body_over_the_limit_is_refused_and_nothing_is_saved(run_on_disk):
    before = db.load(run_on_disk)
    response = post_raw(app.app.test_client(), "/api/buy", body_of(LIMIT + 1))
    assert response.status_code == 413
    assert response.get_json() == {"error": "The request is too large."}
    assert db.load(run_on_disk) == before


def test_a_large_body_is_refused_on_every_api_endpoint_that_reads_one(run_on_disk):
    before = db.load(run_on_disk)
    client = app.app.test_client()
    for url in ("/api/buy-many", "/api/price", "/api/shop/unlock", "/api/staff/hire", "/api/shift/start",
                "/api/new-run", "/api/editor/state"):
        response = post_raw(client, url, body_of(LIMIT * 4))
        assert response.status_code == 413, url
        assert response.get_json()["error"] == "The request is too large.", url
    assert db.load(run_on_disk) == before


def test_a_large_body_is_refused_in_public_mode_too(public):
    client = app.app.test_client()
    assert client.get("/").status_code == 200
    state = client.get("/api/state").get_json()
    response = post_raw(client, "/api/buy", body_of(LIMIT + 1))
    assert response.status_code == 413 and response.get_json() == {"error": "The request is too large."}
    after = client.get("/api/state").get_json()
    assert after["cash"] == state["cash"] and after["products"] == state["products"]


def test_the_limit_is_64_kb():
    assert LIMIT == 64 * 1024 and app.app.config["MAX_CONTENT_LENGTH"] == LIMIT


# ---- Check 2 and 3: under the limit nothing changes ----------------------------------------------

def test_a_body_just_under_the_limit_reaches_the_rule(run_on_disk):
    response = post_raw(app.app.test_client(), "/api/buy", body_of(LIMIT))
    assert response.status_code == 400  # the rule answers: no such product
    assert response.get_json()["error"].startswith("Unknown product")


def test_a_real_order_still_works(run_on_disk):
    before = db.load(run_on_disk)["cash"]
    response = app.app.test_client().post("/api/buy", json={"product": "coffee", "quantity": "5"})
    assert response.status_code == 200
    assert db.load(run_on_disk)["cash"] < before


# ---- Check 4 to 6: the proxy chain, once, without an address -------------------------------------

HEADERS = {"X-Forwarded-For": "203.0.113.7, 198.51.100.20", "CF-Connecting-IP": "203.0.113.7"}


def chain_lines(caplog):
    return [r.getMessage() for r in caplog.records if r.getMessage().startswith("proxy chain:")]


def test_the_first_page_request_logs_the_chain_once_and_no_address(public, monkeypatch, caplog):
    monkeypatch.setenv("CT_PROXY", "1")
    caplog.set_level(logging.WARNING)
    assert app.app.test_client().get("/", headers=HEADERS).status_code == 200
    assert app.app.test_client().get("/map", headers=HEADERS).status_code in (200, 302)  # a second page
    lines = chain_lines(caplog)
    assert lines == ["proxy chain: X-Forwarded-For has 2 entries; CF-Connecting-IP present (the first entry); "
                     "True-Client-IP absent; Forwarded absent"]
    for address in ("203.0.113.7", "198.51.100.20"):
        assert all(address not in r.getMessage() for r in caplog.records)


@pytest.mark.parametrize("headers, expected", [
    ({"X-Forwarded-For": "198.51.100.20, 203.0.113.7", "CF-Connecting-IP": "203.0.113.7"},
     "X-Forwarded-For has 2 entries; CF-Connecting-IP present (the last entry)"),
    ({"X-Forwarded-For": "203.0.113.7", "CF-Connecting-IP": "203.0.113.7"},
     "X-Forwarded-For has 1 entry; CF-Connecting-IP present (the only entry)"),
    ({"X-Forwarded-For": "1.1.1.1, 203.0.113.7, 2.2.2.2", "CF-Connecting-IP": "203.0.113.7"},
     "X-Forwarded-For has 3 entries; CF-Connecting-IP present (another entry)"),
    ({"X-Forwarded-For": "198.51.100.20", "CF-Connecting-IP": "203.0.113.7"},
     "X-Forwarded-For has 1 entry; CF-Connecting-IP present (no entry)"),
    ({"X-Forwarded-For": "198.51.100.20"}, "X-Forwarded-For has 1 entry; CF-Connecting-IP absent"),
    ({"True-Client-IP": "203.0.113.7", "Forwarded": "for=203.0.113.7"},
     "X-Forwarded-For has 0 entries; CF-Connecting-IP absent; True-Client-IP present; Forwarded present"),
])
def test_the_line_says_where_the_visitor_stands(public, monkeypatch, caplog, headers, expected):
    monkeypatch.setenv("CT_PROXY", "1")
    caplog.set_level(logging.WARNING)
    app.app.test_client().get("/", headers=headers)
    (line,) = chain_lines(caplog)
    assert expected in line
    assert "203.0.113.7" not in line and "198.51.100.20" not in line


def test_no_line_without_a_trusted_proxy(public, monkeypatch, caplog):
    monkeypatch.delenv("CT_PROXY", raising=False)
    caplog.set_level(logging.WARNING)
    app.app.test_client().get("/", headers=HEADERS)
    assert chain_lines(caplog) == []


def test_no_line_for_the_health_check_or_files(public, monkeypatch, caplog):
    monkeypatch.setenv("CT_PROXY", "1")
    caplog.set_level(logging.WARNING)
    client = app.app.test_client()
    client.get("/healthz", headers=HEADERS)
    client.get("/static/app.js", headers=HEADERS)
    assert chain_lines(caplog) == []
    client.get("/", headers=HEADERS)
    assert len(chain_lines(caplog)) == 1


def test_no_line_in_local_mode(monkeypatch, caplog):
    monkeypatch.delenv("CT_PUBLIC", raising=False)
    monkeypatch.setenv("CT_PROXY", "1")
    monkeypatch.setattr(app, "_chain_logged", [False])
    caplog.set_level(logging.WARNING)
    app.app.test_client().get("/", headers=HEADERS)
    assert chain_lines(caplog) == []
