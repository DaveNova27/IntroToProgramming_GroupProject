# Weather visuals

Issue #16. Roadmap: `weather-visuals` (section 4.1), one of the specs proposed for the demo (7.17).

## What

The 2.5D world shows the weather of the opened day. Today the sky, the wind and the sea follow only
the clock and the day number (`environmentalProfile` in `static/world/environment.js`); the weather
the server rolled is shown only as a chip in the display. After this spec a rainy day looks rainy.

The server has four kinds of weather (`logic.WEATHER`): `sun`, `rain`, `heat`, `storm`. The world
reads the id from `state.weather.id`, which the API already sends. Nothing in the API changes.

1. **One source.** `ui.js` writes `scene.weather` (a new field in `scene.js`) from `state.weather`:
   the id while the day is open, `null` otherwise. No other place in `static/world/` reads the
   weather from the state, and none reads the forecast (`state.outlook`) for drawing.
2. **A table of looks.** A new pure module `static/world/weather.js` (no page, no canvas, runs in
   Node like `cull.js`) holds one look per id and the neutral look:
   - `weatherLook(id)`: the numbers of a look (sky colours to mix in, cloud amount and cloud colour,
     wind, sea, rain amount and slant, the grade over the scene, haze, lightning yes or no). An id
     that is not an own key of the table (also `null`, `"__proto__"`, a number) gives the neutral look.
   - `rainStreaks(look, t, w, h)`: the streaks of one frame, from the look, the time and the canvas
     size only.
   - `flashAt(look, t, day)`: how bright the lightning is at a time, 0 most of the time.
   - `mixLooks(a, b, k)`: the look between two looks (for the fade in point 6).
   - `shelters(parts, roofs)`: the dry places of point 4, from the Nova's parts and the roofs' opacity.
3. **What each weather looks like.** The numbers are tuned by eye in the build; the table in
   `weather.js` is the truth.

   | Weather | Sky and light | Clouds | Wind and sea | On top |
   |---|---|---|---|---|
   | none (day not open, run over) | as today | as today | as today | nothing |
   | `sun` | as today | as today | as today | nothing |
   | `rain` | grey-blue sky, a cool grey shade over the scene | many, grey | a bit more wind and sea | rain over the whole picture |
   | `heat` | pale, warm sky, a warm tint, a stronger sun glow | almost none | little wind, calm sea | a shimmer of haze near the ground |
   | `storm` | dark slate sky, a dark shade | many, dark, fast | strong wind, high sea (palms, flags and waves follow through `environment.wind` and `environment.sea`) | heavy slanted rain, sometimes lightning |

4. **Where it is drawn.** `environmentalProfile` takes wind, sea and cloud from the look, so every
   caller that already uses it (trees, flags, waves, clouds) follows without a change of its own.
   `drawWorld` (`render.js`) mixes the look's sky colours into the sky gradient, and draws the shade
   or tint, the haze, the rain and the flash after the actors, over the whole canvas.
   **It does not rain indoors.** A wing of the Nova (the Dorm counts as one) whose roof has faded out
   shows its rooms, and the rooms stay dry: no rain and no haze is drawn over the inside of that wing
   (its floor and the inner face of its back wall). While the roof fades, the rain over the wing fades
   with it; over a closed roof it rains as everywhere. The shade over the scene and the flash stay on
   the whole picture, because the light of a rainy day is also grey indoors. This changes the roadmap's
   line "also over the roofless Nova" (decided by David, see "Decide" 5). The night shade and the lamps
   (`drawNightGrade`, `drawNightLights`) keep working on top. The small live window on the dashboard (`scene.preview`) uses the same `drawWorld`
   and so shows the same weather.
5. **Nothing random, nothing from outside.** Every streak, cloud and flash is a function of the look,
   the time, the day and the canvas size. No `Math.random`, no image file, no font, no new library.
6. **Calm and safe to look at.**
   - When the weather changes (the day opens, the editor or a scenario fixes another one, the day
     ends) the look fades over about 2 seconds; with `reducedMotion` it changes at once.
   - Lightning: at most one flash in any 6 seconds, a soft white wash of at most 0.25 alpha that
     fades within half a second. With `reducedMotion` there is no flash, the rain stands still and
     the haze does not move.
   - Cost: at most 240 streaks a frame, drawn as one path per stroke style. No `shadowBlur`, no
     `filter` (spec `smooth-frames`).
7. **Credit.** The code builds on what `environment.js` already has from Felix' project (credited
   in its header). Nothing new is ported from his repository in this spec.

## Out of scope

- Weather rules: which weather a day has, the forecast and its error, the demand factors, the
  temperature. `logic.py`, `guests.py`, `scenarios.py`, `db.py` and `app.py` are not changed.
- Showing the forecast in the world before the day opens (see "Decide" 1).
- New kinds of weather, events drawn in the world (party, surf festival), sound.
- Guests or the player reacting to the weather (umbrellas, running, other clothes), puddles, wet
  textures on single objects, changed room interiors.
- The weather chip, the icons and the texts of the display and the dashboard.
- The roof fade, the camera, the map layout, the night lights.

## Done when

1. `tests/test_weather_visuals.py` (new, `tests/` otherwise untouched) passes. With Node, on `weather.js`:
   - every id of `logic.WEATHER` has a look of its own (the ids are passed in from Python, so a fifth
     weather on the server without a look fails the test);
   - `null`, an unknown id, `"__proto__"`, `"constructor"` and a number give the neutral look;
   - `sun` and the neutral look are equal;
   - the same inputs give the same streaks and the same flash twice in a row;
   - `rain` and `storm` give streaks, never more than 240, all inside the canvas plus a margin;
     `sun`, `heat` and the neutral look give none;
   - `shelters`: a wing with a closed roof gives no dry place, a wing with the roof gone gives its
     parts fully dry, a roof half faded gives them half dry, an unknown wing id in the roofs is ignored;
   - `flashAt` sampled every 50 ms over 10 minutes for several days: never above 0.25, never two
     flashes within 6 seconds, 0 for every look but `storm`.

   As source checks (there is no browser in the tests):
   - no `Math.random`, `shadowBlur` or `filter` in `weather.js`, and it imports nothing outside
     `static/world/`;
   - `scene.weather` is assigned in `ui.js` only, from `state.weather`;
   - no file in `static/world/` uses `outlook` except `ui.js` (the display).

   On the API (a guard for the rule this spec leans on): before the day is opened `/api/state` has
   `weather: null` for two runs with a different real weather; after *Open day* the id is the real
   one; with an editor override it is the override.
2. Checked in the browser by the builder (Playwright, `CT_EDITOR=1`, the weather fixed through
   `/api/editor/weather`), screenshots shown in the session and described in the pull request:
   - the four kinds of weather at three places (the plaza, the beach, inside the Nova with the roof
     gone), by day; `rain` and `storm` also in the evening with the lamps on;
   - in `rain` and `storm` no streak is drawn over the rooms of a wing whose roof is gone (also in
     the Dorm), and it rains on the plaza right next to it and on the closed roofs of the other wings;
   - with the day not open and with `sun`, the picture is the same as on `main` (same pixels at the
     three places, time and motion held still);
   - before the day is opened the picture is the same for a run whose real weather is `storm` and
     one whose real weather is `sun`;
   - the demo scenarios with a fixed weather (`scenarios.py`: rain, heat, sun) show it;
   - with `reducedMotion` nothing of the weather moves or flashes.
3. Measured in the browser at the three places: the JavaScript time of a frame in `storm` is at most
   1 ms above the same frame on `main` (the numbers go into the pull request).
4. `uv run pytest` passes. `README.md` lists the spec and `weather.js`; `AGENTS.md` names
   `weather.js` in the structure; the roadmap marks `weather-visuals` as built.

Rules: nothing here touches money, state, the seed or the API. The drawing stays a function of the
state the server sent and the time only.

## Checked in the browser (2026-11-15)

With Playwright on the running app (`CT_EDITOR=1`), the frame clock held by the script, a 1280 x 800 canvas.

- The four kinds of weather at the plaza, the beach and inside the Nova, `rain` and `storm` also in the
  evening: looked at, as the table in "What" says.
- With the day not open and with `sun` the canvas has the same pixels as on `main`, at the three places.
- Before the day is opened a run whose real weather is `storm` (seed 7) and one whose real weather is
  `sun` (seed 3) give the same pixels, at the three places.
- In `rain` and `storm`, inside the Nova and inside the Dorm, no streak lies over the rooms; it rains
  on the plaza next to them and on the closed roofs.
- The demo scenarios show their fixed weather: `serve-the-cafe` and `other-day-other-choice` rain,
  `guests-decide` heat; `grow` starts with the day not open and so with the neutral look.
- After *Open day* on a rainy day the look fades in over 2 seconds.
- With reduced motion the sky of a storm is one unchanged picture over 60 seconds (1200 frames). Without
  it the lightning shows as the only jumps in brightness.
- JavaScript time of a frame in `storm` against the same frame on `main` (median of 400 frames, three
  rounds, software rendering): the plaza 10.5 against 10.1 ms, the beach 9.6 against 9.3 ms, inside
  the Nova 11.1 against 10.3 ms. At most 0.8 ms more.

## Decide

Defaults chosen while writing the spec, and what the owner (David) said to them before the build.

1. **Before the day opens the world shows the neutral look**, not the forecast. The forecast stays
   in the display. Reason: the world then cannot leak the real weather by mistake, and a wrong
   forecast does not make the sky jump when the day opens.
2. **`sun` looks like today.** The picture of today is a sunny coast already; this keeps the risk
   low and gives a pixel check against `main`.
3. **After the day ends the look goes back to neutral** (`state.weather` is `null` again), so the
   walk home in the evening is dry also after a storm. The other way needs a new field in the API.
4. **Lightning is soft and rare**, and off with `reducedMotion` (point 6 above).
5. **No rain indoors.** The first draft let the rain fall into a wing whose roof had faded out, as
   the roadmap says. David refused that in the session: the rooms of the Nova and the Dorm stay dry.

Points 1 to 4 were confirmed by David in the session, point 5 is his change.

No old test is expected to change. If one does, the build stops and says so (`AGENTS.md`).
