"""Checks from specs/render-cache.md. There is no browser in the tests, so these keep the pieces
in place; that the picture is unchanged was checked in the browser (see the spec)."""

import re
from pathlib import Path

import app

WORLD = Path(app.__file__).parent / "static" / "world"


def source(name):
    return (WORLD / name).read_text(encoding="utf-8")


def test_mix_color_remembers_its_answers():
    code = source("primitives.js")
    assert "const mixed = new Map()" in code and "mixed.get(key)" in code
    assert "mixed.size >" in code  # and it cannot grow without end (a moving amount, the light)


def test_the_terrain_works_from_a_tile_list_made_once():
    code = source("campus.js")
    body = code[code.index("export function drawTerrain"):code.index("export function drawCampusBench")]
    assert "new WeakMap()" in code and "tilesOf(zone)" in body
    assert "mixColor(" not in body and ".sort(" not in body  # nothing is mixed or sorted per frame


def test_a_tile_is_drawn_without_making_objects():
    code = source("primitives.js")
    body = code[code.index("export function drawTile"):code.index("export function drawPlane")]
    assert "isoPoint" not in body


def test_the_nova_walls_and_canopy_are_built_once():
    code = source("nova.js")
    body = code[code.index("export function novaActors"):]
    assert "fixedActors()" in body and "wallActors()" not in body and "canopyActors()" not in body
    assert "built.source !== world.nova" in code


def test_the_world_skips_what_is_far_outside_the_view_and_can_draw_everything():
    code = source("render.js")
    assert "export const options = { cull: true }" in code
    assert re.search(r"depth < 2 \|\| depth > 60", code)  # kites, gulls and the tide pools are always drawn
    assert "visible(actor.depth" in code
