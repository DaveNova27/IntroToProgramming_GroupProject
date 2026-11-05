"""Checks from specs/world-art.md ("Done when"). One test per check."""

from pathlib import Path

import pytest

import app
import world

WORLD = Path(app.__file__).parent / "static" / "world"
ACTIVITIES = [(zone_id, activity) for zone_id, room in world.INTERIORS.items() for activity in room["activities"]]


@pytest.mark.parametrize("zone_id, activity", ACTIVITIES, ids=lambda v: v if isinstance(v, str) else v["label"])
def test_every_person_in_a_room_stands_inside_it_and_has_a_label(zone_id, activity):
    zone = world.ZONES[zone_id]
    assert zone["minX"] <= activity["x"] <= zone["maxX"]
    assert zone["minY"] <= activity["y"] <= zone["maxY"]
    assert activity["label"]


@pytest.mark.parametrize("zone_id, activity", ACTIVITIES, ids=lambda v: v if isinstance(v, str) else v["label"])
def test_the_drawing_code_knows_every_pose(zone_id, activity):
    people = (WORLD / "people.js").read_text()
    assert activity["pose"] == "idle" or f'"{activity["pose"]}"' in people


@pytest.mark.parametrize("name", ["people.js", "walkers.js", "player.js"])
def test_figures_never_talk_to_the_server(name):
    code = (WORLD / name).read_text()
    assert "fetch(" not in code
    assert "/api/" not in code


def test_every_outdoor_place_is_inside_the_campus():
    zone = world.ZONES["campus"]
    assert world.SPACES
    for space in world.SPACES.values():
        assert zone["minX"] <= space["x"] <= zone["maxX"]
        assert zone["minY"] <= space["y"] <= zone["maxY"]
