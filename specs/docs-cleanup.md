# The docs cleaned up (`docs-cleanup`)

Asked for by Felix on 2026-11-23 ("die Doku des Repos aufräumen"; after reading this spec: "alle Punkte
umsetzen außer das mit dem Audit, plus README nicht zu kurz machen"), the rest of item D3 of the audit of
2026-11-21. Builds on `docs-refresh` and `docs-sync`.

## Why

The long documents have grown spec by spec and now say things that are no longer true:

- **`README.md`** (216 lines, 34 KB). The spec table has 63 rows with a median of 274 characters (the
  longest is 711). Its rows are not in order (`client-address` stands before `docs-refresh`). The
  Branch column mixes branch names, PR numbers and "Merged (#50):". Its heading says "all implemented",
  but it also lists dropped and replaced specs.
  - Wrong fact: "one shift per day" (Known issues) no longer holds since `shift-any-shop`: one shift
    per shop, several a day. (The 300 ticks of an opened day are right: `logic.OPEN_DAY_TICKS`.)
  - The Server row lacks seven of the API's routes: `/api/buy-many`, `/api/day/open`,
    `/api/day-override` and the four `/api/shift/*` routes.
  - The roadmap link points to section 4.1 for the open specs.
- **`docs/feature-roadmap.md`** is v6, "state of 2026-11-10/11".
  - Its built table stops at `demo-scenarios` (#96).
  - Its open specs (4.1) and issue status (5) still list `popularity`, `deploy`, `outfits`, `shop-art`
    and `map-layout` as open; all are merged and their issues closed.
  - "The game today" still says "the one shift of the day".
  - David's PR #109 (3 lines, `weather-visuals` moved to built) has been open since 2026-11-15.

## What

1. **README tidy and true, not short.**
   - Same sections, in this order:
     - About;
     - Group;
     - Run (with the demo and the deployed URL);
     - Putting it online;
     - How it fits together;
     - Working in the group;
     - Specs;
     - Known issues and ideas.
   - The sections keep what they explain; only what is wrong or said twice goes.
   - The spec table is split into groups (solo project, game rules, campus and look, server and
     deploy, docs and housekeeping). Inside a group the specs run in build order, with one PR column.
   - Each spec keeps what it does and its key numbers, in at most 400 characters. Today's longest rows
     are cut; the others stay as long as they are.
   - Dropped and replaced specs stay in the table, marked as such.
   - The Server row names every route of `app.py`.
   - Every known issue is checked against the code; what is no longer true goes, and what is true
     stays.
2. **Roadmap brought to the state of today (v7, 2026-11-23).**
   - The built table gets every spec merged since #96.
   - The open specs and the issue status list only what is really open: issues #11 `nova-design`,
     #20 `staff`, #24 `final-polish`, #40 `shop-walk`, plus the specs that still have no issue
     (`disruptions`, `warehouse`).
   - Decisions and next steps that are done are marked done.
   - "The game today" says one shift per shop.
   - Part B does not change (it is the game design reference).
3. **`AGENTS.md`** says to read Part B of the roadmap (the game design) and its security rules
   (section 3) before a spec, and that the open work is in the GitHub Issues (label `spec`). Everything else in it stays.
4. **`tests/test_docs_cleanup.py`** checks that it stays true:
   - no "one shift per day" or "the one shift of the day" in the README or the roadmap;
   - every route of `app.py` named in the README;
   - every spec row at most 400 characters of description;
   - the roadmap's header agrees with itself and lists nothing as both built and open.

## Decide

1. **Text only.** No game code, no rule, no old test changes. The old checks on the README
   (`test_docs_refresh.py`, `test_docs_sync.py`) keep passing as they are. They hold:
   - every spec named in the README;
   - the dropped row;
   - the known-issue sentences they name;
   - "Felix Anthes" twice.
2. **The spec files are not touched.** They are the history of each feature; the README's table says
   which are dropped or replaced.
3. **PR #109.** David's three lines are true and fit this spec. It was still open when this branch was
   built, so this spec makes the same three changes; #109 can then be closed with a note that thanks
   him (Felix decides).
4. **The old audit (`docs/audit-report.md`) is not touched** (Felix). The audit of 2026-11-21 does not
   go into the repo either (it names security details).
5. **`checks/` stays where it is** (as in `docs-sync`, Decide 2).
6. **After the AI review (2026-11-23), all eight findings fixed:**
   - `AGENTS.md` names the security rules of section 3 (3a, 3b) next to Part B, since the PR template
     asks for them.
   - The README's copy tip lists `pgstore.py` (`app.py` imports it).
   - The roadmap's header says "with PR #145", like its built table.
   - `tests/test_docs_cleanup.py` checks rules that stay true instead of today's values:
     - the sections present and in order (more are fine);
     - the version in the title equal to the one in the status line;
     - no spec both built and open, and no issue both open and closed;
     - routes read from Flask's route table.
     
     Closing an issue or writing roadmap v8 needs no change to it. It finds its tables at test time,
     so a renamed heading fails one check with a message instead of the whole file. It no longer
     repeats `test_docs_refresh.py` (every spec named); it checks that no row links to a missing spec.
   - PR #109 changes the same roadmap lines: close it once this is merged, or it will conflict.

## Out of scope

- Branches (D5) and issues (D6). These are clicks on GitHub, not files.
- Moving `checks/` (D2).
- The spec files.
- The old audit report.
- The PR and issue templates.
- Game code.
- Every other audit item.

## Done when

1. The README has the sections above. The spec table is grouped with one PR column, at most 400
   characters of description per spec.
2. The README and the roadmap no longer say "one shift per day". Every route of `app.py` is named in
   the README's Server row.
3. The roadmap is v7 of 2026-11-23 and lists no closed issue as open. `AGENTS.md` points to Part B,
   section 3 and the Issues.
4. `tests/test_docs_cleanup.py` passes; the full suite passes; no old test changed.

## Security

Documentation only. No address, secret, connection string or detail of the audit of 2026-11-21 goes
into the repo.
