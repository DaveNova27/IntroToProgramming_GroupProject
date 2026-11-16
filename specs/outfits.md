# Outfits for the player (`outfits`)

Issue #21. Clothes for the player's figure, bought and changed in the Dorm. Only the look changes.

## What

- **The list** (`OUTFITS` in `logic.py`, prices in integer cents): Basic shirt (free, worn at the start),
  Hawaii shirt 20 €, Rain jacket 25 €, Tracksuit 30 €, Blazer 60 €. None of them is sold in the
  Merchandise shop (hoodie, T-shirt, cap): the player's clothes and the shop's goods stay apart.
- **Buying** (`buy_outfit`): takes the price, adds the outfit to the owned ones and puts it on.
  Refused for an unknown id, an outfit already owned, not enough cash, or a complete run.
- **Wearing** (`wear_outfit`): puts on an owned outfit for free. Refused for an unknown id, an outfit
  not owned, or the one already worn.
- **State:** `state["outfits"] = {"owned": [ids in the order of OUTFITS], "worn": id}`. Stored in
  `db.py` as one JSON value in `meta` (key `outfits`). A save from before outfits, or a broken entry,
  loads as the basic shirt; unknown ids are dropped, a worn outfit that is not owned falls back to the
  basic shirt. The Postgres store goes through `db.through_sqlite`, so it gets the same rules.
- **API:** `POST /api/outfit/buy` and `POST /api/outfit/wear` with `{"outfit": id}`. The view has
  `outfits` (every outfit with price, owned, worn, affordable) and `outfit` (the worn id).
- **Editor and demo:** `editor_set_state` takes `outfits` (`{"owned", "worn"}`, checked), so the state
  stays complete and settable.
- **Weather advice:** every outfit names the weathers it suits (`OUTFITS`, ids of `WEATHER`) and a
  short line. Advice only: the weather asks for no outfit, an outfit changes no rule.
- **Wardrobe in the room:** a second use point of the Dorm (`DORM["wardrobe"]` in `world.py`, joined in
  `zones.js`) in front of the wardrobe at the west wall. Standing there shows the on-screen button
  "Change your clothes" (click it or press E), which opens the wardrobe window. No rule reads it.
- **Screen:** the Dorm panel also shows what you wear and a button "Change your clothes". It opens the
  wardrobe window: a picture of every outfit (inline SVG from `static/world/wardrobe.js`), its line,
  "Good for" with the weathers, "Fits today's weather" when it suits the weather the player may know
  (the real one of an open day, before that today's forecast), and Buy (disabled without enough
  cash), Wear or "Wearing". The player's figure is drawn in the worn outfit (`OUTFIT_LOOKS` in
  `people.js`: long or short sleeves, own trousers, hibiscus print and open collar, hood, zip,
  pockets and reflective band, track stripes, lapels with shirt and tie), also asleep in bed.

## Decide

1. **Only the look:** no bonus to customers (asked on 2026-11-16, no answer: the safe choice before the
   feature freeze, the balance stays as it is). A bonus can be a follow-up.
2. **Where:** the Dorm, always reachable. The server does not read the position: a crafted request
   from elsewhere is valid if the rules allow it (roadmap 3a, 3b).
3. **No outfit from the Merchandise shop:** decided by Gregor on 2026-11-16. That guests leave the
   Merchandise shop wearing what they bought is a separate spec (`merch-wear`).
4. **Prices** are placeholders: small next to a shop unlock (200 € and more), so an outfit is a treat,
   not a trap.
5. **Tests:** the new file `tests/test_outfits.py`. No old test changes: `set(state) ==
   set(logic.new_state())` in two old tests still holds, because `new_state` has the new key too.

## Out of scope

- Any effect on customers, prices, popularity or badges.
- Clothes for guests or employees, and the `merch-wear` idea.
- Buying in the Merchandise shop.

## Done when

1. **List:** whole cents, the basic shirt is free and worn at the start, nothing from the Merchandise shop.
2. **Buy:** price taken, owned, worn; unknown, owned twice, too expensive and after the run are refused
   and change nothing.
3. **Wear:** an owned outfit for free; not owned or already worn is refused.
4. **Saved:** a save round-trips; an old save and a broken entry load as something valid.
5. **API:** buy and wear work; crafted requests (unknown id, missing id, a price sent by the browser) are
   refused or ignored, and the saved run stays identical after a refusal.
6. **Editor:** sets and checks `outfits`.
7. **Screen:** "Change your clothes" opens the wardrobe window with a picture and the weather advice of
   every outfit; the figure draws the worn outfit from the server; checked in the browser (buy, wear,
   walk, sleep), no console errors.

## Security

The server decides every purchase: id from a fixed list, price from the server's table (a price in the
request is ignored), cash never negative, a refused request changes nothing. Names shown with `esc`.
No randomness, nothing loaded from outside.
