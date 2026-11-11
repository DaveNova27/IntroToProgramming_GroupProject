# Demo scenarios (`demo-scenarios`, issue #23)

Written 2026-11-11; David approved it the same day ("Passt", Decide 1 to 5 as recommended) and
chose to build on the branch of PR #95. Built the same day; what the build changed is in "Built" at
the end. The live demo of the course runs on the public
URL and lasts about **3 minutes** (between 2 and 4). A viewer who has never seen the game must
understand the core in that time: you run a stand, **the guests think for themselves** (`guests`),
weather and events move the crowd, staff and new shops make it grow. Submission is 2026-11-23,
23:59; proposed feature freeze 2026-11-17.

The demo is a short list of **prepared days**. Each one is pure data in a new `scenarios.py`: a start
state, a fixed weather and event, a text, a goal. The server loads one by id into the player's own
run; the browser never sends a state. At the end the player plays on freely.

Depends on `guests` (PR #95, `specs/guests.md`, **open when this was written**): build only on a
`main` that has it. Scenarios 2 and 3 show guests changing their mind between two shops. By
`guests` Decide 4 a shop that only the player can run (the Cafe with no employee) never
**receives** guests who look around, so **both shops of those scenarios need a working employee**.

## What

### The 3 minutes (4 scenarios, about 45 seconds each)

| Time | Part | What the viewer sees | Ends when |
|---|---|---|---|
| 0:00 to 0:15 | Intro | The map, the public URL; the presenter presses *Start demo* | the scenario 1 card is up |
| 0:15 to 1:00 | 1 `serve-the-cafe` | The core loop: storeroom, counter, the queue, money | 5 units sold |
| 1:00 to 1:45 | 2 `guests-decide` | Hot day, two staffed shops: guests walk, show thoughts, change their mind | tick 60 of the shift |
| 1:45 to 2:30 | 3 `other-day-other-choice` | Same shops, another day: rain and an exam period, the crowd goes to the Cafe | tick 60 of the shift |
| 2:30 to 3:15 | 4 `grow` | Cash in hand, the Beach Cafe is locked: unlock it, then free play | Beach Cafe unlocked |
| 3:15 to 3:30 | Outro | *Free play* clears the demo; the run goes on; questions | |

Every scenario has about 12 seconds of reading and about 33 seconds of action. Scenarios are
independent: if time is short, drop the last ones (the run is left as it is, *Free play* is always
there).

### Spoken text (one per scenario, the presenter says it while the card is up)

1. *"This is a snack stand on the Nova campus. Customers queue, I carry coffee from the storeroom to
   the counter and sell. Every sale is a request to the server: the browser decides nothing."*
2. *"Now two shops with an employee each. Look at the guests: each one chooses, by walk, queue and
   taste. The bubble says why. Red means 'I changed my mind'. It is a hot day, so the beach wins."*
3. *"Same shops, other day: rain and exam period. Now the Cafe is full and the Beach Cafe is
   quiet. Weather and events are rolled from a seed, so a demo can fix them."*
4. *"Money lets the stand grow: unlock a shop, add products, hire staff. I unlock the Beach Cafe.
   From here the run is yours."*

### The overlay (text on the card, 25 words at most each)

1. "Carry coffee to the counter with Fill, then sell to the queue. Sell 5 cups." Goal: *sold 5*.
2. "Hot day, one employee in each shop. Watch the guests: bubbles say why they pick a shop. Red: they changed their mind." Goal: *watch until tick 60*.
3. "Same shops, other day: rain and the exam period. Now the crowd goes to the Cafe." Goal: *watch until tick 60*.
4. "You have 300 euro. Open the Shops window and unlock the Beach Cafe. Then the run is yours." Goal: *Beach Cafe unlocked*.

### Scenarios are data: `scenarios.py`

`SCENARIOS` is an ordered dictionary, id to entry. Rules only in functions, never in the data.
An entry has:

| Field | What |
|---|---|
| `title`, `text`, `goal_text` | Shown in the overlay. Fixed English texts, no markup. |
| `seed` | Fixed per scenario, so every rehearsal is the same show (same guests, same weather rolls for the temperature). Never sent to the browser. |
| `state` | A patch for the existing `logic.editor_set_state`: `day`, `cash`, `day_override` (fixed weather and event), `shops`, `stock`, `prices`, `employees`, `player`. Because the loader goes through that function, every value is checked by the rules that already exist. |
| `opening` | `None` (day closed), `"open"` (the real `open_day`, staffed shops start their shift) or `"shift:cafe"` (open, then the real `start_shift`). The guest plan is made by the rules, never faked. |
| `goal` | `{"kind": ..., "value": ...}` with `kind` from a fixed list: `sold_at_least` (units sold today), `tick_at_least` (the open day's clock, true also once the day is over), `shop_unlocked` (a shop id). |
| `tick_ms` | How fast the browser runs the clock while this scenario is active (see Decide 2). 400 to 1000. |

Functions (pure, no HTTP, no clock, no `random`):

| Function | What |
|---|---|
| `scenario_ids()` | The ids in order. |
| `load_scenario(scenario_id)` | A new complete state (fresh `logic.new_state(seed)`, the patch applied, the day opened as `opening` says, `state["scenario"] = {"id": ...}`). Refuses an id that is not a string or not in `SCENARIOS` with a `RejectedAction`, and builds from a copy, so nothing is changed on a refusal. |
| `scenario_done(state, scenario_id)` | True when the goal holds in this state. Pure; same state, same answer. |
| `finish_demo(state)` | The state with `scenario` cleared and `day_override` cleared: the weather and events come from the seed again. Refused when no demo is active. |

### What the server and the screen get

- `state["scenario"]` is `{"id": str}` while a demo runs; **no key** means none. Saved in the `meta`
  table as JSON like `day_override`, loaded back only when one runs. `logic.new_state` is unchanged
  (no key), so old saves and old tests compare equal. It is the only new state. A new run
  (`/api/new-run`) has no key, so it ends the demo.
- `POST /api/demo/load` takes `{"id": "...", "confirm": true}`. It replaces **the player's own run**
  with the scenario (like a new run, so it needs `confirm: true` first, see Decide 5), under the
  run lock, with `db.save_new_run`. Works locally and on the public URL. It is **not** an editor
  switch.
- `POST /api/demo/finish` takes `{}` and leaves the demo (`finish_demo`); the run goes on as it is.
- `view()` gets a `demo` block: the list of scenarios (id, title) and, while one is active, its
  index, count, title, text, goal text, `done` (from `scenario_done`) and `tick_ms`. Texts come from
  the data on the server.
- Free play: after `finish`, the clock runs at one tick a second again, the override is gone, the
  state is the player's.
- The editor mode (`CT_EDITOR=1`, local) and `POST /api/editor/state` are untouched and stay off
  in public mode.

On the map page (`static/map.html`, `map.css`, new `static/world/demo.js`, a small hook in
`ui.js`): a *Demo* button opens a start card (nothing changes until the player confirms); a card
with the scenario's step ("2 of 4"), title, text and goal with a tick when done; buttons *Got it*
(hide the text, a small pill with the goal stays and a "?" brings the text back), *Skip scenario*
(becomes *Next* when `done`) and, on the last one, *Free play*. All texts through `textContent`. The
dashboard keeps working and ignores the block. Sync with the dashboard as the new run does.

## Decide

Recommendations for David, **not decided**.

1. **Which scenarios?** Recommended: the four above (core loop, guests decide, same guests on a
   different day, grow). They cover the professor's wish (the guests think), weather and events,
   staff (the two employees in 2 and 3) and unlocking shops, in this order because the viewer
   first needs to know what a sale is. Alternatives: swap 3 for "party at the beach with a surf
   festival" (more colour, less contrast); put 4 first if the audience is not technical; add a 5th
   "staff pays off" only if the freeze date allows (it costs data and one more rehearsal, no code).
2. **How the days are skipped.** Facts: an opened day is `OPEN_DAY_TICKS = 300` and the browser
   sends one tick a second (`shiftTimer` in `ui.js`), so a full day is 5 minutes, more than the
   whole demo. But only the shift (`SHIFT_TICKS = 90`) sells; the other 210 ticks are idle. The
   existing skip (`/api/shift/skip`) finishes a day in one request, but then nobody sees a guest
   walk, so it cannot be the demo. Options:
   (a) **Client interval per scenario** (`tick_ms`, 500 = two ticks a second). No server change,
   no rule touched; the server counts the ticks as before. 90 ticks take 45 seconds; the goals
   are reached by tick 60, so 30 seconds. Rate limit: 120 ticks a minute plus clicks stays under
   `RATE_LIMIT = 240`; below 400 ms it would not, so `tick_ms` has that floor.
   (b) A `ticks: n` field on `/api/shift/tick`: a server change, and guests would jump.
   (c) A shorter `OPEN_DAY_TICKS`: changes the rules and the balance guard.
   Recommended: **(a)**. The demo never plays a day to its end: the next scenario replaces the
   state, so the idle ticks are never reached. The known weak spot (a script can tick faster than
   one a second, `deploy-ready`) is not made worse: the server already accepts it; only the
   player's own run is affected. If the real-network rehearsal shows 500 ms is too fast for the
   host, raise it in the data, no code change.
3. **Overlay: mandatory or skippable?** Recommended **skippable**: *Got it* hides the text, the goal
   pill stays, *Skip scenario* is always there, there is no automatic advance (the presenter sets
   the pace; a forced card or timer would break the rehearsal when something is slow). A mandatory
   overlay blocks the map, which is the thing to show.
4. **Where does "which scenario" live?** In `state["scenario"]` (see above), so the page and the
   server agree after a reload. Another place would be the browser, which is not trusted.
   Built without touching `logic.new_state`: the key exists only while a demo runs (see Decide 7).
5. **The loader replaces the run.** On the public URL a player has one run. Loading a scenario
   overwrites it, so the request needs `confirm: true` and the start card says so. A separate demo
   run per player was considered and rejected: a second database file per player, a second cookie
   or slot, and more public state, for a feature of three minutes.
6. **Fixed seeds.** One seed per scenario in the data, so every rehearsal is the same show. The
   guests are drawn from seed and day (`guests.py`), so scenarios 2 and 3 (days 8 and 9) have
   different guests; the text says "same shops", not "same guests". Randomness still only comes
   from the seed; nothing new draws.
7. **Tests.** No existing test changes. The one risk was the new top-level `scenario` field: tests
   compare `db.load(...) == state` for states made by hand or by `new_state`. Built so that the key
   is only there while a demo runs, so all of them stay equal.
8. **Timeline.** Spec OK by 2026-11-12, `guests` merged by 2026-11-13, build 2026-11-13 to
   2026-11-15, rehearsal on the public URL 2026-11-16, freeze 2026-11-17. If `guests` is not merged
   by 2026-11-14, scenarios 2 and 3 fall back to "weather moves the crowd" without switching and the
   spoken text changes; say so in the PR.

## Out of scope

New game mechanics (including `popularity`, `disruptions`, `warehouse`, `shop-walk`); changing the
guest rules, `OPEN_DAY_TICKS`, `SHIFT_TICKS`, prices or balance; server-side pacing of the clock;
batch ticks; an editor or a recorder for scenarios; sending any state from the browser; a separate
demo run or slot; the free state patch and the editor on the public URL; automatic advancing;
voice, sound or video; a dashboard overlay; extra languages; `weather-visuals` (the weather is
shown by the existing display).

## Done when

1. `tests/test_demo_scenarios.py` (new file; nothing in `tests/` changes):
   - every entry is complete and valid: fields and goal kinds from the fixed lists, `tick_ms` from
     400 to 1000, texts within the length, the patch is accepted by `editor_set_state`;
   - `load_scenario` is deterministic (same id, same state) and gives a complete state: day, cash,
     shops, stock, prices, employees, player, `day_override`, seed; money is integer cents;
   - the day context of each scenario shows the fixed weather and event through
     `make_day_context`; a different id gives a different state;
   - scenarios 2 and 3 have a working employee in both shops; in scenario 2 at least two guests
     change shop before tick 45 and the beach has more guests; scenario 3 turns that round (more
     at the Cafe) and its thoughts name the exam period; with the Cafe employee removed, the Cafe
     receives none (the `guests` rule, checked from here);
   - each scenario has a reference solution (a scripted play of the real rules: refill and sell,
     ticks, unlock) that makes `scenario_done` true within the time window of the table; a
     balance change that breaks a scenario fails the build;
   - `scenario_done` is false at the start, true after the solution, and does not change the state;
   - a full run through the four scenarios and `finish_demo`: the override and `scenario` are gone,
     the next day comes from the seed;
   - `POST /api/demo/load`: needs `confirm: true`; an unknown id, a missing id, a number, a list, a
     dict, `null`, an empty or very long string, an id with path characters, extra fields, a state
     in the body, a non-JSON body, all refused (400) with the saved run **byte-identical**
     (`db.load` equal before and after), and no path or stack trace in the answer;
   - `POST /api/demo/finish` without a demo is refused and changes nothing;
   - in public mode (`CT_PUBLIC=1`): a player loads a scenario into their own run only (the other
     player's file is untouched), the editor endpoints and the weather switch still answer "off",
     the security headers and the rate limit apply to `/api/demo/*`, the answer shows no seed;
   - the state with a scenario survives save and load; a database without the field loads as `None`.
2. In the browser, desktop view (screenshots in the PR): start card, each of the four cards, the
   goal pill with its tick, *Skip scenario*, *Free play*; guests with bubbles in scenarios 2 and 3; no
   console errors; the dashboard still works. A rehearsal run of the 3 minutes with a stopwatch,
   written into the PR (time per scenario, at 500 ms), and one smoke test on the deployed URL.
3. The three roadmap rules hold: the state is complete and settable, the day context takes the
   override, randomness only from the seed; `rg "Math.random" static/world` finds nothing.
4. `uv run pytest` passes (final output pasted), `tests/` untouched apart from the new file.
   `README.md` (spec list, how to start the demo), `docs/feature-roadmap.md` (B4, issue status) updated.
   Branch `demo-scenarios`, PR "Closes #23", AI code review (`/code-review`) done and its findings
   handled.

## Security

Roadmap 3a and 3b `demo-scenarios`. The demo runs on the public URL, so:

- The browser sends an **id and `confirm`, never a state**. The id must be a string in the fixed
  list in `scenarios.py` (check the type first: a list or dict must be refused, not crash). Anything
  else is a `RejectedAction`, and a rejected load changes no saved data.
- The loader writes only into the caller's own run (the per-player file chosen from the signed
  cookie); no player can reach another player's run.
- The editor mode and the free state patch stay behind `CT_EDITOR=1`, local only, and off in public
  mode. The loader reuses `editor_set_state` as a function on data from the repository, not as an
  endpoint.
- Rate limit, security headers and the cap on runs apply to the new endpoints like all `/api/` ones;
  the scenario list is static, so a flood can only reset the flooder's own run.
- Money stays integer cents; goals are evaluated by a fixed list of kinds in code, no `eval`, no
  code in the data. Scenario texts are fixed, written with `textContent`, never `innerHTML`.
- The seed never leaves the server. Error answers contain only our own rule messages: no path, no
  trace.

## Built (2026-11-11)

On the branch of PR #95 (guests), as David chose; the PR shows the guests diff until #95 is merged.

- `scenarios.py`: `SCENARIOS` (data), `scenario_ids`, `load_scenario`, `scenario_done`, `active`,
  `finish_demo`, `demo_view`. One demo seed (39) for all, chosen so that in scenario 2 guests change
  shop in both directions in the first 45 ticks, with three different reasons.
- Scenario 3 has **no guest who changes shop**, unlike the first draft of "Done when": in rain and
  the exam period the Beach Cafe has 4 guests and the Cafe's products are at the guests' spread limit
  (`guests.MAX_SPREAD`), so nobody can move. Changing that is a `guests` rule and out of scope. The
  scenario shows instead what it is about: the crowd turns round (Cafe 38, Beach Cafe 4 against 13
  and 37 in scenario 2) and the bubbles say "Exam period: off to the Cafe". The player stands in the
  Nova (scenarios 1 and 3), so the roof is gone and the Cafe's queue is in sight.
- Scenario 1 opens the Shift panel when it loads (its goal is selling).
- `app.py`: `POST /api/demo/load` (only `id` and `confirm`, anything else is refused) and
  `POST /api/demo/finish` (no fields); `view()` has a `demo` block. `db.py` stores the scenario.
- Screen: a *Demo* button in the top bar, a start dialog (pick the first scenario: handy in a
  rehearsal), `/?demo` opens it at once; the card sits at the bottom left so the shops stay free;
  `static/world/demo.js`, a few lines in `ui.js` (timer pace, the reset after a new run shared with
  *New run*).
- Measured in headless Chromium (local, 500 ms a tick): scenario 1 reached in 13 s with a script
  that clicks Fill and Sell, scenario 2 in 30 s. A rehearsal with a person and one run on the
  deployed URL are still to do (the app is not deployed yet, `deploy` #93).
- Badges earned in a scenario pop up as usual (for example "Doubled" for 200 euro in cash). Left as
  it is: it shows the badges; pre-earning them in the data would hide them.
