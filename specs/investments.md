# Group feature: Invest spare cash in stocks (Campus Tycoon)

**Product:** Campus Tycoon, a growing tycoon business on campus. **User:** the player
running it.

> Group project draft, not from a BRD. Independent of `multi-business.md` and
> `employees.md` (cash-only, no stock/catalogue involved) — can be built in parallel.
> Depends on `longer-run.md` for there to be enough days for a price history to matter.

## Planning answers

1. **Product and user:** Campus Tycoon; the player who invests spare cash alongside
   running their business(es).
2. **Trigger:** the player buys or sells shares of one of a small, fixed set of
   fictional stocks; each trading day the stock's price also moves.
3. **Before:** cash exists (from the business); no shares owned yet, or some already
   owned from an earlier day.
4. **Rule:** buying shares cost `units x current price`, refused if cash is
   insufficient or units is not a positive whole number; nothing changes on a refusal.
   Selling pays `units x current price`, refused if the player does not own that many
   shares. A stock's price for day N is a **deterministic** function of N (and the
   stock's fixed parameters) — not true randomness — so it is exactly reproducible and
   testable.
5. **After:** cash and the player's share holdings update together, same as a product
   purchase does. Opening a new day also moves every stock's price by one step.
6. **Restart:** share holdings, cash and each stock's current price reload exactly as
   before stopping the app; the price for a given day is always the same value.

### Example stocks (placeholder, confirm with the team)

| Stock | Day-1 price | Movement |
|---|---|---|
| Nova Tech Corp | €10.00 | placeholder deterministic formula, e.g. price(day) = base + amplitude × sin(day × step) |
| Carcavelos Realty | €25.00 | same pattern, different parameters |

### Before → action → after

| Before | Action | After |
|---|---|---|
| Cash €200, 0 shares, Nova Tech Corp at €10.00 | Buy 10 shares | Cash €100, 10 shares owned |
| Cash €100, 10 shares at €12.00 (price moved) | Sell 10 shares | Cash €220, 0 shares |
| Cash €50, Nova Tech Corp at €10.00 | Buy 10 shares (€100) | Rejected; cash €50, 0 shares unchanged |
| Owns 5 shares | Sell 6 shares | Rejected; holdings unchanged |

## Why

Spare cash sitting idle between business expansions should be able to grow (or shrink)
like it would for a real investor, without adding a whole second simulation to test
against — a small, deterministic stock system is enough.

## What

- A small, fixed list of stocks (placeholder table above), each with day-1 price and a
  deterministic price formula. No real market data, no true randomness.
- Buy N shares of a stock: costs `N x current price` in cash, adds to the player's
  holdings for that stock. Rejected if unaffordable or N is not a positive whole
  number.
- Sell N shares: pays `N x current price`, removes from holdings. Rejected if the
  player does not own N shares of that stock.
- Each stock's price recalculates once per day, when the day advances (same moment the
  trading day resolves for the business/businesses).
- Dashboard shows each stock's current price, the player's holdings and their current
  value, plus total portfolio value counted into the final result.
- Prices and trades use integer cents, exactly like product prices today.

## Out of scope

- Real market data, external price feeds, true randomness.
- Dividends, stock splits, short selling, margin, options.
- Gambling mechanic (separate, lower-priority idea; not part of this spec).
- Any change to the business/product trading rules.

## Done when

1. **Buy shares:** With cash €200 and Nova Tech Corp at €10.00, buying 10 shares leaves
   cash €100 and 10 shares owned.
2. **Rejected buy:** With cash €50, buying 10 shares at €10.00 (€100) is rejected; cash
   and holdings unchanged.
3. **Sell shares:** Selling shares the player owns pays `N x current price` and reduces
   holdings; selling more than owned is rejected and changes nothing.
4. **Deterministic price:** The price for a given stock on a given day is the same
   value every time it is computed (same day number in, same price out) — verified by a
   test that calls the price function twice for the same day.
5. **Restart:** Holdings, cash and today's stock prices reload exactly as before
   stopping the app.
6. **Final result:** Portfolio value (holdings x current price) is included in the
   player's overall result at the end of the run.
