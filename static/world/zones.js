// The Dorm stands next to the Nova and is entered the same way, so the browser joins its data to the
// Nova's: one more wing for the roof, the walls and the rooms, its room, and the bed as a place to use
// (spec nova-zones). The server keeps the Dorm apart (world.py: DORM); nothing here decides a rule.

export function joinDorm(world) {
  const dorm = world.dorm;
  if (!dorm) return;
  const nova = world.nova;
  world.nova = {
    ...nova,
    wings: [...nova.wings, ...dorm.wings],
    parts: [...nova.parts, ...dorm.parts],
    walls: [...nova.walls, ...dorm.walls],
    entrances: [...nova.entrances, ...dorm.entrances],
    openings: [...nova.openings, ...dorm.openings],
  };
  const rooms = world.interiors.campus;
  world.interiors = {
    ...world.interiors,
    campus: {
      ...rooms,
      areas: [...rooms.areas, ...dorm.interior.areas],
      solid: [...rooms.solid, ...dorm.interior.solid],
      activities: [...rooms.activities, ...dorm.interior.activities],
    },
  };
  world.locations = { ...world.locations, bed: dorm.bed };
}
