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
| Felix Antes | 73306 |

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
(local only, not in Git) and is loaded again on the next start.

**Demo for the presentation** (spec `demo-scenarios`): press *Demo* on the campus (or open
`/?demo`), confirm, and four prepared days follow, about 45 seconds each: run the Cafe, guests
decide, weather and events, grow. The demo replaces your run; *Free play* at the end gives it back to
you as it is. It works locally and on the public URL; the browser only sends a scenario id.

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

## Working in the group

1. Pick a spec from the roadmap ([`docs/feature-roadmap.md`](docs/feature-roadmap.md), section 4.1, open specs) and open or find its GitHub Issue (template "Spec"). Assign yourself before you start.
2. Create a branch named after the spec, e.g. `day-context`, from an up-to-date `main`. Never commit a feature to `main` directly.
3. Write `specs/<name>.md` (What, Out of scope, Done when), then build only that.
4. Run `uv run pytest` before every push. Never edit, delete or skip anything in `tests/`; add new test files for your spec. If your spec changes data that an old test names on purpose, you may confirm that change yourself (rules in `AGENTS.md`).
5. Open a pull request into `main` with the PR template. It needs a passing `Tests` check (GitHub Actions runs `uv run pytest`) and an AI code review (for example `/code-review` in Claude Code) whose findings are fixed or answered in the PR. No human approval is required.
6. One spec per branch and per pull request. Keep it inside the spec's "Out of scope" fence.

Two tracks run in parallel, see the roadmap: **logic** (game rules in `logic.py`, `db.py`, `app.py`) and **visuals** (campus look and walking in `static/world/`, `static/map.css`). Every feature spec follows the three rules in section B3 of the roadmap (complete settable state, overridable day context, no randomness without the seed) so the demo mode can be built last without a rebuild.

## How it fits together

| Layer | Files | Job |
|---|---|---|
| Rules | `logic.py` | Pure functions: `new_state`, `buy`, `set_price`, `customers_for`, `customer_breakdown`, `price_preview`, `trade_day`, `stock_overview`, `overall_gain`, `unlock_shop`, `buy_upgrade`, `hire`, `upgrade_employee`, `fire_employee`. The shops and products are data tables (`SHOPS`, `CATALOGUE`); the customers come from two segments with price curves (`SEGMENTS`), a mix per shop (`SHOP_MIX`) and the day's factors (`FACTORS`), see `specs/pricing.md`. `demand` is the solo project's old rule, kept only because a test pins it. A refused action raises `RejectedAction`; every function returns a new state. Money is integer cents. |
| Guests | `guests.py` | The guests of a day (`day_plan`, `for_shop`): the crowd of `customers_today` as guests with a kind, a start place and a taste; those who look around choose among the shops with an employee by the walk, the queue and their taste. Pure functions, all randomness from the seed, nothing stored beside the queue. See `specs/guests.md`. |
| Demo | `scenarios.py` | The prepared days of the live demo as data (`SCENARIOS`) and their rules: `load_scenario`, `scenario_done`, `finish_demo`, `demo_view`. A scenario is a patch for `editor_set_state`, so the existing checks validate it. See `specs/demo-scenarios.md`. |
| Storage | `db.py` | SQLite, one run (day, cash, products, shops, player, history). An old save without shops still loads. `save` (never rewrites a stored day), `save_new_run` (replaces the run and its history in one transaction), `load`. |
| Storage (public server) | `pgstore.py` | With `CT_PUBLIC=1` and `DATABASE_URL`: each player's run as one JSON document in Postgres at Supabase (`campus_tycoon.runs`), passed through `db.through_sqlite` on the way in and out (the same CHECKs and repairs as a file), a copy in memory written through, 503 when the database cannot be reached. See `specs/persistent-runs.md`. |
| World data | `world.py` | The campus as data: the zone, the Nova building (parts, walls, entrance), desks, solid objects, room layouts. No rules and no drawing. |
| Server | `app.py` | Flask. `GET /api/state`, `/api/world`, `POST /api/buy`, `/api/price`, `/api/price_preview` (read-only: what a price would bring), `/api/open` (needs the current `day`), `/api/new-run` (needs `confirm: true`), `/api/player`, `/api/shop/unlock`, `/api/shop/upgrade`, `/api/staff/hire`, `/api/staff/upgrade`, `/api/staff/fire`, `/api/demo/load` (a scenario id and `confirm: true`), `/api/demo/finish`, and `/api/editor/*` (only with `CT_EDITOR=1`). Each request loads the run, applies one rule and saves only if it was accepted. `/map?embed=1` serves the campus page for the iframe. |
| Dashboard | `static/index.html`, `style.css`, `app.js` | KPIs, stock overview, product cards, open-the-stand forecast, charts, history. Layout uses container queries (`@container dash`) so it also fits the side panel. |
| View switch | `static/views.js` | One campus iframe that is never reloaded: full screen (the default), or over the "Campus live" window of the dashboard page (`#dashboard`). Dashboard as a slide-in panel over the campus. Syncs both views with `postMessage` (`action`, `mode`, `ready`, `open-dashboard`, `panel-open`, `panel-closed`). |
| Campus | `static/map.html`, `map.css`, `static/world/` | The 2.5D world from Felix Antes' Nova Beach Ventures, drawn on a canvas: walking with W A S D or by click, collision, finding a way, smooth camera, walking into the Nova (the roof fades out and the rooms show), light and sea. `main.js` runs the loop, `ui.js` shows the display and panels and talks to the API. Modes `preview` (small window, no display) and `main`. |
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
| `collapsible-stock-panel.md` | `collapsible-stock-panel` | The stock card on the campus page can be folded away, remembered per browser |
| `campus-map.md` | `campus-map` | 3D campus map with truck, queues, ticker (replaced by `world-core`) |
| `view-switch.md` | `view-switch` | Live window on the dashboard, map as main view, dashboard as side panel |
| `nova-campus.md` | `nova-campus` | Scene styled after Nova SBE Carcavelos (beach, tunnel, fort, pines) |
| `finite-prices.md` | `finite-prices` | Refuse non-finite prices without changing the saved run; regression checks in `checks/` |
| `campus-polish.md` | `campus-polish` | Coastal Tycoon visual polish: facade detail, landscaped plaza, warm light, sea and coordinated UI |
| `longer-run.md` | `longer-run` | 30-day season instead of five days (`LAST_DAY` in `logic.py`) |
| `world-api.md` | `world-api` | The campus as data in `world.py`, player position in the state |
| `world-core.md` | `world-core` | The 2.5D world replaces the three.js map; the campus opens first |
| `world-art.md` | `world-art` | Felix' figures for the player and the people in rooms, passers-by outdoors |
| `walk-in.md` | `walk-in` | One big Nova building: walk in, the roof fades out; replaces the room zones; the three desks inside |
| `nova-wings.md` | `nova-wings` | Merged (#50): more wings for the Nova: the Learning Center and the Mercado can be walked into, a Student Hub, one roof per wing |
| `nova-zones.md` | `nova-zones` | Merged (#53): the map around the Nova: a walkable Dorm with a bed panel, a detailed beach way and beach, the Surf Shop and the Beach Cafe outdoors |
| `shop-unlock.md` | `shop-unlock` | Four shops (Cafe, Beach Cafe, Merchandise, Surf Shop): a run starts with the Cafe and its coffee; more shops are unlocked and more products and employee places bought with money, each purchase is one level. Shops window on the campus page. Prices are placeholders. |
| `shop-art.md` | `shop-art` | The four campus shops show their unlock price or level on the map. Their furnishings change with the products bought. |
| `day-context.md` | `day-context` | The seed lives in the state; each day has a weather with a temperature drawn from it; a demo override can fix the weather. Weather and temperature are shown, the demand factors per shop are in `WEATHER` and take effect with `pricing` (#38). |
| `staff.md` | `staff` | Employees (first for the Cafe, later for every shop, see Known issues): hire on a bought place (refiller, seller), level them up, dismiss them. They run on the server every tick like the player's refill and sell, the shift starts by itself when the day opens, wages are paid at the end of the day (without money they stop working). They are named figures in the Cafe. Numbers are placeholders. |
| `editor-mode.md` | `editor-mode` | Dev tools, off unless the server starts with `CT_EDITOR=1` (and only for requests from this computer): set or add cash, fix the weather, skip several days, one validated state patch (day, shops and levels, stock, prices, seed, player), reset the run. Editor panel on the campus page. Base for `demo-scenarios`. Employees became settable with `editor-staff`; popularity is not built yet. |
| `shop-process.md` | `shop-process` | A day played live in the Cafe: *Open day* starts the day clock (300 ticks), *Shift* starts the one 90-tick shift of the day (carry stock from the storeroom to the counter, 20 units, and serve a queue), *Skip* lets the rest of the day pass with no sale. Whoever does not work earns nothing. The day closes into the history like `trade_day`, which stays for the day without a player (later: with staff) and is refused while a day is open. Shift panel on the campus page. Walking in the shop is not wired to it yet. |
| `outlook.md` | `outlook` | Before *Open day* only a forecast of the day's weather is shown (picture and temperature range); the real weather appears once the day is opened, next to the forecast for tomorrow. Wrong about 20 % of the time (a neighbouring weather), drawn from the seed with its own roll so the real weather stays the same; always right with the demo override. The day summary on the campus page is an evening report: the forecast for the next day and a tip per open shop (more, fewer or the usual customers, from the weather table; the tips take effect with `pricing`, #38). The real weather is hidden in the display only: the API still sends it (see the spec's note). |
| `pricing.md` | `pricing` | Customers from two segments (students, visitors) with price curves, a mix per shop and the day's factors (weather first, then the events of `events-and-disruptions`, then the popularity of `popularity`; trend and outfit plug in later); the screen shows the same number everywhere and explains it ("Why this number?", live price preview). Replaces the old one-line demand rule. |
| `events-and-disruptions.md` | `events-and-disruptions` | Campus events (exam period, party, career fair, a three-day surf festival) rolled from the seed with their own generator, first two days quiet, nothing saved; they move the customers of each shop through `FACTORS` and stack with the weather. The demo switch and the editor can fix an event; a fixed weather without an event means no event. Outages and strikes are not built (their own later spec). |
| `popularity.md` | `popularity` | Every shop has a popularity from 0 to 100 (50 at the start): each day with customers its customers give a report card (not served = 0, served = as happy as the price was fair) and popularity walks toward it, a fifth up and a third down. It moves the next days' customers by 85 to 115 % through `FACTORS` (after weather and event). Worked out only on the server from the day's result; the shop panel and the dashboard show the value, its word and why it moved. The editor can set it; old saves start at 50. |
| `day-cycle.md` | `day-cycle` | The day ends at the Dorm. When a day closes it gets dark and a hint offers *Go home*: the player walks to the bed by itself (a move key or a click stops it), or *Skip the walk* goes there at once, lies down, and the day summary with the evening report shows there. *Sleep* goes black, shows the night (Zzz, lamp off), then a sunrise to 09:00; the player stands up beside the bed and a good-morning card lists the forecast, stock and what to do. Ending a day early asks first when nobody works or the own shift still runs. The bed panel says *Open day* in the morning and *End the day* while a day runs. No new endpoint and no new rule; the evening is kept only in the browser. |
| `badges.md` | `badges` | 20 badges (first sale, good day, a team of three, profit streaks of 3, 7 and 14 days, every shop unlocked, season winner, ...), each a bronze, silver or gold medal (`BADGES` in `logic.py`). Given only by the server, the moment they are reached: state badges right after the action (e.g. the first sale), day badges (profit of the day, streaks, weather) when the day closes. On the campus a card at the top left shows a new badge and leaves by itself while the game keeps running; the evening report lists the day's medals, the end of the season and the dashboard show all of them. Badges give no reward; all thresholds are placeholders. |
| `smooth-frames.md` | `smooth-frames` | The campus runs at the screen's rate: no blur filter for the shadows, a slow frame advances the world by its real time. Browser check, not part of the tests. |
| `calm-panels.md` | `calm-panels` | The side panels of the campus stay calm while a day runs: redrawn only when their content changed (typed values and focus stay), shift requests wait for each other instead of being dropped, two outdated texts fixed. |
| `balance-pass.md` | `balance-pass` | The season is balanced: Surf Shop and Merchandise products cost and sell for less (a good season ends at about +5,000 EUR, not +25,000), a warning before a purchase that leaves nothing to buy, a hint for shops only employees can run, the storeroom limit counts the counter. A guard test plays whole seasons. |
| `editor-staff.md` | `editor-staff` | The editor patch can set the employees (shop, place, level, working), so the whole run is settable for the demo mode. A Staff block in the Editor panel. |
| `cleanup-dead-code.md` | `cleanup-dead-code` | Dead code out (the unreachable play-a-day path, unused functions), a price like `1e2` refused, a missing product in the history no longer stops the screen, old specs marked as dropped. |
| `deploy-ready.md` | `deploy-ready` | Security headers on every answer; a public mode (`CT_PUBLIC=1`): a run per player (cookie), a rate limit, no dev switches, no paths in errors; how to run it with a production server. Local play is unchanged. |
| `render-cache.md` | `render-cache` | The campus works out its tile list and the Nova's walls once and skips objects far outside the view (rules in `static/world/cull.js`); the picture is the same, checked pixel by pixel in the browser. Numbers are in the spec. |
| `guests.md` | `claude/website-kriterien-review-so0nrd` (PR #95) | Guests that choose a shop (small version): the day's crowd becomes guests with a kind, a start place and a taste. A third look around and go to another shop that has an employee when it is closer, its queue is shorter or they like it more (at most 30 % more guests per product, the crowd stays the same). On the map they walk from the Dorm, the plaza or the beach to the line of their shop and show their thought in a bubble (red: changed their mind); the Shift panel lists today's guests per shop. A shop that runs alone gets exactly the old queue. |
| `demo-scenarios.md` | `demo-scenarios` (PR #96) | The 3-minute live demo: four prepared days as data in `scenarios.py` (start state, fixed weather and event, text, goal), loaded by id into the player's own run (`POST /api/demo/load` with `confirm`, `POST /api/demo/finish`). A card on the campus shows the step, the text and the goal; the clock runs at two ticks a second while a scenario asks for it. Free play at the end. |
| `stale-tick.md` | `stale-tick` | No stray tick after the run is replaced: a demo scenario, the end of the demo and a new run (also one started on the dashboard, which the campus sends) are sent from the queue of the ticks (none overtakes them), and once they worked the ticks and clicks queued for the old run are dropped (`serial.js` epochs). No 400 and no console error in a scripted run of the four scenarios. Browser only. |
| [`map-layout.md`](specs/map-layout.md) | `map-layout` | Walking routes between the Dorm, Nova and beach shops. The world API supplies all four shop layouts and the central storage positions. |
| `shift-any-shop.md` | `shift-any-shop` (#101) | The player takes a shift in any unlocked shop, not only the Cafe: several shifts a day one after the other (90 of 300 ticks, one per shop), a finished or staffed shift moves aside and goes on, a staffed shop can be taken over. A shop outside the day's guest plan plans alone. The Shift panel lists where the player can start. |
| `weather-visuals.md` | `weather-visuals` (PR #105) | The world shows the weather of the opened day: a grey sky, more clouds and rain on a rainy day, a dark sky, heavy slanted rain, strong wind, high waves and rare soft lightning in a storm, a warm tint and a shimmer on a hot day; a sunny day and a day that is not open look as before. The looks are a table in `static/world/weather.js` (pure, tested with Node); the id comes from `state.weather`, which the server sends only once the day is open, so the world cannot show the real weather early. It does not rain indoors: the rooms of a wing whose roof has faded out stay dry. Nothing is random, lightning and motion are off with reduced motion. |
| `deploy.md` | `deploy` (#93) | The game on the internet: a free Render web service from `render.yaml` (built from `main` when the tests passed, one gunicorn worker, the secret generated by Render), gunicorn pinned in the `deploy` group of `uv.lock`, `GET /healthz` for the host's health check (no player, no cookie, no file). Runs on the public server are erased on restart for now; Supabase follows in `persistent-runs`. |
| `persistent-runs.md` | `persistent-runs` (#112) | Runs on the public server last: one JSON document per player in Postgres at Supabase (Frankfurt) when `DATABASE_URL` is set, through the SQLite rules in memory (`db.through_sqlite`), a write-through copy in memory (one process), a 503 with our sentence when the database is paused or unreachable, the table hidden from Supabase's Data API. Local play and all tests stay on SQLite; the Postgres checks run against a Postgres in CI. |

The tag `v1.0` is the dashboard-only version before the map.

## Group project roadmap

The first specs above are the solo-project history, the rest is the group project.
The plan, with what is built and what is open, is in
[`docs/feature-roadmap.md`](docs/feature-roadmap.md) (roadmap v6, state of 2026-11-10).
The open specs are listed in section 4.1 of the roadmap and in the GitHub Issues (label `spec`). The audit (`docs/audit-report.md`) lists
findings, measurements and feature ideas. The map is the 2.5D
world taken from a teammate's project (Nova Beach Ventures, code and art made with
AI, credit: https://github.com/felix-anthes-png/nova-beach-ventures). Progress is
tracked in the GitHub Issues (label `spec`).

## Known issues and ideas

- Staff: wages, hire and level prices and the speed per level are placeholders. With the customers of `pricing` (about 10 per product at the reference price, up to 20 and more at a low price or on a good day) a level 1 seller (one sale every 4 ticks, about 22 in a shift) can fall behind, so the levels now start to matter; the numbers are still placeholders. `trade_day` (day without a player) has no staff and no wages. Employees work in every shop (`STAFF_SHOPS`, logic only): the Cafe on the player's shift, the other shops in `shift["extra"]`. The player can take a shift in every unlocked shop (`shift-any-shop`). Only the Cafe has figures in the world so far (`WORK_SPOTS`).
- The shop prices, unlock prices and levels are placeholders to balance, and so are the price curves, the shop mix and the weather percents of `pricing` (#38).
- The opened day (300 ticks) is a placeholder length; a shift must fit into what is left of it, one shift per day.
- A played day (`shop-process`) is paced by the browser: it sends one tick request a second, and the server counts them. Two open pages double the speed, and a script can play a day in an instant. Only the player's own run is affected. Walking in the shop is not wired to the rules yet.
- Ideas not yet a spec: customers of the Merchandise shop wear the clothes when they leave, beach loungers to rent at the Beach Cafe, up to three printers on campus (refill paper and ink).
- The Nova has its first form: four wings joined by openings (the main block of 22 × 8 tiles with a glass-roofed atrium, gallery, Cafe, Merchandise and Print Corner; the Learning Center with a Study Hall and a Seminar; the Mercado Supply Hall; the Student Hub with a Lounge and a Meeting Room). Each wing has its own roof, and the whole floor inside can be walked on. The new wings are places only: nobody works there yet and no rule happens there (`shop-walk`, `staff`). The Dorm, the way to the beach, the Surf Shop and the Beach Cafe outside are `nova-zones`; its look is `nova-design`.
- Cafe, Merchandise and the three printers in the Nova are places only: no rule works there yet.
- A trading day (`trade_day`, the day without a player) only moves the light and then shows its result: guests walk only on an opened day.
- Guests (`guests`): the numbers that weigh the walk, the queue and the taste are placeholders. A guest decides once, when the day opens (the plan is stored in the shift as `guest_plan`); nobody changes their mind at the counter. A shop only the player runs (the Cafe without an employee) never receives a guest who looks around; hire an employee to let it. At most 12 guests are drawn at once.
- The passers-by are decoration: they cause no sale. While guests walk (a shift is running) 10 of the 14 keep walking (the others make room).
- To try changes without touching your own save, copy `app.py`, `logic.py`,
  `world.py`, `db.py` and `static/` to a temporary folder and start it there on another
  port (`python -c "import app; app.app.run(port=8770)"`): `db.py` keeps its
  database next to itself.
