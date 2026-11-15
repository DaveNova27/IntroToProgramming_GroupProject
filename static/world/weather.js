// How each weather looks (spec weather-visuals). Pure functions: no page, no canvas, no state.
// The server decides the weather of a day (logic.WEATHER); this only says how it is drawn. Every
// number that moves comes from the look, the time, the day and the size of the canvas: nothing
// here is random, and nothing here decides a rule.

export const MAX_STREAKS = 240; // rain streaks in one frame, at most
export const RAIN_MARGIN = 80; // pixels around the canvas a streak may start or end in
export const FLASH_MAX = 0.25; // the brightest a lightning flash gets (alpha of a white wash)
export const FLASH_SLOT = 9000; // milliseconds: one flash at most in each slot
const FLASH_LATEST = 2500; // a flash starts in the first part of its slot, so two are 6.5 s apart or more
const FLASH_LENGTH = 450; // milliseconds from the first light to none
export const FADE_SECONDS = 2; // from one weather to the next
const FULL_W = 1280; // a full-size canvas for the rain density (pixels)
const FULL_H = 800;

// A look. Colours are [red, green, blue], so two looks can be mixed number by number.
//   sky, skyTop, skyBottom   how far the sky is pulled towards these two colours (0 = the day's own sky)
//   cloudScale               the day's own clouds: 1 = as they are, 0 = none
//   cloudExtra, cloudColor   more and bigger clouds on top, and their colour
//   windScale, windAdd       the day's wind times one, plus the other; the sea the same way
//   rain, slant              how much of MAX_STREAKS falls, and how far a streak leans (x per y)
//   shade, shadeColor        a multiply over the scene (0 = none)
//   tint, tintColor          a colour laid over the scene (0 = none)
//   haze                     a shimmer near the ground (0 = none)
//   glow                     the sun's glow: 1 = as it is
//   lightning                1 = flashes, 0 = none
export const NEUTRAL = Object.freeze({
  sky: 0, skyTop: [141, 200, 213], skyBottom: [214, 228, 192],
  cloudScale: 1, cloudExtra: 0, cloudColor: [244, 238, 225],
  windScale: 1, windAdd: 0, seaScale: 1, seaAdd: 0,
  rain: 0, slant: 0,
  shade: 0, shadeColor: [255, 255, 255],
  tint: 0, tintColor: [255, 255, 255],
  haze: 0, glow: 1, lightning: 0,
});

// One look per weather id of the server. A sunny day is the picture the world always had.
const LOOKS = {
  sun: NEUTRAL,
  rain: {
    ...NEUTRAL,
    sky: 0.78, skyTop: [108, 126, 142], skyBottom: [172, 182, 186],
    cloudScale: 1, cloudExtra: 0.75, cloudColor: [150, 160, 170],
    windScale: 1, windAdd: 0.1, seaScale: 1.1, seaAdd: 0.04,
    rain: 0.8, slant: 0.14,
    shade: 0.5, shadeColor: [150, 168, 190],
    glow: 0.25,
  },
  heat: {
    ...NEUTRAL,
    sky: 0.6, skyTop: [156, 205, 226], skyBottom: [250, 226, 170],
    cloudScale: 0.15,
    windScale: 0.55, seaScale: 0.72,
    tint: 0.11, tintColor: [255, 170, 70],
    haze: 1, glow: 2.2,
  },
  storm: {
    ...NEUTRAL,
    sky: 0.92, skyTop: [44, 54, 70], skyBottom: [104, 112, 122],
    cloudScale: 1, cloudExtra: 1, cloudColor: [74, 82, 96],
    windScale: 1.25, windAdd: 0.18, seaScale: 1.3, seaAdd: 0.1,
    rain: 1, slant: 0.42,
    shade: 0.66, shadeColor: [104, 118, 150],
    glow: 0, lightning: 1,
  },
};

export const WEATHER_IDS = Object.freeze(Object.keys(LOOKS));

// The look of a weather id. Anything that is not one of the ids above gives the neutral look:
// null (the day is not open), an id the server does not have, a name every object has.
export function weatherLook(id) {
  return typeof id === "string" && Object.hasOwn(LOOKS, id) ? LOOKS[id] : NEUTRAL;
}

const lerp = (a, b, k) => a + (b - a) * k;

// The look between two looks: k = 0 gives a, k = 1 gives b.
export function mixLooks(a, b, k) {
  const amount = Math.max(0, Math.min(1, k));
  if (amount <= 0) return a;
  if (amount >= 1) return b;
  const look = {};
  for (const key of Object.keys(NEUTRAL)) {
    look[key] = Array.isArray(a[key]) ? a[key].map((value, i) => lerp(value, b[key][i], amount)) : lerp(a[key], b[key], amount);
  }
  return look;
}

// "rgb(1,2,3)" for a list of three channels (any numbers, rounded and kept between 0 and 255).
export const rgbText = (color) => `rgb(${color.map((channel) => Math.max(0, Math.min(255, Math.round(channel)))).join(",")})`;

// the three channels of "rgb(1,2,3)" (or "rgba(1,2,3,.5)"); nothing for any other text, a hex colour included
const CHANNELS = /^rgba?\(\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)\s*[,)]/;
const channels = (css) => (typeof css === "string" ? (css.match(CHANNELS)?.slice(1, 4).map(Number) ?? []) : []);
const luminance = ([r, g, b]) => 0.2126 * r + 0.7152 * g + 0.0722 * b;

// A colour of the page ("rgb(1,2,3)") pulled towards a colour of a look. Amount 0 gives the text back unchanged.
// `clear` is the colour the same sky has on a clear day at noon: the look's colour is a day colour, so it is
// dimmed by how much darker the sky is now than at noon, and a rainy sky falls dark in the evening like a clear one.
export function pullColor(css, color, amount, clear = null) {
  if (!(amount > 0)) return css;
  const from = channels(css);
  if (from.length < 3) return css;
  const reference = channels(clear);
  const dim = reference.length === 3 && luminance(reference) > 0 ? Math.max(0, Math.min(1, luminance(from) / luminance(reference))) : 1;
  return rgbText(from.map((channel, i) => lerp(channel, color[i] * dim, Math.min(1, amount))));
}

// A fixed number between 0 and 1 for a whole number (the same one every time).
const fraction = (n, salt) => {
  const value = Math.sin(n * 12.9898 + salt * 78.233) * 43758.5453;
  return value - Math.floor(value);
};

// The rain of one frame: two lists of streaks, each [x1, y1, x2, y2, x1, y1, ...] in canvas pixels.
// `far` streaks are short and slow, `near` ones long and fast. With t held still the rain stands.
// A small canvas (the small live view on the dashboard) gets fewer and shorter streaks: the count follows the
// area against a full screen, down to a fifth. `out` is an optional pair of lists to fill again (cleared first),
// so a frame does not allocate new ones.
export function rainStreaks(look, t, w, h, out = { far: [], near: [] }) {
  out.far.length = 0;
  out.near.length = 0;
  if (!(w > 0) || !(h > 0)) return out;
  const density = Math.max(0.2, Math.min(1, (w * h) / (FULL_W * FULL_H)));
  const size = Math.max(0.5, Math.min(1, w / FULL_W));
  const count = Math.min(MAX_STREAKS, Math.round(MAX_STREAKS * Math.max(0, look.rain) * density));
  if (!count) return out;
  const slant = Math.max(-0.6, Math.min(0.6, look.slant));
  for (let i = 0; i < count; i++) {
    const near = i % 3 === 0;
    const length = (near ? 26 : 15) * size * (0.8 + fraction(i, 1) * 0.5);
    const speed = (near ? 1.05 : 0.72) * (0.85 + fraction(i, 2) * 0.3); // pixels per millisecond
    const fall = h + length;
    const y = ((fraction(i, 3) * fall + t * speed) % fall) - length; // top end of the streak
    // the streak moves along its own lean, so it comes back where it started
    const span = w + Math.abs(slant) * fall;
    const start = fraction(i, 4) * span - (slant > 0 ? slant * fall : 0);
    const x = start + slant * (y + length);
    const x2 = x + slant * length;
    const y2 = y + length;
    if (Math.min(x, x2) < -RAIN_MARGIN || Math.max(x, x2) > w + RAIN_MARGIN) continue; // far outside the picture
    (near ? out.near : out.far).push(x, y, x2, y2);
  }
  return out;
}

// How bright the lightning is at a time: 0 most of the time, FLASH_MAX at most. The day moves the
// pattern, so two stormy days do not flash at the same moments.
export function flashAt(look, t, day) {
  if (!(look.lightning > 0) || !(t >= 0)) return 0;
  const slot = Math.floor(t / FLASH_SLOT);
  if (fraction(slot, day + 0.5) > 0.6) return 0; // a slot without a flash
  const since = t - slot * FLASH_SLOT - fraction(slot, day + 7.5) * FLASH_LATEST;
  if (since < 0 || since >= FLASH_LENGTH) return 0;
  const rise = 60;
  const shape = since < rise ? since / rise : 1 - (since - rise) / (FLASH_LENGTH - rise);
  return FLASH_MAX * Math.min(1, look.lightning) * shape;
}

// The dry places: the parts of a building whose roof has faded out, so its rooms show. It does not
// rain indoors. `parts` are the building's blocks (x, y, w, h in tiles, z = wall height, wing),
// `roofs` the opacity of each wing's roof (1 = closed). `dry` runs from just above 0 to 1 (roof gone).
export function shelters(parts, roofs) {
  const out = [];
  for (const part of parts ?? []) {
    if (!roofs || !Object.hasOwn(roofs, part.wing)) continue;
    const roof = Number(roofs[part.wing]);
    if (!(roof < 1)) continue;
    out.push({ x: part.x, y: part.y, w: part.w, h: part.h, z: part.z ?? 0, dry: 1 - Math.max(0, roof) });
  }
  return out;
}

// The dry places in canvas pixels. `parts` and `roofs` as for shelters; `view` is how the world is drawn:
// { tile, depth } pixels per tile across and per tile into the picture, { cx, cy } the camera's centre in map
// pixels, `zoom`, and the canvas size { w, h }. A box runs from the top of the back wall down to the floor's
// front edge, the way the rooms show once the roof is gone.
export function dryBoxes(parts, roofs, view) {
  const { tile, depth, cx, cy, zoom, w, h } = view;
  const px = (x) => (x * tile - cx) * zoom + w / 2;
  const py = (y, z = 0) => (y * depth - z - cy) * zoom + h / 2;
  return shelters(parts, roofs).map((part) => ({
    x: px(part.x), y: py(part.y, part.z), w: part.w * tile * zoom, h: py(part.y + part.h) - py(part.y, part.z), dry: part.dry,
  }));
}

// How to paint something that must not fall indoors: a list of passes, each { inside, outside, factor }.
// `inside` is a box to clip to (null: the whole canvas), `outside` the boxes to cut out, `factor` how strongly to
// paint (1 = fully). The first pass paints the open air at full strength with every box cut out. A box whose roof
// is still fading then gets its own pass at the strength of what is left of its roof, with the fully dry boxes and
// the boxes of earlier passes cut out, so where two boxes overlap the drier one wins and nothing is painted twice.
export function rainPasses(boxes) {
  const dryest = [...boxes].sort((a, b) => b.dry - a.dry);
  const passes = [{ inside: null, outside: dryest, factor: 1 }];
  const done = [];
  for (const box of dryest) {
    if (box.dry < 0.99) passes.push({ inside: box, outside: [...done], factor: 1 - box.dry });
    done.push(box);
  }
  return passes;
}
