# Campus Tycoon: Feature Roadmap (v4)

Status: roadmap v4, state of 2026-11-09 (after PR #80). It replaces v3. What the team decided
stays marked "decided". Part A is the plan and the current state. Part B keeps the game
design reference (core loop, weather and event factors, demo mode, glossary). Read
`AGENTS.md` first for the working rules. The three roadmap rules stay (see B3): complete
settable state, overridable day context, no randomness without the seed.

What changed since v3: the price logic (`pricing`), the day cycle at the Dorm, the straight map
view, badges and the audit fixes (frames, calm panels, hidden weather) are built and merged. The
open work is now walking through the shift, popularity, events, the
looks (`shop-art`, `nova-design`, `weather-visuals`, `map-layout`), guests, outfits, the demo and the
polish. The audit is in `docs/audit-report.md`. A day flow with a storage computer and a truck
is proposed in section 4.2 (`warehouse`).

# Part A: Plan and state

## 1. Where we are

### The game today

A 30-day season with a final settlement, start with 100 euro. The map is one continuous
2.5D world (walk with W A S D or by click): the Dorm, the beach way, the beach, and one big
Nova building with four wings that the player walks into (the roof of a wing fades out).
Four shops stand at fixed places: Cafe (open from the start, coffee), Beach Cafe, Merchandise
and Surf Shop, each with three products. A shop is unlocked with money, and more products and
two employee places are bought in its window; each purchase is one level.

A day runs like this: the player opens the day (a clock of 300 ticks), starts the one shift of
the day (90 ticks) in the Cafe, carries stock from the storeroom to the counter (20 units),
and serves a queue of customers. Skipping lets the rest of the day pass without a sale. Whoever
does not work earns nothing. Employees (refiller, seller; levels 1 to 3; wage per day) work on
the server in every shop. Before the day opens only a forecast of the weather is shown; the
real weather appears once the day is open. The evening report shows tomorrow's forecast
(wrong about 20 % of the time) and a tip per shop. Stock is still bought directly, on the dashboard and in the order panel on the campus page.
Customers come from two kinds (students, visitors) with price curves, a mix per shop and the
weather (`pricing`); the screen explains every number ("Why this number?"). Before the day opens
the numbers follow the forecast, not the real weather (`hidden-weather`). The day starts and ends
at the Dorm (`day-cycle`). The player earns badges (`badges`). All numbers are still placeholders.

### What is built (merged)

| Spec | PR | What |
|---|---|---|
| `longer-run` | #7 | 30-day season |
| `world-api`, `world-core`, `world-art` | #32, #33, #34 | The 2.5D world (Felix' project) replaces the three.js map: campus as data, walking and camera, figures |
| `shop-unlock` | #37 | Four shops, unlocking, levels, shops window |
| `shop-process` | #39 | A day played live in the Cafe: storeroom, counter, queue |
| `day-context` | #42 | Seed in the state, weather with temperature, override |
| `shop-skip` | #44 | Open the day, start the shift separately, skip without sales |
| `outlook` | #45, #59 | Forecast and evening report with tips |
| `walk-in`, `nova-wings` | #49, #50 | One big Nova building, four wings, roofs that fade |
| `clock-follows-day` | #52 | The shown time follows the server ticks |
| `nova-zones` | #53 | The map around the Nova: Dorm, beach way, beach, outdoor shops |
| `staff` | #54, #57, #58 | Employees: hire, level, dismiss, wages; they work in every shop |
| `editor-mode` | #56 | Dev tools behind `CT_EDITOR=1` (cash, weather, skip days, state patch, reset) |
| `pricing` | #62 | Two kinds of customers, price curves, a mix per shop, the weather as a factor, "Why this number?" |
| `collapsible-stock-panel` | #63 | The stock card on the campus can be folded away |
| `day-cycle` | #65 | The day starts and ends at the Dorm: go home, sleep, good-morning card |
| `map-view`, `click-walk` | #67, #69 | The world is seen straight from the front; click-walk keeps a margin at corners |
| `badges` | #79 | 20 badges with medals, awarded by the server |
| `smooth-frames` | #77 | No blur filter for shadows, a slow frame advances the world by its real time (6 to 12 frames per second before, about 50 after) |
| `hidden-weather` | #78 | Before the day opens no shown number depends on the real weather |
| `calm-panels` | #80 | The side panels redraw only when changed, requests wait for each other |
| `balance-pass` | #82 | Cheaper Surf Shop and Merchandise products (a good season ends at about +5,000 EUR, not +25,000), a dead-end warning, a hint for shops only employees can run, the storeroom limit counts the counter, a guard test that plays seasons |
| Audit | #72 | `docs/audit-report.md`: findings, measurements, balance simulation, feature ideas |
| Rules | #25, #47, #70 | AI review replaces the human review; the owner of a PR confirms test exceptions; model and effort hint |

Tests: everything in `tests/` and `checks/` passes in CI (`uv run pytest`).

### What we took from Felix

Done: collision and movement, the Nova room data format, zones and doors, the smooth camera,
the characters (six-frame walk, poses), and the 2.5D renderer. Credit is in the README.
Still to port, if needed: store silhouettes (`shop-art`), `environmentalProfile` and
`drawSkyMotion` (`weather-visuals`), the eight designed spaces (`nova-design`), guest groups
and destination scoring (`guests`), `createShowcaseRun` (`demo-scenarios`). Taken: `scenarioGoals` (the model of `badges`, built). Not taken: 25 district businesses, DJ events, maintenance and cleaning,
management overlays, guest needs, progression levels, showcase editor.

## 2. Decisions the team gave so far

| Topic | Decision |
|---|---|
| Our solo project | Only a starting point. Shops, rules and map are decided fresh by the group. |
| Map | Decided: Felix' 2.5D world. One continuous map, no room screens. One big Nova building that the player walks into, the roof fades out. The day starts and ends at the Dorm; the way to the beach leads to the Surf Shop and the Beach Cafe. Stylised after the real campus. The old three.js map is gone. |
| Backend | Our own Python + Flask + SQLite. The browser decides no rule. |
| Season | Decided: 30 days with a final settlement. |
| Shops | Decided: fixed places, unlocked with money; a shop starts with one product; each purchase in the shop window is one level. Cafe (coffee, cake, bagel), Beach Cafe (beer, coke zero, sandwich), Merchandise (hoodie, t-shirt, cap), Surf Shop (surfboard, wetsuit, surf lesson). The Cafe is open from the start. All prices are placeholders. |
| Build mode | Dropped: fixed places replace it. |
| Work in a shop | Decided: a day is played inside the shop: carry stock from the storeroom to the counter and sell. The counter holds 20 units, so there are two jobs; two employees can take them over. |
| One shift per day | Decided: a shift always lasts the same time, and only the shift earns money. Built (`shop-process`, `shop-skip`). |
| Day length | Built as placeholders: an opened day is 300 ticks (one tick a second), a shift 90 ticks. |
| Guests | Own feature, decided later. |
| Review | An AI reviews every pull request; merging needs the passing `Tests` check. |
| Test changes | The owner of a PR may confirm a test change for their own PR, only when the old test names data the spec changes on purpose (see `AGENTS.md`). |
| Security | Every spec follows section 3a and the per spec list in 3b. |
| AI use | Required by the course. Felix' code and art are AI made and may be used. Credit is in the README. |
| Demo mode | Built last, after the game is complete. The team then chooses which features appear. The editor mode is the base. |

## 3. Security

### 3a. Security: rules for every spec

Add these to every spec's "Done when" and to the AI review. Detailed list per spec in 3b.

1. The server decides every rule. The browser only shows and previews. Money, stock, unlocking, levelling up, hiring, ordering: always re-checked on the server.
2. Every endpoint takes JSON and validates all fields: type, whole numbers, finite, in range, ids from a fixed list (whitelist). Anything else is a `RejectedAction` and changes nothing.
3. Money stays integer cents. A rejected action changes no saved data. One lock per change (load, rule, save).
4. No unescaped data in `innerHTML`. Use `textContent` or `esc()`.
5. No secrets in the repo. Pin dependencies. Nothing from outside the app: no CDN, no web fonts.
6. Error answers contain only our own rule messages, never paths or stack traces.
7. Anything that sets the state directly (editor mode, demo mode) works only locally with an explicit config switch. Never on a public deployment.
8. If the app is deployed: HTTPS, a production server, a session per player, rate limit, security headers (CSP, X-Content-Type-Options, X-Frame-Options).
9. Tests for the security part of each spec: a crafted bad request is refused and the saved state stays identical.

Known weak spot (from the README): a played day is paced by the browser, one tick request a
second counted by the server, so a script can play a day in an instant. Only the player's own
run is affected. Revisit it before any deployment.

### 3b. Security: what to watch per spec

| Spec | Watch out for |
|---|---|
| `shop-unlock`, `shop-process`, `shop-skip` | Built. The server checks cash, shop id and level, storeroom, counter space and queue. Locked shops and a sale after the day ended are refused. Keep the tests for the locked case. |
| `staff` | Built. Wages in integer cents, cash never negative, hiring limit from the level, ids validated. Employees run on the server. |
| `editor-mode` | Built. Active only with `CT_EDITOR=1` and only for requests from this computer. One validated state patch. Must stay off on a public deployment. |
| `pricing` | Prices come from the server. Weather and event factors are integers. A crafted price or demand never changes more than the rule allows. |
| `shop-walk` | Every refill and sale is a request the server checks. No rule depends on the position the browser sends. |
| `day-cycle` | The end of the day is a plain request; the position is never trusted. |
| `warehouse` | Order quantity and total price checked on the server (whole numbers, product id from the list, space in the storage, cash). The delivery time counts server ticks, never the browser clock. Carrying checks the stock that really lies in the storage. A crafted request cannot deliver early or twice. |
| `shop-art`, `nova-design` | Assets only, drawn in code. Labels through `textContent`. |
| `popularity` | Integer, clamped to 0 to 100, computed only on the server. |
| `outlook` | Built. The forecast is made on the server. Known: the API still sends the real weather, only the display hides it. Never expose the seed. |
| `events-and-disruptions` | Events come from the seed. The browser cannot choose one, only the editor override can. |
| `weather-visuals` | The browser only reads the weather it may show. No `eval`, no external scripts. |
| `badges` | Awarded only by the server, after an accepted action or at the end of a day (`specs/badges.md`). No endpoint lets the browser grant a badge. |
| `outfits` | Refuse without enough money and change nothing. Validate the outfit id. |
| `guests` | Number of guests is capped. Guest data comes only from the server. |
| `demo-scenarios` | Loading a scenario needs the demo switch and works only on localhost. Validate the whole state shape. Never public. |
| `final-polish` | Last pass: headers, CSP, dependency versions, no leftover debug code, run `/security-review`. |

## 4. Specs

Track: V = visuals, L = logic. Effort: S small, M medium, L large. Every line is one spec,
one branch, one issue, one pull request.

### 4.1 Open specs (in a sensible order)

| Spec | Issue | Track | Effort | Depends on | What |
|---|---|---|---|---|---|
| `shop-walk` | #40 | L and V | L | shop-process, nova-zones (both done), shop-art | The shift is played by walking: storeroom spot, carry, counter, serve. Each step stays a server request; no rule reads the position. Replaces the Play day panel. Can start with the Cafe. Today only the Cafe can be played, `SHIFT_SHOPS = ("cafe",)`; the other shops run on staff only. |
| `staff` follow-up | #20 | L | S | shop-process | Issue still open: keep trying staff in play. Known: numbers are placeholders, with the current demand a level 1 seller already serves everyone (fixed by `pricing`), `trade_day` has no staff, only the Cafe has employee figures (`WORK_SPOTS`). Proposal, not decided: close it when `pricing` and the figures for the other shops are in. |
| `shop-art` | #18 | V | M | shop-unlock (done) | Looks of the shops on the map: locked and open, visible levels. Reference: Felix' store silhouettes. |
| `nova-design` | #11 | V | L | nova-zones (done) | Look of the Nova (inside and outside) and the beach in Felix' style. |
| `popularity` | #13 | L | M | pricing, balance-pass (both done) | Per shop, 0 to 100 as an integer, computed only on the server from real sales. Felix' `momentum` is the model. |
| `events-and-disruptions` | #14 | L | M | day-context | Campus events (exam period, party, career fair), trends, outages, strikes as entries in the day context. Felix' 7 day types are the event table. |
| `weather-visuals` | #16 | V | M | day-context | Rain, storm, heat and sky in the 2.5D renderer, over the whole scene, also over the roofless Nova. Builds on `environment.js`. The weather is hidden before the day opens (`outlook`): draw only what the display may show. |
| `map-layout` | #71 | V and L | M | map-view (done) | A new arrangement of the map (data in `world.py`, drawing in `static/world/`). See the issue. |
| `outfits` | #21 | L | S | shop-unlock (done) | Optional. The look is an option of `drawPersonFigure`. |
| `guests` | #22 | L and V | L | pricing, shop-walk | Visible guests that choose a shop and walk there; replaces `ai-customers` and `walkways`. Open: sales per day on the server, or live guests. Decided later. |
| `demo-scenarios` | #23 | L | M | the features chosen for the demo, editor-mode (done) | Built last. `scenarios.py`, loader, explanation overlay, free mode at the end. |
| `final-polish` | #24 | V | M | demo-scenarios | Last. Animations, camera, details, last security pass (`/security-review`). |

### 4.2 New from the notes of 2026-11-09 (proposal, no issue yet)

The team's notes describe a fuller day. Part of it is built, the rest is two new specs.

| Note | Status |
|---|---|
| Try staff further | See `staff` follow-up above. |
| End the day and start it at a fixed place | Built: `day-cycle` (#65). |
| A storage computer to order goods; they arrive by truck | New: `warehouse` (proposal, no issue yet). |
| From there the storerooms of the shops are supplied | New: `warehouse` (carrying from the central storage to each shop). |
| Then the workday starts; always the same length (one shift); only then money is earned | Built: `SHIFT_TICKS`, "whoever does not work earns nothing". |
| After work, walk around and do things | The rest of the opened day is free time. What there is to do is open (section 7, question 4). |

| Spec | Track | Effort | Depends on | What | Out of scope |
|---|---|---|---|---|---|
| `day-cycle` | L and V | M | built (#65): outlook, nova-zones | The day starts at the Dorm and ends there: "End the day" at the Dorm opens the day-end screen (the evening report), the next day begins at the Dorm. The dashboard button stays a second way. The position decides no rule: the server takes the end of the day as a plain request. | Ordering, trucks, shop work |
| `warehouse` | L and V | L | shop-process (done), day-cycle | A central storage with a computer: the player orders stock there (server checks money and space), a truck brings it at a fixed time, the goods land in the central storage, and the player carries them to the storeroom of each shop. Replaces buying stock directly on the dashboard. Order, delivery and carrying are all server requests; the walk only decides when. | Pricing, guests, shop art, delivery events |

Effects to agree before building `warehouse`: `buy` and the stock model change (today one `stock`
dict, bought straight into the storerooms), so tests that call `buy` need changes; the editor
mode patches stock; `trade_day` (day without a player) must keep working. Name each test
change in the spec. The old truck of the three.js map is only a reference for the look.

### 4.3 Cleanup (small)

- `specs/employees.md`, `investments.md`, `multi-business.md` and `net-worth.md` come from the
  first draft (PR #1) and belong to the dropped plan; delete or mark them as replaced.
- The cleanup of the audit (dead code, this roadmap and the README, old specs, price text, product name fallback) is proposed as one spec: `cleanup-dead-code` (`docs/audit-report.md`, section 4). The two items above belong to it.
- `shop-skip` (#43) and `clock-follows-day` (#51) have no spec file of their own. The day clock, the shift and Skip are described in `specs/shop-process.md`; the clock display is not described in any spec. Either write a short spec for each or say in `specs/shop-process.md` where they went.

## 5. Issue status (2026-11-09, after PR #80)

| Issue | State |
|---|---|
| Closed, built | #2 `longer-run`, #9 `world-core`, #10 `day-context`, #12 `outlook`, #17 `shop-unlock`, #26 `world-art`, #27 `world-api`, #28 `nova-zones`, #36 `shop-process`, #43 `shop-skip`, #46 `walk-in`, #48 `nova-wings`, #51 `clock-follows-day`, #55 `editor-mode`, #38 `pricing`, #61 `collapsible-stock-panel`, #64 `day-cycle`, #66 `map-view`, #68 `click-walk`, #15 `badges`, #73 `smooth-frames`, #74 `calm-panels`, #75 `hidden-weather`, #76 `balance-pass` |
| Closed, dropped | #3 to #6 (first plan), #19 `walkways` (zones and collision replace it), #29 `build-rules`, #30 `build-mode-ui` |
| Open | #11 `nova-design`, #13 `popularity`, #14 `events-and-disruptions`, #16 `weather-visuals`, #18 `shop-art`, #20 `staff` (follow-up), #21 `outfits`, #22 `guests`, #23 `demo-scenarios`, #24 `final-polish`, #40 `shop-walk`, #71 `map-layout` |
| To open | `warehouse`, and the specs proposed in `docs/audit-report.md` section 4 that have no issue yet (`retire-trade-endpoint`, `render-cache`, `lean-responses`, `editor-staff`, `cleanup-dead-code`, `deploy-ready`) |

## 6. Suggested next steps (proposal)

1. `balance-pass` (#76) is built (#82). The decisions behind it (David, owner of the spec, session of 2026-11-09, written in `specs/balance-pass.md`): warn before a purchase that leaves nothing to buy (no refusal), no loan yet (a loan is the feature `F8` of the audit), the day length is solved by the demo and a speed step, not by the numbers.
2. In parallel, small and independent: `events-and-disruptions` (#14), `shop-art` (#18) or `nova-design` (#11), `weather-visuals` (#16), `map-layout` (#71).
3. Then `popularity` (#13, after the balance) and `shop-walk` (#40, after `shop-art` has the shop places drawn).
4. Agree on `warehouse` (section 4.2) and the follow-up specs of the audit (`docs/audit-report.md`, section 4).
5. `guests` (#22) only when the team decides; then `demo-scenarios` and `final-polish`.

Who works on a spec is set by the assignee of its GitHub Issue (label `spec`); a spec without an assignee is free. Each spec gets its `specs/<name>.md` in its own PR.

## 7. Open decisions

1. Forecast error rate (now 20 %) and the weather and event factors per shop: placeholders, to balance with `pricing`.
2. Day length: an opened day is 300 ticks, a shift 90. Decided by David in the session of 2026-11-09 (to be confirmed by the team): the numbers stay; the demo mode (`demo-scenarios`) skips days for the presentation, and a speed step for the tick (several ticks per request, a feature of its own) is the comfort for normal play.
3. Does `trade_day` (a day without a player) stay as it is, with no staff and no wages, or get staff too?
4. What is there to do in the free time after the shift (`day-cycle`)? For example unlocking and levelling shops at their windows, hiring, walking to the Print Corner, rest at the Dorm.
5. `warehouse`: one central storage for all shops or a storage per shop? How long does a truck take, and can a delivery fail (strike, shortage)? What does the storage hold at most?
6. Who plays the Beach Cafe, Merchandise and Surf Shop shifts: only staff, or also the player (`SHIFT_SHOPS` has only the Cafe)?
7. Nova design: use photos of the real Nova SBE Carcavelos campus as reference?
8. Guests: sales computed per day on the server, or live guests on the map?
9. Ideas from the team, not yet a spec: Merchandise customers wear the clothes when they leave, beach loungers to rent at the Beach Cafe, up to three printers on the campus where paper and ink have to be refilled.
10. Licence and credit for Felix' project: confirm and keep the README credit.

---

# Part B: Game design reference

## B1. How a game day works (the core loop)

Built today, in this order:

1. The seed gives the day context: weather with a temperature. Before the day opens only a forecast is shown.
2. The player buys stock directly into the storeroom of a shop, on the dashboard or in the order panel of the campus page (planned: ordering and a truck, `warehouse`).
3. The player opens the day (300 ticks). The real weather appears.
4. The player starts the shift (90 ticks) in the Cafe: carry stock from the storeroom to the counter (20 units), serve the queue. Employees do the same on the server in every shop. Whoever does not work earns nothing; Skip lets the rest of the day pass without a sale.
5. The day closes into the history: revenue, cost of goods, wages.
6. The evening report shows the forecast for tomorrow and a tip per shop.
7. The player decides: stock, prices, unlocking, levels, staff. The next day starts.

Planned on top: demand from price, weather, events and popularity (`pricing`, `popularity`,
`events-and-disruptions`): DEMAND = base from price x weather x event x trend x popularity
x outfit bonus. Popularity rises with fair prices and full shelves and falls with empty
shelves and too high prices; it affects the next day. The day starts and ends at the Dorm
(`day-cycle`, built).

Everything is per shop: each shop has its own demand, stock, counter and staff.

## B2. Weather and events against shops

Weather factors are in `logic.py` (`WEATHER[..]["demand_percent"]`), 100 means normal demand.
They are placeholders to balance. Today they drive the tips of the evening report; customers
follow them once `pricing` is built.

| Weather | Cafe | Surf Shop | Merchandise | Beach Cafe |
|---|---|---|---|---|
| Sunny | 80 | 130 | 100 | 150 |
| Rainy | 140 | 50 | 120 | 40 |
| Hot | 60 | 120 | 80 | 180 |
| Stormy | 100 | 20 | 100 | 20 |

Event factors are not built yet (`events-and-disruptions`). Starting proposal, 1.0 is normal:

| Event | Cafe | Surf Shop | Merchandise | Beach Cafe |
|---|---|---|---|---|
| No event | 1.0 | 1.0 | 1.0 | 1.0 |
| Exam period | 1.5 | 0.6 | 0.9 | 0.7 |
| Party | 0.8 | 1.0 | 1.1 | 1.5 |
| Career fair | 1.3 | 0.7 | 1.4 | 0.9 |

The factors are multiplied. Example: hot weather on a party day gives the Beach Cafe
1.8 x 1.5 = 2.7, so the player should order much more beer and coke zero. A tip says more
customers at or above 115, fewer at or below 85 (`OUTLOOK_MORE_AT`, `OUTLOOK_LESS_AT`).

## B3. Rules for every feature spec

So that the demo mode needs no rebuild later, every feature spec follows these three rules
from the start:

1. The whole game state is complete and can be set directly: day, cash, shops, stock, popularity, staff, player position all live in the state.
2. The day context can be overridden. `make_day_context(seed, day, override)` takes an optional argument that fixes weather or event.
3. No randomness without the seed. Every random choice comes from the seed stored in the state, also anything drawn on screen (no `Math.random` in `static/world/`).

## B4. Demo mode (presentation)

Built like a tutorial, about 5 minutes, and built last, once the game is complete. Days are
skipped: each scenario loads a prepared start state and shows an explanation text. After
the goal of a scenario is reached, the next scenario loads. At the end the player can keep
playing freely. The editor mode (`editor-mode`) already sets cash, weather, day, shops and
stock; the demo adds scenarios on top.

Scenario data (pure data in a new `scenarios.py`): start state, fixed weather or event for
these days, explanation text, goal condition. Functions: `load_scenario(id)` and
`scenario_done(state, id)`.

Example sequence (a suggestion, the team chooses after the game is complete):

1. Basics: day 1 at the Dorm, 100 euro. Order stock, play a shift in the Cafe.
2. Weather and outlook: the evening report predicts heat. The player stocks beer and coke zero for the Beach Cafe and sees the effect.
3. Second shop: more money, the Surf Shop is unlocked. Then a storm: the Surf Shop collapses, the Cafe profits.
4. Staff and popularity: hire a seller. At a party, staff pays off; empty shelves lower popularity.
5. Disruption and finish: power cut or strike, then badges and the final settlement.

## B5. Glossary

| Term | Meaning |
|---|---|
| Day context | The result of one day's rolled external influences: weather, later events, trends, disruptions. |
| Outlook | The forecast and the evening report with tips for the next day. |
| Open day | The day clock (300 ticks) that starts when the player opens the day. |
| Shift | The one work period of a day (90 ticks) in a shop. Only it earns money. |
| Tick | One server step of the day clock, about a second. |
| Storeroom, counter | The shop's stock (100 units) and the part carried to the counter (20 units). |
| Popularity | Per shop, 0 to 100. Scales customer numbers on the next day. Planned. |
| Seed | A number stored in the state from which all randomness is derived, so runs are reproducible and testable. |
| Editor mode | Dev tools behind `CT_EDITOR=1`, local only. |
| Scenario | A prepared start state with explanation text and a goal, used by the demo mode. |
| Track | Either logic (game rules) or visuals (looks, walking). |
