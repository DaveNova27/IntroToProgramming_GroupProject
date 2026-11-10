# Render cache

Issue #86. Found in the audit (`docs/audit-report.md`, items P4 and P5). `smooth-frames` (PR #77) came
first and removed the big cost; this takes what is left.

## What

The campus does less work and allocates less in every frame, and draws exactly the same picture.

1. **Colours once.** `mixColor` (`static/world/primitives.js`) remembers its answers (the same two
   colours and amount asked again and again, every tile, every frame).
2. **Tiles once.** `drawTerrain` (`static/world/campus.js`) builds the tile list of a zone with its
   colours and its back-to-front order once (`tilesOf`), and each frame only walks the visible part.
   `drawTile` works the corners out itself instead of making four objects per tile.
3. **Walls and canopy once.** `novaActors` (`static/world/nova.js`) builds the wall slices and the canopy
   from the building's data once; their draw functions still read the roofs when they draw.
4. **Out of view, not drawn.** `drawWorld` (`static/world/render.js`) skips objects whose rows are far
   above or below the view (depth is about the map row; 480 px up and 3 rows down are kept).
   Depths outside the map rows (kites and gulls at 200, the tide pools at 1) are always drawn.
   `options.cull = false` switches it off (the check below).

## Out of scope

The roof fade (P3: it costs about 5 ms a frame on a busy machine, but a cached roof needs the rooms
and the sort order rethought), new looks, the canvas resolution, `beach.js` rebuilding its object
list every frame, weather visuals.

## Done when

1. The picture is the same: in the browser the terrain and the Nova's walls, canopy and rooms give the
   same pixels as before at 5 places, and with the culling on or off 198 views (3 zoom levels, 11 x 7
   places, roofs closed and open) give the same pixels.
2. Measured side by side on one machine (the plaza, the beach, inside the Nova): the JavaScript time of a
   frame is lower by about 10 % (3.01 / 2.83 / 3.24 ms before, 2.75 / 2.52 / 2.90 ms after), the
   allocation per frame is lower (944 / 763 / 1016 KB before, 575 / 451 / 635 KB after; this
   sampling varies by up to 40 % between runs), and the frame rate stays at 60.
3. `tests/test_render_cache.py` keeps the pieces in place (source checks: there is no browser in the
   tests). `uv run pytest` passes, `tests/` untouched.

Rules: nothing here touches money, state, randomness or the API; the drawing stays a function of the
state and the time only.
