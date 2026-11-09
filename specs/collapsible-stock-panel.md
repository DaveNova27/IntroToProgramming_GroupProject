# The stock card can be folded away (`collapsible-stock-panel`)

Asked for by Felix on 2026-11-09 after seeing the campus page: the stock card on the left is always
there and covers part of the campus. Screen only, no rule changes, no new API.

## What

The stock card of the campus page (`#hud-stock-card`) gets a toggle button in its header
(`#stock-toggle`, the word "Stock" and a small arrow).

- Click (or Enter / Space on the focused button): the rows are hidden and only a small chip
  with the title stays. Click again: the rows are back.
- The choice is remembered in this browser (`localStorage`, key `ct-stock-folded`). A browser
  that blocks the storage just starts with the card open; nothing breaks.
- The button carries `aria-expanded` and a title ("Hide the stock" / "Show the stock").
- The toggle sits outside `#hud-stock`, the part that is redrawn on every update, so a redraw
  never loses the choice.
- Narrow screens (the bottom bar layout): the same toggle, the collapsed chip sits at the left.
- In the small preview window of the dashboard (`body.preview`) the card stays hidden as before.

## Decide

1. **Where the choice is kept:** in the browser, not in the saved run. It is a view
   preference, not game state, so the demo mode, the editor and `/api/state` are untouched.
2. **Default:** open, as today.
3. **Tests:** the world is drawn in a browser, and these tests only read the files (as the
   other tests of the pages do). The new file `tests/test_stock_panel.py` checks the markup, the
   style rules and the script. No old test changes.

## Out of scope

- Folding other panels (toolbar, price panel, top bar).
- Changing what the card shows.
- A keyboard shortcut.

## Done when

1. **Toggle:** `map.html` has `#stock-toggle` (a `button`, `aria-expanded="true"`) inside
   `#hud-stock-card`, before `#hud-stock`.
2. **Redraw safe:** `renderHud` writes only `#hud-stock`; the toggle is not inside it.
3. **Folded look:** `.hud-stock.collapsed` hides `#hud-stock` and the narrow layout has a
   matching rule.
4. **Remembered:** `ui.js` reads and writes `ct-stock-folded` inside `try`/`catch`.
5. **Preview unchanged:** `body.preview .hud-stock` is still hidden.
6. **Checked in the browser:** fold, unfold, reload keeps the choice, no console errors, also at phone width.

## Security

No input from outside, no new request; the stored value is only compared with `"1"`.
