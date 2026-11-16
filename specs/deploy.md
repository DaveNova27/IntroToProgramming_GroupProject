# Deploy (`deploy`, issue #93)

Agreed by Felix on 2026-11-16 ("1. erst flüchtig dann supabase. 2. ich soll mich drum kümmern, deswegen
würde ich den account erstmal anlegen 3. passt." after drafts of 2026-11-15/16). Builds on `deploy-ready` (#85: public mode, one run per player, limits,
security headers). The course requires the deployed app on a public URL, the code on `main`, the URL
in the README (due 2026-11-23, 23:59, submit in the morning); the live demo runs on that URL.

Every fact about the hosts below was read on their own documentation or pricing pages on 2026-11-15
(re-checked once more that day after a first version). Every claim about our own app was measured on
a scratch copy of `main` (section "Measured"). What could not be checked from here is listed as such under
"Check on the first deploy"; the two weakest points are named in decision 7 (client address, from forum
posts) and in decision 1 (Cloud Run, Cloudflare Pages).

## What

The game runs on the internet at a free `https://….onrender.com` address, started from `main` by
the file `render.yaml` in the repository. Playing it locally (`uv run python app.py`) does not change.

### The host: Render, a free web service

One web service created from the **Blueprint** `render.yaml` (infrastructure as a file in the repo,
so the setup is reviewed like code and can be rebuilt in minutes):

| Setting | Value | Why |
|---|---|---|
| `type` / `runtime` / `plan` | `web` / `python` / `free` | free; Render's first-deploy page: "No payment is required" |
| `region` | `frankfurt` | the nearest of Render's five regions to Lisbon (cannot be changed later) |
| `branch` | `main` | what the course grades |
| `autoDeployTrigger` | `checksPass` | a deploy starts only when the `Tests` check of that commit passed (a merge into `main` already needs it, this also covers a push that skips the PR) |
| `buildCommand` | `uv sync --locked --no-dev --group deploy` | exact versions from `uv.lock`; `--locked` fails the build when `uv.lock` is out of date instead of installing something else; no pytest on the server; gunicorn from the `deploy` group |
| `startCommand` | `uv run --no-sync gunicorn -w 1 --threads 8 --no-control-socket -b 0.0.0.0:$PORT app:app` | one worker (the locks and the rate counter live in the process, `deploy-ready`); 8 threads; the port is `$PORT` (set to 10000 below); `--no-sync` so starting never touches the packages; `--no-control-socket`: gunicorn 26 opens a control socket in the home directory by default (seen in the log), which we do not use and which would need a writable home |
| `PORT` | `10000` | Render's docs call `PORT` an optional variable ("the port that your HTTP server binds to", default 10000); they do not say that Render always sets it. Set explicitly, so `$PORT` in the start command can never be empty (measured: gunicorn with `-b 0.0.0.0:$PORT` and no `PORT` stops with "'' is not a valid port number") |
| `healthCheckPath` | `/healthz` | see below |
| `PYTHON_VERSION` | `3.12.14` | the version `uv` uses for this project here; Render's default for new services is 3.14.x, which nobody has run our tests on. Set as an environment variable (a fully qualified version is required there) and not as `.python-version`, so nobody's local `uv` changes |
| `CT_PUBLIC` | `1` | public mode |
| `CT_PROXY` | `1` | Render's proxy is the only way in; it tells us HTTPS and the visitor |
| `CT_SECRET` | `generateValue: true` | Render makes a random 256-bit value once and keeps it across deploys; it is in no file of the repo |

A build that fails is cancelled by Render and the running version stays up (Render's docs: "How deploys
work"). HTTPS and the certificate are Render's.

### `gunicorn` as a pinned dependency

`pyproject.toml` gets a dependency group `deploy = ["gunicorn>=26.2,<27"]`, `uv.lock` the exact version
(26.2.0, released 2026-08-24). Not 27.0: 27.0.0 came out on 2026-11-10 and 27.0.1 on 2026-11-12 (PyPI),
too new to be the one thing we cannot debug before a demo. The default install (`uv sync`, `uv run pytest`, CI) does not change: only
the `dev` group is installed by default (measured). The README's local command becomes
`uv run --group deploy gunicorn …` instead of `uv run --with gunicorn …`, so a local test of the
production server uses the same version as the server.

### `GET /healthz`

A new route in `app.py`: answers `200` with the text `ok`, in public and in local mode, and does
nothing else: no player, no cookie, no database, no rate counter, no file written.

Why a route of its own:

- **Not `/`.** Measured: a request to `/` without a cookie sets a `ct_player` cookie and counts as a
  *new player* of that address (limit 60 a minute). A probe every few seconds would use up that budget and
  the real players of a class would get "Too many new players".
- **Not a missing path.** A path that does not exist answers 404 (measured for `/healthz` before it
  exists) and Render reads 4xx as "unhealthy".
- **It must never fail for a reason that a restart would not fix, and never touch the disk.** Render
  restarts an instance that fails its health checks, and a restart on the free plan erases all runs.
  So the check only proves "the process answers", nothing more clever.

## Decide

The three marked ► were answered by Felix on 2026-11-16; the rest follows from the numbers above.

1. **Host: Render free web service.** The others, read on their own pages on 2026-11-15:
   - **Vercel** (Hobby plan is free): a Flask app becomes a single Vercel Function that "scales with
     traffic" (several instances), and its static files must move to `public/` (Flask's own static folder
     "should not be used"). Vercel's knowledge base answers "Is SQLite supported in Vercel?" with: it
     "can't be used with Vercel", storage is ephemeral and each instance has its own. That breaks our
     one-process locks, our rate counter and the run files, and would need a hosted database (a rewrite
     of `db.py`). **Ruled out.**
   - **Fly.io:** the trial is $1 of credit for 7 days, no card to start; after that a card is required
     for everything. A small always-on machine costs about $2.19 per 30 days, a persistent volume
     $0.15 per GB per month, and a personal organisation whose monthly bill stays under $5 has it waived
     (Fly's "Free Waiver"). So it is nearly free *with a card* and it is the one option here with a disk
     that survives. Needs its own deploy configuration (not `render.yaml`), so another spec.
   - **Railway:** a free trial of up to 30 days with a one-time $5 grant, then the Free plan with $1 of
     credit per month. Not enough to rely on for a graded demo.
   - **Koyeb:** requires a credit card (a $29 pre-authorisation hold that is cancelled again).
   - **Google Cloud Run:** has a free tier but it is tied to a billing account; I did not check how its
     disk behaves (from memory it is erased too) nor the Dockerfile need.
   - **Cloudflare Pages:** not checked; a static and edge platform, not a place for a long-running Flask
     process.
   If Render fails the sign-up check below, the order is: Fly.io (with a card, it also solves decision 2),
   then a paid Render instance.
2. **► Storage: erased for now, kept later (Supabase).** Answer of the team on 2026-11-16: the runs
   should be kept, and the way is Supabase (David's proposal), but **after** this deploy, as its own spec
   `persistent-runs`: with a `DATABASE_URL` set, a run is stored in Supabase's Postgres; without it,
   SQLite stays (locally and in all tests). That later spec only adds `DATABASE_URL` to `render.yaml`
   (`sync: false`; Render ignores such a variable when an existing Blueprint is updated, so it is entered
   once by hand in the dashboard). Until then this deploy runs with erased runs, as follows. The course guide "Storing data" says this is
   "acceptable for a demo that reloads example data on startup, but not for data that must persist";
   our demo scenarios (`/?demo`) load their own data into a run. Its standard alternative, a hosted
   database such as Supabase, is a rewrite of `db.py` for per-player runs, and a free Supabase project
   pauses after a week without activity. On the free plan the disk is ephemeral: every run in
   `data/players/` is lost when the service redeploys, restarts, or **spins down after 15 minutes
   without a request** (Render: "Free instances", "Local files lost on redeploy"). A persistent disk needs a
   paid instance (not available on free). A free Render Postgres database is not an
   option: it expires after 30 days, and moving the game from SQLite to it is another spec. What we do
   instead:
   - `CT_SECRET` is set, so the cookie of a player whose run was erased is still valid and the player
     simply gets a fresh run on the next call (measured: day 1, €100, no error). Without `CT_SECRET`,
     the secret in `data/players/.secret` is lost with the disk too, and every old cookie becomes
     invalid: each API call answers 400 "Open the game page first" until the page is reloaded (measured).
   - The demo scenarios (`/?demo`) rebuild a run from an id, so a wipe in the middle of the
     presentation costs one click on *Demo*.
   - The first request after idle takes about a minute (Render shows a loading page). **Wake the app
     two minutes before the demo and before the rehearsal**, and do not merge or deploy during them: a
     deploy erases all runs.
   - The honest answer for the walkthrough ("Where is the data stored?") goes into the README:
     one SQLite file per player on the server's disk, erased on restart; for a graded demo that is acceptable,
     for a real product it would be a persistent disk or a hosted database.
   - If the team prefers that nothing is ever erased, two ways, both need a credit card and neither is
     done unless Felix or the team asks: (a) upgrade this one Render service to a paid instance with a
     persistent disk mounted on `data/` (only `render.yaml` changes: `plan`, `disk`; the price is on
     Render's pricing page); (b) move to Fly.io with a volume, which costs cents a month and is waived
     under $5 (decision 1), but needs a new deploy configuration and its own spec.
3. **► Whose Render account: Felix'.** Felix creates the account and the Blueprint. Render's docs:
   once GitHub is connected, "you can deploy services using any repository you have access to"; if the
   repository is missing, the Render GitHub app's "Repository access" has to include it. The repository
   belongs to David's personal account (`DaveNova27`); on a personal account usually only its owner
   can allow an app on it (GitHub's rule, not checked here). So: if the repository does not show up in
   Render, David allows the Render app for it once (`github.com/apps/render/installations/new`). Render's
   docs also warn that deploys stop when the service's creator loses access to the repository; the
   credentials can be changed in the service's settings. I never type credentials, grant permissions
   or accept terms; those clicks are Felix'.
4. **► Service name and URL: `campus-tycoon`.** The name in `render.yaml` decides the address
   (`<name>.onrender.com`, Render adds a suffix when the name is taken, so the final URL is known only
   after the first deploy). A custom domain is out of scope.
5. **Auto deploy on `checksPass`**, not `commit` (see the table), and off by hand on the day of the
   demo if wanted. Every merge into `main` redeploys and erases all runs, so near the demo nothing is
   merged (the roadmap proposes a feature freeze on 2026-11-17; that date is only a proposal of the
   team, the hard deadline is the Moodle submission on 2026-11-23, 23:59).
6. **No access log.** gunicorn's default writes errors only. An access log would write every
   visitor's address into Render's logs, and the health checks would fill them.
7. **Client address behind Render.** The app takes the *last* `X-Forwarded-For` entry. Render appends
   its own hop to that header and does not strip what a client sends (community reports, not Render's docs),
   so the last entry is written by Render and cannot be faked by a visitor. Whether it is the visitor
   or one of Render's own proxies, I could not confirm. Worst case: all players share one counter, so
   at most 60 new players per minute in total (a class of 30 is fine; the 61st gets "Try again in a
   minute"). No code change; checked on the first deploy (below).
8. **No old test changes.** All new checks go into `tests/test_deploy.py`.

## Out of scope

A custom domain; a Dockerfile; another database or a persistent disk (decision 2: Supabase follows as
the spec `persistent-runs`); accounts;
removing old runs; changing the limits or the headers of `deploy-ready`; keep-alive pings that hold a
free service awake (against the spirit of the free plan, and a restart erases the runs anyway);
the bugs of the test report (price that does not survive a reload, stock overview, button names on
mobile, which trade paths to support): each is its own spec.

## Done when

**A. In the pull request (`deploy`, closes #93)**

1. `render.yaml` exists with exactly the settings of the table, and no secret value.
2. `pyproject.toml` has the group `deploy`, `uv.lock` is updated (`uv lock`), the default dependencies
   are unchanged (only Flask; no gunicorn in the default install).
3. `GET /healthz` as described, with `tests/test_deploy.py`:
   - `200` and `ok` without a cookie, in public mode and in local mode; `HEAD` too;
   - no `Set-Cookie`, no file in `data/players/` made, and 500 probes in a row do not use up the new-player
     budget (a page load afterwards still gets a player);
   - the security headers are on it like on every answer;
   - `render.yaml`: the health check path is `/healthz`; the start command has `-w 1` (no other worker
     count), has `--no-control-socket`, binds `0.0.0.0:$PORT`, runs `app:app`; the build command has `--locked`, `--no-dev` and
     `--group deploy`; `CT_PUBLIC` and `CT_PROXY` are `"1"`; `PORT` is `"10000"`; `CT_SECRET` uses `generateValue` and has no
     `value`; `autoDeployTrigger` is `checksPass`; `branch` is `main`; `PYTHON_VERSION` is a fully
     qualified 3.11 or newer;
   - `pyproject.toml`: gunicorn is in the group `deploy` and not in `dependencies`; `uv.lock` names it.
4. README: "Putting it online" is rewritten (the Render steps, the variables, redeploy and
   rollback, what is erased and when, the `deploy` group command); a spec row for `deploy.md`;
   the walkthrough answer on storage; next to the "Deployed app" line one sentence that runs on the
   public server are erased after 15 minutes without visitors or a deploy (on purpose, until
   `persistent-runs`) and that the first visit after a pause takes about a minute. The roadmap marks decision 7.11 and item 11 as decided.
   `AGENTS.md` gets the storage choice and how to reset the data, as the course guide "Storing data"
   asks: locally delete `data/campus_tycoon.db` (or press *New run* in the game); on the public
   server the runs are erased by every restart or deploy, and a player's *New run* (`/api/new-run`)
   resets only that player's run.
5. It works from a fresh copy of the repository, which is all the host has (the tutors' advice): a
   `git clone` of the branch in an empty folder, `uv sync --locked --no-dev --group deploy`, the start
   command with the three variables, `/` and `/healthz` answer 200. Output pasted in the PR.
6. The complete test suite passes (`uv run pytest`), output pasted in the PR; no file in `tests/`
   changed except the new one; AI review (`/code-review` high) done and its findings fixed or answered.

**B. After the merge (by the humans, I prepare the checklist, never the sign-in or the secrets)**

7. The Blueprint is created in Render from `main` (New, Blueprint, pick the repo), the first deploy is
   green, the service is on the `free` plan, `CT_SECRET` exists in its environment, auto deploy shows
   "After CI checks pass".
8. Smoke test on the public URL (below), on a laptop and on a phone on mobile data, all items ticked.
9. A small second PR puts the real URL into the README ("Deployed app:") and into the walkthrough
   notes. Until then the README line stays as it is.
10. The rehearsal (the roadmap's proposal was 2026-11-16; it moves to after the deploy) is played on the
   public URL.

### Smoke test (all on the public `https://` address)

1. `curl -si https://<url>/healthz` is `200 ok`.
2. The page loads with the padlock; `curl -si https://<url>/` shows `Set-Cookie: ct_player=…; Secure;
   HttpOnly; SameSite=Lax`, `Strict-Transport-Security` and the `Content-Security-Policy`.
3. Normal window and private window: two different runs (play a day in one, the other is still at day 1).
4. Play day 1 to its end in the browser (open, a shift or skip, close); reload; the run is still there.
5. `curl -si https://<url>/api/state` without a cookie: 400 "Open the game page first".
6. The editor and the weather override do nothing: `POST /api/editor/cash` answers "The editor is off".
7. `/?demo` loads the first scenario and plays it.
8. A wrong URL and a wrong request body show our sentences, no path, no stack trace.
9. The phone: the page, the campus and a day work on mobile data.
10. Restart behaviour: *Manual Deploy* in the dashboard, then reload in the open browser: no error
    screen, a fresh run at day 1 (this is the known cost of decision 2; if an error screen shows
    instead, `CT_SECRET` is missing).
11. Cold start: leave it 16 minutes, then open the URL; write down how long the first answer takes.
12. The newest version is live: the dashboard shows the commit of the last deploy and it is the head of
    `main` on GitHub (the tutors name an old version as a typical pitfall).

### Redeploy and rollback

- Redeploy: every green commit on `main` (decision 5), or *Manual Deploy* in the dashboard. Every
  redeploy erases all runs.
- Rollback: the dashboard's *Rollbacks* (the free plan keeps the two most recent previous deploys), or revert
  the PR on GitHub and let the deploy run. Never rotate `CT_SECRET` during a demo (all cookies stop
  working).
- If the host fails on the day (a Render outage, the monthly 750 free hours used up): the app
  runs locally (`uv run python app.py`) and the README names that as plan B. The 750 hours are
  enough for one service running all month (744 hours at most), but a second free service in the
  same workspace would share them.

## Measured

On a scratch copy of `main` (2d15526) made with `git archive`, nothing of Felix' own run touched:

- `uv sync --locked --no-dev --group deploy` in a clean folder installs exactly Flask and its
  six libraries (blinker, click, itsdangerous, Jinja2, MarkupSafe, Werkzeug) plus gunicorn 27.0.1, no pytest; `uv run --no-sync gunicorn -w 1 --threads 8
  -b 0.0.0.0:$PORT app:app` starts and answers `/` and `/static/style.css` with 200 (Python 3.12.14).
  gunicorn 26.2.0 answers the same; both log "Control socket listening at ~/.gunicorn/gunicorn.ctl"
  unless `--no-control-socket` is given.
- Final check on the branch (commit 1b773d3), as the host does it: `git clone --branch deploy` into an
  empty folder; `uv sync --locked --no-dev --group deploy` installs Flask, its six libraries and gunicorn
  26.2.0, no pytest, with the local uv 0.12.10 **and** with uv 0.13.7, the version Render gives new
  services (its docs, "Setting your uv version"); `uv.lock` stays unchanged. The start command with
  `PORT=10000 CT_PUBLIC=1 CT_PROXY=1 CT_SECRET=…` answers `/` 200 and `/healthz` 200 `ok`
  (`text/plain`, `no-store`, no cookie), `HEAD /healthz` 200, and the log shows no control socket.
- With `CT_PUBLIC=1 CT_PROXY=1 CT_SECRET=…` and `X-Forwarded-Proto: https`: two cookie jars give two
  `.db` files and two separate runs; `/` sets a Secure cookie and HSTS; a static file sets nothing and makes
  no player; `/healthz` answered 404 before this spec; an API call without a cookie is 400; a bad quantity
  is a 400 with our sentence; the editor answers 400 "The editor is off".
- Restart with the same secret: the run is still there. Disk wiped with the same secret: the old cookie
  gets a fresh run (day 1, €100). Disk wiped without `CT_SECRET`: the old cookie is invalid, API 400.

## Check on the first deploy (could not be verified from here)

- That Render's sign-up asks for no card for a free web service (its own pages say no; forum posts
  disagree). If it asks, stop and tell Felix, decision 1's fallback list applies.
- That Render's Python runtime accepts the build command as written. Render's docs: it "automatically
  adds uv to your Python service's runtime" when `uv.lock` is in the root, 0.13.7 for new services, and the
  same command worked locally with 0.13.7 (Measured). If not, the fix is a build setting in the dashboard
  and the same line in `render.yaml`.
- That the proxy forwards to port 10000 (Render's docs: the default port) and the first health check
  passes within Render's 15 minutes.
- Decision 7: what the address bucket really is cannot be seen from outside; the app logs nothing about
  it. It is only a limit on new players, so the worst case is the shared counter described there.

## Security

- The repository is public: `render.yaml` holds names and switches only; the one secret, `CT_SECRET`,
  is made by Render and never leaves it. `data/` (runs and the local key) is already in `.gitignore`.
- The cookie is Secure and HSTS is on only when the proxy says HTTPS (`X-Forwarded-Proto`), and the
  proxy's header is trusted only because `CT_PROXY=1` is set on a service that nothing but Render's
  proxy can reach.
- `/healthz` shows nothing about the game, the host or the version.
- A leaked `CT_SECRET` would let someone sign a cookie for a player id they already know; the ids are 22
  random characters, so the damage is small, but rotating the value in the dashboard is the answer, and it
  ends every session (do it only outside a demo).
- The editor and the weather override stay off in public mode (`deploy-ready`); the smoke test checks it
  on the real address.
