# Several shops: unlock and upgrade (`shop-unlock`, issue #17)

## What

The game gets several shops. A run starts with one shop, the Cafe, on level 1
with one product (the coffee). More shops are unlocked with money. Each shop has a
window where more products and employee places can be bought with money. Every
purchase raises the shop's level by 1.

The shops, their products, prices, unlock prices, storeroom and counter space are one
data table in `logic.py` (`SHOPS`), with the products in `CATALOGUE`. All money is
integer cents. The shops are the team's list of 2026-11-05: Cafe (coffee, cake, bagel),
Beach Cafe (beer, coke zero, sandwich), Merchandise (hoodie, t-shirt, cap) and Surf Shop
(surfboard, wetsuit, surf lesson). Each shop starts with its first product; the other two
are bought in its window. All prices are placeholders to balance later. The state gets `shops: {id: {unlocked, level, products, staff_places}}`.
`unlock_shop(state, shop)` and `buy_upgrade(state, shop, item)` are pure functions that
return a new state. `buy`, `set_price`, `trade_day`, `stock_overview` and `stock_value`
only count products the player has. The server, the saving, the window and the tests
follow in the next work steps of the issue (`POST /api/shop/unlock`,
`POST /api/shop/upgrade`, `shops` table, window in the world UI).

Employee places are only stored (`staff_places`); employees themselves come with
`staff` (#20). Storeroom (100 units) and counter (20 units) are only data here; they
take effect with `shop-process` (#36).

## Out of scope

How a day runs inside a shop (#36), employees (#20), shop locations on the map (#28),
shop art (#18), guests, balancing the numbers.

## Done when

1. A new run has the Cafe on level 1, only the coffee, and €100.
2. Unlocking a shop and buying from a window cost exactly the listed price, and the
   level rises by 1 with each purchase.
3. Refused, and the saved run stays identical: too little cash, a shop already
   unlocked, an item already bought, an unknown id, a wrong type, a product not yet
   owned (buy and set price), any purchase after the last day.
4. Shops and purchases survive a restart, and a save from before this spec still loads.
5. All money stays integer cents. The state stays complete and settable.
6. `uv run pytest` passes, and every changed old test is named in the PR.
7. In the browser: the window works, a refused purchase shows why, the dashboard still
   works, no console errors.
8. PR opened against `main`, AI code review done and its findings handled.

## Security

The server checks cash, shop id and item id, each from a fixed list. A locked shop, or a
product the player does not have yet, cannot be used by a crafted request. Prices come
from the server only. A rejected action changes no saved data.
