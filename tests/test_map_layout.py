"""Spec map-layout, part 1: the floor plan. Pure data checks on world.py, no server needed.

Every named point is inside its zone, walkable, not inside a solid object and reachable from the
spawn; no free ground is cut off; the Cafe's staff gap is wide enough; the kerb openings lead to the sand.
"""
import math
from collections import deque

import world

RADIUS = 0.28   # the player, as in static/world/physics.js
STEP = 0.2

ZONE = world.ZONES["campus"]
SOLID = world.colliders("campus")


def blocked(x, y):
    if x < ZONE["minX"] + RADIUS or x > ZONE["maxX"] - RADIUS:
        return True
    if y < ZONE["minY"] + RADIUS or y > ZONE["maxY"] - RADIUS:
        return True
    for c in SOLID:
        if c["shape"] == "circle":
            if math.hypot(x - c["x"], y - c["y"]) < c["radius"] + RADIUS:
                return True
        else:
            nx = min(max(x, c["x"]), c["x"] + c["width"])
            ny = min(max(y, c["y"]), c["y"] + c["height"])
            if math.hypot(x - nx, y - ny) < RADIUS:
                return True
    return False


def _grid():
    nx, ny = int(ZONE["maxX"] / STEP) + 1, int(ZONE["maxY"] / STEP) + 1
    free = {(i, j) for i in range(nx) for j in range(ny) if not blocked(i * STEP, j * STEP)}
    start = (round(ZONE["spawn"]["x"] / STEP), round(ZONE["spawn"]["y"] / STEP))
    seen, queue = {start}, deque([start])
    while queue:
        i, j = queue.popleft()
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (i + di, j + dj)
            if n in free and n not in seen:
                seen.add(n)
                queue.append(n)
    return free, seen


FREE, REACHED = _grid()


def reachable(point):
    return (round(point["x"] / STEP), round(point["y"] / STEP)) in REACHED


def named_points():
    pts = {}
    for name, spot in world.WORK_SPOTS["cafe"].items():
        for k, p in enumerate(spot if isinstance(spot, list) else [spot]):
            if isinstance(p, dict) and "x" in p:
                pts[f"cafe.{name}.{k}"] = p
    for shop in world.SHOPS_OUTDOOR:
        pts[f"{shop['id']}.front"] = shop["front"]
    for name, loc in world.LOCATIONS.items():
        pts[name] = loc
    pts["dorm.bed"] = world.DORM["bed"]
    pts["spawn"] = ZONE["spawn"]
    return pts


def test_named_points_are_walkable_and_reachable():
    problems = []
    for name, p in named_points().items():
        if blocked(p["x"], p["y"]):
            problems.append(f"{name} {p['x']},{p['y']} is blocked")
        elif not reachable(p):
            problems.append(f"{name} {p['x']},{p['y']} is not reachable from the spawn")
    assert not problems, problems


def test_no_free_ground_is_cut_off():
    cut_off = sorted((i * STEP, j * STEP) for i, j in FREE - REACHED)
    assert not cut_off, f"{len(cut_off)} free cells cannot be reached, first {cut_off[:5]}"


def test_cafe_staff_gap_is_wide_enough():
    by_id = {c["id"]: c for c in SOLID}
    shelf, counter = by_id["cafe-shelf"], by_id["cafe-counter"]
    gap = counter["y"] - (shelf["y"] + shelf["height"])
    assert gap >= 0.6, f"the gap behind the Cafe counter is {gap:.2f}"


def test_kerb_openings_lead_to_the_sand():
    kerb = world.BEACH["kerb"]
    segs = kerb["segments"]
    y_above, y_below = kerb["y"] - 0.4, kerb["y"] + kerb["h"] + 0.4
    for (_, x0), (x1, _) in zip(segs, segs[1:]):
        x = round((x0 + x1) / 2, 2)
        assert not blocked(x, y_above) and not blocked(x, y_below), f"kerb opening at x {x} is blocked"
        assert reachable({"x": x, "y": y_above}) and reachable({"x": x, "y": y_below}), f"opening at x {x} is cut off"
