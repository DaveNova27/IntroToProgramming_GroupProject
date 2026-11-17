"""Checks from specs/lorry-road.md ("Done when"): a longer road north from the delivery lane.

Drawing only: the road is checked in the source and with Node against the world data; nothing else changes.
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

import app
import world

CAMPUS = Path(app.__file__).parent / "static" / "world" / "campus.js"
NODE = shutil.which("node")


def number(name):
    match = re.search(rf"\b{name} = (-?\d+(?:\.\d+)?)", CAMPUS.read_text())
    assert match, name
    return float(match.group(1))


def test_the_road_runs_from_the_lane_to_the_north_edge_of_the_ground():
    source = CAMPUS.read_text()
    assert "export function drawSupplyRoad()" in source
    assert "drawSupplyRoad(); // first" in source  # drawn with the lane, under it
    assert number("ROAD_FROM") == 0.0  # the north edge of the drawn ground
    assert number("ROAD_FROM") < world.ZONES["campus"]["minY"]  # beyond where anyone walks


def test_the_road_passes_the_learning_center_with_its_kerb():
    learning_center = next(p for p in world.NOVA["parts"] if p["id"] == "learning-center")
    road_east, road_west = number("ROAD_EAST"), number("ROAD_WEST")
    assert road_east + 0.2 <= learning_center["x"]  # asphalt and kerb stay west of its wall
    assert road_west == -1.4  # in line with the west edge of the lane
    lorry_west, lorry_east = -0.9, -0.9 + 1.5  # static/world/beach.js drawDeliveryLorry
    assert road_west < lorry_west and lorry_east < road_east  # the lorry fits the road it came by


def test_the_road_adds_no_solid_object_and_moves_nothing():
    assert "colliders" not in CAMPUS.read_text().split("export function drawSupplyRoad()")[1].split("export function drawServiceLane()")[0]
    ids = {c["id"] for c in world.colliders("campus")}
    assert {"delivery-pallet-north", "delivery-pallet-south", "delivery-gate-post"} <= ids
    assert not [i for i in ids if "road" in i]


@pytest.mark.skipif(NODE is None, reason="Node is not installed")
def test_the_campus_module_still_parses():
    done = subprocess.run([NODE, "--check", str(CAMPUS)], capture_output=True, text=True, timeout=60)
    assert done.returncode == 0, done.stderr
