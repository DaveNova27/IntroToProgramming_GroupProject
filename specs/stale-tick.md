# Stale tick (`stale-tick`)

Written and built 2026-11-12. A small fix for the live demo of `demo-scenarios`.

## Why

A headless Chromium run of the four demo scenarios on `main` showed exactly one
`POST /api/shift/tick` answered 400 ("no open day"): when *Next* went from scenario 3 (open day)
to scenario 4 (`grow`, day closed). A tick that was already waiting or on its way from the old day
reached the server after the new run was saved. Nothing broke (the 400 answer carries the current
state and the page takes it over), but the console showed a red "Failed to load resource: 400",
which could be seen during the live demo. The same race can also make a stale tick count one tick
of the *new* scenario when it has an open day as well (scenario 1 to 2, 2 to 3).

## What

Only `static/world/serial.js` and `static/world/ui.js` change. The server stays as it is: it
already refuses the tick and changes nothing.

1. Every request that replaces the run (the demo load `/api/demo/load`, the end of the demo
   `/api/demo/finish`, which books an open day, and *New run* on the campus `/api/new-run`) is sent
   from the same queue as the ticks and the shift clicks (`requests`, `serial.js`). A tick already
   on its way is answered first; a tick never overtakes the replacing request.
2. `serial.js` gets epochs: `renew()` says the run was replaced. A job queued before it and not
   started yet is dropped; a running job gets `stale()` to ask before it takes its answer over.
3. `renew()` is called only once the replacement **worked** (`freshRun`, and the end of the demo
   without an error). A refused or failed request drops nothing: ticks and clicks queued meanwhile
   still belong to the run that stays, and the answers of requests already sent are taken over.
4. A new run started on the dashboard (`syncFromDashboard`, kind `new-run`) calls `renew()` too,
   and a tick answer that arrives after it is not taken over (the dashboard's state counts).

The tick timer keeps running during a replacement: `once("tick")` lets at most one tick wait, and
that one is dropped once the replacement worked.

## Code review

`/code-review` (high) on the first version found that it ended the old run before the replacement
was answered (a refused demo load dropped queued clicks and the answer of a tick already sent),
that its timer stop could be undone by any redraw, and that the checks only read the source. Fixed
by the design above; the queue is now checked for real with Node. Not fixed: see "Known limit".

## Out of scope

The server and its answers, the pace of the ticks, the dashboard page's own requests
(`static/app.js`), the other campus panels (Stock, Prices, Shops).

## Decide

None: no test changed. New checks in `tests/test_stale_tick.py` (the queue with Node, the wiring
in `ui.js` by its text).

## Known limit

A new run started on the **dashboard** is sent by the dashboard page, which cannot wait for a tick
that the campus has on its way. That tick can still be refused once (its answer is not taken over);
the live demo runs on the campus, so it is not affected.

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
