# Campus Tycoon

Snack-stand simulation: 5 trading days, start with €100. Product rules are in the BRD (CT01-CT05, CT R1-R5). The current task is always the spec in `specs/`.

## Commands
- Run the app: `uv run python app.py` (then open http://127.0.0.1:8000)
- Run tests: `uv run pytest`

## Structure
- `app.py` + `static/`: screen (what the user sees and clicks)
  - `app.py`: Flask server and JSON API; it calls the rules, the browser never decides them
  - `static/index.html`, `style.css`, `app.js`: dashboard
  - `static/map.html`, `map.css`, `map.js`: 3D campus map (three.js from CDN)
  - `static/views.js`: switching between dashboard and map, keeps both in sync
  - `static/common.js`: helpers shared by dashboard and map
- `logic.py`: rules (what is valid, how results are calculated)
- `db.py`: stored state (what is saved and loaded)
- `README.md`: how everything fits together, list of specs, known issues

## Rules
- Build each spec on a branch named after it, e.g. `first-feature`. Never commit a feature to `main` directly.
- After every change, run the tests for the task and paste the final output. The output is the proof, not a sentence.
- Never edit, delete or skip anything in `tests/`. If a test looks wrong, say so and stop.
- One spec per task. Stay inside its "Out of scope" fence.
- Store money as integer cents, never floats.
- A rejected action must not change any saved data.

## How to report
- Paste the final test output and list every file you changed.
