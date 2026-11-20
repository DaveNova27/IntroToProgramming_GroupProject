# The dashboard in the campus look, shorter (`dashboard-look`)

Asked for by Felix on 2026-11-20 (David: "the dashboard still has the design of the very old version").
Two drafts were built as a prototype and compared on screenshots; Felix chose draft B: the look of the
campus and a shorter page. Everything the dashboard shows stays; nothing changes on the server.

## What

1. **The look (`static/style.css`):** the colour tokens of the campus (`map.css`): dark petrol
   `#102f39` for the header and the cash card, lime `#bce65f` as accent, cream `#f6f1e4` cards on
   `#e9e3d2`; 4 px corners and a hard offset shadow (`3px 3px`); labels (KPI names, section titles,
   "SELLING PRICE") in the small mono capitals of the campus HUD; KPI numbers in the mono font. The
   cash chart's bars are petrol instead of purple. The old product tokens (`--sandwich`, `--coffee`,
   `--cookie`) and the background tint made from them go. The dashboard's own dark mode goes, so there
   is one look, like the campus.
2. **The header (`static/index.html`, `style.css`):** a dark bar like the campus top bar. The logo is a
   lime square with "CT" (as on the campus) instead of 🥪, the line under the name says "Carcavelos ·
   Nova SBE · 30-day season" instead of "your snack stand season". The days 1 to 30 are small square
   chips (done: lime, today: lime outline). The tab icon of both pages becomes "CT" too.
3. **Shorter page (`index.html`, `app.js`, `style.css`), from a width of 900 px:**
   - the stock overview card goes (its numbers stand on the product cards and in the campus's stock
     card): the section in `index.html` and `renderStockOverview` in `app.js`. The server still sends
     `stock_overview`, nothing on the server changes;
   - the shop popularity stands beside the campus window (7 + 5 columns), the shops one under another;
   - the products take 8 columns with 3 cards per row (2 between 900 and 1100 px, see "Decide" 6), the
     "Open for day N" panel 4 columns beside them.
4. **Compact product cards (`app.js`, `style.css`):** the price curve moves into "Why this number?"
   (it opens with it); the "Buy stock" block of every card goes. Instead there is **one** button
   "Go to the order PC" (`data-go-order`, the same message to the campus as today) in the head of
   "Your stand".
5. **Products grouped by shop (`app.js`):** inside "Your stand" a small heading per unlocked shop
   (Cafe, Beach Cafe, Merchandise, Surf Shop) and its products under it, in shop order. Which product
   belongs to which shop comes from `state.shops[i].products`; with only the Cafe there is no heading
   (as on the campus's stock card).
6. **Gross profit per shop (`app.js`):** the chart "Gross profit per day" shows one column per shop and
   day (up to 4 colours) instead of one per product (up to 12). A shop's colour is the colour of its
   first product. The tooltip lists the shops of the day and the total; the legend lists the shops.
   The numbers are the sum of the day's `lines` per shop, all from the server's history.
7. **Phones (`style.css`):** the layout below 900 px stays as today (one column); the KPI numbers get
   a size that fits ("€1,000.00" does not break into two lines at 375 px).

## Decide

1. **Draft B, as on the screenshots of 2026-11-20**, plus the points 2, 5 and 6 that the prototype
   could not show (they need HTML or JS).
2. **Keep what other parts and old tests rely on:** the element ids (`pop-grid`, `event-chip`,
   `kpi-*`, `product-grid`, `cash-chart`, `profit-chart`, …), `data-go-order` and the text "Go to the
   order PC" in `app.js` (`tests/test_order_at_warehouse.py`), no inline script or handler in
   `index.html` (`tests/test_deploy_ready.py`). No old test changes.
3. **Grouping in `app.js` itself:** the campus has `stockGroups` in an ES module
   (`static/world/stock_groups.js`); the dashboard is a classic script and cannot import it. The
   dashboard's grouping is a few lines over `state.shops` with the same rule (shop order, only
   unlocked shops, a product no shop names is kept at the end).
4. **One look:** the dark mode of the dashboard goes; the campus never had one.
5. **Tests:** the new file `tests/test_dashboard_look.py`.
6. **After the AI review (2026-11-20):** from 900 px the products show two cards per row and three only
   from 1100 px (a third card was about 200 px wide on a 1024 px laptop); the KPI numbers are 22 px
   while three stand in a row (560 to 900 px) so "€1,000.00" stays inside its card; on a complete run
   the card keeps a "Price curve" fold with the curve; under a shop heading the product names are one
   heading level lower (screen readers hear the grouping); the "Open" panel starts level with the head
   of "Your stand" instead of a fixed offset that missed the first card (the head's height changes with
   the width and the shop headings).

## Out of scope

- The campus page and its panels; the demo mode; removing the dashboard.
- New numbers or rules; the server, `app.py` and `logic.py` stay as they are.
- The tables "Last day's result" and "Run history" and the badges: they only take the new look.

## Done when

1. **Look:** header, cards, labels, numbers and charts in the campus look; no 🥪 and no "snack stand"
   on the page; no dark mode block in `style.css`.
2. **Shorter:** with the run of the screenshots (day 12, three shops) the page at 1280 px is clearly
   shorter than today's (about 3,700 instead of 4,500 px); no stock overview card; popularity beside the
   campus window; one order button.
3. **Grouped and per shop:** products under one heading per unlocked shop; the profit chart has one
   colour per shop and its tooltip adds up to the day's gross profit.
4. **Nothing lost:** prices can still be set and saved, "Why this number?" opens with the curve, the
   order button walks to the PC on the campus, new run, campus window, charts, tables and badges work.
5. **Tests:** `tests/test_dashboard_look.py` (tokens and no dark mode, header, no stock overview, one
   order button, the curve inside the details, grouping by shop, profit series per shop, the layout
   from 900 px, the phone size of the KPI numbers); the full suite passes, old tests untouched.
6. **Checked in the browser:** laptop (1280 px) and phone (375 px) with a played run; saving a price;
   the order button; no console errors.

## Security

Display only: shop and product names come from the server's tables and are escaped with `esc()` like
every other text; no new input, request or rule; nothing loaded from outside.
