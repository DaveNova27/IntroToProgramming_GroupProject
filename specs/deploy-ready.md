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
   - **A run per player.** The first load of the page (`/` or `/map`; not files or probes) gives a
     signed cookie `ct_player` = `<22 random characters>.<signature>` (HMAC-SHA256 with a secret: `CT_SECRET`,
     or a random one kept in `data/players/.secret`), HttpOnly, SameSite=Lax, Secure over HTTPS, one
     year. The run is stored in `data/players/<id>.db`. A cookie we did not sign (forged, altered, only
     the right shape) is no cookie: an API call with it makes no run (400), so nobody can fill the disk
     with made-up ids.
   - **Limits.** 240 API requests per player per minute (a played day needs about 60), 60 new players
     per address per minute, at most 2,000 runs on disk (made one at a time, so it is a hard limit; a new
     run is then refused with 503 "the game is full"; whoever has a run stays in), at most 20,000
     counters at once (beyond that 503 "busy", swept at most once a second). A refused request changes
     nothing. One lock per player (64 stripes), not one for everybody.
   - **Behind a proxy** (`CT_PROXY=1`, only when the proxy is the only way in): the address is the last
     `X-Forwarded-For` entry and HTTPS is `X-Forwarded-Proto: https`; this makes the limit per visitor
     instead of per proxy, and the cookie Secure with HSTS. Without the switch those headers are ignored.
   - **The key** that signs the cookies is made once under a lock and written whole (never half a key).
   - **No dev switches.** The editor (`CT_EDITOR`) and the weather override (`CAMPUS_TYCOON_DEMO`)
     are off in public mode, whatever the environment says.
3. **Answers without paths.** An unexpected error answers 500 with one fixed sentence; the details go
   to the server log only. An API answer is always JSON (also a 404 or 405).
4. **Running it.** `CT_HOST` and `CT_PORT` set where `app.py` listens (default: this computer only).
   For other people use a production server with **one worker** (the locks and the rate counter live in
   the process): `CT_PUBLIC=1 CT_PROXY=1 uv run --with gunicorn gunicorn -w 1 --threads 8 -b 127.0.0.1:8000
   app:app` behind a proxy that does HTTPS. See the README.

## Out of scope

Accounts and passwords, a leaderboard across players, HTTPS itself (the proxy does it), another
database than SQLite, deleting old runs, a Dockerfile, the weak spot that a script can play a day
faster than one tick a second (it only changes the player's own run).

## Done when

1. `tests/test_deploy_ready.py`: the headers on pages, files and the API; no inline script and no
   inline handler in the two pages; local play sets no cookie; two players have two runs; the cookie
   flags and its signature; a returning player keeps the run; no run without a cookie; forged,
   altered and unsigned cookies (also with the right shape) make no run; files get no player; the rate limit answers 429 and changes nothing; new players and the number of
   runs are limited, the counters are bounded, the proxy headers count only with `CT_PROXY=1`; the dev switches are off; an error shows no path.
2. The campus and the dashboard work in the browser with the new headers (no console error from the
   Content-Security-Policy) and in public mode.
3. `uv run pytest` passes, `tests/` untouched.

Rules: money, randomness and the rules are untouched; a refused request (limit, no cookie) saves
nothing; the seed never leaves the server.
