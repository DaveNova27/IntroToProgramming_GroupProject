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

Only `static/world/ui.js` changes. The server stays as it is: it already refuses the tick and
changes nothing.

1. `runGen` counts which run the page plays. `replaceRun(job)` raises it, stops the tick timer and
   queues the job in the same queue as the ticks and the shift clicks (`requests`, `serial.js`):
   a tick already on its way is answered first, then the job sends its request. The timer starts
   again from the answer (`renderAll`) or, if there is no answer, at the end of `replaceRun`.
2. `shiftTick` and `shiftAction` remember `runGen` when they are queued. A job of an older run is
   not sent, and the answer of one that was already on its way is not taken over.
3. Through `replaceRun`: the demo load (`/api/demo/load`), the end of the demo (`/api/demo/finish`,
   it books an open day) and *New run* on the campus (`/api/new-run`).
4. A new run started on the dashboard (`syncFromDashboard`, kind `new-run`) raises `runGen` too.

## Out of scope

The server and its answers, the pace of the ticks, the dashboard page's own requests
(`static/app.js`), the other campus panels (Stock, Prices, Shops).

## Decide

None: no test changed. New checks in `tests/test_stale_tick.py`.

## Known limit

A new run started on the **dashboard** is sent by the dashboard page, which cannot wait for a tick
that the campus has on its way. That tick can still be refused once (the answer is dropped now);
the live demo runs on the campus, so it is not affected.

## Checked in the browser

A Playwright script (not in the repository) runs Demo, confirm, Fill/Sell in scenario 1 until 5
are sold, *Next* three times, unlocks the Beach Cafe and presses *Free play*, counting answers of
400 and above and console errors. To make the race show up locally, tick requests were held back
by a random 0 to 400 ms before they reach the server (as on the public URL).

| Run | 400 answers | Console errors |
|---|---|---|
| `main`, 3 rounds, delay up to 400 ms | 1 (`/api/shift/tick`) | 1 ("Failed to load resource: 400") |
| this fix, 5 rounds, delay up to 400 ms | 0 | 0 |
| this fix, 3 rounds, delay up to 900 ms | 0 | 0 |
| this fix, 1 round, no delay | 0 | 0 |
| this fix, *New run* on the campus during scenario 2, 6 times, delay up to 600 ms | 0 | 0 |
