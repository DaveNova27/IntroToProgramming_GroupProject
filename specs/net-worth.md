> **Dropped.** This spec comes from the first draft (PR #1) and belongs to the dropped plan. It is kept as history only and describes nothing in the game today. See `docs/feature-roadmap.md` for the plan that replaced it.

# Group feature: Net worth and luxury purchases (Campus Tycoon)

**Product:** Campus Tycoon, a growing tycoon business on campus. **User:** the player
running it.

> Group project draft, not from a BRD. Depends on `multi-business.md`; pairs well with
> `investments.md` if that has landed, but does not require it (its value is simply 0
> for net worth if investments do not exist yet).

## Planning answers

1. **Product and user:** Campus Tycoon; the player who wants their overall success, not
   just cash, reflected in the score.
2. **Trigger:** the player buys a luxury item (car, watch, ...) with spare cash; at any
   time, or at the end of the run, they see their net worth.
3. **Before:** the final result only counts cash + business stock value
   (`full-run.md`'s `overall_gain`).
4. **Rule:** buying a luxury item costs its price, refused if unaffordable; nothing
   changes on a refusal. Net worth = cash + stock value of every owned business +
   portfolio value (if investments exist) + value of owned luxury items. Luxury items
   have a fixed resale value (a fraction of purchase price, e.g. 70%) if the player
   ever sells one.
5. **After:** the final result (end of the season, `full-run.md`) reports net worth
   instead of only cash + stock value; a breakdown shows each component.
6. **Restart:** owned luxury items and net worth reload exactly as before stopping the
   app.

### Example luxury items (placeholder, confirm with the team)

| Item | Purchase price | Resale value |
|---|---|---|
| Watch | €300 | €210 (70%) |
| Car | €8,000 | €5,600 (70%) |
| House | €50,000 | €35,000 (70%) |

### Before → action → after

| Before | Action | After |
|---|---|---|
| Cash €500 | Buy Watch (€300) | Cash €200, owns 1 Watch |
| Cash €200 | Buy Car (€8,000) | Rejected; cash €200 unchanged, no Car |
| Owns 1 Watch (€300 paid) | Sell Watch | Cash +€210, Watch no longer owned |
| End of season: cash €1,000, stock value €200, portfolio €150, Watch owned (€300) | View final result | Net worth €1,650, with a breakdown by component |

## Why

Once a player can own several businesses, hold investments and buy luxury items, "cash
+ stock value" undersells what they actually built. Net worth gives one honest number
that includes everything, and a reason to spend profit on something other than
reinvesting it.

## What

- A small, fixed list of luxury items (placeholder table above), each with a purchase
  price and a resale value (fraction of purchase price).
- Buy a luxury item: costs its price, refused if unaffordable. Sell one the player
  owns: pays its resale value, refused if not owned.
- Net worth = cash + (every owned business's stock value at cost, as today) +
  (investment portfolio value, if `investments.md` exists; 0 otherwise) + (sum of
  purchase prices of owned luxury items... or resale values — team to agree which is
  more honest, document the final choice here before implementing).
- The final result screen (`full-run.md`) reports net worth as the headline number,
  with cash / stock value / portfolio / luxury items shown as a breakdown underneath.
- Owning luxury items has no gameplay effect beyond their value (no bonuses, no
  depreciation over time) — kept intentionally simple.

## Out of scope

- Loans, financing luxury items on credit.
- Depreciation over time (resale value is fixed, not time-based).
- Any gameplay bonus from owning a luxury item.
- Investments themselves (`investments.md`) — this spec only adds their value into net
  worth if they exist.

## Done when

1. **Buy:** With cash €500, buying a Watch (€300) leaves cash €200 and the Watch owned.
2. **Rejected buy:** With cash €200, buying a Car (€8,000) is rejected; cash and owned
   items unchanged.
3. **Sell:** Selling an owned Watch pays its resale value and removes it from owned
   items; selling an item not owned is rejected.
4. **Net worth:** At the end of a season, the final result shows net worth equal to the
   sum of its components, each shown in the breakdown, matching a worked example like
   the one above.
5. **Restart:** Owned luxury items and the computed net worth reload exactly as before
   stopping the app.
6. **Existing tests:** `full-run.md`'s existing checks for cash and stock value still
   pass; net worth is additive, not a replacement for those numbers.
