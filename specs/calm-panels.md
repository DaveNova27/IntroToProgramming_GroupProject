# Calm panels

Issue #74. Found in the audit (audit report in PR #72, items U1, U2, U3).

## What

The side panels of the campus page (Stock, Prices, Shops, Your room, Shift) stay calm while a day
runs. Before, the server's tick (once a second) redrew the open panel every time:

1. A quantity typed in the Stock panel jumped back to 10, and the focus was lost; the buttons of the
   Shops panel were replaced every second, so a click that fell on a tick was lost.
2. A click on Refill, Sell or Start shift while a request was running was dropped without a word.
3. Two texts were outdated: "The weather does not change the number of customers yet" (evening
   report) and "every price is above twice the reference" (dashboard notice).

After this spec:

1. `setPanelHtml` (`static/world/ui.js`) redraws a panel only when its content changed. When it did,
   typed values and the focused field (with its cursor) are kept.
2. `static/world/serial.js` runs the shift requests one after the other: a click waits for the
   request before it instead of being dropped; the tick is skipped while the last tick still waits.
3. The two texts are fixed (the first removed, the second says "too high for any customer").

## Out of scope

The look of the panels, `shop-walk`, the dashboard page's own request lock (`static/app.js` `send`),
the editor panel (it already redraws only when its numbers change), accessibility of the panels.

## Done when

1. `tests/test_calm_panels.py`: the serial helper runs jobs in order, survives a failing job, and
   ignores a second tick while one waits (needs Node, skipped without it); both texts are gone; no
   `shiftBusy` is left.
2. Checked in the browser with a day running: a typed quantity (and the focus) survives several
   ticks; a click on a shops button during a tick is not lost.
3. `uv run pytest` passes, `tests/` untouched.

Rules: no money, no randomness and no state are touched; every action is still a server request.
