# World data and player position (`world-api`, issue #27)

## What

`world.py` holds the campus as data: zones with their bounds and spawn points,
doors and other usable places, solid objects, room layouts. `GET /api/world` hands
it to the browser, which only draws it. The state gets `player` (zone, x, y), saved
in its own `player` table, so the position survives a restart and a save from before
this spec still loads. `POST /api/player` saves a new position through
`logic.move_player`. All request bodies go through one check: anything that is not a
JSON object counts as empty and the rules refuse it.

The layout comes from Felix Antes' Nova Beach Ventures, without its shops, districts
and other mechanics. The only places with a job are the supply desk (stock), the snack
stand counter (prices) and the board (dashboard).

## Out of scope

Drawing, movement and camera in the browser (`world-core`). Rules for money, building
or shops. Checking whether the player stands inside furniture: the position is only
for showing the world, and no rule may depend on it.

## Done when

1. `GET /api/world` returns all zones, colliders, room layouts and locations. Every
   location lies inside its zone. Every door leads to a zone and to a free place to
   stand. Every room has a way out.
2. A new run starts at the spawn. The position survives a restart. A save without a
   position, or with a zone that no longer exists, starts at the spawn. A new run resets the position. Moving changes nothing
   but the position, and also works after the last day.
3. An unknown zone, a position outside the bounds, a value that is not a finite number,
   a missing field, or a body that is not a JSON object is refused with 400 and the
   saved run stays identical. This holds for all POST endpoints, also for a quantity that
   cannot be read as a number and a price too high to store.
