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

## Data moves for the checks of the first draft

`tests/test_map_layout.py` (from the first draft of this spec: no free ground cut off, the gap behind the
Cafe counter at least 0.6) went into `main` together with the built design and failed on it, but pytest
stopped at collection (two files called `test_map_layout.py`, fixed by renaming the walk check to
`checks/test_map_layout_walk.py`), so it never ran. Nothing in `tests/` or `checks/` is changed except that
name. The data moved the least that is needed, and the drawing reads the same data:

| Object (`world.py`) | Move | Why |
| --- | --- | --- |
| `cafe-shelf` | height 0.6 to 0.45 (y stays 1.7) | The gap to the counter (y 2.8) grows from 0.5 to 0.65. The counter, its end and the staff spots stay as built. |
| `student-counter` (atrium) | x 22.2 to 22.0 | The gap to the supply desk shrinks from 0.5 to 0.3, so it is shut and the free cell inside it is gone. |
| `umbrellas[1]` (beach, near the sunbather) | y 30.0 to 30.3 | The pocket between the sunbather, the umbrella and the log is filled instead of cut off. The crossing at y 29.1 stays clear. |
| `rocks[0]` (south-west end of the bay) | y 34.4 to 34.8 | The pocket between the rescue boat and the rock is open towards the beach. |

Checked: `uv run pytest` (1259 passed), and in the browser the Cafe, the atrium, the beach near the fire and
the south-west end were looked at, with no console errors.
