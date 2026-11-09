"""The stock card of the campus page can be folded away (specs/collapsible-stock-panel.md).
The page is drawn in a browser, so like the other page tests these read the files."""

import re
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "static"
HTML = (STATIC / "map.html").read_text()
CSS = (STATIC / "map.css").read_text()
UI = (STATIC / "world" / "ui.js").read_text()


def card_html():
    match = re.search(r'<section id="hud-stock-card".*?</section>', HTML, re.S)
    assert match, "the stock card section is missing"
    return match.group(0)


def test_the_card_has_a_toggle_button_before_the_rows():
    card = card_html()
    button = re.search(r'<button id="stock-toggle"[^>]*>', card)
    assert button
    assert 'type="button"' in button.group(0)
    assert 'aria-expanded="true"' in button.group(0)
    assert card.index("stock-toggle") < card.index('id="hud-stock"')


def test_the_redrawn_rows_are_outside_the_toggle():
    assert '<div id="hud-stock"></div>' in card_html()
    redraw = re.search(r'\$\("#hud-stock"\)\.innerHTML = `(.*?)`;', UI, re.S)
    assert redraw
    assert "stock-toggle" not in redraw.group(1)
    assert "<h3>" not in redraw.group(1)  # the title now lives in the button


def test_the_folded_card_hides_the_rows_in_both_layouts():
    assert re.search(r"\.hud-stock\.collapsed #hud-stock\s*\{\s*display:\s*none", CSS)
    narrow = CSS[CSS.index("@media (max-width"):] if "@media (max-width" in CSS else CSS
    assert ".hud-stock.collapsed" in narrow


def test_the_choice_is_remembered_safely():
    assert "ct-stock-folded" in UI
    assert len(re.findall(r"try \{[^}]*ct|try \{[^}]*STOCK_FOLDED_KEY", UI)) >= 2
    assert "wireStockToggle();" in UI


def test_the_toggle_keeps_its_state_for_screen_readers():
    assert 'setAttribute("aria-expanded"' in UI


def test_the_preview_window_still_hides_the_card():
    assert re.search(r"body\.preview[^{]*\.hud-stock", CSS)
