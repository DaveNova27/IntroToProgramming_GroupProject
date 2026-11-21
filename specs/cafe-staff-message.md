# The right reason when employees run the Cafe (`cafe-staff-message`)

Asked for by Christopher on 2026-11-21, item B1 of the audit of 2026-11-21. Builds on `staff` and
`shift-any-shop`.

## Why

The Cafe is the home shop (`SHIFT_SHOPS = ("cafe",)`). When it has a working employee, `open_day`
starts its staffed shift in the player's slot (`state["shift"]["shop"] == "cafe"`, `staffed`). The
shift options then say for the Cafe: `can: False`, `done: True`, "You are working in the Cafe already."
That is not true: the employees work there, the player has not started anything.

The audit read this as "the player can never work in the Cafe". Checked on 2026-11-21: that part is
not so. The Shift panel shows the Cafe's rows (Fill, Sell) for the shift in the slot, and the server
accepts the player's refills and sales there, beside the crew, exactly as after taking over another
shop's staffed shift (`shift-any-shop`: the crew stays). Only the reason is wrong. The panel does
not draw it (options marked `done` are left out), it is the answer to a start in the Cafe that is
refused, and it is in `shift.choices` of every state answer.

## What

1. `_check_start` tells a staffed shift in the slot apart from the player's own:
   - running: "Employees run the Cafe. You can serve here beside them."
   - over: "The shift in the Cafe is over for today."
   The same holds for a crew's shift that moved aside (`extra`, for example the Cafe crew after the
   player started the Beach Cafe) and has ended: "The shift in the Cafe is over for today." instead of
   "You already worked in the Cafe today."
2. The player's own shift keeps its messages ("You are working in the Cafe already.", "You already
   worked in the Cafe today.").
3. Nothing else changes: the start in the Cafe is still refused (the player already serves there),
   `shift_options` still marks it `done` (the panel shows its rows, not a start button), no rule, no
   number, no screen code.

## Decide

1. **Only the message (Christopher, 2026-11-21).** Making the Cafe a "join" like the other staffed
   shops would give it `can: True`, and the panel would draw a "Start shift in the Cafe" button under
   the Cafe's own rows. That needs a change of the screen two days before the deadline, for no new
   possibility: the player can serve there already.
2. **After the AI review (2026-11-21):** the crew's ended shift in `extra` gets the same fix (it said
   "You already worked" too); the text names the shop without a possessive ("The shift in the …"), so
   it reads well for every shop. Answered, not changed: the staffed Cafe stays `done` in the options
   (that keeps the panel from drawing a start button under the Cafe's own rows, decision 1); the test
   helper `advance` is copied from `test_shift_any_shop.py`, so no other test file changes.
3. **No old test changes.** No test pins the old text. New checks go in
   `tests/test_cafe_staff_message.py`.

## Out of scope

- A real takeover of the home shop (`can: True`), a change of `played` or of the wages.
- The stock window during a shift and the "+0" button (audit B6), the price message (audit C2).
- The size of requests and the address behind Cloudflare (`request-limits`).

## Done when

1. A Cafe with a working employee, day opened: the Cafe's option says "Employees run the Cafe. You can
   serve here beside them.", `can` false, `done` true; a crafted start there is refused with that
   text and the state is unchanged.
2. The player refills and sells in that Cafe shift (the server accepts both).
3. After the staffed Cafe shift is over: "The shift in the Cafe is over for today."; the same after
   the Cafe crew moved aside for the player's Beach Cafe shift and both have ended.
4. Without staff, the player's own Cafe shift keeps "You are working in the Cafe already." and,
   once over, "You already worked in the Cafe today."
5. The full suite passes; no old test changed.

## Security

No new input, no new endpoint, no rule changes: only the text of a refusal.
