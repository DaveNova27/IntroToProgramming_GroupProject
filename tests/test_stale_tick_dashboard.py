"""Checks from specs/stale-tick.md, part 2: a new run started on the dashboard is sent by the campus
(from the queue of its ticks) once the campus runs; before that the dashboard sends it itself. The
wiring is checked by its text; the browser was checked with a script (see the spec)."""

from pathlib import Path

import app

STATIC = Path(app.__file__).parent / "static"
APP = (STATIC / "app.js").read_text(encoding="utf-8")
VIEWS = (STATIC / "views.js").read_text(encoding="utf-8")
UI = (STATIC / "world" / "ui.js").read_text(encoding="utf-8")


def test_the_dashboard_asks_the_campus_first_and_sends_only_without_it():
    at = APP.index('"new-run-wanted"')
    wired = APP[at:at + 400]
    assert "cancelable: true" in wired
    assert 'if (!byCampus) send("/api/new-run"' in wired


def test_the_campus_takes_it_over_only_once_it_runs():
    at = VIEWS.index('window.addEventListener("new-run-wanted"')
    handler = VIEWS[at:VIEWS.index("\n});", at)]
    assert handler.index("if (!mapReady) return") < handler.index("e.preventDefault()")
    assert 'tellMap({ type: "new-run" })' in handler
    assert "mapReady = true" in VIEWS[VIEWS.index('msg.type === "ready"'):]
    assert 'msg.type === "new-run-done"' in VIEWS  # its answer becomes the dashboard's message


def test_the_campus_sends_it_from_the_queue_of_its_ticks():
    at = UI.index('if (msg.type === "new-run")')
    assert "newRun()" in UI[at:at + 120]
    assert 'tellDashboard({ type: "new-run-done"' in UI[at:at + 300]
    new_run = UI[UI.index("function newRun()"):]
    assert new_run.index("requests.run(async") < new_run.index('send("/api/new-run"')
    assert UI.count('send("/api/new-run"') == 1  # the campus dialog uses the same function
