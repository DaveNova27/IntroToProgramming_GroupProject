# Walking glides past objects (`smooth-walk`)

Found while playing on 2026-11-16 (Gregor): the player often gets stuck at palms, lamps, posts and
other objects and has to walk a wide curve around them. Screen only: no rule, no API, no `world.py`.

## What

`resolveMovement` (`static/world/physics.js`, from Felix' project) moves the player one step per
frame. If the step runs into an object, it only tried two ways out: the step's left-right part alone,
or its up-down part alone. Walking with one key (for example only D) at a palm leaves no second part
to try, so the player stops. At round objects and at the corners of rectangles this happened in most
directions: of 4368 test walks with one held key at a free-standing round object, 2560 stopped in
front of it.

The fix: before those two old tries, the step glides along the edge of the object it hit. The point
the step would reach is pushed out of the object again, the shortest way (`pushOut`), so the player
moves along the edge instead of stopping. A step aimed straight at the middle of a round object
first leans a little to one side (always the same side for the same step), otherwise the push would
lead straight back. If the glided point hits another object, the old two tries follow, then the old
stop.

## Decide

1. **Glide, not smaller objects:** the radii of the player (0.28) and of the objects in `world.py`
   stay. They are also used by the click route (`paths.js`) and the guests. Smaller radii can be a
   follow-up after playing with the glide.
2. **Numbers:** `HEAD_ON = 0.05` (a step this close to the middle counts as straight at it),
   `LEAN = 0.3` (share of the step it leans to the side), `GAP = 0.001` (the pushed point stays this
   far outside the edge). Named constants at the top of `physics.js`.
3. **Tests:** the new file `tests/test_smooth_walk.py` runs the real `physics.js` with Node: walks with
   one held key at every free-standing round object of the campus, 16 directions, many side offsets.
   None may get stuck (on the old code more than half do), the head-on walk at a palm gets past and
   gives the same result twice, no step ends inside an object, and a walk straight into a wall still
   stops there without sliding. No old test changes.

## Out of scope

- The radii of the player and of the objects, `world.py`.
- The click route (`paths.js`) and the walk loop in `main.js`.
- Places where objects stand so close that there is no gap to pass: there the player still stops.

## Done when

1. **Glide:** `resolveMovement` glides along the object it hit, with the old tries as a fallback.
2. **Test:** `tests/test_smooth_walk.py` passes and fails on the old `physics.js`.
3. **Old tests:** `uv run pytest` passes, also `test_click_walk.py` and `test_world_paths.py` unchanged.
4. **Checked in the browser:** walk with W A S D at palms, lamps and the corners of benches; the player
   glides past, no console errors.

## Security

Drawing and walking only: no rule reads the position, no input from outside, nothing loaded from
outside, no randomness.
