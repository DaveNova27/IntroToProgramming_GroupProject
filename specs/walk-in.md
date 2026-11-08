# Walking into the Nova (`walk-in`, issue to be opened)

BUILT on branch `walk-in`, waiting for the team's review. Decisions from Felix on 2026-11-08,
after David's voice memo (weather visible from inside, the day starts and ends at the Dorm, the
shops and printers inside the Nova, the Surf Shop and the Beach Cafe outside).

## What

The player walks into one big building and the roof fades away. There is no door to click and no
second screen: the Nova stands on the campus map like every other building, with a wide entrance
in its wall. While the player is inside, the whole roof fades out at once, the two walls that face
the camera sink to a low rim, and the rooms underneath are shown. The sky, the light and (later)
the weather are drawn over the whole scene, so it is visible from inside that it rains or that the
sun shines. When the player walks out, the roof comes back.

The three separate room zones (`mercado`, `academy`, `hub`) go away. Their three desks (order
stock, set prices, open the dashboard) move into the Nova, so everything the old rooms offered is
still reachable. The Nova is built to be recognised as the real Nova SBE in Carcavelos (see "Look").

This is the first of the specs that rebuild the world (see the roadmap, phase 2):
`walk-in` (this spec) → `nova-zones` (Dorm, the way to the beach, Surf Shop and Beach Cafe outside)
→ `day-cycle` (the day starts and ends at the Dorm) → `nova-design` (polish).

### Data (`world.py`)

- `ZONES` keeps one zone, `campus`. Its walkable bounds grow to the north so the whole Nova fits.
  The spawn stays `(21, 18)`, outdoors on the plaza; the Dorm spawn comes with `nova-zones`.
- `NOVA` (next to `BUILDINGS`, because those are solid blocks) is the new kind of building. It holds:
  - `parts`: a list of rectangles `{x, y, w, h, z}` (tiles, z = wall height). Together they are the
    footprint: one atrium block in the middle (taller, with the glass roof) and a wing on each side.
    Size: 22 × 8 tiles, so the floor inside is 21 × 7 tiles, where the three academic wings stood
    and north of them. In this first form the wings are plain blocks; longer "fingers" towards the
    sea come with `nova-zones`. The plaza, the courtyard and the food court stay free.
  - `walls`: wall pieces as solid rectangles with the openings left out, written as data like
    `solid` is today. At least one `entrances` entry (`{x, y, width, side}`) on the plaza side, wide
    enough for the player (at least 2 tiles). Openings between the atrium and the wings.
  - the rooms are in `INTERIORS["campus"]` (keyed by the zone they are in): the same format as
    today's room layouts (`areas`, `solid`, `route`, `activities`, in campus coordinates), plus
    `floor`.
- The three academic wings are replaced by the Nova. The Student Hub is removed as well: it stood
  east of the Nova and, seen from the camera, hid the Print Corner. Learning Center and Mercado stay
  as outdoor buildings for now; `nova-wings` makes them wings that can be entered. The three desks stand
  inside: "Order stock" (supply desk) and "Open the dashboard" (Student Central) in the atrium, "Set
  your prices" (cafe counter) in the Cafe. They keep their ids and `action`s.
- The whole floor inside is open to walk on. The labelled areas split it between them (Cafe in the
  west, Atrium in the middle, **Merchandise** and the **Print Corner** in the east wing). Counters and
  shelves stand against the north and west walls, where the camera sees their fronts, and every gap
  between two pieces is either shut (at most 0.5 tiles, less than a person) or at least 1.4 wide, so
  that walking by hand and clicking to walk both find their way and nobody gets stuck. The atrium has a
  gallery with a glass balustrade along its north wall, reached by a staircase (drawing only: the
  upper floor is not walkable). The areas have their own floors (timber, polished stone, carpet,
  concrete) and the light falls through the windows in the north wall and moves with the time of day.
- Inside the Nova, as data and drawing only (no rule): labelled floor areas for the **Cafe**, the
  **Merchandise** shop and a **Print Corner** with three printers (solid props). Who serves there,
  stock on a shelf and refilling paper and ink are later specs (`shop-walk`, `shop-art`, and a new
  spec for the printers, roadmap section 6 idea 9).
- `world_view()` sends `interiors` (keyed `"campus"`) and `nova` with `parts`, `walls` and `entrances`.
- `colliders("campus")` contains the walls and the interior solids. `colliders` for the removed
  zones is gone.

### Browser (`static/world/`)

- A small pure module `roofs.js`: `insideParts(point, parts)` (is the point under the roof, using the
  inner side of the walls) and `stepRoof(current, inside, dt, reducedMotion)` (eases the roof
  opacity towards 0 inside and 1 outside in about 0.45 s; with reduced motion it jumps). It reads
  nothing from the page, so a test can run it with Node.
- `render.js`: for the Nova, draws the floor and the furniture first, the back walls with the
  actors, then the front walls (they sink to a low rim while the roof is open) and the roof last,
  with `globalAlpha` = roof opacity. People of the interior (`activities`) are drawn only while
  the roof opacity is below about 0.98: from outside you do not see in.
- Sky, `drawAmbientLighting` and the coast run for the whole campus zone, as today. Nothing in the
  Nova hides or darkens them; `weather-visuals` later adds rain and storm on top of everything.
- `main.js`: `changeZone` and the door handling are removed. The zoom eases to the closer, indoor
  value while the player is inside, with the existing easing. The header shows the place: "Nova Coast
  Campus" outside, the name of the area (for example "Atrium") inside. The four zone chips in
  `static/map.html` become two: Outside and Nova (lit while the roof is open).
- The passers-by (`walkers.js`) stay outdoors: their goals are the existing `spaces`, and the walls
  are solid for them as for the player.
- Click to walk: `findPath` in `paths.js` runs over the campus with the walls and finds the way in
  through the entrance. If it gets too slow on the larger map, the grid is adjusted in this spec.
- The position is still saved through `POST /api/player` with `zone: "campus"`. A save that holds
  one of the removed zones starts at the spawn (this already works: unknown zone, `world-api`).

## Look (reference for the Nova)

So that the building is recognised at first sight, form and colour follow the real campus. Stylised,
not an exact model; no logo and no official branding. The colours are estimated from photographs.

- Long, low, **white** volumes, at most three floors, **flat roofs with a thick white edge** that
  ends in a slanted line. Walls `#f4f4f1`, shadow side `#c9cdd0`.
- **Slim square white columns** under deep canopies, and a covered passage between the wings.
- **Dark-framed glass fronts** with bluish glass: frame `#1f3a4d`, glass tint `#5b8fb9`.
- The **atrium** in the middle: a glass roof on a white steel truss, a light polished floor, one wide
  staircase, white columns, and a gallery with a glass balustrade on the upper floor. The roof
  fade of this spec applies to it as well.
- A warm grey paved **plaza** in front (`#b9b0a2`), a light lawn between the wings (`#a9c97a`),
  sand and the sea to the south (`#e6d9b8`, `#2f6db0`), as the outdoor map already has.
- The fingers point to the sea, like on the official campus map.

Sources: the photographs of [Studio CAPN](https://www.capnunes.com/nova-sbe/), the official
[campus tour map](https://campustour.novasbe.pt/) and the page of the
[Hovione Atrium](https://campustour.novasbe.pt/p/hovione-atrium). Named things in the Nova (shops,
brands) are our own: Cafe, Merchandise, Print Corner.

## Decide (my recommendations)

1. **Tests that name the removed zones.** Eight existing tests name zones, doors or a number that
   the spec changes on purpose. David confirmed the exception on 2026-11-08, for exactly these tests
   and for the threshold below. They were changed in this PR and nothing else in `tests/` was:
   - `tests/test_world_api.py::test_the_api_serves_the_whole_world`: the zones are `{"campus"}` and the
     rooms are keyed `{"campus"}` (were: `campus`, `mercado`, `academy`, `hub`).
   - `test_every_door_leads_to_a_zone_with_a_free_place_to_stand`: there are no doors (it counted six).
     The same check for the way in: the spawn is in bounds and free, and every entrance of the Nova
     leads to free ground in the doorway, one step outside and one step inside.
   - `test_every_room_has_a_way_out`: the rooms are inside the Nova on the campus, and the Nova has an
     entrance at least 2 tiles wide (was: a door back to the campus from each room zone).
   - `test_the_position_survives_a_restart`, `test_the_api_saves_the_position`,
     `test_moving_changes_nothing_but_the_position` and `test_the_position_can_move_after_the_last_day`
     saved a position in the zones `academy`, `hub` or `mercado`. They use the zone `campus` and a spot
     inside the Nova (23.25, 5.5 and 23.5, 7.25). The last one now compares the whole position, so it
     checks more than before, not less.
   - `tests/test_world_paths.py::test_every_door_and_desk_can_be_reached_from_anywhere` (Node, runs on
     GitHub Actions): `checked > 100` became `checked > 60`. The three desks on one campus give 69
     checks, not more than 100. This is the only threshold that is loosened; every check inside it
     stays as it was.
   Apart from that threshold no assertion was weakened, no test was skipped or deleted, and
   `test_world_art.py` needed no change because the rooms are keyed by the zone `campus`. New checks are in `tests/test_walk_in.py`.
   The alternative, keeping the three room zones until `nova-zones`, leaves two half-working systems
   side by side and was not chosen.
2. **One PR for the mechanism and the Nova.** The mechanism needs a real building to be tested, and a
   throwaway building would mean doing the work twice. So the Nova's first form comes in this
   spec (shape, walls, atrium, three desks, areas), and its detailed look stays in `nova-design`.
3. **Which outdoor buildings go.** The three academic wings (the Nova takes their place) and the
   Student Hub (it hid the Print Corner). Learning Center and Mercado stay. `nova-wings` makes them
   wings that can be entered; `nova-zones` redraws the outdoor map (Dorm, beach way, Surf Shop, Beach
   Cafe).
4. **The whole roof at once.** Decided by Felix, no per-room roofs. Inside this spec the Nova is one
   building with one roof. `nova-wings` proposes one roof per wing.
5. **Printers.** Drawn and placed, without a rule. Decided by Felix to be included.

## Out of scope

More wings, entering the Learning Center and the Mercado (`nova-wings`). The Dorm, the way to the beach, the Surf Shop and the Beach Cafe (`nova-zones`). The day starting
and ending at the Dorm and the day-end screen (`day-cycle`). Rain, storm and sky effects
(`weather-visuals`). Final art and details (`nova-design`). Shop work, serving, carrying stock, staff and
guests (`shop-walk`, `staff`, `guests`). Any rule for money, stock or time: where the player stands
changes no rule, and no rule may read it.

## Done when

1. `uv run pytest` passes. Only the tests named in "Decide" 1 changed (zone names, door count and
   the number of checks), and the change is explained in the PR. New checks are in
   `tests/test_walk_in.py`.
2. The data is complete and consistent: one zone `campus`; the Nova has parts, walls with at least
   one entrance at least 2 tiles wide, and an interior; every location lies inside the zone; no
   wall or solid covers an entrance or the spawn; the three desks stand inside (two in the atrium,
   one in the Cafe) and keep their ids and actions. The areas split the whole floor, people stand on
   free ground, and no free spot inside is cut off: it can be walked to from the entrance, and the
   grid of `paths.js` finds a way to it as well.
3. A test runs the real `paths.js` and `physics.js` with Node on the data from `world.py`: from many
   places on the campus, every desk and every door-less entrance can be reached, and the way never
   walks through a wall (the existing `test_world_paths.py` style).
4. A test runs the real `roofs.js` with Node: inside gives target opacity 0, outside 1; the opacity
   moves monotonically and ends exactly at the target; with reduced motion it jumps at once; the
   point test agrees with the footprint at the walls and at the entrance.
5. In the browser: walking or clicking from the plaza through the entrance fades the roof out
   (about half a second) and shows the atrium with its desks; walking out brings it back. The
   front walls sink while the roof is open. From outside you see no people inside. The sun, the
   light and the sea stay visible from inside. All three desks work from inside and show up in
   the dashboard as before. No console errors; the page also works in the small live window
   of the dashboard.
6. A save with a removed zone starts at the spawn; a save with a position inside the Nova loads
   inside the Nova with the roof open; the position survives a restart.
7. The building is recognisable as the Nova: white volumes with flat roofs and a thick edge, dark glass
   fronts, slim columns, the glass-roofed atrium (checked against "Look" in the browser, with a
   screenshot in the PR).
8. All new code: no `Math.random`, nothing loaded from outside, labels set with `textContent`.
   The README ("How it fits together", the spec table, known issues) and the roadmap (rows for
   `walk-in`, `nova-zones`, `day-cycle`) are up to date.
9. PR "Closes #<issue>", AI code review done and its findings handled.

## Security

Roadmap 3a and 3b: the zone id stays on a whitelist (`campus`), and `POST /api/player` still checks
the position on the server (finite, inside the bounds); no rule depends on the position the
browser sends. The new data is fixed on the server and only read by the browser. Names and
labels are shown through `textContent`; no external asset and no `innerHTML` with data.
