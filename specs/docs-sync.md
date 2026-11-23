# The docs in step with the code (`docs-sync`)

Asked for by Felix on 2026-11-23, items D1 and D4 of the audit of 2026-11-21. Builds on `docs-refresh`.

## Why

The AI agents read `AGENTS.md` first, and its structure list had fallen behind: 9 of the 27 modules in
`static/world/` (`cull.js`, `guide.js`, `people.js`, `player.js`, `serial.js`, `shop-signs.js`,
`stock_groups.js`, `walkers.js`, `wardrobe.js`), `static/badges.css` and the folder `checks/` were not
named. Three sentences were outdated since `persistent-runs` (runs on the public server last now): the
README's line for `deploy.md` ("erased on restart for now"), the docstring of the health check in
`app.py` ("a restart ... erases every run") and the README's roadmap link ("state of 2026-11-10").

## What

1. `AGENTS.md` names every module of `static/world/` with what it does (from its own head comment),
   `static/badges.css`, and says that `uv run pytest` collects `checks/` too and that new checks go in
   new files in `tests/`.
2. The three sentences say what is true now.
3. `tests/test_docs_sync.py` checks that every `static/world/*.js` is named in `AGENTS.md`, so the list
   cannot fall behind again unnoticed, and that the three old sentences are gone.

## Decide

1. **Text only.** No game code, no rule, no test changes; the docstring is the only line in `app.py`.
2. **`checks/` stays where it is.** Moving its files into `tests/` is a change to test files on the day
   of the deadline; `AGENTS.md` now explains the folder instead (audit D2, later if wanted).
3. **The roadmap itself is not rewritten** (audit D3): David's PR #109 touches it; the README link now
   says where the later work is.

## Out of scope

The roadmap and the old audit report (D3), branches and issues (D5, D6), every other audit item.

## Done when

1. Every `static/world/*.js`, `static/badges.css` and `checks/` are named in `AGENTS.md`.
2. "erased on restart for now", "erases every run" and "state of 2026-11-10" are gone.
3. `tests/test_docs_sync.py` passes; the full suite passes; no old test changed.

## Security

Documentation only.
