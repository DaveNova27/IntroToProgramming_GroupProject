// Draws one frame: sky, ground, then everything else sorted from back to front.

import { actorVisible } from "./cull.js";
import { beachActors, drawBeachGround, drawNightGrade, drawNightLights } from "./beach.js";
import { campusActors, drawCampusGroundPlan, drawTerrain } from "./campus.js";
import {
  drawAmbientLighting,
  drawCoastalMotion,
  drawSkyMotion,
  drawWeatherFall,
  drawWeatherFlash,
  drawWeatherShade,
  environmentalProfile,
  lightingProfile,
} from "./environment.js";
import { drawLocation, openPlaces } from "./locations.js";
import { guestActors } from "./guests.js";
import { drawNovaGround, novaActors } from "./nova.js";
import { drawPlayer, playerDepth } from "./player.js";
import { DEPTH, camera, canvas, ctx, depthOf, isoPoint, scene } from "./scene.js";
import { walkerActors } from "./walkers.js";
import { NEUTRAL, pullColor, rgbText } from "./weather.js";

// Objects far above or below the view are not drawn (see cull.js for how far is far).
// `options.cull = false` draws everything: the check that nothing visible is lost.
export const options = { cull: true };

export function drawWorld(t) {
  const w = canvas.clientWidth;
  const h = canvas.clientHeight;
  ctx.clearRect(0, 0, w, h);
  const light = lightingProfile(scene.clock);
  const environment = environmentalProfile(scene.clock, scene.day, t);

  // one open sky over the whole campus: it also shows from inside the Nova, whose roof fades out
  const sky = ctx.createLinearGradient(0, 0, 0, h);
  // the weather of the opened day pulls the sky towards its own colours (spec weather-visuals)
  const look = scene.look;
  // (the colours are day colours: they dim with the light, so a rainy evening is as dark as a clear one)
  sky.addColorStop(0, pullColor(light.top, look.skyTop, look.sky, rgbText(NEUTRAL.skyTop)));
  sky.addColorStop(1, pullColor(light.bottom, look.skyBottom, look.sky, rgbText(NEUTRAL.skyBottom)));
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
    ...guestActors(t),
    ...places.map(([id, loc]) => ({ depth: depthOf(loc.x, loc.y), draw: () => drawLocation(id) })),
    { depth: playerDepth(), draw: () => drawPlayer(t) },
  ];
  // the screen rows the view covers (the same as the translate above, in map pixels)
  const top = center.y - h / (2 * camera.zoom);
  const bottom = center.y + h / (2 * camera.zoom);
  actors.sort((a, b) => a.depth - b.depth);
  for (const actor of actors) if (!options.cull || actorVisible(actor, top, bottom, DEPTH)) actor.draw();
  ctx.restore();

  // the weather lies over the scene, under the evening: its shade, then haze and rain (not indoors)
  drawWeatherShade(w, h);
  drawWeatherFall(t, w, h);
  drawAmbientLighting(light, w, h);
  drawNightGrade(w, h);
  // the lights go on top of the shade, in the same camera as the scene
  ctx.save();
  ctx.translate(w / 2 - center.x * camera.zoom, h / 2 - center.y * camera.zoom);
  ctx.scale(camera.zoom, camera.zoom);
  drawNightLights();
  ctx.restore();
  drawWeatherFlash(t, w, h);
}
