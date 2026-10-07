# Combined stock order

## What

The 3D map order panel shows Sandwiches, Coffee and Cookies together. The
player can set a quantity for every product and submit one combined order.
The full price is checked before anything is saved. An accepted order updates
cash and all selected stock in one saved action, then one delivery truck per
selected product arrives and unloads in catalogue order.

## Out of scope

Changing product costs, storage limits, the dashboard product cards, delivery
fees, discounts, suppliers or the trading rules.

## Done when

1. One map panel accepts quantities for all three products and shows the
   combined cost before ordering.
2. An affordable combined order changes cash and all selected stock together.
3. An invalid or unaffordable combined order changes no saved data and starts
   no delivery animation.
4. Selected delivery trucks arrive and unload one after another.
5. Existing tests and finite-price regression checks pass unchanged.
