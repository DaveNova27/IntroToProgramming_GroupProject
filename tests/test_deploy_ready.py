"""Checks from specs/deploy-ready.md: security headers, the public mode (a run per player, limits,
no dev switches) and answers without paths. Local play is unchanged."""

import pytest

import app
import db
import logic


@pytest.fixture
def public(monkeypatch, tmp_path):
    monkeypatch.setenv("CT_PUBLIC", "1")
    monkeypatch.setattr(app, "PLAYERS_DIR", tmp_path / "players")
    app._hits.clear()
    return tmp_path / "players"


def play(client, path, body=None):
    return client.post(path, json=body or {})


# ---- headers (also locally) ------------------------------------------------------------------------


@pytest.mark.parametrize("path", ["/", "/static/app.js", "/api/world"])
def test_every_answer_has_the_security_headers(path):
    response = app.app.test_client().get(path)
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "SAMEORIGIN"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    csp = response.headers["Content-Security-Policy"]
    assert "default-src 'self'" in csp and "script-src 'self'" in csp and "object-src 'none'" in csp
    assert "http" not in csp  # nothing from outside


def test_the_pages_load_nothing_from_outside_and_no_inline_script():
    import re
    from pathlib import Path
    for name in ("index.html", "map.html"):
        html = (Path(app.__file__).parent / "static" / name).read_text(encoding="utf-8")
        assert not re.search(r"<script(?![^>]*\bsrc=)[^>]*>", html), name  # no inline script
        assert not re.search(r"\bon[a-z]+=\"", html), name  # no inline handlers


def test_local_play_is_unchanged(tmp_path, monkeypatch):
    monkeypatch.delenv("CT_PUBLIC", raising=False)
    client = app.app.test_client()
    response = client.get("/api/state")
    assert response.status_code == 200 and "Set-Cookie" not in response.headers


# ---- the public mode ------------------------------------------------------------------------------------


def test_every_player_has_a_run_of_their_own(public):
    first, second = app.app.test_client(), app.app.test_client()
    first.get("/")
    second.get("/")
    assert play(first, "/api/buy", {"product": "coffee", "quantity": "5"}).status_code == 200
    assert first.get("/api/state").get_json()["products"][0]["stock"] == 5
    assert second.get("/api/state").get_json()["products"][0]["stock"] == 0  # not the same run
    assert len(list(public.glob("*.db"))) == 2


def test_the_cookie_is_http_only_and_a_returning_player_keeps_the_run(public):
    client = app.app.test_client()
    cookie = client.get("/").headers["Set-Cookie"]
    assert "HttpOnly" in cookie and "SameSite=Lax" in cookie and cookie.startswith("ct_player=")
    play(client, "/api/buy", {"product": "coffee", "quantity": "3"})
    assert client.get("/api/state").get_json()["products"][0]["stock"] == 3  # the same cookie, the same run


def test_an_api_call_without_the_cookie_makes_no_run(public):
    client = app.app.test_client()
    response = client.get("/api/state")
    assert response.status_code == 400 and not list(public.glob("*.db"))


@pytest.mark.parametrize("bad", ["../../etc/passwd", "a" * 21, "a" * 23, "..", "a/b" + "c" * 19, "%2e%2e%2f" + "a" * 13])
def test_a_forged_cookie_is_never_a_file_name(public, bad, tmp_path):
    client = app.app.test_client()
    client.set_cookie("ct_player", bad)
    assert client.get("/api/state").status_code == 400
    assert not list(public.glob("*.db")) and not list(tmp_path.glob("*.db"))


def test_the_rate_limit_answers_429_and_changes_nothing(public, monkeypatch):
    monkeypatch.setattr(app, "RATE_LIMIT", 3)
    client = app.app.test_client()
    client.get("/")
    for _ in range(3):
        assert client.get("/api/state").status_code == 200
    before = client.application.test_client()  # a second player is not limited by the first
    before.get("/")
    assert before.get("/api/state").status_code == 200
    limited = play(client, "/api/buy", {"product": "coffee", "quantity": "5"})
    assert limited.status_code == 429 and "Too many" in limited.get_json()["error"]
    monkeypatch.setattr(app, "RATE_LIMIT", 1000)
    assert client.get("/api/state").get_json()["products"][0]["stock"] == 0  # the refused buy was not done


def test_new_players_per_address_are_limited(public, monkeypatch):
    monkeypatch.setattr(app, "NEW_PLAYER_LIMIT", 2)
    statuses = [app.app.test_client().get("/").status_code for _ in range(3)]
    assert statuses == [200, 200, 429]


def test_the_game_can_be_full(public, monkeypatch):
    monkeypatch.setattr(app, "MAX_PLAYERS", 1)
    first = app.app.test_client()
    assert first.get("/").status_code == 200
    assert first.get("/api/state").status_code == 200  # the run of the first player now exists
    full = app.app.test_client().get("/")
    assert full.status_code == 503 and "full" in full.get_json()["error"]
    assert first.get("/api/state").status_code == 200  # whoever is in stays in
    assert len(list(public.glob("*.db"))) == 1


def test_the_dev_switches_are_off_in_public_mode(public, monkeypatch):
    monkeypatch.setenv("CT_EDITOR", "1")
    monkeypatch.setenv("CAMPUS_TYCOON_DEMO", "1")
    client = app.app.test_client()
    client.get("/")
    assert client.get("/api/state").get_json()["editor"] is False
    response = play(client, "/api/editor/cash", {"mode": "set", "cents": 5_000_000})
    assert response.status_code == 400
    assert client.get("/api/state").get_json()["cash"] == logic.STARTING_CASH
    assert play(client, "/api/day-override", {"weather": "storm"}).status_code == 400


# ---- answers without paths ---------------------------------------------------------------------------------


def test_an_unexpected_error_says_nothing_about_the_server(monkeypatch):
    def boom(*_):
        raise RuntimeError("secret /Users/someone/project/logic.py line 12")
    monkeypatch.setattr(logic, "buy", boom)
    client = app.app.test_client()
    client.application.config["PROPAGATE_EXCEPTIONS"] = False
    response = play(client, "/api/buy", {"product": "coffee", "quantity": "1"})
    assert response.status_code == 500
    assert response.get_json() == {"error": "The server hit an error. Nothing was saved."}
    assert "secret" not in response.get_data(as_text=True)
