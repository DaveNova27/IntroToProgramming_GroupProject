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
  - `static/world/`: the 2.5D world as ES modules. `main.js` loop, walking and the roof of the Nova; `ui.js` display and panels; `scene.js` shared state and projection; `render.js` one frame; `campus.js`, `nova.js` (walls, canopy and roofs of the Nova and its wings), `rooms.js` (their rooms), `roofs.js` (when each wing's roof fades), `beach.js` (the beach front, the boardwalk, the outdoor shops, the Dorm's surroundings), `zones.js` (joins the Dorm to the Nova's data), `environment.js`, `primitives.js`, `locations.js` drawing; `guests.js` the guests walking to their shop (drawn from the API); `physics.js`, `paths.js` collision and finding a way
  - `static/views.js`: switching between campus and dashboard, keeps both in sync
  - `static/common.js`: helpers shared by dashboard and campus
- `logic.py`: rules (what is valid, how results are calculated)
- `guests.py`: rules for the guests of a day (who goes to which shop, from the seed)
- `world.py`: the campus as data (zones, doors, solid objects, room layouts)
- `db.py`: stored state (what is saved and loaded)
- `README.md`: how everything fits together, list of specs, known issues
- `docs/feature-roadmap.md`: group plan: features, build order, demo mode, open decisions. Read it before starting a spec.

## Rules
- Build each spec on a branch named after it, e.g. `first-feature`. Never commit a feature to `main` directly.
- After every change, run the tests for the task and paste the final output. The output is the proof, not a sentence.
- Never edit, delete or skip anything in `tests/`. If a test looks wrong, say so and stop.
  - Exception, no one else needed: the member who owns the spec/PR may confirm a test change for their own PR, in their own words in the session. The AI never confirms for them.
  - Allowed only when the old test refers to data the spec changes on purpose (names, counts, thresholds). Never weaken a check, never skip or delete a test.
  - Write each changed test and the reason into the spec ("Decide") and the PR description. New checks go in new test files.
- One spec per task. Stay inside its "Out of scope" fence.
- Store money as integer cents, never floats.
- A rejected action must not change any saved data.
- All randomness comes from the seed stored in the state. No `random` call without it. The same holds for anything drawn: no `Math.random` in `static/world/`.
- The browser decides no rule. The world in `static/world/` only draws and walks; money, stock, days and later unlocking shops always go through the API.
- Nothing is loaded from outside this app: no CDN, no web fonts.
- The whole game state must stay complete and settable (day, cash, shops, stock, popularity, staff, player position), and the day context (weather, events) must accept an override. The demo mode depends on both.

## How to report
- Paste the final test output and list every file you changed.

## Model and effort
Usage limits are limited, so the user should pick the model and the effort on purpose. The
tiers below are named by strength, not by version, so they stay valid when the models change.
- Give the hint only when a task touches more than one file, or when the work changes phase
  (explore, write the spec, build, review). One sentence: which tier and effort you recommend
  and why. No hint for a question or a one-file edit.
- If you can switch yourself (the session tools `set_session_model` and `set_session_effort`,
  load them with ToolSearch if they are only listed as deferred), say what you change first.
  If you cannot, say what the user should set in the app, then carry on with the current
  setting and say which one it is. You cannot see the setting: ask the user to confirm before
  anything that depends on it, such as the build of a big change.
- Recommendation:
  - Explore, read, compare, write a spec, plan: a strong model, medium effort.
  - Build across many files, or anything that has to be checked in the browser: the strongest
    model available, high effort.
  - Review of a PR (`/code-review`): high effort. If it is easy to do, use a different or
    stronger model than the one that built it, but do not hold the review back for it.
  - Small fixes, texts, commit messages, README: a small, fast model, low or medium effort.
  - `xhigh` and `max` only after two failed attempts at the same problem, and say why first.
- These are recommendations. The user decides.

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
