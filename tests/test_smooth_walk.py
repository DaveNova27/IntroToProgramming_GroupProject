"""Walking glides along objects instead of getting stuck (specs/smooth-walk.md).

Runs the real `physics.js` with Node, like tests/test_click_walk.py. A walker holds one direction
key (W A S D, also diagonal) and walks at a free-standing round object (palm, lamp, post ...), from
many directions and with many side offsets. Before the change most of these walks stopped in front
of the object; now each one must get past it. Two more checks keep the old behaviour where it
matters: walking straight into a wall still stops at the wall, and no step ever ends inside an object.
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
import { pointBlocked, resolveMovement } from "./physics.js";

// the numbers of the walk in main.js: radius, speed (tiles per second), one frame at 30 fps
const RADIUS = 0.28, SPEED = 3.5, DT = 1 / 30;
const data = JSON.parse(readFileSync(process.argv[2]));
const zone = data.zones.campus, solid = data.colliders.campus;

// Holds one direction for at most 3 seconds. "past" once the walker is beyond the object.
function holdKey(start, dx, dy, beyond) {
  let position = start, inside = 0;
  for (let time = 0; time < 3; time += DT) {
    position = resolveMovement(position, { x: dx * SPEED * DT, y: dy * SPEED * DT }, zone, solid, RADIUS);
    if (pointBlocked(position, solid, RADIUS)) inside++;
    if (beyond(position)) return { past: true, inside, position };
  }
  return { past: false, inside, position };
}

// 1. round objects with nothing else close by and away from the edge of the campus
const lonely = solid.filter((c) => {
  if (c.shape !== "circle") return false;
  const reach = c.radius + RADIUS;
  const room = reach + 1.5;
  if (c.x - zone.minX < room || zone.maxX - c.x < room || c.y - zone.minY < room || zone.maxY - c.y < room) return false;
  return !solid.some((other) => other !== c && pointBlocked({ x: c.x, y: c.y }, [other], reach + 2 * RADIUS + 0.3));
});
let walks = 0, stuck = 0, inside = 0;
const examples = [];
for (const c of lonely) {
  const reach = c.radius + RADIUS;
  for (let a = 0; a < 16; a++) {
    const angle = (a * Math.PI) / 8, dx = Math.cos(angle), dy = Math.sin(angle);
    for (let o = -0.95; o <= 0.951; o += 0.05) {
      // start 0.6 tiles in front of the object, shifted to the side by o times its reach
      const start = { x: c.x - dx * (reach + 0.6) - dy * o * reach, y: c.y - dy * (reach + 0.6) + dx * o * reach };
      const walk = holdKey(start, dx, dy, (p) => (p.x - c.x) * dx + (p.y - c.y) * dy > reach);
      walks++;
      inside += walk.inside;
      if (!walk.past) {
        stuck++;
        if (examples.length < 5) examples.push({ id: c.id, angle: a, offset: Number(o.toFixed(2)) });
      }
    }
  }
}

// 2. straight into the long side of a wall: still stops at the wall, does not slide or pass
const wall = solid
  .filter((c) => c.shape === "rect" && c.label === "Wall" && c.width >= 3 && c.height < 1)
  .sort((a, b) => a.y - b.y)[0];
let wallWalk = null;
if (wall) {
  const start = { x: wall.x + wall.width / 2, y: wall.y - RADIUS - 0.6 };
  const free = !pointBlocked(start, solid, RADIUS);
  const walk = holdKey(start, 0, 1, (p) => p.y > wall.y);
  const slid = Math.abs(walk.position.x - start.x);
  wallWalk = { id: wall.id, free, past: walk.past, inside: walk.inside, slid };
}

// 3. the same step gives the same result (no randomness)
const palm = lonely.find((c) => c.label === "Palm tree") ?? lonely[0];
const headOn = { x: palm.x - (palm.radius + RADIUS + 0.6), y: palm.y };
const once = holdKey(headOn, 1, 0, (p) => p.x > palm.x + palm.radius + RADIUS);
const again = holdKey(headOn, 1, 0, (p) => p.x > palm.x + palm.radius + RADIUS);

console.log(JSON.stringify({
  objects: lonely.length, walks, stuck, inside, examples, wallWalk,
  headOn: { id: palm.id, past: once.past, same: JSON.stringify(once) === JSON.stringify(again) },
}));
"""


@pytest.fixture(scope="module")
def result(tmp_path_factory):
    if NODE is None:
        pytest.skip("Node is not installed")
    folder = tmp_path_factory.mktemp("smooth_walk")
    shutil.copy(WORLD / "physics.js", folder)
    (folder / "package.json").write_text('{"type": "module"}')
    (folder / "check.js").write_text(CHECK)
    (folder / "world.json").write_text(json.dumps(world.world_view()))
    done = subprocess.run([NODE, "check.js", "world.json"], cwd=folder, capture_output=True, text=True, timeout=120)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


def test_walking_at_a_round_object_glides_past_it(result):
    # before the change more than half of these walks stopped in front of the object
    assert result["objects"] >= 5, result
    assert result["stuck"] == 0, result


def test_straight_at_a_palm_still_gets_past(result):
    assert result["headOn"]["past"], result
    assert result["headOn"]["same"], result


def test_no_step_ends_inside_an_object(result):
    assert result["inside"] == 0, result


def test_straight_into_a_wall_still_stops(result):
    wall = result["wallWalk"]
    assert wall is not None and wall["free"], result
    assert not wall["past"], wall
    assert wall["inside"] == 0, wall
    assert wall["slid"] < 0.01, wall
