# The map around the Nova (`nova-zones`, issue #28 to be rewritten)

Written on 2026-11-08 on the branch `nova-zones`, started from `main` after `walk-in` (#49) and
`nova-wings` (#50) were merged. Decisions come from Felix after David's voice memo (the day starts and
ends at the Dorm, a way to the beach, the Surf Shop and the Beach Cafe stand outside). Felix, on
2026-11-08: the map keeps its size; the look of the beach, the beach way and the shops matters a lot
and gets a lot of detail; the Dorm gets a real function, not only a facade. The open points are in
"Decide".

## What

The Nova is finished (four wings, walked into). The ground around it is still the plain campus of the
solo project. This spec fills the south and the east of the map with the places David described and
draws them with much more care than the rest: arrive, work in the Nova, sleep in the Dorm, walk down
the beach way to the sea.

| Place | What it is | New? |
|---|---|---|
| **Dorm** | a small student residence east of the Hub that can be **walked into**: one room with a bed. The place where a day starts and ends (the function is in its own section). | yes |
| **Beach way** | a 4 tile wide boardwalk from the plaza in front of the Nova south to the sand, with an arch at its start, a few lamps and two benches at the sand end (kept sparse on purpose) | yes |
| **Surf Shop** | an open-air pavilion on the sand, west of the way: counter, awning, a rack of boards, a wetsuit rail | yes |
| **Beach Cafe** | an open-air pavilion on the sand, east of the stage: bar, awning, tables with parasols, string lights (replaces the Food Court) | yes |
| **Beach** | a deeper strip of sand (from y 20, the old promenade and Event Square paving are gone) with ripples, footprints, a few loungers, dunes, a volleyball court, a lifeguard tower, a shoreline with foam, the sea | changed a lot |
| **Plaza and courtyard** | the ground in front of the Nova, kept | no |

The map keeps its size, except for the beach, which grew by two tiles to the south (see the end of this spec): the spawn and the rest of the walkable area do not change. The shops are places to see and walk to; their rules are in `shop-unlock` and `shop-process`,
using them by walking is `shop-walk`. No desk is added in the shops; the three desks stay in the Nova.

### The Dorm and its function

The Dorm is the first place of the day and the last: in the end the player wakes up here to start a
day and goes to bed here to end it (`day-cycle`, with the evening report of `outlook`). Those two
specs do not exist yet, so here the Dorm gets everything that does not need them:

- **A real building.** One room (about 5.4 × 5 tiles) entered the same way as a wing of the Nova: an
  entrance on the south side, its roof fades while the player is inside, its walls facing the camera
  sink. Its data (`DORM`, same shape as the Nova: wings, parts, walls, entrances, openings) is kept apart
  from `NOVA`, because the tests and the code of the Nova count four wings and one joined footprint. The
  browser joins the two when it loads (`zones.js`, `joinDorm`), so the roof code (`roofs.js`, `nova.js`,
  `rooms.js`) is reused and not copied.
- **A room with life.** A bed (the use point), a desk with a laptop and a lamp, a wardrobe, a shelf
  with books and a plant, a rug, a window to the sea, a poster, a corkboard with the day's notes. One
  person (a flatmate asleep or at the laptop) in the same figure style as the Nova's rooms.
- **A use point: the bed.** Using it (E, click or the hint) opens a small **Dorm panel** in the same
  style as the desk panels. It shows what the server already knows, as text: the day number, the cash
  and the day's weather. It has one button that does what the
  Open button of the map already does (`openDay()` in `ui.js`: start the day clock, or let the time
  pass while a shift runs). No new endpoint and no new rule: the panel only calls what exists. What
  "Sleep" means (the evening report, forecast, the next day starting here) is `day-cycle`, which
  replaces this button.
- **A new place.** `DORM["bed"]`: `{zone, x, y, kind: "panel", action: "dorm", label: "Go to bed", wing:
  "dorm", ...}`. It is not in `LOCATIONS`, whose three desks the tests of `walk-in` and `nova-wings`
  pin; the browser adds it to the places (`joinDorm`) and shows it while the roof of its wing is gone
  (`openPlaces` in `locations.js`). `useLocation("dorm")` opens the panel.
- The spawn stays (21, 18) (see Decide 5): a new run still starts on the plaza. The walk to the Dorm
  is short and shows the new map.

### Data (`world.py`)

- `DORM`: `{id, label, wall, wings, parts, walls, entrances, openings, interior, bed}` in the shape of
  `NOVA`. Footprint x 35.0 to 40.5, y 7.6 to 12.6 (it touches the fence behind it and leaves 1.5 tiles to
  the Hub); the entrance (2 tiles wide) is on the south wall. Its walls and furniture are solids, its
  entrance and its floor are free. `interior` holds the Dorm's `areas`, `solid` pieces and `activities`
  (`wing: "dorm"`), in the format of `INTERIORS["campus"]`, which stays as it is.
- `SHOPS_OUTDOOR`: `{id, label, x, y, w, h, front: {x, y}}` for `surf-shop` and `beach-cafe`. Counter and
  posts are solids; the area under the awning in front of the counter is free. `front` is the free
  spot where the shop will be used (`shop-walk`). The ids are the shop ids of the roadmap; no rule
  reads them yet.
- `BEACH_WAY = {x, y, w, h}`: the boardwalk, at least 3 tiles wide, from the south edge of the plaza to
  the promenade, free to walk. The props along it (lamps, planters, benches, signs) are solids with
  gaps of at least 1.4 (the rule of `walk-in`) between them and the boardwalk.
- `BEACH`: the data the drawing reads so that the code has no magic numbers: `{loungers, dunes,
  footprints, buoys, boats}` (positions and sizes, fixed on the server, not random).
- `SPACES`: `foodCourt` is replaced by `beachCafe` ("Beach Cafe") and `surfShop` ("Surf Shop"); `dorm`
  ("Dorm") and `beachWay` ("Beach Way") are added. `lawn` and `promenade` stay. The passers-by
  (`walkers.js`) walk between them.
- Moved or removed: the terrace tables and trees that stand where the new things stand (`TREES`,
  `TERRACE_TABLES`), the Food Court. The east lawn gets smaller to make room for the Dorm.
- `GET /api/world` gets `dorm`, `outdoorShops`, `beachWay` and `beach`; the existing keys stay.
- The beach way has an arch with a sign at its start (two posts, solids), two lamps every 2 tiles and
  two benches; the beach has seven loungers, two dunes, a volleyball net and a lifeguard tower (solids,
  all in `world.py`).

### Browser (`static/world/`)

All of this is drawn in code, in the style of the rest (flat shapes, soft shadows, accent colours),
with the detail below. It is **the most careful drawing of the map**.

- **Beach way** (`campus.js` or a new `beach.js` module): planks in two alternating tones with
  gaps, a darker border beam, nails as dots, a worn centre line, wind-blown sand over the edges,
  a lamp every 4.5 tiles with a small warm light cone at dusk, planters with grass and one palm at
  the start, two benches with a bin, signposts ("Surf Shop", "Beach Cafe", "Beach" with arrows),
  a low rope fence where the way crosses the dunes, and steps down to the sand.
- **Beach:** sand drawn with ripple lines and two tones, wet sand near the water, footprints between
  the way and the water, shells and a starfish, driftwood, dune hills with grass tufts that sway
  slightly, beach loungers and parasols in rows, a volleyball net, a lifeguard tower with a flag,
  a shoreline where foam moves in and out (a wave animation from the clock, no `Math.random`),
  buoys and a small boat on the water, gulls (a few, simple, moving on a loop).
- **Surf Shop:** a timber and white pavilion, teal awning with stripes, boards of different colours on
  a rack, a wetsuit rail, a sign with a wave, a counter, a till, a small chalk board with prices
  (text only, no data), a surfboard stuck in the sand, a lamp.
- **Beach Cafe:** a bar with a coral awning, stools, a menu board, string lights on posts, five tables
  with parasols and chairs, a cooler box, a small speaker, glasses and bottles on the bar.
- **Dorm** (outside): white block with warm timber slats on the door side, windows, a roof garden, a bike
  rack with two bikes, a bench at the door, a mailbox, a threshold deck with a welcome mat, flagstones
  to the plaza, a strip of grass with flowers towards the Hub and the sign "DORM" on its roof.
- **Dorm** (inside): the room of the section above: timber floor, a rug, a bed with pillows and a
  blanket, a wardrobe, a bookshelf, a desk with laptop, lamp and book and a chair, a poster, a cork board
  with notes, a plant, a flatmate at the desk and windows along the walls.
- **Light:** the dusk and night colours of `environment.js` are used for the lamps, the awnings and the
  string lights so they switch on when it gets dark (an option of the drawing, no new rule).
- **Edges:** no void shows at the edge of the map at the smallest and largest zoom.
- Labels (names on signs, captions of the spaces) are written with `textContent` where they are
  DOM, and drawn as canvas text where not; no data is evaluated.
- The roof logic is not copied: `joinDorm` makes the Dorm one more wing of the joined data, so
  `roofs.js`, `nova.js` and `rooms.js` draw and fade it like the others (`LOOK.dorm` in `nova.js` says how
  it looks). The beach, the way and the shops are drawn by `beach.js`.

## Look

The Dorm: white and warm timber, like a small sibling of the Nova. The Surf Shop and the Beach Cafe:
light, open, seaside, awnings in the Nova's accent colours (teal and coral). The beach way: the one
clear line on the map, from the glass front of the Nova straight down to the water, so one sees where
to go. The beach should feel lived in: things lying around, things that move (waves, flags, gulls,
grass), things that light up in the evening. Final polish of the whole game is `nova-design`.

## Decide (my recommendations)

1. **Where the Dorm goes.** Recommendation: east of the Hub (x about 35 to 40.4, y about 8.4 to 13.4),
   entrance on the south side: next to the Nova, away from the beach way, on ground that is empty.
   The alternative is the west, behind the Learning Center, which is fenced off.
2. **The map keeps its size.** Decided by Felix on 2026-11-08. `ZONES["campus"]` does not change, so
   the saved positions, the spawn and every test of the walkable area keep holding.
3. **The Dorm is a walkable room, with a bed that opens a panel.** Recommendation: yes (Felix wants the
   Dorm to have a function). The panel only shows server data and calls what the Open button already
   calls, so no new rule, endpoint or test of the economy is touched. If the team prefers the Dorm to
   stay a facade until `day-cycle`, the room and the panel can be cut without changing the rest.
4. **Open-air shops, no interior.** Recommendation: yes. Surf Shop and Beach Cafe are pavilions the
   player walks up to, as David said ("outside"). Walking into a roofed shop is not needed.
5. **The spawn stays (21, 18).** `day-cycle` moves the start to the Dorm. Keeping it here means no
   existing test changes (`test_a_new_run_starts_at_the_spawn` and the saved-position tests use it).
6. **Tests: no change in `tests/`.** Built that way: the Dorm is kept apart from `NOVA`, `INTERIORS` and
   `LOCATIONS` (all three are pinned by the tests of `walk-in` and `nova-wings`), and the browser joins
   them. All 401 existing tests (and their Node scripts, run in the browser: 486, 711 and 75 checks) pass
   unchanged. The new checks are in `tests/test_nova_zones.py`.
7. **Size of this spec.** The drawing is large (beach, way, two shops, Dorm inside and outside). If
   it grows too big for one PR, the cut is: PR 1 the beach, the way and the two shops; PR 2 the Dorm
   with its room and panel. Both would still be `nova-zones` (a second issue then).

## Out of scope

The evening report, the forecast and the next day starting at the Dorm (`day-cycle`, `outlook`). Desks,
prices, stock or unlocking at the Surf Shop or the Beach Cafe (`shop-unlock`, `shop-process`,
`shop-walk`). Moving the spawn. Making the map smaller. Weather effects over the new places
(`weather-visuals`), outfits, guests. Any rule for money, stock or time: where the player stands
changes no rule, and no rule may read it. The Dorm panel is the only new place that calls an existing
request.

## Done when

1. `uv run pytest` passes. No existing test changed (or each change is named in "Decide" 6 and in the
   PR, confirmed by Felix). New checks are in `tests/test_nova_zones.py`.
2. The data is complete and consistent: the Dorm, the two shops and the beach way each have an id, a
   label and a footprint inside the walkable area; no two footprints overlap, none overlaps a wing, a
   fence or an entrance of the Nova; every `front` spot, the Dorm's entrance and the bed are free for
   a player of the real size; the Dorm's floor is split by its areas, every solid and person stands on
   it, and it has at least four props and one person; the beach way is at least 3 tiles wide and
   free; the gaps between the props are shut (at most 0.5) or at least 1.4; the spawn is still free;
   the `BEACH` data has no random values (the same twice).
3. A walking test (the grid of `paths.js`, real size) shows: from the spawn the Dorm's bed, both shop
   fronts and the end of the beach way on the sand are reachable on foot, the Dorm only through its
   entrance; every named space of `SPACES` is reachable; the three desks are still reached (the
   checks of `walk-in` and `nova-wings` keep passing).
4. A Node test runs the real `roofs.js`: in the Dorm its roof goes out and the Nova's do not; outside
   they come back; it takes about half a second and jumps with reduced motion.
5. The Dorm panel: using the bed opens it; it shows the day, the cash and the weather from the state
   (escaped); its button calls `openDay()`, the same function as the Open button, and there is no new
   endpoint (a test reads `ui.js` and the routes of the app). A rejected request changes nothing, as
   before, because the server decides.
6. In the browser: everything of "Browser" is drawn and cannot be walked through where it is solid;
   the waves, flags, gulls, grass and lights move without `Math.random` and without stutter (the
   frame time of the map stays close to the one before this spec); the lamps and string lights go on at
   dusk; the passers-by walk to the new spaces; no void at any edge; the Nova still opens and closes
   its roofs; walking into the Dorm opens its roof and shows the room; the bed opens the panel; the
   position survives a restart (also inside the Dorm); no console errors; the page also works in the
   live window of the dashboard.
7. The new places are recognisable and carefully drawn (checked against "Look", with a screenshot of
   the beach way, the beach, each shop and the Dorm inside and outside, in daylight and at dusk, in
   the PR).
8. All new code: no `Math.random`, nothing loaded from outside, labels set with `textContent`. The
   README (spec table, known issues) and the roadmap (row `nova-zones`, issues list) are up to date.
9. PR "Closes #28", AI code review done and its findings handled.

## Security

As in `walk-in` and `nova-wings` (roadmap 3a and 3b): the zone id stays on the whitelist (`campus`),
and `POST /api/player` still checks that the position is finite and inside the bounds of the zone,
which must still hold the Dorm; the bounds do not change here. No zone change is added (one
continuous map). No rule depends on the position the browser sends: the Dorm panel's button sends the
same request as the Open button, and the server decides as before (a request on a finished or
already opened day is refused and changes nothing). The new data is fixed on the server and only read
by the browser. Names and labels are shown through `textContent`; no external asset and no
`innerHTML` with data.

## Built differently from the first draft

After Felix saw the first build ("too crammed") the beach was thinned and widened: the sand now starts at y 20, the promenade, the Event Square paving and the signposts are gone, the beach way is 4 tiles wide with four lamps, the shops moved from the paving onto the sand, there are four loungers instead of seven, and the Student Lawn is shorter so that it no longer reaches the sand. Then Felix asked for a bigger beach: the sand and the water start two tiles further south, so the drawn ground is 33 tiles high (it was 30) and the walkable area reaches y 27.7 (it was 25.7); the beach way is 10.2 tiles long. Then Felix said the beach felt pressed against the campus and lacked the look of a beach: the sand and the water moved five tiles further south, so a paved promenade (palms, benches, the Sunset Forum) now lies between the buildings and the dunes. The drawn ground is 46 tiles high (more sea in the south) and the walkable area reaches y 32.7 at that point; the beach way is 14 tiles long with a fourth lamp. The beach got a dune ridge with swaying grass, towels, beach umbrellas, a sandcastle, rocks with foam at both ends of the bay, red and yellow flags by the lifeguard tower, a beach shower, two kites, three swimmers, a line of seaweed left by the tide and water that is light turquoise at the shore and deeper further out. All of it is fixed data in `world.py` (`BEACH`) and drawn in `beach.js`. After that Felix asked for a clearer line between campus and beach, a narrower beach way, a livelier promenade and a closed map edge: a low pale wall with steps now runs between the promenade and the dunes (open at the way and at the two shops), the beach way is 3 tiles wide, the promenade has bike racks, bins, planter boxes, a drinking fountain and an ice cream cart, and the ground and the sea run past the map edge with more waves and a deeper blue far out. Last, the beach way looked laid on top of the ground: it is now pale pavers on the promenade and a weathered boardwalk behind the low wall, with sand drifting over its edges and its end; the sea moved two tiles further south (the walkable area reaches y 34.7, the drawn ground is 48 tiles high, the way is 15.6 tiles long with a fifth lamp), the sand has grains and a damp band, and the water glitters. Then Felix asked to rework the buildings on the beach: the Surf Shop and the Beach Cafe are now huts with a back wall (things hang on it), a west side wall and a roof over the strip above the counter (a striped sail roof with a surfboard sign; a palm thatch roof), so they have two new wall colliders each and the posts moved to the front edge. Then Felix said campus and beach looked like two worlds and the huts were still too small: the paving now turns warm and sandy towards the beach, sand drifts lie on it and blows through each opening of the low wall (which is lower and sand-coloured, with sand piled at its foot), grass grows through the paving, the Surf Shop has changing cabins, the Beach Cafe a kitchen container with an ice cream hatch, each has a chalk sign (new colliders: two annexes, two signs, the fire pit with three log seats), and the evening has a fire pit that burns, lit huts and bunting, and the sun's path on the water. Then Felix asked for people on the beach, a real lifeguard station with rocks, and real waves: three towels have a sunbather, three people sit at the fire pit, four play volleyball with a ball, a dog runs along the shore, two surfers ride and two people paddle (drawing only; sunbathers, the fire pit and its logs block, the players do not); the lifeguard tower is a cabin on stilts with stairs, rails and a lifeguard, with a rescue boat next to it; both ends of the bay have a rock shelf with tide pools and crabs and the east one a lighthouse whose beam turns at dusk; wave sets roll in, break and wash up the sand; and the walkers also go to the fire pit, the shore and the volleyball court (new SPACES). Then Felix said the delivery road in front of the supermarket looked wrong and asked for more care at the Dorm and the campus edge: the delivery lane now runs along the west side of the Mercado (asphalt, kerb, loading bays, pallets, a lorry, a barrier at the south end) and the Service space moved there, the lawn is soft patches instead of a chessboard, the Dorm is warm plaster with a chimney, flower boxes, a timber canopy over its door, a balcony and washing on its roof, and the east edge has a hedge, palm rows, a community garden, a bike shelter and a hammock (scenery outside the walkable area, so no new colliders). The numbers in this spec that name a position are the ones in `world.py`.
