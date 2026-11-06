# The outlook: forecast and evening report (`outlook`, issue #12)

Agreed by Christopher on 2026-11-06 (decisions 1 to 7 below). Builds on `day-context` (#10).

## What

Before a day is opened the player sees only a **forecast** of its weather. The forecast is
right most of the time, but about one day in five it is wrong. Whether it is wrong is
drawn from the seed, so the same run always gets the same forecasts. The real weather
appears when the day is opened; from then on the display shows the real weather of today
and the forecast for tomorrow.

When a day closes, the **evening report** (the day summary on the campus page) shows the
forecast for the next day and a tip per open shop: more customers expected, fewer, or
normal, from the weather's demand factors. The player buys stock with the forecast in
mind and takes a risk doing so.

### Rules in `logic.py`

- `OUTLOOK_MISS_PERCENT = 20`: how often the forecast is wrong, in whole percent
  (placeholder to balance).
- `OUTLOOK_MISS`: the table of wrong forecasts as data. A wrong forecast names a weather
  *next to* the true one, not any weather (see "Decide", 1):
  sun → heat or rain, heat → sun, rain → sun or storm, storm → rain.
- `make_outlook(seed, day, override=None)`: pure. The forecast for `day`. Takes the real
  weather of that day (the same roll as `make_day_context`), then rolls with its own
  generator `random.Random(f"{seed}:{day}:outlook")` whether the forecast misses and, if it
  does, which weather from `OUTLOOK_MISS` it shows. The weather roll of `day-context` is
  not touched, so the real weather stays the same as before this spec. Returns
  `{"day", "weather", "temp_range"}` with the forecast weather and that weather's
  temperature range from `WEATHER` (see "Decide", 2). With an override the forecast is
  always right (see "Decide", 3).
- `outlook(state)`: the forecast for the next day whose weather is not shown yet (see
  "Decide", 6): today while the day is not opened, tomorrow while it is open. `None` when
  there is no such day (day 30 opened, or the season over).
- `OUTLOOK_MORE_AT = 115`, `OUTLOOK_LESS_AT = 85` (roadmap B2) and `outlook_tips(state)`:
  for every unlocked shop, in the order of `SHOPS`, `{"shop", "percent", "advice"}` where
  `percent` is the forecast weather's demand factor for the shop and `advice` is `"more"`
  (percent at or above 115), `"less"` (at or below 85) or `"normal"`. Empty when there is
  no forecast. Only advice about stock; no price advice (see "Decide", 7).

### API and screen

- `GET /api/state` (and every action answer) adds `outlook: {day, id, name, temp_low,
  temp_high, miss_percent, tips: [{shop, name, percent, advice}]}` or `null`. It **never**
  contains the seed or whether the forecast is right.
- `weather` (today's real weather, from `day-context`) stays in the answer even before the
  day is opened, because the `day-context` tests expect it (see "Note for David").
- Display, campus page and dashboard: while the day is not opened the weather field shows
  "Forecast" with the forecast's picture and range, e.g. `22–28 °C`. Once the day is
  opened it shows the real weather with its temperature, and a "Tomorrow" field shows the
  forecast for tomorrow. On a phone (760 px and narrower) the campus display hides the
  "Tomorrow" field, as it already hides the time. Texts are set with `textContent` or
  `esc()`.
- Evening report: the day summary on the campus page shows below the day's table the
  forecast for the next day (picture, name, range), one line per tip, e.g. "Cafe: more
  customers expected (140 %), stock up.", and the note "Forecasts are wrong about 1 day in
  5." Nothing about the forecast after the last day.

## Decide

1. **What does a wrong forecast show?** A neighbouring weather (sun instead of heat, rain
   instead of storm), not a random one.
2. **Temperature in the forecast?** The range of the forecast weather (`22–28 °C`).
3. **Forecast with an override?** The override fixes the weather of every day until it is
   cleared, so the forecast shows it and is right. This holds while the override stays
   set: clearing it brings back the seed's roll, which can differ from the forecast that
   was shown.
4. **Error rate.** A constant of 20 % in `logic.py`, a placeholder.
5. **Tip thresholds.** 115 % and 85 % from the roadmap's table B2, placeholders.
6. **When is the real weather shown?** Only after "Open day" (roadmap B1: the player
   decides, then the day's weather counts). Before that the forecast stands in its place.
   The day of the forecast therefore moves with the open day: before opening it is
   today, while open it is tomorrow.
7. **Price tips?** Not yet. The weather does not change the customers until `pricing`
   (#38); until then the tips follow the weather table and show what the player should
   expect once #38 applies it. How price and weather work together is decided in #38.

## Note for David

Hiding the real weather before "Open day" is done in the display only. The server still
sends today's real `weather` in every answer, because `tests/test_day_context.py` expects
it on a day that is not opened (lines 124, 129-130 and 151), and `tests/` may not be
edited. A player who opens the browser's developer tools can read the real weather before
opening the day. To close that, `weather` would have to be `null` until the day is opened,
which needs those two tests changed with your agreement.

## Out of scope

Events and disruptions (`events-and-disruptions`), popularity, weather changing the
customers (`pricing`, #38), price tips, weather visuals in the world (`weather-visuals`), a
forecast for more than one day, showing afterwards whether a past forecast was right, the
clock that does not move while a day is open (a separate issue), the demo scenarios.

## Done when

1. The same seed and day always give the same forecast, independent of the order in
   which days are asked for. The real weather of every day is the same as before this
   spec (the `day-context` tests stay green).
2. Over many seeds and days the forecast is wrong about `OUTLOOK_MISS_PERCENT` of the
   time (a test with a fixed seed range, between 15 % and 25 %, no flakiness). A wrong
   forecast always shows a weather from `OUTLOOK_MISS` of the real weather; a right one
   shows the real weather.
3. With an override the forecast is that weather.
4. Before opening, the forecast is for today; while a day is open, for tomorrow; none once
   day 30 is open and none after the season.
5. The tips name every unlocked shop and no locked one, with the forecast's factor and the
   advice from the two thresholds; empty without a forecast.
6. Neither the seed nor a right/wrong flag is in any API answer (tested over
   `GET /api/state` and every action answer); the outlook has exactly the fields above.
7. All numbers are whole numbers; the state shape is unchanged (the forecast is
   calculated, not stored); no `random` call without the seed.
8. `tests/` untouched apart from the new `tests/test_outlook.py`; `uv run pytest` passes.
   In the browser: before opening, the forecast stands in the weather field; after
   opening, the real weather and "Tomorrow"; the evening report shows the forecast and
   the tips; no console errors.
9. PR "Closes #12", AI code review done and its findings handled, the note for David in
   the PR description.

## Security

Roadmap 3a and 3b `outlook`: the forecast and the tips are created on the server; the
seed never leaves it; no new endpoint, so no new input to validate; texts through
`textContent` or `esc()`. Known gap: today's real weather is in the answer before the day
is opened (see "Note for David").
