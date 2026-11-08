# Campus Tycoon: Feature Roadmap (v2)

Status: roadmap v2, agreed by the team on 2026-11-05 where it says "decided". It replaces roadmap v1.
Part A is the plan. Part B keeps the game design reference of v1 (core loop, weather and event
factors, demo mode, glossary) that is still valid. Read `AGENTS.md` first for the working rules.
Rules that stay: `AGENTS.md` and the three roadmap rules (complete settable state,
overridable day context, no randomness without the seed).

# Part A: Plan

## 1. Decisions the team gave so far

| Topic | Decision |
|---|---|
| Our solo project | Only a starting point. Shops, rules and map are decided fresh by the group. |
| What we take from Felix | Character control, the people (look and animation), the design, the smooth camera. |
| Map | Decided: Felix' 2.5D world instead of the three.js map. Changed 2026-11-08 (Felix, after David's memo): one continuous map, no room screens. One big Nova building that the player walks into; the whole roof fades out so the rooms and the weather can be seen. The day starts and ends at the Dorm; the way to the beach leads to the Surf Shop and the Beach Cafe outside. The Nova is stylised after the real campus. |
| Backend | Rules are rewritten in our own backend (Python + Flask + SQLite). Felix' `core.js` is only a reference. The browser decides no rule. |
| Season | Decided: 30 days with a final settlement (PR #7 `longer-run`). |
| Shops | Decided: shops stand at fixed places on the map. A place is unlocked with money. A shop starts with one product. Levelling up a shop makes room for another employee or adds a product. Decided on 2026-11-05: Cafe (coffee, cake, bagel), Surf Shop (surfboard, wetsuit, surf lesson), Merchandise (hoodie, t-shirt, cap), Beach Cafe (beer, coke zero, sandwich). The Cafe is open from the start. Prices and steps are placeholders in `shop-unlock`. |
| Build mode | Dropped for now: fixed shop places replace it. Issues #29 and #30 are closed. |
| Work in a shop | Decided: a day is played inside the shop. The player starts alone, carries stock from the storeroom to the counter and sells there. The counter has limited space, so there are two jobs. Two employees can take them over: one refills, one sells. This can differ per shop. |
| Guests | Own feature, decided later. |
| Review | An AI reviews every pull request. Merging needs the passing `Tests` check (rule change is PR #25). |
| Security | Every spec follows the rules in section 3a and the per spec list in 3b. |
| AI use | Required by the course. Felix' code and art are AI made and may be used. Credit it in the README. |

## 2. What we reuse from Felix (read as reference, port or vendor)

| Part | Felix file | Size | How we use it |
|---|---|---|---|
| Collision and movement | `dist/world-physics.js` | 2 KB | Vendor as is (pure functions: `resolveMovement`, `nearestFreePoint`). |
| Interior data | `dist/interior-layouts.js` | 5 KB | Use as the data format for the Nova rooms (zones, colliders, routes, activity points). |
| Zones and doors | `ZONES`, `changeZone`, door hotspots in `dist/app.js` | small | Rewrite cleanly as data. Doors switch zone and spawn point. |
| Camera | `camera` object, smooth follow and zoom in `app.js` | small | Keep the smooth follow. Indoors the whole room fits on screen. |
| Characters | `drawPersonFigure`, `characterView`, pose functions | medium | Done in `world-art`: six-frame walk, facing from movement, activity poses. Drawn in code; Felix' image files in `dist/assets` are not used by his game either. |
| Shop data | `STORES`, `STORE_UNLOCKS`, tier-gated products in `core.js` | small | Reference for `shop-unlock`: Felix also opens shops at fixed places with money. Port only what fits our levels. |
| Weather and calendar data | `districtWeather` (4 states), `CAMPUS_CALENDAR` (7 day types) | tiny | Use as data for `day-context` and `events-and-disruptions`. |

Not taken (too much for us): 25 district businesses, DJ events, maintenance and
cleaning, management overlays, guest needs, scheduled deliveries, progression
levels, showcase editor.

Observed when running it (Nov 2026): all 146 Node tests pass, the world loads without
console errors, walking, build placement (cash 100.00 to 99.00) and interior exit work.
16 of its 28 test files read source files, so write behaviour tests for everything we port.

The baseline (`longer-run`, `world-api`, `world-core`, `world-art`) already took the world, the
characters and the camera. Still to come from this table: shop data, weather and calendar data.

## 3. New spec list

Issues: `world-core` #9, `world-art` #26, `world-api` #27, `day-context` #10, `badges` #15, `nova-zones` #28, `nova-design` #11, `shop-unlock` #17, `shop-process` #36, `shop-walk` #40, `shop-art` #18, `outlook` #12, `popularity` #13, `events-and-disruptions` #14, `weather-visuals` #16, `staff` #20, `outfits` #21, `guests` #22, `demo-scenarios` #23, `final-polish` #24. Old #19 `walkways`, #29 `build-rules` and #30 `build-mode-ui` are closed. Season: #2 `longer-run`. New on 2026-11-08, issues still to be opened: `walk-in` and `day-cycle`; the text of `nova-zones` (#28) has to be replaced by the new one below.

Every line is one spec, one branch, one issue, one pull request. Track: V = visuals,
L = logic. Effort: S small, M medium, L large.

### Phase 1: foundation (parallel)

| Spec | Track | Effort | Depends on | What | Out of scope |
|---|---|---|---|---|---|
| `world-core` | V | L | none | DONE (baseline). Felix' world layer in `static/world/`: isometric projection, zone switching with doors, smooth camera, WASD and click-to-move, collision, finding a way. His outdoor campus and three rooms. Replaces #9 `split-map`. | Economy, build mode, guests, Nova design |
| `world-art` | V | M | world-core | DONE (baseline). Felix' character for the player and for the people in the rooms, drawn in code: six-frame walk, facing, poses. Passers-by outdoors as decoration. | Guest behaviour, outfits |
| `world-api` | L | S | none | DONE (baseline). `world.py`: zone layouts as data (size, colliders, doors, spawn), player position saved in the state, endpoints to read and save it. | Rules for money or building |
| `day-context` | L | M | none | Issue #10 unchanged: seed in the state, `make_day_context(seed, day)`, weather, demand factor, override. Use Felix' weather and calendar data as the starting table. | Events, forecast, popularity |
| `badges` | L | S | none | Issue #15 unchanged. Good first task. | Any effect on play |

### Phase 2: the Nova map

| Spec | Track | Effort | Depends on | What | Out of scope |
|---|---|---|---|---|---|
| `walk-in` | V and L | L | world-core, world-api, world-art | Added 2026-11-08. One big Nova building on the campus map: the player walks in through an entrance, the whole roof fades out, the rooms show, and sky and weather stay visible. Replaces the three room zones; their three desks move into the atrium. Cafe, Merchandise and a Print Corner with three printers as places (no rule). The Nova is stylised after the real campus. Needs an exception for eight tests of `world-api` (see its spec). | Dorm, beach way, outdoor shops, day cycle, weather effects, final art |
| `nova-zones` | V | M | walk-in | Rewritten 2026-11-08. The outdoor map around the Nova: the Dorm, the way to the beach, the Surf Shop and the Beach Cafe outside, the beach. Smaller map size. Decides what becomes of the old outdoor buildings. | Final art, shop rules, weather |
| `nova-design` | V | L | nova-zones | Look of the Nova (inside and outside) and the beach: tiles, walls, colours, details. Replaces #11 `campus-look`. | Rules, new mechanics |

### Phase 3: shops

| Spec | Track | Effort | Depends on | What | Out of scope |
|---|---|---|---|---|---|
| `shop-unlock` | L | M | none | The list of shops as data (the team's four shops): offer, prices, fixed place, unlock price, levels, storeroom and counter space. Unlocking with money, levels (room for an employee or another product), every shop starts with one product. State gets `shops: {id: {...}}`. Replaces #17 `multi-shop`. The list can be written by the team without code first. | How a day runs in a shop, staff, guests, shop art |
| `shop-process` | L and V | L | shop-unlock | A day played live in one shop: storeroom to counter, limited counter space, selling at the counter, a simple queue of customers from the existing price demand. One person alone: touches state, API and screen. | Employees, customers with own choices, several shops at once, popularity |
| `pricing` (#38) | L | M | day-context, shop-process | New price logic instead of the solo project's fixed demand steps: price, weather, events to customers. Replaces only `customers_for` from `shop-process`. Added 2026-11-06. | Shop day, popularity, guests |
| `shop-walk` (#40) | L and V | L | shop-process, nova-zones, shop-art | The shift is played by walking: storeroom spot, carry, counter, serve. Each step is still a server request; no rule reads the position. Replaces the Play day panel. Added 2026-11-06. | Employees, guests, several shops at once, popularity, new price logic |
| `shop-art` | V | M | shop-unlock | Look of the shops on the map: locked and open, visible levels. Replaces #18 `shop-buildings`. | Rules |

### Phase 4: depth (parallel, after the shops)

| Spec | Track | Effort | Depends on | Note |
|---|---|---|---|---|
| `outlook` (#12) | L | M | day-context | Unchanged. Forecast wrong about 20 % of the time, from the seed. |
| `popularity` (#13) | L | M | day-context, shop-process | Per shop, 0 to 100 as an integer. Depends on real sales. Felix' `momentum` is the model. |
| `events-and-disruptions` (#14) | L | M | day-context | Unchanged. Felix' 7 day types as the event table. |
| `weather-visuals` (#16) | V | M | day-context, world-core | Rewritten for the 2.5D renderer: rain, storm, heat, sky. Builds on `environmentalProfile` and `drawSkyMotion` in `static/world/environment.js`. Drawn over the whole scene, also over the roofless Nova interior (`walk-in`). |
| `day-cycle` | L and V | M | outlook, nova-zones | Added 2026-11-08. The day starts at the Dorm and ends there: "End the day" at the Dorm opens the day-end screen (the `outlook` evening report), the next day begins at the Dorm. The dashboard button stays a second way. The position decides no rule: the server still takes the end of the day as a plain request. |
| `staff` (#20) | L | M | shop-process | Employees do the same actions as the player: one refills, one sells. Wage in cents. Jobs and places are data per shop, the level limits the number. |
| `outfits` (#21) | L | S | shop-unlock | Optional. The look is an option of `drawPersonFigure`. |

### Phase 5 and last

| Spec | Track | Note |
|---|---|---|
| `guests` | L and V | Replaces #22 `ai-customers` and #19 `walkways`. Decided later. Felix' guest groups, needs and destination scoring are the reference. Open question: sales per day on the server, or live guests. |
| `demo-scenarios` (#23) | L | Unchanged, built last. |
| `final-polish` (#24) | V | Unchanged, last. |

## 3a. Security: rules for every spec

Add these to every spec's "Done when" and to the AI review. Detailed list per spec in 3b.

1. The server decides every rule. The browser only shows and previews. Money, stock, unlocking, levelling up, hiring: always re-checked on the server.
2. Every endpoint takes JSON and validates all fields: type, whole numbers, finite, in range, ids from a fixed list (whitelist). Anything else is a `RejectedAction` and changes nothing.
3. Money stays integer cents. A rejected action changes no saved data. One lock per change (load, rule, save).
4. No unescaped data in `innerHTML`. Use `textContent` or `esc()`.
5. No secrets in the repo. Pin dependencies. No scripts from a CDN: vendor them into `static/`.
6. Error answers contain only our own rule messages, never paths or stack traces.
7. Anything that sets the state directly (demo mode) works only locally or with an explicit config switch. Never on a public deployment.
8. If the app is deployed: HTTPS, a production server, a session per player, rate limit, security headers (CSP, X-Content-Type-Options, X-Frame-Options).
9. Tests for the security part of each spec: a crafted bad request is refused and the saved state stays identical.

## 3b. Security: what to watch per spec

| Spec | Watch out for |
|---|---|
| `world-core` | Vendored Felix code: check for `eval`, `innerHTML` with data, external URLs. The browser keeps no rule and no truth in `localStorage`. Movement and camera are cosmetic only. |
| `world-art` | Only drawn in code: no external URLs, no user uploads. Passers-by never talk to the server. |
| `world-api` | Zone id from a whitelist. Check the position on the server (finite, inside the zone bounds). No rule may depend on the position the browser sends. |
| `day-context` | The seed lives on the server and is never sent to the browser (it would let players predict the weather). The override works only locally or by config switch. |
| `badges` | Awarded only by the server after a day. No endpoint lets the browser grant a badge. |
| `nova-zones` | A zone change that affects the state is validated on the server (known door, allowed target). |
| `nova-design` | Assets only. Names and labels shown through `textContent`. |
| `shop-unlock` | Server checks cash, shop id and level. A shop that is locked, or a product or staff place not yet reached, cannot be used by a crafted request. Prices come from the server only. Test the locked case. |
| `shop-process` | Every refill and sale is a request the server checks against storeroom, counter space and queue. No rule depends on the position the browser sends. A crafted request cannot sell more than the counter holds or sell after the day ended. |
| `shop-art` | Assets only. |
| `outlook` | The forecast is created on the server. Never expose the seed or the true result of tomorrow. |
| `popularity` | Integer, clamped to 0 to 100, computed only on the server. |
| `events-and-disruptions` | Events come from the seed. The browser cannot choose an event, only the demo override can. |
| `weather-visuals` | The browser only reads today's weather. No `eval`, no external scripts. |
| `staff` | Wages in integer cents, cash never negative, hiring limit from the shop's level, employee and job ids validated. Employees run on the server, the browser only shows them. |
| `outfits` | Refuse without enough money and change nothing. Validate the outfit id. |
| `guests` | Number of guests is capped (performance, no flooding). Guest data comes only from the server. |
| `demo-scenarios` | Setting a state or loading a scenario needs a demo switch and works only on localhost. Validate the whole state shape when setting it. Never public. |
| `final-polish` | Last security pass: headers, CSP, dependency versions, no leftover debug code, run `/security-review`. |

## 4. What happens to the existing issues

| Issue | Action |
|---|---|
| #2 `longer-run` | Keep. PR #7 still waiting for a merge. |
| #9 `split-map` | Rewrite as `world-core`. |
| #10 `day-context`, #12 `outlook`, #14 `events-and-disruptions`, #15 `badges`, #20 `staff`, #21 `outfits`, #23 `demo-scenarios`, #24 `final-polish` | Keep. Update "Depends on" and add Felix references. |
| #11 `campus-look` | Rewrite as `nova-design`. |
| #13 `popularity` | Keep. Depends on `shop-unlock` once shops exist. |
| #16 `weather-visuals` | Rewrite for the 2.5D renderer. |
| #17 `multi-shop` | Rewritten as `shop-unlock`. |
| #18 `shop-buildings` | Rewrite as `shop-art`. |
| #19 `walkways` | Close. Zones and collision replace it. Waypoint routes come back inside `guests`. |
| #22 `ai-customers` | Postpone, merge into `guests`. |
| #29 `build-rules`, #30 `build-mode-ui` | Closed: fixed shop places replace the build mode. |
| New | `world-art`, `world-api`, `nova-zones`, `shop-process` (#36) |

## 5. Suggested start (proposal)

| Person | First spec | Why |
|---|---|---|
| Felix | `walk-in`, then `nova-zones`, then `shop-art` | He knows the world code. `world-core` and `world-art` were brought in from his project for the baseline, with credit, so this is where his own commits start. |
| David | `shop-unlock` | Python rules and API, close to the current `logic.py` and `app.py`. |
| Christopher | `day-context` | Independent of the map. |
| Gregor | `badges` | Independent and small. |

Branch names are the spec names. Each spec gets its `specs/<name>.md` in its own PR.

## 6. Open decisions

1. Old three.js map files: removed inside `world-core` or in a clearly named follow-up.
2. (Decided in `shop-unlock`) Level-up: the player chooses. Each purchase in the shop window (a product or an employee place) raises the level by 1; employee places are bought in order.
3. (Decided 2026-11-05) Shops: Cafe, Surf Shop, Merchandise, Beach Cafe with three products each (see section 1). The Cafe is open from the start with the coffee. Prices, unlock prices and level steps are placeholders in `logic.py`, to balance later. Starting with the coffee only means the old tests that bought the sandwich, coffee or cookie at the start were changed (exception confirmed by David), as with PR #7.
3a. Who buys at the counter? Proposal: a simple queue, its size from price demand and the seed.
3b. How long is a day? Proposal: 1 to 2 minutes with a key to skip. 30 days at 2 minutes is one hour of play.
3c. What happens in a shop where nobody stands? Proposal: without staff it stays closed.
3d. What happens to `trade_day`? Existing tests check it. Proposal: it stays as a day without a player and for skipping.
4. (Decided) Season is 30 days.
5. Forecast error rate (about 20 %) and the weather and event factors per shop.
6. Nova design: use photos of the real Nova SBE Carcavelos campus as reference?
7. Licence and credit: confirm with Felix and name the source in the README.
8. Guests: sales computed per day on the server, or live guests on the map?
9. Ideas from the team, not yet a spec: Merchandise (customers walking out wear the clothes, a visual feature for `shop-art` or `guests`), beach loungers to rent at the Beach Cafe, and up to three printers on the campus where paper and ink have to be refilled.

---

# Part B: Game design reference (from roadmap v1, still valid)

Some wording in v1 mentioned the three.js map, walkways and the human review. Part A wins where they differ.

## B1. How a game day works (the core loop)

Read this as a numbered chain. Each step feeds the next one.

1. External influences are rolled once per day from a seed: weather, campus events, trends, disruptions (outages, strikes). Together they are the DAY CONTEXT.
2. For each shop, DEMAND = base demand (from price) x weather factor x event factor x trend factor x popularity factor x outfit bonus.
3. SALES = min(demand, stock, capacity). Capacity grows with staff.
4. The day produces revenue, minus wages. Badges are checked against the history.
5. POPULARITY of each shop is updated: it rises with fair prices and full shelves, it falls with empty shelves and too high prices. The new value affects the next day.
6. The EVENING REPORT (outlook) shows a forecast of tomorrow's day context. The forecast is wrong sometimes (suggested error rate about 20 %).
7. The player decides: purchases, prices, staff, outfits, unlocking shops. Then the next day starts at step 1.

Everything is per shop once there are several shops: each shop has its own demand, popularity, stock and staff.

## B2. Weather and events against shops (example values)

These factors are examples to discuss, not final numbers. 1.0 means normal demand.

| Weather | Cafe | Surf Shop | Merchandise | Beach Cafe |
|---|---|---|---|---|
| Sun | 0.8 | 1.3 | 1.0 | 1.5 |
| Heat | 0.6 | 1.2 | 0.8 | 1.8 |
| Rain | 1.4 | 0.5 | 1.2 | 0.4 |
| Storm | 1.0 | 0.2 | 1.0 | 0.2 |

| Event | Cafe | Surf Shop | Merchandise | Beach Cafe |
|---|---|---|---|---|
| No event | 1.0 | 1.0 | 1.0 | 1.0 |
| Exam period | 1.5 | 0.6 | 0.9 | 0.7 |
| Party | 0.8 | 1.0 | 1.1 | 1.5 |
| Career fair | 1.3 | 0.7 | 1.4 | 0.9 |

The factors are multiplied. Example: heat on a party day gives the Beach Cafe
1.8 x 1.5 = 2.7, so the player should order much more beer and coke zero. Above 1.15 the
player should order more, below 0.85 less.

## B3. Rules for every feature spec

So that the demo mode needs no rebuild later, every feature spec follows these
three rules from the start:

1. The whole game state is complete and can be set directly: day, cash, shops, stock, popularity, staff all live in the state.
2. The day context can be overridden. `make_day_context(seed, day)` takes an optional argument that fixes weather or event.
3. No randomness without the seed. Every random choice comes from the seed stored in the state.

## B4. Demo mode (presentation)

Built like a tutorial, about 5 minutes. Days are skipped: each scenario loads a
prepared start state and shows an explanation text. After the goal of a
scenario is reached, the next scenario loads. At the end the player can keep
playing freely, so the professor can see that the game also works without a script.

Scenario data (pure data in a new `scenarios.py`): start state, fixed weather or
event for these days, explanation text, goal condition. Functions:
`load_scenario(id)` and `scenario_done(state, id)`.

Example sequence (a suggestion, the final choice comes after the game is complete):

1. Basics: day 1, 100 euro. Buy stock, set a price, play the day.
2. Weather and outlook: the evening report predicts heat. The player orders more beer and coke zero at the Beach Cafe and sees the effect.
3. Second shop: more money, the Surf Shop is unlocked. Then a storm: the Surf Shop collapses, the Cafe profits.
4. Popularity and staff: empty shelves lower popularity. At a party, hiring staff pays off.
5. Disruption and finish: power cut or strike, then badges and the final settlement.

## B5. Glossary

| Term | Meaning |
|---|---|
| Day context (Tageskontext) | The result of one day's rolled external influences: weather, events, trends, disruptions. |
| Outlook | The evening report with a forecast of the next day's day context. |
| Popularity (Beliebtheit) | Per shop, 0 to 100 %. Scales customer numbers on the next day. |
| Seed | A number stored in the state from which all randomness is derived, so runs are reproducible and testable. |
| Scenario | A prepared start state with explanation text and a goal, used by the demo mode. |
| Track | Either logic (game rules) or visuals (appearance, walking paths). |

