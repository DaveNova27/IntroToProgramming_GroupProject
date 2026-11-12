# Shift in any shop (`shift-any-shop`)

Issue #101. Written and built 2026-11-12. Asked for by David while testing the demo: after
unlocking the Beach Cafe he could not work there himself, "only the normal Cafe" could be played.
This is the limit the roadmap names in `shop-walk` (#40): "Today only the Cafe can be played,
`SHIFT_SHOPS = ("cafe",)`". It is the same in the normal game, not only in the demo.

## What

The player can take a shift in **any unlocked shop**: the Cafe, the Beach Cafe, Merchandise or the
Surf Shop, with or without an employee. A shop without an employee earns nothing until the player
works there or hires someone.

Rules (all in `logic.py`, the browser decides nothing):

1. **One shift at a time, one per shop and day.** A shift lasts 90 of the 300 ticks. While the
   player's own shift runs, no second one can start ("A shift is already running"). When it is over,
   the player can start the next one in **another** shop, as long as a whole shift still fits into
   the day (at most three). A shop worked in today is not offered again.
2. **A shift that holds the slot moves aside.** The player's finished shift goes into
   `shift["extra"][shop]` and stays booked for the day. A staffed shift that holds the player's slot
   (the Cafe with an employee) moves aside the same way and goes on running with its crew. So with
   an employee in the Cafe the player can still work in the Beach Cafe.
3. **Joining a staffed shop.** If the chosen shop already has a running staffed shift, the player
   takes that very shift over (the crew stays, nothing starts again). As today in the staffed Cafe,
   it does not count as `played`.
4. **Guests.** The day's plan stays as it was made when the day opened (home shop and staffed
   shops). A shop outside it plans its guests alone when the shift starts, like a shop staffed
   later in the day (`guests.for_shop`): exactly its normal customers, spread over the shift.
   `SHIFT_SHOPS` keeps this meaning: the player's home shop, where a staffed shift takes the slot at
   once and the day's guests are planned.
5. **Dead end and hints.** Stock in an unlocked shop counts as sellable (the player can sell it).
   For an unlocked shop without an employee (not the home shop), `shop_hint` says "It earns nothing unless you take a shift here yourself" instead of "you cannot
   play a shift here yet".
6. **Day result.** `played` is true when any shift of the player's ran (also one that moved aside);
   wages are paid for every shop that ran. `shop` in the result is the shop of the last shift.

Screen: the Shift panel lists a button for every shop the player can start in now (`shift.choices`
from the server: shop, name, can, done, why; `done` = worked there today, not offered again). Ending
the day asks first when the player's shift is over and another shop could still be worked. It shows before the first shift, after a finished shift, and
under the controls while a crew holds the slot ("You can take a shift in another shop").

## Out of scope

Walking through the shift and figures in the other shops (`shop-walk`, `shop-art`), balancing the
other shops (their margins are placeholders; three shifts a day can earn more than one), the
guests' day plan for shops without employees (Decide 2), a way to end a shift early.

## Decide

1. **Several shifts a day, one after the other** (David chose this over one shift in a shop of
   choice). The day is 300 ticks and a shift 90, so up to three.
2. **The guests' plan stays as it is** (David chose "plans alone" over sending guests to every
   unlocked shop at the start of the day). The ~20 guest tests stay as they are.
3. **Old tests that change** (the old tests say the player cannot play there; this spec changes
   that on purpose). The AI does not confirm test changes; David confirmed these four in the
   session on 2026-11-12 ("ja und ok"). Each with its reason:
   - `tests/test_balance.py::test_a_shop_the_player_cannot_play_says_so_until_it_has_an_employee`,
     now `test_a_shop_without_an_employee_says_the_player_can_take_the_shift_until_it_has_one`: a
     locked shop has no hint, an unlocked one without an employee says "take a shift here yourself"
     (the Cafe, the home shop, stays silent as before). Reason: the hint's premise ("you cannot play
     there") is what this spec removes.
   - `tests/test_balance.py::test_stock_nobody_can_sell_does_not_save_the_player_from_the_dead_end`,
     now `test_stock_in_a_shop_without_an_employee_is_no_dead_end_because_the_player_can_sell_it`:
     beer in the unstaffed Beach Cafe is not a dead end; with no stock and no cash it still is.
   - `tests/test_balance.py::test_the_hint_tells_a_stopped_employee_from_a_missing_place`: the
     second check unlocks the shop first (a locked shop has no hint); the text is "buy an
     employee place" (lower case).
   - `tests/test_shop_process.py::test_other_shops_unknown_ids_and_a_second_shift_are_refused`: the
     refusal of a shift in the unlocked Beach Cafe is replaced by one in a locked shop (the Surf
     Shop); the Beach Cafe shift is tested in `tests/test_shift_any_shop.py`. The bad ids and the
     second shift in the Cafe stay refused.

## Built

- `logic.py`: `_check_start`, `shift_options`, new `start_shift` (new / move aside / join),
  `_player_worked`, `_runs`, `shop_hint`.
- `app.py`: `shift_view` sends `choices`.
- `static/world/ui.js`: the Shift panel (`startChoices`).
- `tests/test_shift_any_shop.py` (new, 11 checks).
- Checked in the browser: the Beach Cafe without an employee unlocked in the demo's last
  scenario, the day opened, a shift taken there, beer sold, no 400, no console error. With the
  Cafe staffed (the demo state) the panel offers the Beach Cafe under "You can take a shift in
  another shop".
