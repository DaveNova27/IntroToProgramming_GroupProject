# Campus Tycoon

A 30-day snack-stand simulation (Nova SBE, Introduction to Programming).
Start with €100, buy stock, set prices, open the stand once per day, end with the
best overall result. The rules come from the BRD (CT01–CT05, CT R1–R5); each
feature is described by a spec in `specs/`. Working rules for coding agents are
in `AGENTS.md`. The plan for the group project (features, build order, demo
mode) is in [`docs/feature-roadmap.md`](docs/feature-roadmap.md).

Built individually for the Solo Project, now extended as the Group Project for
2477-2627_S1 Introduction to Programming.

## Group

| Name | Student number |
|---|---|
| David Ben Morsey | 79133 |
| Christopher Bryce Tiedke | 79960 |
| Gregor Maximilian Rosenberger | 78878 |
| Felix Antes | _TODO: add student number_ |

**Deployed app:** _TODO: add the deployed URL once the project is deployed_

## Run

```
uv run python app.py        # then open http://127.0.0.1:8000
uv run pytest               # all checks from the specs
```

Stop the server with **⌃ Control + C**. The run is saved in `data/campus_tycoon.db`
(local only, not in Git) and is loaded again on the next start.

## Working in the group

1. Pick a spec from the roadmap ([`docs/feature-roadmap.md`](docs/feature-roadmap.md), section 7) and open or find its GitHub Issue (template "Spec"). Assign yourself before you start.
2. Create a branch named after the spec, e.g. `day-context`, from an up-to-date `main`. Never commit a feature to `main` directly.
3. Write `specs/<name>.md` (What, Out of scope, Done when), then build only that.
4. Run `uv run pytest` before every push. Never edit, delete or skip anything in `tests/`; add new test files for your spec.
5. Open a pull request into `main` with the PR template. It needs a passing `Tests` check (GitHub Actions runs `uv run pytest`) and an AI code review (for example `/code-review` in Claude Code) whose findings are fixed or answered in the PR. No human approval is required.
6. One spec per branch and per pull request. Keep it inside the spec's "Out of scope" fence.

Two tracks run in parallel, see the roadmap: **logic** (game rules in `logic.py`, `db.py`, `app.py`) and **visuals** (campus look and walking in `static/world/`, `static/map.css`). Every feature spec follows the three rules in section 6 of the roadmap (complete settable state, overridable day context, no randomness without the seed) so the demo mode can be built last without a rebuild.

## How it fits together

| Layer | Files | Job |
|---|---|---|
| Rules | `logic.py` | Pure functions: `new_state`, `buy`, `set_price`, `demand`, `trade_day`, `stock_overview`, `overall_gain`, `unlock_shop`, `buy_upgrade`. The shops and products are data tables (`SHOPS`, `CATALOGUE`). A refused action raises `RejectedAction`; every function returns a new state. Money is integer cents. |
| Storage | `db.py` | SQLite, one run (day, cash, products, shops, player, history). An old save without shops still loads. `save` (never rewrites a stored day), `save_new_run` (replaces the run and its history in one transaction), `load`. |
| World data | `world.py` | The campus as data: zones, doors, desks, solid objects, room layouts. No rules and no drawing. |
| Server | `app.py` | Flask. `GET /api/state`, `/api/world`, `POST /api/buy`, `/api/price`, `/api/open` (needs the current `day`), `/api/new-run` (needs `confirm: true`), `/api/player`, `/api/shop/unlock`, `/api/shop/upgrade`. Each request loads the run, applies one rule and saves only if it was accepted. `/map?embed=1` serves the campus page for the iframe. |
| Dashboard | `static/index.html`, `style.css`, `app.js` | KPIs, stock overview, product cards, open-the-stand forecast, charts, history. Layout uses container queries (`@container dash`) so it also fits the side panel. |
| View switch | `static/views.js` | One campus iframe that is never reloaded: full screen (the default), or over the "Campus live" window of the dashboard page (`#dashboard`). Dashboard as a slide-in panel over the campus. Syncs both views with `postMessage` (`action`, `mode`, `ready`, `open-dashboard`, `panel-open`, `panel-closed`). |
| Campus | `static/map.html`, `map.css`, `static/world/` | The 2.5D world from Felix Antes' Nova Beach Ventures, drawn on a canvas: walking with W A S D or by click, collision, finding a way, smooth camera, doors between the zones, light and sea. `main.js` runs the loop, `ui.js` shows the display and panels and talks to the API. Modes `preview` (small window, no display) and `main`. |
| Shared | `static/common.js` | `$`, `esc`, `fmt`, `fmtSigned`, `toast`, product emoji and colours. |

The browser never decides a rule: it sends the action, the server answers with
the new state (or the reason for a refusal), and the screens only show and
animate that answer.

## Specs (all implemented, tests in `tests/`)

| Spec | Branch | What |
|---|---|---|
| `first-feature.md` | – (initial commit) | Buy, set prices, trade one day, restart safely |
| `full-run.md` | `full-run` | Days 2–5, final result, run history, new run with confirmation. Written without the BRD at hand: check IDs and wording against it. |
| `stock-overview.md` | `stock-overview` | Units, value at cost, sells today / left after today per product |
| `campus-map.md` | `campus-map` | 3D campus map with truck, queues, ticker (replaced by `world-core`) |
| `view-switch.md` | `view-switch` | Live window on the dashboard, map as main view, dashboard as side panel |
| `nova-campus.md` | `nova-campus` | Scene styled after Nova SBE Carcavelos (beach, tunnel, fort, pines) |
| `finite-prices.md` | `finite-prices` | Refuse non-finite prices without changing the saved run; regression checks in `checks/` |
| `campus-polish.md` | `campus-polish` | Coastal Tycoon visual polish: facade detail, landscaped plaza, warm light, sea and coordinated UI |
| `longer-run.md` | `longer-run` | 30-day season instead of five days (`LAST_DAY` in `logic.py`) |
| `world-api.md` | `world-api` | The campus as data in `world.py`, player position in the state |
| `world-core.md` | `world-core` | The 2.5D world replaces the three.js map; the campus opens first |
| `world-art.md` | `world-art` | Felix' figures for the player and the people in rooms, passers-by outdoors |
| `shop-unlock.md` | `shop-unlock` | Four shops (Cafe, Beach Cafe, Merchandise, Surf Shop): a run starts with the Cafe and its coffee; more shops are unlocked and more products and employee places bought with money, each purchase is one level. Shops window on the campus page. Prices are placeholders. |
| `shop-process.md` | `shop-process` | A day played live in the Cafe: *Open day* starts the day clock (300 ticks), *Shift* starts the one 90-tick shift of the day (carry stock from the storeroom to the counter, 20 units, and serve a queue), *Skip* lets the rest of the day pass with no sale. Whoever does not work earns nothing. The day closes into the history like `trade_day`, which stays for the day without a player (later: with staff) and is refused while a day is open. Shift panel on the campus page. Walking in the shop is not wired to it yet. |

The tag `v1.0` is the dashboard-only version before the map.

## Group project roadmap

The specs above are the solo-project history. The group project continues with
the specs listed in [`docs/feature-roadmap.md`](docs/feature-roadmap.md) (roadmap v2):
`world-core`, `world-art`, `world-api`, `day-context`, `badges`, `nova-zones`,
`nova-design`, `shop-unlock`, `shop-process`, `shop-art`,
`outlook`, `popularity`, `events-and-disruptions`, `weather-visuals`, `staff`,
`outfits`, `guests`, `demo-scenarios` and `final-polish`. The map is the 2.5D
world taken from a teammate's project (Nova Beach Ventures, code and art made with
AI, credit: https://github.com/felix-anthes-png/nova-beach-ventures). Progress is
tracked in the GitHub Issues (label `spec`).

## Known issues and ideas

- The shop prices, unlock prices and levels are placeholders to balance. The price logic itself is replaced in `pricing` (#38).
- The opened day (300 ticks) is a placeholder length; a shift must fit into what is left of it, one shift per day.
- A played day (`shop-process`) is paced by the browser: it sends one tick request a second, and the server counts them. Two open pages double the speed, and a script can play a day in an instant. Only the player's own run is affected. Walking in the shop is not wired to the rules yet.
- Ideas not yet a spec: customers of the Merchandise shop wear the clothes when they leave, beach loungers to rent at the Beach Cafe, up to three printers on campus (refill paper and ink).
- The campus still shows Felix' layout. `nova-zones` and `nova-design` turn it into the real Nova with its beach cafe.
- A trading day only moves the light and then shows its result. The old map's truck, queues and live ticker went with three.js; customers on the map are the spec `guests`.
- The passers-by are decoration: they cause no sale.
- Water in the courtyard basin is not solid: people can walk through it.
- To try changes without touching your own save, copy `app.py`, `logic.py`,
  `world.py`, `db.py` and `static/` to a temporary folder and start it there on another
  port (`python -c "import app; app.app.run(port=8770)"`): `db.py` keeps its
  database next to itself.
