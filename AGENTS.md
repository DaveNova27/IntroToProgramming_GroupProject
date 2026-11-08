# Campus Tycoon

Snack-stand simulation: a 30-day season, start with €100. Product rules are in the BRD (CT01-CT05, CT R1-R5). The current task is always the spec in `specs/`.

## Commands
- Run the app: `uv run python app.py` (then open http://127.0.0.1:8000)
- Run tests: `uv run pytest`

## Structure
- `app.py` + `static/`: screen (what the user sees and clicks)
  - `app.py`: Flask server and JSON API; it calls the rules, the browser never decides them
  - `static/index.html`, `style.css`, `app.js`: dashboard
  - `static/map.html`, `map.css`: campus page with its display on top
  - `static/world/`: the 2.5D world as ES modules. `main.js` loop, walking and the roof of the Nova; `ui.js` display and panels; `scene.js` shared state and projection; `render.js` one frame; `campus.js`, `nova.js` (walls, canopy and roofs of the Nova and its wings), `rooms.js` (their rooms), `roofs.js` (when each wing's roof fades), `environment.js`, `primitives.js`, `locations.js` drawing; `physics.js`, `paths.js` collision and finding a way
  - `static/views.js`: switching between campus and dashboard, keeps both in sync
  - `static/common.js`: helpers shared by dashboard and campus
- `logic.py`: rules (what is valid, how results are calculated)
- `world.py`: the campus as data (zones, doors, solid objects, room layouts)
- `db.py`: stored state (what is saved and loaded)
- `README.md`: how everything fits together, list of specs, known issues
- `docs/feature-roadmap.md`: group plan: features, build order, demo mode, open decisions. Read it before starting a spec.

## Rules
- Build each spec on a branch named after it, e.g. `first-feature`. Never commit a feature to `main` directly.
- After every change, run the tests for the task and paste the final output. The output is the proof, not a sentence.
- Never edit, delete or skip anything in `tests/`. If a test looks wrong, say so and stop.
- One spec per task. Stay inside its "Out of scope" fence.
- Store money as integer cents, never floats.
- A rejected action must not change any saved data.
- All randomness comes from the seed stored in the state. No `random` call without it. The same holds for anything drawn: no `Math.random` in `static/world/`.
- The browser decides no rule. The world in `static/world/` only draws and walks; money, stock, days and later unlocking shops always go through the API.
- Nothing is loaded from outside this app: no CDN, no web fonts.
- The whole game state must stay complete and settable (day, cash, shops, stock, popularity, staff, player position), and the day context (weather, events) must accept an override. The demo mode depends on both.

## How to report
- Paste the final test output and list every file you changed.

## Group workflow

This is now the Nova SBE group project (2477-2627_S1, 3-4 members). Everyone must
contribute code to this repository.

- One GitHub Issue per spec, using the "Spec" issue template. Assign yourself before
  starting.
- Open a pull request from your spec branch into `main`. `main` is protected: a PR
  needs a passing `Tests` check (GitHub Actions runs `uv run pytest` on every PR)
  before it can be merged. No human approval is required.
- Every PR gets an AI code review (for example `/code-review` in Claude Code) before
  it is merged. Fix the findings or answer them in the PR. The AI review replaces the
  review by another member.
- Keep PRs scoped to one spec, same as the solo rules above.
