# Campus events and trends (`events-and-disruptions`, issue #14)

Agreed by Felix on 2026-11-09 ("Ja, bauen" after the draft). The one old-test change of Decide 7 confirmed by him in his own words the same day ("Ja, bestätige ich"). Builds on `day-context` (#10) and
`pricing` (#38, the socket `FACTORS`). Decision 1 below splits the issue: this spec is the events
(and the trend that lasts several days); outages and strikes come as their own spec.

## What

Some days have an **event** on campus: an exam period, a party, a career fair, a surf festival. An
event is rolled from the seed like the weather, lasts one to three days and changes how many
customers each shop gets. It stacks with the weather: a hot day with a party gives the Beach Cafe a
lot more customers, so the player should have ordered more beer. The browser never chooses an event,
only the demo override and the editor can.

Everything goes through the socket that `pricing` built: one more function in `FACTORS`.
`customers_for`, the curves and the mixes are not touched.

### Rules in `logic.py`

- `EVENTS`: the table as data. Per event: `name`, `weight` (how often it is the one that starts),
  `days` (how long it lasts, 1 to 3), `demand_percent` per shop (whole percent, 100 = normal, the
  roadmap's table B2) and `visitors_percent` (an extra percent on top for the visitors, like
  `VISITOR_WEATHER`; 100 = no extra). Starting table, all placeholders to balance:

  | Event | Weight | Days | Cafe | Surf Shop | Merchandise | Beach Cafe | Visitors extra |
  |---|---|---|---|---|---|---|---|
  | `exam_period` Exam period | 35 | 2 | 150 | 60 | 90 | 70 | 70 |
  | `party` Party | 30 | 1 | 80 | 100 | 110 | 150 | 110 |
  | `career_fair` Career fair | 25 | 1 | 130 | 70 | 140 | 90 | 120 |
  | `surf_festival` Surf festival | 10 | 3 | 90 | 170 | 130 | 160 | 150 |

- `EVENT_START_PERCENT = 30`: the chance that an event starts on a day, in whole percent.
  `FIRST_EVENT_DAY = 3`: the first two days are quiet, so the player learns the shops and the weather
  first (see "Decide" 3).
- `event_starting(seed, day)`: pure. `None` or an event id. A day before `FIRST_EVENT_DAY` gives `None`.
  Rolls with its **own** generator `random.Random(f"{seed}:{day}:event")`, so the weather rolls and the
  outlook rolls stay exactly as they are.
- `make_event(seed, day, override=None)`: pure. The event that is on during `day`: the newest event
  that started on `day` or on one of the two days before it and is still running (an event that
  started on day 5 with `days` 3 is on during days 5, 6 and 7; a newer start replaces it). No state,
  so a run can jump to any day (editor, demo) and the answer is the same. Returns `None` or
  `{"id", "name", "day_of", "days"}` (`day_of` 1 to `days`).
  With an `override` that names an event the answer is that event (day 1 of its length); an
  override that exists but names no event, or names `"none"`, means **no event** (see "Decide" 2).
- `day_context(state)` gains `"event"`: `make_event(...)` (or `None`). `make_day_context` is
  extended with the same field; the weather, the temperature and `demand_percent` are unchanged.
- `_event_factor(state, shop)`: the factor for `FACTORS` after the weather. Label
  `"Event: Party"`; `{"students": percent, "visitors": percent * visitors_percent / 100}` with exact
  fractions. No event: it returns 100 for both segments, so the explanation shows no line for it.
- `set_day_override(state, weather, event=None)`: `weather` an id from `WEATHER` or `None`, `event` an id
  from `EVENTS`, `"none"` or `None`. Both `None` clears the override. The override is saved as
  `{"weather": id}`, `{"event": id}` or both. Unknown ids and wrong types are refused, the state is
  left alone. `editor_set_state` accepts the same shape under `day_override`.

### API and screen

- `GET /api/state` adds `event: {id, name, day_of, days}` or `null`, **only once the day is open**
  (like `weather`, see `weather_view`). The seed never leaves the server.
- `POST /api/day-override` and `POST /api/editor/weather` take an optional `event`. The demo switch
  and the editor switch guard them as before.
- The explanation of a customer number (Part 5 of `pricing`, "Why this number?") shows one more step
  when an event is on: "Event: Party" with the customers after it.
- The display shows the event while the day is open: a stat "EVENT" in the top bar of the campus page, a
  chip on the dashboard and a row in the Dorm panel, e.g. "Surf festival 2/3" (the day counts only for
  events of several days). Texts are set with `textContent` or `esc()`.
- The editor panel's weather block becomes "Weather and event": two dropdowns, "Fix" and "Seed's" (back to
  the seed's weather and events). The event dropdown starts at "No event".

## Why

`pricing` made the customers depend on the price and the weather, but every day looks the same apart
from the weather. Events give the player a reason to look at the news before ordering and to change
prices from day to day. The stacking with the weather is what makes it interesting, and the cap
`MAX_CUSTOMERS` keeps it safe.

## Decide

1. **Split of the issue.** The issue names events, trends, outages and strikes. Events and the trend
   (a longer event) fit the customer socket and are built here. Outages (a shop closed, goods scarce)
   and strikes (fewer walk-in customers or higher purchase prices) change stock, staff and buying and
   have to be agreed with `warehouse` and `staff`. Proposal: they become their own spec
   (`disruptions`, new issue), built after this one. The issue keeps its number for the events.
2. **An override without an event means "no event".** Otherwise a day with a rolled event would break
   the tests that fix the weather (the storm line of `pricing`, group A) and every demo that fixes the
   weather. Whoever wants an event in a demo names it.
3. **First two days quiet.** On day 1 and 2 no event starts (placeholder `FIRST_EVENT_DAY = 3`).
   Reason: the numbers of the old tests on day 1 and the first impression of the game stay as they are.
4. **Volume only.** Events change how many customers come, not how price-sensitive they are (same as the
   note in `specs/pricing.md`, Part 4). An event that shifts the price tolerance needs a second kind
   of factor and its own spec.
5. **Several days without state.** Whether an event is on is calculated from the seed and the day, never
   saved. The editor can set any day and gets the right event for it.
6. **Tips and forecast.** The forecast of tomorrow (`outlook`) and the tips of the evening report stay
   weather only here. Forecasting events is a later spec, see "Out of scope". Known gap: like the real
   weather, the event shows through the customer numbers in `GET /api/state` before the day is opened (they
   use today's real context). That is the same gap `outlook` documents for the weather.
7. **Old tests.** Checked while building (full suite, 784 passed, 1 failed): exactly one old test needs a
   change, and no test with a customer number does. The first two days are quiet and the tests that fix
   the weather get no event.
   - `tests/test_pricing.py::test_the_weather_table_is_still_the_one_source` (merged with #62) asserts
     `logic.FACTORS == (logic._weather_factor,)`, that is exactly one factor. This spec adds the second one
     on purpose ("one more function in `FACTORS`", the plug-in the pricing spec describes). The line
     becomes `assert logic.FACTORS[0] is logic._weather_factor`: the weather stays the first factor, the
     number of factors is no longer pinned. No check is weakened, skipped or deleted. Owner's confirmation
     in their own words: Felix, 2026-11-09, "Ja, bestätige ich" (AGENTS.md).

## Out of scope

- Outages and strikes (decision 1), forecast of events, popularity, the look of events on the map.
- Events that shift the price tolerance (decision 4).
- A calendar the player can read in advance.

## Done when

1. **Table:** `EVENTS` has the four events above; every demand percent is a whole number from 0 to 300,
   `days` is 1 to 3, the weights are positive.
2. **Same seed, same event:** `make_event` gives the same answer for the same seed and day, in any order
   of calls, and does not change the weather or the temperature of any day for any seed.
3. **Quiet start:** no event on day 1 and 2 for any of 200 seeds.
4. **Frequency:** over 30 days and 200 seeds, events are on during roughly the share the table implies
   (a wide guard band, not an exact number).
5. **Duration:** an event with `days` 3 that starts on day 5 is on during days 5, 6 and 7 with
   `day_of` 1, 2 and 3; a newer start replaces it.
6. **Stacking:** at the reference price on a hot day with a party, the customers of the Beach Cafe
   equal the exact value of weather percent times event percent (checked by hand from the table), and
   never more than `MAX_CUSTOMERS`.
7. **Override:** an override that names a weather only gives no event; one that names an event gives
   it; `"none"` gives none; unknown ids and wrong types are refused through the rule and through the
   endpoints and leave the saved state identical.
8. **One number:** `customers_today`, `start_shift`, `trade_day`, `stock_overview` and the state view
   still show the same number on a day with an event.
9. **Explanation:** the breakdown has a line "Event: ..." on an event day and none otherwise.
10. **Visible only when open:** `GET /api/state` has `event: null` before the day is opened and the
    event after, and never the seed.
11. **Editor and demo:** the editor can set an event and clear it; state patches with `day_override`
    accept `{"weather", "event"}` and refuse anything else.

## Security

Events come from the seed. The browser cannot choose one; only the demo switch (`CAMPUS_TYCOON_DEMO=1`) and the
editor (`CT_EDITOR=1`, this computer only) can set one. Every field is validated, a refused request
leaves the saved state identical, event names reach the page through `textContent` or `esc()`, no
new secrets, no new randomness outside the seed.
