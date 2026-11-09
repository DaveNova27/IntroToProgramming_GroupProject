"""The real weather of a day is not sent before the day is open (review of PR #45)."""

import app
import db
import logic

SEED = 987654321


def test_real_weather_only_once_the_day_is_open(tmp_path, monkeypatch):
    path = tmp_path / "run.db"
    db.save(logic.new_state(SEED), path)
    real_save = db.save
    monkeypatch.setattr(app, "load_run", lambda: db.load(path))
    monkeypatch.setattr(app.db, "save", lambda state: real_save(state, path))
    client = app.app.test_client()

    before = client.get("/api/state").get_json()
    assert before["weather"] is None and before["outlook"] is not None

    opened = client.post("/api/day/open").get_json()["state"]
    assert opened["weather"]["id"] == logic.make_day_context(SEED, 1)["weather"]
