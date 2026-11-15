<<<<<<< Updated upstream
# Map layout

Issue [#71](https://github.com/DaveNova27/IntroToProgramming_GroupProject/issues/71) · Branch `map-layout`

## Decide

The browser walk covered the Dorm, all four Nova wings, the service lane, the two outdoor shops, the promenade and the shoreline. In the small live window the coral stroke looked like a barrier. In the main view it crossed furniture and ended in open paving. The courtyard planters, benches at the sand end of the boardwalk and the gap behind the Cafe counter also disagreed with what the player could walk through.

| Place | Floor plan decision and reason |
| --- | --- |
| Campus and Nova | Keep the 90 × 48 ground and the walking limits of x = 1–41 and y = 1–34.7. The Dorm door, the Nova's three exterior entrances and the openings between the four wings already connect the rooms. The north fences and sea at y = 35 bound the walk. |
| Dorm to Nova | Remove the coral stroke from x = 7.2 to 34.6. Keep the flagstones from the Dorm and the paved crossing at y = 16.9. At x = 23 the crossing turns north through the main entrance. Keep three courtyard planters beside this axis, clear the one in front of the doorway and move the eastern planting out of the Hub. The planters and reflecting pool now block exactly where they are drawn, within the existing planter edge tolerance. |
| Palms | Thin the 13 walkable-area palms to ten. Two frame the west plaza and boardwalk approach, one stands east of the courtyard basin, three frame the Lawn and Dorm, two flank the Sunset Forum and two frame the promenade. This clears the service lane, the westward turn from the Dorm, the approach to the boardwalk arch and both shop stairways. The trunks use the same coordinates for drawing and collision. The background trees beyond the walking area are scenery. |
| Terrace, Lawn and boardwalk | Keep the terrace tables on their existing pads. Only the four pergola posts are solid so a player can pass under it. Give the two Lawn benches their drawn footprints. Set the arch posts half a tile farther down the three-tile boardwalk to leave turning room behind the terrace planter. Move the lamps at the shop crossing to y = 27.8. Draw both end benches from their solid footprints at y = 32. |
| Promenade to shops | Put the west steps at x = 3.6–5.75 and the east steps at x = 31.8–34.5. Each now leads down beside its hut. Keep the boardwalk opening and the far east beach access. Grow dune grass only along wall segments. Set the west planter, east bench and ice cream cart back from the approaches. |
| Surf Shop to Beach Cafe | Keep a straight crossing along y = 29.1. Move the fire and its log seats 2.25 tiles towards the water, with their occupants and walking destination. Shift the adjacent towel clear of the logs. Put the cafe sign beside the kitchen container. Keep a table with an inward-facing seat on either side of the Beach Cafe entrance, clear of the awning posts, open the middle to the queue and remove the end bar stool to give the cooler a usable approach. |
| Cafe counter | The former staff aisle between the shelves and counter was 0.5 tiles wide. A player is 0.56 tiles across. Shorten the east end of the counter by 1.4 tiles. The shelf and counter can now be reached from that end, and the existing refiller walks between them. Keep two solid stools at the west end so the first customer can stand clear of the seats. |

## Fixed places

`GET /api/world` serves `places.shops` and `places.central_storage`. Coordinates are standing positions in campus tiles. Each shop has a zone, wing, front, storeroom, counter, seller, two break spots and a queue. A queue has a head and an x/y step for each of the next five visible places. The existing staff, guest and outdoor-front data use the same coordinates.

| Shop | Front | Where the other places fit |
| --- | --- | --- |
| Cafe | (17.7, 5.0) | Stock at the end of the shelf, counter access around its east end, seller on the service side facing the line. Break beside the seating. |
| Merchandise | (30.8, 4.8) | Stock by the north shelf, counter and seller beside the display table, breaks along the southeast edge. |
| Surf Shop | (8.6, 27.55) | Stock by the board rack, counter to its east, seller towards the sand, breaks at the cabin end of the deck. |
| Beach Cafe | (28.2, 27.4) | Stock by the cooler, counter at the east end of the bar, seller in the centre opening, breaks southwest of the tables. |

The Mercado already has racks, pallets and a clear middle aisle. Reserve its south entrance at (7.5, 13.0), the computer standing position beside the crates at (8.6, 10.8), and the truck unloading point on the west service lane at (1.55, 12.1). The dock pallets and gate post have solid footprints. The loading point is reachable on foot around the south end of the Mercado.

## Acceptance

- The data check starts at the actual spawn, walks connected floor with a full player footprint and checks the final approach to each of the 51 standing or queuing positions. A second check covers the direct crossings with spare clearance.
- In the browser, walk from the Dorm across the plaza into the Nova, visit the four wings and the loading point, pass both outdoor shops by the side stairs, and follow the boardwalk to the shore. At stops, switch to the small dashboard window and back.
- The table is fixed server data. Position grants no permission to buy, sell, work or order. The scope covers the floor plan and positions. Shop art, walking a shift, the Nova redesign, changes to the Dorm day cycle, ordering and truck behaviour belong to their own specs.
=======
# The floor plan and the places on it (`map-layout`)

Issue #71. Branch `map-layout`. Depends on `map-view` (merged, #67, #69). Waits for `day-cycle`
(#64, PR #65) before `world.py` and `static/world/locations.js` are touched: it changes the Dorm and the
same files. `shop-walk` (#40), `shop-art` (#18), `nova-design` (#11) and `warehouse` build on this spec.

DRAFT, part 1 only. Part 2 (the places) is decided after part 1 is built.

## What

Two parts. Part 1 finishes the floor plan of the whole map in `world.py`. Part 2 fixes the places of the
four shops and the central storage on it, as data.

### Part 1: the floor plan

Found by walking the map in the browser (front view) and by a reachability check from the spawn
(21, 18), player radius 0.28:

1. The campus is 90 x 48 tiles but a person walks only on x 1 to 41 and y 1.0 to 34.7. The meadow east of
   x 41 and the sea from y 35 are ground only.
2. Four small pockets of free ground cannot be reached from the spawn: between the rescue boat, the west
   rock and the edge (about x 1.4 to 2.0, y 33.8 to 34.4); beside the sunbather and the umbrella (about
   20.4, 30.4); between the two desks in the atrium (about 22.0, 2.0); and the Cafe's staff spots,
   see point 4.
3. The gaps beside the benches at the sand end of the beach way (x 11.9 to 12.35 and 16.5 to 16.95) are
   narrower than a person but not shut.
4. The Cafe's `storeroom`, `counter` and `seller` spots (y 2.52) lie between the shelf (to y 2.3) and the
   counter (from y 2.8): a gap of 0.5, a person needs 0.56. All three points are solid. Not decided
   yet, see "Decide" 4.

### Part 2: the places on it

As in the issue: per shop (Cafe, Beach Cafe, Merchandise, Surf Shop) the entrance or front, the
storeroom spot, the counter spot, the seller spot, break spots and the queue line, in one table of one
shape; and a place for the central storage with its computer and a spot where a truck unloads (data
only, for `warehouse`). Decided later.

## Decide

1. **Zone size:** unchanged. The walkable box stays x 1 to 41, y 1.0 to 34.7; the ground stays 90 x 48.
2. **Kerb:** unchanged. The four openings of the low wall between promenade and sand stay
   (x 5.2 to 8.4, 12.2 to 16.6, 26.4 to 30.2, 37.0 to 39.6). A test checks that each one is walkable and
   leads to the sand.
3. **Pockets and narrow gaps:** fixed by moving the objects the least that is needed, so that no free
   ground is cut off and every gap between two solid objects is either shut (at most 0.5) or at least 1.4
   wide (the same rule as inside the Nova). The exact moves are listed here when built, with the
   drawing code that reads the same data (`BEACH`) staying in step.
4. **Cafe staff spots:** the gap behind the counter is widened to at least 0.6 (shelf and counter move
   apart, the staff spots at y 2.52 stay or move to the middle of the new gap), so that `storeroom`,
   `counter` and `seller` are walkable and reachable. The drawing of the Cafe (`rooms.js`) must still
   match; the test covers them like every other point.
5. **Tests (new file `tests/test_map_layout.py`):** every named point is inside its zone, walkable, not in a
   solid object and reachable from the spawn; no free pocket is cut off; no gap between 0.5 and 1.4.
   `tests/` is otherwise untouched. If an existing test names data this spec changes, I stop and the owner
   of the PR decides.

## Out of scope

Game rules, walking the shift (`shop-walk`), new looks for the shops (`shop-art`), the Nova look
(`nova-design`), the Dorm and the day start (`day-cycle`), the truck and ordering (`warehouse`). No new
art, no change to the size of the zone, no new kerb openings.

## Done when

1. **Spec:** this file, with the Decide section up to date.
2. **Floor plan:** the points of Decide 3 are fixed and everything free is walkable from the spawn.
3. **Data table:** the places of all four shops and the central storage in one table, served by
   `/api/world` (part 2).
4. **Tests:** `tests/test_map_layout.py` passes and fails on the old data.
5. **Browser:** looked at in the main view and in the small dashboard window; no console errors.
6. **Review:** `uv run pytest` passes, PR against `main`, AI code review done.

## Security

The data is fixed on the server, the position is never trusted, no rule reads it. Follows sections 3a and
3b of `docs/feature-roadmap.md`. Nothing is loaded from outside.
>>>>>>> Stashed changes
