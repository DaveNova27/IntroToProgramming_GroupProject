# Coastal campus visual polish

## What

Keep the stylised, low-poly Tycoon scene and Nova SBE coastal landmarks.
Improve the default composition, warm daylight, soft shadows, glass facade
detail, plaza paving, planting, seating, kiosk finishes and Atlantic shoreline.
Use a coordinated cream, ocean-teal and terracotta palette in the map HUD and
dashboard. Existing ordering, prices, trading animations, view switching and
reduced-motion support remain usable on desktop and narrow screens.
Animation progress stays within 0..1 and zero-length walks finish directly,
so frame timing and Skip cannot generate invalid curve coordinates.
Remove the sports field, keep plants clear of walking routes, make the beach
tunnel read as a lit underpass whose entrances stay off the road, and keep
beach-bound customers visible as they settle directly on towels. Surfers walk
from the beach through the tunnel to campus. Daylight remains until the beach
visitors have settled; dusk then closes the day without a motionless gap.

## Out of scope

Game rules, catalogue, stored state, new mechanics, exact architectural
reconstruction, official logos, new external asset services and BRD ID changes.

## Done when

1. All existing tests and finite-price regression checks pass unchanged.
2. Browser inspection shows the detailed campus, kiosk, plaza and coast in
   both the main map and dashboard preview without rendering errors.
3. Map order/price panels and dashboard switching remain functional; narrow
   screen controls fit. Trading and deliveries are checked on a temporary save.
