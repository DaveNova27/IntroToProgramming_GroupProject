"""Checks from specs/weather-visuals.md. The looks of the weather are pure functions (weather.js), so
they run for real with Node. The pieces around them are kept in place by source checks, because there
is no browser in the tests: the picture itself was checked in the browser (see the spec). The last
tests guard the rule the world leans on: the server sends no real weather before the day is open."""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

import app
import db
import logic

WORLD = Path(app.__file__).parent / "static" / "world"
NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="Node is not installed")


def run_node(tmp_path, body):
    """Run a script that imports weather.js and prints one JSON value."""
    script = tmp_path / "check.mjs"
    script.write_text(f'import * as weather from "{(WORLD / "weather.js").as_uri()}";\n{body}\n')
    done = subprocess.run([NODE, str(script)], capture_output=True, text=True, timeout=120)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


# ---- the looks -------------------------------------------------------------------------------

@needs_node
def test_every_weather_of_the_server_has_a_look_of_its_own(tmp_path):
    ids = list(logic.WEATHER)
    out = run_node(tmp_path, f"""
const ids = {json.dumps(ids)};
console.log(JSON.stringify({{
  known: weather.WEATHER_IDS,
  looks: ids.map((id) => JSON.stringify(weather.weatherLook(id))),
  neutral: JSON.stringify(weather.NEUTRAL),
}}));""")
    assert sorted(out["known"]) == sorted(ids)  # a new weather on the server needs a look here
    others = [look for wid, look in zip(ids, out["looks"]) if wid != "sun"]
    assert len(set(others)) == len(others)  # no two of them look the same
    assert out["neutral"] not in others  # and each differs from a day without weather


@needs_node
def test_sun_and_a_day_without_weather_look_the_same(tmp_path):
    out = run_node(tmp_path, """
console.log(JSON.stringify([JSON.stringify(weather.weatherLook("sun")), JSON.stringify(weather.NEUTRAL)]));""")
    assert out[0] == out[1]


@needs_node
def test_anything_that_is_no_weather_id_gives_the_neutral_look(tmp_path):
    out = run_node(tmp_path, """
const odd = [null, undefined, "", "snow", "__proto__", "constructor", "toString", "hasOwnProperty", 3, 0, {}, ["rain"], true];
console.log(JSON.stringify(odd.map((id) => weather.weatherLook(id) === weather.NEUTRAL)));""")
    assert out == [True] * 13


@needs_node
def test_mixing_two_looks_starts_at_one_and_ends_at_the_other(tmp_path):
    out = run_node(tmp_path, """
const a = weather.NEUTRAL, b = weather.weatherLook("storm"), half = weather.mixLooks(a, b, 0.5);
console.log(JSON.stringify({
  start: weather.mixLooks(a, b, 0) === a, end: weather.mixLooks(a, b, 1) === b,
  below: weather.mixLooks(a, b, -2) === a, above: weather.mixLooks(a, b, 7) === b,
  rain: half.rain, shade: half.shade, sky: half.skyTop, keys: Object.keys(half).sort(), all: Object.keys(a).sort(),
  untouched: JSON.stringify(a) === JSON.stringify(weather.NEUTRAL),
}));""")
    assert out["start"] and out["end"] and out["below"] and out["above"] and out["untouched"]
    assert out["rain"] == pytest.approx(0.5) and 0 < out["shade"] < 1
    assert out["keys"] == out["all"]
    assert len(out["sky"]) == 3


# ---- rain ------------------------------------------------------------------------------------

@needs_node
def test_rain_falls_only_in_rain_and_storm_and_stays_in_the_picture(tmp_path):
    out = run_node(tmp_path, """
const sizes = [[1280, 800], [390, 700], [2400, 1300], [300, 180]];
const result = {};
for (const id of ["none", ...weather.WEATHER_IDS]) {
  const look = weather.weatherLook(id);
  let most = 0, least = Infinity, inside = true, whole = true;
  for (const [w, h] of sizes) for (let t = 0; t < 20000; t += 437) {
    const { far, near } = weather.rainStreaks(look, t, w, h);
    const count = (far.length + near.length) / 4;
    most = Math.max(most, count); least = Math.min(least, count);
    whole = whole && far.length % 4 === 0 && near.length % 4 === 0;
    for (const list of [far, near]) for (let i = 0; i < list.length; i += 2) {
      const x = list[i], y = list[i + 1];
      if (!(x >= -weather.RAIN_MARGIN && x <= w + weather.RAIN_MARGIN && y >= -weather.RAIN_MARGIN && y <= h + weather.RAIN_MARGIN)) inside = false;
    }
  }
  result[id] = { most, least, inside, whole };
}
console.log(JSON.stringify({ result, max: weather.MAX_STREAKS, empty: weather.rainStreaks(weather.weatherLook("storm"), 5, 0, 0) }));""")
    result = out["result"]
    assert out["max"] == 240
    for dry in ("none", "sun", "heat"):
        assert result[dry]["most"] == 0, dry
    for wet in ("rain", "storm"):
        assert 0 < result[wet]["least"] and result[wet]["most"] <= 240, wet
        assert result[wet]["inside"] and result[wet]["whole"], wet
    assert result["storm"]["most"] > result["rain"]["most"]  # a storm rains harder
    assert out["empty"] == {"far": [], "near": []}  # a canvas without a size


@needs_node
def test_the_same_moment_gives_the_same_rain_and_the_same_flash(tmp_path):
    out = run_node(tmp_path, """
const storm = weather.weatherLook("storm");
const rain = (t) => JSON.stringify(weather.rainStreaks(storm, t, 1280, 800));
const flashes = (day) => { const list = []; for (let t = 0; t < 120000; t += 50) list.push(weather.flashAt(storm, t, day)); return JSON.stringify(list); };
console.log(JSON.stringify({
  rainTwice: rain(4321) === rain(4321), rainMoves: rain(4321) !== rain(4400),
  flashTwice: flashes(3) === flashes(3), daysDiffer: flashes(3) !== flashes(4),
}));""")
    assert out == {"rainTwice": True, "rainMoves": True, "flashTwice": True, "daysDiffer": True}


# ---- lightning -------------------------------------------------------------------------------

@needs_node
def test_lightning_is_soft_and_rare_and_only_in_a_storm(tmp_path):
    out = run_node(tmp_path, """
const result = {};
for (const id of ["none", ...weather.WEATHER_IDS]) {
  const look = weather.weatherLook(id);
  let brightest = 0, count = 0, closest = Infinity, longest = 0;
  for (const day of [1, 2, 7, 15, 30]) {
    let last = -Infinity, lit = false, since = 0;
    for (let t = 0; t <= 600000; t += 50) {
      const flash = weather.flashAt(look, t, day);
      brightest = Math.max(brightest, flash);
      if (flash > 0 && !lit) { count++; closest = Math.min(closest, t - last); last = t; since = t; }
      if (flash > 0) longest = Math.max(longest, t - since);
      lit = flash > 0;
    }
  }
  result[id] = { brightest, count, closest, longest };
}
const storm = weather.weatherLook("storm");
console.log(JSON.stringify({ result, max: weather.FLASH_MAX, odd: [weather.flashAt(storm, -5, 1), weather.flashAt(storm, NaN, 1)] }));""")
    assert out["max"] == 0.25
    for calm in ("none", "sun", "rain", "heat"):
        assert out["result"][calm]["count"] == 0 and out["result"][calm]["brightest"] == 0, calm
    storm = out["result"]["storm"]
    assert storm["count"] > 50  # it does flash: 5 days of 10 minutes
    assert 0 < storm["brightest"] <= 0.25
    assert storm["closest"] >= 6000  # never two flashes within 6 seconds
    assert storm["longest"] <= 500  # a flash is over within half a second
    assert out["odd"] == [0, 0]


# ---- no rain indoors ---------------------------------------------------------------------------

@needs_node
def test_only_a_wing_whose_roof_fades_is_a_dry_place(tmp_path):
    out = run_node(tmp_path, """
const parts = [
  { wing: "nova", x: 11.5, y: 1.2, w: 7.5, h: 8, z: 78 }, { wing: "nova", x: 19, y: 1.2, w: 8, h: 8, z: 96 },
  { wing: "hub", x: 27.5, y: 9.2, w: 6, h: 5, z: 56 }, { wing: "dorm", x: 36, y: 10, w: 4, h: 4, z: 50 },
];
const dry = (roofs) => weather.shelters(parts, roofs).map((p) => [p.x, p.y, p.w, p.h, p.z, p.dry]);
console.log(JSON.stringify({
  closed: dry({ nova: 1, hub: 1, dorm: 1 }),
  gone: dry({ nova: 0, hub: 1, dorm: 1 }),
  half: dry({ nova: 1, hub: 0.5, dorm: 1 }),
  dorm: dry({ nova: 1, hub: 1, dorm: 0 }),
  noEntry: dry({}),
  unknown: dry({ castle: 0, __proto__: 0 }),
  nothing: [weather.shelters(undefined, { nova: 0 }), weather.shelters(parts, undefined), weather.shelters(parts, null)],
}));""")
    assert out["closed"] == []  # it rains on a closed roof as everywhere
    assert out["gone"] == [[11.5, 1.2, 7.5, 8, 78, 1], [19, 1.2, 8, 8, 96, 1]]  # every part of the open wing, fully dry
    assert out["half"] == [[27.5, 9.2, 6, 5, 56, 0.5]]
    assert out["dorm"] == [[36, 10, 4, 4, 50, 1]]  # the Dorm counts as a wing
    assert out["noEntry"] == []  # a wing without an entry is closed (scene.js: roofOf)
    assert out["unknown"] == []
    assert out["nothing"] == [[], [], []]


# ---- the pieces around the looks (source checks) -----------------------------------------------

def source(name):
    return (WORLD / name).read_text()


def test_the_looks_are_pure_and_use_nothing_random_or_slow():
    text = source("weather.js")
    for banned in ("Math.random", "shadowBlur", "filter", "document", "window", "fetch(", "Date.now", "performance."):
        assert banned not in text, banned
    assert not re.search(r"^\s*import\b", text, re.MULTILINE)  # it stands alone, so Node can run it
    # what draws the weather has no blur and nothing random either (spec smooth-frames)
    for name in ("environment.js", "render.js"):
        for banned in ("Math.random", "shadowBlur", "ctx.filter"):
            assert banned not in source(name), (name, banned)


def test_nothing_is_loaded_from_outside_for_the_weather():
    for name in ("weather.js", "environment.js", "render.js"):
        text = source(name)
        assert "new Image" not in text and "FontFace" not in text and "url(" not in text, name
        # the only address in these files is the credit for Felix' project, in a comment
        for address in re.findall(r"https?://[^\s)]+", text):
            assert address == "https://github.com/felix-anthes-png/nova-beach-ventures", (name, address)
        for target in re.findall(r"""from\s+["']([^"']+)["']""", text):
            assert target.startswith("./"), (name, target)


def test_the_world_takes_the_weather_from_the_server_s_answer_only():
    # one place writes it, from state.weather (which the server leaves empty until the day is open)
    writers = {path.name: re.findall(r"scene\.weather\s*=[^=].*", path.read_text()) for path in WORLD.glob("*.js")}
    writers = {name: lines for name, lines in writers.items() if lines}
    assert list(writers) == ["ui.js"], writers
    assert len(writers["ui.js"]) == 1 and "state.weather" in writers["ui.js"][0], writers
    assert "outlook" not in writers["ui.js"][0]
    # the forecast is for the display only: no drawing code reads it
    for path in WORLD.glob("*.js"):
        if path.name != "ui.js":
            assert "outlook" not in path.read_text(), path.name
    # the drawing reads the look, never the state's weather by itself
    for name in ("environment.js", "render.js"):
        assert "state.weather" not in source(name) and "scene.weather" not in source(name), name
        assert "scene.look" in source(name), name


def test_the_weather_fades_in_and_stands_still_with_reduced_motion():
    main = source("main.js")
    assert "updateWeather(dt)" in main and "mixLooks(" in main and "weatherLook(" in main
    assert re.search(r"weatherFade\s*=\s*weatherShown === undefined \|\| reducedMotion \? 1 : 0", main)
    env = source("environment.js")
    assert "rainStreaks(look, reducedMotion ? 0 : t" in env  # the rain stands
    assert re.search(r"function drawWeatherFlash\(t, w, h\) \{\s*if \(reducedMotion\) return;", env)  # no flash
    assert "shelters(world.nova?.parts, scene.roofs)" in env  # the dry places come from the roofs
    render = source("render.js")
    for call in ("drawWeatherShade(w, h)", "drawWeatherFall(t, w, h)", "drawWeatherFlash(t, w, h)"):
        assert call in render, call


# ---- the server: no real weather before the day is open ---------------------------------------

@pytest.fixture
def client(tmp_path, monkeypatch):
    """A test client on a temporary database, with the editor switched on (to fix a seed or a weather)."""
    path = tmp_path / "run.db"
    db.save(logic.new_state(7), path)
    real_save, real_new = db.save, db.save_new_run
    monkeypatch.setattr(app, "load_run", lambda: db.load(path))
    monkeypatch.setattr(app.db, "save", lambda s: real_save(s, path))
    monkeypatch.setattr(app.db, "save_new_run", lambda s: real_new(s, path))
    monkeypatch.setenv("CT_EDITOR", "1")
    return app.app.test_client()


def seeds_with(weather_a, weather_b):
    """Two seeds whose first day has these two kinds of real weather."""
    found = {}
    for seed in range(1, 400):
        real = logic.day_context(logic.new_state(seed))["weather"]
        found.setdefault(real, seed)
        if weather_a in found and weather_b in found:
            return found[weather_a], found[weather_b]
    raise AssertionError("no such seeds")


def test_the_server_sends_the_weather_only_once_the_day_is_open(client):
    for real, seed in zip(("storm", "sun"), seeds_with("storm", "sun")):
        assert client.post("/api/editor/reset", json={"confirm": True, "seed": seed}).status_code == 200
        before = client.get("/api/state").get_json()
        assert before["weather"] is None, real  # nothing for the world to draw
        opened = client.post("/api/day/open", json={}).get_json()["state"]
        assert opened["weather"]["id"] == real
        assert client.get("/api/state").get_json()["weather"]["id"] == real


def test_a_fixed_weather_is_the_one_the_world_gets(client):
    for wid in logic.WEATHER:
        assert client.post("/api/editor/reset", json={"confirm": True, "seed": 11}).status_code == 200
        assert client.post("/api/editor/weather", json={"weather": wid, "event": "none"}).status_code == 200
        assert client.get("/api/state").get_json()["weather"] is None  # still closed
        assert client.post("/api/day/open", json={}).get_json()["state"]["weather"]["id"] == wid
