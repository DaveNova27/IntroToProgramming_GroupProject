# Cleanup: dead code and small findings

Issue #84. Found in the audit (`docs/audit-report.md`, items Q1, D1, B6, B8).

## What

Nothing new for the player; less to read and a few small fixes.

1. **Dead code out** (Q1): the unreachable play-a-day path of the campus (`playDay`, `animating`,
   `dayRunning`, `fast`, the Skip button `#btn-fast`, the `kind: "open"` branch of the dashboard
   message: no screen sends it any more), `novaIsOpen`, `rectCollider`, `circleCollider`,
   `drawColumnLine`, the unused field `shift_day_ticks`, the old label "Play day" and the
   reference to a `map.js` that no longer exists.
2. **Price text** (B6): `euros_to_cents` accepts only plain digits with a point or a comma. `1e2`,
   `1_0`, a sign and digits of other scripts were accepted before; they are now refused with the
   usual message. Valid amounts and the two-decimal rule are as before.
3. **Missing product** (B8): the history and the day summary show the product id when the run no
   longer owns the product (an edited run), instead of stopping to draw.
4. **Old specs** (D1): `employees`, `investments`, `multi-business` and `net-worth` say at the top
   that they belong to the dropped first plan.

## Out of scope

Splitting big files, behaviour changes, `logic.demand` (a test pins it), `/api/day-override`
(tests pin it), `/api/open` (its own spec `retire-trade-endpoint`), `drawFacadeBandX` (14 callers).

## Done when

1. `tests/test_cleanup.py`: the removed names are gone from `static/` and `app.py`; the price
   text cases; the valid cases still convert.
2. The campus runs in the browser as before (a day, the panels, the evening; no console errors).
3. `uv run pytest` passes, `tests/` untouched.

Rules: no money rule, randomness or state changes; a refused price changes nothing.
