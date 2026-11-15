"""Walk the layout served to the browser with its 0.28-tile player radius."""

import math
from collections import deque

import app
import logic

RADIUS = 0.28
STEP = 0.25


def world_data():
    response = app.app.test_client().get("/api/world")
    assert response.status_code == 200
    return response.get_json()


def free(point, zone, solid, radius=RADIUS):
    x, y = point
    if not (zone["minX"] + radius <= x <= zone["maxX"] - radius
            and zone["minY"] + radius <= y <= zone["maxY"] - radius):
        return False
    for item in solid:
        dx, dy = x - item["x"], y - item["y"]
        if item["shape"] == "circle":
            if dx * dx + dy * dy < (radius + item["radius"]) ** 2:
                return False
        else:
            dx = max(-dx, 0, dx - item["width"])
            dy = max(-dy, 0, dy - item["height"])
            if dx * dx + dy * dy < radius ** 2:
                return False
    return True


def connected_floor(zone, solid):
    spawn = zone["spawn"]["x"], zone["spawn"]["y"]
    # Extra clearance of half a step certifies the whole segment between adjacent cells.
    margin = RADIUS + STEP / 2
    assert free(spawn, zone, solid, margin)
    connected = {spawn}
    seen = {spawn}
    todo = deque([spawn])
    while todo:
        x, y = todo.popleft()
        for point in ((x - STEP, y), (x + STEP, y), (x, y - STEP), (x, y + STEP)):
            if point in seen:
                continue
            seen.add(point)
            if free(point, zone, solid, margin):
                connected.add(point)
                todo.append(point)
    return connected


def test_every_shop_and_storage_position_is_walkable_from_spawn():
    data = world_data()
    shops = data["places"]["shops"]
    assert set(shops) == set(logic.SHOPS)
    destinations = []
    for shop, place in shops.items():
        assert place["zone"] == "campus"
        assert len(place["break"]) >= 2
        points = [place[key] for key in ("front", "storeroom", "counter", "seller")] + place["break"]
        line = place["queue"]
        assert (line["dx"], line["dy"]) != (0, 0)
        assert data["guests"]["lines"][shop] == {"wing": place["wing"], **line}
        for i in range(6):
            points.append({"x": line["x"] + i * line["dx"], "y": line["y"] + i * line["dy"]})
        destinations.extend((shop, p["x"], p["y"]) for p in points)
    storage = data["places"]["central_storage"]
    assert storage["zone"] == "campus"
    destinations.extend((key, storage[key]["x"], storage[key]["y"]) for key in ("front", "computer", "unload"))

    zone, solid = data["zones"]["campus"], data["colliders"]["campus"]
    floor = connected_floor(zone, solid)
    for name, x, y in destinations:
        assert free((x, y), zone, solid), (name, x, y)
        # Finish the walk at the exact spot. A disc centred halfway along this last
        # short step covers the moving player's full footprint from start to finish.
        assert any(
            free(((x + px) / 2, (y + py) / 2), zone, solid, RADIUS + math.hypot(px - x, py - y) / 2)
            for px, py in floor if abs(px - x) <= STEP and abs(py - y) <= STEP
        ), (name, x, y)


def test_main_crossings_have_room_to_walk_straight():
    data = world_data()
    zone, solid = data["zones"]["campus"], data["colliders"]["campus"]
    crossings = [
        ((38, 13), (38, 16.9)),       # Dorm flagstones
        ((38, 16.9), (14.4, 16.9)),   # plaza to the boardwalk arch
        ((23, 16.9), (23, 8.5)),      # courtyard to the Nova
        ((14.4, 16.9), (14.4, 32.5)), # boardwalk
        ((4.7, 22), (4.7, 28.7)),     # west steps beside the Surf Shop
        ((33.1, 22), (33.1, 29.1)),   # east steps beside the Beach Cafe
        ((8.6, 29.1), (33.1, 29.1)),  # along the shop fronts, north of the fire
        ((28.2, 29.1), (28.2, 27.4)), # through the Beach Cafe seating
    ]
    for (x, y), (end_x, end_y) in crossings:
        steps = math.ceil(math.hypot(end_x - x, end_y - y) / 0.1)
        for i in range(steps + 1):
            p = x + (end_x - x) * i / steps, y + (end_y - y) * i / steps
            assert free(p, zone, solid, RADIUS + 0.10), p
