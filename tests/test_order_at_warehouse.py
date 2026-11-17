"""Checks from specs/order-at-warehouse.md ("Done when"): stock is ordered at the PC in the Supply Hall.

The server is unchanged (it never reads the position); the place, the walk and the screens are checked.
"""

import copy
import json
import shutil
import subprocess
from pathlib import Path

import pytest

import app
import db
import logic
import world

STATIC = Path(app.__file__).parent / "static"
WORLD_JS = STATIC / "world"
NODE = shutil.which("node")
REACH = 1.65  # static/world/locations.js
RADIUS = 0.28  # static/world/scene.js PLAYER_RADIUS


def area(area_id):
    return next(a for a in world.INTERIORS["campus"]["areas"] if a["id"] == area_id)


def inside(rect, x, y):
    return rect["x"] <= x <= rect["x"] + rect["w"] and rect["y"] <= y <= rect["y"] + rect["h"]


# ---- Check 1: the place ---------------------------------------------------------------------

def test_the_order_pc_stands_in_the_supply_hall():
    desk = next(s for s in world.INTERIORS["campus"]["solid"] if s["id"] == "order-pc")
    assert desk["wing"] == "mercado"
    hall = area("supply")
    for x, y in [(desk["x"], desk["y"]), (desk["x"] + desk["w"], desk["y"] + desk["h"])]:
        assert inside(hall, x, y), (x, y)


def test_the_order_place_is_in_front_of_the_pc_and_free():
    spot = world.LOCATIONS["supplier"]
    assert spot["action"] == "stock" and spot["label"] == "Order stock" and spot["wing"] == "mercado"
    assert spot["title"] == "ORDER PC" and spot["sub"] == "SUPPLY HALL"
    assert inside(area("supply"), spot["x"], spot["y"])
    desk = next(s for s in world.colliders("campus") if s["id"] == "order-pc")
    nearest_x = min(max(spot["x"], desk["x"]), desk["x"] + desk["width"])
    nearest_y = min(max(spot["y"], desk["y"]), desk["y"] + desk["height"])
    gap = ((spot["x"] - nearest_x) ** 2 + (spot["y"] - nearest_y) ** 2) ** 0.5
    assert RADIUS < gap < REACH  # a player fits there and reaches the PC
    for item in world.colliders("campus"):
        if item["shape"] == "rect":
            nx = min(max(spot["x"], item["x"]), item["x"] + item["width"])
            ny = min(max(spot["y"], item["y"]), item["y"] + item["height"])
            assert ((spot["x"] - nx) ** 2 + (spot["y"] - ny) ** 2) ** 0.5 >= RADIUS, item["id"]


def test_there_is_only_one_place_to_order_and_the_atrium_desk_is_gone():
    stock = [i for i, loc in world.LOCATIONS.items() if loc["action"] == "stock"]
    assert stock == ["supplier"]
    atrium = area("atrium")
    assert not inside(atrium, world.LOCATIONS["supplier"]["x"], world.LOCATIONS["supplier"]["y"])


WALK = """
import { readFileSync } from "node:fs";
import { findPath } from "./paths.js";
import { nearestFreePoint } from "./physics.js";
const data = JSON.parse(readFileSync(process.argv[2]));
const zone = data.zones.campus, solid = data.colliders.campus, pc = data.locations.supplier;
const goal = nearestFreePoint({ x: pc.x, y: pc.y }, zone, solid, 0.28);
const out = {};
// from the arrival plaza, the atrium of the Nova and the Dorm
for (const [name, start] of Object.entries({ plaza: { x: 7.4, y: 15.35 }, atrium: { x: 21.0, y: 6.0 }, dorm: { x: 36.8, y: 11.1 } })) {
  const path = findPath(start, goal, zone, solid, 0.28);
  const end = path ? path[path.length - 1] : null;
  out[name] = end ? Math.hypot(end.x - pc.x, end.y - pc.y) : null;
}
console.log(JSON.stringify(out));
"""


@pytest.mark.skipif(NODE is None, reason="Node is not installed")
def test_the_pc_is_reached_on_foot_from_the_plaza_the_atrium_and_the_dorm(tmp_path):
    for name in ("paths.js", "physics.js"):
        shutil.copy(WORLD_JS / name, tmp_path)
    (tmp_path / "package.json").write_text('{"type": "module"}')
    (tmp_path / "walk.js").write_text(WALK)
    (tmp_path / "world.json").write_text(json.dumps(world.world_view()))
    done = subprocess.run([NODE, "walk.js", "world.json"], cwd=tmp_path, capture_output=True, text=True, timeout=60)
    assert done.returncode == 0, done.stderr
    for start, distance in json.loads(done.stdout).items():
        assert distance is not None and distance < REACH, (start, distance)


def test_the_pc_is_drawn():
    rooms = (WORLD_JS / "rooms.js").read_text()
    assert 'id === "order-pc"' in rooms and "function drawOrderPc" in rooms


# ---- Check 2: the campus opens the order window only at the PC -------------------------------

def test_the_stock_button_walks_to_the_pc_and_the_window_needs_the_pc():
    ui = (WORLD_JS / "ui.js").read_text()
    main = (WORLD_JS / "main.js").read_text()
    assert '$("#btn-order").addEventListener("click", goOrder);' in ui
    assert 'if (mode === "order" && !atOrderPc()) return goOrder();' in ui
    assert 'const ORDER_PLACE = "supplier";' in ui and "walkToPlace(ORDER_PLACE)" in ui
    assert "function walkToPlace(id)" in main and "walkToPlace });" in main
    # the dashboard's button: the map walks once it is the main view again
    assert 'msg.type === "go-order"' in ui and "orderOnMain" in ui
    # review finding: walking away from the PC closes the order window, checked every frame
    assert 'if (panelMode === "order" && !atOrderPc()) closePanel();' in ui
    assert "keepOrderAtPc();" in main


# ---- Check 3: the dashboard has no buy form ---------------------------------------------------

def test_the_dashboard_has_no_buy_form_but_a_way_to_the_pc():
    dashboard = (STATIC / "app.js").read_text()
    views = (STATIC / "views.js").read_text()
    assert 'data-form="buy"' not in dashboard and "/api/buy" not in dashboard
    assert "data-go-order" in dashboard and "Go to the order PC" in dashboard
    assert 'window.addEventListener("go-order"' in views and 'tellMap({ type: "go-order" })' in views


# ---- Check 4: the server is unchanged ---------------------------------------------------------

@pytest.fixture
def run_on_disk(tmp_path, monkeypatch):
    path = tmp_path / "run.db"
    db.save(logic.new_state(), path)
    real_save = db.save
    monkeypatch.setattr(app, "load_run", lambda: db.load(path))
    monkeypatch.setattr(app.db, "save", lambda state, *_, **__: real_save(state, path))
    return path


def test_buying_through_the_api_works_from_anywhere_as_before(run_on_disk):
    # the position decides no rule (roadmap 3a): the player stands far from the PC
    state = db.load(run_on_disk)
    state["player"] = {"zone": "campus", "x": 36.8, "y": 11.1}
    db.save(state, run_on_disk)
    response = app.app.test_client().post("/api/buy", json={"product": "coffee", "quantity": 5})
    assert response.status_code == 200, response.get_json()
    after = db.load(run_on_disk)
    assert after["stock"]["coffee"] == 5
    assert after["cash"] == state["cash"] - 5 * logic.CATALOGUE["coffee"]["cost"]


def test_a_refused_purchase_still_changes_nothing(run_on_disk):
    before = copy.deepcopy(db.load(run_on_disk))
    response = app.app.test_client().post("/api/buy", json={"product": "coffee", "quantity": 999})
    assert response.status_code == 400
    assert db.load(run_on_disk) == before
