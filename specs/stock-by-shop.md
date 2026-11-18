# Stock card grouped by shop (`stock-by-shop`)

Asked for by Felix on 2026-11-18: the stock card at the top left of the campus page lists every product
in one long list. With several shops and their upgrades that is up to 12 rows without telling which shop
a product belongs to. The list should be split into the shops. The card must stay foldable.

## What

- **Groups (`static/world/ui.js`, the redraw of `#hud-stock`):** the rows are grouped by shop, in the
  order of the shops (Cafe, Beach Cafe, Merchandise, Surf Shop). Each group starts with a small heading
  with the shop's name; under it the rows of that shop's products, drawn exactly as today (emoji, name,
  customers today, units).
- **Which product belongs where:** from the API answer that is already there: `state.shops[i].products`
  (ids) and `state.shops[i].name`. No new field, no change in `app.py` or `logic.py`.
- **Only what the player owns (Felix, 2026-11-18):** a shop appears only once it is unlocked, and in it
  only the products the player has bought (as today, `state.products` holds only owned products). One
  shop: only that shop; two shops: only those two; and so on. A locked shop never shows an empty group.
- **A pure helper (`static/world/stock_groups.js`, new):** `stockGroups(products, shops)` returns
  `[{shop, name, products}]` in shop order, with the product objects in catalogue order and nothing
  invented: a product without an unlocked shop is not dropped but goes into a last group without a
  name. No drawing, no DOM, so Node can test it.
- **Folding stays as it is:** the button `#stock-toggle`, `aria-expanded`, the remembered choice
  (`ct-stock-folded`) and the folded chip do not change. Folded, the whole card with all groups is
  hidden.
- **Narrow screens (the bottom bar, `max-width: 760px`):** no shop names (names are hidden there
  already); a thin divider between the groups so the shops stay apart. Each group spreads its rows as
  the old bar did (the Cafe alone fills the bar as before); a bar wider than the screen scrolls
  sideways.

## AI review findings (fixed)

1. On phones the Cafe's rows bunched up at the left: each group now grows and spreads its rows.
2. The phone bar did not scroll, it ran past the edge: `min-width: 0` on the list.
3. Under a tall card the badge card ran off the bottom of short windows: it moves beside the card.
4. Screen readers heard the shop's name twice: the visible heading is `aria-hidden`.
5. A classic scrollbar took width from the 214px card: a thin scrollbar.
6. The spec described the heading's markup differently than built: Decide 2 updated.
7. The "heading from two shops on" rule was only found as text in the source: it is now `heading` in
   `stockGroups` and tested in Node.

## Decide

1. **Heading only from two shops on:** with only the Cafe the card looks exactly as today; a single
   heading "Cafe" over three rows tells nothing. From the second unlocked shop on every group has its
   heading.
2. **The heading is not a `<h3>`:** `tests/test_stock_panel.py` checks that the redrawn rows contain no
   `<h3>` (the card's title lives in the button). Each shop is a wrapper `<div class="stock-group">`
   with `role="group"` and `aria-label` = the shop's name, so screen readers hear the shop; the visible
   heading inside it is a `<div class="stock-group-name" aria-hidden="true">`, so the name is said once.
   Whether there is a heading is decided in `stockGroups` (`heading`), so Node tests it.
3. **Tall card:** with all four shops fully upgraded the card has 12 rows and 4 headings. It gets a
   `max-height` of the window minus the top bar and the bottom bar, and scrolls inside if needed (a
   thin scrollbar), so it never covers the toolbar. The badge card normally stands below it
   (`placeBadge`); where it would run off the bottom of a short window, it stands right of the stock
   card under the top bar instead.
4. **One fold for the whole card:** single shops cannot be folded on their own (see Out of scope).
5. **Tests:** the new file `tests/test_stock_by_shop.py`. No old test changes; the checks in
   `tests/test_stock_panel.py` (toggle before the rows, no `<h3>`, folded rows hidden in both layouts,
   remembered choice) must keep passing unchanged.

## Out of scope

- Folding single shops; sorting or filtering the rows.
- Showing how full each shop's storeroom is (a rule of `logic.py`; it would need a new field from the
  API, a spec of its own if wanted).
- The order window, the morning card and the dashboard's stock list.

## Done when

1. **Grouped:** with two or more unlocked shops, the card shows one heading per unlocked shop and under
   it exactly that shop's owned products; no locked shop appears; with only the Cafe it looks as before.
2. **Foldable:** folding and unfolding works as before, also after a reload (remembered choice).
3. **Tests:** `tests/test_stock_by_shop.py`
   - `stockGroups` (run in Node): shop order, products in catalogue order, locked shops left out, one
     unlocked shop gives one group, an unknown product is kept in the last group, input unchanged;
   - the page: the redraw uses `stockGroups`, the heading has `role="group"` and an `aria-label`, the
     narrow layout has the divider, the card has a `max-height` and `overflow-y: auto`;
   - the full suite passes, `tests/test_stock_panel.py` untouched.
4. **Checked in the browser:** with the demo editor (all shops unlocked, every upgrade), the card shows
   four groups on a laptop width and dividers on a phone width; folding works; no console errors.

## Security

Display only: the shop names and product names come from the server's own tables and are escaped with
`esc()` like every other text on the card. No input, no rule, nothing loaded from outside, no
randomness.
