# A longer road for the lorry (`lorry-road`)

Asked for by Gregor on 2026-11-17: the delivery lorry stands on a short lane west of the Supply Hall. The
road should go on much further to the back (north), so that it looks like the way the goods come from.

## What

- **The road (`static/world/campus.js`, `drawSupplyRoad`):** from the north end of the delivery lane
  (y 8.0) a road runs north along the west side of the Learning Center up to the north edge of the drawn
  ground (y 0.0, `ROAD_FROM`), where it leads off the campus. Asphalt like the lane, a kerb on each
  side, centre dashes every tile. It is 3.4 tiles wide (x −1.4 to 2.0), narrower than the lane, so it
  passes the Learning Center's west wall (x 2.2) with its kerb in between.
- **Only drawing:** no new solid object, no change to where a person may walk (the zone starts at
  y 1.0), no rule. The lorry, the lane, the barrier and the pallets stay where they are.

## Decide

1. **North, to the edge of the ground:** above y 0.0 there is only sky; a road into the sky would look
   wrong. Asked on 2026-11-17: north (up the screen), not west.
2. **Tests:** the new file `tests/test_lorry_road.py`. No old test changes.

## Out of scope

- The lorry arriving as an animation (a spec of its own if wanted).
- Moving the lorry, the lane or the Supply Hall; new solid objects.

## Done when

1. **Road:** drawn from the lane to the north edge, clear of the Learning Center, with kerbs and dashes.
2. **Nothing else changes:** the colliders, the zones and the lorry are the same; the full test suite passes.
3. **Checked in the browser:** the road runs north from the lane past the Learning Center; no console errors.

## Security

Drawing only: no input, no rule, nothing loaded from outside, no randomness.
