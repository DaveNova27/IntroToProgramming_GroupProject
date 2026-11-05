"""Checks from specs/world-core.md ("Done when"), check 4 and the module syntax.

These run the real browser modules with Node. GitHub Actions has Node; on a computer
without it they are skipped, and everything else still runs.
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
MODULES = sorted(WORLD.glob("*.js"))

needs_node = pytest.mark.skipif(NODE is None, reason="Node is not installed")

# Walk from many places to every door and desk and check the whole way.
CHECK = """
import { readFileSync } from "node:fs";
import { findPath } from "./paths.js";
import { nearestFreePoint, pointBlocked } from "./physics.js";

const RADIUS = 0.28;
const REACH = 1.65;
const world = JSON.parse(readFileSync(process.argv[2]));
const problems = [];
let checked = 0;
for (const [zoneId, zone] of Object.entries(world.zones)) {
  const solid = world.colliders[zoneId];
  const starts = [zone.spawn];
  for (let i = 0; i < 40; i++) {
    starts.push({
      x: zone.minX + 0.3 + (zone.maxX - zone.minX - 0.6) * ((i * 0.6180339) % 1),
      y: zone.minY + 0.3 + (zone.maxY - zone.minY - 0.6) * ((i * 0.7548776) % 1),
    });
  }
  for (const start of starts.filter((p) => !pointBlocked(p, solid, RADIUS))) {
    for (const loc of Object.values(world.locations).filter((l) => l.zone === zoneId)) {
      checked++;
      // the same goal as a click on it in main.js
      const goal = nearestFreePoint({ x: loc.x, y: loc.y }, zone, solid, RADIUS);
      const path = findPath(start, goal, zone, solid, RADIUS);
      if (!path) {
        problems.push(`no way to ${loc.title} in ${zoneId}`);
        continue;
      }
      const end = path[path.length - 1];
      if (Math.hypot(end.x - loc.x, end.y - loc.y) >= REACH) problems.push(`${loc.title} out of reach`);
      let from = start;
      path.slice(0, -1).forEach((to) => {
        const steps = Math.ceil(Math.hypot(to.x - from.x, to.y - from.y) / 0.05);
        for (let i = 1; i <= steps; i++) {
          const p = { x: from.x + ((to.x - from.x) * i) / steps, y: from.y + ((to.y - from.y) * i) / steps };
          if (pointBlocked(p, solid, RADIUS - 0.01)) problems.push(`walks through something in ${zoneId}`);
        }
        from = to;
      });
    }
  }
}
console.log(JSON.stringify({ checked, problems: [...new Set(problems)] }));
"""


@needs_node
def test_every_door_and_desk_can_be_reached_from_anywhere(tmp_path):
    for name in ("paths.js", "physics.js"):
        shutil.copy(WORLD / name, tmp_path)
    (tmp_path / "package.json").write_text('{"type": "module"}')
    (tmp_path / "check.js").write_text(CHECK)
    (tmp_path / "world.json").write_text(json.dumps(world.world_view()))
    done = subprocess.run(
        [NODE, "check.js", "world.json"], cwd=tmp_path, capture_output=True, text=True, timeout=60,
    )
    assert done.returncode == 0, done.stderr
    result = json.loads(done.stdout)
    assert result["checked"] > 100
    assert result["problems"] == []


@needs_node
@pytest.mark.parametrize("module", MODULES, ids=lambda m: m.name)
def test_every_module_has_valid_syntax(tmp_path, module):
    (tmp_path / "package.json").write_text('{"type": "module"}')
    shutil.copy(module, tmp_path)
    done = subprocess.run([NODE, "--check", module.name], cwd=tmp_path, capture_output=True, text=True, timeout=30)
    assert done.returncode == 0, done.stderr
