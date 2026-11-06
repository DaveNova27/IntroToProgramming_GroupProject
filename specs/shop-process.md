# A day played live in one shop (`shop-process`, issue #36)

DRAFT: to be agreed before any code is written.

## What

A trading day is played inside a shop. The player starts a shift in one shop (first only
the Cafe), carries stock from the storeroom to the counter, and sells at the counter to
the customers in the queue. The counter holds only `COUNTER_UNITS` (20) in total, so
there are two jobs: refilling and selling. When the day's time is up the shift closes by
itself, the day is booked in `history` like a `trade_day` result, and the day counter
goes up by 1.

### Storeroom and counter

- **Storeroom** = the stock of the shop's products in `state["stock"]`. The product lists
  of the shops do not overlap, so this is already one storeroom per shop and no old save
  or test changes. `buy` keeps working as it is. Capacity `SHOPS[shop]["storage"]` (100)
  is checked on `buy` only if no old test conflicts; otherwise the check stays out and
  is named as a known issue (decided during the build, not silently).
- **Counter** = `state["shift"]["counter"]`, units per product, at most `COUNTER_UNITS`
  in total.

### State

`state["shift"]` is `None` (no shift) or a plain dict, complete and settable:

```
{"shop": "cafe", "tick": 0, "counter": {"coffee": 0},
 "queue": [{"product": "coffee", "arrives": 12, "patience_until": 27}, ...],
 "sold": {"coffee": 0}, "lost": 0}
```

### Time

The day has `DAY_TICKS` (90) ticks. The server counts them in the state: one request
`tick` = exactly one tick. Time is never read from the browser's clock and the browser
cannot send a number of ticks. The browser calls `tick` about once a second. The tick that
reaches `DAY_TICKS` closes the shift on the server. Skip key: the existing
`trade_day` (day without a player). It is refused while a shift is open.

### Customers

At `start_shift` the server builds the queue once, without randomness (the state has no
seed yet; `day-context` #10 brings it): for each product of the shop, `customers_for(price,
ref_price)` customers come, taken from the existing `demand()` as a placeholder, spread
evenly over the day and interleaved by product. Each wants one unit of one product and
waits `PATIENCE_TICKS` (15) after arriving, then leaves (`lost` + 1). They make no choices
(that stays in #22 `guests`). Prices come from `state["prices"]`.

`customers_for` is the single place that turns price into customers. The new price logic
(weather, events, reference prices) replaces that one function in its own spec and
changes nothing else here.

### Actions (all pure functions that return a new state, like `buy`)

- `start_shift(state, shop)`: shop id from `SHOPS`, shop unlocked, no shift open, run not
  finished. Builds the queue, counter empty.
- `refill(state, product, quantity)`: whole number > 0, product belongs to the open
  shift's shop and is owned, storeroom holds it, counter space left. Moves storeroom to
  counter.
- `sell(state, product)`: sells one unit to the first waiting customer who wants that
  product (arrived, not left); the counter holds it. Cash + price, `sold` + 1.
- `tick(state)`: tick + 1; customers past their patience leave; at `DAY_TICKS` the shift
  closes: queue rest is lost, unsold counter units go back to the storeroom, one history
  entry (same fields as `trade_day`), `day` + 1, `shift` = `None`.

Revenue and cost of goods follow CT R4 (cost of the units sold). Money is integer cents.

### API and screen

`POST /api/shift/start`, `/refill`, `/sell`, `/tick`; `GET /api/state` shows the shift
(counter, queue length, tick, sold). The shop state is saved in `db.py` (a `shift` row;
an old save loads with `shift = None`). In `static/world/` the player walks in the Cafe,
takes stock at the storeroom spot, puts it on the counter, and serves at the counter.
Walking is only drawing: each refill and sale is a request, and the server never
reads the position.

## Out of scope

Employees (#20 `staff`: they will later do refilling and selling like the player, until
then the player is the only person and a shop without a running shift sells nothing),
customers with their own choices (#22), several shops open at once, popularity, the new
price logic (own spec), balancing numbers, weather and events.

## Done when

1. A shift can be started in the Cafe only; the other shops, locked or not, are refused
   in this spec (one shop first).
2. Refill and sell work as above; the counter never holds more than 20 units in total.
3. Refused, and the saved run stays identical: unknown or non-string ids, wrong types
   (bool, float, string, negative, zero), more than the storeroom holds, more than the
   counter space, selling a product that is not on the counter, selling with nobody
   waiting for it, any action without an open shift, a second `start_shift`, an unlocked
   check for locked shops, `trade_day` while a shift is open, anything after the last day.
4. A crafted request cannot sell more than the counter holds and cannot sell after the
   day ended (the shift is gone, `sell` is refused). Both are tested.
5. No rule reads a position; `move_player` stays cosmetic.
6. The shift survives a restart; a save from before this spec loads with no shift.
7. Money is integer cents; the state is complete and settable; no `random`.
8. `trade_day` and its tests are unchanged; `tests/` and `checks/` are untouched
   (no test exception for this spec).
9. `uv run pytest` passes. In the browser: a whole day in the Cafe is playable, refused
   actions show why, no console errors.
10. PR "Closes #36", AI code review done and its findings handled.

## Security

Follows `docs/feature-roadmap.md` 3a and 3b: the server checks every refill and sale
against storeroom, counter space and queue; ids from fixed lists; JSON fields validated;
one lock per change; rejected actions change nothing; error texts are our own rule
messages; texts shown via `textContent`.
