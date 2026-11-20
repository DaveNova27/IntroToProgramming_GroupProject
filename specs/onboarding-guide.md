# A guide for the first day (`onboarding-guide`)

Asked for by Felix on 2026-11-20, from the playtest of 2026-11-18: whoever opens the game for the first
time (for example the professor on the live URL) stands on the campus with no hint what to do. A small
card with three steps shows the way through the first day, ticks each step off by itself and then goes.
It should take little room. Later it may become part of the demo (not in this spec).

## What

- **The card (`static/map.html`, `static/map.css`):** a small card at the bottom left above the toolbar,
  in the place and the look of the demo card (dark panel, lime accent), at most 300 px wide. Title
  "Your first day", then three steps, each with a round check:
  1. **Order coffee at the PC** (in the Supply Hall)
  2. **Open the day**
  3. **Take the shift in the Cafe**
  The first step that is not done is the current one: it is bold and has a small **Go** button. The done
  steps show a ✓ and are dimmed. Under the steps one line: "Then fill the counter and sell to the
  guests." A × closes the card.
- **Go does what the toolbar does (`static/world/ui.js`):** step 1 runs the *Stock* action (the player
  walks to the PC and the order window opens), step 2 the *Open day* action, step 3 opens the *Shift*
  panel. No new action, no new request.
- **Done comes from the server's state (`static/world/guide.js`, new, pure):** `guideSteps(state)`
  returns the three steps with `done`, read from what the API already sends; the browser decides no
  rule:
  - ordered: there is stock (`stock_value` > 0, counter included), or a day was played (`history`);
  - opened: the day is open (`shift` is not null), or a day was played;
  - shift: the badge `own-shift` is earned, or the player's shift is running (`shift.shop`).
  `guideVisible(state, remembered)` says whether the card shows (see Decide 1). No DOM in this module,
  so Node tests it.
- **When all three are done:** the card says "All set. Good luck with the season!" for 4 seconds and
  goes; it is remembered as done.

## Decide

1. **Only on the first day of a run, until it is done or closed:** the card shows while the run has no
   played day yet (`history` empty), not all steps are done, and the player has not finished or closed it
   before. It does not show during a demo scenario (the demo has its own card), on a complete run, or in
   the small preview on the dashboard.
2. **Remembered per browser:** finishing or closing it is kept in `localStorage` (`ct-guide`: `done` or
   `closed`), read and written inside `try`/`catch`. Without storage (a private window) the card shows
   again on the first day of a new run; nothing breaks. This is a per-viewer convenience, not game state,
   so it does not go to the server.
3. **Phones:** the bottom of a phone holds the stock bar and the "press E" hint, so the card stands at
   the top left under the place label instead, and shows only the current step (the others are hidden).
4. **The badge card stays where it is:** it stands below the stock card at the top left; the guide is at
   the bottom (laptop) or listed among the things the badge card stands below (phone).
5. **Tests:** the new file `tests/test_onboarding_guide.py`. No old test changes.

## Found while building

- An order redraws only the HUD (`renderHud`), not the whole screen, so the first step did not tick:
  the guide is redrawn from `renderHud`, which every answer of the server runs.
- An old check (`tests/test_world_core.py`) forbids the word "three" in `map.html` (the old three.js
  map): the HTML comment says "3 steps". The test is unchanged.

## AI review findings (fixed)

1. Screen readers were not told when a step ticked or "All set" appeared: a hidden live region
   (`#guide-live`, `aria-live="polite"`) says "Step done. Next: …" and "All set …".
2. The guide copied the demo card's box styles: one shared rule `.demo-card, .guide-card`; the guide
   only sets its smaller width and padding.

## Out of scope

- The guide inside the demo mode (a later spec if wanted).
- More steps (prices, shops, staff), a tutorial with arrows in the world, sounds.
- Any rule, endpoint or stored state on the server.

## Done when

1. **First visit:** a new run on day 1 shows the card with step 1 current; Go on each step does the
   toolbar's action.
2. **Ticks by itself:** ordering, opening the day and starting the shift tick the steps in turn; after
   the third the card says "All set" and goes; a reload does not bring it back.
3. **Closing:** × hides it and a reload does not bring it back; a private window shows it again.
4. **Stays out of the way:** not in a demo, not on a complete run, not in the preview, not after the
   first day; on a phone it stands at the top and shows one step.
5. **Tests:** `tests/test_onboarding_guide.py`
   - `guideSteps` and `guideVisible` in Node against `app.view` of real states: a new run, after a
     purchase, after opening the day, after starting the shift, a played day, a demo, a complete run,
     remembered `done` and `closed`;
   - the page: the card in `map.html`, the Go buttons call the existing actions, storage inside
     `try`/`catch`, the phone rule, hidden in the preview;
   - the full suite passes.
6. **Checked in the browser:** the three steps on a laptop and on a phone width; no console errors.

## Security

Display only: the step texts are fixed in the page, nothing typed is shown, `localStorage` holds one
word. No input, no rule, nothing loaded from outside, no randomness.
