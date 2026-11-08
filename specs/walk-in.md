# Walking into the Nova (`walk-in`, issue to be opened)

DRAFT: to be agreed with the team before any code is written. Decisions from Felix on 2026-11-08,
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
- `BUILDINGS["nova"]` is a new kind of building with:
  - `parts`: a list of rectangles `{x, y, w, h, z}` (tiles, z = wall height). Together they are the
    footprint: one atrium block in the middle and two long wings ("fingers") pointing towards the
    sea (south). Placeholder size: about 22 × 9 tiles, the space of today's three academic wings.
    The plaza, the courtyard and the food court stay free.
  - `walls`: wall pieces as solid rectangles with the openings left out, written as data like
    `solid` is today. At least one `entrances` entry (`{x, y, width, side}`) on the plaza side, wide
    enough for the player (at least 2 tiles). Openings between the atrium and the wings.
  - `interior`: the same format as today's room layouts: `areas`, `solid`, `route`,
    `activities`, in campus coordinates, plus `floor`.
- The other buildings (Learning Center, the three academic wings, Mercado, Student Hub on the outdoor
  map) stay as they are for now; `nova-zones` decides what becomes of them. The three desks stand
  in the atrium: "Order stock" (supply desk), "Set your prices" (cafe counter), "Open the dashboard"
  (Student Central). They keep their ids and `action`s.
- Inside the Nova, as data and drawing only (no rule): labelled floor areas for the **Cafe**, the
  **Merchandise** shop and a **Print Corner** with three printers (solid props). Who serves there,
  stock on a shelf and refilling paper and ink are later specs (`shop-walk`, `shop-art`, and a new
  spec for the printers, roadmap section 6 idea 9).
- `world_view()` sends `interiors` keyed by building id (`"nova"`), plus the building list with
  `parts`, `walls` and `entrances`.
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

1. **Tests that name the removed zones.** Eight tests in `tests/test_world_api.py` name zones or
   doors that no longer exist: `test_the_api_serves_the_whole_world`,
   `test_every_door_leads_to_a_zone_with_a_free_place_to_stand` (counts six doors),
   `test_every_room_has_a_way_out`, `test_the_position_survives_a_restart` (zone `academy`),
   `test_the_api_saves_the_position` and `test_a_new_run_puts_the_player_back_at_the_spawn` (zone
   `hub`), `test_moving_changes_nothing_but_the_position` (zone `mercado`) and
   `test_the_position_can_move_after_the_last_day` (zone `hub`). `tests/` may not be edited, so this
   needs an exception that David confirms (as for PR #7). Recommendation: change only the zone
   names and the door count to the new data, weaken no check, and add the new checks in
   `tests/test_walk_in.py`. The alternative, keeping the three room zones until `nova-zones`,
   leaves two half-working systems side by side and is not recommended.
2. **One PR for the mechanism and the Nova.** The mechanism needs a real building to be tested, and a
   throwaway building would mean doing the work twice. So the Nova's first form comes in this
   spec (shape, walls, atrium, three desks, areas), and its detailed look stays in `nova-design`.
3. **Which outdoor buildings go.** Recommendation: none in this spec; the Nova is added next to
   them and the old room entrances disappear with the old zones. `nova-zones` redraws the outdoor
   map (Dorm, beach way, Surf Shop, Beach Cafe) and decides about the rest.
4. **The whole roof at once.** Decided by Felix, no per-room roofs.
5. **Printers.** Drawn and placed, without a rule. Decided by Felix to be included.

## Out of scope

The Dorm, the way to the beach, the Surf Shop and the Beach Cafe (`nova-zones`). The day starting
and ending at the Dorm and the day-end screen (`day-cycle`). Rain, storm and sky effects
(`weather-visuals`). Final art and details (`nova-design`). Shop work, serving, carrying stock, staff and
guests (`shop-walk`, `staff`, `guests`). Any rule for money, stock or time: where the player stands
changes no rule, and no rule may read it.

## Done when

1. `uv run pytest` passes. Only the eight tests of "Decide" 1 changed (zone names and door count),
   and the change is explained in the PR. New checks are in `tests/test_walk_in.py`.
2. The data is complete and consistent: one zone `campus`; the Nova has parts, walls with at least
   one entrance at least 2 tiles wide, and an interior; every location lies inside the zone; no
   wall or solid covers an entrance or the spawn; the three desks stand inside the atrium and keep
   their ids and actions.
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
