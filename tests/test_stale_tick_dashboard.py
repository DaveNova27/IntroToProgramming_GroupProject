"""Checks from specs/stale-tick.md, part 2: a new run started on the dashboard is sent by the campus
(from the queue of its ticks) once the campus runs; before that the dashboard sends it itself. The
dashboard shows that it waits, tells when the campus does not answer, and shows a refused request's
state. The wiring is checked by its text (functions cut out whole); the browser was checked with a
script (see the spec)."""

import re
from pathlib import Path

import app

STATIC = Path(app.__file__).parent / "static"
APP = (STATIC / "app.js").read_text(encoding="utf-8")
VIEWS = (STATIC / "views.js").read_text(encoding="utf-8")
UI = (STATIC / "world" / "ui.js").read_text(encoding="utf-8")


def body(source, name):
    """The text of a top-level function, up to the line that closes it."""
    match = re.search(rf"^(?:async )?function {name}\(.*?^}}$", source, re.S | re.M)
    assert match, f"function {name} not found"
    return match.group(0)


def test_the_dashboard_asks_the_campus_first_and_sends_only_without_it():
    wire = body(APP, "wireNewRun")
    assert "if (!window.newRunByCampus?.()) send(\"/api/new-run\"" in wire


def test_the_campus_takes_it_over_only_once_it_runs_and_only_once_at_a_time():
    handoff = body(VIEWS, "newRunByCampus")
    assert handoff.index("if (!mapReady) return false") < handoff.index('tellMap({ type: "new-run" })')
    assert handoff.index("if (newRunWait) return true") < handoff.index('tellMap({ type: "new-run" })')
    assert 'classList.add("busy")' in handoff  # the dashboard shows that it waits
    assert "not answered" in handoff  # and says so when the campus never answers
    assert "mapReady = true" in VIEWS[VIEWS.index('msg.type === "ready"'):]
    assert 'classList.remove("busy")' in body(VIEWS, "newRunAnswered")


def test_the_answer_of_the_campus_reaches_the_dashboard_even_when_it_was_refused():
    done = VIEWS[VIEWS.index('msg.type === "new-run-done"'):]
    done = done[:done.index("if (msg.type ===", 10)] if "if (msg.type ===" in done[10:] else done
    assert "newRunAnswered()" in done
    assert "applyExternalState(msg.state)" in done  # a refused request still sends the state
    new_run = body(UI, "newRun")
    assert "if (data.state) state = data.state" in new_run  # an answer without a state changes nothing
    assert "state: data.state" in new_run
    assert "{ keep: true }" in new_run  # never dropped by an earlier replacement


def test_the_campus_answers_the_dashboard_from_its_message_handler():
    at = UI.index('if (msg.type === "new-run")')
    handler = UI[at:UI.index("\n    }\n", at)]
    assert "newRun()" in handler
    assert 'tellDashboard({ type: "new-run-done"' in handler
    assert UI.count('send("/api/new-run"') == 1  # the campus dialog uses the same function
