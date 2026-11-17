# Guests wear what they buy in the Merchandise shop (`merch-wear`)

From the team's ideas (roadmap 7.9): "Merchandise customers wear the clothes when they leave". Asked for
by Gregor on 2026-11-17. Only drawing and one note on the server: no rule, no number changes.

## What

- **The note (`logic.py`):** `WEARABLE = ("hoodie", "tshirt", "cap")`. When `_serve` sells one of them to
  a customer who is a guest, the shift (or the crew's shift in `extra`) keeps
  `{"guest": id, "product": pid, "tick": tick}` in `shift["dressed"]`, the newest `DRESSED_KEEP = 20`.
  It is the same for the player at the counter and for employees, because both sell through `_serve`.
  Only the server knows whether a guest bought or gave up, so the browser does not guess.
- **The view (`app.py`):** `guests.dressed` lists `{"id", "product"}` of the notes of the last
  `DRESSED_SHOW_TICKS = 10` ticks.
- **The map (`guests.js`, `people.js`):** a guest who is gone from the list and has a note first puts
  the item on at the counter (`DRESS_MS = 1600`): arms up, the hoodie or T-shirt comes down over the
  body from the neck, the cap comes down onto the head. Then the guest walks home wearing exactly that
  item, campus merch with the university's name: a purple hoodie with NOVA across the chest, hood,
  kangaroo pocket and strings, a coral T-shirt with NOVA SBE, a green cap with an N on the front (the
  colours of the products on the dashboard). With reduced motion
  there is no animation: the guest leaves dressed at once.

## Decide

1. **A note on the server, not a guess:** a guest leaves the list when served, when they give up, or
   when the shift ends. Only a sale makes the note, so nobody who gave up walks off in a new hoodie.
2. **Kept small:** at most 20 notes per shift and shown for 10 ticks; the shift is saved as before.
3. **Tests:** the new file `tests/test_merch_wear.py`. No old test changes.

## Out of scope

- Guests of other shops, employees, the player's outfits (`outfits`).
- Any effect on customers, prices, popularity or badges.
- Guests who are not drawn (more than the screen shows) get a note but no animation.

## Done when

1. **Note:** a sale of a hoodie, T-shirt or cap to a guest notes guest, product and tick (also by staff);
   food and customers without a guest get none; the note changes no number of the sale; at most 20 kept;
   the shift with notes round-trips through the save.
2. **View:** a fresh note is in `guests.dressed`, an old one is not.
3. **Map:** checked in the browser: the guest puts the item on at the counter and leaves wearing it;
   no console errors.

## Security

Nothing comes from the browser: the note is written only by the server when it sells. Product ids from
a fixed list, no randomness, nothing loaded from outside.
