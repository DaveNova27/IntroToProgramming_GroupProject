# Editor: staff

Issue #83. Found in the audit (`docs/audit-report.md`, item B7). The demo mode (`demo-scenarios`)
needs the whole run to be settable (AGENTS.md).

## What

`logic.editor_set_state` (the patch of `POST /api/editor/state`) takes a new key `employees`: the
list of all employees the run should have, each `{"shop", "place"}` and optionally `"level"`
(1 to 3, default 1) and `"working"` (default true). The list **replaces** all employees: whoever
is not in it is dismissed.

- Every employee sits on a bought place of an unlocked shop (`staff_places`), one per place.
  `shops` in the same patch is applied first, so one patch can buy the places and fill them.
- Someone who already sits on that place stays the same person (same id and name) with the new level
  and `working`. A new person gets a new id (`employee_seq` counts on, an id is never used twice), the
  name and the job (from the place), through the same `_add_employee` as hiring.
- It is not a hire: it costs no money and starts nothing. The patch is refused while a day is open,
  so there is no staffed shift to open.
- Anything else (a bad shape, an unknown or locked shop, a place that is not bought, twice the same
  place, a level outside 1 to 3, a non-boolean `working`) is refused and changes nothing.
- The Editor panel gets a "Staff" block: *Fill empty places* (keeps the team, adds level 1 people),
  *All on top level*, *Dismiss all*.
- Before this, setting a shop's level in the editor gave places without employees (nobody to sell).

## Out of scope

Scenarios and the loader (`demo-scenarios`), the open day in the patch, the history, the staff
numbers (wages, speed, prices), a "hire" through the editor with money.

## Done when

1. `tests/test_editor_staff.py`: levels, `working`, ids, job and name; the same place keeps the same
   person, a dismissed id is not reused, a partial list dismisses the rest, save and load keep it; 14 bad lists are refused and leave the state as it was; places
   must be bought; shops and employees in one patch; the endpoint needs `CT_EDITOR=1` and validates.
2. The Editor panel's Staff buttons work (checked in the browser).
3. `uv run pytest` passes, `tests/` untouched.

Rules: only the editor (local, `CT_EDITOR=1`) can do it; money, randomness and the saved state of a
refused patch are untouched.
