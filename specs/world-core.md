# The 2.5D world (`world-core`, issue #9)

## What

The three.js map is replaced by the 2.5D world from Felix Antes' Nova Beach Ventures,
as ES modules in `static/world/`. The player walks with W A S D or by clicking the
ground, the camera follows smoothly, doors change the zone, and clicking a door or desk
walks there and uses it. The campus opens first; the dashboard stays available as a side
panel and as its own page (`#dashboard`). Stock, prices, opening a day and a new run work
from the world and stay in sync with the dashboard. All of it goes through the existing
API: the browser decides no rule. Nothing loads from outside this app any more.

Shown: the outdoor campus (Felix' coast district without expansion areas) and three rooms
(Mercado, Academic Wing, Student Hub), because this page replaces the old map and has to
be playable. `nova-zones` and `nova-design` turn this into the real Nova layout.

The code is taken from Felix' `dist/app.js`, reduced to what is used and formatted so it
can be read and reviewed. `paths.js` is new: Felix' straight walking stops at the first
bench, so a click on a far door would not arrive.

## Out of scope

The figure of the player and other people (`world-art`). Felix' economy, shops, districts,
guests, staff, overlays, build mode, day clock and localStorage save. Weather effects
(`weather-visuals`). The day clock here only moves the light; it has no rule behind it.

## Done when

1. `uv run pytest` passes. The page and every module load from this server, every import
   resolves, nothing is loaded from an external address, and the code has no `Math.random`.
2. In the browser: walking with keys and by click stops at solid objects, every door works
   in both directions, the position survives a reload, and there are no console errors.
3. Stock, prices (also a refused one), opening a day with its summary, and a new run work
   from the world and show up on the dashboard, and the other way round.
4. A click on a door or desk from anywhere in a zone finds a way there. A test runs the
   real `paths.js` with Node on the data from `world.py`.
