# Badges (`badges`, issue #15)

Proposed by Gregor on 2026-11-09. Depends on nothing. Felix' `scenarioGoals` is the model.

## What

The player earns **badges** for things done during the season: a first sale, a good day,
a second shop, a team of three, a run of profitable days. There are 20 badges, spread over
the whole season, so there is still something to reach in the last days. A badge is only an
award: it gives no money and changes no rule.

Badges are awarded **only by the server**, the moment they are reached: a badge that depends
on the state (a sale, a hire, a shop, the cash) right after the action that reaches it, e.g.
at the first sale; a badge that needs the whole day (profit of the day, streaks, weather)
when the day closes. No endpoint lets the browser grant a badge. Each badge is earned at most
once per run.

### The badges

All numbers are placeholders, to balance once `pricing` (#38) is in. Money is in cents in
the code. "Profit" of a day is the day result's `net` (gross profit minus wages); a day
booked by `trade_day` has no wages, so its `net` is its `gross_profit`.

Start (about day 1 to 5)

| id | Name | Earned when |
|---|---|---|
| `first-sale` | ☕ First sale | at least one unit was sold that day |
| `own-shift` | 🧑‍🍳 Behind the counter | the player played the shift that day (not staff, not skipped before it started) |
| `first-hire` | 👤 The boss | at least one employee is hired |
| `good-day` | 💰 Good day | the day's profit is at least 50 euro |

Middle (about day 5 to 15)

| id | Name | Earned when |
|---|---|---|
| `no-one-left` | 😊 Nobody leaves empty-handed | something was sold and no customer left without buying |
| `expansion` | 🏪 Expansion | at least two shops are unlocked |
| `doubled` | 📈 Doubled | the cash is at least 200 euro |
| `team` | 👥 A whole team | at least 3 employees at the same time |
| `upgrade` | 🔧 Upgrade | any shop is above level 1 |
| `pro` | ⭐ Pro | any employee is on level 3 |

Streaks (days in a row, counted back from the day that just ended)

| id | Name | Earned when |
|---|---|---|
| `streak-3` | 🔥 On track | the last 3 days all had a profit above 0 |
| `streak-7` | 🔥🔥 On a roll | the last 7 days all had a profit above 0 |
| `hard-worker` | 💪 Hard worker | the player played the shift on each of the last 5 days |
| `streak-14` | 🔥🔥🔥 Unstoppable | the last 14 days all had a profit above 0 |

Late (about day 15 to 30)

| id | Name | Earned when |
|---|---|---|
| `empire` | 🌍 Empire | every shop in `SHOPS` is unlocked (not a fixed 4: more shops will come) |
| `big-team` | 🏢 Big team | at least 6 employees at the same time |
| `record-day` | 🚀 Record day | the day's profit is at least 150 euro |
| `storm-proof` | ⛈️ Storm-proof | the day's weather was storm and its profit was above 0 |
| `wealthy` | 💎 Wealthy | the cash is at least 1,000 euro |
| `season-winner` | 👑 Season winner | day 30 has ended and the cash is at least 2,000 euro |

Given at once (after the action): `first-sale`, `own-shift` (when the shift starts),
`first-hire`, `expansion`, `doubled`, `team`, `upgrade`, `pro`, `empire`, `big-team`,
`wealthy`. Given when the day closes: `good-day`, `no-one-left`, the streaks, `hard-worker`,
`record-day`, `storm-proof`, `season-winner`.

### Rules in `logic.py`

- `BADGES`: the table above as data, in this order: `id`, `name`, `icon`, `text` (the
  condition in one short sentence for the screen), `when` (`"now"` or `"day"`) and the check;
  the thresholds as constants
  (`GOOD_DAY_NET = 5_000`, `RECORD_DAY_NET = 15_000`, `DOUBLED_CASH = 20_000`,
  `WEALTHY_CASH = 100_000`, `WINNER_CASH = 200_000`, `TEAM_SIZE = 3`, `BIG_TEAM_SIZE = 6`,
  ...). A new badge is one new entry plus its check.
- The state gets `badges`: a list of `{"id", "day"}` in the order they were earned. A new
  run starts with `[]`.
- `award_badges(new, result=None)`: without a result it checks the `"now"` badges and stamps
  them with the open day; `app.apply` calls it after every accepted game action (not after a
  refused one, and not in the editor's own actions). With a result it is called at the end of
  `_close_shift` and `trade_day`, after the day's result is in `history` and before `day`
  moves on, and checks all badges. It then adds `"badges"` to the day's result: every badge
  earned on that day, also those given during it, so the evening report lists them all.
  Nothing is given after the season. Pure: no randomness, nothing read from the browser.
- "Sold so far" counts the booked days and the sales of the open day (the player's shift and
  the staffed shops). "Played" is true from the start of the player's own shift.
- To tell whether the player played a shift, the day result gets `"played": True/False`:
  true when the player's shift ran in a shop and was not taken over by staff
  (`shift["staffed"]`). `trade_day` results are `False`.
- A result without `lost` (from `trade_day`) counts the customers who wanted to buy and
  could not: the sum of `demand - sold` over its lines.
- The weather of a day comes from `make_day_context(seed, day, override)`, the same as the
  day used.
- Editor: `editor_set_state` cuts `badges` the same way it cuts `history` (only badges
  earned on a day before the new day stay), and accepts a `badges` list of known ids so the
  demo mode can set them. Unknown ids or doubles are refused and nothing changes.

### Saved state in `db.py`

- New table `badges (id TEXT PRIMARY KEY, day INTEGER)`. `load` and `save` read and write
  it; `save_new_run` clears it. An older database without the table starts with `[]`.

### API and screen

- `GET /api/state` (and every action answer) adds `badges: [{id, name, icon, text, day}]`
  for all badges in `BADGES` order; `day` is `null` while not earned.
- No new endpoint. Nothing in a request can add a badge.
- Every badge is a **medal**: a bronze, silver or gold coin on a ribbon with the badge's icon
  inside (`BADGE_TIER` in `logic.py`, sent as `tier`; the look in `static/badges.css`, the
  markup `medalHtml` in `static/common.js`). Bronze for the start, silver for the middle,
  gold for the late game; the profit streaks climb with their length. A badge not earned
  yet is a grey medal.
- **Card when a badge is earned** (campus page): as soon as an answer of the server has a
  badge that was not earned before, a card slides in at the **top left**: the medal with a
  short burst of sparks, "Badge earned", the name, the tier and "n / 20", and the condition.
  It sits right below what is already there (the stock card on wide screens, the place label
  on phones), never on top of it. The game keeps running: nothing is dimmed, the clock and
  the customers go on, the player keeps walking, nothing has to be clicked. The card leaves
  by itself after 4.5 seconds (a thin line along its bottom runs out); a small × closes it
  earlier. Several new badges come one after the other. While a card is shown the short
  messages (toasts) move to its right, or below it where there is no room (phones), so they
  never overlap. A badge reached while the dashboard is in front comes when the campus is
  shown again. Badges earned before the page was loaded do not show. The sparks take their
  direction and colour from the piece's number (no `Math.random`); with reduced motion there
  are no sparks and no animation.
- Dashboard: a "Badges" panel with all badges as medals, earned ones with their day,
  the others grey with their condition, and a count "7 / 20 earned".
- Evening report (campus page): "Badges today" with every badge earned that day as a medal,
  also those that already popped up during the day. The day summary on the dashboard: one
  line per badge, e.g. "New badge: 💰 Good day".
- **End of the season**: the final screen on the campus page and the final banner on the
  dashboard show "Your badges · n / 20" and every earned badge as a medal with its name and
  day.
- Texts are set with `textContent` or `esc()`.

## Decide

1. **How many badges?** No limit in the roadmap. 20, so that every part of the season has
   something to reach (Gregor).
2. **Rewards?** None. A badge is only an award, so it cannot change the balance of the game.
   Rewards could be their own spec later.
3. **Empire.** "All shops in `SHOPS`", not "4 shops": more shops will come (Gregor).
4. **Profit for streaks.** The day's `net` above 0, so a day where wages eat the whole
   profit does not count.
5. **Names on screen.** English, like the rest of the game's texts.
6. **When is a badge given?** The moment it is reached (Gregor): the first sale pops up at
   the sale, not at the end of the day. Badges that need the whole day come when it closes.
   The end of the day lists every badge of that day again. This changes roadmap 3b ("after a
   day") to "only by the server, after an accepted action or at the end of a day"; the
   security point stays: no request can grant a badge. Updated in
   `docs/feature-roadmap.md`.
7. **How it looks** (Gregor): a card at the top left, a bit smaller than a pop-up in the
   middle, that does not stop the game and leaves by itself; at the end of the day a list of
   the day's medals, at the end of the season all medals again.

## Out of scope

Rewards for badges, popularity, events, pricing changes, sounds, a badges screen inside the
2.5D world (the card lies over it), badges across several runs (a high score),
changing any existing game rule or number.

## Done when

1. Every badge is earned exactly on the day its condition is first true at the end of a
   day, and never twice (a test per badge, with a state set up for it).
2. Streaks: a day without profit (or without a played shift for `hard-worker`) starts the
   count again.
3. `empire` follows the number of shops in `SHOPS`.
4. No API request can add a badge: every endpoint is called with a `badges` field and the
   list stays the same (except the editor's `state`, which validates it).
5. The editor cuts badges together with the history; a bad `badges` patch is refused and
   changes nothing.
6. Badges are saved and loaded; a new run has none; an old database without the table
   loads.
7. The state shape stays complete and settable; no `random` call; money in whole cents.
8. `tests/` untouched apart from the new `tests/test_badges.py`; `uv run pytest` passes.
   Every badge has a tier (bronze, silver or gold).
   The first sale, a hire and an unlock give their badge at once (through the API, with the
   day still open); day badges wait for the end of the day; the day's result lists the badges
   given during it.
   In the browser: the panel shows all badges as medals; a new badge pops up in the middle
   as a card at the top left at the moment it is reached, below the stock card or the place
   label and beside the toasts (checked wide, narrow and phone size); the clock keeps running
   and the card leaves by itself after 4.5 seconds; several come one after the other; the evening report lists the
   day's medals; the end of the season shows the earned medals; no console errors.
9. PR "Closes #15", AI code review done and its findings handled.

## Security

Roadmap 3a and 3b `badges`: awarded only by the server, after an accepted action or at the
end of a day; no endpoint lets the browser grant a badge; the editor's `badges` patch is validated (known ids, no doubles)
and works only where the editor works; texts through `textContent` or `esc()`.
