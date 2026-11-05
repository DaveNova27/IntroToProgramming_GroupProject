# Group feature: Hire staff to run a business for you (Campus Tycoon)

**Product:** Campus Tycoon, a growing tycoon business on campus. **User:** the player
running it.

> Group project draft, not from a BRD. Depends on `multi-business.md` landing first —
> staff are hired per owned business.

## Planning answers

1. **Product and user:** Campus Tycoon; the player who owns one or more businesses.
2. **Trigger:** the player hires staff for a business they own; from then on that
   business trades automatically each day without the player setting it up by hand.
3. **Before:** a business trades only when the player explicitly buys stock, sets a
   price and opens it that day; with no staff, a day with no action sells nothing.
4. **Rule:** hiring staff for a business costs a one-time hire price, refused if
   unaffordable; nothing changes on a refusal. A staffed business has a **daily wage**,
   paid automatically when the day advances; if cash cannot cover a day's total wages,
   staff for the cheapest-to-retain business(es) are let go first rather than letting
   cash go negative (exact tie-break rule to be agreed with the team).
5. **After:** each day, every staffed business automatically restocks (buys up to its
   last-set stock level, cash permitting) and trades at its last-set price, exactly as
   if the player had done it manually; wages are deducted the same day.
6. **Restart:** staffing status, wages owed/paid and each business's last-set price
   reload exactly as before stopping the app; a staffed business keeps auto-trading
   after a restart.

### Before → action → after

| Before | Action | After |
|---|---|---|
| Cash €300, Merchandise Stand owned, unstaffed | Hire staff (€200, €10/day wage) | Cash €100, Merchandise Stand staffed |
| Cash €50, wants to hire staff costing €200 | Hire staff | Rejected; cash €50 unchanged, still unstaffed |
| Merchandise Stand staffed, price €15, last stocked 20 units | Day advances, player does nothing | Business restocks up to 20 units (cash permitting), trades at €15, wage €10 deducted, all in the day's result |
| Cash insufficient to pay a day's total wages | Day advances | The agreed tie-break rule drops staff for one or more businesses; cash never goes negative |

## Why

Running several businesses by hand every day does not scale. Staff let the player
trade passively once a business is set up, while still costing money, so idle
businesses are not free to keep.

## What

- "Hire staff" for an owned business: one-time cost, refused if unaffordable.
- A staffed business has a daily wage, deducted automatically when the day advances,
  before or alongside that business's own trade result.
- A staffed business auto-trades every day: restocks toward its last manually-set
  target quantity (cash permitting, following the same purchase rules as a manual buy)
  and sells at its last manually-set price. The player can still change the price or
  target stock at any time; the next automatic day uses the new values.
- An unstaffed business does nothing on its own; the player must act manually, same as
  today.
- If total daily wages exceed available cash, apply one agreed, deterministic
  tie-break rule (e.g. let go the business with the lowest wage first) so cash never
  goes negative. Document the exact rule in this spec once the team agrees it, before
  implementing.
- Dashboard shows which businesses are staffed, their wage, and a running total of
  wages paid.

## Out of scope

- Staff skill levels, training, multiple staff per business, firing on request (only
  automatic let-go from the cash rule above).
- Any player-controlled, real-time or first-person element. Staffing only ever changes
  what happens automatically when a day advances.
- Investments (`investments.md`) and net worth/luxury items (`net-worth.md`): separate
  specs.

## Done when

1. **Hire:** With cash €300, hiring staff for €200 leaves cash €100 and marks the
   business staffed.
2. **Rejected hire:** With cash €50, hiring staff costing €200 is rejected; cash and
   staffing unchanged.
3. **Auto-trade:** A staffed business with a last-set price and target stock trades
   automatically when the day advances, without any manual buy/price/open call that
   day; wages are deducted the same day.
4. **Unaffordable wages:** When total daily wages exceed cash, the agreed tie-break
   rule applies and cash never goes negative after the day advances.
5. **Restart:** Staffing, last-set prices/stock targets and wages-paid-so-far reload
   exactly as before stopping the app.
6. **Existing tests:** Manual buy/price/trade behaviour for unstaffed businesses is
   unchanged.
