# Third feature: Stock overview (Campus Tycoon)

**Product:** Campus Tycoon, a snack stand on campus. **User:** the player running the stand.

## Planning answers

1. **Product and user:** Campus Tycoon; the player who runs the stand.
2. **Trigger:** the player looks at the dashboard, before or after buying, changing a price or trading a day.
3. **Before:** an active or complete run exists.
4. **Rule:** the overview only reads the run; it never changes stock, cash or prices. "Sells today" uses the same demand and stock rules as trading (CT R1, CT R2).
5. **After:** for every product the player sees how many units are available, what they are worth at purchase cost, how many the current price would sell today and how many would be left after today.
6. **Restart:** the overview is calculated from the saved run, so it shows the same numbers after a restart.

### Example

| Before | Overview |
|---|---|
| 12 Sandwiches at €4 (ref €4), 3 Coffees at €5 (ref €2), no Cookies | Sandwich: 12 units, €24.00 at cost, sells 10 today, 2 left · Coffee: 3 units, €2.40, sells 0, 3 left · Cookie: 0 units · Total: 15 units, €26.40 |

## Why

The player sees at a glance which product is running low and which stock would just sit on the shelf, before deciding what to buy and before opening the stand.

## What

- One overview for all products: units in stock, value at purchase cost, units the current price sells today, units left after today. (CT01, CT R4)
- Sells today = min(demand at the current price, units in stock); left after today = units - sells today. (CT R1, CT R2)
- A total row: all units and their total value at cost, equal to the stock value used for the overall result. (CT R4)
- After day 5 nothing sells any more: sells today is 0 and everything counts as left.
- The overview updates after every accepted purchase, price change, trading day and new run.

## Out of scope

- Buying from the overview, reorder suggestions, warnings or alerts.
- Changing the demand rule, the catalogue or how stock is stored.
- Spoilage, stock limits, storage costs.

## Done when

1. **Overview:** For the example above, the overview shows exactly the numbers in the table, and the total value equals `stock_value`.
2. **Read only:** Building the overview leaves the run unchanged.
3. **Stock limits sales:** With 3 Sandwiches at the reference price, sells today is 3 and left after today is 0.
4. **Complete run:** After day 5, sells today is 0 for every product and left after today equals the units in stock.
