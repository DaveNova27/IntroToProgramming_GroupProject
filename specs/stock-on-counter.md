# The stock card counts the counter too (`stock-on-counter`)

Issue #138. Asked for by Christopher on 2026-11-21, item B6 of the audit of 2026-11-21. Builds on
`shop-process` (storeroom and counter), `staff` (crews with counters of their own) and
`stock-by-shop` (the stock card grouped by shop).

## Why

1. **The stock card shows 0 although the player has coffee.** During a shift the player moves units
   from the storeroom to the counter (`refill`). The stock card shows only the storeroom
   (`state["stock"]`), so after "Fill" it says "Coffee 0" while 16 coffee stand on the counter. At the
   end of the day the unsold units go back to the storeroom, so they are the player's all the time.
   The same 0 makes the "Order" button glow ("you have nothing left").
2. **A "+0" button.** In the Shift panel the small refill button is "+N" with N = min(5, storeroom,
   room on the counter). When nothing can move, it is drawn as a disabled "+0", which reads like a
   broken button.

## What

1. **The server counts the counter.** Each product in the state answer gets `on_counter`: the units of
   that product on the counters of the open day, the player's shift and every crew's shift beside it
   (`shift.extra`). 0 without an open day. `stock` stays the storeroom.
2. **The stock card shows what the player holds.** The number is `stock + on_counter`; when
   `on_counter` is more than 0 the small line under the name ends with "· N on the counter".
3. **The same total** for the glow of the "Order" button (it glows only when the player holds nothing
   at all), for the "N in stock" badge of each product on the dashboard and for the dashboard's stock
   tile ("N units in stock", before "on the shelf"; the euro value beside it, `stock_value`, always
   counted the counter), so both screens agree.
4. **No "+0".** The Shift panel leaves the "+N" button out when N is 0; an empty cell takes its place
   in the row's grid, so "Fill" and "Sell" stay at the end of the row (each row is a grid of its own,
   so this is no alignment across rows). "Fill" and "Sell" stay as they are, disabled when they can do
   nothing.

## Decide

1. **The server adds, the screen shows.** The browser decides no rule (AGENTS.md); a sum over the
   counters of all shifts is data of the state, so the server sends it like `stock`. The screen only
   adds the two numbers it was given.
2. **Total, not storeroom.** What the player wants to know on the card is "how much do I have", and
   that is the storeroom plus the counters (both come back at the end of the day). The Shift panel
   still says "storeroom N · counter M" for the shop being played.
3. **Out of the morning card.** Before the day opens there is no counter, so it is unchanged.
4. **The order window keeps "you have N" of the storeroom.** `test_bulk_order.py` pins that text
   (`you have ${esc(x.stock)}`), and old tests stay as they are; during a shift the window is used
   less, so this waits for after the deadline.
5. **No old test changes.** New checks go in `tests/test_stock_on_counter.py`.
6. **After the AI review (2026-11-21):** the sum is a rule in `logic.py` (`units_on_counter`, built on
   `_shift_parts` like `_counter_units`), the view only passes it on; the dashboard's "in stock" badge
   shows the same total (it said 0 during a shift too); the crew test waits for the crew's first refill
   instead of a fixed 5 ticks. Answered, not changed: the screen tests read the source of `ui.js`, as
   the other page tests of the project do.
7. **After Felix' review (2026-11-21):** the dashboard's stock tile counts the counter too and says
   "in stock" (it said "on the shelf" with the storeroom only, next to a euro value that counted the
   counter); the comment and this spec no longer promise that the empty cell lines up the columns of
   all rows. "you have N" in the order window stays the storeroom (Decide 4): changing it would change
   the old test `test_bulk_order.py:184`, and Christopher decided to leave old tests as they are.

## Out of scope

- The dashboard's stock overview (`stock_overview`) and "you have N" in the order window, any rule or
  number of a shift.
- The Cafe message (`cafe-staff-message`, #136), the price message (audit C2).

## Done when

1. Without an open day every product has `on_counter` 0.
2. After the player fills the Cafe counter with 16 coffee, coffee has `stock` 44 (of 60) and
   `on_counter` 16; a crew's counter in another shop counts for its products.
3. After the day ends, `on_counter` is 0 again and `stock` holds the unsold units.
4. The stock card draws `stock + on_counter` and "on the counter" only when there is some; the order
   hint, the dashboard's "in stock" badge and its stock tile ("N units in stock") use the same total.
5. The Shift panel draws no "+0" button; "Fill" and "Sell" stay at the end of the row.
6. Checked in the browser: during a Cafe shift with a full counter the card shows the total and
   "on the counter", and no "+0" button.
7. The full suite passes; no old test changed.

## Security

No new input, no new endpoint. `on_counter` is a count from the state like `stock`, drawn as a number;
no text from the server is added to the page.
