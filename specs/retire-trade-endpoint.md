# Retire the trade endpoint (`retire-trade-endpoint`)

Asked for by Felix on 2026-11-21, item A1 of the audit of 2026-11-21 (and B5 of `docs/audit-report.md`
of 2026-11-09, which already proposed this spec by name; `specs/cleanup-dead-code.md` left it for it).

## Why

`POST /api/open` books a whole day with `logic.trade_day`: every customer of the day buys, in every
unlocked shop, with no shift, no staff and no wages. No screen calls it any more (the campus plays a
day with *Open day*, a shift and *Skip*), but the endpoint still answers. A request sent by hand
therefore earns money without working, which breaks the rule of the game "whoever does not work
earns nothing" (`shop-process`).

## What

1. **`POST /api/open` is refused**, always, with the usual refusal of the API: status 400, the
   sentence "A day is played on the campus: open the day and take a shift.", and the unchanged state.
   Nothing is saved. The route stays (it answers 400 instead of 404, as the old tests expect of it).
2. **`logic.trade_day` stays** as a function. It changes nothing saved by itself and keeps two uses:
   the dashboard's forecast "Open for day N" (`view()`, a preview on a copy) and the editor's
   *Skip days* (`editor_skip_days`, only with `CT_EDITOR=1` from this computer).
3. **The README** (table "How it fits together", line *Server*) no longer lists `/api/open` as an
   action; the spec gets its line in the spec table.

## Decide

1. **Refused always, no editor exception.** The audit suggested "except in editor mode"; the editor
   already has *Skip days* with the same rule, so a second way is not needed, and one rule is simpler
   to test.
2. **The route stays and answers 400.** Removing it (404) would break `tests/test_world_api.py:182`
   and `tests/test_shop_process.py:181`, which expect a 400 from it; a refusal keeps them true.
3. **One old test changes, confirmed by the owner of this spec (Felix) in his own words in the
   session:** `tests/test_popularity.py::test_the_state_explains_the_last_day` (line 455) books its day
   with `/api/open` and expects 200. It is about the popularity report of the last day, not about the
   endpoint, so it books the same day the way the game does: `/api/day/open`, `/api/shift/start` in the
   Cafe, `/api/shift/skip`. Checked before: that day gives exactly the same report (popularity 33,
   `{"served": 0, "fair": None, "score": 0}`), so its asserts on the report stay word for word; the one
   line that called `/api/open` becomes three calls, each asserted to answer 200. Nothing is weakened.
   Felix confirmed it on 2026-11-21 in these words: "ich bestätige die Änderung an test_popularity.py:455".
4. **These old tests stay true without a change:** `tests/test_popularity.py:480` (the popularity can
   only fall), `tests/test_day_context.py:150` (no seed in any answer; the day is still not open),
   `tests/test_world_api.py:182` (a body that is not an object is refused with 400),
   `tests/test_shop_process.py:181` (refused while a day is open). The tests of `trade_day` itself
   (`test_first_feature.py`, `test_full_run.py`, `test_pricing.py`, ...) call the function, not the
   endpoint, and stay as they are.
5. **Tests:** the new file `tests/test_retire_trade_endpoint.py`.

## Out of scope

- `/api/day-override` and the editor's weather (the old audit wanted to merge them; a spec of its own).
- `logic.trade_day` itself, the forecast on the dashboard, the editor's *Skip days*.
- The other findings of the audit (A2, B1 to B6, C, D): one spec each, step by step.

## Done when

1. `POST /api/open` answers 400 with the sentence above and the state, for every body (the current
   day, an old day, an empty or broken body), on a fresh run, on a run with stock and staff, and while
   a day is open; the stored run is unchanged byte for byte after each try.
2. With the public mode on (a player cookie) it is refused the same way.
3. The dashboard forecast still comes from `trade_day` and is unchanged; the editor's *Skip days*
   still works.
4. No screen file (`static/`) calls `/api/open`.
5. `test_popularity.py:455` changed as in "Decide" 3, written into the PR; the full suite passes; no
   other old test changed.

## Security

The change closes a way to earn money without playing; it adds no input, no request and no rule that
reads the request body. The refusal returns only the player's own state, like every refusal.
