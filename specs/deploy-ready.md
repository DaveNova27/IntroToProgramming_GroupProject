# Deploy ready

Issue #85. Found in the audit (`docs/audit-report.md`, item S1) and the roadmap (3a, point 8: a
session per player, a rate limit, security headers, a production server).

## What

The app can be put on the internet without every visitor sharing one run. Local play, as in the
README (`uv run python app.py`), does not change.

1. **Security headers on every answer** (also locally): `X-Content-Type-Options: nosniff`,
   `X-Frame-Options: SAMEORIGIN` (the campus is an iframe of our own page), `Referrer-Policy:
   no-referrer`, and a `Content-Security-Policy` that allows only our own files (`default-src 'self'`,
   `script-src 'self'`, inline styles only for the colours, `object-src 'none'`). `Strict-Transport-
   Security` when the request came over HTTPS.
2. **Public mode** (`CT_PUBLIC=1`):
   - **A run per player.** The first page load gives a random cookie (`ct_player`, HttpOnly, SameSite=
     Lax, Secure over HTTPS, one year); the run is stored in `data/players/<cookie>.db`. A cookie that is
     not exactly 22 characters of `A-Z a-z 0-9 _ -` is never used as a file name. An API call without a
     valid cookie makes no run (400).
   - **Limits.** 240 API requests per player per minute (a played day needs about 60), 30 new players
     per address per minute, at most 2,000 runs on disk (then 503 "the game is full"). A refused
     request changes nothing.
   - **No dev switches.** The editor (`CT_EDITOR`) and the weather override (`CAMPUS_TYCOON_DEMO`)
     are off in public mode, whatever the environment says.
3. **Answers without paths.** An unexpected error answers 500 with one fixed sentence; the details go
   to the server log only.
4. **Running it.** `CT_HOST` and `CT_PORT` set where `app.py` listens (default: this computer only).
   For other people use a production server with **one worker** (the lock and the rate counter live in
   the process): `uv run --with gunicorn gunicorn -w 1 --threads 8 -b 127.0.0.1:8000 app:app` behind a
   proxy that does HTTPS (`CT_PUBLIC=1`). See the README.

## Out of scope

Accounts and passwords, a leaderboard across players, HTTPS itself (the proxy does it), another
database than SQLite, deleting old runs, a Dockerfile, the weak spot that a script can play a day
faster than one tick a second (it only changes the player's own run).

## Done when

1. `tests/test_deploy_ready.py`: the headers on pages, files and the API; no inline script and no
   inline handler in the two pages; local play sets no cookie; two players have two runs; the cookie
   flags; a returning player keeps the run; no run without a cookie; forged cookies (path tricks) are
   never a file name; the rate limit answers 429 and changes nothing; new players and the number of
   runs are limited; the dev switches are off; an error shows no path.
2. The campus and the dashboard work in the browser with the new headers (no console error from the
   Content-Security-Policy) and in public mode.
3. `uv run pytest` passes, `tests/` untouched.

Rules: money, randomness and the rules are untouched; a refused request (limit, no cookie) saves
nothing; the seed never leaves the server.
