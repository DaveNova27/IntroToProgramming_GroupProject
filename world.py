"""The campus as data: the zone, the Nova building, solid objects and the room layout.

No rules, no database and no drawing in this file. The browser reads all of it
from GET /api/world and only draws it. logic.py uses the zones to check where the
player may stand.

There is one zone, the campus. The Nova is a building on it: the player walks in
through its entrance and the browser fades the roof out (spec walk-in). The Nova has
four wings, each with its own roof (spec nova-wings).

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
        "width": 90, "height": 48, "minX": 1, "maxX": 41, "minY": 1.0, "maxY": 34.7,
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
# The Learning Center and the Mercado are wings of the Nova now (see NOVA below).

PLANTERS = [
    {"id": "academic-planter-west", "x": 13.1, "y": 9.45, "w": 6.9, "h": 0.62, "z": 13},
    {"id": "academic-planter-east", "x": 26.0, "y": 9.45, "w": 1.4, "h": 0.62, "z": 13},
]

# palm trees: x, y, size
TREES = [
    [1.9, 14.4, 0.85], [5, 14, 0.8], [25, 12, 0.76], [37, 19, 0.8], [23.4, 21.6, 0.72],
    [40, 21, 0.86],
    # spec nova-zones: a palm each side of the start of the beach way, two near the Dorm
    [10.4, 18.9, 0.9], [18.8, 18.5, 0.84], [34.4, 15.2, 0.8], [40.4, 15.0, 0.88],
    # and a few on the promenade, between the paving and the dunes
    [4.4, 22.3, 0.92], [22.9, 20.9, 0.84], [35.0, 22.6, 0.9],
]

TERRACE_TABLES = [
    [14.7, 14.95], [17.1, 14.7], [19.15, 15.25], [20.65, 14.55],
]

# named outdoor places, where passers-by walk to
SPACES = {
    "arrival": {"id": "arrival", "name": "Arrival Plaza", "x": 7.4, "y": 15.35},
    "courtyard": {"id": "courtyard", "name": "Academic Courtyard", "x": 20.1, "y": 12.75},
    "terrace": {"id": "terrace", "name": "Cafe Terrace", "x": 17.55, "y": 14.25},
    "service": {"id": "service", "name": "Service Lane", "x": 1.9, "y": 11.0},
    "beachCafe": {"id": "beachCafe", "name": "Beach Cafe", "x": 28.2, "y": 27.4},
    "surfShop": {"id": "surfShop", "name": "Surf Shop", "x": 8.6, "y": 27.55},
    "beachWay": {"id": "beachWay", "name": "Beach Way", "x": 14.4, "y": 21.0},
    "fireside": {"id": "fireside", "name": "Fire Pit", "x": 22.8, "y": 30.9},
    "shore": {"id": "shore", "name": "Shore", "x": 19.0, "y": 34.0},
    "court": {"id": "court", "name": "Volleyball Court", "x": 38.0, "y": 33.2},
    "dorm": {"id": "dorm", "name": "Dorm", "x": 38.0, "y": 13.9},
    "lawn": {"id": "lawn", "name": "Student Lawn", "x": 35.5, "y": 19.9},
    "promenade": {"id": "promenade", "name": "Beach Promenade", "x": 30.5, "y": 22.15},
    "eventSquare": {"id": "eventSquare", "name": "Event Square", "x": 20.5, "y": 21.35},
}


# ---- the Nova ----------------------------------------------------------------------
# One big building north of the courtyard, made of four wings (spec nova-wings), each with
# its own roof:
#   nova             the main block: Cafe, atrium with a gallery, Merchandise, Print Corner
#   learning-center  west of it, joined to its west wall: the Study Hall
#   mercado          south of the Learning Center, a finger pointing south: the Supply Hall
#   hub              south of the Nova's east part, a finger pointing south: the Student Hub
# parts: the footprint, joined blocks (z = wall height in drawing units), each of one wing.
# walls: wall pieces as solid rectangles, written with the openings left out. side: which
#   side of its wing the wall is on. hides: the wings that stand behind this wall, seen from
#   the camera (it sinks while one of them is open); a front wall hides its own wing.
# entrances: the openings from outside. openings: the openings between two wings. Both are
#   gaps in the walls, at least 2 tiles wide; side tells along which axis they run.
# wings: fadesWith lists the wings that stand behind this one, seen from the camera: this
#   roof fades too while the player is in one of them, or it would hide them.
# Stylised after the real Nova SBE in Carcavelos (white volumes, flat roofs, a glass-roofed
# atrium in the middle). The whole floor inside is open to walk on.

NOVA = {
    "id": "nova", "label": "Nova", "wall": 0.5,
    "wings": [
        {"id": "nova", "label": "Nova", "fadesWith": ["learning-center"]},
        {"id": "learning-center", "label": "Learning Center", "fadesWith": []},
        {"id": "mercado", "label": "Mercado Supply Hall", "fadesWith": ["learning-center"]},
        {"id": "hub", "label": "Student Hub", "fadesWith": ["nova"]},
    ],
    "parts": [
        {"id": "west", "wing": "nova", "x": 11.5, "y": 1.2, "w": 7.5, "h": 8.0, "z": 78},
        {"id": "atrium", "wing": "nova", "x": 19.0, "y": 1.2, "w": 8.0, "h": 8.0, "z": 96, "glassRoof": True},
        {"id": "east", "wing": "nova", "x": 27.0, "y": 1.2, "w": 6.5, "h": 8.0, "z": 78},
        {"id": "learning-center", "wing": "learning-center", "x": 2.2, "y": 3.25, "w": 9.3, "h": 5.4, "z": 73},
        {"id": "mercado", "wing": "mercado", "x": 3.15, "y": 8.15, "w": 8.35, "h": 5.15, "z": 58},
        {"id": "hub", "wing": "hub", "x": 27.5, "y": 9.2, "w": 6.0, "h": 5.0, "z": 56},
    ],
    "walls": [
        # the Nova
        {"id": "nova-north-wall", "wing": "nova", "x": 11.5, "y": 1.2, "w": 22.0, "h": 0.5, "side": "north"},
        {"id": "nova-west-wall-north", "wing": "nova", "x": 11.5, "y": 1.2, "w": 0.5, "h": 2.55, "side": "west", "hides": ["learning-center"]},
        {"id": "nova-west-wall-south", "wing": "nova", "x": 11.5, "y": 5.75, "w": 0.5, "h": 3.45, "side": "west", "hides": ["learning-center"]},
        {"id": "nova-east-wall", "wing": "nova", "x": 33.0, "y": 1.2, "w": 0.5, "h": 8.0, "side": "east"},
        {"id": "nova-south-wall-west", "wing": "nova", "x": 11.5, "y": 8.7, "w": 9.5, "h": 0.5, "side": "south"},
        {"id": "nova-south-wall-east-1", "wing": "nova", "x": 25.0, "y": 8.7, "w": 4.5, "h": 0.5, "side": "south"},
        {"id": "nova-south-wall-east-2", "wing": "nova", "x": 31.5, "y": 8.7, "w": 2.0, "h": 0.5, "side": "south"},
        # the Learning Center (its south wall is the Mercado's north wall)
        {"id": "lc-north-wall", "wing": "learning-center", "x": 2.2, "y": 3.25, "w": 9.3, "h": 0.5, "side": "north"},
        {"id": "lc-west-wall", "wing": "learning-center", "x": 2.2, "y": 3.25, "w": 0.5, "h": 5.4, "side": "west"},
        {"id": "lc-south-wall-west", "wing": "learning-center", "x": 2.2, "y": 8.15, "w": 4.3, "h": 0.5, "side": "south"},
        {"id": "lc-south-wall-east", "wing": "learning-center", "x": 8.5, "y": 8.15, "w": 3.0, "h": 0.5, "side": "south"},
        # the Mercado
        {"id": "mercado-west-wall", "wing": "mercado", "x": 3.15, "y": 8.65, "w": 0.5, "h": 4.65, "side": "west"},
        {"id": "mercado-east-wall", "wing": "mercado", "x": 11.0, "y": 8.65, "w": 0.5, "h": 4.65, "side": "east"},
        {"id": "mercado-south-wall-west", "wing": "mercado", "x": 3.15, "y": 12.8, "w": 3.35, "h": 0.5, "side": "south"},
        {"id": "mercado-south-wall-east", "wing": "mercado", "x": 8.5, "y": 12.8, "w": 3.0, "h": 0.5, "side": "south"},
        # the Student Hub (its north wall is the Nova's south wall)
        {"id": "hub-west-wall", "wing": "hub", "x": 27.5, "y": 9.2, "w": 0.5, "h": 5.0, "side": "west"},
        {"id": "hub-east-wall", "wing": "hub", "x": 33.0, "y": 9.2, "w": 0.5, "h": 5.0, "side": "east"},
        {"id": "hub-south-wall-west", "wing": "hub", "x": 27.5, "y": 13.7, "w": 2.0, "h": 0.5, "side": "south"},
        {"id": "hub-south-wall-east", "wing": "hub", "x": 31.5, "y": 13.7, "w": 2.0, "h": 0.5, "side": "south"},
    ],
    "entrances": [
        {"id": "main", "wing": "nova", "x": 21.0, "y": 8.7, "width": 4.0, "side": "south"},
        {"id": "mercado", "wing": "mercado", "x": 6.5, "y": 12.8, "width": 2.0, "side": "south"},
        {"id": "hub", "wing": "hub", "x": 29.5, "y": 13.7, "width": 2.0, "side": "south"},
    ],
    "openings": [
        {"id": "nova-learning-center", "x": 11.5, "y": 3.75, "width": 2.0, "side": "west", "between": ["learning-center", "nova"]},
        {"id": "learning-center-mercado", "x": 6.5, "y": 8.15, "width": 2.0, "side": "south", "between": ["learning-center", "mercado"]},
        {"id": "nova-hub", "x": 29.5, "y": 8.7, "width": 2.0, "side": "south", "between": ["nova", "hub"]},
    ],
}

# ---- the rooms inside the Nova -----------------------------------------------------
# Keyed by the zone they are in: the only rooms are those inside the Nova on the campus.
# Every entry belongs to a wing ("wing"). areas: the floor of each wing, split into labelled
# places (together they cover all of it); labelAt is where the name is written on the floor.
# solid: furniture, placed so that wide aisles stay open everywhere. Counters and shelves
# stand against the north and west walls, where the camera sees their fronts.
# route: the marked way in. activities: where people stand or sit, and what they do there.
# Every place is a place only: no rule works there yet.

INTERIORS = {
    "campus": {
        "name": "Nova",
        "floor": "#e9e7e1",
        "areas": [
            # the Nova
            {"id": "cafe", "wing": "nova", "label": "Cafe", "x": 12.0, "y": 1.7, "w": 7.0, "h": 7.0, "color": "#ff7b5b", "labelAt": {"x": 12.4, "y": 4.7}},
            {"id": "atrium", "wing": "nova", "label": "Atrium", "x": 19.0, "y": 1.7, "w": 8.0, "h": 7.0, "color": "#64cbc8", "labelAt": {"x": 19.4, "y": 5.0}},
            {"id": "merch", "wing": "nova", "label": "Merchandise", "x": 27.0, "y": 1.7, "w": 6.0, "h": 3.3, "color": "#bce65f", "labelAt": {"x": 27.6, "y": 3.1}},
            {"id": "print", "wing": "nova", "label": "Print Corner", "x": 27.0, "y": 5.0, "w": 6.0, "h": 3.7, "color": "#9a7bc1", "labelAt": {"x": 27.5, "y": 5.85}},
            # the Learning Center
            {"id": "study", "wing": "learning-center", "label": "Study Hall", "x": 2.7, "y": 3.75, "w": 5.8, "h": 4.4, "color": "#64cbc8", "labelAt": {"x": 3.7, "y": 7.55}},
            {"id": "seminar", "wing": "learning-center", "label": "Seminar", "x": 8.5, "y": 3.75, "w": 3.0, "h": 4.4, "color": "#9a7bc1", "labelAt": {"x": 8.8, "y": 5.05}},
            # the Mercado
            {"id": "supply", "wing": "mercado", "label": "Supply Hall", "x": 3.65, "y": 8.65, "w": 7.35, "h": 4.15, "color": "#f5c95e", "labelAt": {"x": 6.5, "y": 10.9}},
            # the Student Hub
            {"id": "lounge", "wing": "hub", "label": "Lounge", "x": 28.0, "y": 9.2, "w": 5.0, "h": 2.9, "color": "#ff7b5b", "labelAt": {"x": 29.2, "y": 11.7}},
            {"id": "meeting", "wing": "hub", "label": "Meeting Room", "x": 28.0, "y": 12.1, "w": 5.0, "h": 1.6, "color": "#64cbc8", "labelAt": {"x": 30.0, "y": 12.5}},
        ],
        "solid": [
            # Every gap between two pieces is either shut (at most 0.5, less than a person) or at
            # least 1.4 wide, so that walking by hand and clicking to walk both find their way.
            # ---- the Nova ----
            # cafe: shelves and counter against the north wall (the barista stands between them), tables
            {"id": "cafe-shelf", "wing": "nova", "x": 12.5, "y": 1.7, "w": 6.5, "h": 0.6, "label": "Cafe shelves", "kind": "furniture"},
            {"id": "cafe-counter", "wing": "nova", "x": 12.5, "y": 2.8, "w": 6.5, "h": 0.85, "label": "Cafe counter", "kind": "counter"},
            {"id": "cafe-table-1", "wing": "nova", "x": 12.5, "y": 5.4, "w": 1.8, "h": 0.7, "label": "Cafe table", "kind": "furniture"},
            {"id": "cafe-table-2", "wing": "nova", "x": 14.8, "y": 5.4, "w": 1.8, "h": 0.7, "label": "Cafe table", "kind": "furniture"},
            {"id": "cafe-table-3", "wing": "nova", "x": 13.4, "y": 7.55, "w": 1.8, "h": 0.7, "label": "Cafe table", "kind": "furniture"},
            {"id": "cafe-table-4", "wing": "nova", "x": 15.6, "y": 7.55, "w": 1.8, "h": 0.7, "label": "Cafe table", "kind": "furniture"},
            {"id": "cafe-plant-west", "wing": "nova", "r": 0.38, "x": 12.65, "y": 8.15, "label": "Planter", "kind": "prop"},
            # atrium: the two desks under the gallery, the staircase, benches and planters
            {"id": "supply-counter", "wing": "nova", "x": 19.45, "y": 2.2, "w": 2.25, "h": 0.85, "label": "Supply desk", "kind": "counter"},
            {"id": "student-counter", "wing": "nova", "x": 22.2, "y": 2.2, "w": 3.0, "h": 0.85, "label": "Student Central", "kind": "counter"},
            {"id": "staircase", "wing": "nova", "x": 25.2, "y": 1.9, "w": 1.5, "h": 2.9, "label": "Staircase", "kind": "furniture"},
            {"id": "atrium-bench-west", "wing": "nova", "x": 19.5, "y": 5.9, "w": 1.8, "h": 0.5, "label": "Bench", "kind": "furniture"},
            {"id": "atrium-bench-east", "wing": "nova", "x": 24.7, "y": 5.9, "w": 1.8, "h": 0.5, "label": "Bench", "kind": "furniture"},
            {"id": "atrium-plant-west", "wing": "nova", "r": 0.45, "x": 19.6, "y": 8.2, "label": "Planter", "kind": "prop"},
            {"id": "atrium-plant-east", "wing": "nova", "r": 0.45, "x": 25.9, "y": 8.2, "label": "Planter", "kind": "prop"},
            {"id": "column-west-1", "wing": "nova", "r": 0.18, "x": 19.0, "y": 3.2, "label": "Column", "kind": "prop"},
            {"id": "column-west-2", "wing": "nova", "r": 0.18, "x": 19.0, "y": 7.6, "label": "Column", "kind": "prop"},
            {"id": "column-east-1", "wing": "nova", "r": 0.18, "x": 27.0, "y": 5.3, "label": "Column", "kind": "prop"},
            {"id": "column-east-2", "wing": "nova", "r": 0.18, "x": 27.0, "y": 8.1, "label": "Column", "kind": "prop"},
            # merchandise: a shelf wall on the north wall, a display table and a rack on the east wall
            {"id": "merch-shelf", "wing": "nova", "x": 27.2, "y": 1.7, "w": 5.3, "h": 0.5, "label": "Merchandise shelf", "kind": "furniture"},
            {"id": "merch-table", "wing": "nova", "x": 28.2, "y": 3.7, "w": 1.9, "h": 0.8, "label": "Display table", "kind": "furniture"},
            {"id": "merch-rack", "wing": "nova", "x": 31.5, "y": 3.5, "w": 1.5, "h": 0.6, "label": "Merchandise rack", "kind": "furniture"},
            # print corner: three printers in a row, a planter closes the row
            {"id": "printer-1", "wing": "nova", "x": 28.4, "y": 6.9, "w": 0.9, "h": 0.7, "label": "Printer", "kind": "prop"},
            {"id": "printer-2", "wing": "nova", "x": 29.8, "y": 6.9, "w": 0.9, "h": 0.7, "label": "Printer", "kind": "prop"},
            {"id": "printer-3", "wing": "nova", "x": 31.2, "y": 6.9, "w": 0.9, "h": 0.7, "label": "Printer", "kind": "prop"},
            {"id": "print-plant", "wing": "nova", "r": 0.4, "x": 32.55, "y": 7.25, "label": "Planter", "kind": "prop"},
            # ---- the Learning Center ----
            # a shelf wall on the north wall, two long tables, a seminar table in the south-east corner
            {"id": "study-shelf", "wing": "learning-center", "x": 2.9, "y": 3.75, "w": 8.1, "h": 0.55, "label": "Bookshelves", "kind": "furniture"},
            {"id": "study-table-1", "wing": "learning-center", "x": 3.2, "y": 5.7, "w": 2.0, "h": 0.8, "label": "Study table", "kind": "furniture"},
            {"id": "study-table-2", "wing": "learning-center", "x": 6.6, "y": 5.7, "w": 2.0, "h": 0.8, "label": "Study table", "kind": "furniture"},
            {"id": "seminar-table", "wing": "learning-center", "x": 10.0, "y": 6.9, "w": 1.2, "h": 1.0, "label": "Seminar table", "kind": "furniture"},
            {"id": "study-plant", "wing": "learning-center", "r": 0.4, "x": 3.15, "y": 7.65, "label": "Planter", "kind": "prop"},
            # ---- the Mercado ----
            # a rack on the west wall, two pallets beside it, crates on the east wall, an aisle in the middle
            {"id": "stock-rack-west", "wing": "mercado", "x": 3.65, "y": 9.0, "w": 0.8, "h": 3.4, "label": "Storage rack", "kind": "furniture"},
            {"id": "stock-pallet-1", "wing": "mercado", "x": 4.95, "y": 9.15, "w": 1.2, "h": 1.0, "label": "Pallet", "kind": "prop"},
            {"id": "stock-pallet-2", "wing": "mercado", "x": 4.95, "y": 11.55, "w": 1.2, "h": 1.0, "label": "Pallet", "kind": "prop"},
            {"id": "stock-crates-1", "wing": "mercado", "x": 9.2, "y": 9.15, "w": 1.8, "h": 1.0, "label": "Crates", "kind": "prop"},
            {"id": "stock-crates-2", "wing": "mercado", "x": 9.2, "y": 11.55, "w": 1.8, "h": 1.0, "label": "Crates", "kind": "prop"},
            # ---- the Student Hub ----
            # a sofa on each side wall, a meeting table and a charging bar in the south corners
            {"id": "hub-sofa-west", "wing": "hub", "x": 28.0, "y": 9.7, "w": 0.95, "h": 2.3, "label": "Sofa", "kind": "furniture"},
            {"id": "hub-sofa-east", "wing": "hub", "x": 32.05, "y": 9.7, "w": 0.95, "h": 2.3, "label": "Sofa", "kind": "furniture"},
            {"id": "hub-meeting-table", "wing": "hub", "x": 28.0, "y": 12.8, "w": 1.6, "h": 0.85, "label": "Meeting table", "kind": "furniture"},
            {"id": "hub-charging-bar", "wing": "hub", "x": 32.3, "y": 12.6, "w": 0.7, "h": 1.1, "label": "Charging bar", "kind": "furniture"},
        ],
        "route": [{"x": 23.0, "y": 8.4}, {"x": 23.0, "y": 5.8}, {"x": 23.7, "y": 4.1}],
        "activities": [
            {"wing": "nova", "x": 14.8, "y": 2.52, "pose": "service", "role": "service", "facing": {"x": 0, "y": 1}, "label": "Serving coffee"},
            {"wing": "nova", "x": 13.9, "y": 4.4, "pose": "phone", "facing": {"x": 0.3, "y": -1}, "label": "Ordering"},
            {"wing": "nova", "x": 13.8, "y": 6.6, "pose": "sit", "facing": {"x": 0.2, "y": -1}, "label": "Eating"},
            {"wing": "nova", "x": 15.3, "y": 6.6, "pose": "sit", "facing": {"x": -0.2, "y": -1}, "label": "Studying"},
            {"wing": "nova", "x": 23.7, "y": 1.97, "pose": "service", "role": "service", "facing": {"x": 0, "y": 1}, "label": "Helping a student"},
            {"wing": "nova", "x": 22.0, "y": 7.2, "pose": "chat", "facing": {"x": 1, "y": 0}, "label": "Meeting"},
            {"wing": "nova", "x": 29.4, "y": 2.95, "pose": "browse", "facing": {"x": 0, "y": -1}, "label": "Browsing"},
            {"wing": "nova", "x": 31.6, "y": 4.6, "pose": "browse", "facing": {"x": 0, "y": -1}, "label": "Looking at shirts"},
            {"wing": "nova", "x": 30.0, "y": 6.2, "pose": "repair", "role": "technician", "facing": {"x": 0, "y": 1}, "label": "Refilling paper"},
            {"wing": "learning-center", "x": 3.7, "y": 6.85, "pose": "sit", "facing": {"x": 0, "y": -1}, "label": "Studying"},
            {"wing": "learning-center", "x": 7.1, "y": 5.35, "pose": "sit", "facing": {"x": 0, "y": 1}, "label": "Reading"},
            {"wing": "learning-center", "x": 5.6, "y": 4.75, "pose": "browse", "facing": {"x": 0, "y": -1}, "label": "Looking for a book"},
            {"wing": "learning-center", "x": 9.3, "y": 7.4, "pose": "chat", "facing": {"x": 1, "y": 0}, "label": "Seminar"},
            {"wing": "learning-center", "x": 10.6, "y": 6.0, "pose": "chat", "facing": {"x": -1, "y": 0}, "label": "Seminar"},
            {"wing": "mercado", "x": 5.55, "y": 10.85, "pose": "repair", "role": "technician", "facing": {"x": 0, "y": 1}, "label": "Stacking boxes"},
            {"wing": "mercado", "x": 9.85, "y": 10.85, "pose": "phone", "facing": {"x": 0, "y": -1}, "label": "Checking the order"},
            {"wing": "hub", "x": 30.0, "y": 10.9, "pose": "chat", "facing": {"x": 1, "y": 0}, "label": "Chatting"},
            {"wing": "hub", "x": 31.0, "y": 10.9, "pose": "chat", "facing": {"x": -1, "y": 0}, "label": "Chatting"},
            {"wing": "hub", "x": 31.2, "y": 12.3, "pose": "phone", "facing": {"x": 0, "y": -1}, "label": "Waiting for a friend"},
        ],
    },
}


# ---- where the employees stand (staff) -----------------------------------------------------
# Only for drawing: the figures of a shop's employees. A working refiller walks between the
# storeroom spot (at the shelves) and the counter spot, a working seller stands at the seller
# spot, everybody else waits at a break spot. No rule reads any of these points.
WORK_SPOTS = {
    "cafe": {
        "wing": "nova",
        "storeroom": {"x": 18.4, "y": 2.52},
        "counter": {"x": 15.7, "y": 2.52},
        "seller": {"x": 13.2, "y": 2.52},
        "break": [{"x": 18.5, "y": 4.4}, {"x": 17.5, "y": 4.7}],
    },
}


# ---- the beach way, the outdoor shops and the Dorm (spec nova-zones) ------------------
# Fixed data, the same on every start. The browser draws it and only walks round it.

# the boardwalk from the plaza south to the sand: it has to stay free to walk
BEACH_WAY = {"id": "beach-way", "label": "Beach Way", "x": 12.9, "y": 17.2, "w": 3.0, "h": 15.6}

# open-air pavilions on the sand. front: the free spot where the shop will be used later.
SHOPS_OUTDOOR = [
    {"id": "surf-shop", "label": "Surf Shop", "x": 5.8, "y": 26.0, "w": 5.1, "h": 2.4,
     "front": {"x": 8.6, "y": 27.55}},
    {"id": "beach-cafe", "label": "Beach Cafe", "x": 25.0, "y": 25.7, "w": 6.6, "h": 3.0,
     "front": {"x": 28.2, "y": 27.4}},
]

# things on the sand and in the water: positions only, the same on every start.
# The paving ends at y 24.5; the dune ridge and the sand start at y 25, the sea at y 35.
BEACH = {
    "sandFrom": 25.0,
    "seaFrom": 35.0,
    "loungers": [
        {"x": 4.4, "y": 32.2, "color": "#ff7458"}, {"x": 6.2, "y": 32.2, "color": "#64cbc8"},
        {"x": 32.8, "y": 32.4, "color": "#f5c95e"}, {"x": 34.4, "y": 32.4, "color": "#bce65f"},
    ],
    # the dune ridge between the promenade and the sand: two mounds that block, grass in a line
    "dunes": [{"x": 3.0, "y": 24.9, "r": 0.7}, {"x": 35.5, "y": 25.0, "r": 0.7}],
    # the low wall between promenade and dunes; it is open at the steps (the gaps between segments)
    "kerb": {"y": 24.25, "h": 0.35, "segments": [[1.0, 5.2], [8.4, 12.2], [16.6, 26.4], [30.2, 37.0], [39.6, 41.4]]},
    # things on the promenade: bins, planter boxes (x, y, w, h), fountain, ice cream cart
    "bins": [[10.4, 22.6], [27.2, 22.4], [37.4, 22.6]],
    "planterBoxes": [[6.2, 21.2, 1.8, 0.7], [28.0, 20.2, 1.8, 0.7], [36.2, 21.6, 1.8, 0.7]],
    "fountain": {"x": 20.6, "y": 20.4},
    "iceCart": {"x": 33.4, "y": 21.9, "w": 1.5, "h": 0.9},
    "grassLine": {"y": 24.75, "from": 1.4, "to": 41.0, "gaps": [[11.6, 17.4], [24.8, 32.4]]},
    "volleyball": {"x1": 36.2, "x2": 39.8, "y": 30.2},
    "tower": {"x": 1.5, "y": 30.3, "w": 1.6, "h": 1.6},
    "rescueBoat": {"x": 1.6, "y": 32.6, "w": 1.8, "h": 0.95},
    "flags": [{"x": 4.2, "y": 30.2, "color": "#e24d3f"}, {"x": 5.1, "y": 30.4, "color": "#f5c95e"}],
    # flat on the sand, nobody is blocked by them: x, y, width, depth, colour, stripe colour
    "towels": [
        {"x": 8.6, "y": 31.6, "occupied": True, "w": 0.9, "h": 1.7, "color": "#ff7458", "stripe": "#ffffff"},
        {"x": 10.2, "y": 32.3, "w": 0.9, "h": 1.7, "color": "#64cbc8", "stripe": "#f5c95e"},
        {"x": 19.4, "y": 30.6, "occupied": True, "w": 0.9, "h": 1.7, "color": "#f5c95e", "stripe": "#ff7458"},
        {"x": 21.2, "y": 31.6, "w": 0.9, "h": 1.7, "color": "#9a7bc1", "stripe": "#ffffff"},
        {"x": 26.8, "y": 32.4, "occupied": True, "w": 0.9, "h": 1.7, "color": "#bce65f", "stripe": "#31545b"},
        {"x": 30.0, "y": 30.8, "w": 0.9, "h": 1.7, "color": "#ff7458", "stripe": "#64cbc8"},
    ],
    # beach umbrellas that stand alone: the post blocks, the canopy does not
    "umbrellas": [
        {"x": 9.9, "y": 31.4, "color": "#ff7458"}, {"x": 20.6, "y": 30.0, "color": "#64cbc8"},
        {"x": 28.9, "y": 31.6, "color": "#f5c95e"},
    ],
    "sandcastle": {"x": 24.4, "y": 33.0},
    # a fire pit with log seats: it burns in the evening (drawing only)
    "firePit": {"x": 22.8, "y": 29.2, "logs": [[-1.8, -0.6, 0.3, 1.2], [1.5, -0.6, 0.3, 1.2], [-0.6, -1.8, 1.2, 0.3]]},
    # annexes of the huts: the Surf Shop's changing cabins and the Beach Cafe's kitchen container,
    # and a chalk sign in front of each
    "annexes": [
        {"id": "surf-cabins", "x": 10.95, "y": 26.0, "w": 1.2, "h": 1.4},
        {"id": "cafe-container", "x": 23.1, "y": 25.7, "w": 1.8, "h": 1.5},
    ],
    "signs": [{"id": "surf-sign", "x": 6.6, "y": 28.9}, {"id": "cafe-sign", "x": 24.4, "y": 29.0}],
    # benches on the promenade, facing the sea
    "benches": [[2.2, 23.4], [9.4, 23.4], [23.8, 23.4], [33.4, 23.4]],
    # rocks at the two ends of the bay, in the wash of the waves
    "rocks": [
        {"x": 2.7, "y": 34.4, "r": 0.5, "block": True}, {"x": 1.7, "y": 34.9, "r": 0.34, "block": False},
        {"x": 3.5, "y": 35.2, "r": 0.28, "block": False},
        {"x": 39.5, "y": 34.3, "r": 0.5, "block": True}, {"x": 40.5, "y": 35.0, "r": 0.34, "block": False},
        {"x": 38.7, "y": 35.3, "r": 0.26, "block": False},
    ],
    "shower": {"x": 17.7, "y": 31.0},
    # people on the beach (drawing only): who sits at the fire, who plays volleyball, a dog on the shore
    "fireside": [[21.15, 29.2, 1, 0], [24.45, 29.2, -1, 0], [22.2, 27.55, 0, 1]],
    "players": [
        {"x": 37.2, "y": 29.0, "team": 0, "phase": 0.0}, {"x": 39.0, "y": 28.7, "team": 0, "phase": 2.0},
        {"x": 37.9, "y": 31.5, "team": 1, "phase": 1.0}, {"x": 36.7, "y": 31.9, "team": 1, "phase": 3.0},
    ],
    "dog": {"x0": 6.0, "x1": 19.0, "y": 33.9},
    "surfers": [
        {"x0": 9.0, "x1": 22.0, "y": 37.6, "phase": 0.0, "color": "#ff7458"},
        {"x0": 24.0, "x1": 37.0, "y": 38.6, "phase": 0.55, "color": "#64cbc8"},
    ],
    "paddlers": [{"x": 15.5, "y": 41.0, "phase": 0.0}, {"x": 31.0, "y": 42.2, "phase": 1.6}],
    # flat rock shelves at both ends of the bay, with tide pools; a lighthouse on the east one
    "rockShelves": [{"x": 1.2, "y": 35.0, "w": 3.6, "h": 1.6}, {"x": 38.2, "y": 35.2, "w": 3.8, "h": 2.8}],
    "pools": [[2.0, 35.7], [3.5, 36.1], [39.3, 36.2], [40.6, 36.9]],
    "crabs": [[2.7, 35.8], [39.9, 36.0]],
    "lighthouse": {"x": 40.6, "y": 36.9},
    "kites": [{"x": 22.4, "y": 31.0, "color": "#ff7458", "phase": 0.0}, {"x": 31.6, "y": 31.6, "color": "#64cbc8", "phase": 2.4}],
    "swimmers": [{"x": 7.5, "y": 36.8, "phase": 0.0}, {"x": 21.5, "y": 37.6, "phase": 1.7}, {"x": 30.4, "y": 36.4, "phase": 3.1}],
    "footprints": [
        {"x": round(16.9 + 0.62 * i, 2), "y": round(33.8 - 0.25 * (i % 2) - 0.05 * i, 2), "side": i % 2}
        for i in range(8)
    ],
    "shells": [[11.6, 34.0], [19.4, 34.1], [23.2, 34.2], [33.0, 34.3], [9.0, 30.4], [27.5, 30.6]],
    "driftwood": [{"x": 9.0, "y": 34.1, "length": 1.6}, {"x": 26.5, "y": 34.2, "length": 1.2}],
    "buoys": [[6.0, 38.4], [15.5, 39.1], [26.0, 38.6], [35.5, 39.2]],
    "boats": [{"x": 9.5, "y": 39.0, "color": "#ff7458"}, {"x": 31.0, "y": 39.4, "color": "#f5c95e"}],
    "gulls": [{"x": 12.0, "y": 32.0, "phase": 0.0}, {"x": 28.0, "y": 30.0, "phase": 2.1}, {"x": 20.0, "y": 33.0, "phase": 4.2}],
}

# The Dorm: a small building east of the Hub, entered like a wing of the Nova (same data shape, one
# wing). The tests and the code of the Nova read NOVA only, so the Dorm is kept apart here and the
# browser joins the two. interior: the one room, with the bed that opens the Dorm panel.
DORM = {
    "id": "dorm", "label": "Dorm", "wall": 0.5,
    "wings": [{"id": "dorm", "label": "Dorm", "fadesWith": []}],
    "parts": [{"id": "dorm", "wing": "dorm", "x": 35.0, "y": 7.6, "w": 5.5, "h": 5.0, "z": 56}],
    "walls": [
        {"id": "dorm-north-wall", "wing": "dorm", "x": 35.0, "y": 7.6, "w": 5.5, "h": 0.5, "side": "north"},
        {"id": "dorm-west-wall", "wing": "dorm", "x": 35.0, "y": 7.6, "w": 0.5, "h": 5.0, "side": "west"},
        {"id": "dorm-east-wall", "wing": "dorm", "x": 40.0, "y": 7.6, "w": 0.5, "h": 5.0, "side": "east"},
        {"id": "dorm-south-wall-west", "wing": "dorm", "x": 35.0, "y": 12.1, "w": 2.0, "h": 0.5, "side": "south"},
        {"id": "dorm-south-wall-east", "wing": "dorm", "x": 39.0, "y": 12.1, "w": 1.5, "h": 0.5, "side": "south"},
    ],
    "entrances": [{"id": "dorm", "wing": "dorm", "x": 37.0, "y": 12.1, "width": 2.0, "side": "south"}],
    "openings": [],
    "interior": {
        "areas": [
            {"id": "dorm-sleep", "wing": "dorm", "label": "Sleep", "x": 35.5, "y": 8.1, "w": 2.5, "h": 4.0, "color": "#c99a62", "labelAt": {"x": 36.2, "y": 11.2}},
            {"id": "dorm-desk", "wing": "dorm", "label": "Desk", "x": 38.0, "y": 8.1, "w": 2.0, "h": 4.0, "color": "#64cbc8", "labelAt": {"x": 38.3, "y": 10.4}},
        ],
        "solid": [
            {"id": "dorm-bed", "wing": "dorm", "x": 35.5, "y": 8.1, "w": 1.5, "h": 2.1, "label": "Bed", "kind": "prop"},
            {"id": "dorm-shelf", "wing": "dorm", "x": 37.3, "y": 8.1, "w": 0.9, "h": 0.5, "label": "Bookshelf", "kind": "prop"},
            {"id": "dorm-desk", "wing": "dorm", "x": 38.4, "y": 8.1, "w": 1.6, "h": 0.7, "label": "Desk", "kind": "prop"},
            {"id": "dorm-wardrobe", "wing": "dorm", "x": 35.5, "y": 10.6, "w": 0.6, "h": 1.3, "label": "Wardrobe", "kind": "prop"},
            {"id": "dorm-plant", "wing": "dorm", "r": 0.35, "x": 39.5, "y": 11.55, "label": "Planter", "kind": "prop"},
        ],
        "activities": [
            {"wing": "dorm", "x": 39.2, "y": 9.45, "pose": "sit", "facing": {"x": 0, "y": -1}, "label": "Flatmate at the laptop"},
        ],
    },
    # the bed: the use point of the Dorm. It opens a panel; it is no door and decides no rule.
    "bed": {
        "zone": "campus", "x": 36.5, "y": 10.75, "kind": "panel", "action": "dorm", "label": "Go to bed",
        "color": "#c99a62", "title": "YOUR BED", "sub": "DORM", "wing": "dorm",
    },
}


# ---- solid objects, in one format for the movement code ----------------------------

def _rect(cid, x, y, width, height, label, kind):
    return {"id": cid, "shape": "rect", "x": x, "y": y, "width": width, "height": height, "label": label, "kind": kind}


def _circle(cid, x, y, radius, label, kind):
    return {"id": cid, "shape": "circle", "x": x, "y": y, "radius": radius, "label": label, "kind": kind}


def _campus_colliders():
    solid = [
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
        _rect("lawn-planter", 38.4, 17.55, 0.48, 2.1, "Lawn planter", "prop"),
    ]
    solid += [_circle(f"terrace-table-{i}", x, y, 0.36, "Terrace table", "prop") for i, (x, y) in enumerate(TERRACE_TABLES)]
    solid += [_circle(f"tree-{i}", x, y, 0.27, "Palm tree", "prop") for i, (x, y, _) in enumerate(TREES)]
    return solid + _zone_colliders() + _nova_colliders()


def _zone_colliders():
    """The beach way, the outdoor shops, the beach and the Dorm (spec nova-zones)."""
    solid = []
    # the arch at the start of the beach way, five lamps along it, two benches at the sand end
    solid.append(_circle("way-arch-west", 12.75, 17.5, 0.15, "Arch post", "prop"))
    solid.append(_circle("way-arch-east", 16.05, 17.5, 0.15, "Arch post", "prop"))
    for i, y in enumerate((19.4, 22.4, 25.4, 28.4, 31.4)):
        solid.append(_circle(f"way-lamp-west-{i}", 12.65, y, 0.12, "Lamp", "prop"))
        solid.append(_circle(f"way-lamp-east-{i}", 16.15, y, 0.12, "Lamp", "prop"))
    solid.append(_rect("way-bench-west", 11.9, 32.0, 0.45, 1.3, "Bench", "prop"))
    solid.append(_rect("way-bench-east", 16.5, 32.0, 0.45, 1.3, "Bench", "prop"))
    # the Surf Shop: counter, board rack, four posts of the awning
    solid.append(_rect("surf-wall-north", 5.8, 26.0, 5.1, 0.2, "Wall", "wall"))
    solid.append(_rect("surf-wall-west", 5.8, 26.2, 0.2, 1.2, "Wall", "wall"))
    solid.append(_rect("surf-counter", 6.8, 26.2, 3.6, 0.8, "Surf Shop counter", "prop"))
    solid.append(_rect("surf-rack", 6.05, 26.6, 0.5, 1.7, "Board rack", "prop"))
    for i, (x, y) in enumerate(((6.0, 27.5), (10.75, 27.5))):
        solid.append(_circle(f"surf-post-{i}", x, y, 0.12, "Post", "prop"))
    # the Beach Cafe: bar, cooler, posts and three tables
    solid.append(_rect("cafe-wall-north", 25.0, 25.7, 6.6, 0.2, "Wall", "wall"))
    solid.append(_rect("cafe-wall-west", 25.0, 25.9, 0.2, 1.2, "Wall", "wall"))
    solid.append(_rect("cafe-bar", 25.6, 26.0, 5.2, 0.8, "Beach Cafe bar", "prop"))
    solid.append(_rect("cafe-cooler", 31.1, 26.0, 0.7, 0.5, "Cooler", "prop"))
    for i, (x, y) in enumerate(((25.3, 27.0), (31.4, 27.0), (25.3, 28.5), (31.4, 28.5))):
        solid.append(_circle(f"cafe-post-{i}", x, y, 0.12, "Post", "prop"))
    for i, x in enumerate((26.2, 28.5, 30.8)):
        solid.append(_circle(f"beach-table-{i}", x, 28.2, 0.36, "Beach table", "prop"))
    # the beach
    for i, lounger in enumerate(BEACH["loungers"]):
        solid.append(_rect(f"lounger-{i}", lounger["x"], lounger["y"], 0.8, 1.5, "Lounger", "prop"))
    for i, dune in enumerate(BEACH["dunes"]):
        solid.append(_circle(f"dune-{i}", dune["x"], dune["y"], dune["r"], "Dune", "prop"))
    for i, umbrella in enumerate(BEACH["umbrellas"]):
        solid.append(_circle(f"umbrella-{i}", umbrella["x"], umbrella["y"], 0.15, "Beach umbrella", "prop"))
    for i, rock in enumerate(r for r in BEACH["rocks"] if r["block"]):
        solid.append(_circle(f"rock-{i}", rock["x"], rock["y"], rock["r"], "Rock", "prop"))
    kerb = BEACH["kerb"]
    for i, (x0, x1) in enumerate(kerb["segments"]):
        solid.append(_rect(f"kerb-{i}", x0, kerb["y"], x1 - x0, kerb["h"], "Low wall", "prop"))
    for i, (x, y) in enumerate(BEACH["bins"]):
        solid.append(_circle(f"bin-{i}", x, y, 0.22, "Bin", "prop"))
    for i, (x, y, w, h) in enumerate(BEACH["planterBoxes"]):
        solid.append(_rect(f"planter-box-{i}", x, y, w, h, "Planter", "prop"))
    fountain = BEACH["fountain"]
    solid.append(_circle("fountain", fountain["x"], fountain["y"], 0.25, "Drinking fountain", "prop"))
    cart = BEACH["iceCart"]
    solid.append(_rect("ice-cart", cart["x"], cart["y"], cart["w"], cart["h"], "Ice cream cart", "prop"))
    for i, (x, y) in enumerate(BEACH["benches"]):
        solid.append(_rect(f"promenade-bench-{i}", x, y, 1.4, 0.42, "Bench", "prop"))
    for annex in BEACH["annexes"]:
        solid.append(_rect(annex["id"], annex["x"], annex["y"], annex["w"], annex["h"], "Annex", "prop"))
    for sign in BEACH["signs"]:
        solid.append(_circle(sign["id"], sign["x"], sign["y"], 0.3, "Chalk sign", "prop"))
    pit = BEACH["firePit"]
    solid.append(_circle("fire-pit", pit["x"], pit["y"], 0.55, "Fire pit", "prop"))
    for i, (dx, dy, w, h) in enumerate(pit["logs"]):
        solid.append(_rect(f"fire-log-{i}", pit["x"] + dx, pit["y"] + dy, w, h, "Log", "prop"))
    castle = BEACH["sandcastle"]
    solid.append(_circle("sandcastle", castle["x"], castle["y"], 0.4, "Sandcastle", "prop"))
    shower = BEACH["shower"]
    solid.append(_circle("beach-shower", shower["x"], shower["y"], 0.15, "Beach shower", "prop"))
    net = BEACH["volleyball"]
    solid.append(_circle("net-post-west", net["x1"], net["y"], 0.12, "Net post", "prop"))
    solid.append(_circle("net-post-east", net["x2"], net["y"], 0.12, "Net post", "prop"))
    tower = BEACH["tower"]
    solid.append(_rect("lifeguard-tower", tower["x"], tower["y"], tower["w"], tower["h"], "Lifeguard tower", "prop"))
    solid.append(_rect("tower-stairs", tower["x"] + tower["w"], tower["y"], 0.5, tower["h"], "Stairs", "prop"))
    boat = BEACH["rescueBoat"]
    solid.append(_rect("rescue-boat", boat["x"], boat["y"], boat["w"], boat["h"], "Rescue boat", "prop"))
    for i, towel in enumerate(t for t in BEACH["towels"] if t.get("occupied")):
        solid.append(_rect(f"sunbather-{i}", towel["x"] + 0.05, towel["y"] + 0.05, towel["w"] - 0.1, towel["h"] - 0.1, "Sunbather", "prop"))
    # the Dorm: walls, furniture, and what stands at its door
    solid += [_rect(w["id"], w["x"], w["y"], w["w"], w["h"], "Wall", "wall") for w in DORM["walls"]]
    for item in DORM["interior"]["solid"]:
        if "r" in item:
            solid.append(_circle(item["id"], item["x"], item["y"], item["r"], item["label"], item["kind"]))
        else:
            solid.append(_rect(item["id"], item["x"], item["y"], item["w"], item["h"], item["label"], item["kind"]))
    solid.append(_rect("dorm-bench", 39.3, 13.1, 1.2, 0.4, "Bench", "prop"))
    return solid


def _nova_colliders():
    solid = [_rect(wall["id"], wall["x"], wall["y"], wall["w"], wall["h"], "Wall", "wall") for wall in NOVA["walls"]]
    for item in INTERIORS["campus"]["solid"]:
        if "r" in item:
            solid.append(_circle(item["id"], item["x"], item["y"], item["r"], item["label"], item["kind"]))
        else:
            solid.append(_rect(item["id"], item["x"], item["y"], item["w"], item["h"], item["label"], item["kind"]))
    # nobody walks behind the buildings: the ground north of the Learning Center and west of it,
    # and the ground north-east of the Nova are closed off
    solid += [
        _rect("north-west-fence", 0, 0, 11.5, 3.25, "Fence", "boundary"),
        _rect("west-fence", 0, 3.25, 2.2, 5.4, "Fence", "boundary"),
        _rect("north-east-fence", 33.5, 0, 10.5, 7.5, "Fence", "boundary"),
    ]
    return solid


def colliders(zone_id):
    """Everything solid in one zone: the walls and furniture of the Nova and its wings, the props."""
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
        "planters": PLANTERS,
        "trees": TREES,
        "spaces": SPACES,
        "nova": NOVA,
        "interiors": INTERIORS,
        "work_spots": WORK_SPOTS,
        "dorm": DORM,
        "outdoorShops": SHOPS_OUTDOOR,
        "beachWay": BEACH_WAY,
        "beach": BEACH,
    }
