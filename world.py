"""The campus as data: the zone, the Nova building, solid objects and the room layout.

No rules, no database and no drawing in this file. The browser reads all of it
from GET /api/world and only draws it. logic.py uses the zones to check where the
player may stand.

There is one zone, the campus. The Nova is a building on it: the player walks in
through its entrance and the browser fades the roof out (spec walk-in).

Units are map tiles, not money, so plain numbers are fine here.
The layout comes from Felix Antes' project Nova Beach Ventures
(https://github.com/felix-anthes-png/nova-beach-ventures), without its shops.
"""

START_ZONE = "campus"


# ---- zones -----------------------------------------------------------------------
# width/height: size of the drawn ground. minX..maxY: where a person may walk.
# minY reaches up to the north wall of the Nova (the ground behind it is fenced off).

ZONES = {
    "campus": {
        "id": "campus", "name": "Nova Coast Campus", "sub": "CARCAVELOS OUTDOORS",
        "width": 90, "height": 30, "minX": 1, "maxX": 41, "minY": 1.0, "maxY": 25.7,
        "outdoor": True, "spawn": {"x": 21, "y": 18},
    },
}


# ---- places the player can use with E or a click ---------------------------------
# kind "panel" opens a screen in the browser ("action"). The three desks stand in the
# atrium of the Nova. There are no doors: the Nova is entered by walking in.

LOCATIONS = {
    "supplier": {
        "zone": "campus", "x": 20.7, "y": 4.1, "kind": "panel", "action": "stock", "label": "Order stock",
        "color": "#f5c95e", "title": "SUPPLY DESK", "sub": "ORDER DESK",
    },
    "stand": {
        "zone": "campus", "x": 15.4, "y": 4.4, "kind": "panel", "action": "prices", "label": "Set your prices",
        "color": "#ff7b5b", "title": "CAFE COUNTER", "sub": "CAFE",
    },
    "board": {
        "zone": "campus", "x": 23.7, "y": 4.1, "kind": "panel", "action": "dashboard", "label": "Open the dashboard",
        "color": "#67b7d1", "title": "STUDENT CENTRAL", "sub": "RESULTS",
    },
}


# ---- the outdoor campus -----------------------------------------------------------

BUILDINGS = {
    "library": {"id": "learning-center", "x": 2.2, "y": 3.25, "w": 8.4, "h": 5.15, "label": "Learning Center"},
    "mercado": {"id": "mercado-building", "x": 3.15, "y": 8.85, "w": 8.25, "h": 4.45, "label": "Mercado Supply Hall"},
}

PLANTERS = [
    {"id": "academic-planter-west", "x": 13.1, "y": 9.45, "w": 6.9, "h": 0.62, "z": 13},
    {"id": "academic-planter-east", "x": 26.0, "y": 9.45, "w": 6.9, "h": 0.62, "z": 13},
    {"id": "library-planter", "x": 3.05, "y": 8.58, "w": 2.55, "h": 0.55, "z": 12},
    {"id": "mercado-planter", "x": 4.05, "y": 13.36, "w": 2.35, "h": 0.52, "z": 11},
]

# palm trees: x, y, size
TREES = [
    [2, 8, 0.9], [5, 14, 0.8], [11, 19, 0.82], [14, 22, 0.9], [25, 12, 0.76], [29, 19, 0.88],
    [37, 9, 0.83], [39, 12, 0.92], [37, 19, 0.8], [6, 21, 0.75], [24, 22, 0.72], [40, 21, 0.86],
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


# ---- the Nova ----------------------------------------------------------------------
# One big building north of the courtyard, where the three academic wings stood.
# parts: the footprint, three joined blocks (z = wall height in drawing units).
# walls: wall pieces as solid rectangles, written with the openings left out.
# entrances: the openings in the walls.
# Stylised after the real Nova SBE in Carcavelos (white volumes, flat roofs, a glass-roofed
# atrium in the middle). The whole floor inside is open to walk on.

NOVA = {
    "id": "nova", "label": "Nova", "wall": 0.5,
    "parts": [
        {"id": "west", "x": 11.5, "y": 1.2, "w": 7.5, "h": 8.0, "z": 78},
        {"id": "atrium", "x": 19.0, "y": 1.2, "w": 8.0, "h": 8.0, "z": 96, "glassRoof": True},
        {"id": "east", "x": 27.0, "y": 1.2, "w": 6.5, "h": 8.0, "z": 78},
    ],
    "walls": [
        {"id": "nova-north-wall", "x": 11.5, "y": 1.2, "w": 22.0, "h": 0.5, "side": "north"},
        {"id": "nova-west-wall", "x": 11.5, "y": 1.2, "w": 0.5, "h": 8.0, "side": "west"},
        {"id": "nova-east-wall", "x": 33.0, "y": 1.2, "w": 0.5, "h": 8.0, "side": "east"},
        {"id": "nova-south-wall-west", "x": 11.5, "y": 8.7, "w": 9.5, "h": 0.5, "side": "south"},
        {"id": "nova-south-wall-east", "x": 25.0, "y": 8.7, "w": 8.5, "h": 0.5, "side": "south"},
    ],
    "entrances": [{"id": "main", "x": 21.0, "y": 8.7, "width": 4.0, "side": "south"}],
}

# ---- the rooms inside the Nova -----------------------------------------------------
# Keyed by the zone they are in: the only rooms are those inside the Nova on the campus.
# areas: the floor, split into labelled places (together they cover all of it); labelAt is
# where the name is written on the floor.
# solid: furniture, placed so that wide aisles stay open everywhere. Counters and shelves
# stand against the north and west walls, where the camera sees their fronts.
# route: the marked way in. activities: where people stand or sit, and what they do there.
# Cafe, Merchandise and the Print Corner are places only: no rule works there yet.

INTERIORS = {
    "campus": {
        "name": "Nova",
        "floor": "#e9e7e1",
        "areas": [
            {"id": "cafe", "label": "Cafe", "x": 12.0, "y": 1.7, "w": 7.0, "h": 7.0, "color": "#ff7b5b", "labelAt": {"x": 12.4, "y": 4.7}},
            {"id": "atrium", "label": "Atrium", "x": 19.0, "y": 1.7, "w": 8.0, "h": 7.0, "color": "#64cbc8", "labelAt": {"x": 19.4, "y": 5.0}},
            {"id": "merch", "label": "Merchandise", "x": 27.0, "y": 1.7, "w": 6.0, "h": 3.3, "color": "#bce65f", "labelAt": {"x": 27.6, "y": 3.1}},
            {"id": "print", "label": "Print Corner", "x": 27.0, "y": 5.0, "w": 6.0, "h": 3.7, "color": "#9a7bc1", "labelAt": {"x": 27.5, "y": 5.85}},
        ],
        "solid": [
            # Every gap between two pieces is either shut (at most 0.5, less than a person) or at least
            # 1.4 wide, so that walking by hand and clicking to walk both find their way.
            # cafe: shelves and counter against the north wall (the barista stands between them), tables
            {"id": "cafe-shelf", "x": 12.5, "y": 1.7, "w": 6.5, "h": 0.6, "label": "Cafe shelves", "kind": "furniture"},
            {"id": "cafe-counter", "x": 12.5, "y": 2.8, "w": 6.5, "h": 0.85, "label": "Cafe counter", "kind": "counter"},
            {"id": "cafe-table-1", "x": 12.5, "y": 5.4, "w": 1.8, "h": 0.7, "label": "Cafe table", "kind": "furniture"},
            {"id": "cafe-table-2", "x": 14.8, "y": 5.4, "w": 1.8, "h": 0.7, "label": "Cafe table", "kind": "furniture"},
            {"id": "cafe-table-3", "x": 13.4, "y": 7.55, "w": 1.8, "h": 0.7, "label": "Cafe table", "kind": "furniture"},
            {"id": "cafe-table-4", "x": 15.6, "y": 7.55, "w": 1.8, "h": 0.7, "label": "Cafe table", "kind": "furniture"},
            {"id": "cafe-plant-west", "r": 0.38, "x": 12.65, "y": 8.15, "label": "Planter", "kind": "prop"},
            # atrium: the two desks under the gallery, the staircase, benches and planters
            {"id": "supply-counter", "x": 19.45, "y": 2.2, "w": 2.25, "h": 0.85, "label": "Supply desk", "kind": "counter"},
            {"id": "student-counter", "x": 22.2, "y": 2.2, "w": 3.0, "h": 0.85, "label": "Student Central", "kind": "counter"},
            {"id": "staircase", "x": 25.2, "y": 1.9, "w": 1.5, "h": 2.9, "label": "Staircase", "kind": "furniture"},
            {"id": "atrium-bench-west", "x": 19.5, "y": 5.9, "w": 1.8, "h": 0.5, "label": "Bench", "kind": "furniture"},
            {"id": "atrium-bench-east", "x": 24.7, "y": 5.9, "w": 1.8, "h": 0.5, "label": "Bench", "kind": "furniture"},
            {"id": "atrium-plant-west", "r": 0.45, "x": 19.6, "y": 8.2, "label": "Planter", "kind": "prop"},
            {"id": "atrium-plant-east", "r": 0.45, "x": 25.9, "y": 8.2, "label": "Planter", "kind": "prop"},
            {"id": "column-west-1", "r": 0.18, "x": 19.0, "y": 3.2, "label": "Column", "kind": "prop"},
            {"id": "column-west-2", "r": 0.18, "x": 19.0, "y": 7.6, "label": "Column", "kind": "prop"},
            {"id": "column-east-1", "r": 0.18, "x": 27.0, "y": 5.3, "label": "Column", "kind": "prop"},
            {"id": "column-east-2", "r": 0.18, "x": 27.0, "y": 8.1, "label": "Column", "kind": "prop"},
            # merchandise: a shelf wall on the north wall, a display table and a rack on the east wall
            {"id": "merch-shelf", "x": 27.2, "y": 1.7, "w": 5.3, "h": 0.5, "label": "Merchandise shelf", "kind": "furniture"},
            {"id": "merch-table", "x": 28.2, "y": 3.7, "w": 1.9, "h": 0.8, "label": "Display table", "kind": "furniture"},
            {"id": "merch-rack", "x": 31.5, "y": 3.5, "w": 1.5, "h": 0.6, "label": "Merchandise rack", "kind": "furniture"},
            # print corner: three printers in a row, a planter closes the row
            {"id": "printer-1", "x": 28.4, "y": 6.9, "w": 0.9, "h": 0.7, "label": "Printer", "kind": "prop"},
            {"id": "printer-2", "x": 29.8, "y": 6.9, "w": 0.9, "h": 0.7, "label": "Printer", "kind": "prop"},
            {"id": "printer-3", "x": 31.2, "y": 6.9, "w": 0.9, "h": 0.7, "label": "Printer", "kind": "prop"},
            {"id": "print-plant", "r": 0.4, "x": 32.55, "y": 7.25, "label": "Planter", "kind": "prop"},
        ],
        "route": [{"x": 23.0, "y": 8.4}, {"x": 23.0, "y": 5.8}, {"x": 23.7, "y": 4.1}],
        "activities": [
            {"x": 14.8, "y": 2.52, "pose": "service", "role": "service", "facing": {"x": 0, "y": 1}, "label": "Serving coffee"},
            {"x": 13.9, "y": 4.4, "pose": "phone", "facing": {"x": 0.3, "y": -1}, "label": "Ordering"},
            {"x": 13.8, "y": 6.6, "pose": "sit", "facing": {"x": 0.2, "y": -1}, "label": "Eating"},
            {"x": 15.3, "y": 6.6, "pose": "sit", "facing": {"x": -0.2, "y": -1}, "label": "Studying"},
            {"x": 23.7, "y": 1.97, "pose": "service", "role": "service", "facing": {"x": 0, "y": 1}, "label": "Helping a student"},
            {"x": 22.0, "y": 7.2, "pose": "chat", "facing": {"x": 1, "y": 0}, "label": "Meeting"},
            {"x": 29.4, "y": 2.95, "pose": "browse", "facing": {"x": 0, "y": -1}, "label": "Browsing"},
            {"x": 31.6, "y": 4.6, "pose": "browse", "facing": {"x": 0, "y": -1}, "label": "Looking at shirts"},
            {"x": 30.0, "y": 6.2, "pose": "repair", "role": "technician", "facing": {"x": 0, "y": 1}, "label": "Refilling paper"},
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
    return solid + _nova_colliders()


def _nova_colliders():
    solid = [_rect(wall["id"], wall["x"], wall["y"], wall["w"], wall["h"], "Wall", "wall") for wall in NOVA["walls"]]
    for item in INTERIORS["campus"]["solid"]:
        if "r" in item:
            solid.append(_circle(item["id"], item["x"], item["y"], item["r"], item["label"], item["kind"]))
        else:
            solid.append(_rect(item["id"], item["x"], item["y"], item["w"], item["h"], item["label"], item["kind"]))
    # nobody walks behind the buildings: the ground north of y 7.5 is closed off beside the Nova
    solid += [
        _rect("north-west-fence", 0, 0, 11.5, 7.5, "Fence", "boundary"),
        _rect("north-east-fence", 33.5, 0, 10.5, 7.5, "Fence", "boundary"),
    ]
    return solid


def colliders(zone_id):
    """Everything solid in one zone: the buildings, the walls and furniture of the Nova, the props."""
    if zone_id not in ZONES:
        raise KeyError(zone_id)
    return _campus_colliders()


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
        "nova": NOVA,
        "interiors": INTERIORS,
    }
