# Second feature: Play the full run (Campus Tycoon)

**Product:** Campus Tycoon, a snack stand on campus. **User:** the player running the stand.

> Draft derived from the "Out of scope" list of `first-feature.md` (CT01 confirmation,
> CT05, A6, history review). The BRD itself was not available when this was written:
> check the IDs and wording against it before treating this spec as final.

## Planning answers

1. **Product and user:** Campus Tycoon; the player who runs the stand.
2. **Trigger:** the player trades days 2 to 5; after day 5 they look at the final result; at any time they click "New run" and confirm it.
3. **Before:** a saved run exists, at any day from 1 to "complete" (after day 5).
4. **Rule:** after day 5, buying, changing a price and opening the stand are refused. A new run only starts after an explicit confirmation.
5. **After:** a complete run shows final cash, remaining stock at cost and the overall result. A confirmed new run is day 1, €100, no stock, reference prices and no history.
6. **Restart:** a complete run is still complete after a restart; a new run is still new after a restart, without any day of the old run.

### Before → action → after

| Before | Action | After |
|---|---|---|
| Day 1, €100, no stock | Buy 15 Sandwiches, price €4, open day 1; price €9, open days 2-5 | Run complete: cash €110, 5 Sandwiches left (€10 at cost), overall result +€20 |
| Run complete | Buy 1 Sandwich / set a price / open the stand | Rejected with a message; nothing saved changes |
| Any saved run with history | "New run", then "Cancel" | Nothing changes |
| Any saved run with history | "New run", then confirm | Day 1, €100, stock 0, reference prices, history empty |

## Why

The player can play all five days, see how well the stand did in the end, and start again without the old run leaking into the new one.

## What

- Show every completed day in a history table: day, units sold, revenue, cost of goods sold, gross profit, cash after the day, plus a total row. (review of earlier days)
- After day 5 the run is complete. Show final cash, remaining stock at cost and the overall result = final cash + remaining stock at cost - €100. (CT05, CT R4)
- When the run is complete, buying, setting prices and opening are disabled on screen and refused by the rules; a refused action changes nothing. (A6)
- "New run" asks for confirmation. Cancel changes nothing. Confirm replaces the saved run with a fresh one in one transaction: day 1, €100, stock 0 for every product, prices at the reference price, no history. (CT01)

## Out of scope

- Random events, upgrades, competitors, running costs, spoilage, borrowing, returns.
- Several saved runs, high scores, accounts, multiplayer, external services.
- Changing the demand rule or the catalogue.

## Done when

1. **Full run:** With the scenario in the table, the run is complete after day 5, with cash €110, Sandwich stock 5, remaining stock at cost €10 and overall result +€20. History holds exactly five days, numbered 1 to 5.
2. **Locked after day 5:** Buying, setting a price and opening the stand on a complete run are rejected, and the saved run is unchanged.
3. **New run:** After a confirmed new run, the saved run is day 1, €100, stock 0, reference prices and an empty history, also after reloading it from the database. Trading day 1 of the new run stores a new day 1 record, not the old one.
4. **Restart:** A complete run reloaded from the database is still complete, with the same final result.
