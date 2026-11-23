# README: objectives and installation (`readme-install`)

Written 2026-11-23 by David, before the submission (2026-11-23, 23:59). Docs only, no game code.

## What

The Moodle submission asks for "a README file describing the project, its objectives, installation
instructions, and how to run the application". The README described the project and how to run it,
but had no objectives and assumed that `uv` was already installed. Two sections are added:

1. **Objectives** (after the introduction): a playable business game; rules decided on the server;
   reproducible from a seed; online for everyone; verified by tests and reviews.
2. **Installation** (before *Run*): install uv (macOS, Linux, Windows), clone the repository,
   `uv sync`. uv brings the right Python (3.11 or newer) and the versions of `uv.lock`. No key or
   database is needed to play locally.

## Decide

1. **uv only.** The project is built and tested with uv (`uv.lock`, the CI, Render). A second way with
   pip and a `requirements.txt` would be one more thing to keep in step; not added.

## Out of scope

Game code, tests, the other sections of the README.

## Done when

- `uv run pytest` passes; nothing in `tests/` changed.
- The installation steps work on a fresh clone (`uv sync`, then `uv run python app.py`).
- README spec table names this spec; issue and PR opened; AI review done.
