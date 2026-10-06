# First feature: Trade one day (Campus Tycoon)

**Product:** Campus Tycoon, a snack stand on campus. **User:** the player running the stand.

## Planning answers

1. **Product and user:** Campus Tycoon; the player who runs the stand.
2. **Trigger:** the player enters a quantity and clicks "Buy", sets a selling price, then clicks "Open for the day".
3. **Before:** an active run exists: day 1, cash €100, stock 0 for every product, catalogue loaded.
4. **Rule:** refuse a purchase that costs more than the available cash, a quantity that is not a positive whole number, and a selling price that is zero or negative.
5. **After:** cash and stock change together; a trading day adds exactly one history record and advances the day by one.
6. **Restart:** cash, stock, chosen prices, current day and the history of completed days are exactly as before stopping the app.

### Catalogue (fixed)

| Product  | Unit cost | Reference price |
|----------|-----------|-----------------|
| Sandwich | €2.00     | €4.00           |
| Coffee   | €0.80     | €2.00           |
| Cookie   | €0.50     | €1.50           |

### Before → action → after

| Before | Action | After |
|---|---|---|
| Day 1, cash €100, Sandwich stock 0 | Buy 10 Sandwiches (€2 each) | Cash €80, Sandwich stock 10 |
| Cash €80, Sandwich stock 10 | Buy 41 more Sandwiches (€82) | Rejected; cash €80, stock 10 unchanged |
| Cash €80, stock 10, Sandwich price €4 | Open for the day | Sold 10, revenue €40, COGS €20, gross profit €20, cash €120, stock 0, day 2 |

## Why

The player can buy stock, set a price, trade one day and see the result reconcile, then close the app and continue later without losing or repeating anything.

## What

- Show the current day, cash and stock per product. (CT01, partial)
- Buy a positive whole-number quantity of a product. Show the total cost. Reject an unaffordable purchase and leave cash and stock unchanged. Update cash and stock together. (CT02, CT R3)
- Set a positive selling price per product. Reject zero or negative prices. (CT03)
- Open for one day using current stock and prices. Demand per product: 10 units if price <= reference price, 5 units if price > reference and <= 2x reference, 0 units above 2x reference. (CT R1)
- Units sold = min(demand, stock). Unsold stock carries forward. Stock never goes negative. (CT R2)
- Show units sold, revenue, cost of goods sold and gross profit per product and in total. Revenue = units sold x price; gross profit = revenue - purchase cost of the units sold. (CT04, CT R4)
- Record the completed day exactly once and advance the day by one. (CT R5)
- Save accepted purchases and price changes immediately. Save the day's results together with the updated balances. (What the product must remember)
- On start, load the saved run if one exists.

## Out of scope

- Days 2-5 flow polish, the final results screen after day 5 and disabling actions after day 5 (CT05, A6).
- Starting a new run and its confirmation dialog (CT01 confirmation).
- Review screen for the history of earlier days (beyond storing it).
- Random events, upgrades, competitors, running costs, spoilage, borrowing, returns.
- Accounts, multiplayer, external services, styling and artwork.

## Done when

1. **Accepted purchase and trade:** With €100 and no stock, buying 10 Sandwiches gives cash €80 and Sandwich stock 10. Opening the day at a Sandwich price of €4 (other products out of stock) gives revenue €40, COGS €20, gross profit €20, cash €120, Sandwich stock 0 and the day is now 2. (A1, A3)
2. **Rejected purchase:** With cash €80 and Sandwich stock 10, buying 41 more Sandwiches (€82) is rejected with a message. Cash is still €80 and stock is still 10. A price of €0 or -€1 is rejected and the saved price is unchanged. (A1, A2)
3. **Restart:** After completing day 1 as in check 1, stop the app and reopen it. Cash €120, Sandwich stock 0, day 2, the chosen prices and exactly one history record for day 1 are shown. Reloading again does not create a second record. (A5)
4. **Boundaries:** For a reference price of €4, prices of €4, €4.01, €8 and €8.01 give demand 10, 5, 5 and 0. With only 3 Sandwiches in stock and demand 10, exactly 3 are sold and stock is 0. (A2, A4)
