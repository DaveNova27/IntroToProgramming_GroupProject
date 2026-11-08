// The roof of a building the player walks into: is the player under it, and how far has it
// faded out. Pure functions: no drawing, no page, no game rules (spec walk-in).
// The roof is only for showing. Where the player stands changes no rule.

export const ROOF_SECONDS = 0.45; // time to fade the roof fully out or in
const EDGE = 0.25; // tiles: the roof starts to fade as the player steps into the doorway

const covers = (part, x, y) => x >= part.x && x <= part.x + part.w && y >= part.y && y <= part.y + part.h;

// Is the point under the roof of a building made of joined rectangles? A point counts as
// inside when it and the four points `margin` tiles around it lie on the footprint, so the
// seams between two joined parts do not count as an edge.
export function insideParts(point, parts, margin = EDGE) {
  const onFootprint = (x, y) => parts.some((part) => covers(part, x, y));
  return (
    onFootprint(point.x, point.y) &&
    onFootprint(point.x - margin, point.y) &&
    onFootprint(point.x + margin, point.y) &&
    onFootprint(point.x, point.y - margin) &&
    onFootprint(point.x, point.y + margin)
  );
}

// Roof opacity for the next frame: 1 = closed, 0 = gone. Moves towards the target at a steady
// speed and ends exactly on it. With reduced motion it jumps.
export function stepRoof(current, inside, dt, reducedMotion = false) {
  const target = inside ? 0 : 1;
  if (reducedMotion) return target;
  const step = Math.max(0, dt) / ROOF_SECONDS;
  return current < target ? Math.min(target, current + step) : Math.max(target, current - step);
}

// The labelled floor area under a point (for the name of the place), or null.
export function areaAt(point, areas) {
  return areas.find((area) => covers({ x: area.x, y: area.y, w: area.w, h: area.h }, point.x, point.y)) ?? null;
}
