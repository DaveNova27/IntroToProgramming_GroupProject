"""Checks from specs/day-cycle.md ("Done when"). The day cycle is drawn in the browser; the
server only holds the wake-up spot and keeps every rule as before."""

import json
import math
import shutil
import subprocess
from pathlib import Path

import pytest

import app
import db
import world
from test_world_api import is_blocked as blocked
from test_world_api import run_on_disk  # noqa: F401 (a fixture, used by name)

WORLD_JS = Path(__file__).resolve().parent.parent / "static" / "world"
REACH = 1.65  # static/world/locations.js
NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="Node is not installed")


# ---- Check 1: the wake-up spot ---------------------------------------------------------------------

def test_the_wake_up_spot_is_free_inside_the_dorm_and_next_to_the_bed():
    wake = world.DORM["wake"]
    assert wake["zone"] == "campus"
    zone = world.ZONES["campus"]
    assert zone["minX"] <= wake["x"] <= zone["maxX"] and zone["minY"] <= wake["y"] <= zone["maxY"]
    part = world.DORM["parts"][0]
    wall = world.DORM["wall"]
    assert part["x"] + wall < wake["x"] < part["x"] + part["w"] - wall
    assert part["y"] + wall < wake["y"] < part["y"] + part["h"] - wall
    assert not blocked(wake["x"], wake["y"], world.colliders("campus"))
    bed = world.DORM["bed"]
    assert math.hypot(wake["x"] - bed["x"], wake["y"] - bed["y"]) < REACH, "the bed is in reach on waking"


def test_the_wake_up_spot_is_sent_to_the_browser():
    assert world.world_view()["dorm"]["wake"] == world.DORM["wake"]


def test_the_wake_up_spot_is_saved_like_any_position(run_on_disk):  # noqa: F811
    wake = world.DORM["wake"]
    body = {"zone": wake["zone"], "x": wake["x"], "y": wake["y"]}
    response = app.app.test_client().post("/api/player", json=body)
    assert response.status_code == 200
    assert db.load(run_on_disk)["player"] == body


# ---- Check 3: no new endpoint, no new rule ---------------------------------------------------------

def test_the_day_cycle_adds_no_endpoint():
    rules = {rule.rule for rule in app.app.url_map.iter_rules()}
    assert not [r for r in rules if "sleep" in r or "wake" in r or "home" in r or "evening" in r]


def test_a_crafted_skip_without_an_open_day_is_refused_and_changes_nothing(run_on_disk):  # noqa: F811
    before = db.load(run_on_disk)
    response = app.app.test_client().post("/api/shift/skip", json={})
    assert response.status_code == 400
    assert db.load(run_on_disk) == before


def test_the_evening_hint_offers_go_home_and_skip_the_walk():
    page = (WORLD_JS.parent / "map.html").read_text()
    assert 'id="btn-go-home"' in page and 'id="btn-skip-walk"' in page


def test_ending_a_day_early_asks_first_and_then_sends_the_skip_that_exists():
    page = (WORLD_JS.parent / "map.html").read_text()
    assert 'id="end-day-dialog"' in page
    ui = (WORLD_JS / "ui.js").read_text()
    assert 'shiftAction("/api/shift/skip", {})' in ui  # the same request as before, no new one


def test_the_browser_draws_the_cycle_without_randomness_or_server_calls_from_the_figures():
    for name in ("main.js", "ui.js", "player.js", "people.js"):
        assert "Math.random" not in (WORLD_JS / name).read_text(), name
    people = (WORLD_JS / "people.js").read_text()
    assert '"lie"' in people, "the figure knows the pose for lying in bed"


# ---- Check 2: "Go home" finds the bed from anywhere (the real browser modules, Node) -----------------

# Walks from the far places of the map (the shops on the beach, the Nova, the spawn) and from many
# spread-out spots to the bed, the same way "Go home" does in main.js: findPath to the free point
# closest to the bed, which must end in reach of it, without walking through anything.
GO_HOME = """
import { readFileSync } from "node:fs";
import { findPath } from "./paths.js";
import { nearestFreePoint, pointBlocked } from "./physics.js";

const RADIUS = 0.28;
const REACH = 1.65;
const { world, starts } = JSON.parse(readFileSync(process.argv[2]));
const zone = world.zones.campus;
const solid = world.colliders.campus;
const bed = world.dorm.bed;
const goal = nearestFreePoint({ x: bed.x, y: bed.y }, zone, solid, RADIUS);
for (let i = 0; i < 40; i++) {
  starts.push({
    x: zone.minX + 0.3 + (zone.maxX - zone.minX - 0.6) * ((i * 0.6180339) % 1),
    y: zone.minY + 0.3 + (zone.maxY - zone.minY - 0.6) * ((i * 0.7548776) % 1),
  });
}
const problems = [];
let checked = 0;
for (const start of starts.filter((p) => !pointBlocked(p, solid, RADIUS))) {
  checked++;
  const path = findPath(start, goal, zone, solid, RADIUS);
  if (!path) {
    problems.push(`no way home from ${start.x.toFixed(1)}, ${start.y.toFixed(1)}`);
    continue;
  }
  const end = path[path.length - 1];
  if (Math.hypot(end.x - bed.x, end.y - bed.y) >= REACH) problems.push("the walk ends out of reach of the bed");
  let from = start;
  path.slice(0, -1).forEach((to) => {
    const steps = Math.ceil(Math.hypot(to.x - from.x, to.y - from.y) / 0.05);
    for (let i = 1; i <= steps; i++) {
      const p = { x: from.x + ((to.x - from.x) * i) / steps, y: from.y + ((to.y - from.y) * i) / steps };
      if (pointBlocked(p, solid, RADIUS - 0.01)) problems.push("the way home walks through something");
    }
    from = to;
  });
}
console.log(JSON.stringify({ checked, problems: [...new Set(problems)] }));
"""


def far_places():
    """The front of every outdoor shop, a spot in every room of the Nova, and the spawn."""
    places = [dict(world.ZONES["campus"]["spawn"])]
    places += [dict(shop["front"]) for shop in world.SHOPS_OUTDOOR]
    for area in world.INTERIORS["campus"]["areas"]:
        places.append({"x": area["x"] + area["w"] / 2, "y": area["y"] + area["h"] / 2})
    return places


@needs_node
def test_go_home_reaches_the_bed_from_the_beach_the_shops_and_the_nova(tmp_path):
    for name in ("paths.js", "physics.js"):
        shutil.copy(WORLD_JS / name, tmp_path)
    (tmp_path / "package.json").write_text('{"type": "module"}')
    (tmp_path / "go_home.js").write_text(GO_HOME)
    (tmp_path / "input.json").write_text(json.dumps({"world": world.world_view(), "starts": far_places()}))
    done = subprocess.run(
        [NODE, "go_home.js", "input.json"], cwd=tmp_path, capture_output=True, text=True, timeout=120,
    )
    assert done.returncode == 0, done.stderr
    result = json.loads(done.stdout)
    assert result["checked"] > 30
    assert result["problems"] == []
