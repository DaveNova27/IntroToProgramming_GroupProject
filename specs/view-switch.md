# Fifth feature: Switch between dashboard and campus map (Campus Tycoon)

**Product:** Campus Tycoon, a snack stand on campus. **User:** the player running the stand.

## Planning answers

1. **Product and user:** Campus Tycoon; the player who runs the stand.
2. **Trigger:** the player clicks the live campus window on the dashboard, or opens the dashboard panel on the map and makes it the main view again.
3. **Before:** an active or complete run exists; both views show the same saved run.
4. **Rule:** switching views never changes the run. Both views send actions through the same checks; a rejected action changes nothing in either view.
5. **After:** the chosen view fills the screen; the other one stays reachable (a live window on the dashboard, a slide-in panel on the map). An accepted action in one view shows up in the other right away; the map animates it (truck, students) even when it is only the small window.
6. **Restart:** reloading keeps the chosen main view (the address ends in `#map` while the map is the main view); nothing is replayed.

## Why

The player wants the overview of the dashboard and the feel of the campus at the same time, and to move between them without losing their place.

## What

- Dashboard: a "Campus live" window showing the 3D campus, slowly turning. Clicking it grows the map into the main view.
- Map as main view: the dashboard slides in from the right as a panel (from a tab at the edge or the map's "Dashboard" link). "Make main view" shrinks the map back into its window and the dashboard fills the screen again.
- Both views stay in sync: after an accepted purchase, price change, trading day or new run in one view, the other shows the new run immediately; the map plays the truck or the trading day in its window.
- The browser's back button returns from the map to the dashboard; `/map` opens the dashboard with the map as the main view.

## Out of scope

- Any change to the rules, the catalogue or what is stored.
- Changes to the map scene or the dashboard content beyond what the switch needs.
- Several windows or browser tabs kept in sync with each other.

## Done when

1. **Same rules:** All existing tests pass unchanged; both views use only the existing API.
2. **Grow:** Clicking the campus window turns the map into the full-screen main view without reloading the scene; the address ends in `#map`.
3. **Panel and back:** On the map, the dashboard slides in from the right; "Make main view" (or the back button) brings the dashboard back with the map in its window.
4. **In sync:** Buying 10 Sandwiches on the dashboard plays the truck in the campus window and the map shows Sandwich 10 and cash €80; buying on the map updates the dashboard panel to the same numbers.
5. **Reload:** Reloading with `#map` opens the map as the main view; reloading without it opens the dashboard; nothing is replayed.
