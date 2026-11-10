# Render cache

Issue #86. Found in the audit (`docs/audit-report.md`, items P4 and P5). `smooth-frames` (PR #77) came
first and removed the big cost; this takes what is left.

## What

The campus does less work and allocates less in every frame, and draws exactly the same picture.

1. **Tiles once.** `drawTerrain` (`static/world/campus.js`) builds the tile list of a zone with its
   colours and its back-to-front order once (`tilesOf`) and keeps where each row starts, so a frame walks
   only the rows in view. `drawTile` works the corners out with `isoX` and `isoY` (new in `scene.js`,
   the one definition of the projection that `isoPoint` is built from) instead of making four objects
   per tile.
2. **Walls and canopy once.** `novaActors` (`static/world/nova.js`) builds the wall slices and the canopy
   from the building's data once; their draw functions still read the roofs when they draw. They are
   built again when the building, its parts or walls, or their number change.
3. **Out of view, not drawn.** `drawWorld` (`static/world/render.js`) skips actors whose rows are far
   above or below the view. The rules are in `static/world/cull.js` (pure, tested with Node): 640 px up
   (the longest hedge reaches about 424), 5 rows down (a pool of lamp light reaches about 105 px). An
   actor flagged `always` is never left out (the kites, the gulls, the tide pools: no depth guess).
   `options.cull = false` switches it off (the check below).

(A cache for `mixColor` was tried and dropped in review: the tile list already makes each colour once,
and the callers with a moving amount, like the sky, only ever missed.)

## Out of scope

The roof fade (P3: it costs about 5 ms a frame on a busy machine, but a cached roof needs the rooms
and the sort order rethought), new looks, the canvas resolution, `beach.js` rebuilding its object
list every frame, weather visuals.

## Done when

1. The picture is the same, checked in the browser (one window, old and new side by side): the terrain
   and the Nova's walls, canopy and rooms give the same pixels at 5 places; with the culling on or off
   358 views (3 zoom levels, many places, roofs closed and open, by day, at dusk and late in the
   evening when the lamps glow) give the same pixels.
2. Measured side by side on one machine with the first version of this change (the plaza, the beach,
   inside the Nova): the JavaScript time of a frame was lower by about 10 % (3.01 / 2.83 / 3.24 ms
   before, 2.75 / 2.52 / 2.90 ms after) and the allocation per frame lower (944 / 763 / 1016 KB before,
   575 / 451 / 635 KB after; this sampling varies by up to 40 % between runs), at 60 frames a second.
   After the review the colour cache was dropped and the row index added; the timing was **not**
   measured again (the browser connection was lost), only the picture check above.
3. `tests/test_render_cache.py`: the rules of what is in view run with Node (tall objects and light
   reach in, far ones do not, `always` is always drawn, rows are clamped); source checks keep the other
   pieces in place (there is no browser in the tests). `uv run pytest` passes, `tests/` untouched.

Rules: nothing here touches money, state, randomness or the API; the drawing stays a function of the
state and the time only.
