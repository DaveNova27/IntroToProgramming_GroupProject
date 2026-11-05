---
name: Spec
about: One feature/spec to build on its own branch
title: "[spec] "
labels: spec
assignees: ""
---

## Roadmap entry

Name from `docs/feature-roadmap.md` (section 7), e.g. `day-context`.
Track: logic / visuals / end.

## Depends on

Other specs that must be merged first, or "none".

## Spec file

`specs/<name>.md` (create it on this issue's branch, in the same PR)

## Branch

`<branch-name>` (same as the spec name)

## What

Two or three sentences: what the player or the code can do afterwards.

## Out of scope

What this spec explicitly does not cover.

## Done when

- [ ] Spec file in `specs/`
- [ ] Implementation on its own branch
- [ ] Tests added and passing (`uv run pytest`), `tests/` untouched
- [ ] Follows the three roadmap rules (settable state, overridable day context, seed-only randomness)
- [ ] PR opened against `main`, AI code review done and its findings handled
