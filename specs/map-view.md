# The world seen straight from the front (`map-view`, issue #66)

Asked for by David on 2026-11-09: the 45 degree isometric view is awkward to walk and to click in.
Drawing only: no rule reads the camera, no new API, `world.py` stays as it is.

BUILT on branch `map-view` (2026-11-09), checked in the browser; waiting for the AI code review.

A quick prototype on this branch (only `isoPoint` and `canvasWorldPoint` changed) showed that most of
the world already draws correctly, because the shapes (`drawBlock`, `drawTile`, `drawPlane`) all go
through `isoPoint`: a block then shows its top and its south face, and its east face folds to a line.
The list below is what the prototype showed as broken.

## What

### Camera (`static/world/scene.js`)

- New projection: x goes right, y goes down (north at the top, the sea at the bottom), height goes up.
  `isoPoint(x, y, z)` returns `{ x: x * TILE, y: y * DEPTH - z }`, where `TILE = 44` pixels per tile
  across and `DEPTH = TILE * 0.7` pixels per tile into the picture (see Decide 1).
- `canvasWorldPoint(event)` is the exact inverse at height 0, so a click lands on the floor tile
  under the pointer.
- `TILE_W` and `TILE_H` go away; every use is replaced by `TILE` / `DEPTH` or removed.
- One helper `depthOf(x, y)` (the sort key, see below) lives in `scene.js`. The name `isoPoint` stays,
  so the about 380 calls do not have to change.

### Draw order

Everything that sorted by `x + y` sorts by the front edge `y` instead: `render.js` (places, player),
`campus.js` (ground tiles, planters, trees), `nova.js` (canopy, columns, roofs, `roofDepth`),
`rooms.js` (`onTop`, `frontDepth`, stools, employees, room people, plants, columns), `walkers.js`,
`beach.js`. Fixed depths (`46.98`, `43.2`, `46.4`, ...) are checked one by one. Within the same `y` a
small `x` share keeps the order stable, so nothing flickers.

### Walking

- Keys (`main.js`): W / ↑ = north (y−1), S / ↓ = south (y+1), A / ← = west (x−1), D / → = east (x+1).
  Two keys at once walk diagonally at the same speed as before.
- Click to walk keeps working through the new `canvasWorldPoint`.
- The OUTSIDE / NOVA switch: the prototype showed the player stopping halfway. Check it on `main`
  first; fix it here only if this branch caused it.

### What is cut to the diagonal view

- **Walls of the Nova** (`nova.js`, `wallHeight`): only the south wall faces the camera now. A south
  wall sinks to the rim when its roof is gone; east and west walls keep their height. The data field
  `hides` keeps working as before.
- **Roofs** (`roofs.js` untouched): each wing still fades when the player enters it. `fadesWith`
  in `world.py` is not changed; if a roof now hides a different wing, that is listed in "Known
  issues" of the PR, not fixed in `world.py` (see Out of scope).
- **Floor captions** (`drawSpaceCaption` in `primitives.js`, room labels in `rooms.js`): no more
  rotation along the diagonal, the text lies flat and straight.
- **Rings and shadows** on the floor (`floorRing` in `rooms.js`, and `drawFootprintShadow` in
  `primitives.js` for the shadow under a footprint): an ellipse with width `TILE` and height `DEPTH`
  per tile. The rescue boat is sized the same way.
- **East and west faces** are seen edge-on: `drawFacadeBandX` (bands on a face along y) draws nothing,
  the Nova's east ledge and fins and the side art of the delivery lorry (ribs, stripes, name, side
  wheels) are not drawn; the lorry shows its front wheels instead.
- **Figures** (`characterView` in `people.js`): facing north shows the back, south the front, east
  or west the profile.
- **Overhead parts** (the canopies of the Nova and the Dorm) sort by their front edge, so a person
  under them is drawn behind them; a roof sorts just after its south wall.
- **Hand-set pixel offsets** that follow the old diagonal (for example the kite string on the beach)
  are made horizontal or vertical. Shapes and colours stay.
- **View range and zoom**: the culling margins in `campus.js` use `TILE` / `DEPTH`. The zoom levels in
  `main.js` stay as they are (see Decide 5).
- **The Dorm's canopy** (`drawDormFront` in `beach.js`): seen from the front it stands over the first
  row of the room, so it fades with the Dorm's roof, as the Nova's canopy already does.

## Look

From the front at a slight angle from above, like a top-down RPG: you see the roof (top) and the south
front of every building, never the east or west face. The figures keep their art; only which side
of them shows is worked out for the straight view.

## Decide

1. **Depth 0.7 (decided by David, 2026-11-09):** one tile into the picture is 0.7 of a tile across.
   A full square (1.0) looked almost straight from above with very large roofs; 0.7 reads more "from
   the front" and shows more of the campus at once.
2. **Walls and roofs from the front:** south walls are the fronts that sink to a rim when the roof
   fades; east and west walls show as their thin tops. No new wall art.
3. **Name `isoPoint` kept:** renaming 380 calls would only make the diff harder to review. The
   comment at the function says it is now a straight view.
4. **Tests:** no browser test exists. A new file `tests/test_map_view.py` reads the files, like the
   other tests of the pages: `isoPoint` uses `TILE` and `DEPTH`, `TILE_W` / `TILE_H` and the diagonal
   rotation are gone, no `x + y` sort key, the keys walk straight, only the south wall is a front, no
   `Math.random` in `static/world/`. No old test changes.
5. **Zoom unchanged:** one tile now covers 44 × 30.8 ≈ 1,355 px², before it was 76 × 38 / 2 = 1,444 px²,
   so the same zoom shows about as much of the campus as before. Checked in the browser.

## Out of scope

- The map layout and the places in `world.py` (spec `map-layout`), including `fadesWith` and `hides`.
- Game rules, the API, the saved state.
- New art, shop looks, new figures, weather.
- The Dorm's day flow (`day-cycle`, #64).

## Done when

1. **Camera:** `isoPoint` and `canvasWorldPoint` are the straight view with depth 0.7, and a click
   lands on the tile under the pointer.
2. **Order:** nothing sorts by `x + y` any more; the player is drawn correctly in front of and behind
   the beach-way gate, the Surf Shop, counters, trees and walkers.
3. **Walking:** WASD / arrows walk straight north, south, west, east; click to walk works on the
   campus, in every wing of the Nova, at the Dorm and on the beach.
4. **Nova:** the roof of each wing fades when the player enters it; south walls sink to a rim; the
   rooms are fully visible.
5. **Captions:** floor captions are straight.
6. **Sea at the bottom** of the screen, the campus on one horizontal line.
7. **Checked in the browser:** main view and the small window on the dashboard, no console errors.
8. **Tests:** `uv run pytest` passes, `tests/` unchanged apart from the new `tests/test_map_view.py`.

## Known issues (not part of this spec)

- **Click to walk sometimes gives up halfway**, for example from inside the Nova to the Dorm. It
  happens without any camera: a replay of `findPath` and the walk loop in Node with the data of
  `/api/world` stops at the corner of `hub-west-wall`, because the planned line passes the corner with
  less room than the walk needs, and the walk gives up after 0.5 s (`stuckFor` in `main.js`).
  `paths.js`, `physics.js` and `world.py` are unchanged on this branch, so `main` has the same bug.
  Proposal: its own small spec (more clearance in `straighten`, or a new route instead of giving up).

- **Slices along x** (`sliced` in `rooms.js`, the planter and canopy slices): they were cut so a
  person beside a long piece sorts right in the diagonal view. Now all slices of a piece share one
  front edge, so they bring nothing for the order, but they also change nothing on screen. Left as
  they are (found by the AI review); merging them is a cleanup for later.

## Security

Drawing only. No input from outside, no new request, nothing loaded from outside the app, no
`Math.random`. Sections 3a/3b of `docs/feature-roadmap.md` are not touched.
