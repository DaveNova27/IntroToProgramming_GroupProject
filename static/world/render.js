// Draws one frame: sky, ground, then everything else sorted from back to front.

import { campusActors, drawCampusGroundPlan, drawTerrain } from "./campus.js";
import {
  drawAmbientLighting,
  drawCoastalMotion,
  drawSkyMotion,
  environmentalProfile,
  lightingProfile,
} from "./environment.js";
import { drawLocation, locationsHere } from "./locations.js";
import { drawPlayer } from "./player.js";
import { roomActors } from "./rooms.js";
import { activeZone, camera, canvas, ctx, isoPoint, scene } from "./scene.js";

export function drawWorld(t) {
  const w = canvas.clientWidth;
  const h = canvas.clientHeight;
  ctx.clearRect(0, 0, w, h);
  const zone = activeZone();
  const light = lightingProfile(scene.clock);
  const environment = environmentalProfile(scene.clock, scene.day, t);

  const sky = ctx.createLinearGradient(0, 0, 0, h);
  sky.addColorStop(0, zone.outdoor ? light.top : "#122d36");
  sky.addColorStop(1, zone.outdoor ? light.bottom : "#34505a");
  ctx.fillStyle = sky;
  ctx.fillRect(0, 0, w, h);
  if (zone.outdoor) drawSkyMotion(t, environment, w, h);

  const center = isoPoint(camera.x, camera.y);
  ctx.save();
  ctx.translate(w / 2 - center.x * camera.zoom, h / 2 - center.y * camera.zoom);
  ctx.scale(camera.zoom, camera.zoom);
  drawTerrain(t);
  if (zone.outdoor) {
    drawCoastalMotion(t, environment);
    drawCampusGroundPlan(t);
  }

  const actors = [
    ...(zone.outdoor ? campusActors(t) : roomActors()),
    ...locationsHere().map(([id, loc]) => ({ depth: loc.x + loc.y, draw: () => drawLocation(id) })),
    { depth: scene.player.x + scene.player.y, draw: () => drawPlayer(t) },
  ];
  actors.sort((a, b) => a.depth - b.depth).forEach((actor) => actor.draw());
  ctx.restore();

  if (zone.outdoor) drawAmbientLighting(light, w, h);
}
