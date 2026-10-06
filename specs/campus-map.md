# Fourth feature: 3D campus map (Campus Tycoon)

**Product:** Campus Tycoon, a snack stand on campus. **User:** the player running the stand.

## Planning answers

1. **Product and user:** Campus Tycoon; the player who runs the stand.
2. **Trigger:** the player opens the campus map and buys stock, sets prices or opens the stand there.
3. **Before:** an active or complete run exists (the same saved run the dashboard shows).
4. **Rule:** the map is a second screen for the same rules. Every action goes through the same checks as on the dashboard; a rejected action shows the reason, plays no animation and changes nothing.
5. **After:** an accepted action is saved exactly as on the dashboard, then animated on the map. The map shows the same cash, stock, prices and day as the dashboard.
6. **Restart:** the map loads the saved run like the dashboard does; animations are never replayed after a reload.

## Why

Running the stand should feel like a tycoon game: the player sees their kiosk in a 3D campus, a delivery truck bringing what they ordered and students buying, instead of only numbers.

## What

- A 3D campus the player can rotate and zoom: the kiosk with its menu board (prices), a storage shed, campus buildings, paths, trees and a road. (presentation only)
- The storage shed shows one pallet per product, each with a sign showing the product's symbol and its units in stock; crates carry the product's symbol.
- A head-up display with day, cash, overall result and stock per product.
- Order stock: choose product and quantity, see the total cost, order. Accepted: a truck drives in, unloads crates onto the product's pallet, cash goes down. (CT02, CT R3)
- Set prices on the menu board, with the expected demand per day. (CT03, CT R1)
- Open for the day: students walk to the window of the product they want and say what they buy; the product is handed over, a coin shows the price, cash and the pallet update, and a live sales ticker lists every sale with units sold per product. Students who find a product sold out or priced above twice the reference turn away and say why. Afterwards a day summary shows units sold, revenue, cost of goods sold and gross profit. (CT04, CT R2, CT R4, CT R5)
- After day 5: a final result card and "Start a new run" with confirmation. (CT05, CT01)
- A skip button finishes the running animation at once; with "reduce motion" switched on, no animation plays.
- Links between the map and the dashboard.

## Out of scope

- Any change to the rules, the catalogue or what is stored.
- Sound, music, building upgrades, decorations to buy, competitors, weather events.
- Working without an internet connection (the 3D library is loaded from a CDN; the dashboard keeps working offline).

## Done when

1. **Same rules:** All existing tests pass unchanged; the map uses only the existing API.
2. **Order:** Ordering 10 Sandwiches with €100 plays the truck, ends with cash €80 and the Sandwich pallet sign showing 10, the same as the dashboard shows.
3. **Rejected order:** Ordering more than the cash allows shows the reason, plays no truck and leaves cash and stock unchanged.
4. **Trading day:** Opening day 1 with 10 Sandwiches at €4 shows 10 Sandwich sales in the ticker, then a summary with revenue €40, cost of goods sold €20, gross profit €20; afterwards the map shows cash €120, day 2 and an empty Sandwich pallet.
5. **Reload:** Reloading the map after a trading day shows the saved run without replaying anything.
