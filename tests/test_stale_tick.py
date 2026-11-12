"""Checks from specs/stale-tick.md: once the run is replaced (a demo scenario, the end of the demo,
a new run) no tick of the old run goes out and no old answer is taken over. The browser was checked
with a scripted run of the four scenarios (see the spec); these keep the wiring in place."""

import re
from pathlib import Path

import app

UI = (Path(app.__file__).parent / "static" / "world" / "ui.js").read_text(encoding="utf-8")


def body(name):
    """The text of a top-level function in ui.js, up to the next line that closes it."""
    match = re.search(rf"^(?:async )?function {name}\(.*?^}}$", UI, re.S | re.M)
    assert match, f"function {name} not found in ui.js"
    return match.group(0)


def test_replace_run_stops_the_clock_before_the_request():
    text = body("replaceRun")
    assert "runGen++" in text
    stop = text.index("clearInterval(shiftTimer)")
    assert stop < text.index("requests.run(job)"), "the clock must stop before the job is queued"
    assert "syncShiftTimer" in text, "without an answer the clock must start again"


def test_a_tick_from_the_old_run_is_not_sent_and_its_answer_is_dropped():
    text = body("shiftTick")
    assert "const gen = runGen" in text
    send = text.index('send("/api/shift/tick"')
    assert text.index("gen !== runGen") < send, "a tick of the old run must not be sent"
    assert "gen !== runGen" in text[send:], "the answer of a tick of the old run must be dropped"


def test_a_click_from_the_old_run_is_not_sent():
    text = body("shiftAction")
    assert "const gen = runGen" in text
    assert text.index("gen !== runGen") < text.index("send(path, body)")


def test_every_way_that_replaces_the_run_goes_through_replace_run():
    for path in ("/api/demo/load", "/api/demo/finish", "/api/new-run"):
        at = UI.index(f'send("{path}"')
        assert "replaceRun(" in UI[at - 300:at], f"{path} is not sent through replaceRun"


def test_a_new_run_from_the_dashboard_also_ends_the_old_ticks():
    assert "runGen++" in body("syncFromDashboard")
