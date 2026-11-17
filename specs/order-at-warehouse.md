# Order stock at the PC in the Supply Hall (`order-at-warehouse`)

Asked for by Gregor on 2026-11-17: stock is ordered in the warehouse, on foot. The player walks into the
Mercado Supply Hall (the warehouse with the loading bay and the lorry) to a small PC and orders there.

## What

- **The order PC (`world.py`):** a desk with a PC against the north wall of the Supply Hall
  (`order-pc` in the room's solid objects). The use point `supplier` ("Order stock") moves from the
  atrium of the Nova to the front of that desk, in the wing `mercado`; its id and its action `stock`
  stay, so everything that opens the order window keeps working. It shows "ORDER PC" over "SUPPLY HALL".
- **Drawing (`rooms.js`):** the desk with a monitor, a keyboard and a small stack of order slips.
- **The campus (`ui.js`, `main.js`):** the order window opens only when the player stands at the PC.
  The "Stock" button of the toolbar walks the player to the PC (like a click on it) and opens the
  window on arrival; standing there it opens at once. A "Skip the walk" is not added: the walk is the point.
- **The dashboard (`app.js`):** the product cards no longer have a buy form. In its place a line says
  where to order, with a button that switches to the campus and walks the player to the PC.
- **The server is unchanged:** `POST /api/buy` stays as it is. By the roadmap rules (3a, 3b) no rule reads
  the player's position, so a crafted request from elsewhere is still valid if the rules allow it. The
  walk is a matter of the screen, like every other desk.

## Decide

1. **Move, not add:** the desk in the atrium goes away, so there is one place to order. The id
   `supplier` and the action `stock` stay.
2. **Old tests that name the desk's place change (confirm in the PR):** `tests/test_nova_wings.py`
   (`test_the_three_desks_keep_their_ids_actions_and_places`: the place of `supplier` and that it stands
   on the floor of the Nova) and `tests/test_walk_in.py` (`test_the_three_desks_stand_in_the_atrium_...`:
   `supplier` stands in the atrium). Both pin data this spec changes on purpose (the desk's place); the
   ids and actions they check stay the same. Nothing is weakened: the new place is checked the same way
   (on the floor of its wing, in its room, not blocked).
3. **The dashboard keeps no shortcut:** ordering is only at the PC (Gregor, 2026-11-17).
4. **Tests:** the new file `tests/test_order_at_warehouse.py`.

## Out of scope

- The lorry: it stays where it is, on the delivery lane west of the Supply Hall. Its road and a
  delivery animation are a spec of their own (`lorry-arrival`).
- Delivery times, a central storage, carrying goods to the shops (`warehouse`).
- Prices, the server's buy rule, the demo scenarios.

## Done when

1. **Place:** the use point `supplier` stands in the Supply Hall in front of the order PC, reachable on
   foot from the plaza and from inside the Nova; nothing blocks it.
2. **Campus:** the order window opens at the PC (E or a click); the "Stock" button walks there first;
   away from the PC it does not open.
3. **Dashboard:** no buy form, the note and the button instead.
4. **Server:** `/api/buy` works as before; the full test suite passes.
5. **Checked in the browser:** walk to the PC, order, the stock arrives; the button from far away walks
   there; no console errors.

## Security

Unchanged: the server checks every purchase (integer cents, storeroom space, cash). The position decides
no rule. Nothing loaded from outside, no randomness.
