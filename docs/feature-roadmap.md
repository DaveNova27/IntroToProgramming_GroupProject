# Campus Tycoon: Feature Roadmap

Status: proposal after the first group call (Nova SBE, 4 members). Everything
here is a plan to discuss, not a decision, unless it says "decided".

This file is plain text on purpose so that every team member's AI assistant can
read it from the repository. Read `AGENTS.md` first for the working rules.

## 1. Project context

Campus Tycoon is a snack-stand simulation with a Flask server and a browser UI.

| Part | Files | Job |
|---|---|---|
| Rules | `logic.py` | Pure functions. Every function takes a state and returns a NEW state. A refused action raises `RejectedAction` and changes nothing. Money is integer cents. |
| Storage | `db.py` | SQLite, one run. |
| Server | `app.py` | Flask JSON API. The browser never decides a rule. |
| Dashboard | `static/index.html`, `style.css`, `app.js` | HUD, stock overview, product cards, charts. |
| 3D map | `static/map.html`, `map.css`, `map.js` | three.js campus scene with kiosk, customers, deliveries, day/night. |
| Shared | `static/views.js`, `static/common.js` | View switching and helpers. |

Working rules that apply to every task (from `AGENTS.md`):

- One spec per task, one branch per spec, one GitHub Issue per spec, one pull request per spec.
- Never commit a feature to `main` directly. A pull request needs one approving review from another member and a passing `Tests` check.
- Never edit, delete or skip anything in `tests/`.
- Store money as integer cents, never floats.
- A rejected action must not change any saved data.
- Stay inside the spec's "Out of scope" section.
- Spec format: `What`, `Out of scope`, `Done when` (see `specs/campus-polish.md`).

Current state of the game: one kiosk, three products (sandwich, coffee, cookie),
demand is a fixed function of price (`demand()` in `logic.py`: 10 units at or
below the reference price, 5 up to twice that price, 0 above). The 30-day season
exists on the branch `longer-run` and is not yet merged into `main`.

## 2. Decisions so far

| Topic | Decision |
|---|---|
| Customers | Rule-based "AI" customers, not a language model. Deterministic with a seed, testable. (Suggestion from the professor: AI-driven customers and demand steered by external factors such as weather.) |
| Season length | 30 days. The planned 10-day short mode is dropped. |
| Presentation | A demo mode with scenarios, built LAST, after the game is complete. The team then chooses which features appear in it. |
| Stock market / casino | Cut. Not part of the core. |
| Multiplayer | Cut. Mention only as an outlook. It is a security risk: the server would have to check every rule and trust nothing from the browser. |
| Visuals | Appearance of the campus and the walking paths of the figures are their own track, parallel to the game rules. |

## 3. The 11 points from the meeting, with status

| # | Feature | Status | Effort | Depends on |
|---|---|---|---|---|
| 1 | Several shops (own products, prices, target groups; unlocked one after another with money and level) | Core | large | day-context |
| 2 | Changing demand (daily fluctuation, trends such as a "matcha week") | Core | small to medium | day-context |
| 3.1 | Campus events (exam period, party, career fair) | Core | medium | day-context |
| 3.2 | Weather (sun, rain, storm, heat) shifts demand between shops | Core | medium | day-context |
| 3.3 | Outages (power cut, supply shortage): shop closed or goods scarce | Extension | small | day-context |
| 3.4 | Strikes (metro, suppliers): fewer walk-in customers or higher purchase prices | Extension | small | day-context |
| 3.5 | AI-based customers | Extension | large | walkways, day-context |
| 4 | Fixed length with final settlement (30 days) | Core | done on `longer-run` | none |
| 5 | Popularity of a shop in % (0 to 100) | Core | medium | day-context |
| 6 | Outlook for the next day (evening report, forecast sometimes wrong) | Core | medium | day-context |
| 7 | Buy outfits for the player figure (optional small bonus) | Optional | small (logic), medium (3D) | multi-shop |
| 8 | Badges for milestones | Extension | small | other features for some badges |
| 9 | Hire staff (wage vs. more customers served) | Extension | medium | multi-shop |
| 10 | Stock market, casino | Cut | | |
| 11 | Multiplayer | Cut | | |

## 4. How a game day works (the core loop)

Read this as a numbered chain. Each step feeds the next one.

1. External influences are rolled once per day from a seed: weather, campus events, trends, disruptions (outages, strikes). Together they are the DAY CONTEXT.
2. For each shop, DEMAND = base demand (from price) x weather factor x event factor x trend factor x popularity factor x outfit bonus.
3. SALES = min(demand, stock, capacity). Capacity grows with staff.
4. The day produces revenue, minus wages. Badges are checked against the history.
5. POPULARITY of each shop is updated: it rises with fair prices and full shelves, it falls with empty shelves and too high prices. The new value affects the next day.
6. The EVENING REPORT (outlook) shows a forecast of tomorrow's day context. The forecast is wrong sometimes (suggested error rate about 20 %).
7. The player decides: purchases, prices, staff, outfits, unlocking shops. Then the next day starts at step 1.

Everything is per shop once there are several shops: each shop has its own demand, popularity, stock and staff.

## 5. Weather and events against shops (example values)

These factors are examples to discuss, not final numbers. 1.0 means normal demand.

| Weather | Ice stand | Surf shop | Cafe | Snack stand |
|---|---|---|---|---|
| Sun | 1.5 | 1.3 | 0.8 | 1.0 |
| Heat | 2.0 | 1.2 | 0.5 | 0.8 |
| Rain | 0.4 | 0.5 | 1.4 | 1.1 |
| Storm | 0.2 | 0.2 | 1.0 | 0.7 |

| Event | Ice stand | Surf shop | Cafe | Snack stand |
|---|---|---|---|---|
| No event | 1.0 | 1.0 | 1.0 | 1.0 |
| Exam period | 0.9 | 0.6 | 1.5 | 1.2 |
| Party | 1.3 | 1.0 | 0.8 | 1.4 |
| Career fair | 1.0 | 0.7 | 1.3 | 1.3 |

The factors are multiplied. Example: heat on a party day gives the ice stand
2.0 x 1.3 = 2.6, so the player should order much more ice. Above 1.15 the
player should order more, below 0.85 less.

## 6. Rules for every feature spec

So that the demo mode needs no rebuild later, every feature spec follows these
three rules from the start:

1. The whole game state is complete and can be set directly: day, cash, shops, stock, popularity, staff all live in the state.
2. The day context can be overridden. `make_day_context(seed, day)` takes an optional argument that fixes weather or event.
3. No randomness without the seed. Every random choice comes from the seed stored in the state.

## 7. Build order

Two tracks run in parallel: LOGIC (game rules) and VISUALS (appearance, walking
paths). Each line below is one spec, one branch, one issue, one pull request.

### Phase 1: foundation (in parallel)

1. `split-map` (visuals): split `static/map.js` (about 1860 lines, one file) into modules without changing behaviour. Prevents merge conflicts for all later map work.
2. `day-context` (logic): seed, weather, demand factor, override for demos. Features 2 and 3.2.

### Phase 2: after the foundation (all in parallel)

3. `campus-look` (visuals, needs `split-map`): polish the campus look, details, light, planting.
4. `outlook` (logic): evening report with an uncertain forecast. Feature 6.
5. `popularity` (logic): popularity 0 to 100 %. Feature 5.
6. `events-and-disruptions` (logic): events, trends, outages, strikes. Features 2, 3.1, 3.3, 3.4.
7. `badges` (logic): Feature 8. Good starting task for a new member.
8. `weather-visuals` (visuals, needs `day-context`): rain, storm, heat and sky on the map.

### Phase 3: several shops (one person alone)

9. `multi-shop` (logic): several shops with unlocking. Feature 1. This touches state, database, API and UI at once, so nobody else should change those parts at the same time.

### Phase 4: what builds on the shops (in parallel)

10. `shop-buildings` (visuals): models for ice stand, surf shop, cafe, snack stand.
11. `walkways` (visuals): a network of waypoints, shops as data (position, entrance, queue), natural walking paths. Today `map.js` has fixed constants for one kiosk, two doors and one queue.
12. `staff` (logic): Feature 9.
13. `outfits` (logic): Feature 7, optional.

### Phase 5

14. `ai-customers` (logic, needs `walkways`): each customer chooses a target by budget, favourite product and weather preference, and walks there. Feature 3.5.

### Phase 6: last

15. `demo-scenarios`: scenario loader, explanation overlay and the scenarios themselves. The team chooses which features go in, once the game is complete.
16. `final-polish`: fine polish of animations, camera and details, matching the demo.

## 8. Demo mode (presentation)

Built like a tutorial, about 5 minutes. Days are skipped: each scenario loads a
prepared start state and shows an explanation text. After the goal of a
scenario is reached, the next scenario loads. At the end the player can keep
playing freely, so the professor can see that the game also works without a script.

Scenario data (pure data in a new `scenarios.py`): start state, fixed weather or
event for these days, explanation text, goal condition. Functions:
`load_scenario(id)` and `scenario_done(state, id)`.

Example sequence (a suggestion, the final choice comes after the game is complete):

1. Basics: day 1, 100 euro. Buy stock, set a price, play the day.
2. Weather and outlook: the evening report predicts heat. The player orders more ice and sees the effect.
3. Second shop: more money, the surf shop is unlocked. Then a storm: the surf shop collapses, the cafe profits.
4. Popularity and staff: empty shelves lower popularity. At a party, hiring staff pays off.
5. Disruption and finish: power cut or strike, then badges and the final settlement.

## 9. Visuals track

| Topic | Today | Goal |
|---|---|---|
| Code structure | `map.js` has about 1860 lines in one file | Modules for scene, buildings, customers and camera |
| Campus look | Buildings, plaza, coast and kiosk polished by the spec `campus-polish` | Fine polish of details, light and planting |
| Walking paths | Fixed constants for one kiosk | Waypoint network, shops as data |
| Weather | Sky colours exist (`setSky`) | Rain, storm and heat visible on the map |
| Shop buildings | One kiosk | One model per shop |
| Customers | Random customers on a fixed route | Each customer picks a target and walks the network |

## 10. Where the code goes

| File | What is added |
|---|---|
| `logic.py` | `make_day_context(seed, day)`, `demand()` with factors, `forecast()`, `update_popularity()`, `check_badges()`, wages and capacity in `trade_day()`. All pure functions returning a new state. |
| `db.py` | New state fields: `seed`, `shops`, `popularity`, `staff`, `badges`, `outfits`. Money stays integer cents. |
| `app.py` | New endpoints for the evening report, unlocking a shop, staff and buying outfits. The browser decides no rule. |
| `scenarios.py` | New, last: scenarios as data. |
| `static/` | Dashboard: evening report, shop selection, staff, outfits, demo overlay. Map: split into modules, then weather, shop buildings, walking network, customers, outfits on the figure. |
| `tests/` | New test files per spec. Existing tests stay unchanged. |

## 11. Open decisions

1. Strength of the weather, event and trend factors per shop. The values in section 5 are guesses.
2. Error rate of the forecast. Suggestion: about 20 %.
3. Formula for popularity: how many points do fair prices give, how many do empty shelves cost?
4. Shop unlocking: which shops, at which price and level, and which shop starts?
5. Shops early (more depth, but a big rebuild) or first weather, outlook and popularity with one shop? Walking paths and shop buildings depend on this.
6. Who takes which track. Suggestion: one person for `split-map` and the visuals, one for `day-context`, and the newest member for `badges`.
7. Which features go into the demo (decided at the end).
8. Should the professor be able to keep playing freely after the demo?

## 12. Glossary

| Term | Meaning |
|---|---|
| Day context (Tageskontext) | The result of one day's rolled external influences: weather, events, trends, disruptions. |
| Outlook | The evening report with a forecast of the next day's day context. |
| Popularity (Beliebtheit) | Per shop, 0 to 100 %. Scales customer numbers on the next day. |
| Seed | A number stored in the state from which all randomness is derived, so runs are reproducible and testable. |
| Scenario | A prepared start state with explanation text and a goal, used by the demo mode. |
| Track | Either logic (game rules) or visuals (appearance, walking paths). |
