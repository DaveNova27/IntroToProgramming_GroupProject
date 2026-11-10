// Which objects and which rows of the ground are inside the view. Pure functions: no page, no drawing.
// An object's depth is about the map row it stands on, so the screen row it stands on is depth * rowPixels.
// What stands above it reaches up at most TALL pixels (the longest hedge reaches about 424, the Nova's
// roofs cover eight rows and are about 120 px high), what hangs below it SKIRT rows (a pool of lamp
// light reaches about 105 px, which is under 5 rows). An actor with `always` is never left out (the
// kites and gulls fly over everything, the tide pools lie at the water).

export const TALL = 640;
export const SKIRT = 5;

// `top` and `bottom` are the screen rows (in map pixels) the view covers.
export function actorVisible(actor, top, bottom, rowPixels) {
  if (actor.always) return true;
  return (actor.depth - SKIRT) * rowPixels - TALL <= bottom && (actor.depth + SKIRT) * rowPixels >= top;
}

// The first and last map row (0 to rows - 1) that can show in the view, with one row to spare.
export function rowRange(top, bottom, rowPixels, rows) {
  return [Math.max(0, Math.floor(top / rowPixels) - 1), Math.min(rows - 1, Math.ceil(bottom / rowPixels) + 1)];
}
