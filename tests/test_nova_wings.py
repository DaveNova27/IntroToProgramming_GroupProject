"""Checks from specs/nova-wings.md ("Done when"). One test per check.

The checks on the data and on walking run in Python. The checks on the roofs and on walking
with the real browser modules run with Node, as in test_walk_in.py: GitHub Actions has Node;
on a computer without it they are skipped and everything else still runs.

Some checks of test_walk_in.py look at the Nova as one rectangle with one entrance. They are
not edited (see the spec, "Decide" 4): the checks here do the same work for every wing.
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
WINGS = ["nova", "learning-center", "mercado", "hub"]


# ---- helpers -----------------------------------------------------------------------

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


def areas_of(wing):
    return [a for a in world.INTERIORS["campus"]["areas"] if a["wing"] == wing]


def floor_of(wing):
    """The floor of a wing: the box around its areas (a test below checks that they fill it)."""
    areas = areas_of(wing)
    x0 = min(a["x"] for a in areas)
    y0 = min(a["y"] for a in areas)
    x1 = max(a["x"] + a["w"] for a in areas)
    y1 = max(a["y"] + a["h"] for a in areas)
    return x0, y0, x1, y1


def on_floor(x, y, wing, margin=0.0):
    x0, y0, x1, y1 = floor_of(wing)
    return x0 - margin <= x <= x1 + margin and y0 - margin <= y <= y1 + margin


def covers(rect, x, y):
    return rect["x"] <= x <= rect["x"] + rect["w"] and rect["y"] <= y <= rect["y"] + rect["h"]


def gap_rect(opening):
    """The rectangle a wall would fill if the opening were not there."""
    wall = world.NOVA["wall"]
    if opening["side"] in ("north", "south"):
        return opening["x"], opening["y"], opening["x"] + opening["width"], opening["y"] + wall
    return opening["x"], opening["y"], opening["x"] + wall, opening["y"] + opening["width"]


def centre_line(opening):
    """Three points across the wall in the middle of the gap: before it, in it, behind it."""
    wall = world.NOVA["wall"]
    x0, y0, x1, y1 = gap_rect(opening)
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    if opening["side"] in ("north", "south"):
        return [(mx, y0 - 0.6), (mx, y0 + 0.25), (mx, y0 + wall + 0.6)]
    return [(x0 - 0.6, my), (x0 + 0.25, my), (x0 + wall + 0.6, my)]


def all_gaps():
    return list(world.NOVA["entrances"]) + list(world.NOVA["openings"])


def solid_rects():
    return world.colliders("campus")


# ---- Check 2: four wings, and everything belongs to one of them --------------------

def test_the_nova_has_four_wings_with_the_data_the_browser_needs():
    wings = world.NOVA["wings"]
    assert [w["id"] for w in wings] == WINGS
    for wing in wings:
        assert wing["label"]
        assert set(wing["fadesWith"]) <= set(WINGS) - {wing["id"]}


def test_every_part_wall_area_solid_and_person_belongs_to_a_wing():
    interiors = world.INTERIORS["campus"]
    groups = [world.NOVA["parts"], world.NOVA["walls"], world.NOVA["entrances"], interiors["areas"],
              interiors["solid"], interiors["activities"]]
    for group in groups:
        for entry in group:
            assert entry["wing"] in WINGS, entry
    for wing in WINGS:
        assert any(p["wing"] == wing for p in world.NOVA["parts"]), wing
        assert any(w["wing"] == wing for w in world.NOVA["walls"]), wing
    for wall in world.NOVA["walls"]:
        assert set(wall.get("hides", [])) <= set(WINGS)
        assert wall["side"] in ("north", "south", "east", "west")


def test_the_flat_lists_stay_so_the_code_of_walk_in_keeps_reading_them():
    data = app.app.test_client().get("/api/world").get_json()
    assert data["nova"]["parts"] and data["nova"]["walls"] and data["nova"]["entrances"]
    assert data["nova"]["wings"] and data["nova"]["openings"]
    assert "buildings" not in data  # the Learning Center and the Mercado are wings now


def test_the_wings_are_joined_into_one_footprint():
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


# ---- Check 2: entrances and openings -------------------------------------------------

def test_the_two_new_entrances_are_on_the_south_side_and_wide_enough():
    entrances = world.NOVA["entrances"]
    assert {e["wing"] for e in entrances} == {"nova", "mercado", "hub"}
    for entrance in entrances:
        assert entrance["side"] == "south"
        assert entrance["width"] >= 2
    assert not any(e["wing"] == "learning-center" for e in entrances)


def test_the_openings_join_two_wings_and_are_wide_enough():
    openings = world.NOVA["openings"]
    assert {frozenset(o["between"]) for o in openings} == {
        frozenset({"nova", "learning-center"}),
        frozenset({"learning-center", "mercado"}),
        frozenset({"nova", "hub"}),
    }
    for opening in openings:
        assert opening["width"] >= 2
        # one step in front of the wall is on the floor of one wing, one step behind it on the other
        before, _, after = centre_line(opening)
        for wing, spot in zip(opening["between"], (before, after)):
            assert on_floor(*spot, wing) or on_floor(*(after if spot is before else before), wing), (opening["id"], wing)
        assert {w for w in opening["between"] if on_floor(*before, w) or on_floor(*after, w)} == set(opening["between"])


def test_no_wall_or_solid_covers_an_opening_or_an_entrance():
    solid = solid_rects()
    for gap in all_gaps():
        x0, y0, x1, y1 = gap_rect(gap)
        for item in solid:
            if item["kind"] == "boundary":
                continue
            if item["shape"] == "circle":
                ix = min(max(item["x"], x0), x1)
                iy = min(max(item["y"], y0), y1)
                overlaps = math.hypot(item["x"] - ix, item["y"] - iy) < item["radius"]
            else:
                overlaps = (
                    item["x"] < x1 and x0 < item["x"] + item["width"]
                    and item["y"] < y1 and y0 < item["y"] + item["height"]
                )
            assert not overlaps, (gap["id"], item["id"])


def test_a_player_of_the_real_size_passes_through_every_opening_and_entrance():
    solid = solid_rects()
    for gap in all_gaps():
        for x, y in centre_line(gap):
            assert not is_blocked(x, y, solid), (gap["id"], x, y)


def test_the_walls_only_meet_at_their_corners():
    walls = world.NOVA["walls"]
    corner = world.NOVA["wall"] ** 2
    for index, a in enumerate(walls):
        for b in walls[index + 1:]:
            overlap_x = min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"])
            overlap_y = min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"])
            if overlap_x > 0.01 and overlap_y > 0.01:
                assert overlap_x * overlap_y <= corner + 1e-9, (a["id"], b["id"])


# ---- Check 2: the rooms of each wing --------------------------------------------------

def test_the_places_of_each_wing_split_its_floor_between_them():
    for wing in WINGS:
        areas = areas_of(wing)
        x0, y0, x1, y1 = floor_of(wing)
        assert sum(a["w"] * a["h"] for a in areas) == pytest.approx((x1 - x0) * (y1 - y0)), wing
        for index, a in enumerate(areas):
            for b in areas[index + 1:]:
                apart = (
                    a["x"] + a["w"] <= b["x"] + 1e-9 or b["x"] + b["w"] <= a["x"] + 1e-9
                    or a["y"] + a["h"] <= b["y"] + 1e-9 or b["y"] + b["h"] <= a["y"] + 1e-9
                )
                assert apart, (a["id"], b["id"])
        for a in areas:
            assert covers(a, a["labelAt"]["x"], a["labelAt"]["y"]), a["id"]
    ids = [a["id"] for a in world.INTERIORS["campus"]["areas"]]
    assert len(ids) == len(set(ids))


def test_the_floor_of_a_wing_lies_inside_its_walls():
    wall_rects = [(w["x"], w["y"], w["x"] + w["w"], w["y"] + w["h"]) for w in world.NOVA["walls"]]
    for wing in WINGS:
        x0, y0, x1, y1 = floor_of(wing)
        parts = [p for p in world.NOVA["parts"] if p["wing"] == wing]
        assert min(p["x"] for p in parts) <= x0 and x1 <= max(p["x"] + p["w"] for p in parts), wing
        assert min(p["y"] for p in parts) <= y0 and y1 <= max(p["y"] + p["h"] for p in parts), wing
        for wx0, wy0, wx1, wy1 in wall_rects:
            # a wall may touch the floor, but never lie on it
            assert not (wx0 < x1 - 1e-9 and x0 + 1e-9 < wx1 and wy0 < y1 - 1e-9 and y0 + 1e-9 < wy1), (wing, wx0, wy0)


def test_every_solid_stands_on_the_floor_of_its_own_wing():
    for item in world.INTERIORS["campus"]["solid"]:
        wing = item["wing"]
        x0, y0, x1, y1 = floor_of(wing)
        if "r" in item:
            assert x0 <= item["x"] - item["r"] and item["x"] + item["r"] <= x1 + 1e-9, item["id"]
            assert y0 <= item["y"] - item["r"] and item["y"] + item["r"] <= y1 + 1e-9, item["id"]
        else:
            assert x0 <= item["x"] and item["x"] + item["w"] <= x1 + 1e-9, item["id"]
            assert y0 <= item["y"] and item["y"] + item["h"] <= y1 + 1e-9, item["id"]


def test_every_new_wing_has_its_own_floor_props_and_people():
    solid = world.INTERIORS["campus"]["solid"]
    people = world.INTERIORS["campus"]["activities"]
    for wing in ("learning-center", "mercado", "hub"):
        assert areas_of(wing), wing
        assert len([s for s in solid if s["wing"] == wing]) >= 4, wing
        assert len([p for p in people if p["wing"] == wing]) >= 2, wing


def test_the_people_stand_on_the_floor_of_their_wing_on_free_ground_or_behind_a_counter():
    solid = solid_rects()
    for person in world.INTERIORS["campus"]["activities"]:
        assert on_floor(person["x"], person["y"], person["wing"]), person["label"]
        if person.get("role") != "service":
            assert not is_blocked(person["x"], person["y"], solid), (person["wing"], person["label"], person["x"], person["y"])


def test_the_three_desks_keep_their_ids_actions_and_places():
    assert {i: (l["action"], l["x"], l["y"]) for i, l in world.LOCATIONS.items()} == {
        "supplier": ("stock", 20.7, 4.1), "stand": ("prices", 15.4, 4.4), "board": ("dashboard", 23.7, 4.1),
    }
    for loc in world.LOCATIONS.values():
        assert on_floor(loc["x"], loc["y"], "nova")


# ---- Check 3: a player can walk everywhere and click to walk everywhere --------------

def floors():
    return [floor_of(wing) for wing in WINGS]


def test_the_rooms_of_every_wing_have_no_dead_corners_for_a_player_to_get_stuck_in():
    """Every spot a player can stand on in any wing can be walked to from the spawn."""
    zone = world.ZONES["campus"]
    solid = solid_rects()
    step = 0.2
    columns = int((zone["maxX"] - zone["minX"]) / step) + 1
    rows = int((zone["maxY"] - zone["minY"]) / step) + 1
    point = lambda c, r: (zone["minX"] + c * step, zone["minY"] + r * step)  # noqa: E731
    cache = {}

    def free(c, r):
        if (c, r) not in cache:
            cache[(c, r)] = 0 <= c < columns and 0 <= r < rows and not is_blocked(*point(c, r), solid)
        return cache[(c, r)]

    start = (round((zone["spawn"]["x"] - zone["minX"]) / step), round((zone["spawn"]["y"] - zone["minY"]) / step))
    assert free(*start)
    seen = {start}
    todo = deque([start])
    while todo:
        c, r = todo.popleft()
        for n in ((c + 1, r), (c - 1, r), (c, r + 1), (c, r - 1)):
            if n not in seen and free(*n):
                seen.add(n)
                todo.append(n)
    for wing in WINGS:
        x0, y0, x1, y1 = floor_of(wing)
        lost = set()
        total = 0
        for c in range(columns):
            for r in range(rows):
                x, y = point(c, r)
                if x0 <= x <= x1 and y0 <= y <= y1 and free(c, r):
                    total += 1
                    if (c, r) not in seen:
                        lost.add((c, r))
        # a sliver behind two counters (smaller than a person) is no place to stand; a real pocket is
        while lost:
            cell = lost.pop()
            pocket = {cell}
            todo = deque([cell])
            while todo:
                c, r = todo.popleft()
                for n in ((c + 1, r), (c - 1, r), (c, r + 1), (c, r - 1)):
                    if n in lost:
                        lost.discard(n)
                        pocket.add(n)
                        todo.append(n)
            assert len(pocket) <= 4, (wing, sorted((round(point(*cell)[0], 1), round(point(*cell)[1], 1)) for cell in pocket)[:5])
        assert total / (((x1 - x0) / step) * ((y1 - y0) / step)) > 0.35, wing  # most of the floor is open


def test_clicking_to_walk_finds_a_way_to_every_spot_in_every_wing():
    """The same grid as static/world/paths.js (half tiles, the radius plus 0.02): every free spot
    inside any wing has a grid point next to it that is connected to the spawn. A gap that is wide
    enough for the player but too narrow for the grid would make a click there do nothing."""
    zone = world.ZONES["campus"]
    solid = solid_rects()
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
    for wing in WINGS:
        x0, y0, x1, y1 = floor_of(wing)
        lost = []
        x = x0
        while x <= x1:
            y = y0
            while y <= y1:
                if not is_blocked(x, y, solid) and nearest_node(x, y) not in seen:
                    lost.append((round(x, 1), round(y, 1)))
                y += 0.1
            x += 0.1
        assert not lost, (wing, lost[:5])
    for loc_id, loc in world.LOCATIONS.items():
        assert nearest_node(loc["x"], loc["y"]) in seen, loc_id


def reachable_wings(plugs=()):
    """Walk from the spawn over a grid with a real-sized player; which wings can be entered?"""
    zone = world.ZONES["campus"]
    solid = solid_rects() + list(plugs)
    step = 0.3
    columns = int((zone["maxX"] - zone["minX"]) / step) + 1
    rows = int((zone["maxY"] - zone["minY"]) / step) + 1
    point = lambda c, r: (zone["minX"] + c * step, zone["minY"] + r * step)  # noqa: E731
    cache = {}

    def ok(c, r):
        if (c, r) not in cache:
            cache[(c, r)] = 0 <= c < columns and 0 <= r < rows and not is_blocked(*point(c, r), solid)
        return cache[(c, r)]

    start = (round((zone["spawn"]["x"] - zone["minX"]) / step), round((zone["spawn"]["y"] - zone["minY"]) / step))
    seen = {start}
    todo = deque([start])
    while todo:
        c, r = todo.popleft()
        for n in ((c + 1, r), (c - 1, r), (c, r + 1), (c, r - 1)):
            if n not in seen and ok(*n):
                seen.add(n)
                todo.append(n)
    reached = {wing for wing in WINGS if any(on_floor(*point(c, r), wing) for c, r in seen)}
    desks = {
        loc_id for loc_id, loc in world.LOCATIONS.items()
        if any(math.hypot(point(c, r)[0] - loc["x"], point(c, r)[1] - loc["y"]) < REACH for c, r in seen)
    }
    return reached, desks


def plug(gap):
    x0, y0, x1, y1 = gap_rect(gap)
    return {"id": f"plug-{gap['id']}", "shape": "rect", "x": x0 - 0.2, "y": y0 - 0.2, "width": x1 - x0 + 0.4,
            "height": y1 - y0 + 0.4, "label": "x", "kind": "wall"}


def test_every_wing_and_every_desk_can_be_reached_on_foot_from_the_spawn():
    reached, desks = reachable_wings()
    assert reached == set(WINGS)
    assert desks == set(world.LOCATIONS)


def test_the_wings_can_only_be_entered_through_the_entrances_and_openings():
    outside = [plug(e) for e in world.NOVA["entrances"]]
    reached, desks = reachable_wings(outside)
    assert reached == set() and desks == set()
    # with only the Mercado entrance open, the Learning Center and the Nova are reached through it
    only_mercado = [plug(e) for e in world.NOVA["entrances"] if e["id"] != "mercado"]
    reached, desks = reachable_wings(only_mercado)
    assert reached == set(WINGS) and desks == set(world.LOCATIONS)
    # with only the Hub entrance open, the Hub and the Nova behind it are reached, the others are not
    only_hub = [plug(e) for e in world.NOVA["entrances"] if e["id"] != "hub"]
    reached, _ = reachable_wings(only_hub)
    assert reached == set(WINGS)
    # shut the openings as well: a wing is then only reached through its own entrance
    openings = [plug(o) for o in world.NOVA["openings"]]
    reached, _ = reachable_wings(openings)
    assert reached == {"nova", "mercado", "hub"}
    reached, _ = reachable_wings(openings + [plug(e) for e in world.NOVA["entrances"] if e["id"] != "main"])
    assert reached == {"nova"}


# ---- Check 6: a position in any wing is only a position -----------------------------------

@pytest.mark.parametrize("wing", WINGS)
def test_a_position_in_any_wing_is_saved_and_survives_a_restart(tmp_path, wing):
    x0, y0, x1, y1 = floor_of(wing)
    solid = solid_rects()
    spot = next(
        (x0 + (x1 - x0) * fx, y0 + (y1 - y0) * fy)
        for fy in (0.5, 0.3, 0.7, 0.9, 0.1) for fx in (0.5, 0.3, 0.7, 0.9, 0.1)
        if not is_blocked(x0 + (x1 - x0) * fx, y0 + (y1 - y0) * fy, solid)
    )
    path = tmp_path / "run.db"
    state = logic.move_player(logic.new_state(), "campus", spot[0], spot[1])
    db.save(state, path)
    loaded = db.load(path)
    assert loaded["player"] == {"zone": "campus", "x": pytest.approx(spot[0], abs=0.01), "y": pytest.approx(spot[1], abs=0.01)}


def test_the_bounds_of_the_zone_hold_every_wing():
    zone = world.ZONES["campus"]
    for part in world.NOVA["parts"]:
        assert zone["minX"] <= part["x"] and part["x"] + part["w"] <= zone["maxX"]
        assert zone["minY"] <= part["y"] and part["y"] + part["h"] <= zone["maxY"]
    for x, y in ((3.0, 4.0), (30.0, 13.0)):  # a spot in the Learning Center and one in the Hub
        logic.move_player(logic.new_state(), "campus", x, y)
    with pytest.raises(logic.RejectedAction):
        logic.move_player(logic.new_state(), "campus", 4.0, float("nan"))
    with pytest.raises(logic.RejectedAction):
        logic.move_player(logic.new_state(), "campus", 90.0, 4.0)


# ---- Check 4 and 5: the roofs and the way in, with the real browser modules ------------------

ROOF_CHECK = """
import { readFileSync } from "node:fs";
import { ROOF_SECONDS, areaAt, roofGoesOut, stepRoof, stepRoofs, wingsAt } from "./roofs.js";

const world = JSON.parse(readFileSync(process.argv[2]));
const { parts, wings, entrances, openings, wall } = world.nova;
const areas = world.interiors.campus.areas;
const problems = [];
const expect = (ok, text) => { if (!ok) problems.push(text); };
const names = (list) => [...list].sort().join(",");
const open = (inside) => wings.filter((wing) => roofGoesOut(wing.id, wings, inside)).map((wing) => wing.id);

// in the middle of a wing the player is in that wing only, and its roof goes out
const middleOf = (id) => {
  const own = areas.filter((area) => area.wing === id);
  const x0 = Math.min(...own.map((a) => a.x)), x1 = Math.max(...own.map((a) => a.x + a.w));
  const y0 = Math.min(...own.map((a) => a.y)), y1 = Math.max(...own.map((a) => a.y + a.h));
  return { x: (x0 + x1) / 2, y: (y0 + y1) / 2 };
};
for (const wing of wings) {
  const inside = wingsAt(middleOf(wing.id), parts);
  expect(names(inside) === wing.id, `the middle of ${wing.id} is in ${wing.id} only (got ${inside})`);
  const goingOut = open(inside);
  expect(goingOut.includes(wing.id), `the roof of ${wing.id} goes out when the player is in it`);
  for (const other of wings) {
    const behind = other.fadesWith.includes(wing.id);
    expect(goingOut.includes(other.id) === (other.id === wing.id || behind), `in ${wing.id}, the roof of ${other.id} ${behind ? "goes out too" : "stays"}`);
  }
}
// the roofs that stay: in the Learning Center the Hub stays closed, in the Hub only the Hub opens
expect(names(open(["learning-center"])) === "learning-center,mercado,nova", "in the Learning Center: it, the Mercado and the Nova");
expect(names(open(["mercado"])) === "mercado", "in the Mercado only the Mercado opens");
expect(names(open(["hub"])) === "hub", "in the Hub only the Hub opens");
expect(names(open(["nova"])) === "hub,nova", "in the Nova: it and the Hub, which stands in front of it");

// outside, and the doorways
expect(!wingsAt({ x: 21, y: 11.2 }, parts).length, "the plaza in front is outside");
expect(!wingsAt({ x: 5, y: 2 }, parts).length, "the ground north of the Learning Center is outside");
expect(!wingsAt({ x: 20, y: 12.5 }, parts).length, "the courtyard between the fingers is outside");
for (const door of entrances) {
  const x = door.x + door.width / 2;
  expect(!wingsAt({ x, y: door.y + wall + 0.6 }, parts).length, `in front of the ${door.id} entrance is outside`);
  expect(names(wingsAt({ x, y: door.y + 0.1 }, parts)) === door.wing, `the ${door.id} doorway counts as inside ${door.wing}`);
}
for (const gap of openings) {
  const point = gap.side === "south" || gap.side === "north"
    ? { x: gap.x + gap.width / 2, y: gap.y + wall / 2 }
    : { x: gap.x + wall / 2, y: gap.y + gap.width / 2 };
  expect(names(wingsAt(point, parts)) === names(gap.between), `the opening ${gap.id} is in both of its wings (got ${wingsAt(point, parts)})`);
}

// a walk in a straight line through every entrance and opening: the player is never outside once in,
// and no roof flickers (a roof changes its mind at most twice: out, then back in)
const lines = [];
for (const door of entrances) {
  const x = door.x + door.width / 2;
  lines.push([{ x, y: door.y + 3.5 }, { x, y: door.y - 3.5 }, door.id]);
}
for (const gap of openings) {
  if (gap.side === "south" || gap.side === "north") {
    const x = gap.x + gap.width / 2;
    lines.push([{ x, y: gap.y - 2 }, { x, y: gap.y + wall + 2 }, gap.id], [{ x, y: gap.y + wall + 2 }, { x, y: gap.y - 2 }, gap.id]);
  } else {
    const y = gap.y + gap.width / 2;
    lines.push([{ x: gap.x - 2, y }, { x: gap.x + wall + 2, y }, gap.id], [{ x: gap.x + wall + 2, y }, { x: gap.x - 2, y }, gap.id]);
  }
}
for (const [from, to, id] of lines) {
  const length = Math.hypot(to.x - from.x, to.y - from.y);
  const steps = Math.ceil(length / 0.05);
  let current = {};
  const targets = {};
  let inRoom = false;
  for (let i = 0; i <= steps; i++) {
    const p = { x: from.x + ((to.x - from.x) * i) / steps, y: from.y + ((to.y - from.y) * i) / steps };
    const inside = wingsAt(p, parts);
    if (inside.length) inRoom = true;
    else if (inRoom && openings.some((g) => g.id === id)) expect(false, `the player is outside while crossing ${id} at ${p.x.toFixed(2)},${p.y.toFixed(2)}`);
    for (const wing of wings) {
      const out = roofGoesOut(wing.id, wings, inside);
      (targets[wing.id] ??= []).push(out);
    }
    const before = current;
    current = stepRoofs(current, wings, inside, 0.05 / 3.5);
    for (const wing of wings) {
      if (inside.includes(wing.id)) expect((current[wing.id] ?? 1) <= (before[wing.id] ?? 1), `a roof gets thicker over the player in ${wing.id} (${id})`);
    }
  }
  for (const wing of wings) {
    const changes = targets[wing.id].filter((v, i, all) => i && v !== all[i - 1]).length;
    expect(changes <= 2, `the roof of ${wing.id} flickers along ${id} (${changes} changes)`);
  }
}

// fading: steady, never back, ends exactly on the target, takes about ROOF_SECONDS, jumps with reduced motion
let roofs = {};
let frames = 0;
while ((roofs.mercado ?? 1) > 0 && frames < 1000) {
  const next = stepRoofs(roofs, wings, ["mercado"], 1 / 60);
  expect(next.mercado <= (roofs.mercado ?? 1), "going into the Mercado never makes its roof thicker");
  expect(next["learning-center"] === 1 && next.nova === 1 && next.hub === 1, "the other roofs stay closed in the Mercado");
  roofs = next;
  frames++;
}
expect(roofs.mercado === 0, "the roof of the Mercado ends exactly at 0");
expect(Math.abs(frames / 60 - ROOF_SECONDS) < 0.05, `the fade takes about ${ROOF_SECONDS}s (took ${frames / 60}s)`);
roofs = stepRoofs(roofs, wings, [], 10);
expect(wings.every((wing) => roofs[wing.id] === 1), "a long frame outside closes every roof exactly");
roofs = stepRoofs({}, wings, ["learning-center"], 0);
expect(wings.every((wing) => roofs[wing.id] === 1), "no time, no change");
roofs = stepRoofs({}, wings, ["nova"], 1 / 60, true);
expect(roofs.nova === 0 && roofs.hub === 0 && roofs.mercado === 1 && roofs["learning-center"] === 1, "reduced motion jumps");
expect(stepRoof(1, true, 1 / 60, true) === 0 && stepRoof(0, false, 1 / 60, true) === 1, "stepRoof still jumps with reduced motion");

// the names of the places
const at = (x, y) => areaAt({ x, y }, areas)?.id ?? null;
expect(at(14, 5) === "cafe" && at(21, 5) === "atrium" && at(30, 3) === "merch" && at(30, 7) === "print", "the places of the Nova");
expect(at(5, 7) === "study" && at(10, 5) === "seminar", "the places of the Learning Center");
expect(at(7, 11) === "supply", "the Supply Hall");
expect(at(30, 10) === "lounge" && at(30, 13) === "meeting", "the places of the Hub");
expect(at(21, 12) === null, "no place outside");

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
const { entrances, wall, parts, wings } = world.nova;
const areas = world.interiors.campus.areas;
const problems = [];
let checked = 0;
let throughDoor = 0;
let wingToWing = 0;

const starts = [zone.spawn];
for (let i = 0; i < 60; i++) {
  starts.push({
    x: zone.minX + 0.3 + (zone.maxX - zone.minX - 0.6) * ((i * 0.6180339) % 1),
    y: zone.minY + 0.3 + (zone.maxY - zone.minY - 0.6) * ((i * 0.7548776) % 1),
  });
}
const floors = wings.map((wing) => {
  const own = areas.filter((area) => area.wing === wing.id);
  return {
    id: wing.id,
    x0: Math.min(...own.map((a) => a.x)), x1: Math.max(...own.map((a) => a.x + a.w)),
    y0: Math.min(...own.map((a) => a.y)), y1: Math.max(...own.map((a) => a.y + a.h)),
  };
});
const insideSpots = [];
for (const floor of floors) {
  for (let x = floor.x0 + 0.4; x < floor.x1 - 0.2; x += 0.9) {
    for (let y = floor.y0 + 0.3; y < floor.y1 - 0.1; y += 0.7) insideSpots.push({ x, y, wing: floor.id });
  }
}
starts.push(...insideSpots);
const underRoof = (p) => parts.some((part) => p.x > part.x && p.x < part.x + part.w && p.y > part.y && p.y < part.y + part.h);
const crosses = (p, door) => p.y > door.y && p.y < door.y + wall && p.x > door.x && p.x < door.x + door.width;

function walk(start, goal, label) {
  const path = findPath(start, goal, zone, solid, RADIUS);
  if (!path) {
    problems.push(`no way to ${label}`);
    return null;
  }
  const crossed = new Set();
  let from = start;
  path.forEach((to) => {
    const steps = Math.ceil(Math.hypot(to.x - from.x, to.y - from.y) / 0.05);
    for (let i = 1; i <= steps; i++) {
      const p = { x: from.x + ((to.x - from.x) * i) / steps, y: from.y + ((to.y - from.y) * i) / steps };
      if (pointBlocked(p, solid, RADIUS - 0.01)) problems.push(`walks through something near ${label}`);
      for (const door of entrances) if (crosses(p, door)) crossed.add(door.id);
    }
    from = to;
  });
  return { path, crossed };
}

for (const start of starts.filter((p) => !pointBlocked(p, solid, RADIUS))) {
  for (const loc of Object.values(world.locations)) {
    checked++;
    const goal = nearestFreePoint({ x: loc.x, y: loc.y }, zone, solid, RADIUS);
    const result = walk(start, goal, loc.title);
    if (!result) continue;
    const end = result.path[result.path.length - 1];
    if (Math.hypot(end.x - loc.x, end.y - loc.y) >= REACH) problems.push(`${loc.title} out of reach`);
    if (!underRoof(start)) {
      // from outside, the only way in leads through an entrance
      if (result.crossed.size) throughDoor++;
      else problems.push(`${loc.title} was reached from outside without using an entrance`);
    }
  }
}

// from a place in each wing to a place in every other wing, and out to the plaza and back
for (const a of floors) {
  const from = insideSpots.find((s) => s.wing === a.id && !pointBlocked(s, solid, RADIUS));
  for (const b of floors) {
    if (a === b) continue;
    const to = insideSpots.find((s) => s.wing === b.id && !pointBlocked(s, solid, RADIUS) && s !== from);
    wingToWing++;
    walk(from, to, `${b.id} from ${a.id}`);
  }
  wingToWing++;
  const out = walk(from, zone.spawn, `the plaza from ${a.id}`);
  if (out && !out.crossed.size) problems.push(`left ${a.id} to the plaza without using an entrance`);
}

console.log(JSON.stringify({ checked, throughDoor, wingToWing, problems: [...new Set(problems)] }));
"""


def run_node(tmp_path, script, modules):
    for name in modules:
        shutil.copy(WORLD / name, tmp_path)
    (tmp_path / "package.json").write_text('{"type": "module"}')
    (tmp_path / "check.js").write_text(script)
    (tmp_path / "world.json").write_text(json.dumps(world.world_view()))
    done = subprocess.run([NODE, "check.js", "world.json"], cwd=tmp_path, capture_output=True, text=True, timeout=120)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


@needs_node
def test_the_roofs_of_the_wings_fade_with_the_real_roofs_module(tmp_path):
    assert run_node(tmp_path, ROOF_CHECK, ["roofs.js"])["problems"] == []


@needs_node
def test_every_desk_and_every_wing_is_reached_on_foot_with_the_real_path_finder(tmp_path):
    result = run_node(tmp_path, WALK_CHECK, ["paths.js", "physics.js"])
    assert result["checked"] > 600
    assert result["throughDoor"] > 30
    assert result["wingToWing"] >= 16
    assert result["problems"] == []
