# Click to walk does not stop at corners (`click-walk`)

Found while checking `map-view` (PR #67) on 2026-11-09: a click on a far place sometimes walks a
while and then stops halfway, for example from the Nova to the Dorm. It is the same on `main`
before `map-view`: it does not come from the camera. Screen only: no rule, no API, no `world.py`.

## What

`findPath` (`static/world/paths.js`) finds a way on a grid and then "straightens" it: it keeps only the
corners and cuts across wherever a straight line stays free. The line is allowed to pass a solid
object at exactly the width of the player. The walker in `main.js` never follows the line exactly
(it turns at 0.15 tiles from a point), so it drifts a hair closer, `resolveMovement` blocks it, it
makes no progress, and after 0.5 s `walk()` gives up. Example: from (23.06, 8.11) to the Dorm the route
cuts along the south end of `hub-west-wall` and stops at (27.29, 14.41).

The fix: straightening keeps a margin of `CORNER_MARGIN = 0.1` tiles more than the player's radius
from every solid object. The grid search itself is unchanged.

## Decide

1. **Margin 0.1:** 400 fixed start and goal pairs on the campus: 27 gave up before; 2 give up with 0.1,
   and the same 2 with 0.15 and 0.2, so more margin does not help. The 2 are tight spots, not corners,
   and stay as a known issue.
2. **Where:** in `findPath` (one named constant), not in `main.js`: the walker stays as it is, and the
   route is what was wrong.
3. **Tests:** the new file `tests/test_click_walk.py` runs the real modules with Node and a copy of the
   walk loop on the 400 pairs and allows at most 5 give-ups (it fails on the old code with 27). The
   route test of `walk-in` (`test_world_paths.py`) still passes unchanged. No old test changes.

## Out of scope

- The walk loop in `main.js` (the 0.5 s give-up, the 0.15 tolerance).
- The grid size, the collision rules (`physics.js`) and everything in `world.py`.
- The 2 remaining tight spots.

## Done when

1. **Margin:** `paths.js` straightens with `radius + CORNER_MARGIN`.
2. **Test:** `tests/test_click_walk.py` passes and fails without the change.
3. **Same routes:** `test_world_paths.py` passes unchanged (every door and desk still reachable).
4. **Checked in the browser:** click from inside the Nova to the Dorm and from the beach to the Nova;
   the player arrives, no console errors.

## Security

Drawing and walking only: no rule reads the route, no input from outside, nothing loaded from outside.
