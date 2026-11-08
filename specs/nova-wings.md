# More wings for the Nova (`nova-wings`, issue to be opened)

Built on 2026-11-08 on the branch `nova-wings`, waiting for the team's review. It builds on `walk-in`
(that spec has to be merged first). It started from Felix' question why the Mercado cannot be entered
and why the Nova has only one block. The open points are in "Decide".

## What

After `walk-in` the Nova is one block of three parts side by side. The two old outdoor buildings
beside it, the **Learning Center** (west, x 2.2 to 10.6, y 3.25 to 8.4) and the **Mercado Supply
Hall** (south-west, x 3.15 to 11.4, y 8.85 to 13.3), are solid blocks: no entrance, no inside. From
outside they look like wings of the Nova and cannot be entered.

This spec turns the Nova into a campus of several wings, all walked into the same way as the main
building:

| Wing | Where | What it is |
|---|---|---|
| `nova` | the main block of `walk-in` (22 × 8 tiles) | atrium, Cafe, Merchandise, Print Corner. Unchanged. |
| `learning-center` | west of it, joined to its west wall | a **Study Hall** (bookshelf wall, two long tables) and a **Seminar** corner |
| `mercado` | south of the Learning Center, a finger pointing south | the **Supply Hall**: storage rack, pallets, crates, an aisle in the middle |
| `hub` | south of the Nova's east part, a finger pointing south | the **Student Hub**: a Lounge with two sofas and a Meeting Room |

The two fingers point towards the sea, like on the official campus map, and the courtyard with the
pool lies between them. The wings are joined by openings in their shared walls, so one can walk from
the Study Hall through the Nova into the Hub without going outside. The rooms are places only: who
works there and what happens there comes with later specs, no rule is added here.

Each wing has its own roof. Walking into a wing fades **its** roof out (about half a second, as in
`walk-in`) and shows its rooms; a closed wing shows nothing inside. Seen from the camera (which looks
from the south-east), a wing that stands in front of another one would hide it, and a wall in front of
a wing hides it as well. So a wing names the wings that stand behind it (`fadesWith`): its roof fades
too while the player is in one of those. A wall can name the wings it hides (`hides`) and sinks to a
low rim while one of them is open, like the front walls of every wing do for their own wing.

### Data (`world.py`)

- `NOVA["wings"]`: a list of `{id, label, fadesWith}` for the four wings above. `fadesWith` of `nova`
  is `["learning-center"]` (the Nova is east of the Learning Center and hides its east half), of
  `mercado` it is `["learning-center"]` (the Mercado is in front of it), of `hub` it is `["nova"]` (the
  Hub is in front of the Print Corner), of `learning-center` it is empty.
- Every entry of `NOVA["parts"]`, `["walls"]` and `["entrances"]` and of the areas, solids and
  activities of `INTERIORS["campus"]` has a `wing`. The lists stay flat over all wings, so the code
  and most tests of `walk-in` keep reading them. A wall has a `side` (the side of its wing it is on)
  and, where it stands between two wings, `hides`.
- `NOVA["openings"]`: the passages between two wings, `{id, x, y, width, side, between: [wing, wing]}`,
  2 tiles wide, in the wall the two wings share. The wall is written around them like around an
  entrance (`side` tells along which axis they run). One in the Nova's west wall (towards the
  Learning Center), one in the wall between the Learning Center and the Mercado (it is the Learning
  Center's south wall), one in the Nova's south wall (towards the Hub).
- `NOVA["entrances"]` has two more entries, both on the **south** side (the plaza side): one into
  the Mercado, one into the Hub. The Learning Center has no entrance of its own: it is reached
  through the Nova or the Mercado.
- Footprints in tiles (the first numbers of this spec moved so that the walls meet): Learning Center
  x 2.2 to 11.5, y 3.25 to 8.65; Mercado x 3.15 to 11.5, y 8.15 to 13.3 (its north wall is the
  Learning Center's south wall); Hub x 27.5 to 33.5, y 9.2 to 14.2 (its north wall is the Nova's
  south wall). The floor of a wing is the box around its places.
- What stood where the wings stand moves or goes: the outdoor blocks `BUILDINGS` (the `buildings` key
  of `GET /api/world` goes with them), `library-planter` and `mercado-planter` (the wings draw their
  own fronts), the tree at (2, 8) (now at (1.8, 10.6)), the tail of `academic-planter-east` (it ends at
  x 27.4 where the Hub begins). The canopy and the columns of the Nova give way to the Hub: the
  browser cuts them where another wing stands in front of the main block.
- The fences behind the buildings follow the wings: one north of the Learning Center (x 0 to 11.5,
  y 0 to 3.25), one west of it (x 0 to 2.2, y 3.25 to 8.65), the north-east one is unchanged.
- The three desks keep their ids, their actions and their places (two in the atrium, one in the
  Cafe). Moving the supply desk into the Mercado is for `shop-walk`.
- `INTERIORS["campus"]` has the rooms of the three new wings in the same format as today: `areas`
  that split each floor between them, `solid` pieces, `activities` (two or three people each). Every
  gap between two pieces is either shut (at most 0.5) or at least 1.4 wide, the rule of `walk-in`,
  checked by the walking tests below. No new poses.

### Browser (`static/world/`)

- `roofs.js` (pure, testable with Node): keeps `ROOF_SECONDS`, `insideParts`, `stepRoof` and `areaAt`
  as they are and adds `wingsAt`, `roofGoesOut` and `stepRoofs`. The roof is a map from wing id to
  opacity. `wingsAt(point, parts)` says which wings the player stands in: none outside, the wing under
  the player, and at an opening both wings it joins. `stepRoofs(...)` moves the roof of every wing
  towards 0 if the player is in it or in a wing that is named in its `fadesWith`, towards 1 for the
  rest, with the speed and the reduced-motion rule of `stepRoof`.
- `scene.js`: `scene.roof` becomes `scene.roofs` (opacity per wing); `scene.wing` (the wing of the
  player, or null) is added; `scene.inNova` stays and is true in any wing, so the zoom and the chips
  in `main.js` keep working. `roofOf(id)` and `wingIsOpen(id)` read them.
- `nova.js`: walls, canopy, roofs, gallery, shadows and plinths are drawn per wing from the data.
  A wall sinks to the rim when a wing it hides is open. The roof of a wing is sorted after everything
  inside it (its depth comes from its footprint, not a fixed number). The rooms of a wing are drawn
  while its roof is thinner than 0.98, so an open wing can be seen into from the next one.
- `rooms.js`: floors (carpet, timber, concrete), entrance mats, window light, furniture and people for
  every wing, in the same style as the Nova. Wide pieces are drawn in slices, pieces against a side
  wall in slices along y.
- `campus.js`: the outdoor Learning Center and Mercado are gone; only the planters along the facades stay.
- `main.js`: the banner shows the place inside (or the name of the wing) and "Nova Coast Campus" outside;
  the chips in `static/map.html` stay "Outside" and "Nova" (the Nova includes all its wings).
- `paths.js` and `physics.js` need no change: openings and entrances are gaps in the wall rectangles.

## Look

As in `walk-in` ("Look"): white volumes, flat roofs with a thick edge, dark glass fronts, slim columns.
The Learning Center keeps its roof garden and a teal line along its front, the Mercado a yellow one.
The Hub is the lightest wing, with the most glass and a coral line. The fingers are long and low
(the Mercado and the Hub are lower than the Learning Center), and the courtyard between them stays
open to the south.

## Decide (my recommendations)

1. **One roof per wing, or one roof for everything.** Recommendation: per wing, with `fadesWith`.
   Otherwise a step into the small Mercado strips the roof off the whole Nova. The price is the
   `fadesWith` data and a roof opacity per wing. The alternative is simpler (the whole joined campus is
   one building with one roof, as in `walk-in`), but it shows everything at once and gives up the
   closed, unseen wings. Felix decided "the whole roof at once, no per-room roofs" for `walk-in`; this
   spec does not change that inside one wing, so it needs the team's yes.
2. **The Hub, a new wing.** Recommendation: yes. It makes the courtyard a courtyard between two
   fingers, like the real campus. It was removed in `walk-in` because it hid the Print Corner;
   `fadesWith` solves that. If the team wants a smaller spec, build the Learning Center and the
   Mercado first and the Hub as a second PR.
3. **All entrances on the south side.** The tests of `walk-in` sample an entrance from the south.
   Entrances on another side would need different samples. The Learning Center has none of its own.
4. **Tests of `walk-in` that this spec changes.** They are in a file of the previous spec, so the
   change needs an exception that David confirms (as `walk-in` needs one for `world-api`). Four assume
   one rectangle, one entrance or that every part is joined on all sides (checked against
   `tests/test_walk_in.py` on 2026-11-08, the Node ones by running them in the browser):
   - `test_the_places_split_the_whole_floor_between_them`: the floor is the bounding box of all parts,
     and the areas must fill it. With the wings the box holds the open ground between them.
   - `test_the_rooms_have_no_dead_corners_for_a_player_to_get_stuck_in`: the same box, one door
     (`entrances[0]`), and "more than 40 % of the box is free".
   - `test_the_roof_fades_with_the_real_roofs_module` (Node): it expects `(5, 5)`, "the ground west of
     the building", to be outside, and it treats the west edge of every part after the first as a seam
     inside the building. Both are the Learning Center now.
   - `test_every_desk_is_reached_on_foot_from_outside_through_the_entrance` (Node): it counts only the
     first entrance as the way in, but from the plaza in front of the Mercado the way to a desk now
     leads through the Mercado.
   Recommendation: take the floor of each wing instead of the box, look at all entrances, and move the
   point and the seam loop; weaken no check. The new checks are in `tests/test_nova_wings.py` and
   cover the same ground for every wing. Every other test of `walk-in` keeps passing as it is, because
   the flat lists and the exports of `roofs.js` stay. Until the exception is confirmed the existing
   tests are left as they are (the same rule as in `walk-in`); the two Python ones then fail, the two
   Node ones fail on GitHub Actions.
5. **Order.** After `walk-in` is merged; before `nova-zones`, which then redraws the map around the
   finished building. `nova-zones` no longer decides what becomes of the Learning Center and the
   Mercado.
6. **Reading `GET /api/world`.** The key `buildings` is gone. `test_the_api_serves_the_whole_world` in
   `tests/test_world_api.py` reads it; that test is one of the seven `walk-in` already needs an
   exception for.

## Out of scope

The Dorm, the way to the beach, the Surf Shop and the Beach Cafe (`nova-zones`). The day cycle
(`day-cycle`). Moving the supply desk or any desk, stock in the Mercado, who works in which wing,
guests in the Hub (`shop-walk`, `staff`, `guests`). A walkable upper floor (the gallery stays a picture).
Weather effects. Final art (`nova-design`). Any rule for money, stock or time: where the player stands
changes no rule, and no rule may read it.

## Done when

1. `uv run pytest` passes. Only the tests named in "Decide" 4 changed, and the change is explained in
   the PR. New checks are in `tests/test_nova_wings.py`.
2. The data is complete and consistent: four wings, and each part, wall, entrance, area, solid and
   activity belongs to one of them; the openings join two wings and are 2 tiles wide, and no wall or
   solid covers an opening or an entrance; the parts form one connected footprint; the three entrances
   are on the south side and at least 2 tiles wide; a player of the real size passes through each of
   them; the spawn is free; the places of each wing split its floor between them; every solid and every
   person stands on the floor of its own wing; the walls meet only at their corners; every wing has its
   own floor, at least four props and two people.
3. A test walks the grid of `paths.js` over the data from `world.py` with a player of the real size:
   every free spot inside every wing can be walked to from the spawn, and every one has a grid point
   next to it that is connected to it (a gap too narrow for the grid would make a click there do
   nothing). Every wing and every desk can be reached on foot, and only through an entrance or an
   opening. A Node test runs the real `paths.js` and `physics.js`: from many places outside and inside,
   all three desks are reached, the way never crosses a wall, from outside it uses an entrance, and one
   can walk from every wing to every other and out to the plaza.
4. A Node test runs the real `roofs.js`: in one wing its roof goes out and the others only if they name
   it in `fadesWith`; in an opening both wings are open; walking a line through every entrance and
   opening never takes the player outside while crossing an opening and never makes a roof flicker;
   the roof of a wing the player is in never gets thicker; the opacity ends exactly on its target, takes
   about half a second, and jumps with reduced motion.
5. In the browser: walking or clicking from the plaza into the Mercado fades its roof and shows
   its rooms; walking on through the opening into the Learning Center opens that roof (and, because they
   hide it, the Mercado's and the Nova's) and into the Nova works without a flicker; the Hub opens when
   the player stands in the Hub or in the Nova; walking out brings every roof back. A closed wing shows no
   people inside. Sun, light and sea stay visible from inside every wing. The three desks work as before.
   No console errors; the page also works in the live window of the dashboard.
6. A save with a position inside any wing loads inside that wing with its roof open; the position
   survives a restart.
7. The wings are recognisable as the Nova (checked against "Look", with a screenshot of each wing in
   the PR).
8. All new code: no `Math.random`, nothing loaded from outside, labels set with `textContent`. The
   README (spec table, known issues) and the roadmap (rows for `nova-wings` and `nova-zones`, issues
   list) are up to date.
9. PR "Closes #<issue>", AI code review done and its findings handled.

## Security

As in `walk-in` (roadmap 3a and 3b): the zone id stays on the whitelist (`campus`), and
`POST /api/player` still checks that the position is finite and inside the bounds of the zone, which
must still hold every wing. No rule depends on the position the browser sends. The new data is fixed
on the server and only read by the browser. Names and labels are shown through `textContent`; no
external asset and no `innerHTML` with data.
