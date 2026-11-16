# Persistent runs (`persistent-runs`, issue #112)

Agreed by Felix on 2026-11-16 ("1. ich lege das supabase projekt an. 2. ja das passt", local Postgres
allowed, "issue: anlegen", building while he creates the Supabase account). Follows `deploy` (#93, PR #110/#111): the game is live at
https://campus-tycoon.onrender.com, but Render's free plan erases every run on restart, deploy and
after 15 minutes without visitors. The team decided on 2026-11-16 that runs must be kept, with Supabase
(David's proposal), after the deploy and as its own spec.

Every fact about Supabase and Render below was read on their own pages on 2026-11-16; every number
about our app was measured on this repository. What could not be checked from here is listed under
"Check on the first deploy".

## What

On the public server every player's run is stored in a **Postgres database at Supabase** (region
Frankfurt), so it survives restarts, deploys and idle spin-downs of the Render service. Locally and in
every existing test nothing changes: without the variable `DATABASE_URL` the game uses SQLite exactly as
today.

### When Postgres is used

Only when **both** `CT_PUBLIC=1` and `DATABASE_URL` are set (the public server). Local play
(`uv run python app.py`) has one run and no player ids and stays on `data/campus_tycoon.db`, also when
someone has `DATABASE_URL` in their shell. The tests never set `DATABASE_URL`; the Postgres tests use
their own variable `TEST_DATABASE_URL` (below), so no existing test can reach a database by accident.

### The table

One table in a schema of our own, created by the app on first use (`CREATE ... IF NOT EXISTS`, so a
second start changes nothing):

```sql
CREATE SCHEMA IF NOT EXISTS campus_tycoon;
CREATE TABLE IF NOT EXISTS campus_tycoon.runs (
    player_id  text PRIMARY KEY CHECK (player_id ~ '^[A-Za-z0-9_-]{22}$'),
    state      jsonb NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE campus_tycoon.runs ENABLE ROW LEVEL SECURITY;          -- no policies: the Data API sees nothing
REVOKE ALL ON SCHEMA campus_tycoon FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA campus_tycoon FROM PUBLIC;      -- and from anon, authenticated if they exist
```

A run is **one JSON document**: the whole state dict that `logic.py` already works with (a fresh run is
993 bytes, a finished 30-day season 7,897 bytes, measured; both survive `json.dumps`/`json.loads`
unchanged). One save is one `INSERT ... ON CONFLICT (player_id) DO UPDATE`: a single statement, so it
is written whole or not at all, like the one SQLite transaction today.

### The same rules as SQLite, from the same code

The SQLite tables are also the last guard of the state: their `CHECK`s refuse negative cash or stock, a
price of 0, two employees on one place; `db.load` drops products, shops, jobs and badges that no longer
exist after a code change, caps a price far above the reference, moves a player whose zone is gone. A
JSON document would skip all of that. So **every state goes through SQLite in memory** on its way in
and out of Postgres:

- `db.py` gets a mechanical split: the body of `load()` moves into `_read(conn)` (`load(path)` opens the
  file and calls it, behaviour unchanged), and a new `db.through_sqlite(state)` writes the state into a
  fresh in-memory SQLite database with the existing `_write` and reads it back with `_read`.
- Saving to Postgres: `through_sqlite(state)` first. A state that breaks a `CHECK` raises before anything
  is sent (nothing saved, 500 with our sentence, as today). What is stored is the state as SQLite would
  load it.
- Loading from Postgres: the JSON goes through `through_sqlite` too, so a run saved before a later change
  of the catalogue, the shops or the map is repaired exactly as an old SQLite file is.

No rule is written twice; the 220 existing calls of `db.load`/`db.save` in the tests keep guarding it.

### A copy in memory (why, and why it is safe)

Supabase's free plan includes 5 GB of egress a month (pricing page). If every request loaded the run
from the database, a player in the demo (2 ticks a second, `tick_ms` 500) would read about 8 KB × 120 a
minute, roughly 60 MB an hour: 5 GB would be about 85 player-hours. So the server keeps the runs it has
loaded in a dictionary (at most 500, the least recently used one is dropped and simply loaded again):

- **Read:** from memory; from Postgres only the first time after a start, or after the run was dropped.
  Every read hands out a deep copy and every write stores one, so a rule that changes a dict in place
  and is then refused can never change the copy (a rejected action changes no saved data).
- **Write-through:** every save goes to Postgres first, and only when that worked is the copy in memory
  replaced. A failed save leaves both as they were.
- **Safe because there is exactly one process:** one gunicorn worker (`deploy-ready`, `render.yaml`) and
  one Render instance (the free plan cannot scale). Every change of a run already happens under that
  player's lock (`run_lock()`), so nobody can read a half-written copy. If the app ever ran more than
  one worker, this copy would be wrong; the existing test of `render.yaml` (`-w 1`) guards it.

### Connecting to Supabase

- **Session pooler**, not the direct connection: on the free plan the direct connection is IPv6 only,
  the shared pooler is IPv4 on every plan; Supabase recommends session mode for "a persistent backend
  on an IPv4-only network" (Supabase, "Connect to your database"). Session mode also supports prepared
  statements, so the driver needs no special setting. Whether Render's free plan can reach IPv6 I did not
  check, and with the session pooler it does not matter.
- The connection string comes from the Supabase dashboard (*Connect* → *Session pooler*); its host and
  user name cannot be made up from the region. It contains the database password: it is a **secret**,
  entered only in Render's dashboard as `DATABASE_URL`, never in the repository, never in a log line.
- **TLS:** the app adds `sslmode=require` when the string has no `sslmode` (Supabase: "Most drivers
  default to prefer, which falls back to sending your data in plaintext").
- **Driver:** `psycopg[binary]` 3.3 (3.3.9 on 2026-11-12; wheels for Linux x86_64 and macOS arm64) and
  `psycopg-pool` 3.3 (3.3.3, 2026-09-22), both in the main dependencies of `pyproject.toml` (the tests
  in CI need them too) and pinned in `uv.lock`. A pool of 1 to 4 connections (one worker, 8 threads),
  each connection checked before use, so a connection the pooler closed while idle is replaced
  instead of failing a request; a request waits at most 5 seconds for a connection.

### When the database cannot be reached

A paused Supabase project, a network problem or a wrong password: every API call answers **503**
"The game's storage cannot be reached right now. Nothing was saved. Try again in a minute." (JSON like
every API answer), the details go to the server log without the connection string. Nothing is half
saved: the copy in memory changes only after a successful write. The page itself still loads.
`/healthz` does **not** ask the database: a restart cannot fix a paused database, and a failing health
check would only make Render restart the service in a loop.

### What changes in the code

| File | Change |
|---|---|
| `pgstore.py` (new) | The Postgres store: `enabled()`, `load(player_id)`, `save(state, player_id)`, `exists(player_id)`, `count()`, the schema, the pool, the copy in memory, `Unavailable` |
| `db.py` | `load()` split into `load(path)` + `_read(conn)` (no behaviour change); new `through_sqlite(state)` |
| `app.py` | One place decides the store (`_in_postgres()`): `load_run()` and the seven `db.save`/`db.save_new_run` calls go through `_load_stored`, `_save_run`, `_save_new_run`, `_run_exists`, `_run_count`; the cap of 2,000 runs counts rows instead of files; `Unavailable` answers 503 |
| `pyproject.toml`, `uv.lock` | `psycopg[binary]>=3.3,<3.4`, `psycopg-pool>=3.3,<3.4` |
| `.github/workflows/tests.yml` | A `postgres:17` service for the job `pytest` (its id stays, the branch protection depends on it) and `TEST_DATABASE_URL` for the Postgres tests |
| `tests/test_persistent_runs.py` (new) | See "Done when" |
| `README.md`, `AGENTS.md`, `specs/deploy.md` link | Where the data is stored now, how to reset it, the walkthrough answer |

`save_new_run` needs no own Postgres code: SQLite keeps old days on a normal save and deletes them only
for a new run; a JSON document is always written whole, so a new run simply replaces it.

## Decide

The ones marked ► were answered by Felix on 2026-11-16; the rest follows from the facts above.

1. **► Who creates the Supabase project: Felix.** An account, a project named e.g. `campus-tycoon` in
   *Central EU (Frankfurt)* (`eu-central-1`, the region nearest to Render's Frankfurt), a strong
   database password kept in a password manager. The free plan allows 2 active projects. Whether the
   sign-up asks for a card I did not check (the pricing page does not say). I never create accounts,
   type passwords or copy the connection string; those clicks are the account owner's (Felix or David).
2. **► The pause rule: accepted.** "Free projects are paused after 1 week of inactivity" (pricing page).
   Paused, the game answers 503 until someone presses *Restore* in the Supabase dashboard. Playing on
   the public URL counts as activity; the README gets a line: "open the game at least once a week, and
   check the Supabase dashboard the day before the demo".
3. **► No backups** (explained to Felix on 2026-11-16, his answer pending; it changes no code).
   "Automatic backups: not included in free" (pricing page). If the project is deleted or broken, the runs
   are gone; for a course project that is acceptable.
4. **`DATABASE_URL` only in Render's dashboard, not in `render.yaml`.** Render keeps environment
   variables that the Blueprint does not mention ("Render preserves existing environment variables,
   even if you omit them from the Blueprint file", Blueprint reference). Writing it into `render.yaml`
   as `sync: false` would change two tests of `deploy` (`test_the_variables_are_exactly_the_ones_of_the_spec`,
   the check that the file has no `sync: false`), and old tests change only with a reason; this one
   has none. The README names the variable.
5. **JSON document instead of the ten SQLite tables in Postgres.** Same state, one statement per save,
   no second set of table definitions to keep in step; the tables' rules stay in force through
   `through_sqlite`. Querying single fields in Postgres is not needed by the game.
6. **The Data API stays out:** our own schema (a custom schema reaches the Data API only after it is added
   to *Exposed schemas* in the API settings and granted to `anon` and `authenticated`, Supabase, "Using
   custom schemas"), RLS on with no policy ("RLS with no policies denies every request"), and the grants
   revoked. Three locks on one door, because Supabase's defaults grant new objects in `public` to `anon`
   (Supabase, "Securing your API"). Recommended click for the account owner, not required: Data API
   settings → turn off *Automatically expose new tables*.
7. **`sslmode=require`, not `verify-full`.** `require` encrypts; `verify-full` would also check the
   server's certificate but needs Supabase's root certificate file from the dashboard in the repository.
   Possible later, not needed for the course.
8. **Local tests of Postgres.** In CI the Postgres tests always run (service container). On a laptop
   they run when `TEST_DATABASE_URL` points at a Postgres; without it they are skipped with the reason
   "no test database" (like the Node tests without Node). Felix' laptop has no Postgres; the official
   macOS binaries (EDB, `postgresql-17.8-1-osx-binaries.zip`, 360 MB) go to `~/Claude/tools` like Node
   (Felix' yes on 2026-11-16), so the Postgres tests run locally too.
9. **No old test changes.** All new checks in `tests/test_persistent_runs.py`.

## Out of scope

Accounts and login (Supabase Auth); one run on several devices; moving local SQLite runs to Supabase;
deleting old runs (2,000 runs × 8 KB is far below the 500 MB of the free plan); backups; `verify-full`;
Supabase's Data API, Realtime or Storage; a second worker or instance; the bugs of the test report
(own specs).

## Done when

**A. In the pull request (`persistent-runs`)**

1. `db.py`: `load` split, `through_sqlite` added; all existing tests pass unchanged.
2. `pgstore.py`, the `app.py` wiring and the 503 answer as described; `pyproject.toml`/`uv.lock` pinned.
3. `tests/test_persistent_runs.py`:
   - without a database (run everywhere): `through_sqlite` gives exactly what `save` + `load` of a file
     give, for a fresh run, a full season, staff, a demo scenario, a run with a removed product, shop,
     badge and zone; a state that breaks a `CHECK` raises in `through_sqlite`; Postgres is used only with
     `CT_PUBLIC=1` **and** `DATABASE_URL`; local mode with `DATABASE_URL` set stays on SQLite;
     `sslmode=require` is added only when missing; an unreachable database answers 503 with our
     sentence, does not contain the connection string, and `/healthz` stays 200;
   - with `TEST_DATABASE_URL` (CI): the schema is made once and a second start changes nothing; RLS is on;
     `anon` and `authenticated` (created in the test database) cannot read the table; save + load give
     the same state; a new run replaces the old one; a rejected action changes nothing in the row;
     two players have two rows; the cap counts rows; a "restart" (copy in memory cleared) gives the same
     run back from Postgres; a failed write leaves the copy in memory unchanged; the copy is read from
     memory the second time (no second query).
4. CI runs the Postgres tests (the workflow's service), and they pass there; the complete suite passes
   locally (with Node), output in the PR.
5. README ("Where is the data stored?", the variable, the pause rule, reset), `AGENTS.md` (storage and
   reset), roadmap; spec row.
6. AI review (`/code-review` high) done, findings fixed or answered.

**B. After the merge (the account owner; I prepare the checklist, never the sign-in or the secret)**

7. Supabase project in Frankfurt; *Connect* → *Session pooler* → copy the string with the password.
8. Render dashboard → `campus-tycoon` → *Environment* → add `DATABASE_URL` (secret) → save; Render
   redeploys.
9. Smoke test: play day 1, note day and cash; *Manual Deploy*; reload: **the same day and cash** (the
   point of this spec). Leave it 16 minutes, reload: still the same. A second browser: its own run. In the
   Supabase table editor: one row per player, nothing readable through the Data API (`anon`).

## Measured

- State as JSON: fresh run 993 bytes, finished season 7,897 bytes (SQLite file of the same season:
  77,824 bytes); `json.loads(json.dumps(state)) == state` for both.
- `app.py` reaches the store in one function (`load_run`) and seven save calls, all through `_db_kw()`;
  three test files set `app.PLAYERS_DIR`, none sets `DATABASE_URL`.
- PyPI on 2026-11-16: psycopg 3.3.9 (2026-11-12), psycopg-pool 3.3.3 (2026-09-22), both
  `requires_python >=3.10`.
- Built, against a local PostgreSQL 17.8 (official EDB binaries, signed by EDB) on 127.0.0.1: the whole
  suite with Node and `TEST_DATABASE_URL` set, nothing skipped. An outage by hand: a run saved, the
  database stopped: the next load waits 5 seconds and raises `Unavailable` (cause `PoolTimeout`); the
  database started again: loads work after 2.3 seconds, without restarting the app. The pool's log lines
  name host and port, never the password; a malformed `DATABASE_URL` would have been quoted in part by
  psycopg's error, so it is caught and logged as "not a valid connection string".

## Check on the first deploy (could not be verified from here)

- Whether Supabase's sign-up asks for a card.
- That Render reaches the session pooler (IPv4, port 5432) and the first request after a deploy takes
  well under a second for a known player (one query, then memory).
- How Supabase counts egress for database reads exactly (the pricing page names 5 GB of egress for the
  free plan; the copy in memory keeps reads to about one per player and start either way).

## Security

- The connection string is a password: only in Render's dashboard; the app never prints it (errors say
  only that the storage cannot be reached); no file of the repository holds it, and no `.env` file is
  used.
- The table is invisible to Supabase's Data API (own schema, RLS without policies, grants revoked); the
  app connects as the database owner through the pooler.
- `player_id` is the random 22-character id from the signed cookie (`deploy-ready`); the table refuses
  any other shape. A cookie we did not sign still makes no run.
- TLS is required for the connection.
- The run holds no personal data (no names, no addresses: a game state and a random id); it lives in the
  EU (Frankfurt).
