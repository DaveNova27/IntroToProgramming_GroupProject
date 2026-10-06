# Sixth feature: The campus looks like Nova SBE in Carcavelos (Campus Tycoon)

**Product:** Campus Tycoon, a snack stand on campus. **User:** the player running the stand.

## Planning answers

1. **Product and user:** Campus Tycoon; the player who runs the stand.
2. **Trigger:** the player looks at the 3D campus (live window or main view).
3. **Before:** the 3D map shows a generic campus (library, lecture hall, dorms).
4. **Rule:** only the look of the scene changes; rules, stored data and every interaction stay as they are.
5. **After:** the scene is a stylised, low-poly version of the Nova SBE campus in Carcavelos, recognisable by its main features.
6. **Restart:** nothing new is stored.

## Why

The player studies at Nova SBE: running the stand on their own campus by the sea makes the game feel like theirs.

## What

Stylised after public descriptions of the campus (not an exact model):

- Low white buildings (two to three storeys) with long glass ribbons: four "finger" buildings joined at the back by a "learning street", an atrium with a glass roof between them, a library and student residences.
- The campus faces the ocean: the coastal road in front, Carcavelos beach and the Atlantic behind it, gentle waves, beach umbrellas.
- A tunnel from the campus to the beach; some students go to the beach after buying.
- Stone pines and junipers, lawns, a sports field, the pentagonal water tank.
- The Forte de São Julião da Barra with its lighthouse on the coast next to the campus.
- The kiosk, the storage shed, the truck and the students work exactly as before.

## Out of scope

- Any change to rules, catalogue, stored data or the dashboard.
- An exact or measured model of the real buildings; logos or official branding.
- Weather, tides, traffic other than the delivery truck.

## Done when

1. **Same rules:** All existing tests pass unchanged.
2. **Recognisable:** The default view shows the white finger buildings, the kiosk on the plaza, the road and a strip of beach and sea; rotating shows the fort and the beach.
3. **Still playable:** Ordering stock still plays the truck to the shed; a trading day still shows queues, bubbles, coins and the ticker; some students leave through the beach tunnel.
