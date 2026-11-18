# README up to date, CI actions pinned (`docs-refresh`)

Asked for by Felix on 2026-11-18, before the presentation: the README is what the walkthrough opens
first, and parts of it no longer match the game. The two small security gaps of the rubric check (CI
actions not pinned, no Dependabot) are closed in the same go. No game code changes.

## What

1. **The name (`README.md`):** "Felix Antes" → "Felix Anthes", in the members table (line 20) and in the
   description of the campus (line 112).
2. **The spec list (`README.md`):** a row for each built spec that is missing, in the style of the
   others (file, branch with PR number, two or three sentences from the spec): `click-walk`,
   `hidden-weather`, `map-view`, `outfits`, `smooth-walk`, `merch-wear`, `order-at-warehouse`,
   `bulk-order`, `lorry-road`. The four specs of the first draft (`employees`, `investments`,
   `multi-business`, `net-worth`) get one row together, marked dropped, as their files say.
3. **"Known issues and ideas" (`README.md`):** only what built specs contradict:
   - the idea "customers of the Merchandise shop wear the clothes when they leave" is built
     (`merch-wear`, #117): out of the ideas;
   - the Mercado Supply Hall is no longer a place without a rule: stock is ordered at its PC
     (`order-at-warehouse`, #118);
   - the Cafe and the Merchandise shop in the Nova are no longer "places only": guests walk there and
     queue (`PLACES["shops"]` in `world.py`), and the employees' figures stand in the Cafe
     (`WORK_SPOTS`). Found while building: the spec first named only the Cafe; the Merchandise shop
     is a guest destination too. The printers stay "decoration only".
   Everything else in the section was checked and still holds (for example "Only the Cafe has figures in
   the world so far": `WORK_SPOTS` has only the Cafe), so it stays.
4. **CI actions pinned (`.github/workflows/tests.yml`):** each `uses:` names a full commit SHA with the
   version as a comment, the same versions as today:
   - `actions/checkout@11d5960a326750d5838078e36cf38b85af677262 # v4.4.0` (what `v4` points to)
   - `astral-sh/setup-uv@caf0cab7a618c569241d31dcd442f54681755d39 # v3.2.4` (what `v3` points to)
   The job id `pytest` (the required check of `main`) and everything else in the file stay.
5. **Dependabot (`.github/dependabot.yml`, new):** weekly update checks for the Python packages
   (`uv`, the lock file `uv.lock`) and for the GitHub Actions, at most 3 open PRs each. Its PRs go
   through the same `pytest` check and are merged by a member like every PR.

## Decide

1. **Same versions, only pinned:** no upgrade of the actions in this spec (an upgrade could change the
   CI just before the deadline); Dependabot proposes upgrades as their own PRs.
2. **Dependabot weekly, 3 PRs at most:** enough to see security fixes, not so many that PRs pile up in
   the last week. Nobody has to merge them before the deadline.
3. **README only where it is wrong or missing:** no rewrite of sections that are right; the roadmap
   (`docs/feature-roadmap.md`) waits for David's PR #109.
4. **Tests:** the new file `tests/test_docs_refresh.py`. No old test changes. The tests check that every
   action is pinned to a full SHA with a version comment and which actions are used, not the SHAs
   themselves: otherwise every Dependabot update of a pin would fail the `pytest` check.

## AI review findings (fixed)

1. Dependabot would also propose major upgrades of the actions (setup-uv v3 to today's major), whose
   changed defaults can break the CI: major versions are ignored for both ecosystems.
2. A merged update of `uv.lock` goes to the live site at once (`render.yaml` deploys `main`): major
   versions are ignored there too, and the file and the PR say not to merge Dependabot PRs before the
   presentation.

## Out of scope

- `docs/feature-roadmap.md`, open issues, old branches.
- Any change to the game, the tests in `tests/` or the dependencies themselves.

## Done when

1. **README:** the name is right in both places; every spec file in `specs/` is named in the README; the
   three outdated points are fixed.
2. **CI:** every `uses:` in `.github/workflows/` is pinned to a 40-character SHA; the job id is still
   `pytest`; the `Tests` check passes on the PR.
3. **Dependabot:** `.github/dependabot.yml` is valid (version 2, the ecosystems `uv` and
   `github-actions`, weekly).
4. **Tests:** `tests/test_docs_refresh.py` checks 1 to 3 in the files; the full suite passes.

## Security

Pinning to a commit SHA means a moved or hijacked tag cannot change what runs in our CI. Dependabot
only opens PRs; nothing is merged or deployed without the `pytest` check and a member. No secret is
added anywhere.
