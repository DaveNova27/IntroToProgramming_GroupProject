# Order several products at once (`bulk-order`)

Asked for by Gregor on 2026-11-17: once more products are unlocked, the order window at the PC should let
the player pick a quantity for several products and order them all with one click, not one by one.

## What

- **The rule (`logic.py`):** `buy_many(state, items)` takes a list of `{"product", "quantity"}`. It is one
  purchase: every line is checked like `buy` (owned product, whole number above 0, room in that shop's
  storeroom, the run not complete), the cash is checked against the total of all lines, and then all
  lines are booked together. If one line is refused, the whole order is refused and nothing changes;
  the message names the line. A product may appear only once; an empty list is refused. Lines with
  quantity 0 are left out by the browser and refused by the server (nothing to order is no order).
- **The API (`app.py`):** `POST /api/buy-many` with `{"items": [...]}`. At most one line per product
  (so at most the number of products). The answer names what was bought and the total.
  `POST /api/buy` stays as it is.
- **The order window (`ui.js`, `map.css`):** one row per owned product: name, cost per unit, stock now,
  a quantity field (starting at 0) with − and +. Under the rows the total of the whole order and what
  is left of the cash; one button "Order all" (disabled while the total is 0). A line whose quantity
  is not a whole number shows the reason and keeps the button off. The window stays at the PC
  (`order-at-warehouse`).

## Decide

1. **All or nothing:** a half-booked order would be confusing (the player would not know what arrived)
   and harder to test. The roadmap rule "a rejected action must not change any saved data" holds for
   the whole order.
2. **The old single-product order** in the window is replaced by the rows; `/api/buy` stays for the
   tests and the editor. No old test changes.
3. **Tests:** the new file `tests/test_bulk_order.py`.

## Out of scope

- Delivery times, the lorry (`lorry-arrival`), a central storage (`warehouse`).
- Prices, discounts for bigger orders, the dashboard.

## Done when

1. **Rule:** several products bought at once; cash and stock change together; a refused line (unknown or
   not owned product, bad quantity, no room, the same product twice, empty list) or too little cash for
   the total refuses everything and changes nothing; the storeroom limit counts all lines of one shop together.
2. **API:** works; crafted bodies (no list, too many lines, wrong types) are refused and the saved run
   stays identical.
3. **Window:** rows, total, "Order all"; checked in the browser with two unlocked shops; no console errors.

## Security

The server checks every line and the total, in integer cents. Product ids from a fixed list, quantities
whole numbers, the list length bounded. A refused order changes nothing.
