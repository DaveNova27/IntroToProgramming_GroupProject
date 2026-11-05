# Figures and people (`world-art`, issue #26)

## What

The player gets Felix Antes' character from Nova Beach Ventures: six walking frames,
facing from the direction of movement, poses, hair, props. It is drawn on the canvas in
code (`static/world/people.js`), no image files. Each room shows the people from its layout
in `world.py`, with a short label when the player comes close. Fourteen passers-by walk
between the named places outdoors (`walkers.js`), around solid objects.

The passers-by are decoration: they buy nothing, no rule reads them, and the browser does
not send them to the server. Their paths come from their number, with no random numbers.

## Out of scope

Customers who decide something or who cause sales (`guests`, decided later). Outfits.
Staff as a mechanic: the `role` in a room layout only changes the prop in a person's hand.

## Done when

1. `uv run pytest` passes. Every person in a room stands inside that room and has a label.
   The drawing code knows every pose used in a layout. People and passers-by never talk to
   the server.
2. In the browser: the player walks and turns as a figure, the rooms show people, passers-by
   walk around the campus without passing through buildings, and there are no console errors.
