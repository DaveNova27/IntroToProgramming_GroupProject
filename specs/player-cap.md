# A full game makes room (`player-cap`)

Asked for by Felix on 2026-11-21, item A2 of the audit of 2026-11-21. Builds on `deploy-ready` (the cap
of 2,000 runs) and `persistent-runs` (the runs in Postgres).

## Why

The public server keeps at most `MAX_PLAYERS = 2000` runs (`deploy-ready`). A run is made at a new
player's first API call and is never deleted. Once 2,000 runs exist, every new visitor gets 503 "The
game is full right now", for good, until somebody deletes rows in Supabase by hand. Filling it takes no
skill: a new cookie and one `GET /api/state` make a run, and 60 new players per address and minute are
allowed, so one address fills the game in about 34 minutes. The same happens slowly without any attack,
because every browser and every private window makes a run.

## What

1. **When the game is full, the oldest idle run makes room.** A new run that would be number
   `MAX_PLAYERS + 1` first removes the stored run that was changed longest ago, if it has not changed
   for at least `IDLE_BEFORE_REPLACE = 10` minutes; then the new run is made. Only when every stored run
   changed within the last 10 minutes is the answer still 503 "The game is full right now".
2. **One run for one run, one at a time.** At most one run is removed per new run, under the lock that
   already makes new runs one at a time (`_create_lock`), so the cap stays a hard one.
3. **"Changed" is the time of the last save.** Postgres: the column `updated_at` (set by every save,
   already there). SQLite (public mode without `DATABASE_URL`): the file's modification time (every
   save writes the file; loading it does not). Looking at the game (`GET /api/state`) is no change.
4. **Postgres:** one statement removes the row and returns its id; the copy in memory of that player is
   dropped. **SQLite:** the player's file is deleted.
5. **The log** says that a run was replaced and how long it had been idle, never which player.
6. **A replaced player** who comes back starts a new run on day 1, exactly like a player whose run is
   gone; nothing else changes for them.

## Decide

1. **Replace, do not delete on a timer.** Nothing is deleted while the game is not full, so in normal use
   (far fewer than 2,000 players) no run is ever lost. Only a full game replaces idle runs, the one
   changed longest ago first. No clean-up job, no new setting.
2. **10 minutes.** A run that plays a day is saved every second (each tick), so only runs nobody plays
   count as idle. Against one address at the allowed 60 new players a minute, at most 600 runs are
   younger than 10 minutes, far below 2,000: a new visitor always finds a run to replace. A player who
   leaves the game for more than 10 minutes can lose the run only while the game is full.
3. **`MAX_PLAYERS` stays 2,000.** Runs are small (measured: 1.0 KB new, 6.9 KB after 30 days), so the cap
   is about the database, not about room; the problem was that it filled for good.
4. **When a run is made does not change.** The old tests pin that the first `GET /api/state` makes the
   run and counts against the cap (`test_deploy_ready.py`: `test_every_player_has_a_run_of_their_own`,
   `test_the_game_can_be_full`, `test_a_new_run_is_made_one_at_a_time_and_the_cap_is_hard`;
   `test_persistent_runs.py::test_the_cap_counts_the_rows`). They stay true: the runs they make are
   seconds old, so none is replaced. This also answers finding 1 of the review of
   `retire-trade-endpoint` (a refused request makes a run for a new player): such runs are now replaced
   when room is needed.
5. **`NEW_PLAYER_LIMIT` stays 60.** Lowering it waits for audit item B3 (which address the server sees
   behind Cloudflare), else a whole class on one network could be locked out.
6. **No old test changes.** New checks go in the new file `tests/test_player_cap.py`; the Postgres
   checks there run in CI like the others (`TEST_DATABASE_URL`).
7. **After the AI review (2026-11-21):** the log line is a WARNING (Flask writes from WARNING on in
   production, an INFO line would never reach Render's log); when an idle run's lock is held by another
   request (that player, or anybody waiting on the same of the 64 stripes), the next idle run is tried,
   up to `REPLACE_CANDIDATES = 5`, instead of answering "full"; the run locks are reentrant (`RLock`), so
   `load_run` takes its own run's lock itself and a full game may take a stripe the request already
   holds; `deploy-ready.md` and `persistent-runs.md` point to this spec.

## Out of scope

- B2 (the size of a request) and B3 (the address behind Cloudflare): their own specs.
- Making a run only at the first change; a message to a replaced player; a page to clean up by hand.
- The local game (one run on this computer): no cap, nothing changes.

## Done when

1. Public mode with SQLite files and `MAX_PLAYERS = 3`: three runs idle for more than 10 minutes and a
   new player: the run changed longest ago is gone, the new one is there, still 3 runs; the two others
   are unchanged.
2. The same with all three runs changed within 10 minutes: 503 "full", nothing removed.
3. Only idle runs count: with one idle and two fresh runs, the idle one is replaced, the next new player
   gets 503.
4. Hard cap: 8 new players at once with 3 idle runs and `MAX_PLAYERS = 3`: exactly 3 get a run, 5 get 503,
   3 runs stored.
5. A replaced player who comes back gets a fresh run on day 1 (and needs room like any new player).
6. Looking (`GET /api/state`) does not refresh a run's time; a save does.
7. Postgres (CI): the same rule on the rows (`updated_at`), the copy in memory of the replaced player is
   dropped, the log names no player.
8. The full suite passes; no old test changed.

## Security

This removes a cheap way to lock every new visitor out of the public game. It adds no input and no
endpoint; the only data removed is a run that is idle, and only when the game is full. The log line holds
no player id. The SQL uses parameters, like every statement in `pgstore.py`.
