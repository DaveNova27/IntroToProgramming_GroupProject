# Campus Tycoon

A five-day snack-stand simulation (Nova SBE, Introduction to Programming).
Start with €100, buy stock, set prices, open the stand five times, end with the
best overall result. The rules come from the BRD (CT01–CT05, CT R1–R5); each
feature is described by a spec in `specs/`. Working rules for coding agents are
in `AGENTS.md`.

## Run

```
uv run python app.py        # then open http://127.0.0.1:8000
uv run pytest               # all checks from the specs
```

Stop the server with **⌃ Control + C**. The run is saved in `data/campus_tycoon.db`
(local only, not in Git) and is loaded again on the next start.

## How it fits together

| Layer | Files | Job |
|---|---|---|
| Rules | `logic.py` | Pure functions: `new_state`, `buy`, `set_price`, `demand`, `trade_day`, `stock_overview`, `overall_gain`. A refused action raises `RejectedAction`; every function returns a new state. Money is integer cents. |
| Storage | `db.py` | SQLite, one run. `save` (never rewrites a stored day), `save_new_run` (replaces the run and its history in one transaction), `load`. |
| Server | `app.py` | Flask. `GET /api/state`, `POST /api/buy`, `/api/price`, `/api/open` (needs the current `day`), `/api/new-run` (needs `confirm: true`). Each request loads the run, applies one rule and saves only if it was accepted. `/map` redirects to `/#map`; `/map?embed=1` serves the map page for the iframe. |
| Dashboard | `static/index.html`, `style.css`, `app.js` | KPIs, stock overview, product cards, open-the-stand forecast, charts, history. Layout uses container queries (`@container dash`) so it also fits the side panel. |
| View switch | `static/views.js` | One map iframe that is never reloaded: over the "Campus live" window on the dashboard, or full screen (`#map`). Dashboard as a slide-in panel over the map. Syncs both views with `postMessage` (`action`, `mode`, `ready`, `open-dashboard`, `panel-open`). |
| 3D map | `static/map.html`, `map.css`, `map.js` | three.js 0.170 from the jsDelivr CDN (needs internet). Stylised Nova SBE campus in Carcavelos: kiosk, storage shed, truck deliveries, students queueing per product, live sales ticker, day/night. Modes `preview` (small window, auto-rotate, no HUD) and `main`. Animations run one after another in a queue (`enqueue`). |
| Shared | `static/common.js` | `$`, `esc`, `fmt`, `fmtSigned`, `toast`, product emoji. |

The browser never decides a rule: it sends the action, the server answers with
the new state (or the reason for a refusal), and the screens only show and
animate that answer.

## Specs (all implemented, tests in `tests/`)

| Spec | Branch | What |
|---|---|---|
| `first-feature.md` | – (initial commit) | Buy, set prices, trade one day, restart safely |
| `full-run.md` | `full-run` | Days 2–5, final result, run history, new run with confirmation. Written without the BRD at hand: check IDs and wording against it. |
| `stock-overview.md` | `stock-overview` | Units, value at cost, sells today / left after today per product |
| `campus-map.md` | `campus-map` | 3D campus map with truck, queues, ticker |
| `view-switch.md` | `view-switch` | Live window on the dashboard, map as main view, dashboard as side panel |
| `nova-campus.md` | `nova-campus` | Scene styled after Nova SBE Carcavelos (beach, tunnel, fort, pines) |
| `finite-prices.md` | `finite-prices` | Refuse non-finite prices without changing the saved run; regression checks in `checks/` |

The tag `v1.0` is the dashboard-only version before the map.

## Known issues and ideas

- The 3D map needs an internet connection for three.js; the dashboard works offline.
- To try changes without touching your own save, copy `app.py`, `logic.py`,
  `db.py` and `static/` to a temporary folder and start it there on another
  port (`python -c "import app; app.app.run(port=8765)"`): `db.py` keeps its
  database next to itself.
