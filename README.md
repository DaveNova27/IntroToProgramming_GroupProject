# Campus Tycoon

A 30-day snack-stand simulation (Nova SBE, Introduction to Programming).
Start with €100, buy stock, set prices, open the day and work the shops, end with the
best overall result. The rules come from the BRD (CT01–CT05, CT R1–R5); each
feature is described by a spec in `specs/` (list below). Working rules for coding agents are
in `AGENTS.md`. The game design (core loop, weather and events, demo mode, glossary) and the
group's plan are in [`docs/feature-roadmap.md`](docs/feature-roadmap.md); the open work is in the
GitHub Issues (label `spec`).

Built individually for the Solo Project, now extended as the Group Project for
2477-2627_S1 Introduction to Programming. The campus is the 2.5D world taken from a teammate's
project (Nova Beach Ventures, code and art made with AI, credit:
https://github.com/felix-anthes-png/nova-beach-ventures). The audit of 2026-11-09
(`docs/audit-report.md`) lists findings, measurements and feature ideas.

## Group

| Name | Student number |
|---|---|
| David Ben Morsey | 79133 |
| Christopher Bryce Tiedke | 79960 |
| Gregor Maximilian Rosenberger | 78878 |
| Felix Anthes | 73306 |

**Deployed app:** https://campus-tycoon.onrender.com

On the public server every run is stored in a Postgres database at Supabase (Frankfurt) and survives
restarts and deploys (spec `persistent-runs`; without `DATABASE_URL` the server falls back to its
temporary disk, which the free host erases). The first visit after a pause takes about a minute while
the server wakes up.

## Run

```
uv run python app.py        # then open http://127.0.0.1:8000
uv run pytest               # all checks from the specs
```

Stop the server with **⌃ Control + C**. The run is saved in `data/campus_tycoon.db`
(local only, not in Git) and is loaded again on the next start. `CT_EDITOR=1 uv run python app.py`
switches on the editor's dev tools (spec `editor-mode`).

**Demo for the presentation** (spec `demo-day`, built on `demo-scenarios`): press *Demo* on the campus
(or open `/?demo`), confirm, and one continuous rainy day follows, from the bed in the morning to the bed
in the evening, in seven steps: wake up, buy the rain jacket, order the day's coffee at the PC, the Cafe
shift, (sun) buy the Beach Cafe and an employee, (rain again) everyone goes inside, go home and sleep.
The card at the bottom left always shows the next step as a button ("Next step: Order stock"); it walks
the figure there, and the card moves on once the goal holds on the server. *Skip* goes on without the
goal (for a rehearsal). The demo replaces your run; *Free play* at the end gives it back to you as it is.
It works locally and on the public URL; the browser only sends the demo's id or `{}`.

**Trying changes without touching your own save:** copy `app.py`, `logic.py`, `guests.py`,
`scenarios.py`, `world.py`, `db.py`, `pgstore.py` and `static/` to a temporary folder and start it there on another
port (`python -c "import app; app.app.run(port=8770)"`): `db.py` keeps its database next to itself.

## Putting it online

Local play needs nothing. The public server runs on **Render**, a free web service described in
[`render.yaml`](render.yaml) (specs `deploy-ready` and `deploy`):

- **Set up once:** in the Render dashboard *New → Blueprint*, pick this repository, confirm. Render
  builds with `uv sync --locked --no-dev --group deploy` (the exact versions of `uv.lock`, gunicorn
  from the `deploy` group, no pytest) and starts `gunicorn` with **one worker** (the locks and the rate
  counter live in the process) on port 10000. `GET /healthz` answers `ok` for Render's health check
  and touches nothing.
- **Variables** (all in `render.yaml`, no secret in the repository): `CT_PUBLIC=1` (a run per player,
  limits, no editor and no weather override), `CT_PROXY=1` (Render's proxy says HTTPS and the visitor),
  `CT_SECRET` (signs the player cookie; Render generates it once and keeps it), `PORT=10000`,
  `PYTHON_VERSION=3.12.14`. One more, **only in Render's dashboard** (*Environment*, as a secret):
  `DATABASE_URL`, the Supabase connection string (*Connect* → *Session pooler*, with the database
  password). It is a password: never in the repository, never in a chat.
- **Redeploy:** every merge into `main` whose `Tests` check passed deploys by itself, or *Manual Deploy*
  in the dashboard. A failed build keeps the running version.
- **Rollback:** *Rollbacks* in the dashboard (the free plan keeps the two previous deploys), or revert
  the pull request on GitHub.
- **What lasts:** the runs, in Supabase. A deploy or restart only empties the server's copy in memory;
  the next request loads the run again. Open the URL two minutes before a demo so the server is awake.
- **Supabase pauses** a free project after a week without activity; the game then answers "The game's
  storage cannot be reached right now" until someone presses *Restore* in the Supabase dashboard. Play
  at least once a week, and check the dashboard the day before the demo. The free plan has no backups.
- **Plan B** if the host is down: `uv run python app.py` on a laptop.

The production server locally, for a test (same gunicorn version as the host):

```
CT_PUBLIC=1 uv run --group deploy gunicorn -w 1 --threads 8 --no-control-socket -b 127.0.0.1:8000 app:app
```

Set `CT_PROXY=1` only behind a proxy that is the only way to reach the server: it then tells the server
who the visitor is, and the cookie is Secure. The server never shows a path or a stack trace to a player.

**Where is the data stored?** Locally in SQLite, one file: `data/campus_tycoon.db`. On the public
server in Postgres at Supabase (Frankfurt): one row per player in the table `campus_tycoon.runs`, the
whole run as one JSON document, found by the random id in the signed cookie. Every run passes through
the same SQLite tables in memory on its way in and out (`db.through_sqlite`), so both stores check and
repair a run with the same rules. The server keeps the runs it has loaded in memory and writes every
change through to Postgres first, which works because exactly one process serves the game. The table is
hidden from Supabase's Data API (own schema, row level security without policies, no grants).

## How it fits together

| Layer | Files | Job |
|---|---|---|
| Rules | `logic.py` | Pure functions: `new_state`, `buy`, `set_price`, `customers_for`, `customer_breakdown`, `price_preview`, `trade_day`, `stock_overview`, `overall_gain`, `unlock_shop`, `buy_upgrade`, `hire`, `upgrade_employee`, `fire_employee`. The shops and products are data tables (`SHOPS`, `CATALOGUE`); the customers come from two segments with price curves (`SEGMENTS`), a mix per shop (`SHOP_MIX`) and the day's factors (`FACTORS`), see `specs/pricing.md`. `demand` is the solo project's old rule, kept only because a test pins it. A refused action raises `RejectedAction`; every function returns a new state. Money is integer cents. |
| Guests | `guests.py` | The guests of a day (`day_plan`, `for_shop`): the crowd of `customers_today` as guests with a kind, a start place and a taste; those who look around choose among the shops with an employee by the walk, the queue and their taste. Pure functions, all randomness from the seed, nothing stored beside the queue. See `specs/guests.md`. |
| Demo | `scenarios.py` | The demo day as data (`STEPS`: text, button, target, goal, and for the start and the two jumps a prepared state) and its rules: `load_scenario`, `advance` (the card moves on by itself), `next_step` (the card's button; a jump loads its state), `step_done`, `finish_demo`, `demo_view`. A prepared state is a patch for `editor_set_state`, so the existing checks validate it. See `specs/demo-day.md`. |
| Storage | `db.py` | SQLite, one run (day, cash, products, shops, player, history). An old save without shops still loads. `save` (never rewrites a stored day), `save_new_run` (replaces the run and its history in one transaction), `load`. |
| Storage (public server) | `pgstore.py` | With `CT_PUBLIC=1` and `DATABASE_URL`: each player's run as one JSON document in Postgres at Supabase (`campus_tycoon.runs`), passed through `db.through_sqlite` on the way in and out (the same CHECKs and repairs as a file), a copy in memory written through, 503 when the database cannot be reached. See `specs/persistent-runs.md`. |
| World data | `world.py` | The campus as data: the zone, the Nova building (parts, walls, entrance), desks, solid objects, room layouts. No rules and no drawing. |
| Server | `app.py` | Flask. Each request loads the run, applies one rule and saves only if it was accepted. **Read:** `GET /api/state`, `/api/world`, `/map` (`?embed=1` for the campus iframe), `/healthz` (the host's health check). **Stock and prices:** `POST /api/buy`, `/api/buy-many` (several products, all or nothing), `/api/price`, `/api/price_preview` (read-only: what a price would bring). **The day:** `/api/day/open`, `/api/shift/start` (a shop), `/api/shift/refill`, `/api/shift/sell`, `/api/shift/tick` (the browser's clock, one a second), `/api/shift/skip`, `/api/day-override` (fix weather and event; a demo switch, off in public mode). **Campus and growth:** `/api/player` (position), `/api/shop/unlock`, `/api/shop/upgrade`, `/api/staff/hire`, `/api/staff/upgrade`, `/api/staff/fire`, `/api/outfit/buy`, `/api/outfit/wear` (an outfit id). **Run and demo:** `/api/new-run` (needs `confirm: true`), `/api/demo/load` (the demo's id and `confirm: true`), `/api/demo/next` (`{}`: the next step of the demo day), `/api/demo/finish`. **Editor** (only with `CT_EDITOR=1`, from this computer): `/api/editor/cash`, `/api/editor/weather`, `/api/editor/skip-days`, `/api/editor/state`, `/api/editor/reset`. `/api/open` (the old instant day) is retired and always refused (`retire-trade-endpoint`). |
| Dashboard | `static/index.html`, `style.css`, `app.js` | KPIs, shop popularity, product cards grouped by shop, open-the-stand forecast, charts, badges, history; in the campus look. Layout uses container queries (`@container dash`) so it also fits the side panel. |
| View switch | `static/views.js` | One campus iframe that is never reloaded: full screen (the default), or over the "Campus live" window of the dashboard page (`#dashboard`). Dashboard as a slide-in panel over the campus. Syncs both views with `postMessage` (`action`, `mode`, `ready`, `open-dashboard`, `panel-open`, `panel-closed`). |
| Campus | `static/map.html`, `map.css`, `static/world/` | The 2.5D world from Felix Anthes' Nova Beach Ventures, drawn on a canvas: walking with W A S D or by click, collision, finding a way, smooth camera, walking into the Nova (the roof fades out and the rooms show), light and sea. `main.js` runs the loop, `ui.js` shows the display and panels and talks to the API. Modes `preview` (small window, no display) and `main`. |
| Shared | `static/common.js` | `$`, `esc`, `fmt`, `fmtSigned`, `toast`, product emoji and colours. |

The browser never decides a rule: it sends the action, the server answers with
the new state (or the reason for a refusal), and the screens only show and
animate that answer.

## Working in the group

1. Pick an open spec from the GitHub Issues (label `spec`) or open one with the template "Spec". Assign yourself before you start.
2. Create a branch named after the spec, e.g. `day-context`, from an up-to-date `main`. Never commit a feature to `main` directly.
3. Write `specs/<name>.md` (Why, What, Decide, Out of scope, Done when), then build only that.
4. Run `uv run pytest` before every push. Never edit, delete or skip anything in `tests/`; add new test files for your spec. If your spec changes data that an old test names on purpose, you may confirm that change yourself (rules in `AGENTS.md`).
5. Open a pull request into `main` with the PR template. It needs a passing `Tests` check (GitHub Actions runs `uv run pytest`) and an AI code review (for example `/code-review` in Claude Code) whose findings are fixed or answered in the PR. No human approval is required. A merge into `main` deploys by itself.
6. One spec per branch and per pull request. Keep it inside the spec's "Out of scope" fence.

Two tracks run in parallel: **logic** (game rules in `logic.py`, `db.py`, `app.py`) and **visuals** (campus look and walking in `static/world/`, `static/map.css`). Every feature spec follows the three rules in section B3 of the roadmap (complete settable state, overridable day context, no randomness without the seed), so the demo can set any moment of a run.

## Specs

Each spec is built on a branch of the same name (follow-ups and `guests` on branches of their own) and
merged with the pull requests in the PR column; its checks are in `tests/` (three older ones in `checks/`). The
tag `v1.0` is the dashboard-only version before the map.

### Solo project

Built for the Solo Project, before the group started (no pull requests).

| Spec | PR | What |
|---|---|---|
| [`first-feature.md`](specs/first-feature.md) | – | Buy, set prices, trade one day, restart safely. |
| [`full-run.md`](specs/full-run.md) | – | Days 2–5, final result, run history, new run with confirmation. Written without the BRD at hand: check IDs and wording against it. |
| [`stock-overview.md`](specs/stock-overview.md) | – | Units, value at cost, sells today / left after today per product |
| [`campus-map.md`](specs/campus-map.md) | – | **Replaced** by `world-core`. 3D campus map with truck, queues, ticker. |
| [`view-switch.md`](specs/view-switch.md) | – | Live window on the dashboard, map as main view, dashboard as side panel |
| [`nova-campus.md`](specs/nova-campus.md) | – | Scene styled after Nova SBE Carcavelos (beach, tunnel, fort, pines) |
| [`finite-prices.md`](specs/finite-prices.md) | – | Refuse non-finite prices without changing the saved run; regression checks in `checks/` |
| [`campus-polish.md`](specs/campus-polish.md) | – | Coastal Tycoon visual polish: facade detail, landscaped plaza, warm light, sea and coordinated UI |

### Game rules

Rules on the server (`logic.py`, `guests.py`, `scenarios.py`, `app.py`).

| Spec | PR | What |
|---|---|---|
| [`longer-run.md`](specs/longer-run.md) | #7 | 30-day season instead of five days (`LAST_DAY` in `logic.py`) |
| [`shop-unlock.md`](specs/shop-unlock.md) | #37 | Four shops (Cafe, Beach Cafe, Merchandise, Surf Shop): a run starts with the Cafe and its coffee; more shops are unlocked and more products and employee places bought with money, each purchase is one level. Shops window on the campus page. Prices are placeholders. |
| [`shop-process.md`](specs/shop-process.md) | #39, #44 | A day played live in the Cafe: *Open day* starts the day clock (300 ticks), *Shift* starts a 90-tick shift (carry stock from the storeroom to the counter, 20 units, and serve a queue), *Skip* lets the rest of the day pass with no sale. Whoever does not work earns nothing. `trade_day` is refused while a day is open. Later one shift per shop (`shift-any-shop`). |
| [`day-context.md`](specs/day-context.md) | #42 | The seed lives in the state; each day has a weather with a temperature drawn from it; a demo override can fix the weather. Weather and temperature are shown; the demand factors per shop are in `WEATHER` and take effect through `pricing`. |
| [`outlook.md`](specs/outlook.md) | #45, #59 | Before *Open day* only a forecast of the day's weather is shown (picture and temperature range); the real weather appears once the day is opened. The forecast is wrong about 20 % of the time (a neighbouring weather, from the seed with its own roll), always right with the demo override. The evening report gives tomorrow's forecast and a tip per open shop. |
| [`staff.md`](specs/staff.md) | #54, #57, #58 | Employees (first for the Cafe, later for every shop, see Known issues): hire on a bought place (refiller, seller), level them up, dismiss them. They run on the server every tick like the player's refill and sell, the shift starts by itself when the day opens, wages are paid at the end of the day (without money they stop working). They are named figures in the Cafe. Numbers are placeholders. |
| [`editor-mode.md`](specs/editor-mode.md) | #56 | Dev tools, off unless the server starts with `CT_EDITOR=1` (and only for requests from this computer): set or add cash, fix the weather, skip several days, one validated state patch (day, shops and levels, stock, prices, seed, player), reset the run. Editor panel on the campus page. Base for `demo-scenarios`; employees and popularity became settable later. |
| [`pricing.md`](specs/pricing.md) | #62 | Customers from two segments (students, visitors) with price curves, a mix per shop and the day's factors (weather first, then the events of `events-and-disruptions`, then the popularity of `popularity`; trend and outfit plug in later); the screen shows the same number everywhere and explains it ("Why this number?", live price preview). Replaces the old one-line demand rule. |
| [`hidden-weather.md`](specs/hidden-weather.md) | #78 | Before the day is opened nothing on the screens depends on the real weather: `logic.known_state` gives the state as the player may know it (the forecast instead of the weather), and the view and the price preview use it. The rules that book a day still use the real weather. |
| [`badges.md`](specs/badges.md) | #79 | 20 badges (first sale, good day, a team of three, profit streaks of 3, 7 and 14 days, every shop unlocked, season winner, ...), each a bronze, silver or gold medal (`BADGES` in `logic.py`), given only by the server the moment they are reached. A card on the campus shows a new one; the evening report, the season's end and the dashboard list them. No reward; placeholder thresholds. |
| [`balance-pass.md`](specs/balance-pass.md) | #82 | The season is balanced: Surf Shop and Merchandise products cost and sell for less (a good season ends at about +5,000 EUR, not +25,000), a warning before a purchase that leaves nothing to buy, a hint for shops only employees can run, the storeroom limit counts the counter. A guard test plays whole seasons. |
| [`editor-staff.md`](specs/editor-staff.md) | #87 | The editor patch can set the employees (shop, place, level, working), so the whole run is settable for the demo mode. A Staff block in the Editor panel. |
| [`events-and-disruptions.md`](specs/events-and-disruptions.md) | #91 | Campus events (exam period, party, career fair, a three-day surf festival) rolled from the seed with their own generator, first two days quiet, nothing saved; they move the customers of each shop through `FACTORS` and stack with the weather. The demo switch and the editor can fix an event; a fixed weather without an event means no event. Outages and strikes are not built (their own later spec). |
| [`guests.md`](specs/guests.md) | #95 | Guests that choose a shop (small version): the day's crowd becomes guests with a kind, a start place and a taste. A third look around and go to another shop with an employee when it is closer, its queue shorter or they like it more (at most 30 % more guests per product, the crowd stays the same). On the map they walk to their shop's line and show their thought in a bubble. |
| [`demo-scenarios.md`](specs/demo-scenarios.md) | #96 | The 3-minute live demo: four prepared days as data in `scenarios.py` (start state, fixed weather and event, text, goal), loaded by id into the player's own run (`POST /api/demo/load` with `confirm`, `POST /api/demo/finish`). A card on the campus shows the step, the text and the goal; the clock runs at two ticks a second while a scenario asks for it. Free play at the end. |
| [`shift-any-shop.md`](specs/shift-any-shop.md) | #103 | The player takes a shift in any unlocked shop, not only the Cafe: several shifts a day one after the other (90 of 300 ticks, one per shop), a finished or staffed shift moves aside and goes on, a staffed shop can be taken over. A shop outside the day's guest plan plans alone. The Shift panel lists where the player can start. |
| [`popularity.md`](specs/popularity.md) | #104 | Every shop has a popularity from 0 to 100 (50 at the start). Each day its customers give a report card (not served = 0, served = as happy as the price was fair) and popularity walks toward it, a fifth up and a third down. It moves the next days' customers by 85 to 115 % through `FACTORS`. Server only; the shop panel and the dashboard show it and why it moved. |
| [`outfits.md`](specs/outfits.md) | #116 | Clothes for the player's figure, bought and changed in the Dorm (basic shirt free, four more from 20 to 60 EUR, prices in cents). Buying and wearing are rules on the server (`buy_outfit`, `wear_outfit`); only the look changes. |
| [`order-at-warehouse.md`](specs/order-at-warehouse.md) | #118 | Stock is ordered on foot at a PC in the Mercado Supply Hall: the *Stock* button walks the player there, the dashboard sends you there. Two old tests that pinned the old desk's place were changed, confirmed by the PR owner (see the spec). |
| [`bulk-order.md`](specs/bulk-order.md) | #119 | The order window has one row per product, so several products are ordered with one click (`/api/buy-many`, all or nothing). `/api/buy` stays. |
| [`cafe-staff-message.md`](specs/cafe-staff-message.md) | #137 | When employees run the Cafe in the player's slot, a refused start there says "Employees run the Cafe. You can serve here beside them." (or "The shift in the Cafe is over for today.") instead of "You are working in the Cafe already.". Only the text; the player could already serve there beside the crew. |
| [`stock-on-counter.md`](specs/stock-on-counter.md) | #139 | The stock card shows what the player holds: the storeroom plus the units on the counters of the open day (`on_counter`, counted by the server; unsold units go back at the day's end), with "N on the counter". The Order button's hint and the dashboard's "in stock" badge and stock tile use the same total. The Shift panel draws no "+0" button. |

### Campus and look

The world in `static/world/`, `world.py` and the dashboard. They draw and walk; no rule is decided here.

| Spec | PR | What |
|---|---|---|
| [`world-api.md`](specs/world-api.md) | #32 | The campus as data in `world.py`, player position in the state |
| [`world-core.md`](specs/world-core.md) | #33 | The 2.5D world replaces the three.js map; the campus opens first |
| [`world-art.md`](specs/world-art.md) | #34 | Felix' figures for the player and the people in rooms, passers-by outdoors |
| [`walk-in.md`](specs/walk-in.md) | #49 | One big Nova building: walk in, the roof fades out; replaces the room zones; the three desks inside |
| [`nova-wings.md`](specs/nova-wings.md) | #50 | More wings for the Nova: the Learning Center and the Mercado can be walked into, a Student Hub, one roof per wing. |
| [`nova-zones.md`](specs/nova-zones.md) | #53 | The map around the Nova: a walkable Dorm with a bed panel, a detailed beach way and beach, the Surf Shop and the Beach Cafe outdoors. |
| [`collapsible-stock-panel.md`](specs/collapsible-stock-panel.md) | #63 | The stock card on the campus page can be folded away, remembered per browser |
| [`day-cycle.md`](specs/day-cycle.md) | #65 | The day ends at the Dorm: when a day closes it gets dark, *Go home* walks the player to the bed (or *Skip the walk*), and the day summary with the evening report shows there. *Sleep* shows the night and a sunrise to 09:00, then a good-morning card lists the forecast, stock and what to do. Ending a day early asks first. No new endpoint and no new rule. |
| [`map-view.md`](specs/map-view.md) | #67 | The world seen straight from the front instead of at 45 degrees: x goes right, y goes down (north at the top, the sea at the bottom), so walking and clicking match the screen. A click lands on the floor tile under the pointer. Drawing only: no rule reads the camera, `world.py` stays. |
| [`click-walk.md`](specs/click-walk.md) | #69 | Click to walk no longer stops halfway at corners: a route first keeps a little more distance from every solid object than the player's radius and falls back to the old tight margin only where nothing else fits, so nothing reachable becomes unreachable. Screen only. |
| [`smooth-frames.md`](specs/smooth-frames.md) | #77 | The campus runs at the screen's rate: no blur filter for the shadows, a slow frame advances the world by its real time. Browser check, not part of the tests. |
| [`calm-panels.md`](specs/calm-panels.md) | #80 | The side panels of the campus stay calm while a day runs: redrawn only when their content changed (typed values and focus stay), shift requests wait for each other instead of being dropped, two outdated texts fixed. |
| [`render-cache.md`](specs/render-cache.md) | #90 | The campus works out its tile list and the Nova's walls once and skips objects far outside the view (rules in `static/world/cull.js`); the picture is the same, checked pixel by pixel in the browser. Numbers are in the spec. |
| [`stale-tick.md`](specs/stale-tick.md) | #100 | No stray tick after the run is replaced: a demo scenario, the end of the demo and a new run (also one started on the dashboard, which the campus sends) are sent from the queue of the ticks (none overtakes them), and once they worked the ticks and clicks queued for the old run are dropped (`serial.js` epochs). No 400 and no console error in a scripted run of the four scenarios. Browser only. |
| [`weather-visuals.md`](specs/weather-visuals.md) | #105 | The world shows the weather of the opened day: grey sky and rain, a storm with wind, high waves and rare soft lightning, a warm tint and shimmer on a hot day; a sunny or unopened day looks as before. The looks are a table in `static/world/weather.js` (pure, tested with Node). No rain indoors, nothing random, lightning and motion off with reduced motion. |
| [`shop-art.md`](specs/shop-art.md) | #106 | The four campus shops show their unlock price or level on the map. Their furnishings change with the products bought. |
| [`map-layout.md`](specs/map-layout.md) | #107, #108 | Walking routes between the Dorm, Nova and beach shops. The world API supplies all four shop layouts and the central storage positions. |
| [`smooth-walk.md`](specs/smooth-walk.md) | #115 | Walking glides past palms, lamps and other objects instead of stopping at them: a step that hits an object slides along its edge before the old two tries. Screen only: no rule, no API, no `world.py`. |
| [`merch-wear.md`](specs/merch-wear.md) | #117 | Guests who buy a hoodie, T-shirt or cap in the Merchandise shop put it on at the counter and walk home wearing it. The server keeps a note of who bought what (`shift["dressed"]`), the map only draws it; no number changes. |
| [`lorry-road.md`](specs/lorry-road.md) | #120 | The road of the delivery lorry runs north from the lane to the edge of the campus. Drawing only. |
| [`stock-by-shop.md`](specs/stock-by-shop.md) | #122 | The stock card on the campus page is grouped by shop: only unlocked shops with the products the player owns, a heading per shop from the second shop on, a divider on phones; it stays foldable and scrolls inside when tall. |
| [`onboarding-guide.md`](specs/onboarding-guide.md) | #127 | A small card guides a new player through the first day in three steps (order coffee at the PC, open the day, take the shift in the Cafe), each with a *Go* button that presses the toolbar's own button. The steps tick off from the server's state (`static/world/guide.js`, pure). Only on the first day of a run, not in a demo; closing it is remembered per browser. |
| [`dashboard-look.md`](specs/dashboard-look.md) | #129 | The dashboard in the campus look (petrol, lime, cream, square corners, mono labels, a dark header with the CT logo) and shorter: no stock overview card, popularity beside the campus window, compact product cards grouped by shop with the price curve inside "Why this number?", one "Go to the order PC" button, gross profit per shop. No dark mode; the server is unchanged. |

### Server, deploy and security

The public server: one run per player, limits, hosting and storage.

| Spec | PR | What |
|---|---|---|
| [`deploy-ready.md`](specs/deploy-ready.md) | #89 | Security headers on every answer; a public mode (`CT_PUBLIC=1`): a run per player (cookie), a rate limit, no dev switches, no paths in errors; how to run it with a production server. Local play is unchanged. |
| [`deploy.md`](specs/deploy.md) | #110, #111 | The game on the internet: a free Render web service from `render.yaml` (built from `main` when the tests passed, one gunicorn worker, the secret generated by Render), gunicorn pinned in the `deploy` group of `uv.lock`, `GET /healthz` for the host's health check (no player, no cookie, no file). Runs on the public server were erased on a restart until `persistent-runs` moved them to Supabase. |
| [`persistent-runs.md`](specs/persistent-runs.md) | #113, #114 | Runs on the public server last: one JSON document per player in Postgres at Supabase (Frankfurt) when `DATABASE_URL` is set, passed through the SQLite rules (`db.through_sqlite`), a write-through copy in memory (one process), a 503 with our sentence when the database cannot be reached, the table hidden from Supabase's Data API. Local play and the tests stay on SQLite. |
| [`retire-trade-endpoint.md`](specs/retire-trade-endpoint.md) | #131 | `POST /api/open` is refused (400, the unchanged state): it booked a whole day with `trade_day`, with no shift, no staff and no wages, so a request sent by hand earned money without playing. `logic.trade_day` stays for the dashboard's forecast and the editor's *Skip days*. |
| [`player-cap.md`](specs/player-cap.md) | #133 | A full public game (2,000 runs) makes room: the run saved longest ago is replaced if it has not been saved for 10 minutes (Postgres `updated_at`, a file's mtime), one for one under the lock of new runs; only with no idle run is the answer still 503 "full". Nothing is deleted while the game is not full; the log names no player. |
| [`request-limits.md`](specs/request-limits.md) | #134 | A request body over 64 KB is refused with 413 and a JSON error before any rule, nothing saved. Behind a trusted proxy the first 5 visits (`/`) after a start log the proxy chain (header names and counts, never an address), to decide which address the server should take behind Cloudflare. |
| [`client-address.md`](specs/client-address.md) | #143 | Behind Cloudflare and Render the limit of new players brakes each visitor on their own: `client_address()` takes the entry Cloudflare wrote, the third from the right of `X-Forwarded-For` (`PROXY_HOPS = 2`), only when Render received the request from a Cloudflare address (`CLOUDFLARE_NETWORKS`). Other chains keep the old rule; IPv6 counts by its /64. Confirmed in Render's log. |

### Docs and housekeeping

| Spec | PR | What |
|---|---|---|
| [`cleanup-dead-code.md`](specs/cleanup-dead-code.md) | #88 | Dead code out (the unreachable play-a-day path, unused functions), a price like `1e2` refused, a missing product in the history no longer stops the screen, old specs marked as dropped. |
| [`docs-refresh.md`](specs/docs-refresh.md) | #124 | The README brought up to date (name, the missing specs, three outdated known issues); the CI actions pinned to commit SHAs (same versions); Dependabot checks the Python packages and the actions weekly. No game code changes. |
| [`docs-sync.md`](specs/docs-sync.md) | #141 | The docs brought up to date after the audit of 2026-11-21 (items D1, D4): `AGENTS.md` names every module of `static/world/`, `badges.css` and `checks/`; three outdated sentences fixed (the deploy line, the roadmap link, the health check's docstring). No game code changes. |
| [`demo-day.md`](specs/demo-day.md) | #146 | The demo becomes one day from bed to bed in seven steps (`scenarios.py`). The card shows the next step as a button that walks the figure there; a reached goal moves it on (`advance`), the two jumps (sun, rain again) load a prepared state of the same day (`POST /api/demo/next`). Replaces the four scenarios of `demo-scenarios`. |
| [`docs-cleanup.md`](specs/docs-cleanup.md) | #145 | The README tidied (specs grouped with their PRs, every route of the server named, the known issues checked against the code) and the roadmap brought to v7 of 2026-11-23. No game code changes. |
| `employees.md`, `investments.md`, `multi-business.md`, `net-worth.md` | #1 | **Dropped.** The first draft of the group features, kept as history only; they describe nothing in the game today. The plan that replaced them is `docs/feature-roadmap.md`. |

## Known issues and ideas

- Staff: wages, hire and level prices and the speed per level are placeholders. With the customers of `pricing` (about 10 per product at the reference price, up to 20 and more at a low price or on a good day) a level 1 seller (one sale every 4 ticks, about 22 in a shift) can fall behind, so the levels now start to matter; the numbers are still placeholders. `trade_day` (day without a player) has no staff and no wages. Employees work in every shop (`STAFF_SHOPS`, logic only): the Cafe on the player's shift, the other shops in `shift["extra"]`. The player can take a shift in every unlocked shop (`shift-any-shop`). Only the Cafe has figures in the world so far (`WORK_SPOTS`).
- The shop prices, unlock prices and levels are placeholders to balance, and so are the price curves, the shop mix and the weather percents of `pricing` (#38).
- The opened day (300 ticks, `OPEN_DAY_TICKS`) and a shift (90 ticks, `SHIFT_TICKS`) are placeholder lengths. A shift must fit into what is left of the day; the player works one shift per shop and day (`shift-any-shop`).
- A played day (`shop-process`) is paced by the browser: it sends one tick request a second, and the server counts them. Two open pages double the speed, and a script can play a day faster (on the public server only the limit of 240 requests a minute slows it). Only the player's own run is affected. Walking in the shop is not wired to the rules yet (issue #40 `shop-walk`).
- Ideas not yet a spec: beach loungers to rent at the Beach Cafe, up to three printers on campus (refill paper and ink). (Merchandise customers wearing what they bought is built: `merch-wear`.)
- The Nova has its first form: four wings joined by openings (the main block of 22 × 8 tiles with a glass-roofed atrium, gallery, Cafe, Merchandise and Print Corner; the Learning Center with a Study Hall and a Seminar; the Mercado Supply Hall; the Student Hub with a Lounge and a Meeting Room). Each wing has its own roof, and the whole floor inside can be walked on. Stock is ordered at the PC in the Mercado Supply Hall (`order-at-warehouse`); the other new wings are places only: nobody works there yet and no rule happens there (issue #40 `shop-walk`). The Dorm, the way to the beach, the Surf Shop and the Beach Cafe outside are `nova-zones`; their final look is the open issue #11 `nova-design`.
- The Cafe and the Merchandise shop in the Nova are shops: guests walk there and queue (`PLACES` in `world.py`); the employees' figures stand only in the Cafe (`WORK_SPOTS`). The three printers of the Print Corner are decoration only: no rule works there yet.
- A trading day (`trade_day`, the day without a player) only moves the light and then shows its result: guests walk only on an opened day.
- Guests (`guests`): the numbers that weigh the walk, the queue and the taste are placeholders. A guest decides once, when the day opens (the plan is stored in the shift as `guest_plan`); nobody changes their mind at the counter. A shop only the player runs (the Cafe without an employee) never receives a guest who looks around; hire an employee to let it. At most 12 guests are drawn at once.
- The passers-by are decoration: they cause no sale. While guests walk (a shift is running) 10 of the 14 keep walking (the others make room).
