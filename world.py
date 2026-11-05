"""The campus as data: zones, doors, solid objects and room layouts.

No rules, no database and no drawing in this file. The browser reads all of it
from GET /api/world and only draws it. logic.py uses the zones to check where the
player may stand; a later build mode can use the same colliders as protected ground.

Units are map tiles, not money, so plain numbers are fine here.
The layout comes from Felix Antes' project Nova Beach Ventures
(https://github.com/felix-anthes-png/nova-beach-ventures), without its shops.
"""

START_ZONE = "campus"


# ---- zones -----------------------------------------------------------------------
# width/height: size of the drawn ground. minX..maxY: where a person may walk.

ZONES = {
    "campus": {
        "id": "campus", "name": "Nova Coast Campus", "sub": "CARCAVELOS OUTDOORS",
        "width": 90, "height": 30, "minX": 1, "maxX": 41, "minY": 7.5, "maxY": 25.7,
        "outdoor": True, "spawn": {"x": 21, "y": 18},
    },
    "mercado": {
        "id": "mercado", "name": "Mercado Supply Hall", "sub": "SUPPLY INTERIOR",
        "width": 15, "height": 12, "minX": 1.2, "maxX": 13.8, "minY": 1.2, "maxY": 10.3,
        "outdoor": False, "spawn": {"x": 7.5, "y": 8.8}, "floor": "#d8c79f", "accent": "#f5c95e",
    },
    "academy": {
        "id": "academy", "name": "Academic Wing", "sub": "COURTYARD INTERIOR",
        "width": 15, "height": 12, "minX": 1.2, "maxX": 13.8, "minY": 1.2, "maxY": 10.3,
        "outdoor": False, "spawn": {"x": 7.5, "y": 8.8}, "floor": "#d7dad3", "accent": "#ff7b5b",
    },
    "hub": {
        "id": "hub", "name": "Student Hub", "sub": "STUDENT INTERIOR",
        "width": 15, "height": 12, "minX": 1.2, "maxX": 13.8, "minY": 1.2, "maxY": 10.3,
        "outdoor": False, "spawn": {"x": 7.5, "y": 8.8}, "floor": "#cddbd5", "accent": "#64cbc8",
    },
}


# ---- places the player can use with E or a click ---------------------------------
# kind "door" changes the zone. kind "panel" opens a screen in the browser ("action").

LOCATIONS = {
    "marketDoor": {
        "zone": "campus", "x": 7, "y": 15.2, "kind": "door", "label": "Enter Mercado Supply Hall",
        "targetZone": "mercado", "color": "#f5c95e", "title": "MERCADO", "sub": "ENTER",
    },
    "academyDoor": {
        "zone": "campus", "x": 20, "y": 12.2, "kind": "door", "label": "Enter the Academic Wing",
        "targetZone": "academy", "color": "#ff7b5b", "title": "ACADEMIC WING", "sub": "ENTER",
    },
    "hubDoor": {
        "zone": "campus", "x": 34.5, "y": 14.2, "kind": "door", "label": "Enter the Student Hub",
        "targetZone": "hub", "color": "#64cbc8", "title": "STUDENT HUB", "sub": "ENTER",
    },
    "supplier": {
        "zone": "mercado", "x": 7.5, "y": 4.2, "kind": "panel", "action": "stock", "label": "Order stock",
        "color": "#f5c95e", "title": "SUPPLY DESK", "sub": "ORDER DESK",
    },
    "marketExit": {
        "zone": "mercado", "x": 7.5, "y": 9.8, "kind": "door", "label": "Back outside",
        "targetZone": "campus", "spawn": {"x": 7, "y": 16.8}, "color": "#f5c95e", "title": "CAMPUS", "sub": "EXIT",
    },
    "stand": {
        "zone": "academy", "x": 7.25, "y": 3.72, "kind": "panel", "action": "prices", "label": "Set your prices",
        "color": "#ff7b5b", "title": "SNACK STAND", "sub": "SNACK STAND",
    },
    "academyExit": {
        "zone": "academy", "x": 7.5, "y": 9.8, "kind": "door", "label": "Back outside",
        "targetZone": "campus", "spawn": {"x": 20, "y": 13.8}, "color": "#ff7b5b", "title": "CAMPUS", "sub": "EXIT",
    },
    "board": {
        "zone": "hub", "x": 10.5, "y": 5.2, "kind": "panel", "action": "dashboard", "label": "Open the dashboard",
        "color": "#67b7d1", "title": "VENTURE BOARD", "sub": "RESULTS",
    },
    "hubExit": {
        "zone": "hub", "x": 7.5, "y": 9.8, "kind": "door", "label": "Back outside",
        "targetZone": "campus", "spawn": {"x": 34.5, "y": 15.8}, "color": "#64cbc8", "title": "CAMPUS", "sub": "EXIT",
    },
}


# ---- the outdoor campus -----------------------------------------------------------

BUILDINGS = {
    "library": {"id": "learning-center", "x": 2.2, "y": 3.25, "w": 8.4, "h": 5.15, "label": "Learning Center"},
    "mercado": {"id": "mercado-building", "x": 3.15, "y": 8.85, "w": 8.25, "h": 4.45, "label": "Mercado Supply Hall"},
    "academicWest": {"id": "academic-west", "x": 12.2, "y": 3.1, "w": 6.2, "h": 5.7, "label": "Academic Wing"},
    "academicCentre": {"id": "academic-centre", "x": 18.2, "y": 3.55, "w": 5.8, "h": 5.15, "label": "Academic Wing"},
    "academicEast": {"id": "academic-east", "x": 23.8, "y": 3.05, "w": 6.3, "h": 5.75, "label": "Academic Wing"},
    "studentHub": {"id": "student-hub", "x": 30.05, "y": 5.05, "w": 9.2, "h": 6.15, "label": "Student Hub"},
}

PLANTERS = [
    {"id": "academic-planter-west", "x": 13.1, "y": 8.95, "w": 4.2, "h": 0.62, "z": 13},
    {"id": "academic-planter-east", "x": 24.6, "y": 8.95, "w": 4.35, "h": 0.62, "z": 13},
    {"id": "library-planter", "x": 3.05, "y": 8.58, "w": 2.55, "h": 0.55, "z": 12},
    {"id": "mercado-planter", "x": 4.05, "y": 13.36, "w": 2.35, "h": 0.52, "z": 11},
    {"id": "hub-planter-west", "x": 31.05, "y": 11.35, "w": 3.15, "h": 0.58, "z": 12},
    {"id": "hub-planter-east", "x": 36.15, "y": 11.35, "w": 2.15, "h": 0.58, "z": 12},
]

# palm trees: x, y, size
TREES = [
    [2, 8, 0.9], [5, 14, 0.8], [11, 19, 0.82], [14, 22, 0.9], [18, 10, 0.72], [25, 12, 0.76], [29, 19, 0.88],
    [32, 9, 0.83], [39, 12, 0.92], [37, 19, 0.8], [6, 21, 0.75], [24, 22, 0.72], [40, 21, 0.86],
]

TERRACE_TABLES = [
    [14.7, 14.95], [17.1, 14.7], [19.15, 15.25], [20.65, 14.55],
    [25.35, 19.75], [27.2, 20.35], [29.25, 19.75], [31, 20.45],
]

# named outdoor places, where passers-by walk to
SPACES = {
    "arrival": {"id": "arrival", "name": "Arrival Plaza", "x": 7.4, "y": 15.35},
    "courtyard": {"id": "courtyard", "name": "Academic Courtyard", "x": 20.1, "y": 12.75},
    "terrace": {"id": "terrace", "name": "Cafe Terrace", "x": 17.55, "y": 14.25},
    "service": {"id": "service", "name": "Service Lane", "x": 8.4, "y": 18.25},
    "foodCourt": {"id": "foodCourt", "name": "Food Court", "x": 28.2, "y": 19.55},
    "lawn": {"id": "lawn", "name": "Student Lawn", "x": 35.5, "y": 19.9},
    "promenade": {"id": "promenade", "name": "Beach Promenade", "x": 30.5, "y": 22.15},
    "eventSquare": {"id": "eventSquare", "name": "Event Square", "x": 20.5, "y": 21.35},
}


# ---- the rooms --------------------------------------------------------------------
# areas: labelled floor areas. solid: furniture. route: the marked way in.
# activities: where people stand or sit in the room, and what they do there.

INTERIORS = {
    "academy": {
        "name": "Academic Wing",
        "areas": [
            {"id": "service", "label": "Snack Stand", "x": 5.65, "y": 2.15, "w": 4.3, "h": 0.85, "color": "#ff7b5b"},
            {"id": "study", "label": "Study Commons", "x": 1.7, "y": 5.25, "w": 4.4, "h": 3.9, "color": "#d2a66c"},
            {"id": "quiet", "label": "Quiet Tables", "x": 9.25, "y": 3.7, "w": 3.75, "h": 3.1, "color": "#64cbc8"},
        ],
        "solid": [
            {"id": "stand-counter", "x": 5.65, "y": 2.15, "w": 4.3, "h": 0.85, "label": "Snack stand counter", "kind": "counter"},
            {"id": "pastry-display", "x": 5.8, "y": 3.05, "w": 1.15, "h": 0.65, "label": "Display", "kind": "counter"},
            {"id": "academy-table-west", "x": 2.1, "y": 5.65, "w": 3.5, "h": 0.75, "label": "Communal table", "kind": "furniture"},
            {"id": "academy-table-east", "x": 9.9, "y": 4.2, "w": 3, "h": 0.75, "label": "Quiet study table", "kind": "furniture"},
            {"id": "academy-lounge", "x": 2.2, "y": 7.25, "w": 2.5, "h": 1.85, "label": "Study lounge", "kind": "furniture"},
            {"id": "academy-plant", "r": 0.38, "x": 11.8, "y": 7.2, "label": "Planter", "kind": "prop"},
        ],
        "route": [{"x": 7.5, "y": 8.8}, {"x": 7.5, "y": 7.25}, {"x": 7.2, "y": 5.7}, {"x": 7.25, "y": 4.15}],
        "activities": [
            {"x": 7.25, "y": 3.6, "pose": "service", "role": "service", "facing": {"x": 0, "y": -1}, "label": "Serving"},
            {"x": 7.2, "y": 4.25, "pose": "phone", "facing": {"x": 0, "y": -1}, "label": "Ordering"},
            {"x": 6.75, "y": 4.72, "pose": "idle", "facing": {"x": 0.4, "y": -1}, "label": "Queueing"},
            {"x": 4.7, "y": 6.55, "pose": "sit", "facing": {"x": 1, "y": -0.2}, "label": "Eating"},
            {"x": 10.65, "y": 5.25, "pose": "sit", "facing": {"x": -1, "y": 0.2}, "label": "Studying"},
            {"x": 4.9, "y": 7.65, "pose": "chat", "facing": {"x": -1, "y": 0}, "label": "Group study"},
        ],
    },
    "mercado": {
        "name": "Mercado Supply Hall",
        "areas": [
            {"id": "stock", "label": "Dry Stock", "x": 1.65, "y": 1.8, "w": 4.9, "h": 5.8, "color": "#f5c95e"},
            {"id": "dispatch", "label": "Order & Dispatch", "x": 5.9, "y": 3.45, "w": 3.3, "h": 2.2, "color": "#ff8060"},
            {"id": "cold", "label": "Cold Storage", "x": 9.35, "y": 1.7, "w": 3.85, "h": 3.2, "color": "#64cbc8"},
        ],
        "solid": [
            {"id": "shelf-north", "x": 2.05, "y": 2.45, "w": 4, "h": 0.62, "label": "Market shelving", "kind": "furniture"},
            {"id": "shelf-west", "x": 2.1, "y": 6.55, "w": 3.6, "h": 0.62, "label": "Market shelving", "kind": "furniture"},
            {"id": "cold-room", "x": 9.7, "y": 2.05, "w": 3.15, "h": 2.25, "label": "Cold store", "kind": "room"},
            {"id": "shelf-east", "x": 10.1, "y": 6.1, "w": 2.8, "h": 0.62, "label": "Market shelving", "kind": "furniture"},
            {"id": "supply-counter", "x": 6.4, "y": 3.78, "w": 2.2, "h": 0.82, "label": "Supply desk", "kind": "counter"},
            {"id": "mercado-plant", "r": 0.35, "x": 7.6, "y": 7.7, "label": "Planter", "kind": "prop"},
        ],
        "route": [{"x": 7.5, "y": 8.8}, {"x": 8.45, "y": 8.25}, {"x": 8.45, "y": 6.4}, {"x": 7.55, "y": 5.45}, {"x": 7.5, "y": 5.02}],
        "activities": [
            {"x": 7.45, "y": 3.5, "pose": "service", "role": "service", "facing": {"x": 0, "y": 1}, "label": "Preparing order"},
            {"x": 7.5, "y": 4.9, "pose": "phone", "facing": {"x": 0, "y": -1}, "label": "Confirming order"},
            {"x": 6.95, "y": 5.35, "pose": "idle", "facing": {"x": 0.3, "y": -1}, "label": "Waiting"},
            {"x": 4.75, "y": 3.55, "pose": "browse", "facing": {"x": -1, "y": -0.3}, "label": "Checking stock"},
            {"x": 10.3, "y": 5.35, "pose": "browse", "facing": {"x": 0.5, "y": -1}, "label": "Restocking"},
            {"x": 4.9, "y": 7.55, "pose": "repair", "role": "technician", "facing": {"x": -1, "y": -0.2}, "label": "Moving crates"},
        ],
    },
    "hub": {
        "name": "Student Hub",
        "areas": [
            {"id": "venture", "label": "Venture Studio", "x": 8.45, "y": 2.4, "w": 4.6, "h": 3.5, "color": "#bce65f"},
            {"id": "social", "label": "Student Lounge", "x": 1.65, "y": 6.15, "w": 11.4, "h": 3.15, "color": "#9a7bc1"},
        ],
        "solid": [
            {"id": "venture-desk", "x": 9.55, "y": 4.78, "w": 1.9, "h": 0.82, "label": "Venture desk", "kind": "counter"},
            {"id": "hub-lounge-west", "x": 2.15, "y": 7, "w": 2.5, "h": 1.85, "label": "Student lounge", "kind": "furniture"},
            {"id": "hub-lounge-east", "x": 9.8, "y": 6.1, "w": 2.5, "h": 1.85, "label": "Student lounge", "kind": "furniture"},
            {"id": "hub-plant", "r": 0.38, "x": 7.8, "y": 6.9, "label": "Planter", "kind": "prop"},
        ],
        "route": [{"x": 7.5, "y": 8.8}, {"x": 6.8, "y": 8.25}, {"x": 6.55, "y": 6.7}, {"x": 6.65, "y": 5.65}],
        "activities": [
            {"x": 10.45, "y": 4.45, "pose": "phone", "facing": {"x": 0, "y": 1}, "label": "Reviewing finances"},
            {"x": 4.8, "y": 7.7, "pose": "sit", "facing": {"x": -1, "y": 0}, "label": "Student club meeting"},
            {"x": 9.25, "y": 8.35, "pose": "chat", "facing": {"x": 1, "y": -0.2}, "label": "Networking"},
        ],
    },
}


# ---- solid objects, in one format for the movement code ----------------------------

def _rect(cid, x, y, width, height, label, kind):
    return {"id": cid, "shape": "rect", "x": x, "y": y, "width": width, "height": height, "label": label, "kind": kind}


def _circle(cid, x, y, radius, label, kind):
    return {"id": cid, "shape": "circle", "x": x, "y": y, "radius": radius, "label": label, "kind": kind}


def _campus_colliders():
    solid = [_rect(b["id"], b["x"], b["y"], b["w"], b["h"], b["label"], "building") for b in BUILDINGS.values()]
    solid += [
        _rect(p["id"], p["x"] + 0.04, p["y"] + 0.04, p["w"] - 0.08, p["h"] - 0.08, "Facade planter", "prop")
        for p in PLANTERS
    ]
    solid += [
        _rect("sunset-forum", 18.35, 22.08, 4.3, 2.25, "Sunset Forum", "venue"),
        _rect("arrival-bench-west", 5.05, 16.1, 1.4, 0.42, "Bench", "prop"),
        _rect("arrival-bench-east", 9.45, 14.72, 1.4, 0.42, "Bench", "prop"),
        _rect("arrival-planter", 10.55, 15.3, 0.55, 1.2, "Planter", "prop"),
        _rect("courtyard-bench-west", 13.35, 11.8, 1.4, 0.42, "Bench", "prop"),
        _rect("courtyard-bench-east", 24.8, 11.75, 1.4, 0.42, "Bench", "prop"),
        _rect("terrace-pergola", 14.05, 14.35, 2.25, 1.35, "Pergola", "prop"),
        _rect("terrace-planter", 13.72, 15.88, 7.75, 0.42, "Terrace planter", "prop"),
        _rect("food-pergola-west", 24.65, 17.75, 3.05, 1.15, "Food court canopy", "prop"),
        _rect("food-pergola-east", 28.25, 17.75, 3.25, 1.15, "Food court canopy", "prop"),
        _rect("lawn-planter", 38.4, 17.55, 0.48, 4.15, "Lawn planter", "prop"),
    ]
    solid += [_circle(f"terrace-table-{i}", x, y, 0.36, "Terrace table", "prop") for i, (x, y) in enumerate(TERRACE_TABLES)]
    solid += [_circle(f"tree-{i}", x, y, 0.27, "Palm tree", "prop") for i, (x, y, _) in enumerate(TREES)]
    return solid


def _room_colliders(zone_id):
    solid = [
        _rect("north-wall", 0, 0, 15, 1, "Wall", "wall"),
        _rect("west-wall", 0, 0, 1, 12, "Wall", "wall"),
    ]
    for item in INTERIORS[zone_id]["solid"]:
        if "r" in item:
            solid.append(_circle(item["id"], item["x"], item["y"], item["r"], item["label"], item["kind"]))
        else:
            solid.append(_rect(item["id"], item["x"], item["y"], item["w"], item["h"], item["label"], item["kind"]))
    return solid


def colliders(zone_id):
    """Everything solid in one zone."""
    return _campus_colliders() if zone_id == "campus" else _room_colliders(zone_id)


def start_player():
    """Where a new run starts."""
    spawn = ZONES[START_ZONE]["spawn"]
    return {"zone": START_ZONE, "x": float(spawn["x"]), "y": float(spawn["y"])}


def world_view():
    """The whole world for the browser (GET /api/world)."""
    return {
        "zones": ZONES,
        "locations": LOCATIONS,
        "colliders": {zone_id: colliders(zone_id) for zone_id in ZONES},
        "buildings": BUILDINGS,
        "planters": PLANTERS,
        "trees": TREES,
        "spaces": SPACES,
        "interiors": INTERIORS,
    }
