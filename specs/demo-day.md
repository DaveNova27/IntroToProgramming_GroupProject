# Demo day (`demo-day`)

Written 2026-11-23 by David (owner of this spec and its PR), for the presentation on 2026-11-24.
Builds on `demo-scenarios` (`specs/demo-scenarios.md`, issue #23) and replaces its four separate
scenarios with **one continuous day** that starts in bed and ends in bed. Status: David approved
it on 2026-11-23 ("Yes, build it": Decide 1 to 7 as recommended); built the same day, see "Built".

Test confirmation (David, in his own words, 2026-11-23): the checks in `tests/test_demo_scenarios.py`
that test the old scenarios (ids, count, order, texts) may be changed for this rebuild, because the
demo is replaced on purpose by one continuous day. AGENTS.md limits apply: no check weakened, nothing
skipped or deleted, only checks on the data that changes on purpose; every changed check and its
reason is listed under "Decide" (Decide 6) and in the PR. New checks go in a new file.

## What

### The day, step by step

The demo card at the bottom left always shows **the next step as a button**
("Next step: Order stock"). The button makes the figure walk there (the existing click-to-move path
finding, `findPath`). A step is done when its goal holds on the server; the card then shows the
next step.

| # | Step id | Where the button walks | What the card says (short) | Done when |
|---|---|---|---|---|
| 0 | `wake-up` | (stays in bed) | It is dark and slowly gets light. Forecast of the day: **rain**. How the day goes: dress, stock, Cafe, Beach Cafe, rain, home. | the presenter presses *Next step* |
| 1 | `get-dressed` | the wardrobe in the Dorm | Rain today: buy the rain jacket and put it on. The start money pays for the jacket and the stock. | the rain jacket is worn |
| 2 | `order-stock` | the Order PC in the Mercado Supply Hall | The Cafe needs about **N coffee** today (N from today's demand, by the server). Order them. | coffee in stock ≥ N |
| 3 | `cafe-shift` | the Cafe counter (the day is opened first) | Fill the counter, sell to the queue. | N coffee sold today (nice to have: the queue is empty, Decide 4) |
| 4 | `beach-cafe` | the Beach Cafe | Later: the sun is out and the Cafe earned well. Guests head to the beach. Buy the Beach Cafe and an employee. | the Beach Cafe is unlocked and has a working employee |
| 5 | `rain-again` | the Cafe counter | The rain is back: everyone goes inside, for coffee or merchandise. Merchandise and Surf Shop are open. A short Cafe shift. | 4 coffee sold in the Cafe |
| 6 | `end-the-day` | the bed in the Dorm | Back home: end the day, sleep, read the evening report and tomorrow's forecast. | the day is booked (the next day has begun) |

After step 6 the card shows *Free play*: the existing `finish_demo` (override and `scenario` cleared,
the run goes on). Rough timing at 500 ms a tick: 0 about 20 s, 1 to 3 about 90 s, 4 about 40 s,
5 about 30 s, 6 about 20 s: about 3.5 minutes.

### Continuous steps and "jump" steps (Decide 1)

- Steps 0 to 3 and step 6 are **continuous**: the player's own actions count (the jacket bought, the
  coffee ordered, the shift played). The server moves the card on by itself when the goal holds.
- Steps 4 and 5 are **jumps**: each has a prepared start state in the data (more money, the weather
  of the step, the shops that are open). It loads only when the presenter presses
  *Next step: Beach Cafe* (or *Rain again*), so a shift is never cut in the middle of a sentence. The
  day number stays the same (day 1) in every step, so it reads as one day.
- The jacket stays on after a jump (the jump states own and wear it).

### Data: `scenarios.py`

One demo, `DEMO_DAY`: an ordered list of steps. Each step is pure data:

| Field | What |
|---|---|
| `id`, `title`, `text`, `button` | Fixed English texts. `button` is the label after "Next step:" ("Order stock"). `text` at most 25 words; it may hold one fixed placeholder `{need}` that the server fills (step 2 and 3). |
| `target` | Where the button walks, from a fixed list: `None`, `wardrobe`, `order-pc`, `cafe`, `beach_cafe`, `bed`. The browser takes the spot from `/api/world` (it is already there: `DORM.wardrobe`, `DORM.bed`, the PC and the shop doors). |
| `goal` | `{"kind", "value"}`, kind from a fixed list: `manual`, `outfit_worn`, `stock_for_demand`, `sold_at_least`, `shop_staffed`, `day_over`. Checked by code, no code in the data. |
| `state` | `None` (continuous) or a patch for `logic.editor_set_state` (a jump; also step 0, the start). Money in cents, weather and event in `day_override`. |
| `opening` | For a state: `None`, `"open"` or `"shift:cafe"` (the real `open_day` / `start_shift`). |
| `tick_ms` | 400 to 1000, as before (rate limit). |

State: `state["scenario"] = {"id": "demo-day", "step": n}`. No key means no demo, as before. The
seed stays one fixed demo seed; randomness only from it.

Start state (step 0): day 1, `logic.STARTING_CASH` (100 euro), no stock, `day_override` rain, the
player in bed in the Dorm, the basic shirt. 100 euro pay the rain jacket (25 euro) and the coffee of
the day (about 13 × 0.80 euro) with money left.

Jump 4: day 1 open, sun, about 350 euro, the Cafe with coffee and cake, 40 beer in stock for the
Beach Cafe (delivered earlier), the Beach Cafe locked: unlock (200 euro) plus an employee place
(60 euro) fit. Jump 5: day 1, rain, all four shops open, Beach Cafe, Merchandise and Surf Shop with
a working employee and stock, the Cafe shift started.

Functions (pure): `load_step(n)` (the start state of step 0 or a jump), `step_done(state)`,
`advance(state)` (moves the step on while the current continuous step is done and the next one is
continuous; called by the server after every accepted action), `next_step(state)` (the presenter's
button: the next step, loading its state if it is a jump; allowed also when the step is not done, as
*Skip* was before), `finish_demo(state)` (unchanged), `demo_view(state)` (the card: step, count,
title, text with `{need}` filled, button, target, done, tick_ms; never the seed or the patch).

### Server

- `POST /api/demo/load` stays: `{"id": "demo-day", "confirm": true}` loads step 0. Same checks as
  today (only `id` and `confirm`, ids from the fixed list, a refusal changes nothing).
- New `POST /api/demo/next` with `{}`: `next_step`. Refused without a demo or with any field.
- `apply()` calls `scenarios.advance` after an accepted action (a tick too), so the card moves on.
- `POST /api/demo/finish` unchanged.

### Screen (`static/world/demo.js`, small hooks in `ui.js`, `map.html`, `map.css`)

- The card shows the step ("3 of 7"), title, text and one button "Next step: …". A click on a
  continuous step walks the figure to `target` (no request). On a done step, or a jump, it first sends
  `/api/demo/next`, then walks. *Got it* (fold the text) and *End demo* stay.
- Step 3's button first sends the existing `/api/day/open` when the day is still closed, then walks
  to the Cafe (Decide 3).
- Step 0: on load the figure lies in bed and the existing dawn of `day-cycle` runs (dark, then light).
- Step 6: the existing evening (end the day at the bed, the report, *Sleep*, the dawn). Then the card
  says *Free play*.
- Every text through `textContent`. `Math.random` nowhere.

## Decide

Recommendations for David.

1. **One day, but jumps for 4 and 5.** The rules give a day one weather (`make_day_context`); a
   change of weather in the middle of an open day would be a new rule (`disruptions`, out of scope).
   Recommended: steps 4 and 5 load a prepared state of the same day 1 with their own weather. The clock
   of the day starts again at the jump (the light goes back to the morning). Alternative: a demo-only
   weather change mid-day: rejected, new rule.
2. **When the card moves on.** Recommended: continuous steps by themselves (the server, after each
   accepted action), jumps only by the button. Alternative: always by the button (simpler, but the
   card would not react to the goal).
3. **Who opens the day.** The day must be open before the Cafe shift (`start_shift` refuses
   otherwise). Recommended: the step-3 button sends `/api/day/open` (the request the bed panel uses)
   and then walks to the Cafe. Alternative: an extra step "Open the day" at the bed after dressing.
4. **Step 3 goal.** Recommended: N coffee sold, with N = the same number as in step 2 (the demand of
   the day). "The queue is empty at the end" is nice to have: only if the guests of the day really
   come in N; checked in the build, not a goal.
5. **The old four scenarios go.** `SCENARIOS` is replaced by `DEMO_DAY`. The *Demo* dialog no longer
   picks a scenario; it only asks to confirm (the run is replaced).
6. **Changed tests** (all in `tests/test_demo_scenarios.py`, under David's confirmation above). Each
   check stays as strong, on the new data:
   - `test_the_demo_has_four_scenarios_in_order` → the demo has the seven steps in order.
   - `test_every_entry_is_complete_and_valid` → every step: the new field set, kinds from the
     fixed lists, `tick_ms` range, text length, the patch accepted by `editor_set_state`, cents.
   - `test_load_scenario_is_deterministic_and_complete`, `test_different_ids_give_different_runs`,
     `test_the_data_is_not_changed_by_loading` → the same for step 0 and the two jumps.
   - `test_both_shops_have_a_working_employee`, the guest checks of scenarios 2 and 3
     (`..._change_their_mind_early...`, `..._without_the_cafe_employee...`, `..._turns_the_crowd_round...`)
     → on jumps 4 and 5: the staffed shops have working employees and a guest plan; in jump 4 (sun) the
     beach gets more guests than the Cafe, in jump 5 (rain) the Cafe and Merchandise more than the
     beach; guests change shop; without the Cafe employee the Cafe receives none. If the seed cannot
     give one of these, I stop and say so.
   - `test_every_scenario_is_solved_in_its_time`, `test_the_whole_demo_ends_in_free_play`,
     `..._skipped_day...`, `..._watched_day...` → a reference play of the whole day by the real rules
     (buy jacket, order, open, shift, next, unlock + place, shift, skip) reaches every goal, then
     `finish_demo` gives free play from the seed.
   - `test_demo_view_sends_texts_but_never_the_seed_or_the_patch`, the endpoint and public-mode
     tests → the same checks with `"demo-day"` instead of `"grow"` / `"guests-decide"`; the bad-load
     list stays complete ("grow" itself becomes one more unknown id).
   New checks (`/api/demo/next`, `advance`, `{need}`, targets) go in a new file
   `tests/test_demo_day.py`.
7. **One test outside that file.** `tests/test_persistent_runs.py:96` loads
   `scenarios.load_scenario("grow")` to check a demo run survives the Postgres round trip. It breaks
   when "grow" goes. Your confirmation covers only `test_demo_scenarios.py`. Recommended: you also
   confirm changing that one line to the new demo's start (`"demo-day"`), the check stays the same.
   Alternative: keep a hidden `load_scenario("grow")` alive only for that test (dead code, not
   recommended).

## Out of scope

New game rules (a weather change inside an open day included); the open specs `shop-walk`, `staff`,
`nova-design`, `final-polish`, `disruptions`, `warehouse`; changes to guests, prices, balance,
`OPEN_DAY_TICKS`, `SHIFT_TICKS`; sending any state from the browser; a second demo.

## Done when

1. `uv run pytest` passes (output pasted); `tests/` changed only as in Decide 6 and 7, new checks in
   `tests/test_demo_day.py`.
2. The demo played once from bed to bed and into free play in the browser (screenshots per step).
3. Security (roadmap 3a, 3b `demo-scenarios`): the browser sends an id, `confirm` or `{}`, never a
   state; a refused load or next changes nothing (`db.load` equal before and after); no seed in any
   answer; public mode loads only into the player's own run; rate limit and headers on `/api/demo/*`;
   money in cents; texts through `textContent`; `rg "Math.random" static/world` finds nothing.
4. The three roadmap rules hold: the state stays complete and settable, the day context takes the
   override, randomness only from the seed.
5. `README.md` (spec list, how the demo runs) and this spec ("Built") updated; every changed file listed.

## Built (2026-11-23)

- `scenarios.py`: `STEPS` (seven steps as data), `load_scenario`, `load_step`, `advance`, `next_step`,
  `step_done`, `scenario_done`, `need`, `finish_demo`, `demo_view`. State: `{"id": "demo-day", "step": n}`.
  Demo seed 39 as before. Goal kinds: `manual`, `outfit_worn`, `stock_for_demand`, `sold_for_demand`,
  `shop_staffed`, `shop_sold_at_least`, `day_over`.
- `app.py`: `apply()` calls `scenarios.advance` after every accepted action; new `POST /api/demo/next`
  (no fields; a jump is saved like a new run). `/api/demo/load` and `/api/demo/finish` unchanged.
- Screen: the card has one big button "Next step: …", *Got it*, *Skip* (rehearsal) and *End demo* /
  *Free play*; the start dialog no longer picks a scenario. `main.js` got `walkToSpot` (walk to a shop's
  spot and open its panel on arrival: the Shift panel at the Cafe, the Shops window at the Beach Cafe).
  The night and sunrise of `sleep()` became `nightToMorning()`, also run when the demo starts.
- Played twice in the browser (public mode on a separate port, so no real save was touched), from the
  bed to free play. What that changed:
  - The bulk order only redrew the HUD, so the card stayed on "Order stock": the HUD redraw now redraws
    the card too (it is cached, so this is cheap).
  - In the Cafe shift two guests left while serving lagged, and the card stayed on "Sell 13 coffee".
    The Cafe-shift step (and the rainy step) now also count as done once the player's own shift in that
    shop is over: a guest who left must not stop the demo.
  - Jump 5 put the figure at the beach, and three guests left during the 15-second walk to the Cafe
    (the shift starts with the jump). Jump 5 now starts at the Cafe.
  - The guests come spread over the whole shift (a `guests` rule, not touched), so the rainy step's goal
    is 4 coffee (about 14 s at 400 ms a tick), not 10. In jump 5 the Cafe sells coffee only (one Fill,
    one Sell for the presenter); jump 4's Cafe has an employee, so nobody waits unserved while the
    player is at the beach.
- Timing measured in the browser: wake-up and sunrise about 7 s; walk to the wardrobe 2 s; walk to the
  PC about 12 s; Cafe shift about 35 s (13 guests at 400 ms); walk to the beach about 10 s; rainy
  shift about 15 s; walk home about 10 s; evening and sleep about 10 s. With the presenter's talking,
  about 3.5 to 4 minutes.
- Numbers of the day (seed 39, rain): the Cafe's demand is 13 coffee (10.40 euro); after the jacket
  (25 euro) and the stock 64.60 euro are left. In the reference play all 13 are sold and nobody leaves.

### Changed checks in `tests/test_demo_scenarios.py` (Decide 6, as built)

Every old test function is still there and checks the same thing on the new data:

| Old check | Now |
|---|---|
| `test_the_demo_has_four_scenarios_in_order` | renamed `test_the_demo_has_its_seven_steps_in_order`: one demo id, the seven step ids in order |
| `test_every_entry_is_complete_and_valid` | per step: the new field set, ids, texts, targets, openings, goal kinds, `tick_ms`, the patch accepted by `editor_set_state`, cents |
| `test_no_scenario_ticks_into_the_rate_limit` | per step |
| `test_load_scenario_is_deterministic_and_complete` | per loadable step (the start and the two jumps) |
| `test_different_ids_give_different_runs` | the three loadable steps differ |
| `test_the_loaded_run_survives_save_and_load` | jump 5 |
| `test_load_scenario_refuses_anything_but_a_known_id` | the same bad values on the new id |
| `test_the_data_is_not_changed_by_loading` | the three loadable steps |
| `test_both_shops_have_a_working_employee` | jump 4 (after buying the beach employee: Cafe and Beach Cafe) and jump 5 (three staffed shops, all four in the guest plan) |
| `test_guests_change_their_mind_early_in_scenario_2` | jump 5: at least two guests change shop before tick 45, the Merch shop receives, Cafe and Merch beat the beach in the rain |
| `test_without_the_cafe_employee_the_cafe_receives_no_guest` | jump 5 (the Cafe has no employee) and jump 4 with its Cafe employee removed |
| `test_scenario_3_turns_the_crowd_round_and_names_the_event` | sun (jump 4) against rain (jump 5), from the guest plans as before: the beach wins in the sun, the Cafe in the rain, the beach has more guests in the sun, the Cafe more coffee guests in the rain (counted per product, because jump 5's Cafe sells coffee only), and a thought says "Rainy" |
| `test_every_scenario_is_solved_in_its_time` | per step 1 to 6: reached by the reference play, not done at the start, the check only reads, done within its ticks (Cafe shift 90, rainy shift 40) |
| `test_a_watched_day_that_is_over_counts_as_seen` | jump 5 skipped: day 2, the step counts as seen |
| `test_selling_on_a_skipped_day_is_booked_from_the_history` | the Cafe shift: sold and then skipped still counts (from the booked line); skipped without selling does not |
| `test_the_whole_demo_ends_in_free_play` | the whole day by the reference play, then `finish_demo` |
| `test_finish_on_an_open_day_books_it_under_the_fixed_weather_first` | jump 5: day 1 booked under rain |
| `test_a_stale_scenario_can_still_be_left`, `test_an_unknown_saved_scenario_counts_as_none` | the new id; the same saved values as before |
| `test_demo_view_sends_texts_but_never_the_seed_or_the_patch` | the new card fields; the first card asks the server first (was: the panel of scenario 1); the last is marked (was: no next after "grow") |
| endpoint and public-mode tests | the new id; the load test reaches the badges check (first-hire, expansion) through the jump to step 5, because the start has no employee; the finish test buys the jacket instead of unlocking a shop; "Day 1 closed" instead of "Day 8 closed" |

New checks are in `tests/test_demo_day.py`, also the ones first written into the changed file (moved
there after the review).

### Changed check outside that file (Decide 7)

`tests/test_persistent_runs.py:96` loaded `scenarios.load_scenario("grow")`, which is gone. David
confirmed the change on 2026-11-23 ("CONFIRM", his answer to that question); the line now loads
`"demo-day"`. The check is the same: a demo run gives the same state through SQLite as from a file.

### Code review (`/code-review`, high effort, 2026-11-23): 8 findings, all fixed

1. A double click on *Next step* sent two requests and skipped a whole step: the card's buttons now
   ignore clicks while one is on its way (`demo.js`).
2. The type check of the saved id was lost: a list or dict id raised in the lookup and broke every
   request. Back in `_current`; checked with damaged ids in `test_demo_day.py`.
3. *Next step* pressed during the opening sunrise could move the step on without a walk: the walk now
   waits for the sunrise (`ui.js`). In the browser the night's overlay already catches such a click,
   so this is a safety net.
4. A walk of the card stayed pending when another walk started (toolbar, Go home): `walkToPlace`,
   `goHome` and `wakeAt` clear it (`main.js`).
5. While the card already shows the jump, it sent the jump's pace (500 ms) for the Cafe day that is
   still open (400 ms): `tick_ms` now comes from the running step.
6. The crowd check compared the demand formula instead of the guest plans: it counts the Cafe's coffee
   guests in the two plans again.
7. New checks had been written into the changed `test_demo_scenarios.py`: moved to `test_demo_day.py`.
8. The PR description now lists every changed check with its reason.

### Open

- A rehearsal with a person and a stopwatch, and one run on the deployed URL.
