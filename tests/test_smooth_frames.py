"""Checks from specs/smooth-frames.md: nothing in the world may use the canvas blur filter."""

import re
from pathlib import Path

import app

WORLD = Path(app.__file__).parent / "static" / "world"


def test_no_canvas_filter_in_the_world():
    # ctx.filter = "blur(...)" is rasterised on the CPU path of a big canvas: 35 shadows a frame
    # took 66 to 160 ms (audit P1). A guard like the one for Math.random.
    pattern = re.compile(r"\.filter\s*=(?!=)")
    hits = [f"{path.name}:{n}" for path in sorted(WORLD.glob("*.js"))
            for n, line in enumerate(path.read_text().splitlines(), 1) if pattern.search(line)]
    assert hits == []
