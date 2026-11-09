# Smooth frames

Issue #73. Found in the audit (audit report in PR #72, `docs/audit-report.md` on branch `audit`, items P1 and P2).

## What

The campus runs at the screen's rate instead of 6 to 12 frames per second.

1. `drawSoftShadow` (`static/world/primitives.js`) no longer sets `ctx.filter = "blur(2px)"`. It was
   called 35 times per frame and cost 66 to 160 ms on a 3420 x 1904 canvas. The shadow is one plain ellipse
   (a second ellipse for a soft edge cost about 4 ms more and was dropped).
2. The frame step in `static/world/main.js` is no longer cut at 0.04 s. A slow frame (up to 0.1 s)
   advances the world by its real time; walking is calculated in steps of at most 0.04 s, so the
   collision works as before. The steps are equal, `walk()` still runs once per frame at least, the
   rest of a frame is skipped when a door or desk was used or the zone changed, the walkers are
   stepped the same way, and the first frame after the page load does not move the world.

## Out of scope

Ground cache, culling, the roof fade, memory per frame, the canvas resolution, new looks.

## Done when

1. No `ctx.filter` in `static/world/` (new test `tests/test_smooth_frames.py`).
2. Measured in the browser on the plaza, old and new side by side on the same machine: the mean frame
   is at most a quarter of before (measured: 97 ms before, 21 ms after, which equals the old code with
   the blur switched off).
3. Holding a key for 3 s moves the figure about 10.5 tiles (before, with the slow frames: 3.2; measured after: 10.4).
4. `uv run pytest` passes, `tests/` untouched.

Rules: no money, no randomness and no state are touched.

## Decide

- The 2 px soft edge of the shadows is dropped (a second ellipse cost about 4 ms). If the hard edge
  looks wrong to the team, a radial gradient is the next thing to try, not the blur filter.
- Criteria 2 and 3 are browser measurements and have no automated test (the frame rate depends on the
  computer). The guard in `tests/test_smooth_frames.py` only keeps the blur filter out.
