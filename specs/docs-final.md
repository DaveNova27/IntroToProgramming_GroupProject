# Docs for the submission (`docs-final`)

Written 2026-11-23 by David, a few hours before the submission (2026-11-23, 23:59). Docs only, no
game code.

## What

1. **The old audit report goes.** `docs/audit-report.md` (the audit of 2026-11-09, PR #72) is removed
   from the repository, as David asked. It stays in the git history. The README no longer points to it;
   the roadmap says where it went (section 1 and the "To open" row of section 5). The old specs that
   name it as the source of a finding are history and stay as they are.
2. **The docs name the demo day.** The roadmap still described the demo as "four prepared days":
   section 1 (the game today, the built table), 1a (course requirements), 2 (decisions), 3b (security
   per spec) and 5 (issue status, now after PR #146 with #147 `demo-day`) are brought up to date.

## Decide

1. **The audit goes, against an earlier decision.** In `docs-cleanup` (PR #145, Decide 4) Felix decided
   that the old audit is not touched. David asked on 2026-11-23 to take it out. The report is in the
   history (`git show 80a0d3d:docs/audit-report.md`), so nothing is lost. If the team wants it back, a
   revert of this PR brings it back.
2. **Old specs unchanged.** Ten specs name `docs/audit-report.md` as the source of their finding. They
   record what was true when they were written, like a commit message; rewriting them would change
   history, not documentation.

## Out of scope

Game code, tests, the other docs, the open issues (#11, #20, #24, #40), the Dependabot PR (#125).

## Done when

- `uv run pytest` passes (output in the PR); nothing in `tests/` changed.
- No file outside `specs/` and git history names `docs/audit-report.md`.
- README spec table names this spec; issue and PR opened; AI code review done.
