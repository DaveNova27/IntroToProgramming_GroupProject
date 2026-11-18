"""Checks from specs/stock-by-shop.md ("Done when"): the stock card is grouped by shop and stays foldable.

The grouping is a pure module (static/world/stock_groups.js), run here with Node against the API's own
answer; the page itself is checked in its source like the other page tests (tests/test_stock_panel.py).
"""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

import app
import logic

STATIC = Path(app.__file__).parent / "static"
GROUPS = STATIC / "world" / "stock_groups.js"
UI = (STATIC / "world" / "ui.js").read_text()
CSS = (STATIC / "map.css").read_text()
NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="Node is not installed")


def run_groups(products, shops):
    """stockGroups(products, shops) in Node; also reports whether the inputs were changed."""
    script = (
        f"import {{ stockGroups }} from {json.dumps(GROUPS.as_uri())};"
        f"const products = {json.dumps(products)}, shops = {json.dumps(shops)};"
        "const before = JSON.stringify([products, shops]);"
        "const groups = stockGroups(products, shops);"
        "console.log(JSON.stringify({groups, same: before === JSON.stringify([products, shops])}));"
    )
    done = subprocess.run([NODE, "--input-type=module", "-e", script], capture_output=True, text=True, timeout=60)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


def unlock_all(state):
    """Every shop unlocked with every product of its window, as the demo editor can set it."""
    for sid in logic.SHOPS:
        state["shops"][sid]["unlocked"] = True
        state["shops"][sid]["products"] = logic.shop_product_ids(sid)
    return state


def shape(result):
    return [(g["shop"], g["name"], [p["id"] for p in g["products"]]) for g in result["groups"]]


@needs_node
def test_a_new_run_has_one_group_the_cafe_with_its_products():
    view = app.view(logic.new_state(1))
    result = run_groups(view["products"], view["shops"])
    cafe = next(s for s in view["shops"] if s["id"] == "cafe")
    assert shape(result) == [("cafe", "Cafe", cafe["products"])]
    assert result["groups"][0]["heading"] == ""  # the Cafe alone: no heading, the card looks as before
    assert result["same"]


@needs_node
def test_from_two_shops_on_every_named_group_has_its_heading():
    products = [{"id": "coffee"}, {"id": "beer"}, {"id": "mystery"}]
    shops = [{"id": "cafe", "name": "Cafe", "unlocked": True, "products": ["coffee"]},
             {"id": "beach_cafe", "name": "Beach Cafe", "unlocked": True, "products": ["beer"]}]
    headings = [g["heading"] for g in run_groups(products, shops)["groups"]]
    assert headings == ["Cafe", "Beach Cafe", ""]  # the group without a shop has no name to show


@needs_node
def test_every_shop_unlocked_gives_one_group_per_shop_in_shop_order_and_catalogue_order():
    view = app.view(unlock_all(logic.new_state(1)))
    result = run_groups(view["products"], view["shops"])
    assert [g[0] for g in shape(result)] == list(logic.SHOPS)
    order = list(logic.CATALOGUE)
    for sid, name, ids in shape(result):
        assert name == logic.SHOPS[sid]["name"]
        assert set(ids) == set(logic.shop_product_ids(sid))
        assert ids == sorted(ids, key=order.index)  # as the API lists them
    every = [pid for _, _, ids in shape(result) for pid in ids]
    assert sorted(every) == sorted(p["id"] for p in view["products"])  # each product once, none lost
    assert result["same"]


@needs_node
def test_only_the_unlocked_shops_appear_two_shops_give_two_groups():
    state = logic.new_state(1)
    state["shops"]["surf_shop"]["unlocked"] = True
    state["shops"]["surf_shop"]["products"] = [logic.SHOPS["surf_shop"]["start_product"]]
    view = app.view(state)
    result = run_groups(view["products"], view["shops"])
    assert [g[0] for g in shape(result)] == ["cafe", "surf_shop"]
    assert shape(result)[1][2] == [logic.SHOPS["surf_shop"]["start_product"]]  # only what was bought


@needs_node
def test_a_product_no_unlocked_shop_names_is_kept_in_a_last_group_without_a_name():
    products = [{"id": "coffee"}, {"id": "mystery"}]
    shops = [{"id": "cafe", "name": "Cafe", "unlocked": True, "products": ["coffee"]},
             {"id": "surf_shop", "name": "Surf Shop", "unlocked": False, "products": ["mystery"]}]
    result = run_groups(products, shops)
    assert shape(result) == [("cafe", "Cafe", ["coffee"]), (None, "", ["mystery"])]
    assert result["same"]


@needs_node
def test_no_empty_group_and_no_product_twice():
    products = [{"id": "coffee"}]
    shops = [{"id": "cafe", "name": "Cafe", "unlocked": True, "products": ["coffee"]},
             {"id": "copy", "name": "Copy", "unlocked": True, "products": ["coffee"]},
             {"id": "beach_cafe", "name": "Beach Cafe", "unlocked": True, "products": ["beer"]}]
    assert shape(run_groups(products, shops)) == [("cafe", "Cafe", ["coffee"])]


def redraw():
    match = re.search(r'\$\("#hud-stock"\)\.innerHTML = `(.*?)`;', UI, re.S)
    assert match
    return match.group(1)


def test_the_card_is_drawn_from_the_groups_with_a_named_group_per_shop():
    assert 'import { stockGroups } from "./stock_groups.js";' in UI
    assert "stockGroups(state.products, state.shops)" in UI
    body = redraw()
    assert 'role="group"' in body and "aria-label" in body
    assert "esc(g.name)" in body and "esc(g.heading)" in body  # escaped like every text on the card
    assert 'class="stock-group-name" aria-hidden="true"' in body  # the name is said once, by the group
    assert "<h3>" not in body and "stock-toggle" not in body  # the fold of the card is untouched


def test_the_tall_card_scrolls_inside_and_the_narrow_bar_shows_dividers():
    assert re.search(r"#hud-stock\s*\{[^}]*max-height:[^}]*overflow-y:\s*auto", CSS)
    start = CSS.index("  .hud-stock { top: auto;")
    narrow = CSS[start:CSS.index("\n}", start)]
    assert ".stock-group-name { display: none; }" in narrow
    assert re.search(r"\.stock-group \+ \.stock-group \{[^}]*border-left", narrow)
    # review findings: the bar scrolls instead of running past the edge, each shop spreads its rows
    assert re.search(r"\.hud-stock #hud-stock \{[^}]*min-width: 0;[^}]*overflow-x: auto", narrow)
    assert re.search(r"\.stock-group \{[^}]*flex: 1 0 auto;[^}]*justify-content: space-around", narrow)


def test_the_badge_card_moves_beside_a_stock_card_too_tall_to_stand_under():
    assert "besideTallStock(area) ?? { top: badgeTop(), left: null }" in UI
    beside = UI.split("function besideTallStock(area) {")[1].split("\n}\n")[0]
    assert "window.innerHeight - BADGE_FLOOR" in beside  # only when it would run off the bottom
    assert "r.top >= bar + 80" in beside  # never beside the phone's bottom bar
    assert "window.innerWidth - 10" in beside  # and only where it fits


@needs_node
def test_the_modules_still_parse():
    for path in (GROUPS, STATIC / "world" / "ui.js"):
        done = subprocess.run([NODE, "--check", str(path)], capture_output=True, text=True, timeout=60)
        assert done.returncode == 0, (path.name, done.stderr)
