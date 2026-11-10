// Draws one frame: sky, ground, then everything else sorted from back to front.

import { beachActors, drawBeachGround, drawNightGrade, drawNightLights } from "./beach.js";
import { campusActors, drawCampusGroundPlan, drawTerrain } from "./campus.js";
import {
  drawAmbientLighting,
  drawCoastalMotion,
  drawSkyMotion,
  environmentalProfile,
  lightingProfile,
} from "./environment.js";
import { drawLocation, openPlaces } from "./locations.js";
import { drawNovaGround, novaActors } from "./nova.js";
import { drawPlayer, playerDepth } from "./player.js";
import { DEPTH, camera, canvas, ctx, depthOf, isoPoint, scene } from "./scene.js";
import { walkerActors } from "./walkers.js";

// Objects far above or below the view are not drawn. An object's depth is about its tile row, so the
// screen row it stands on is depth * DEPTH. What stands above it reaches up at most TALL pixels (the
// Nova's roofs cover eight rows and are about 120 px high), what hangs below it SKIRT rows. Depths
// outside the map rows (the kites and gulls at 200, the tide pools at 1) are drawn always.
// `options.cull = false` draws everything: the check that nothing visible is lost.
export const options = { cull: true };
const TALL = 480;
const SKIRT = 3;

function visible(depth, top, bottom) {
  if (!options.cull || depth < 2 || depth > 60) return true;
  return (depth - SKIRT) * DEPTH - TALL <= bottom && (depth + SKIRT) * DEPTH >= top;
}

export function drawWorld(t) {
  const w = canvas.clientWidth;
  const h = canvas.clientHeight;
  ctx.clearRect(0, 0, w, h);
  const light = lightingProfile(scene.clock);
  const environment = environmentalProfile(scene.clock, scene.day, t);

  // one open sky over the whole campus: it also shows from inside the Nova, whose roof fades out
  const sky = ctx.createLinearGradient(0, 0, 0, h);
  sky.addColorStop(0, light.top);
  sky.addColorStop(1, light.bottom);
  ctx.fillStyle = sky;
  ctx.fillRect(0, 0, w, h);
  drawSkyMotion(t, environment, w, h);

  const center = isoPoint(camera.x, camera.y);
  ctx.save();
  ctx.translate(w / 2 - center.x * camera.zoom, h / 2 - center.y * camera.zoom);
  ctx.scale(camera.zoom, camera.zoom);
  drawTerrain(t);
  drawCoastalMotion(t, environment);
  drawCampusGroundPlan(t);
  drawBeachGround(t);
  drawNovaGround();

  // the desks stand inside the Nova: they show only while the roof is gone
  const places = openPlaces();
  const actors = [
    ...campusActors(t),
    ...beachActors(t),
    ...novaActors(t),
    ...walkerActors(t),
    ...places.map(([id, loc]) => ({ depth: depthOf(loc.x, loc.y), draw: () => drawLocation(id) })),
    { depth: playerDepth(), draw: () => drawPlayer(t) },
  ];
  // the screen rows the view covers (the same as the translate above, in map pixels)
  const top = center.y - h / (2 * camera.zoom);
  const bottom = center.y + h / (2 * camera.zoom);
  actors.sort((a, b) => a.depth - b.depth);
  for (const actor of actors) if (visible(actor.depth, top, bottom)) actor.draw();
  ctx.restore();

  drawAmbientLighting(light, w, h);
  drawNightGrade(w, h);
  // the lights go on top of the shade, in the same camera as the scene
  ctx.save();
  ctx.translate(w / 2 - center.x * camera.zoom, h / 2 - center.y * camera.zoom);
  ctx.scale(camera.zoom, camera.zoom);
  drawNightLights();
  ctx.restore();
}
