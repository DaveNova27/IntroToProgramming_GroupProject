"""The world is seen straight from the front (specs/map-view.md).
The world is drawn in a browser, so like the other page tests these read the files."""

import re
from pathlib import Path

WORLD = Path(__file__).resolve().parent.parent / "static" / "world"
SOURCES = {path.name: path.read_text() for path in sorted(WORLD.glob("*.js"))}
SCENE = SOURCES["scene.js"]
MAIN = SOURCES["main.js"]


def function_body(source, name):
    match = re.search(r"export function " + name + r"\(.*?\n\}", source, re.S)
    assert match, f"{name} is missing"
    return match.group(0)


def test_the_camera_is_the_straight_view_with_depth_0_7():
    assert re.search(r"export const TILE = 44;", SCENE)
    assert re.search(r"export const DEPTH = TILE \* 0\.7;", SCENE)
    body = function_body(SCENE, "isoPoint")
    assert "x: x * TILE" in body
    assert "y: y * DEPTH - z" in body


def test_a_click_maps_back_with_the_same_scale():
    body = function_body(SCENE, "canvasWorldPoint")
    assert "ix / TILE" in body
    assert "iy / DEPTH" in body


def test_the_diagonal_tile_sizes_and_rotation_are_gone():
    for name, source in SOURCES.items():
        assert "TILE_W" not in source, name
        assert "TILE_H" not in source, name
        assert "atan2(19, 38)" not in source, name


def test_the_draw_order_goes_by_the_front_edge():
    assert re.search(r"export const depthOf = \(x, y\) => y \+ x \* 0\.001;", SCENE)
    # no sort key adds up x and y any more: `depth: a.x + a.y` or `add(a.x + a.y`
    diagonal = re.compile(r"(depth:|add\()\s*([\w.\[\]]+)\.x \+ \2\.y")
    for name, source in SOURCES.items():
        assert not diagonal.search(source), name


def test_the_keys_walk_straight():
    match = re.search(r"function keyDirection\(\) \{(.*?)\n\}", MAIN, re.S)
    assert match
    keys = match.group(1)
    assert re.search(r'"arrowup"\)\) dy--;', keys)
    assert re.search(r'"arrowdown"\)\) dy\+\+;', keys)
    assert re.search(r'"arrowleft"\)\) dx--;', keys)
    assert re.search(r'"arrowright"\)\) dx\+\+;', keys)


def test_only_the_south_wall_faces_the_camera():
    assert 'const front = wall.side === "south";' in SOURCES["nova.js"]


def test_nothing_random_in_the_world():
    for name, source in SOURCES.items():
        assert "Math.random" not in source, name
