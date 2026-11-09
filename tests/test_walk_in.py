"""Checks from specs/walk-in.md ("Done when"). One test per check.

The checks on the data and the way in run in Python. The checks on the roof and on walking
with the real browser modules run with Node, as in test_world_paths.py: GitHub Actions has
Node; on a computer without it they are skipped and everything else still runs.
"""

import json
import math
import shutil
import subprocess
from collections import deque
from pathlib import Path

import pytest

import app
import db
import logic
import world

WORLD = Path(app.__file__).parent / "static" / "world"
NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="Node is not installed")

RADIUS = 0.28  # the same as PLAYER_RADIUS in static/world/scene.js
REACH = 1.65  # the same as REACH in static/world/locations.js


def is_blocked(x, y, solid, radius=RADIUS):
    """The same check as pointBlocked in static/world/physics.js."""
    for item in solid:
        if item["shape"] == "circle":
            if math.hypot(x - item["x"], y - item["y"]) < item["radius"] + radius:
                return True
        else:
            nearest_x = min(max(x, item["x"]), item["x"] + item["width"])
            nearest_y = min(max(y, item["y"]), item["y"] + item["height"])
            if math.hypot(x - nearest_x, y - nearest_y) < radius:
                return True
    return False


def floor():
    """The walkable floor of the Nova: the footprint without its walls."""
    parts, wall = world.NOVA["parts"], world.NOVA["wall"]
    x0 = min(p["x"] for p in parts) + wall
    y0 = min(p["y"] for p in parts) + wall
    x1 = max(p["x"] + p["w"] for p in parts) - wall
    y1 = max(p["y"] + p["h"] for p in parts) - wall
    return x0, y0, x1, y1


def wing_floors():
    """The walkable floor of every wing (spec nova-wings): the box around the parts of the wing, without
    the thickness of the walls that run along its edges. Written from the parts and the walls only."""
    wall = world.NOVA["wall"]
    near = lambda a, b: abs(a - b) < 1e-9  # noqa: E731
    floors = {}
    for wing in world.NOVA["wings"]:
        parts = [p for p in world.NOVA["parts"] if p["wing"] == wing["id"]]
        x0 = min(p["x"] for p in parts)
        y0 = min(p["y"] for p in parts)
        x1 = max(p["x"] + p["w"] for p in parts)
        y1 = max(p["y"] + p["h"] for p in parts)
        along_x = [w for w in world.NOVA["walls"] if w["w"] > w["h"] and w["x"] < x1 and w["x"] + w["w"] > x0]
        along_y = [w for w in world.NOVA["walls"] if w["h"] >= w["w"] and w["y"] < y1 and w["y"] + w["h"] > y0]
        floors[wing["id"]] = (
            x0 + (wall if any(near(w["x"], x0) for w in along_y) else 0),
            y0 + (wall if any(near(w["y"], y0) for w in along_x) else 0),
            x1 - (wall if any(near(w["x"] + w["w"], x1) for w in along_y) else 0),
            y1 - (wall if any(near(w["y"] + w["h"], y1) for w in along_x) else 0),
        )
    return floors


def gaps():
    """Every way through a wall: the entrances and the openings between the wings."""
    return world.NOVA["entrances"] + world.NOVA.get("openings", [])


def inside(rect, x, y):
    return rect["x"] <= x <= rect["x"] + rect["w"] and rect["y"] <= y <= rect["y"] + rect["h"]


# ---- Check 1: one zone, and the Nova is a building on it --------------------

def test_there_is_one_zone_and_the_nova_stands_on_it():
    assert set(world.ZONES) == {"campus"}
    assert set(world.INTERIORS) == {"campus"}
    data = app.app.test_client().get("/api/world").get_json()
    assert set(data["zones"]) == {"campus"}
    assert set(data["colliders"]) == {"campus"}
    assert data["nova"]["parts"] and data["nova"]["walls"] and data["nova"]["entrances"]
    assert set(data["interiors"]) == {"campus"}


def test_the_removed_zones_have_no_colliders_any_more():
    for zone_id in ("mercado", "academy", "hub"):
        with pytest.raises(KeyError):
            world.colliders(zone_id)


def test_there_are_no_doors_only_desks():
    assert world.LOCATIONS
    assert all(loc["kind"] == "panel" for loc in world.LOCATIONS.values())
    assert all(loc["zone"] == "campus" for loc in world.LOCATIONS.values())


# ---- Check 2: the walls, the entrance and the rooms are consistent ----------

def test_the_nova_has_an_entrance_at_least_two_tiles_wide():
    entrances = world.NOVA["entrances"]
    assert entrances
    for entrance in entrances:
        assert entrance["width"] >= 2


def test_the_parts_form_one_connected_footprint():
    parts = world.NOVA["parts"]
    seen = {0}
    todo = [0]
    while todo:
        a = parts[todo.pop()]
        for index, b in enumerate(parts):
            touches = (
                a["x"] <= b["x"] + b["w"] and b["x"] <= a["x"] + a["w"]
                and a["y"] <= b["y"] + b["h"] and b["y"] <= a["y"] + a["h"]
            )
            if touches and index not in seen:
                seen.add(index)
                todo.append(index)
    assert seen == set(range(len(parts)))


def test_the_entrance_is_free_to_walk_through():
    solid = world.colliders("campus")
    for entrance in world.NOVA["entrances"]:
        # from the middle of the opening, across the wall, a player of the real size passes
        x_values = [entrance["x"] + entrance["width"] * f for f in (0.25, 0.5, 0.75)]
        for x in x_values:
            for y in (entrance["y"] - 1, entrance["y"] + 0.25, entrance["y"] + world.NOVA["wall"] + 1):
                assert not is_blocked(x, y, solid), (x, y)


def test_no_wall_covers_an_entrance():
    for entrance in world.NOVA["entrances"]:
        for wall in world.NOVA["walls"]:
            overlaps = (
                wall["x"] < entrance["x"] + entrance["width"] and entrance["x"] < wall["x"] + wall["w"]
                and wall["y"] < entrance["y"] + world.NOVA["wall"] and entrance["y"] < wall["y"] + wall["h"]
            )
            assert not overlaps, wall["id"]


def test_the_spawn_is_outside_and_free():
    spawn = world.ZONES["campus"]["spawn"]
    parts_cover = any(inside(p, spawn["x"], spawn["y"]) for p in world.NOVA["parts"])
    assert not parts_cover
    assert not is_blocked(spawn["x"], spawn["y"], world.colliders("campus"))


def test_every_solid_in_the_rooms_stands_on_the_floor_and_off_the_walls():
    x0, y0, x1, y1 = floor()
    for item in world.INTERIORS["campus"]["solid"]:
        if "r" in item:
            assert x0 <= item["x"] - item["r"] and item["x"] + item["r"] <= x1, item["id"]
            assert y0 <= item["y"] - item["r"] and item["y"] + item["r"] <= y1, item["id"]
        else:
            assert x0 <= item["x"] and item["x"] + item["w"] <= x1, item["id"]
            assert y0 <= item["y"] and item["y"] + item["h"] <= y1, item["id"]


def test_the_cafe_the_merchandise_shop_and_the_print_corner_are_places_with_three_printers():
    areas = {area["id"] for area in world.INTERIORS["campus"]["areas"]}
    assert {"cafe", "merch", "print", "atrium"} <= areas
    printers = [item for item in world.INTERIORS["campus"]["solid"] if item["id"].startswith("printer")]
    assert len(printers) == 3
    print_corner = next(area for area in world.INTERIORS["campus"]["areas"] if area["id"] == "print")
    assert all(inside(print_corner, p["x"] + p["w"] / 2, p["y"] + p["h"] / 2) for p in printers)


def test_the_three_desks_stand_in_the_atrium_and_keep_their_ids_and_actions():
    actions = {loc_id: loc["action"] for loc_id, loc in world.LOCATIONS.items()}
    assert actions == {"supplier": "stock", "stand": "prices", "board": "dashboard"}
    atrium = next(area for area in world.INTERIORS["campus"]["areas"] if area["id"] == "atrium")
    cafe = next(area for area in world.INTERIORS["campus"]["areas"] if area["id"] == "cafe")
    solid = world.colliders("campus")
    for loc_id, loc in world.LOCATIONS.items():
        assert inside(atrium if loc_id != "stand" else cafe, loc["x"], loc["y"]), loc_id
        assert not is_blocked(loc["x"], loc["y"], solid), loc_id


def test_the_places_split_the_whole_floor_between_them():
    # spec nova-wings: the floor of each wing instead of one box around the whole building
    all_areas = world.INTERIORS["campus"]["areas"]
    for wing, (x0, y0, x1, y1) in wing_floors().items():
        areas = [a for a in all_areas if a["wing"] == wing]
        assert areas, wing
        for area in areas:
            assert x0 <= area["x"] and area["x"] + area["w"] <= x1 + 1e-9, area["id"]
            assert y0 <= area["y"] and area["y"] + area["h"] <= y1 + 1e-9, area["id"]
        assert sum(a["w"] * a["h"] for a in areas) == pytest.approx((x1 - x0) * (y1 - y0)), wing
        for index, a in enumerate(areas):
            for b in areas[index + 1:]:
                apart = (
                    a["x"] + a["w"] <= b["x"] + 1e-9 or b["x"] + b["w"] <= a["x"] + 1e-9
                    or a["y"] + a["h"] <= b["y"] + 1e-9 or b["y"] + b["h"] <= a["y"] + 1e-9
                )
                assert apart, (a["id"], b["id"])
        for area in areas:  # the name on the floor lies inside its own place
            assert inside(area, area["labelAt"]["x"], area["labelAt"]["y"]), area["id"]


def test_the_people_in_the_rooms_stand_on_free_ground_or_behind_a_counter():
    x0, y0, x1, y1 = floor()
    solid = world.colliders("campus")
    for person in world.INTERIORS["campus"]["activities"]:
        assert x0 <= person["x"] <= x1 and y0 <= person["y"] <= y1, person["label"]
        if person.get("role") != "service":  # staff stand in the shut lane behind their counter
            assert not is_blocked(person["x"], person["y"], solid), person["label"]


def test_the_rooms_have_no_dead_corners_for_a_player_to_get_stuck_in():
    """Every spot inside that a player can stand on can be walked to from a way in. Spec nova-wings:
    for the floor of each wing, from the entrances and the openings that lead into it."""
    solid = world.colliders("campus")
    step = 0.2
    wall = world.NOVA["wall"]
    for wing, (x0, y0, x1, y1) in wing_floors().items():
        columns = int((x1 - x0) / step) + 1
        rows = int((y1 - y0) / step) + 1
        free = {
            (c, r)
            for c in range(columns)
            for r in range(rows)
            if not is_blocked(x0 + c * step, y0 + r * step, solid)
        }
        starts = set()
        for gap in gaps():
            if gap["side"] in ("south", "north"):
                centre = (gap["x"] + gap["width"] / 2, gap["y"] + wall / 2)
                probes = [(centre[0], centre[1] - wall / 2 - 0.4), (centre[0], centre[1] + wall / 2 + 0.4)]
            else:
                centre = (gap["x"] + wall / 2, gap["y"] + gap["width"] / 2)
                probes = [(centre[0] - wall / 2 - 0.4, centre[1]), (centre[0] + wall / 2 + 0.4, centre[1])]
            for px, py in probes:
                if x0 <= px <= x1 and y0 <= py <= y1:
                    starts.add((round((px - x0) / step), round((py - y0) / step)))
        assert starts, f"{wing} has no way in"
        assert starts & free, wing
        seen = set(starts & free)
        todo = deque(seen)
        while todo:
            c, r = todo.popleft()
            for n in ((c + 1, r), (c - 1, r), (c, r + 1), (c, r - 1)):
                if n in free and n not in seen:
                    seen.add(n)
                    todo.append(n)
        cut_off = sorted(free - seen)
        assert not cut_off, (wing, [(round(x0 + c * step, 1), round(y0 + r * step, 1)) for c, r in cut_off[:5]])
        assert len(free) / (columns * rows) > 0.4, wing  # most of the floor is open to walk on


def test_clicking_to_walk_finds_a_way_to_every_spot_a_player_can_stand_on():
    """The same grid as static/world/paths.js (half tiles, the radius plus 0.02): every free spot
    inside has a grid point next to it that is connected to the spawn. A gap that is wide enough
    for the player but too narrow for the grid would make a click there do nothing."""
    zone = world.ZONES["campus"]
    solid = world.colliders("campus")
    step = 0.5
    clearance = RADIUS + 0.02
    columns = int((zone["maxX"] - zone["minX"]) / step) + 1
    rows = int((zone["maxY"] - zone["minY"]) / step) + 1
    node_free = {
        (c, r)
        for c in range(columns)
        for r in range(rows)
        if not is_blocked(zone["minX"] + c * step, zone["minY"] + r * step, solid, clearance)
    }

    def nearest_node(x, y):
        c0 = round((x - zone["minX"]) / step)
        r0 = round((y - zone["minY"]) / step)
        for ring in range(9):
            best, best_distance = None, math.inf
            for r in range(r0 - ring, r0 + ring + 1):
                for c in range(c0 - ring, c0 + ring + 1):
                    if (c, r) in node_free:
                        distance = math.hypot(zone["minX"] + c * step - x, zone["minY"] + r * step - y)
                        if distance < best_distance:
                            best, best_distance = (c, r), distance
            if best:
                return best
        return None

    start = nearest_node(zone["spawn"]["x"], zone["spawn"]["y"])
    seen = {start}
    todo = deque([start])
    while todo:
        c, r = todo.popleft()
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                n = (c + dc, r + dr)
                if (dr or dc) and n in node_free and n not in seen:
                    if dr and dc and ((c + dc, r) not in node_free or (c, r + dr) not in node_free):
                        continue  # no cutting the corner of a solid object
                    seen.add(n)
                    todo.append(n)
    x0, y0, x1, y1 = floor()
    lost = []
    x = x0
    while x <= x1:
        y = y0
        while y <= y1:
            if not is_blocked(x, y, solid) and nearest_node(x, y) not in seen:
                lost.append((round(x, 1), round(y, 1)))
            y += 0.1
        x += 0.1
    assert not lost, lost[:5]
    for loc_id, loc in world.LOCATIONS.items():
        assert nearest_node(loc["x"], loc["y"]) in seen, loc_id


# ---- Check 3: a player can walk to every desk, and only through the entrance --

def reachable_desks(extra=()):
    """Walk from the spawn over a grid with a real-sized player; which desks come within reach?"""
    zone = world.ZONES["campus"]
    solid = world.colliders("campus") + list(extra)
    step = 0.3
    columns = int((zone["maxX"] - zone["minX"]) / step) + 1
    rows = int((zone["maxY"] - zone["minY"]) / step) + 1
    point = lambda c, r: (zone["minX"] + c * step, zone["minY"] + r * step)  # noqa: E731
    free = {}

    def ok(c, r):
        if (c, r) not in free:
            free[(c, r)] = 0 <= c < columns and 0 <= r < rows and not is_blocked(*point(c, r), solid)
        return free[(c, r)]

    start = (round((zone["spawn"]["x"] - zone["minX"]) / step), round((zone["spawn"]["y"] - zone["minY"]) / step))
    assert ok(*start)
    seen = {start}
    todo = deque([start])
    while todo:
        c, r = todo.popleft()
        for nc, nr in ((c + 1, r), (c - 1, r), (c, r + 1), (c, r - 1)):
            if (nc, nr) not in seen and ok(nc, nr):
                seen.add((nc, nr))
                todo.append((nc, nr))
    return {
        loc_id
        for loc_id, loc in world.LOCATIONS.items()
        if any(math.hypot(point(c, r)[0] - loc["x"], point(c, r)[1] - loc["y"]) < REACH for c, r in seen)
    }


def test_every_desk_can_be_reached_on_foot_from_the_spawn():
    assert reachable_desks() == set(world.LOCATIONS)


def test_the_desks_can_only_be_reached_through_the_entrance():
    plug = [
        {"id": "plug", "shape": "rect", "x": e["x"], "y": e["y"] - 0.2, "width": e["width"], "height": 1.0,
         "label": "x", "kind": "wall"}
        for e in world.NOVA["entrances"]
    ]
    assert reachable_desks(plug) == set()


# ---- Check 4: the position stays only a position -----------------------------

def test_a_position_inside_the_nova_is_saved_and_survives_a_restart(tmp_path):
    path = tmp_path / "run.db"
    loc = world.LOCATIONS["board"]
    state = logic.move_player(logic.new_state(), "campus", loc["x"], loc["y"])
    db.save(state, path)
    assert db.load(path)["player"] == {"zone": "campus", "x": loc["x"], "y": loc["y"]}


@pytest.mark.parametrize("old_zone", ["mercado", "academy", "hub"])
def test_a_save_in_a_removed_room_starts_at_the_spawn(tmp_path, old_zone):
    path = tmp_path / "run.db"
    db.save(logic.new_state(), path)
    with db.connect(path) as conn:
        conn.execute("UPDATE player SET zone = ?", (old_zone,))
    assert db.load(path)["player"] == world.start_player()


def test_a_removed_zone_is_refused_when_the_browser_sends_it():
    state = logic.new_state()
    with pytest.raises(logic.RejectedAction):
        logic.move_player(state, "hub", 7.5, 8.8)


# ---- Check 5: the roof and the way in, with the real browser modules ---------

ROOF_CHECK = """
import { readFileSync } from "node:fs";
import { ROOF_SECONDS, areaAt, insideParts, stepRoof } from "./roofs.js";

const world = JSON.parse(readFileSync(process.argv[2]));
const parts = world.nova.parts;
const areas = world.interiors.campus.areas;
const door = world.nova.entrances[0];
const middle = door.x + door.width / 2;
const problems = [];
const expect = (ok, text) => { if (!ok) problems.push(text); };

expect(insideParts({ x: 21, y: 5 }, parts), "the middle of the atrium is inside");
expect(!insideParts({ x: 21, y: 11.2 }, parts), "the plaza in front is outside");
expect(!insideParts({ x: 1.5, y: 5 }, parts), "the ground west of the building is outside");
expect(!insideParts({ x: 21, y: door.y + 0.5 + 0.2 }, parts), "just in front of the wall line is outside");
expect(insideParts({ x: middle, y: door.y + 0.1 }, parts), "the doorway counts as inside");

// the seams between the joined parts are no edge: the roof must not flicker there
const novaParts = parts.filter((part) => part.wing === "nova");
for (let i = 1; i < novaParts.length; i++) {
  const seam = novaParts[i].x;
  for (const y of [4, 5, 6, 7]) expect(insideParts({ x: seam, y }, parts), `the seam at ${seam},${y} is inside`);
}

// fading in: steady, never back, ends exactly on the target, takes about ROOF_SECONDS
let opacity = 1;
let frames = 0;
while (opacity > 0 && frames < 1000) {
  const next = stepRoof(opacity, true, 1 / 60);
  expect(next <= opacity, "going inside never makes the roof thicker");
  opacity = next;
  frames++;
}
expect(opacity === 0, "the roof ends exactly at 0 inside");
expect(Math.abs(frames / 60 - ROOF_SECONDS) < 0.05, `the fade takes about ${ROOF_SECONDS}s (took ${frames / 60}s)`);
frames = 0;
while (opacity < 1 && frames < 1000) {
  const next = stepRoof(opacity, false, 1 / 60);
  expect(next >= opacity, "going outside never makes the roof thinner");
  opacity = next;
  frames++;
}
expect(opacity === 1, "the roof ends exactly at 1 outside");
expect(stepRoof(0.5, true, 0) === 0.5, "no time, no change");
expect(stepRoof(0.2, true, 10) === 0 && stepRoof(0.8, false, 10) === 1, "a long frame never overshoots");
expect(stepRoof(1, true, 1 / 60, true) === 0 && stepRoof(0, false, 1 / 60, true) === 1, "reduced motion jumps");

// the names of the places
expect(areaAt({ x: 14, y: 5 }, areas)?.id === "cafe", "the cafe area");
expect(areaAt({ x: 21, y: 5 }, areas)?.id === "atrium", "the atrium area");
expect(areaAt({ x: 30, y: 3 }, areas)?.id === "merch", "the merchandise area");
expect(areaAt({ x: 30, y: 7 }, areas)?.id === "print", "the print corner");
expect(areaAt({ x: 21, y: 12 }, areas) === null, "no area outside");

console.log(JSON.stringify({ problems }));
"""

WALK_CHECK = """
import { readFileSync } from "node:fs";
import { findPath } from "./paths.js";
import { nearestFreePoint, pointBlocked } from "./physics.js";

const RADIUS = 0.28;
const REACH = 1.65;
const world = JSON.parse(readFileSync(process.argv[2]));
const zone = world.zones.campus;
const solid = world.colliders.campus;
const entrances = world.nova.entrances;
const wall = world.nova.wall;
const problems = [];
let checked = 0;
let throughDoor = 0;
const starts = [zone.spawn];
for (let i = 0; i < 60; i++) {
  starts.push({
    x: zone.minX + 0.3 + (zone.maxX - zone.minX - 0.6) * ((i * 0.6180339) % 1),
    y: zone.minY + 0.3 + (zone.maxY - zone.minY - 0.6) * ((i * 0.7548776) % 1),
  });
}
for (let x = 12.4; x < 32.7; x += 0.9) {
  for (let y = 2.0; y < 8.5; y += 0.7) starts.push({ x, y }); // all over the inside as well
}
const underRoof = (p) => world.nova.parts.some((part) => p.x > part.x && p.x < part.x + part.w && p.y > part.y && p.y < part.y + part.h);
for (const start of starts.filter((p) => !pointBlocked(p, solid, RADIUS))) {
  for (const loc of Object.values(world.locations)) {
    checked++;
    const goal = nearestFreePoint({ x: loc.x, y: loc.y }, zone, solid, RADIUS);
    const path = findPath(start, goal, zone, solid, RADIUS);
    if (!path) {
      problems.push(`no way to ${loc.title}`);
      continue;
    }
    const end = path[path.length - 1];
    if (Math.hypot(end.x - loc.x, end.y - loc.y) >= REACH) problems.push(`${loc.title} out of reach`);
    let from = start;
    let crossedDoor = false;
    path.forEach((to) => {
      const steps = Math.ceil(Math.hypot(to.x - from.x, to.y - from.y) / 0.05);
      for (let i = 1; i <= steps; i++) {
        const p = { x: from.x + ((to.x - from.x) * i) / steps, y: from.y + ((to.y - from.y) * i) / steps };
        if (pointBlocked(p, solid, RADIUS - 0.01)) problems.push(`walks through something near ${loc.title}`);
        if (entrances.some((door) => p.y > door.y && p.y < door.y + wall && p.x > door.x && p.x < door.x + door.width)) crossedDoor = true;
      }
      from = to;
    });
    if (!underRoof(start)) {
      // from outside, the only way in leads through the entrance
      if (crossedDoor) throughDoor++;
      else problems.push(`${loc.title} was reached from outside without using the entrance`);
    }
  }
}
console.log(JSON.stringify({ checked, throughDoor, problems: [...new Set(problems)] }));
"""


def run_node(tmp_path, script, modules):
    for name in modules:
        shutil.copy(WORLD / name, tmp_path)
    (tmp_path / "package.json").write_text('{"type": "module"}')
    (tmp_path / "check.js").write_text(script)
    (tmp_path / "world.json").write_text(json.dumps(world.world_view()))
    done = subprocess.run([NODE, "check.js", "world.json"], cwd=tmp_path, capture_output=True, text=True, timeout=60)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


@needs_node
def test_the_roof_fades_with_the_real_roofs_module(tmp_path):
    assert run_node(tmp_path, ROOF_CHECK, ["roofs.js"])["problems"] == []


@needs_node
def test_every_desk_is_reached_on_foot_from_outside_through_the_entrance(tmp_path):
    result = run_node(tmp_path, WALK_CHECK, ["paths.js", "physics.js"])
    assert result["checked"] > 300
    assert result["throughDoor"] > 20
    assert result["problems"] == []
