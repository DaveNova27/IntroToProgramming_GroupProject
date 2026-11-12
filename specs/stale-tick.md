# Stale tick (`stale-tick`)

Issue #99. Written and built 2026-11-12. A small fix for the live demo of `demo-scenarios`.

## Why

A headless Chromium run of the four demo scenarios on `main` showed exactly one
`POST /api/shift/tick` answered 400 ("no open day"): when *Next* went from scenario 3 (open day)
to scenario 4 (`grow`, day closed). A tick that was already waiting or on its way from the old day
reached the server after the new run was saved. Nothing broke (the 400 answer carries the current
state and the page takes it over), but the console showed a red "Failed to load resource: 400",
which could be seen during the live demo. The same race can also make a stale tick count one tick
of the *new* scenario when it has an open day as well (scenario 1 to 2, 2 to 3).

## What

Only the browser changes (`static/world/serial.js`, `static/world/ui.js`, `static/views.js`,
`static/app.js`). The server stays as it is: it already refuses the tick and changes nothing.

1. Every request that replaces the run (the demo load `/api/demo/load`, the end of the demo
   `/api/demo/finish`, which books an open day, and *New run* on the campus `/api/new-run`) is sent
   from the same queue as the ticks and the shift clicks (`requests`, `serial.js`). A tick already
   on its way is answered first; a tick never overtakes the replacing request.
2. `serial.js` gets epochs: `renew()` says the run was replaced. A job queued before it and not
   started yet is dropped; a running job gets `stale()` to ask before it takes its answer over.
3. `renew()` is called only once the replacement **worked** (`freshRun`, and the end of the demo
   without an error). A refused or failed request drops nothing: ticks and clicks queued meanwhile
   still belong to the run that stays, and the answers of requests already sent are taken over.
4. A new run started on the **dashboard** is sent by the campus once it runs: the dashboard fires
   `new-run-wanted` (cancelable); `views.js` takes it over when the map has said `ready` and sends
   the map `{type: "new-run"}`. The map runs the same `newRun()` as its own dialog (from the queue
   of the ticks) and answers `new-run-done` with the message or the error, which the dashboard
   shows as its toast; the new state comes as before with the `action` message (typed inputs are
   not kept after a new run, as before). Before the map is ready no tick runs, so the dashboard
   sends the request itself, as before.
5. If the dashboard ever sends a new run itself, `syncFromDashboard` (kind `new-run`) calls
   `renew()` too, and a tick answer that arrives after it is not taken over.

The tick timer keeps running during a replacement: `once("tick")` lets at most one tick wait, and
that one is dropped once the replacement worked.

## Code review

`/code-review` (high) on the first version found that it ended the old run before the replacement
was answered (a refused demo load dropped queued clicks and the answer of a tick already sent),
that its timer stop could be undone by any redraw, and that the checks only read the source. Fixed
by the design above; the queue is now checked for real with Node. The dashboard's new run, first left open, is
point 4.

## Out of scope

The server and its answers, the pace of the ticks, the dashboard page's own requests
(`static/app.js`), the other campus panels (Stock, Prices, Shops).

## Decide

None: no test changed. New checks in `tests/test_stale_tick.py` (the queue with Node, the wiring
in `ui.js` by its text) and `tests/test_stale_tick_dashboard.py` (the dashboard's new run).

## Known limit

None left. The first version of this spec left the dashboard's new run open (the dashboard could
not wait for a tick the campus had on its way); David asked to fix it in the same PR (point 4).

## Checked in the browser

A Playwright script (not in the repository) runs Demo, confirm, Fill/Sell in scenario 1 until 5
are sold, *Next* three times, unlocks the Beach Cafe and presses *Free play*, counting answers of
400 and above and console errors. To make the race show up locally, tick requests were held back
by a random 0 to 400 ms before they reach the server (as on the public URL).

| Run | 400 answers | Console errors |
|---|---|---|
| `main`, 3 rounds, delay up to 400 ms | 1 (`/api/shift/tick`) | 1 ("Failed to load resource: 400") |
| first version, 5 rounds, delay up to 400 ms | 0 | 0 |
| first version, 3 rounds, delay up to 900 ms | 0 | 0 |
| first version, 1 round, no delay | 0 | 0 |
| first version, *New run* on the campus during scenario 2, 6 times, delay up to 600 ms | 0 | 0 |
| after the review, 5 rounds, delay up to 400 ms | 0 | 0 |
| after the review, 3 rounds, delay up to 900 ms | 0 | 0 |
| after the review, 1 round, no delay | 0 | 0 |
| after the review, *New run* on the campus during scenario 2, 6 times, delay up to 600 ms | 0 | 0 |
| before point 4: *Start a new run* on the dashboard during scenario 2, 6 times, delay up to 600 ms | 3 (`/api/shift/tick`) | 3 |
| with point 4: the same, 6 times, delay up to 600 ms (all 6 sent by the campus) | 0 | 0 |
| with point 4: the same, 6 times, delay up to 900 ms | 0 | 0 |
| with point 4: four scenarios 3 rounds (400 ms), campus *New run* 6 times | 0 | 0 |
