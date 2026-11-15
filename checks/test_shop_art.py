"""Exercise the map signs and actual drawing commands with server shop responses."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

import app
import logic
import world


@pytest.mark.skipif(shutil.which("node") is None, reason="Node runs the browser modules")
def test_shops_follow_the_owned_products_and_level(tmp_path):
    root = Path(app.__file__).parent
    shutil.copytree(root / "static/world", tmp_path / "world")
    shutil.copy(root / "checks/shop_art.mjs", tmp_path)
    (tmp_path / "package.json").write_text('{"type":"module"}')
    fresh = logic.new_state()
    rich = logic.editor_cash(fresh, "set", 2_000_000)
    cases = {}
    for sid in logic.SHOPS:
        opened = rich if sid == "cafe" else logic.unlock_shop(rich, sid)
        cases[sid] = {
            item: app.shops_view(logic.buy_upgrade(opened, sid, item))
            for item in logic.SHOPS[sid]["window"] if item != "staff_2"
        }
        cases[sid]["base"] = app.shops_view(opened)
    data = {"world": world.world_view(), "fresh": app.shops_view(fresh), "cases": cases}
    done = subprocess.run(
        ["node", "shop_art.mjs"], cwd=tmp_path, input=json.dumps(data),
        text=True, capture_output=True, timeout=30,
    )
    assert done.returncode == 0, done.stderr
