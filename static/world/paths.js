// Finding a way around solid objects, so a click on a door also works from far away.
// Pure functions on a grid of half tiles: no drawing and no game rules.

import { pointBlocked } from "./physics.js";

const STEP = 0.5; // tiles between two grid points
const SAMPLE = 0.1; // tiles between two checks along a straight line
const SQRT2 = Math.SQRT2;

function buildGrid(bounds, colliders, radius) {
  const columns = Math.floor((bounds.maxX - bounds.minX) / STEP) + 1;
  const rows = Math.floor((bounds.maxY - bounds.minY) / STEP) + 1;
  const free = new Uint8Array(columns * rows);
  for (let row = 0; row < rows; row++) {
    for (let column = 0; column < columns; column++) {
      const point = { x: bounds.minX + column * STEP, y: bounds.minY + row * STEP };
      free[row * columns + column] = pointBlocked(point, colliders, radius) ? 0 : 1;
    }
  }
  return { columns, rows, free };
}

// the free grid point closest to a position, searching outward
function nearestNode(grid, bounds, point) {
  const column = Math.round((point.x - bounds.minX) / STEP);
  const row = Math.round((point.y - bounds.minY) / STEP);
  for (let ring = 0; ring <= 8; ring++) {
    let best = -1;
    let bestDistance = Infinity;
    for (let r = row - ring; r <= row + ring; r++) {
      for (let c = column - ring; c <= column + ring; c++) {
        if (r < 0 || c < 0 || r >= grid.rows || c >= grid.columns) continue;
        const node = r * grid.columns + c;
        if (!grid.free[node]) continue;
        const distance = Math.hypot(bounds.minX + c * STEP - point.x, bounds.minY + r * STEP - point.y);
        if (distance < bestDistance) {
          best = node;
          bestDistance = distance;
        }
      }
    }
    if (best >= 0) return best;
  }
  return -1;
}

// A* over the grid. Diagonal steps may not cut the corner of a solid object.
function search(grid, start, goal) {
  const { columns, rows, free } = grid;
  const estimate = (node) => {
    const dx = Math.abs((node % columns) - (goal % columns));
    const dy = Math.abs(Math.floor(node / columns) - Math.floor(goal / columns));
    return Math.max(dx, dy) + (SQRT2 - 1) * Math.min(dx, dy);
  };
  const cost = new Float64Array(free.length).fill(Infinity);
  const from = new Int32Array(free.length).fill(-1);
  const open = new Set([start]);
  cost[start] = 0;
  while (open.size) {
    let current = -1;
    let lowest = Infinity;
    for (const node of open) {
      const total = cost[node] + estimate(node);
      if (total < lowest) {
        lowest = total;
        current = node;
      }
    }
    if (current === goal) {
      const nodes = [];
      for (let node = goal; node !== -1; node = from[node]) nodes.push(node);
      return nodes.reverse();
    }
    open.delete(current);
    const column = current % columns;
    const row = Math.floor(current / columns);
    for (let dr = -1; dr <= 1; dr++) {
      for (let dc = -1; dc <= 1; dc++) {
        if (!dr && !dc) continue;
        const r = row + dr;
        const c = column + dc;
        if (r < 0 || c < 0 || r >= rows || c >= columns) continue;
        const next = r * columns + c;
        if (!free[next]) continue;
        if (dr && dc && (!free[row * columns + c] || !free[r * columns + column])) continue;
        const step = cost[current] + (dr && dc ? SQRT2 : 1);
        if (step < cost[next]) {
          cost[next] = step;
          from[next] = current;
          open.add(next);
        }
      }
    }
  }
  return null;
}

function lineIsFree(a, b, colliders, radius) {
  const length = Math.hypot(b.x - a.x, b.y - a.y);
  const samples = Math.max(1, Math.ceil(length / SAMPLE));
  for (let i = 1; i <= samples; i++) {
    const k = i / samples;
    if (pointBlocked({ x: a.x + (b.x - a.x) * k, y: a.y + (b.y - a.y) * k }, colliders, radius)) return false;
  }
  return true;
}

// Keep only the corners: walk straight as far as the line stays free.
function straighten(points, colliders, radius) {
  const kept = [points[0]];
  let index = 0;
  while (index < points.length - 1) {
    let next = points.length - 1;
    while (next > index + 1 && !lineIsFree(points[index], points[next], colliders, radius)) next--;
    kept.push(points[next]);
    index = next;
  }
  return kept;
}

// The points to walk through from start to goal, without the start itself.
// Returns null if there is no way. The radius is the size of the person.
export function findPath(start, goal, bounds, colliders, radius) {
  const clearance = radius + 0.02;
  if (lineIsFree(start, goal, colliders, clearance)) return [goal];
  const grid = buildGrid(bounds, colliders, clearance);
  const first = nearestNode(grid, bounds, start);
  const last = nearestNode(grid, bounds, goal);
  if (first < 0 || last < 0) return null;
  const nodes = search(grid, first, last);
  if (!nodes) return null;
  const points = nodes.map((node) => ({
    x: bounds.minX + (node % grid.columns) * STEP,
    y: bounds.minY + Math.floor(node / grid.columns) * STEP,
  }));
  return straighten([start, ...points, goal], colliders, radius);
}
