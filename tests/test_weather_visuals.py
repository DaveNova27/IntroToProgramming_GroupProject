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
def test_every_look_has_all_the_keys_and_cannot_be_changed(tmp_path):
    out = run_node(tmp_path, """
const keys = Object.keys(weather.NEUTRAL).sort();
const bad = [], loose = [], text = [];
for (const id of ["none", ...weather.WEATHER_IDS]) {
  const look = weather.weatherLook(id);
  if (JSON.stringify(Object.keys(look).sort()) !== JSON.stringify(keys)) bad.push(id + ": keys");
  for (const key of keys) {
    const value = look[key], reference = weather.NEUTRAL[key];
    if (Array.isArray(reference)) {
      if (!Array.isArray(value) || value.length !== 3 || !value.every((c) => Number.isFinite(c) && c >= 0 && c <= 255)) bad.push(id + ": " + key);
      if (!Object.isFrozen(value)) loose.push(id + ": " + key);
    } else if (!Number.isFinite(value)) bad.push(id + ": " + key);
  }
  if (!Object.isFrozen(look)) loose.push(id);
}
let threw = 0;
for (const change of [() => { weather.NEUTRAL.rain = 1; }, () => { weather.NEUTRAL.tintColor[0] = 0; }, () => { weather.weatherLook("heat").skyTop.push(1); }]) {
  try { change(); } catch { threw++; }
}
console.log(JSON.stringify({ bad, loose, threw, still: weather.NEUTRAL.rain === 0 && weather.NEUTRAL.tintColor[0] === 255 }));""")
    assert out["bad"] == []  # no look lacks a key, and every colour has three channels (mixLooks needs both)
    assert out["loose"] == []  # the looks share their colour lists, so those are frozen too
    assert out["threw"] == 3 and out["still"]  # a change is refused and nothing moved


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


@needs_node
def test_a_day_that_is_no_number_gives_no_flash_instead_of_a_white_screen(tmp_path):
    out = run_node(tmp_path, """
const storm = weather.weatherLook("storm");
const odd = [undefined, null, NaN, Infinity, "3", {}];
const all = odd.map((day) => { let most = 0; for (let t = 0; t < 120000; t += 50) { const f = weather.flashAt(storm, t, day); if (!(f >= 0 && f <= weather.FLASH_MAX)) return "bad"; most = Math.max(most, f); } return most; });
console.log(JSON.stringify(all));""")
    assert out == [0] * 6


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


@needs_node
def test_dry_places_are_put_on_the_canvas_the_way_the_world_is_drawn(tmp_path):
    out = run_node(tmp_path, """
const parts = [{ wing: "nova", x: 10, y: 2, w: 4, h: 3, z: 50 }];
const view = { tile: 44, depth: 30.8, cx: 440, cy: 100, zoom: 2, w: 1000, h: 600 };
const [box] = weather.dryBoxes(parts, { nova: 0 }, view);
console.log(JSON.stringify({
  box, none: weather.dryBoxes(parts, { nova: 1 }, view), floor: (2 + 3) * 30.8,
}));""")
    box = out["box"]
    assert box["x"] == pytest.approx((10 * 44 - 440) * 2 + 500)  # the left edge of the floor
    assert box["w"] == pytest.approx(4 * 44 * 2)
    assert box["y"] == pytest.approx((2 * 30.8 - 50 - 100) * 2 + 300)  # the top of the back wall
    assert box["y"] + box["h"] == pytest.approx((out["floor"] - 100) * 2 + 300)  # the front edge of the floor
    assert box["dry"] == 1
    assert out["none"] == []


@needs_node
def test_rain_is_painted_once_and_never_into_a_dry_place(tmp_path):
    out = run_node(tmp_path, """
const box = (x, dry) => ({ x, y: 0, w: 100, h: 100, dry });
const names = (list) => list.map((b) => b.x);
const describe = (boxes) => weather.rainPasses(boxes).map((p) => ({ inside: p.inside && p.inside.x, outside: names(p.outside), factor: p.factor }));
const a = box(0, 1), b = box(50, 0.4), c = box(80, 0.7);
console.log(JSON.stringify({
  open: describe([]),
  dry: describe([a]),
  fading: describe([b]),
  mixed: describe([b, a]),
  two: describe([b, c]),
}));""")
    assert out["open"] == [{"inside": None, "outside": [], "factor": 1}]  # open air only
    assert out["dry"] == [{"inside": None, "outside": [0], "factor": 1}]  # a dry place is cut out, nothing repaints it
    assert out["fading"] == [
        {"inside": None, "outside": [50], "factor": 1},
        {"inside": 50, "outside": [], "factor": pytest.approx(0.6)},
    ]
    # a dry box and a fading one: the fading pass cuts the dry one out, so no rain leaks into it
    assert out["mixed"][1] == {"inside": 50, "outside": [0], "factor": pytest.approx(0.6)}
    # two fading boxes: the drier one (0.7) comes first, the other cuts it out, so the overlap is painted once
    assert [p["inside"] for p in out["two"]] == [None, 80, 50]
    assert out["two"][2]["outside"] == [80]
    assert out["two"][1]["factor"] == pytest.approx(0.3) and out["two"][2]["factor"] == pytest.approx(0.6)


@needs_node
def test_a_sky_colour_is_pulled_towards_the_weather_and_dims_with_the_light(tmp_path):
    out = run_node(tmp_path, """
const rain = weather.weatherLook("rain"), noon = "rgb(141,200,213)", dusk = "rgb(32,62,88)";
const clear = "rgb(141,200,213)";
console.log(JSON.stringify({
  none: weather.pullColor(noon, rain.skyTop, 0, clear),
  full: weather.pullColor(noon, [10, 20, 30], 1, clear),
  half: weather.pullColor("rgb(0,100,200)", [100, 200, 100], 0.5),
  noonTop: weather.pullColor(noon, rain.skyTop, rain.sky, clear),
  duskTop: weather.pullColor(dusk, rain.skyTop, rain.sky, clear),
  over: weather.pullColor(noon, [10, 20, 30], 7, clear),
  bad: [weather.pullColor("#8dc8d5", [1, 2, 3], 1, clear), weather.pullColor(null, [1, 2, 3], 1, clear), weather.pullColor(noon, [1, 2, 3], NaN, clear), weather.pullColor("rgb(1,2,3)", [255, 255, 255], 1, "rgb(0,0,0)")],
  text: [weather.rgbText([300, -4, 12.6]), weather.rgbText([1, 2, 3])],
}));""")
    assert out["none"] == "rgb(141,200,213)"  # amount 0 gives the text back
    assert out["full"] == "rgb(10,20,30)"
    assert out["half"] == "rgb(50,150,150)"
    assert out["over"] == "rgb(10,20,30)"  # more than all the way stops at the look's colour
    # at dusk the rainy sky is dark too: darker than the rain sky at noon, and not brighter than a clear dusk sky by much
    noon_top = [int(v) for v in out["noonTop"][4:-1].split(",")]
    dusk_top = [int(v) for v in out["duskTop"][4:-1].split(",")]
    assert all(d < n for d, n in zip(dusk_top, noon_top))
    assert max(dusk_top) < 90
    assert out["bad"] == ["#8dc8d5", None, "rgb(141,200,213)", "rgb(255,255,255)"]  # not an rgb text, no colour, NaN, no reference light
    assert out["text"] == ["rgb(255,0,13)", "rgb(1,2,3)"]


@needs_node
def test_a_small_canvas_gets_thinner_rain_and_the_lists_can_be_reused(tmp_path):
    out = run_node(tmp_path, """
const storm = weather.weatherLook("storm");
const count = (w, h, t) => { const s = weather.rainStreaks(storm, t, w, h); return (s.far.length + s.near.length) / 4; };
const average = (w, h) => { let sum = 0; for (let t = 0; t < 4000; t += 400) sum += count(w, h, t); return sum / 10; };
const reuse = { far: [1, 2, 3], near: [9] };
const again = weather.rainStreaks(storm, 100, 1280, 800, reuse);
const fresh = weather.rainStreaks(storm, 100, 1280, 800);
const longest = (w, h) => { const s = weather.rainStreaks(storm, 50, w, h); let m = 0; for (const list of [s.far, s.near]) for (let i = 0; i < list.length; i += 4) m = Math.max(m, Math.hypot(list[i + 2] - list[i], list[i + 3] - list[i + 1])); return m; };
console.log(JSON.stringify({
  full: average(1280, 800), small: average(600, 375), huge: average(2560, 1600),
  same: again === reuse && JSON.stringify(again) === JSON.stringify(fresh),
  shortSmall: longest(600, 375) < longest(1280, 800),
}));""")
    assert out["small"] < out["full"] * 0.5  # a live window a fifth of the screen is not a curtain
    assert out["huge"] <= 240 and out["full"] <= 240
    assert out["same"]  # filled again, nothing of the old content stays
    assert out["shortSmall"]


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
    assert "dryBoxes(world.nova?.parts, scene.roofs" in env  # the dry places come from the roofs
    assert "function drawHaze" in env and re.search(r"const bands = \[\];[\s\S]*outdoors\(w, h, look\.haze", env)  # the bands are built once, before the passes
    assert env.count("dryBoxes(") == 1  # worked out once a frame for haze and rain together
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
