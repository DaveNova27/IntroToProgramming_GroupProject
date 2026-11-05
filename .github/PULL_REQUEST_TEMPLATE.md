## Spec

Closes #<issue number>. Spec file: `specs/<name>.md`

## What changed

Short description. List every file you changed.

## Checklist

- [ ] One spec only, inside its "Out of scope" fence
- [ ] Branch is named after the spec and based on an up-to-date `main`
- [ ] `uv run pytest` passes (paste the final output below)
- [ ] Nothing in `tests/` was edited, deleted or skipped (new test files are fine)
- [ ] Money is integer cents, a rejected action changes no saved data
- [ ] Randomness comes from the seed, state stays complete and settable
- [ ] If the UI changed: checked in the browser (dashboard and map)
- [ ] AI code review done (for example `/code-review`), findings fixed or answered below

## Test output

```
paste the final `uv run pytest` output here
```

## Notes for the reviewer

Anything that is unfinished, risky or needs a decision.
