"""Click to walk does not give up halfway (specs/click-walk.md).

Runs the real browser modules with Node, like tests/test_world_paths.py: the route comes from
`findPath` and a copy of the walk loop of main.js (step, slide along a wall, give up after 0.5 s
without progress). main.js cannot run without a browser, so the numbers here (speed, 0.15 turn
tolerance, 0.5 s, the progress threshold) must be kept the same as in `walk()` there.
On a computer without Node the test is skipped.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

import app
import world

WORLD = Path(app.__file__).parent / "static" / "world"
NODE = shutil.which("node")

CHECK = """
import { readFileSync } from "node:fs";
import { findPath } from "./paths.js";
import { pointBlocked, resolveMovement } from "./physics.js";

const RADIUS = 0.28, SPEED = 3.5, DT = 1 / 30, PAIRS = 400;
const data = JSON.parse(readFileSync(process.argv[2]));
const zone = data.zones.campus, solid = data.colliders.campus;
let seed = 12345; // a fixed generator: the same pairs on every run
const random = () => (seed = (seed * 1664525 + 1013904223) % 4294967296) / 4294967296;
const pick = () => {
  for (;;) {
    const p = { x: zone.minX + 1 + random() * (zone.maxX - zone.minX - 2), y: zone.minY + 1 + random() * (zone.maxY - zone.minY - 2) };
    if (!pointBlocked(p, solid, RADIUS + 0.05)) return p;
  }
};
function walk(from, to) {
  let position = from;
  const route = findPath(position, to, zone, solid, RADIUS);
  if (!route) return "noWay";
  let stuck = 0, time = 0;
  while (route.length && time < 90) {
    let distance = Math.hypot(route[0].x - position.x, route[0].y - position.y);
    while (route.length && distance < 0.15) {
      route.shift();
      if (route.length) distance = Math.hypot(route[0].x - position.x, route[0].y - position.y);
    }
    if (!route.length) break;
    const delta = { x: ((route[0].x - position.x) / distance) * SPEED * DT, y: ((route[0].y - position.y) / distance) * SPEED * DT };
    position = resolveMovement(position, delta, zone, solid, RADIUS);
    const gained = distance - Math.hypot(route[0].x - position.x, route[0].y - position.y);
    stuck = gained > SPEED * DT * 0.2 ? 0 : stuck + DT;
    if (stuck > 0.5) return "gaveUp";
    time += DT;
  }
  return "arrived";
}
// the walk that stopped at the corner of hub-west-wall: from the Nova to the steps of the Dorm
const dorm = walk({ x: 23.06, y: 8.11 }, { x: 38, y: 12.9 });
let arrived = 0, gaveUp = 0, noWay = 0;
for (let i = 0; i < PAIRS; i++) {
  const outcome = walk(pick(), pick());
  if (outcome === "arrived") arrived++;
  else if (outcome === "gaveUp") gaveUp++;
  else noWay++;
}
console.log(JSON.stringify({ dorm, pairs: PAIRS, arrived, gaveUp, noWay }));
"""


@pytest.mark.skipif(NODE is None, reason="Node is not installed")
def test_a_clicked_route_is_walked_to_the_end(tmp_path):
    for name in ("paths.js", "physics.js"):
        shutil.copy(WORLD / name, tmp_path)
    (tmp_path / "package.json").write_text('{"type": "module"}')
    (tmp_path / "check.js").write_text(CHECK)
    (tmp_path / "world.json").write_text(json.dumps(world.world_view()))
    done = subprocess.run([NODE, "check.js", "world.json"], cwd=tmp_path, capture_output=True, text=True, timeout=120)
    assert done.returncode == 0, done.stderr
    result = json.loads(done.stdout)
    assert result["dorm"] == "arrived", result
    assert result["noWay"] == 0
    # before the fix 27 of 400 walks gave up at a corner, after it none does; a few are allowed so that
    # a change of the campus layout does not break this test for no reason of the route
    assert result["gaveUp"] <= 2, result
