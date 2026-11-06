# The day context: seed and weather (`day-context`, issue #10)

DRAFT, agreed with David on 2026-11-06 (three decisions, display with temperature and picture, sun most frequent).

## What

The run gets a seed. From the seed and the day number the server rolls the weather of
each day (sun, heat, rain, storm) together with a temperature. The player sees today's weather on
the screen as a small picture (sun, heat, rain, storm) with the temperature. The weather
has demand factors per shop (the roadmap's B2 table), but in this spec they are only
**calculated and exposed**, not applied to the number of customers (see "Decide").

### State

- `state["seed"]`: a whole number. A new run draws it once from `secrets` (the only place
  randomness is created). `new_state(seed=None)` takes a seed for tests and the demo mode.
  It is saved in a new `meta` table. A save from before this spec gets a fresh seed on its first load
  and keeps it from then on.
- `state["day_override"]`: `None`, or `{"weather": "<id>"}`. Complete and settable.

### Rules in `logic.py`

- `WEATHER`: the table as data. Per weather: name, roll weight (how often it appears), the
  temperature range in whole degrees Celsius, and the demand factor per shop in whole percent (100 = normal, so no floats). Starting table from Felix'
  `districtWeather` and the roadmap B2 values. Placeholders to balance.
- `make_day_context(seed, day, override=None)`: pure. Rolls with
  `random.Random(f"{seed}:{day}")`, so the same seed and day always give the same weather,
  in any order. Returns `{"day", "weather", "temperature", "demand_percent": {shop: int}}`.
  The temperature is a whole number inside the weather's range, rolled from the same seed. If
  `override` names a weather, that weather is used (its temperature is still rolled from the seed).
- `day_context(state)`: `make_day_context(state["seed"], state["day"], state["day_override"])`.
- `set_day_override(state, weather)`: weather id from the table or `None` to clear. Refused
  for unknown ids and wrong types.

### API and screen

- `GET /api/state` adds `weather: {id, name, temperature}` for today and `demand_percent` per shop. It
  **never** contains the seed.
- `POST /api/day-override` (the demo hook) is refused (404-style rule message) unless the
  server was started with `CAMPUS_TYCOON_DEMO=1` **and** the request comes from the loopback
  address. Everything else about the override stays a rule function the later demo mode can call.
- The head-up display on the campus page and the dashboard show today's weather: a small
  picture and the temperature, e.g. `24 °C`. The pictures are small inline SVG drawn in code
  (no files, nothing from outside); the name and the temperature are set with `textContent`.
  The look of the weather in the world (rain, sky, light) is `weather-visuals`.

## Decide (my recommendations)

1. **Does the weather change the customers now?** Recommendation: no. Existing tests
   (`trade_day` and the shop shift expect 10 customers at the reference price in a fresh run)
   would fail with a random weather, and `tests/` may not be edited. The factors are applied
   in `pricing` (#38), which replaces `customers_for` anyway; that spec has to settle the test
   question. The issue text says "a demand factor in `demand()`": this is the one deviation.
2. **How is the override switched on?** Recommendation: environment variable plus loopback
   only, as above. Roadmap 3a point 7 and 3b `day-context`.
3. **How often each weather appears.** Decided: sun is the most frequent, the others are less
   frequent. Weights in percent: sun 40, rain 25, heat 20, storm 15. Placeholders to balance.
   Temperature ranges in °C (placeholders): sun 22 to 28, heat 31 to 38, rain 14 to 19, storm 12 to 17.

## Out of scope

Events, trends, outages, strikes, forecast (`outlook`), popularity, weather visuals, applying the
factors to customers (#38), the demo scenarios themselves.

## Done when

1. A new run has a seed; the same seed and day always give the same weather, independent of
   the order in which days are asked for; different seeds differ.
2. Over many days every weather appears, sun is the most frequent and the shares follow the
   weights roughly (a test with a fixed seed range, no flakiness). Every temperature lies inside
   the range of its weather.
3. The override fixes the weather; clearing it brings the rolled weather back.
4. Refused, and the saved run stays identical: unknown weather id, wrong types, the override
   endpoint without the switch, the override endpoint from a non-loopback address.
5. The seed is never in any API answer (tested over `GET /api/state` and every action answer).
6. The seed and the override survive a restart; a save from before this spec still loads.
7. All numbers are whole numbers; the state stays complete and settable; no `random` call
   without the seed.
8. `tests/` untouched (only a new test file), `uv run pytest` passes. In the browser: today's
   weather with its picture and temperature is shown on the campus page and on the dashboard
   and changes with the override, no console errors.
9. PR "Closes #10", AI code review done and its findings handled.

## Security

Roadmap 3a and 3b: the seed lives on the server only; the override is a local demo switch;
every field validated against the fixed weather list; a rejected action changes nothing; error
texts are our own rule messages.
