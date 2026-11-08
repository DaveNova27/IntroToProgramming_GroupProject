"""Checks from specs/nova-zones.md ("Done when"). One test per check.

The data of the beach way, the two outdoor shops, the beach and the Dorm is fixed on the server (world.py);
these tests read it the way the browser does and walk over it with a player of the real size. No
existing test is edited: the Dorm is kept apart from NOVA, so the checks of walk-in and nova-wings still
see the Nova as before.
"""

import importlib
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

RADIUS = 0.28  # the same as PLAYER_RADIUS in static/world/scene.js
WORLD_JS = Path(app.__file__).parent / "static" / "world"
NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="Node is not installed")


@pytest.fixture
def run_on_disk(tmp_path, monkeypatch):
    """The real API on a temporary save, so the player's own run stays untouched."""
    path = tmp_path / "run.db"
    db.save(logic.new_state(), path)
    real_save = db.save
    monkeypatch.setattr(app, "load_run", lambda: db.load(path))
    monkeypatch.setattr(app.db, "save", lambda state: real_save(state, path))
    return path


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


def solids():
    return world.colliders("campus")


def footprint(thing):
    return thing["x"], thing["y"], thing["x"] + thing["w"], thing["y"] + thing["h"]


def overlap(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def zone():
    return world.ZONES["campus"]


def inside_zone(x, y):
    z = zone()
    return z["minX"] <= x <= z["maxX"] and z["minY"] <= y <= z["maxY"]


def shape_distance(a, b):
    """Gap between two solids of the dorm data (rectangles x, y, w, h or circles r)."""
    def box(s):
        if "r" in s:
            return s["x"] - s["r"], s["y"] - s["r"], s["x"] + s["r"], s["y"] + s["r"]
        return s["x"], s["y"], s["x"] + s["w"], s["y"] + s["h"]
    ax0, ay0, ax1, ay1 = box(a)
    bx0, by0, bx1, by1 = box(b)
    return math.hypot(max(bx0 - ax1, ax0 - bx1, 0), max(by0 - ay1, ay0 - by1, 0))


def walk_grid(plugs=()):
    """Walk from the spawn over a grid with a real-sized player; returns (cells, point function)."""
    z = zone()
    blocked_by = solids() + list(plugs)
    step = 0.3
    columns = int((z["maxX"] - z["minX"]) / step) + 1
    rows = int((z["maxY"] - z["minY"]) / step) + 1
    point = lambda c, r: (z["minX"] + c * step, z["minY"] + r * step)  # noqa: E731
    cache = {}

    def ok(c, r):
        if (c, r) not in cache:
            cache[(c, r)] = 0 <= c < columns and 0 <= r < rows and not is_blocked(*point(c, r), blocked_by)
        return cache[(c, r)]

    start = (round((z["spawn"]["x"] - z["minX"]) / step), round((z["spawn"]["y"] - z["minY"]) / step))
    seen = {start}
    todo = deque([start])
    while todo:
        c, r = todo.popleft()
        for n in ((c + 1, r), (c - 1, r), (c, r + 1), (c, r - 1)):
            if n not in seen and ok(*n):
                seen.add(n)
                todo.append(n)
    return {point(c, r) for c, r in seen}


def reaches(cells, x, y, within=0.45):
    return any(math.hypot(px - x, py - y) < within for px, py in cells)


def dorm_floor():
    """The walkable floor of the Dorm: the box of its part without the thickness of its walls."""
    part = world.DORM["parts"][0]
    wall = world.DORM["wall"]
    return part["x"] + wall, part["y"] + wall, part["x"] + part["w"] - wall, part["y"] + part["h"] - wall


# ---- Check 2: the data is complete and consistent ----------------------------------

def test_the_world_serves_the_dorm_the_shops_the_way_and_the_beach():
    view = world.world_view()
    for key in ("dorm", "outdoorShops", "beachWay", "beach"):
        assert view[key], key
    assert view["spaces"] and view["nova"]["wings"] and view["planters"] and view["trees"]


def test_the_dorm_is_a_wing_shaped_like_the_nova_and_kept_apart_from_it():
    dorm = world.DORM
    assert [w["id"] for w in dorm["wings"]] == ["dorm"]
    for group in ("parts", "walls", "entrances"):
        assert dorm[group] and all(item["wing"] == "dorm" for item in dorm[group]), group
    assert all(w["wing"] == "dorm" for w in dorm["interior"]["areas"] + dorm["interior"]["solid"] + dorm["interior"]["activities"])
    # kept apart: the Nova and its tests do not see it
    assert "dorm" not in {w["id"] for w in world.NOVA["wings"]}
    assert not any(p["wing"] == "dorm" for p in world.NOVA["parts"])
    assert not any(a["wing"] == "dorm" for a in world.INTERIORS["campus"]["areas"])
    assert "bed" not in world.LOCATIONS


def test_the_entrance_of_the_dorm_is_on_the_south_side_and_wide_enough():
    (entrance,) = world.DORM["entrances"]
    assert entrance["side"] == "south" and entrance["width"] >= 2
    wall_y = entrance["y"]
    for wall in world.DORM["walls"]:
        # no wall covers the entrance
        assert not (wall["x"] < entrance["x"] + entrance["width"] and entrance["x"] < wall["x"] + wall["w"]
                    and wall["y"] < wall_y + world.DORM["wall"] and wall_y < wall["y"] + wall["h"]), wall["id"]


def test_the_places_of_the_dorm_split_its_floor_between_them():
    x0, y0, x1, y1 = dorm_floor()
    areas = world.DORM["interior"]["areas"]
    assert min(a["x"] for a in areas) == pytest.approx(x0) and max(a["x"] + a["w"] for a in areas) == pytest.approx(x1)
    assert min(a["y"] for a in areas) == pytest.approx(y0) and max(a["y"] + a["h"] for a in areas) == pytest.approx(y1)
    assert sum(a["w"] * a["h"] for a in areas) == pytest.approx((x1 - x0) * (y1 - y0))
    for a, b in ((a, b) for i, a in enumerate(areas) for b in areas[i + 1:]):
        assert not overlap(footprint(a), footprint(b)), (a["id"], b["id"])


def test_everything_in_the_dorm_stands_on_its_floor_and_it_is_furnished():
    x0, y0, x1, y1 = dorm_floor()
    interior = world.DORM["interior"]
    assert len(interior["solid"]) >= 4 and len(interior["activities"]) >= 1
    for item in interior["solid"]:
        r = item.get("r", 0)
        left, top, right, bottom = (item["x"] - r, item["y"] - r, item["x"] + r, item["y"] + r) if r else footprint(item)
        assert x0 - 1e-9 <= left and right <= x1 + 1e-9 and y0 - 1e-9 <= top and bottom <= y1 + 1e-9, item["id"]
    for person in interior["activities"]:
        assert x0 <= person["x"] <= x1 and y0 <= person["y"] <= y1


def test_every_gap_in_the_dorm_is_shut_or_wide_enough_for_the_grid():
    """The rule of walk-in: a gap between two pieces is at most 0.5 (shut) or at least 1.4 wide."""
    interior = world.DORM["interior"]
    pieces = interior["solid"]
    for a, b in ((a, b) for i, a in enumerate(pieces) for b in pieces[i + 1:]):
        gap = shape_distance(a, b)
        assert gap <= 0.5 or gap >= 1.4 - 1e-9, (a["id"], b["id"], round(gap, 2))
    x0, y0, x1, y1 = dorm_floor()
    for item in pieces:
        walls = [
            ("west", item["x"] - item.get("r", 0) - x0), ("north", item["y"] - item.get("r", 0) - y0),
            ("east", x1 - (item["x"] + item.get("w", 0) + item.get("r", 0))),
            ("south", y1 - (item["y"] + item.get("h", 0) + item.get("r", 0))),
        ]
        for side, gap in walls:
            assert gap <= 0.5 or gap >= 1.4 - 1e-9, (item["id"], side, round(gap, 2))


def test_the_new_places_stay_inside_the_walkable_area_and_do_not_overlap():
    boxes = {s["id"]: footprint(s) for s in world.SHOPS_OUTDOOR}
    boxes["beach-way"] = footprint(world.BEACH_WAY)
    boxes["dorm"] = footprint(world.DORM["parts"][0])
    z = zone()
    for name, (x0, y0, x1, y1) in boxes.items():
        assert z["minX"] <= x0 and x1 <= z["maxX"] and z["minY"] <= y0 and y1 <= z["maxY"], name
    names = list(boxes)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            assert not overlap(boxes[a], boxes[b]), (a, b)
        for part in world.NOVA["parts"]:
            assert not overlap(boxes[a], footprint(part)), (a, part["id"])
        for entrance in world.NOVA["entrances"]:
            gap = (entrance["x"], entrance["y"], entrance["x"] + entrance["width"], entrance["y"] + world.NOVA["wall"])
            assert not overlap(boxes[a], gap), (a, entrance["id"])
        for fence in (s for s in solids() if s["kind"] == "boundary"):
            fbox = (fence["x"], fence["y"], fence["x"] + fence["width"], fence["y"] + fence["height"])
            assert not overlap(boxes[a], fbox), (a, fence["id"])


def test_the_shops_have_a_free_front_spot_and_are_known_by_their_roadmap_ids():
    assert {s["id"] for s in world.SHOPS_OUTDOOR} == {"surf-shop", "beach-cafe"}
    for shop in world.SHOPS_OUTDOOR:
        front = shop["front"]
        assert inside_zone(front["x"], front["y"]), shop["id"]
        assert not is_blocked(front["x"], front["y"], solids()), shop["id"]
        x0, y0, x1, y1 = footprint(shop)
        assert x0 <= front["x"] <= x1 and y0 <= front["y"] <= y1, "the front spot is under the awning"


def test_the_dorm_entrance_the_bed_and_the_spawn_are_free_for_a_real_sized_player():
    (entrance,) = world.DORM["entrances"]
    middle = entrance["x"] + entrance["width"] / 2
    for dy in (-0.6, 0.25, 0.6, 1.2):  # outside, in the doorway, inside
        assert not is_blocked(middle, entrance["y"] + dy + 0.25, solids()), dy
    bed = world.DORM["bed"]
    assert bed["kind"] == "panel" and bed["action"] == "dorm" and bed["zone"] == "campus" and bed["wing"] == "dorm"
    assert inside_zone(bed["x"], bed["y"]) and not is_blocked(bed["x"], bed["y"], solids())
    spawn = zone()["spawn"]
    assert spawn == {"x": 21, "y": 18} and not is_blocked(spawn["x"], spawn["y"], solids())


def test_the_beach_way_is_at_least_three_tiles_wide_and_free_to_walk():
    way = world.BEACH_WAY
    assert way["w"] >= 3
    inner = [way["x"] + 0.4 + i * 0.2 for i in range(int((way["w"] - 0.8) / 0.2) + 1)]
    y = way["y"]
    while y <= way["y"] + way["h"]:
        for x in inner:
            assert not is_blocked(x, y, solids()), (round(x, 2), round(y, 2))
        y += 0.2


def test_the_spaces_are_named_in_bounds_and_the_new_ones_are_free():
    for space in world.SPACES.values():
        assert inside_zone(space["x"], space["y"]), space["id"]
    for name in ("beachCafe", "surfShop", "beachWay", "dorm"):
        space = world.SPACES[name]
        assert not is_blocked(space["x"], space["y"], solids()), name
    assert {"beachCafe", "surfShop", "beachWay", "dorm"} <= set(world.SPACES)
    assert "foodCourt" not in world.SPACES


def test_the_beach_data_is_fixed_and_not_random():
    first = repr(world.BEACH)
    reloaded = importlib.reload(world)
    try:
        assert repr(reloaded.BEACH) == first
    finally:
        importlib.reload(world)
    source = Path(world.__file__).read_text()
    assert "import random" not in source and "random." not in source
    for name in ("beach.js", "zones.js"):
        assert "Math.random" not in (WORLD_JS / name).read_text()


# ---- Check 3: walking ------------------------------------------------------------------------

def test_the_dorm_the_shops_the_beach_and_every_space_can_be_reached_on_foot():
    cells = walk_grid()
    bed = world.DORM["bed"]
    assert reaches(cells, bed["x"], bed["y"]), "the bed"
    for shop in world.SHOPS_OUTDOOR:
        assert reaches(cells, shop["front"]["x"], shop["front"]["y"]), shop["id"]
    way = world.BEACH_WAY
    assert reaches(cells, way["x"] + way["w"] / 2, way["y"] + way["h"] - 0.2), "the end of the beach way on the sand"
    for space in world.SPACES.values():
        assert reaches(cells, space["x"], space["y"]), space["id"]
    for loc in world.LOCATIONS.values():
        assert reaches(cells, loc["x"], loc["y"], within=1.65), loc["id"]  # the three desks, as before


def test_every_free_spot_on_the_map_is_connected_to_the_spawn():
    """No pocket that the new props shut off: a click there would do nothing."""
    cells = {(round(x, 3), round(y, 3)) for x, y in walk_grid()}
    z = zone()
    step = 0.3
    solid = solids()
    cut_off = [
        (round(z["minX"] + i * step, 2), round(z["minY"] + j * step, 2))
        for i in range(int((z["maxX"] - z["minX"]) / step) + 1)
        for j in range(int((z["maxY"] - z["minY"]) / step) + 1)
        if not is_blocked(z["minX"] + i * step, z["minY"] + j * step, solid)
        and (round(z["minX"] + i * step, 3), round(z["minY"] + j * step, 3)) not in cells
    ]
    assert cut_off == []


def test_the_dorm_can_only_be_entered_through_its_entrance():
    (entrance,) = world.DORM["entrances"]
    plug = {"id": "plug", "shape": "rect", "x": entrance["x"] - 0.2, "y": entrance["y"] - 0.2,
            "width": entrance["width"] + 0.4, "height": world.DORM["wall"] + 0.4, "label": "x", "kind": "wall"}
    cells = walk_grid([plug])
    x0, y0, x1, y1 = dorm_floor()
    assert not any(x0 < x < x1 and y0 < y < y1 for x, y in cells), "nobody gets in through a wall"
    assert any(x0 < x < x1 and y0 < y < y1 for x, y in walk_grid()), "and with the entrance open everybody does"


# ---- Check 5: the use point of the Dorm and the API ----------------------------------------------

def test_the_bed_is_the_only_new_use_point_and_the_panel_needs_no_new_endpoint():
    rules = {rule.rule for rule in app.app.url_map.iter_rules()}
    assert not [r for r in rules if "dorm" in r or "sleep" in r], "the panel calls the requests that exist"
    ui = (WORLD_JS / "ui.js").read_text()
    assert 'action === "dorm"' in ui
    # the button does what the Open button does: the same function, no new request
    assert "data-dorm-open" in ui and "return openDay();" in ui


def test_a_position_inside_the_dorm_is_saved_and_comes_back(run_on_disk):
    client = app.app.test_client()
    bed = world.DORM["bed"]
    body = {"zone": "campus", "x": bed["x"], "y": bed["y"]}
    assert client.post("/api/player", json=body).status_code == 200
    assert client.get("/api/state").get_json()["player"] == {"zone": "campus", "x": bed["x"], "y": bed["y"]}


def test_a_position_outside_the_map_is_still_refused(run_on_disk):
    client = app.app.test_client()
    before = client.get("/api/state").get_json()["player"]
    for body in ({"zone": "campus", "x": 45, "y": 10}, {"zone": "dorm", "x": 38, "y": 10}):
        assert client.post("/api/player", json=body).status_code == 400
    assert client.get("/api/state").get_json()["player"] == before


# ---- Check 4: the roof of the Dorm, with the real browser modules (Node) ---------------------------

ROOF_CHECK = """
import { readFileSync } from "node:fs";
import { ROOF_SECONDS, insideParts, stepRoofs, wingsAt } from "./roofs.js";
import { joinDorm } from "./zones.js";

const world = JSON.parse(readFileSync(process.argv[2]));
const nova = world.nova;
const novaWingCount = nova.wings.length;
joinDorm(world);
const problems = [];
const expect = (ok, text) => ok || problems.push(text);

// the browser joins the Dorm to the Nova: one more wing, its walls and parts, its room and its bed
expect(world.nova.wings.length === novaWingCount + 1, "the Dorm is one more wing");
expect(world.nova.wings.some((w) => w.id === "dorm"), "the wing is called dorm");
expect(world.nova.walls.length === nova.walls.length + world.dorm.walls.length, "its walls are joined");
expect(world.nova.entrances.some((e) => e.wing === "dorm"), "its entrance is joined");
expect(world.interiors.campus.areas.some((a) => a.wing === "dorm"), "its room is joined");
expect(world.locations.bed?.action === "dorm", "the bed is a place");
expect(!("bed" in world.locations) || world.locations.bed.wing === "dorm", "the bed belongs to the Dorm");

const parts = world.nova.parts;
const wings = world.nova.wings;
const door = world.dorm.entrances[0];
const middle = door.x + door.width / 2;
expect(wingsAt({ x: middle, y: 10 }, parts).join() === "dorm", "in the room the player is in the Dorm only");
expect(wingsAt({ x: 38, y: 15 }, parts).length === 0, "on the plaza in front of it nobody is inside");
expect(wingsAt({ x: 21, y: 5 }, parts).join() === "nova", "in the atrium the Dorm is not involved");
expect(!insideParts({ x: 34.3, y: 10 }, parts), "the strip between the Hub and the Dorm is outside");

// walking in through the entrance: inside flips once, never back
let flips = 0;
let was = insideParts({ x: middle, y: door.y + 2 }, parts);
for (let y = door.y + 2; y >= door.y - 2; y -= 0.05) {
  const now = insideParts({ x: middle, y }, parts);
  if (now !== was) flips++;
  was = now;
}
expect(flips === 1, `the roof edge is crossed once at the entrance (${flips})`);

// the roofs: only the Dorm goes out when the player is in it, all come back outside
let roofs = {};
const dt = 1 / 60;
const inside = wingsAt({ x: middle, y: 10 }, parts);
let seconds = 0;
let thickest = 0;
for (let i = 0; i < 120; i++) {
  const next = stepRoofs(roofs, wings, inside, dt);
  if (roofs.dorm !== undefined && next.dorm > roofs.dorm + 1e-12) problems.push("the roof of the room got thicker");
  roofs = next;
  if (roofs.dorm > 0) seconds = (i + 1) * dt;
  thickest = Math.max(thickest, ...wings.filter((w) => w.id !== "dorm").map((w) => 1 - roofs[w.id]));
}
expect(roofs.dorm === 0, "the roof of the Dorm ends exactly gone");
expect(Math.abs(seconds - ROOF_SECONDS) < 0.05, `it takes about ${ROOF_SECONDS} s (${seconds.toFixed(2)})`);
expect(thickest === 0, "no other roof moves");
for (let i = 0; i < 120; i++) roofs = stepRoofs(roofs, wings, [], dt);
expect(wings.every((w) => roofs[w.id] === 1), "outside every roof is back");
expect(stepRoofs({}, wings, inside, dt, true).dorm === 0, "with reduced motion it jumps");
console.log(JSON.stringify({ problems }));
"""


@needs_node
def test_the_roof_of_the_dorm_opens_and_closes_with_the_real_browser_modules(tmp_path):
    for name in ("roofs.js", "zones.js"):
        shutil.copy(WORLD_JS / name, tmp_path)
    (tmp_path / "package.json").write_text('{"type": "module"}')
    (tmp_path / "check.js").write_text(ROOF_CHECK)
    (tmp_path / "world.json").write_text(json.dumps(world.world_view()))
    done = subprocess.run([NODE, "check.js", "world.json"], cwd=tmp_path, capture_output=True, text=True, timeout=60)
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout)["problems"] == []
