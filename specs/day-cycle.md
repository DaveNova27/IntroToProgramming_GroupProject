# The day starts and ends at the Dorm (`day-cycle`, issue to be opened)

Written by Christopher, 2026-11-09; decision 2 taken by him, the others are recommendations
waiting for the team (and decision 6 for Felix). Builds on `outlook` (#12, the evening report) and
`nova-zones` (#28, the Dorm with its bed panel).

## What

The day gets a place: the player wakes up in the Dorm, goes out to work, and comes back
to the Dorm to end the day. Today the day summary with the evening report pops up
wherever the player stands when the clock runs out, and every day starts where the last
one ended. After this spec:

1. **Morning.** The player stands beside the bed in the Dorm. The bed panel has the
   "Open day N" button (as today) and shows the forecast for the day.
2. **During the day.** The player walks to a shop and works. The bed panel now says
   "End the day": it ends the day early, with the request that already exists for
   skipping (`/api/shift/skip`).
3. **Evening.** When the day closes (the clock ran out on the server, the day was skipped,
   or it was ended from the dashboard), the summary does **not** pop up on the map. It
   gets dark (as today) and a hint in the display says "Day N is over. Time to go home."
   with a button **"Go home"**; the Open button of the toolbar says "Go home" too. The
   player may also walk there alone.
4. **Go home.** The button makes the player walk to the bed by itself: the same way
   finding as click-to-move (`findPath` in `paths.js`), through the Dorm's entrance, at
   walking speed. Any move key or click on the map stops the walk and gives the control
   back. Arriving in reach of the bed counts like using it. A player who ends the day while
   standing at the bed goes to bed at once.
5. **Going to bed.** At the bed the player **lies down** on it (a new pose "lie" of the
   person figure) and the panel shows the day summary and the evening report of
   `outlook` (the same overlay as today). Its button is "Sleep".
6. **Sleep.** The screen fades to black and back, the clock is set to the morning, and the
   player stands up beside the bed: step 1 of the next day.

The server decides no rule from the position. Every step is a request that already
exists; the Dorm is only the way to reach it. The dashboard keeps its own buttons and its
report, so the whole game still works without walking.

### Data in `world.py`

- `DORM["wake"]`: `{"zone": "campus", "x", "y"}`, a free spot beside the bed where the
  player stands after sleeping. Fixed data, sent with `/api/world` like the rest of `DORM`.
  Not a new rule: the browser saves the position with `POST /api/player`, which already
  checks zone and bounds.

### Screen (`static/world/`)

- `ui.js`: the bed panel has three states, read from the state the server sends and from
  one browser flag "evening" (see "Decide", 3):
  - no open day and not evening: "Open day N" (`openDay()`, as today) and the forecast;
  - a day open (`state.shift` not null): "End the day" (`/api/shift/skip`);
  - evening: the day summary of the last day (`state.history[-1]`) with the evening report
    and the button "Sleep".
- `shiftTick()` and `shiftAction()` no longer call `showDaySummary()` directly. They set
  "evening" and show the hint with the button "Go home".
- `main.js`: "Go home" starts an automatic walk to the bed's use point with `findPath`,
  as a click on the map does. A move key or a click stops it. Arriving opens the bed.
- `people.js` / `player.js`: a pose "lie" for the person figure (lying on the bed,
  facing up, no walk frames). Drawn in code, no `Math.random`.
- "Sleep": closes the summary, fades the scene to black and back (cosmetic), runs the
  clock to the morning as `data-next` does today, puts the player standing at
  `DORM["wake"]` and saves it with `POST /api/player`. After the last day "Sleep" leads
  to the final result instead (`showFinal()`, as today).
- A day ended through the dashboard sync (`syncFromDashboard` in `ui.js`) also puts the
  campus into "evening". `views.js` is not changed.
- `locations.js`, `main.js`: no use ring around the bed and no "Go to bed" hint while the
  player lies in it.
- Texts through `textContent` or `esc()`.

## Decide

1. **Where does a new run start?** Recommendation: on the plaza, as today. Moving the
   spawn into the Dorm breaks `tests/test_world_api.py::test_a_new_run_starts_at_the_spawn`
   (it pins `(21, 18)`), and tests in `tests/` are not changed. Only the following days
   start at the Dorm. Alternative: move the spawn and ask the owner of the test for an
   exception.
2. **How does the player get to the Dorm?** Decided by Christopher on 2026-11-09: a
   button "Go home" walks the player there automatically; walking alone works too. On the
   bed the player lies down, then the screen fades to the morning. The dashboard still
   shows its report as before, so the game works without the map.
3. **Where is "evening" kept?** Recommendation: only in the browser, not in the state.
   It decides no rule and nothing is lost when it is lost: after a reload it is simply
   morning, and the report of the last day is still in the history. The state shape stays
   the same, so no test of the state changes.
4. **Does "Sleep" start the next day at once?** Recommendation: no. Sleep brings the
   morning; the player buys stock and sets prices with the forecast in mind, then opens
   the day at the bed or on the dashboard (roadmap B1, step 7 before step 1).
5. **What does "End the day" do while a shift runs?** Recommendation: the same as the
   Skip button today (`/api/shift/skip`: the rest of the day is played out by the server).
   No new rule.
6. **Felix.** The bed panel is his (`nova-zones`). He should agree that `day-cycle`
   replaces its button as his spec planned.

## Out of scope

A new endpoint or a new rule on the server, any rule that reads the position, moving the
spawn of a new run (see "Decide", 1), a darker night drawn over the map beyond the short
fade, weather visuals (`weather-visuals`), events (`events-and-disruptions`), changes to
the evening report itself (`outlook`), walking a shift (`shop-walk`), the flatmate or
other people in the Dorm, the demo scenarios.

## Done when

1. `DORM["wake"]` lies inside the campus bounds, is not blocked by any collider, lies
   inside the Dorm's room and in reach of the bed; `POST /api/player` accepts it (new test
   `tests/test_day_cycle.py`).
2. A day that closes on the map does not open the summary; the hint with "Go home" is
   shown instead. "Go home" walks the player to the bed from any walkable spot of the
   campus (shops, beach, inside the Nova); a move key stops it. At the bed the player
   lies down and the summary and the evening report are shown; "Sleep" fades to the
   morning and puts the player standing beside the bed.
3. "Open day" and "End the day" at the bed send only the requests that exist today; a
   crafted request is refused by the server as before and changes nothing.
4. The dashboard works as before (the live window shows no evening hint).
5. After the last day "Sleep" leads to the final result.
6. A reload in the evening gives a normal morning without errors.
7. `tests/` untouched apart from the new `tests/test_day_cycle.py`; `uv run pytest` passes.
   In the browser: the whole cycle over two days, no console errors, on a desktop and a
   phone width.
8. PR "Closes #<issue>", AI code review done and its findings handled.

## Security

Roadmap 3a, and 3b `nova-zones`: the position decides no rule; the server re-checks every
open, skip and move as today. No new endpoint, so no new input to validate. The wake-up
spot is fixed server data. Texts through `textContent` or `esc()`.
