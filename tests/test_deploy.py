"""Checks from specs/deploy.md: the health check of the host, the Render Blueprint (render.yaml) and
the pinned production server. The Blueprint is read as text (no YAML library in the project): the
file is short and its layout is fixed by the spec."""

import re
import tomllib
from pathlib import Path

import pytest
from flask import Flask

import app

ROOT = Path(app.__file__).parent
RENDER = (ROOT / "render.yaml").read_text(encoding="utf-8")


@pytest.fixture
def public(monkeypatch, tmp_path):
    monkeypatch.setenv("CT_PUBLIC", "1")
    monkeypatch.setenv("CT_PROXY", "1")
    monkeypatch.setattr(app, "PLAYERS_DIR", tmp_path / "players")
    app._hits.clear()
    return tmp_path / "players"


def setting(key):
    """A setting of the one service in render.yaml ("    key: value")."""
    found = re.findall(rf"^    {key}: (.+)$", RENDER, re.M)
    assert len(found) == 1, f"{key} must be set exactly once in render.yaml"
    return found[0].strip()


def env_vars():
    """The envVars of the service: {key: {field: value}}, values as written (quotes kept)."""
    entries, current = {}, None
    for line in RENDER.splitlines():
        start = re.match(r"^      - key: (\S+)\s*$", line)
        if start:
            assert start.group(1) not in entries, f"{start.group(1)} is listed twice"
            current = entries[start.group(1)] = {}
            continue
        field = re.match(r"^        (\w+): (.+?)\s*$", line)
        if field and current is not None:
            current[field.group(1)] = field.group(2)
    return entries


# ---- GET /healthz ---------------------------------------------------------------------------------


def test_the_health_check_answers_ok_locally(monkeypatch):
    monkeypatch.delenv("CT_PUBLIC", raising=False)
    response = app.app.test_client().get("/healthz")
    assert response.status_code == 200 and response.get_data() == b"ok"
    assert response.mimetype == "text/plain"
    assert "Set-Cookie" not in response.headers


def test_the_health_check_answers_ok_in_public_mode_and_makes_no_player(public):
    client = app.app.test_client()
    response = client.get("/healthz", headers={"X-Forwarded-Proto": "https"})
    assert response.status_code == 200 and response.get_data() == b"ok"
    assert "Set-Cookie" not in response.headers
    assert not public.exists()  # not even the players folder is made: the check writes nothing


def test_head_works_and_other_methods_do_not(public):
    client = app.app.test_client()
    assert client.head("/healthz").status_code == 200
    assert client.post("/healthz").status_code == 405


def test_the_health_check_is_never_cached(public):
    assert app.app.test_client().get("/healthz").headers["Cache-Control"] == "no-store"


def test_many_probes_do_not_use_up_the_new_player_budget(public):
    client = app.app.test_client()
    for _ in range(500):  # far more than the 60 new players a minute an address may make
        assert client.get("/healthz").status_code == 200
    assert not app._hits  # nothing was counted
    page = client.get("/")
    assert page.status_code == 200 and page.headers["Set-Cookie"].startswith("ct_player=")


def test_a_forged_cookie_changes_nothing_for_the_health_check(public):
    client = app.app.test_client()
    client.set_cookie("ct_player", "made-up.0000")
    response = client.get("/healthz")
    assert response.status_code == 200 and "Set-Cookie" not in response.headers
    assert not public.exists()


def test_the_health_check_has_the_security_headers(public):
    response = app.app.test_client().get("/healthz", headers={"X-Forwarded-Proto": "https"})
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "default-src 'self'" in response.headers["Content-Security-Policy"]
    assert response.headers["Strict-Transport-Security"] == "max-age=31536000"


# ---- render.yaml ----------------------------------------------------------------------------------


def test_the_blueprint_has_one_free_web_service_in_frankfurt_from_main():
    assert len(re.findall(r"^  - type: ", RENDER, re.M)) == 1
    assert re.search(r"^  - type: web$", RENDER, re.M)
    assert setting("name") == "campus-tycoon"
    assert setting("runtime") == "python"
    assert setting("plan") == "free"
    assert setting("region") == "frankfurt"
    assert setting("branch") == "main"


def test_a_deploy_starts_only_when_the_tests_passed():
    assert setting("autoDeployTrigger") == "checksPass"


def test_the_host_checks_the_health_route():
    assert setting("healthCheckPath") == "/healthz"
    assert any(rule.rule == "/healthz" for rule in app.app.url_map.iter_rules())


def test_the_build_installs_exactly_the_lockfile_without_dev_tools():
    words = setting("buildCommand").split()
    assert words[:2] == ["uv", "sync"]
    assert "--locked" in words  # an outdated uv.lock fails the build instead of installing other versions
    assert "--no-dev" in words  # no pytest on the server
    assert "--group" in words and words[words.index("--group") + 1] == "deploy"


def test_the_server_runs_one_worker_of_our_app_on_the_given_port():
    command = setting("startCommand")
    words = command.split()
    assert words[:4] == ["uv", "run", "--no-sync", "gunicorn"]
    assert words[-1] == "app:app"
    assert isinstance(app.app, Flask)  # app:app is our Flask app
    # exactly one worker: the locks and the rate counter live in the process (specs/deploy-ready.md)
    assert words.count("-w") == 1 and words[words.index("-w") + 1] == "1"
    assert not any(w.startswith("--workers") or (w.startswith("-w") and w != "-w") for w in words)
    assert words.count("-b") == 1 and words[words.index("-b") + 1] == "0.0.0.0:$PORT"
    assert "--no-control-socket" in words
    assert "--access-logfile" not in command  # no visitor addresses in the host's logs


def test_the_variables_are_exactly_the_ones_of_the_spec():
    assert set(env_vars()) == {"PYTHON_VERSION", "PORT", "CT_PUBLIC", "CT_PROXY", "CT_SECRET"}


def test_public_mode_behind_the_proxy_on_port_10000():
    env = env_vars()
    assert env["CT_PUBLIC"] == {"value": '"1"'}
    assert env["CT_PROXY"] == {"value": '"1"'}
    assert env["PORT"] == {"value": '"10000"'}


def test_the_secret_is_made_by_render_and_never_written_in_the_file():
    assert env_vars()["CT_SECRET"] == {"generateValue": "true"}
    assert "sync: false" not in RENDER  # nothing a person has to type into the Blueprint


def test_the_python_version_is_pinned_and_allowed_by_the_project():
    value = env_vars()["PYTHON_VERSION"]["value"]
    match = re.fullmatch(r'"3\.(\d+)\.(\d+)"', value)  # Render needs a fully qualified version
    assert match, value
    requires = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["requires-python"]
    assert requires == ">=3.11"
    assert int(match.group(1)) >= 11


# ---- the pinned production server -----------------------------------------------------------------


def test_gunicorn_is_in_the_deploy_group_only():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert not any("gunicorn" in dep for dep in project["project"]["dependencies"])  # local play needs no gunicorn
    assert not any("gunicorn" in dep for dep in project["dependency-groups"]["dev"])
    assert any(dep.startswith("gunicorn") for dep in project["dependency-groups"]["deploy"])


def test_the_lockfile_pins_gunicorn_for_the_deploy_group():
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    packages = {p["name"]: p for p in lock["package"]}
    assert packages["gunicorn"]["version"].startswith("26.")
    ours = packages["campus-tycoon"]
    assert {"name": "gunicorn"} in ours["dev-dependencies"]["deploy"]
