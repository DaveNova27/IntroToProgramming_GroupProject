"""Checks from specs/render-cache.md. The rules of what is in view run for real with Node (cull.js is
pure); the rest of the pieces are kept in place by source checks, because there is no browser in the
tests: that the picture is unchanged was checked in the browser (see the spec)."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

import app

WORLD = Path(app.__file__).parent / "static" / "world"
NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="Node is not installed")

CHECK = """
import { SKIRT, TALL, actorVisible, rowRange } from "%s";
const ROW = 30.8, view = { top: 1000, bottom: 1900 };  // a 900 px view
const seen = (actor) => actorVisible(actor, view.top, view.bottom, ROW);
const out = {
  inside: seen({ depth: 40 }),
  tooFarAbove: seen({ depth: (view.top - 100 * ROW) / ROW - SKIRT - 8 }),         // its feet are far above the view
  tallReachesIn: seen({ depth: (view.bottom + TALL - 1) / ROW + SKIRT }),          // below the view, but tall enough to reach in
  tooFarBelow: seen({ depth: (view.bottom + TALL) / ROW + SKIRT + 1 }),
  justAboveWithLight: seen({ depth: view.top / ROW - SKIRT + 0.01 }),              // a lamp's light still reaches in
  always: seen({ depth: 200, always: true }) && seen({ depth: -50, always: true }),
  rows: rowRange(1000, 1900, ROW, 48), rowsTop: rowRange(-500, 300, ROW, 48), rowsBottom: rowRange(1400, 5000, ROW, 48),
};
console.log(JSON.stringify(out));
"""


@needs_node
def test_what_is_in_view_is_decided_with_room_for_tall_objects_and_light(tmp_path):
    script = tmp_path / "check.mjs"
    script.write_text(CHECK % (WORLD / "cull.js").as_uri())
    done = subprocess.run([NODE, str(script)], capture_output=True, text=True, timeout=30)
    assert done.returncode == 0, done.stderr
    r = json.loads(done.stdout)
    assert r["inside"] and r["tallReachesIn"] and r["justAboveWithLight"] and r["always"]
    assert not r["tooFarAbove"] and not r["tooFarBelow"]
    assert r["rows"][0] == 31 and r["rows"][1] == 47  # row 32 is the first with something in view; clamped
    assert r["rowsTop"][0] == 0 and r["rowsBottom"][1] == 47  # clamped to the map


def source(name):
    return (WORLD / name).read_text(encoding="utf-8")


def test_the_objects_that_must_always_be_drawn_say_so_and_nothing_is_culled_by_a_depth_guess():
    beach, render = source("beach.js"), source("render.js")
    assert "drawTidePools(t), true)" in beach and "drawKite(k, t), true)" in beach and "drawGull(g, t), true)" in beach
    assert "depth > 60" not in render and "actorVisible(actor" in render
    assert "export const options = { cull: true }" in render  # `false` draws everything: the check


def test_the_terrain_works_from_a_tile_list_made_once_and_walks_only_the_rows_in_view():
    code = source("campus.js")
    body = code[code.index("export function drawTerrain"):code.index("export function drawCampusBench")]
    assert "new WeakMap()" in code and "tilesOf(zone)" in body and "rowRange(" in body and "rowStart" in body
    assert "mixColor(" not in body and ".sort(" not in body  # nothing is mixed or sorted per frame


def test_there_is_one_definition_of_the_projection_and_a_tile_makes_no_objects():
    scene = source("scene.js")
    assert "export const isoX" in scene and "isoX(x)" in scene  # isoPoint is built from them
    body = source("primitives.js")
    body = body[body.index("export function drawTile"):body.index("export function drawPlane")]
    assert "isoPoint" not in body and "isoX(" in body and "* TILE" not in body


def test_the_nova_walls_and_canopy_are_built_again_when_the_building_changes():
    code = source("nova.js")
    body = code[code.index("export function novaActors"):]
    assert "fixedActors()" in body and "wallActors()" not in body and "canopyActors()" not in body
    assert "buildingKey" in code and "world.nova.parts.length" in code
