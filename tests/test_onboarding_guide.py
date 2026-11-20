"""Checks from specs/onboarding-guide.md ("Done when"): a guide with three steps for the first day.

Which step is done is a pure module (static/world/guide.js), run here with Node against app.view of
real states; the page itself is checked in its source like the other page tests.
"""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

import app
import logic

STATIC = Path(app.__file__).parent / "static"
GUIDE = STATIC / "world" / "guide.js"
UI = (STATIC / "world" / "ui.js").read_text()
HTML = (STATIC / "map.html").read_text()
CSS = (STATIC / "map.css").read_text()
NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="Node is not installed")


def run_guide(view, remembered=None):
    """guideSteps, guideVisible and guideAllDone of one view, in Node."""
    script = (
        f"import {{ guideSteps, guideVisible, guideAllDone }} from {json.dumps(GUIDE.as_uri())};"
        f"const view = {json.dumps(view)}, remembered = {json.dumps(remembered)};"
        "console.log(JSON.stringify({steps: guideSteps(view), visible: guideVisible(view, remembered),"
        " allDone: guideAllDone(view, remembered)}));"
    )
    done = subprocess.run([NODE, "--input-type=module", "-e", script], capture_output=True, text=True, timeout=60)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


def done_map(result):
    return {s["id"]: s["done"] for s in result["steps"]}


def current(result):
    return [s["id"] for s in result["steps"] if s["current"]]


def first_day():
    """A new run: day 1, nothing bought, the day not open."""
    return logic.new_state(1)


def ordered():
    return logic.buy(first_day(), "coffee", 12)


def opened():
    return logic.open_day(ordered())


def on_shift():
    return logic.start_shift(opened(), "cafe")


@needs_node
def test_a_new_run_shows_the_guide_with_the_first_step_current():
    result = run_guide(app.view(first_day()))
    assert [s["id"] for s in result["steps"]] == ["order", "open", "shift"]
    assert done_map(result) == {"order": False, "open": False, "shift": False}
    assert current(result) == ["order"]
    assert result["visible"] and not result["allDone"]


@needs_node
def test_the_steps_tick_one_after_the_other_from_the_servers_state():
    after_order = run_guide(app.view(ordered()))
    assert done_map(after_order) == {"order": True, "open": False, "shift": False}
    assert current(after_order) == ["open"] and after_order["visible"]

    after_open = run_guide(app.view(opened()))
    assert done_map(after_open) == {"order": True, "open": True, "shift": False}
    assert current(after_open) == ["shift"] and after_open["visible"]

    after_shift = run_guide(app.view(on_shift()))
    assert all(done_map(after_shift).values()) and current(after_shift) == []
    assert not after_shift["visible"] and after_shift["allDone"]  # "All set", then it goes


@needs_node
def test_opening_without_ordering_keeps_the_order_step_current():
    result = run_guide(app.view(logic.open_day(first_day())))
    assert done_map(result)["open"] and not done_map(result)["order"]
    assert current(result) == ["order"]


@needs_node
def test_a_played_day_ends_the_guide_without_all_set():
    state, _ = logic.skip_shift(opened())
    result = run_guide(app.view(state))
    assert state["history"]
    assert not result["visible"] and not result["allDone"]


@needs_node
def test_no_guide_in_a_demo_or_on_a_complete_run():
    demo = app.view(first_day())
    demo["demo"] = {**(demo.get("demo") or {}), "active": {"id": "serve-the-cafe"}}
    assert not run_guide(demo)["visible"]
    demo_done = app.view(on_shift())
    demo_done["demo"] = {**(demo_done.get("demo") or {}), "active": {"id": "serve-the-cafe"}}
    assert not run_guide(demo_done)["allDone"]  # a scenario's state never fakes "All set"
    finished = app.view(first_day())
    finished["finished"] = True
    assert not run_guide(finished)["visible"]


@needs_node
@pytest.mark.parametrize("remembered", ["done", "closed"])
def test_a_finished_or_closed_guide_stays_away(remembered):
    result = run_guide(app.view(first_day()), remembered)
    assert not result["visible"] and not result["allDone"]


def test_the_card_is_on_the_page_and_hidden_until_drawn():
    card = re.search(r'<aside id="guide-card".*?</aside>', HTML, re.S)
    assert card and " hidden" in card.group(0).split(">")[0]
    for part in ('id="guide-close"', 'aria-label="Close the guide"', 'id="guide-steps"', 'id="guide-note"'):
        assert part in card.group(0)


def test_review_findings_screen_readers_hear_it_and_the_box_is_shared():
    card = re.search(r'<aside id="guide-card".*?</aside>', HTML, re.S).group(0)
    assert '<p id="guide-live" class="guide-sr" aria-live="polite"></p>' in card
    assert '$("#guide-live").textContent = `Step done. Next: ${next.text}.`;' in UI
    assert '$("#guide-live").textContent = "All set. Good luck with the season!";' in UI
    assert re.search(r"^\.demo-card, \.guide-card \{\n  position: absolute;", CSS, re.M)  # one box, two cards


def test_go_presses_the_toolbars_own_buttons_and_nothing_new():
    assert 'import { guideAllDone, guideSteps, guideVisible } from "./guide.js";' in UI
    assert 'const buttons = { order: "#btn-order", open: "#btn-open", shift: "#btn-shift" };' in UI
    assert "$(buttons[step]).click();" in UI
    wire = UI.split("function wireGuide() {")[1].split("\n}\n")[0]
    assert "send(" not in wire and "fetch(" not in wire  # no request of its own
    assert "wireGuide();" in UI
    # found in the browser check: an order redraws only the HUD, so the guide must tick from there
    hud = UI.split("function renderHud() {")[1].split("\n}\n")[0]
    assert "renderGuide();" in hud


def test_the_choice_is_remembered_safely_in_this_browser_only():
    assert 'const GUIDE_KEY = "ct-guide";' in UI
    assert re.search(r"try \{\s*const kept = localStorage\.getItem\(GUIDE_KEY\);[^}]*\} catch", UI)
    assert re.search(r"try \{ localStorage\.setItem\(GUIDE_KEY, value\); \} catch", UI)


def test_the_guide_stays_out_of_the_way_on_phones_and_in_the_preview():
    assert re.search(r"body\.preview \.guide-card \{ display: none !important; \}", CSS)
    phone = CSS.split("/* the guide for the first day")[1].split("/* popularity")[0]
    narrow = phone[phone.index("@media (max-width: 760px)"):]
    assert ".guide-card { top: 110px; bottom: auto;" in narrow
    assert ".guide-step:not(.current) { display: none; }" in narrow
    assert '".guide-card"' in UI.split("function badgeTop() {")[1].split("\n}\n")[0]  # badge card below it


@needs_node
def test_the_modules_still_parse():
    for path in (GUIDE, STATIC / "world" / "ui.js"):
        done = subprocess.run([NODE, "--check", str(path)], capture_output=True, text=True, timeout=60)
        assert done.returncode == 0, (path.name, done.stderr)
