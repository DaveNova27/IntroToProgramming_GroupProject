# Balance pass

Issue #76. Found in the audit (`docs/audit-report.md`, items G1, B2, B3, B4; the simulation is in
section 3.3.3). Decisions of the spec owner (David) in the session: a warning instead of a
refusal against the dead end, no loan yet, the day length is not touched here.

## What

The 30-day season is exciting from the first to the last day, no single shop decides it, and the
player is not trapped by a purchase.

Measured before (real rules, seeds 1 to 20, a player who serves the Cafe without a mistake):

| Strategy | Result of the season |
|---|---|
| only coffee | +332 EUR |
| the whole Cafe | +1,500 EUR |
| Cafe, then straight to the Surf Shop, then the rest | +25,345 EUR |
| the Beach Cafe unlocked without an employee place | +1,300 EUR |

The Surf Shop pays out about 500 EUR a day for one product (the Cafe: 12 to 25 EUR), and every shop
has the same 10 customers per product at the reference price, so the margin alone decides. Until day
10 money is tight, from day 10 on it explodes.

### 1. The numbers (G1)

`logic.py` only: the cost and the reference price of the products of the Surf Shop and the
Merchandise shop (`CATALOGUE`). The mix per shop (`SHOP_MIX`), the unlock prices, the window prices
and the wages stay: tests pin them, and the simulation shows they hold. Targets (a proposal the
owner can change in the PR; the numbers are measured, see "Done when"):

- A good player ends with **+3,000 to +8,000 EUR** (about all four shops). Not 25,000.
- No shop makes more than **half** of the profit of a full season of the best strategy.
- On a neutral day no shop's best profit is more than 5 times another's.
- The Cafe alone still earns something, but clearly less than several shops (800 to 2,500 EUR).
- The first days stay tight (under 1,000 EUR on day 10).
- The best price of every product stays in its band in `tests/test_pricing.py` (`BANDS`) and above
  its cost. The ratio of cost to reference price is kept, the prices are scaled down.

Built: Surf Shop and Merchandise products cost and sell for about 16 % and 36 % of what they did
(surfboard 6.50 / 14.50 EUR, wetsuit 4.00 / 9.50, surf lesson 1.30 / 4.00, hoodie 6.50 / 12.50,
T-shirt 2.20 / 5.40, cap 1.50 / 4.30). The Surf Shop and the Wetsuit are renamed "rental" so the
prices make sense; the ids stay.

Not done on purpose: a second employee per shop (the audit found it 816 EUR worse) is a question of
the staff numbers and stays with the staff follow-up (#20).

### 2. The simulation as a guard

`tests/test_balance.py` (new) plays whole seasons with the real rules: a player who serves the Cafe
without a mistake, sets the best price every morning and buys the next step of a plan when the cash
still pays the stock of the day. Two plans (the Cafe only; the Cafe, then the Surf Shop, Merchandise
and the Beach Cafe) on two fixed seeds (about 10 seconds), and the targets above as bands.
Measured: Cafe only +1,522 / +1,609 EUR; all shops +5,302 / +5,235 EUR with the Cafe 21 %, the Surf
Shop 44 %, Merchandise 26 %, the Beach Cafe 9 % of the profit. A bigger run (20 seeds, 8
strategies, outside the tests) gave the same picture.

### 3. The dead end (B2)

A purchase that leaves the player with no cash for the cheapest unit of an owned product **and** no
stock at all (storeroom and counters) shows a **warning**, never a refusal. The server decides:
`shop_offers` (and the unlock row of `shops_view`) gets a `warning` text or `null`; the Shops panel
only shows it under the button (the dashboard has no shop window). The purchase itself stays allowed.

### 4. The trap (B3)

A shop without an employee place sells nothing, and only the Cafe can be played by the player
(`SHIFT_SHOPS`). `logic.shop_hint` gives such a shop a `hint` ("sells only through employees ..."),
shown in the Shops panel. No rule changes; the real fix is `shop-walk`.

The dead end counts only stock somebody can sell (the Cafe, or a shop with a working employee) and
leaves out the wages due at the end of the day. The hint tells a shop without a place from a shop
whose employee stopped. A saved price above 3 times the reference price (a save from before the new
prices) starts again at the reference price when it is loaded.

### 5. The storeroom limit (B4)

The storeroom limit of a shop counts the units on the counter of a running shift too
(`_check_storeroom_space` in `logic.py`), so carrying stock to the counter and buying again cannot
exceed it.

## Out of scope

New rules (popularity, events, an emergency loan), `warehouse`, the day length and the speed of
the tick, the look, new products, a second employee per place, `shop-walk`.

## Done when

1. The targets of section 1 hold in `tests/test_balance.py` on the seeds 1 and 2.
2. Warning, trap hint and storeroom limit have a test each in a new file (the saved run is
   unchanged by a refused or warned action; nothing is refused for the warning).
3. Old tests that name numbers this spec changes on purpose change **only** with the owner's
   confirmation in the session (`AGENTS.md`). None had to change (see "Decide").
4. The Shops panel shows the warning and the hint (checked in the browser; the dashboard has no shop window).
5. `uv run pytest` passes.

Rules: money stays integer cents, a rejected action changes nothing, no randomness outside the
seed (the simulation uses fixed seeds), the state stays complete and settable.

## Decide

No old test changed: none of them pins the new prices or names. The numbers that tests pin (the mix
per shop, the unlock prices, the window prices) were left alone for that reason.
