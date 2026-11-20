// The guide for the first day (specs/onboarding-guide.md). Pure: no DOM, so Node can test it. Whether a
// step is done is read from what the API already sends; the screen decides no rule.

export const GUIDE_STEPS = [
  { id: "order", text: "Order coffee at the PC", where: "in the Supply Hall" },
  { id: "open", text: "Open the day" },
  { id: "shift", text: "Take the shift in the Cafe" },
];

const played = (state) => (state.history?.length ?? 0) > 0;

const DONE = {
  // stock to sell (the counter included) or a day already behind the player
  order: (state) => (state.stock_value ?? 0) > 0 || played(state),
  // the day clock runs, or a day was played
  open: (state) => state.shift != null || played(state),
  // the server's badge for a shift of one's own, or the own shift runs right now
  shift: (state) => (state.badges ?? []).some((b) => b.id === "own-shift" && b.day != null)
    || !!state.shift?.shop,
};

// The three steps with `done`, and which one is current (the first not done; null when all are).
export function guideSteps(state) {
  const steps = GUIDE_STEPS.map((step) => ({ ...step, done: DONE[step.id](state) }));
  const current = steps.find((step) => !step.done)?.id ?? null;
  return steps.map((step) => ({ ...step, current: step.id === current }));
}

// Whether the card shows. remembered: what this browser kept ("done", "closed" or null).
// Only on the first day of a run (no played day yet), not in a demo scenario, not on a complete run,
// not once finished or closed before, and not when every step is already done.
export function guideVisible(state, remembered) {
  if (!firstDay(state, remembered)) return false;
  return guideSteps(state).some((step) => !step.done);
}

// True when the player has just done the last step on the first day: the card says "All set" once.
// A demo, a complete run or a played day never count, so loading a scenario cannot fake it.
export function guideAllDone(state, remembered) {
  return firstDay(state, remembered) && guideSteps(state).every((step) => step.done);
}

function firstDay(state, remembered) {
  if (remembered === "done" || remembered === "closed") return false;
  if (!state || state.finished || played(state)) return false;
  return !(state.demo?.active || state.demo?.stale);
}
