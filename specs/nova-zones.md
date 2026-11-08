# The map around the Nova (`nova-zones`, issue #28 to be rewritten)

Written on 2026-11-08 on the branch `nova-zones`, started from `main` after `walk-in` (#49) and
`nova-wings` (#50) were merged. Decisions come from Felix after David's voice memo (the day starts and
ends at the Dorm, a way to the beach, the Surf Shop and the Beach Cafe stand outside). The open points
are in "Decide".

## What

The Nova is finished (four wings, walked into). What is left of the old campus around it is a wide,
mostly empty ground of 90 × 30 tiles from the solo project. This spec turns it into a **smaller map
with a purpose**: arrive, go to the Nova, go to the Dorm, walk down to the beach.

| Place | What it is | New? |
|---|---|---|
| **Dorm** | a small student residence east of the Hub, with a doorstep. The day will start and end here (`day-cycle`). Here it is a building and a place, nothing more. | yes |
| **Beach way** | a boardwalk from the plaza in front of the Nova south to the promenade and the sand | yes |
| **Surf Shop** | an open-air pavilion on the beach way, west side: counter, awning, a rack of boards | yes |
| **Beach Cafe** | an open-air pavilion on the beach, east side: counter, awning, a few tables | yes (replaces the Food Court) |
| **Beach** | sand, the promenade and the sea at the south edge, kept as it is | changed a little |
| **Plaza and courtyard** | the ground in front of the Nova, kept | no |

The shops are places to **see and walk to** only. Their rules (prices, stock, unlocking) are in
`shop-unlock` and `shop-process`, their use by walking is `shop-walk`. No desk is added here: the three
desks stay in the Nova.

### Data (`world.py`)

- `ZONES["campus"]`: `width` 90 → 46, `height` 30 → 28, `maxX` 41 → 41 (unchanged), `minY`/`maxY`
  unchanged, spawn unchanged (21, 18). The ground ends 5 tiles behind the east edge of the walkable
  area; a hedge and a wall hide the edge (see Browser). The old map was twice as wide as the part
  anyone could walk on.
- New `BUILDINGS`-like list `ZONE_BUILDINGS`: `{id, label, kind, x, y, w, h, z, entrance}` for the
  Dorm. `kind` is `residence`. The `entrance` is a spot `{x, y}` on its south side, where the
  doorstep is. The Dorm is a solid block (the walking collider is its footprint); its inside does not
  exist yet.
- New `SHOPS_OUTDOOR` list: `{id, label, x, y, w, h, front: {x, y}}` for `surf-shop` and `beach-cafe`.
  The pavilion's counter and posts are solids; the area under the awning in front of the counter is
  free. `front` is the free spot where the shop will be used (`shop-walk`). The ids are the shop ids
  of the roadmap (`surf-shop`, `beach-cafe`); no rule reads them yet.
- `SPACES`: `foodCourt` is replaced by `beachCafe` ("Beach Cafe") and `surfShop` ("Surf Shop"); `dorm`
  ("Dorm") and `beachWay` ("Beach Way") are added. The passers-by (`walkers.js`) walk between them.
  `lawn` and `promenade` stay.
- The beach way is data too: `BEACH_WAY = {x, y, w, h}` (a boardwalk, at least 3 tiles wide, from the
  plaza south edge to the promenade) so a test can check that it is free to walk.
- Moved or removed: the terrace tables and trees that stand where the new things stand (the
  `TREES` and `TERRACE_TABLES` lists are edited, the `lawn-planter` and `arrival-planter` stay where
  they do not collide). The east lawn is smaller to make room for the Dorm.
- `GET /api/world` gets `dorm` (the building with its entrance) and `outdoorShops`; the existing
  keys stay.

### Browser (`static/world/`)

- `campus.js`: draws the Dorm (low white block, warm timber door side, a few windows, a small sign
  "DORM"), the boardwalk (planks along the way), the Surf Shop (teal awning, boards on a rack, a
  counter) and the Beach Cafe (coral awning, counter, three tables with parasols). The sea at the
  south and the sand keep their place, on the smaller ground. The Food Court is gone.
- The east and north-east edge: a hedge and a low wall along the new ground edge so that no void
  shows at the camera's farthest zoom.
- The roof logic and `main.js` stay: the Dorm has no inside. Walking round it is plain collision.
- Labels (names on signs, captions of the spaces) are written with `textContent` where they are DOM,
  and drawn as canvas text where not; no data is evaluated.

## Look

White and warm timber for the Dorm, like a small sibling of the Nova; the Surf Shop and the Beach
Cafe are light, open and seaside (awnings in the Nova's accent colours, teal and coral). The beach
way is the one clear line on the map: from the Nova's glass front straight down to the water.
Final polish is `nova-design`.

## Decide (my recommendations)

1. **Where the Dorm goes.** Recommendation: east of the Hub (x about 35 to 40.5, y about 8.5 to 13.5),
   entrance on its south side. It is next to the Nova (short walk to work), away from the beach way,
   and the east lawn it replaces is empty. The alternative is the west, behind the Learning
   Center, which is fenced off.
2. **Smaller map.** Recommendation: 46 × 28 drawn, walkable area unchanged, so the saved positions,
   the spawn and every test about the walkable area keep holding. A smaller *walkable* area would
   break tests that sample positions and is not needed to make the map feel smaller.
3. **The Dorm has no inside here.** A walkable Dorm is a new wing and a bigger spec. Day start/end
   happen at its doorstep (`day-cycle`), which is enough for the loop David described.
4. **Open-air shops, no interior.** Recommendation: yes. Surf Shop and Beach Cafe are pavilions the
   player walks up to, as David said ("outside"). Walking into a roofed shop is not needed.
5. **The spawn stays (21, 18).** `day-cycle` moves the start to the Dorm. Keeping it here means no
   existing test changes (`test_a_new_run_starts_at_the_spawn` and the saved-position tests use it).
6. **Tests.** I expect **no change in `tests/`**: the existing tests read the world from `world.py`
   and only need the spawn, the bounds, `SPACES`, `trees`, `planters` to exist and be free. If one
   turns out to break, the build stops there, the change is written here, and Felix, as the owner
   of this PR, confirms it in his own words (the AI never confirms for him) before it is made. New
   checks go in `tests/test_nova_zones.py`.

## Out of scope

Walking into the Dorm or any room in it. The day cycle and its screen (`day-cycle`). Desks, prices,
stock or unlocking at the Surf Shop or the Beach Cafe (`shop-unlock`, `shop-process`, `shop-walk`).
Moving the spawn. Final art, weather effects, outfits, guests (`nova-design`, `weather-visuals`,
`outfits`, `guests`). Any rule for money, stock or time: where the player stands changes no rule,
and no rule may read it.

## Done when

1. `uv run pytest` passes. No existing test changed (or each change is named in "Decide" 6 and in the
   PR, confirmed by Felix). New checks are in `tests/test_nova_zones.py`.
2. The data is complete and consistent: the Dorm, the two shops and the beach way each have an id,
   a label and a footprint inside the walkable area; no two footprints overlap, none overlaps a wing,
   a fence or an entrance of the Nova; every `front` spot and the Dorm's entrance is free for a
   player of the real size; the beach way is at least 3 tiles wide and free; the spawn is still free.
3. A walking test (the grid of `paths.js`, real size) shows: from the spawn the Dorm's doorstep, both
   shop fronts and the end of the beach way on the sand are reachable on foot; every named space of
   `SPACES` is reachable; the three desks are still reached (the walk-in checks keep passing).
4. In the browser: the Dorm, the boardwalk, the Surf Shop and the Beach Cafe are drawn and cannot be
   walked through; the passers-by walk to the new spaces; no void shows at any edge of the map at
   the smallest and the largest zoom; the Nova still opens and closes its roofs; the position
   survives a restart; no console errors; the page also works in the live window of the dashboard.
5. The new places are recognisable (checked against "Look", with a screenshot of the Dorm, the beach
   way and each shop in the PR).
6. All new code: no `Math.random`, nothing loaded from outside, labels set with `textContent`.
   The README (spec table, known issues) and the roadmap (row `nova-zones`, issues list) are up to date.
7. PR "Closes #28", AI code review done and its findings handled.

## Security

As in `walk-in` and `nova-wings` (roadmap 3a and 3b): the zone id stays on the whitelist (`campus`),
and `POST /api/player` still checks that the position is finite and inside the bounds of the zone;
the bounds do not change here. No zone change is added (one continuous map), so there is no
transition to validate. No rule depends on the position the browser sends. The new data is fixed on
the server and only read by the browser. Names and labels are shown through `textContent`; no
external asset and no `innerHTML` with data.
