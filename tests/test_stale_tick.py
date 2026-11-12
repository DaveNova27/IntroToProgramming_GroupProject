"""Checks from specs/stale-tick.md: a request that replaces the run waits in the queue of the ticks,
and once it worked no tick or click queued for the old run goes out. The queue (serial.js) runs for
real with Node (skipped without it); the wiring in ui.js is checked by its text. The browser was
checked with a scripted run of the four demo scenarios (see the spec)."""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

import app

STATIC = Path(app.__file__).parent / "static"
UI = (STATIC / "world" / "ui.js").read_text(encoding="utf-8")
NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="Node is not installed")

CHECK = """
import { createSerial } from "%s";
const { run, once, renew } = createSerial();
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
const sent = [];
const out = {};

// the replacing request waits for a tick already on its way: never both at once
let inFlight = 0, overlap = false;
const request = (name, ms) => async () => {
  inFlight++; if (inFlight > 1) overlap = true;
  sent.push(name); await wait(ms); inFlight--;
};
const tick1 = once("tick", request("tick 1", 30));
const load = run(async () => { await request("load", 20)(); renew(); }); // the load worked
const tick2 = once("tick", request("tick 2 (old run)", 5));  // queued during the load: dropped
const click = run(request("sell (old run)", 5));             // queued during the load: dropped
await Promise.all([tick1, load, tick2, click]);
await once("tick", request("tick 3 (new run)", 5));          // queued after: sent
out.overlap = overlap;

// a replacement that failed (no renew) drops nothing
const kept = [];
const failed = run(async () => { await wait(10); });
const sell = run(async () => { kept.push("sell"); });
await Promise.all([failed, sell]);
out.kept = kept;

// a job already sent can see that the run was replaced meanwhile (the dashboard's new run)
let seen = null;
const job = run(async (stale) => { await wait(20); seen = stale(); });
await wait(5); renew();
await job;
out.staleAfterRenew = seen;
let fresh = null;
await run(async (stale) => { fresh = stale(); });
out.staleWithoutRenew = fresh;

out.sent = sent;
console.log(JSON.stringify(out));
"""


@needs_node
def test_the_queue_drops_what_was_queued_for_the_replaced_run(tmp_path):
    script = tmp_path / "check.mjs"
    script.write_text(CHECK % (STATIC / "world" / "serial.js").as_uri())
    done = subprocess.run([NODE, str(script)], capture_output=True, text=True, timeout=30)
    assert done.returncode == 0, done.stderr
    result = json.loads(done.stdout)
    assert result["sent"] == ["tick 1", "load", "tick 3 (new run)"]
    assert result["overlap"] is False
    assert result["kept"] == ["sell"]
    assert result["staleAfterRenew"] is True
    assert result["staleWithoutRenew"] is False


def body(name):
    """The text of a top-level function in ui.js, up to the line that closes it."""
    match = re.search(rf"^(?:async )?function {name}\(.*?^}}$", UI, re.S | re.M)
    assert match, f"function {name} not found in ui.js"
    return match.group(0)


def test_every_request_that_replaces_the_run_waits_in_the_queue_of_the_ticks():
    for path in ("/api/demo/load", "/api/demo/finish", "/api/new-run"):
        at = UI.index(f'send("{path}"')
        start = UI.rindex("requests.run(async", 0, at)
        assert "\n\n" not in UI[start:at], f"{path} is not sent from inside requests.run"


def test_the_old_run_ends_only_when_the_replacement_worked():
    assert "requests.renew()" in body("freshRun")  # new run and demo load, after a good answer
    assert "requests.renew()" in body("syncFromDashboard")
    finish = UI[UI.index('send("/api/demo/finish"'):]
    assert finish.index("if (!data.error) requests.renew()") < finish.index("})),")


def test_a_tick_answer_of_the_replaced_run_is_not_taken_over():
    tick = body("shiftTick")
    assert tick.index("stale()") > tick.index('send("/api/shift/tick"')
