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

`logic.py` only: `CATALOGUE` (cost and reference price), `SHOP_MIX`, the unlock prices and the
window prices in `SHOPS`. Targets, as a **proposal** the owner confirms or changes in the PR:

- A good player ends with **+3,000 to +8,000 EUR** (a very good one, about all four shops, near
  the top). Not 25,000.
- No shop makes more than **half** of the profit of a full season of the best strategy.
- Opening the next shop is worth it but not at once: an unlocked shop with its first employee pays
  its unlock price and its first employee back within **8 to 14 days** at the reference price.
- A second employee per shop does not lose money (the audit found it 816 EUR worse).
- Cash on day 5 is above the 100 EUR start for the Cafe-only strategy, and it is still below the
  price of the second shop on day 5 for every strategy (the first days stay tight).
- The best price of every product stays in its band in `tests/test_pricing.py` (`BANDS`) and above its
  cost. If a new cost moves it out of a band, the numbers change, not the band.

The method: change the tables, run the simulation of this spec, repeat. The simulation is the
source of the numbers, not a guess.

### 2. The simulation as a guard

`tests/test_balance.py` (new) plays whole seasons with the real rules and fixed strategies over a
fixed list of seeds (20 seeds, a few seconds) and checks the targets above as bands (min and max of
the mean), not as exact values. The strategies are: only coffee, the whole Cafe, the Cafe and then one
shop after the other (in two orders), and a player who never works (staff only).
A failing test prints the table of the strategies.

### 3. The dead end (B2)

A purchase that leaves the player with no cash for the cheapest unit of an owned product **and** no
stock at all (storeroom and counters) shows a **warning**, never a refusal. The server decides:
`shop_offers` (and the unlock row of `shops_view`) gets a `warning` text or `null`; the Shops panel
and the dashboard only show it under the button. The purchase itself stays allowed.

### 4. The trap (B3)

A shop without an employee place sells nothing, and only the Cafe can be played by the player
(`SHIFT_SHOPS`). The unlock row of such a shop says so in the Shops panel ("sells only through
employees: buy an employee place first"). No rule changes; the real fix is `shop-walk`.

### 5. The storeroom limit (B4)

The storeroom limit of a shop counts the units on the counter of a running shift too
(`_check_storeroom_space` in `logic.py`), so carrying stock to the counter and buying again cannot
exceed it.

## Out of scope

New rules (popularity, events, an emergency loan), `warehouse`, the day length and the speed of
the tick, the look, new products, a second employee per place, `shop-walk`.

## Done when

1. The targets of section 1 hold in `tests/test_balance.py` on the seeds 1 to 20.
2. Warning, trap hint and storeroom limit have a test each in a new file (the saved run is
   unchanged by a refused or warned action; nothing is refused for the warning).
3. Old tests that name numbers this spec changes on purpose (prices, names, thresholds) change
   **only** with the owner's confirmation in the session (`AGENTS.md`). Each one is written here
   under "Decide" with its reason and in the PR description. No test is weakened, skipped or deleted.
4. The Shops panel and the dashboard show the warning and the hint (checked in the browser).
5. `uv run pytest` passes.

Rules: money stays integer cents, a rejected action changes nothing, no randomness outside the
seed (the simulation uses fixed seeds), the state stays complete and settable.

## Decide

_Filled in during the build: each changed old test, with the owner's confirmation._
