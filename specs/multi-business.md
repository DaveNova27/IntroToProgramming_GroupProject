> **Dropped.** This spec comes from the first draft (PR #1) and belongs to the dropped plan. It is kept as history only and describes nothing in the game today. See `docs/feature-roadmap.md` for the plan that replaced it.

# Group feature: Own more than one business (Campus Tycoon)

**Product:** Campus Tycoon, a growing tycoon business on campus. **User:** the player
running it.

> Group project draft, not from a BRD; agree catalogue/prices with the team before
> building. Depends on `longer-run.md` landing first. This is the foundation the
> `employees.md` and (later) `net-worth.md` specs build on.

## Planning answers

1. **Product and user:** Campus Tycoon; the player who owns and runs several businesses.
2. **Trigger:** the player has enough cash and buys a new business (e.g. Merchandise
   Stand, Surf Shop); afterwards they switch between their businesses to buy stock, set
   prices and trade each one.
3. **Before:** the player owns the snack stand only (today's single business), with its
   own cash-funded stock and prices.
4. **Rule:** cash is shared across all owned businesses (one wallet). Stock, prices and a
   business's own catalogue belong to that business only. Buying a business costs its
   purchase price and is refused if cash is insufficient; nothing changes on a refusal.
   Every existing buy/price/trade rule (CT R1-R5) applies per business, unchanged.
5. **After:** the player sees every owned business, can buy stock/set prices/trade each
   one independently, same day for all of them. A newly bought business starts with
   zero stock and reference prices, like a fresh stand.
6. **Restart:** every owned business, with its own stock, prices and that business's
   share of the day's history, reloads exactly as before stopping the app.

### Example businesses (placeholder catalogue, confirm with the team)

| Business | Purchase price | Example catalogue |
|---|---|---|
| Snack Stand | owned from day 1 | Sandwich, Coffee, Cookie (existing) |
| Merchandise Stand | €500 | Hoodie, Cap, Tote bag |
| Surf Shop | €2,000 | Board rental, Wetsuit rental, Sunscreen |

### Before → action → after

| Before | Action | After |
|---|---|---|
| Cash €600, only Snack Stand owned | Buy Merchandise Stand (€500) | Cash €100, Merchandise Stand owned with 0 stock, reference prices |
| Cash €100 | Buy Surf Shop (€2,000) | Rejected; cash €100 unchanged, Surf Shop not owned |
| Snack Stand and Merchandise Stand owned, both stocked | Open for the day | Both businesses trade the same day independently; one combined day record, cash reflects both results |

## Why

A single stand caps how deep a 30-day season can go. Several businesses, bought as cash
allows, give the player real expansion decisions without changing how any one business
is run.

## What

- A list of owned businesses instead of one implicit stand. The existing snack stand is
  business #1, owned from the start, unchanged in behaviour.
- A small, fixed set of further business types, each with its own catalogue (unit
  cost, reference price) and a purchase price to unlock it. (placeholder table above)
- "Buy a business": spend cash to add one to the owned list. Refused if unaffordable or
  already owned; a refusal changes nothing.
- Every business the player owns can be stocked, priced and traded exactly like the
  snack stand today (same demand rule, same per-product rejection rules).
- Opening "for the day" trades every owned business for that day in one action; the
  dashboard shows each business's units sold, revenue, COGS and gross profit, plus a
  combined total.
- Stock overview (`stock-overview.md`) extends per business, same per-product numbers as
  today.

## Out of scope

- Staff/automation (`employees.md`), investments (`investments.md`), luxury
  items/net worth (`net-worth.md`): separate specs, built on top of this one.
- Selling or closing a business once bought.
- More than the placeholder set of business types; exact names/prices/catalogues to be
  agreed with the team, not treated as final here.
- The 3D campus map showing more than one shop. Keep the map working; extending it to
  multiple shops is explicitly later/optional.

## Done when

1. **Buy a business:** With cash €600, buying the Merchandise Stand (€500) leaves cash
   €100 and adds it to the owned list with 0 stock and reference prices.
2. **Rejected purchase:** With cash €100, buying the Surf Shop (€2,000) is rejected; cash
   and owned businesses are unchanged.
3. **Independent trading:** With the Snack Stand and Merchandise Stand both stocked,
   opening for the day trades both using their own prices/stock, in one history entry
   with a per-business and a combined breakdown.
4. **Unowned business:** Trying to buy stock, set a price or trade a business the player
   does not own is rejected; nothing changes.
5. **Restart:** All owned businesses, their stock, prices and the day's combined history
   reload exactly as before stopping the app.
6. **Existing tests:** All current tests for the snack stand pass unchanged (it is
   business #1 with the same behaviour).
