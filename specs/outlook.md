# The outlook: a forecast of tomorrow's weather (`outlook`, issue #12)

Agreed by Christopher on 2026-11-06 (all five recommendations accepted). Builds on `day-context` (#10).

## What

The player sees a forecast of tomorrow's weather next to today's weather. The forecast is
right most of the time, but about one day in five it is wrong. Whether it is wrong is
drawn from the seed, so the same run always gets the same forecasts. With the forecast
the player decides how much stock to buy for tomorrow, and takes a risk doing so.

### Rules in `logic.py`

- `OUTLOOK_MISS_PERCENT = 20`: how often the forecast is wrong, in whole percent
  (placeholder to balance).
- `OUTLOOK_MISS`: the table of wrong forecasts as data. A wrong forecast names a weather
  *next to* the true one, not any weather (see "Decide", 1):
  sun → heat or rain, heat → sun, rain → sun or storm, storm → rain.
- `make_outlook(seed, day, override=None)`: pure. The forecast for `day` (the day after
  today). Takes the true weather from `make_day_context(seed, day, override)`, then rolls
  with its own generator `random.Random(f"{seed}:{day}:outlook")` whether the forecast
  misses and, if it does, which weather from `OUTLOOK_MISS` it shows. The weather roll of
  `day-context` is not touched, so today's and tomorrow's real weather stay the same as
  before this spec. Returns `{"day", "weather", "temp_range"}` with the forecast weather and
  that weather's temperature range from `WEATHER` (see "Decide", 2).
  With an override the forecast is always right (see "Decide", 3).
- `outlook(state)`: the forecast for `state["day"] + 1`, or `None` when there is no
  tomorrow (on the last day and after the season).

### API and screen

- `GET /api/state` (and every action answer) adds `outlook: {day, id, name, temp_low,
  temp_high}` or `null`. It **never** contains the seed, the true weather of tomorrow, or
  whether the forecast is right.
- Next to today's weather the dashboard and the head-up display on the campus page show
  "Tomorrow": the small picture of the forecast weather and its range, e.g. `22–28 °C`.
  The pictures are the existing inline SVG of `day-context`; texts are set with
  `textContent`.

## Decide (my recommendations)

1. **What does a wrong forecast show?** Recommendation: a neighbouring weather (sun
   instead of heat, rain instead of storm), not a random one. It is closer to real
   forecasts and the player is misled a little, not completely.
2. **Temperature in the forecast?** Recommendation: the range of the forecast weather
   (`22–28 °C`), not an exact number. It needs no extra roll and reads like a forecast.
3. **Forecast with an override?** Recommendation: the override fixes the weather of every
   day until it is cleared, so tomorrow is also that weather, and the forecast shows it
   and is always right. The demo mode then never shows a wrong forecast by accident.
4. **When is there a forecast?** Recommendation: whenever there is a tomorrow, also while
   a day is open. None on day 30 and after the season.
5. **Error rate.** Recommendation: a constant of 20 % in `logic.py`, a placeholder like
   the other numbers.

## Out of scope

Events and disruptions (`events-and-disruptions`), popularity, weather changing the
customers (`pricing`, #38), weather visuals in the world (`weather-visuals`), a forecast
for more than one day, showing afterwards whether a past forecast was right, the demo
scenarios.

## Done when

1. The same seed and day always give the same forecast, independent of the order in
   which days are asked for. The real weather of every day is the same as before this
   spec (the `day-context` tests stay green).
2. Over many seeds and days the forecast is wrong about `OUTLOOK_MISS_PERCENT` of the
   time (a test with a fixed seed range, between 15 % and 25 %, no flakiness). A wrong
   forecast always shows a weather from `OUTLOOK_MISS` of the true weather; a right one
   shows the true weather.
3. With an override the forecast is that weather and always right.
4. No forecast on the last day and after the season; there is one while a day is open.
5. Neither the seed nor the true weather of tomorrow nor a right/wrong flag is in any API
   answer (tested over `GET /api/state` and every action answer, on a day where the
   forecast is wrong).
6. All numbers are whole numbers; the state shape is unchanged (the forecast is
   calculated, not stored); no `random` call without the seed.
7. `tests/` untouched apart from the new `tests/test_outlook.py`; `uv run pytest` passes.
   In the browser: the forecast with picture and range is shown on the dashboard and on the
   campus page and changes with the override, no console errors.
8. PR "Closes #12", AI code review done and its findings handled.

## Security

Roadmap 3a and 3b `outlook`: the forecast is created on the server; the seed and the true
result of tomorrow never leave it; no new endpoint, so no new input to validate; texts
through `textContent`.
