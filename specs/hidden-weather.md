# Hidden weather

Issue #75. Found in the audit (`docs/audit-report.md`, item B1).

## What

Before the day is opened the screens must not show anything that depends on the real weather.
Until now the field `weather` was empty, but `products[].breakdown` and `products[].customers`
(also the stock overview, the day forecast and the live price preview) were calculated with the
real weather and named it ("Weather: Rainy"). In 28 of 40 seeds the real weather could be read
before the day was open, so the 20 % forecast error was worthless.

`logic.known_state(state)` gives the state as the player may reason about it: before the day is
opened the weather is the forecast. `app.view` and `/api/price_preview` use it for the numbers
they show. The rules that book a day (`start_shift`, `tick`, `trade_day` on the saved run) still
use the real state. An open day or a finished run is unchanged.

## Out of scope

The forecast error rate, events, weather visuals, the wording of the breakdown line, the demo override.

## Done when

1. Two runs with the same forecast but a different real weather give the same `products`,
   `stock_overview`, `forecast` and `price_preview` before the day is opened (`tests/test_hidden_weather.py`).
2. After *Open day* the real weather is shown and counts as before.
3. The saved state is not changed by `known_state`.
4. `uv run pytest` passes, `tests/` untouched.

Note for the player: the numbers before the day are now based on the forecast; they can change
when the day opens (a wrong forecast).

## Decide: two changed tests

Confirmed in the session by the owner of this spec (David): the two old tests named the data this
spec changes on purpose. Nothing is weakened, skipped or deleted.

1. `tests/test_pricing.py::test_the_shift_the_day_the_overview_and_the_screen_agree` (4 cases):
   it compared the stock overview and the screen with the real shift **before** the day was open.
   Now both are compared on the opened day (`logic.open_day`), where the real weather counts.
   The shift, the day and the planned customers are still compared as before.
2. `tests/test_pricing.py::test_the_endpoint_answers_and_saves_nothing`: the expected preview is now
   `customer_breakdown(logic.known_state(before), ...)`, because before the day is opened the
   preview uses the forecast. It still checks status 200 and that nothing is saved.
