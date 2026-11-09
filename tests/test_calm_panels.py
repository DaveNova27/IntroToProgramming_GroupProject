"""Checks from specs/calm-panels.md: requests wait for each other, panels redraw only when needed,
and the outdated texts are gone. The serial helper runs for real with Node (skipped without it)."""

import shutil
import subprocess
from pathlib import Path

import pytest

import app

STATIC = Path(app.__file__).parent / "static"
NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="Node is not installed")

CHECK = """
import { createSerial } from "%s";
const { run, once } = createSerial();
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
const log = [];

// jobs run one after the other, in the order they came, none is dropped
await Promise.all([
  run(async () => { log.push("a start"); await wait(30); log.push("a end"); }),
  run(async () => { log.push("b start"); await wait(5); log.push("b end"); }),
  run(async () => { log.push("c start"); log.push("c end"); }),
]);

// a job that fails does not stop the ones after it
let failed = false;
await run(async () => { throw new Error("boom"); }).catch(() => { failed = true; });
await run(async () => { log.push("after failure"); });

// once(): a second tick while the first one waits is ignored, a later one runs again
const ticks = [];
const slow = run(async () => { await wait(30); });
const t1 = once("tick", async () => { ticks.push(1); });
const t2 = once("tick", async () => { ticks.push(2); });
await Promise.all([slow, t1, t2]);
await once("tick", async () => { ticks.push(3); });

console.log(JSON.stringify({ log, failed, ticks }));
"""


@needs_node
def test_requests_wait_for_each_other_and_ticks_do_not_pile_up(tmp_path):
    script = tmp_path / "check.mjs"
    script.write_text(CHECK % (STATIC / "world" / "serial.js").as_uri())
    done = subprocess.run([NODE, str(script)], capture_output=True, text=True, timeout=30)
    assert done.returncode == 0, done.stderr
    import json
    result = json.loads(done.stdout)
    assert result["log"] == ["a start", "a end", "b start", "b end", "c start", "c end", "after failure"]
    assert result["failed"] is True
    assert result["ticks"] == [1, 3]


def test_outdated_texts_are_gone():
    ui = (STATIC / "world" / "ui.js").read_text()
    dashboard = (STATIC / "app.js").read_text()
    assert "number of customers yet" not in ui  # "the weather does not change the number of customers yet"
    assert "above twice the reference" not in dashboard


def test_the_panels_do_not_drop_a_click_while_a_request_runs():
    ui = (STATIC / "world" / "ui.js").read_text()
    assert "shiftBusy" not in ui
    assert "createSerial" in ui
