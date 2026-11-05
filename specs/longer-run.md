# Group feature: A season instead of five days (Campus Tycoon)

**Product:** Campus Tycoon, a growing tycoon business on campus. **User:** the player running it.

> Group project draft, not from a BRD. Agree the exact day count with the team before
> building; `30` below is a placeholder. This spec should land **before**
> `multi-business.md`, `investments.md`, `employees.md` and `net-worth.md`: they all
> assume a run that is long enough for a business to grow, pay off staff or earn
> dividends.

## Planning answers

1. **Product and user:** Campus Tycoon; the player who runs it.
2. **Trigger:** the player keeps trading past day 5, into day 6 and onward.
3. **Before:** a run ends and locks after day 5 (`full-run.md`, CT05).
4. **Rule:** a run has a configurable number of days (`SEASON_LENGTH`, default 30) instead
   of a hardcoded 5. Every rule that compared the day to 5 now compares it to
   `SEASON_LENGTH`. Nothing else about a day (buy, price, demand, trade) changes.
5. **After:** the player can trade for `SEASON_LENGTH` days; the run completes and locks
   exactly as before, just later. History, final result and "New run" behave the same.
6. **Restart:** a run at any day between 1 and `SEASON_LENGTH`, or complete, reloads
   exactly as it was, same as today.

## Why

Multiple businesses, staff and investments need time to pay off. Five days was enough to
prove the core loop works; it is not enough for a season of real decisions.

## What

- Replace every hardcoded `5` that means "the last trading day" with one named constant
  (`SEASON_LENGTH`), defined once in `logic.py`. Default `30`.
- `full-run.md`'s rules (lock after the last day, final result, "New run" with
  confirmation) keep working unchanged, just against the new length.
- The history table, charts and the dashboard's day counter show "Day X of
  `SEASON_LENGTH`" instead of implying 5 is the end.
- No change to demand, pricing or the catalogue.

## Out of scope

- Infinite/sandbox play (no fixed end). Rejected for this project: a run needs a
  reproducible final result to test and to grade.
- Changing `SEASON_LENGTH` per run (e.g. a setting on "New run"). One constant for now.
- Any new business type, staff, investment or luxury mechanic (separate specs).
- The 3D campus map. Keep it working if touched, but do not extend it here.

## Done when

1. **Longer run:** Trading days 1 through `SEASON_LENGTH` all work exactly like days 1-5
   did before; the run only locks after day `SEASON_LENGTH`.
2. **Boundary:** Day `SEASON_LENGTH` behaves like the old day 5 (last tradable day, then
   locked); day `SEASON_LENGTH + 1` does not exist.
3. **Existing tests:** All current tests pass after replacing the hardcoded day count
   with the constant (adjust any test that assumed exactly 5 days to use the constant).
4. **Restart:** A run reloaded mid-season or after completion shows the same day, cash,
   stock and history as before stopping the app.
