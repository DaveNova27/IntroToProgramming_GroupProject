# Guests that choose a shop (`guests`, issue #22), small version

Written 2026-11-11 after the talk with the professor: he is happy with the game and the map;
the one thing he wants is that **the people think for themselves**. This is the small version of
`guests`: each guest decides where to go, and you can see it. No needs, no moods, no groups.
Builds on `pricing` (#62, who buys how much), `events-and-disruptions` (#91) and the walkers of
`world-art` (the decorative people, `static/world/walkers.js`).

Built the same day with Claude at David's request, with the recommendations below (Decide 1 to 5
as recommended, for David to confirm in the PR; 6 is open for Felix). No existing test changed.

## What

Before this spec a customer was a number. `customers_today` said "7 coffees today" and
`_new_shift` spread them over the shift. Nobody chose anything, and the people on the map were
decoration that bought nothing.

After this spec the crowd of a day is a list of **guests**. A guest has a kind (student or
visitor, from `pricing`), a start place (Dorm, Arrival Plaza, Beach) and a taste for every shop.
Most guests are **regulars**: they go where `pricing` sent them. A third of the guests of every
product (`CHOOSER_PERCENT`, 30) **look around**: they compare the shops that have an employee
today and go to another one when it is clearly better. On the map every guest walks to the line of their
shop and shows a thought ("Long queue at the Beach Cafe: the Cafe instead").

```
score(guest, shop) = near(start, shop)    100 % at the line, 1.5 % less for every tick of walking (at least 40 %)
                   x queue(shop)          100 % with no queue, 3 % less for every guest who would wait there (at least 40 %)
                   x taste(guest, shop)   80 to 120 %, a personal preference, from the seed
a guest who looks around goes to the best other shop if it scores at least 115 % of the wished one
```

- How many people want what today stays `pricing`'s answer (price curve x weather x event x
  mix). It is **not** counted a second time: the score weighs only what `pricing` does not know,
  **the walk**, **the queue the guest would find** and **personal taste**.
- The crowd keeps its size: guests only spread it (Decide 1). A product takes at most 30 % more
  guests than its own (`MAX_SPREAD`) and never more than `MAX_CUSTOMERS`; it keeps at least 70 %
  (only the 30 % who look around can leave). A product nobody of that kind buys at its price
  gets nobody.
- A guest who changes shop picks a product there, weighted by what their kind wants of it today.
- Guests decide in the order they would arrive; each one sees the queues of everyone placed before.
- The thought says why: today's event or weather ("Hot: good day for the Beach Cafe"), a cheap
  price ("Coffee is cheap today"), the reason to change ("The Cafe is closer", "Long queue at ...",
  "Feels like ... today"), the reason to stay ("Looked around: the Cafe is closest") or "My usual
  Cafe". A fixed list of texts.

### Where the numbers come from

All in a new module `guests.py` (rules, no HTTP, nothing saved):

| Function | What |
|---|---|
| `guest_shops(state)` | The shops guests come from today: unlocked and served today, where the player can work a shift (`SHIFT_SHOPS`) or with a working employee. |
| `served_shops(state)` | The shops with a working employee: only these can **receive** a guest who looks around (Decide 4). |
| `plan_day(state, shops, first_id)` | The guests of the day, from `random.Random(f"{seed}:{day}:guests")`, the prices and the day context only. Same state, same guests. Returns per shop its guests with id, kind, start, product, offset (ticks after the shift starts), wish (the shop wanted first), walk and thought. |
| `day_plan(state)` | The whole day's plan with a summary per shop (total, came from, went to, top thoughts), worked out **once** when the day opens. |
| `for_shop(state, shop)` | The guests of one shop for its queue (own guests in the old queue's order, then those who came from elsewhere) and its summary, taken from the stored plan. |

`open_day` stores the plan in the shift (`guest_plan`, with `guest_shops`), so every queue made
later in the day (the player's shift, a shop staffed at noon) comes from the same plan and the
shops' summaries always agree. A shop that is not in the plan, or whose products changed since (a
product bought on the open day), plans alone with ids after those of the day. `logic._new_shift`
builds the queue from `for_shop`. Each queue entry carries its guest (id, kind, start, wish, walk,
thought); the summary is stored in the shift as `guests`. The arrival tick is
the old one (`(j x SHIFT_TICKS) // count + k` after the start), so **a shop that runs alone gets
exactly the old queue**: same customers, same order, same ticks. Starting a shift without an open
day, or a shop that gets staff later in the day, plans alone.

The places are data in `world.py` (`GUESTS`): three start places, the line of every shop (head and
direction), the walking speed (1.45 tiles a tick) and the detour (1.3). `guest_walk_ticks(start,
shop)` is the straight line x detour / speed, at least 3. It only weighs the choice; it does not
move the arrival.

### What the player sees

- On the map (`static/world/guests.js`) every guest of a running shop walks from their start to
  the line of their shop with `findPath`, timed by the server's ticks so they reach the line on the
  tick the server says, waits there facing the counter, and walks back home once served or out of
  patience (up to 12 walk home at once). A guest inside the Nova shows only while its roof is gone,
  like the employees.
- At most 12 guests are drawn (`MAX_VISIBLE_GUESTS`), shared equally by the running shops; within
  a shop the first to set off. The API sends only guests who have set off (no future customers).
- A thought bubble for 4.5 seconds after setting off, 9 seconds for a guest who changed shop (in
  red), and always next to the player. Neighbours in a line think at three heights.
- The passers-by (`walkers.js`) step aside, 4 instead of 14, only while a shift is running
  (`guests.active` in the API).
- The Shift panel lists **Today's guests** per running shop: how many, from which shops they came,
  where guests who wanted this shop went instead, the most common thought. The Cafe, before the
  player starts the shift, says its guests come when the shift starts (only a shop the player can
  start a shift in is announced like that).

### What it changes in the game

A shop with a long queue loses guests to the next shop that has an employee; a shop far from where
a guest starts is less attractive. Staff now draws guests to a shop just by being there.
For the demo (3 minutes) it is visible: force the weather to heat or rain and the guests split
differently between the Cafe and the Beach Cafe, with the reason in their bubbles.

Balance (the guard of `balance-pass`, plus seeds 3 to 6), the gain at the end of the season in euro:

| | seed 1 | 2 | 3 | 4 | 5 | 6 | mean of seeds 1 and 2 (the guard) |
|---|---|---|---|---|---|---|---|
| before (nobody looks around) | 5,929 | 5,260 | 5,996 | 5,514 | 4,959 | 4,749 | 5,594 |
| with guests | 5,852 | 5,067 | 5,795 | 5,460 | 4,814 | 4,660 | 5,460 |

About 2 % less: a guest who goes to another shop sometimes finds no stock there. The Cafe alone
is unchanged (1,695), because a single shop has nothing to choose. The band 3,000 to 8,000 holds.

## Decide

1. **Does the crowd size stay?** Yes (built): guests only spread the crowd that `pricing`
   computes. Nobody stays home; that idea of the first draft would have lowered the balance.
2. **Tests.** No existing test changed. Guests choose only among the shops served today, and the
   old tests play one shop at a time (or start a shift without an open day), so their queues are
   the old ones exactly. The new checks are in `tests/test_guests.py`.
3. **Constants.** `CHOOSER_PERCENT`, `MAX_SPREAD`, `SWITCH_MARGIN`, `NEAR_LOSS`, `QUEUE_LOSS`,
   `TASTE`, `STRONG`, the start weights per kind and the places in `world.GUESTS` are
   placeholders, set once in `guests.py` and `world.py`.
4. **Who plays the other shops?** Changed after the code review (finding 3). A shop that only the
   player can run (the Cafe without an employee) may **lose** guests but never **receives** one:
   nobody can promise when the day opens that the player starts a shift there, and a guest sent
   to an empty counter would be neither sold nor lost. Its own guests still come as `pricing`
   says. A guest moves only to a shop with a working employee. In the demo, hire a Cafe employee to
   let the Cafe receive guests.
5. **Walk time on the server.** A fixed formula on the places in `world.py`; no path finding on
   the server. The position of a guest decides no rule.
6. **Felix.** The passers-by are his code (`walkers.js`): only four of them stay out while guests
   walk. He should agree.

## Out of scope

Needs and moods (hunger, thirst, boredom), groups of friends, guests buying several products,
guests that remember a bad day (`popularity`), changing one's mind at the counter, outfits, a new
endpoint, changing prices or the price curves of `pricing`, `trade_day` (the day without a player
has no guests), the walk of the player's own shift (`shop-walk`), disruptions, the demo scenarios
(`demo-scenarios` only reads the guests).

## Done when

1. `plan_day` is deterministic: same seed, day and state give the same guests; another seed gives
   others (`tests/test_guests.py`).
2. The crowd of a day is conserved: the guests of all shops are exactly the sum of
   `customers_today` of the shops guests come from today; every product stays between 70 % and
   130 % of its own guests. The shops of one day tell the same story (who left one is who arrived
   at the other), and no id is used twice in a day, also for a shop staffed at noon.
3. A shop that runs alone gets the old queue (customers, order, ticks).
4. A long queue sends guests elsewhere (and without the queue factor nobody leaves for it); a
   product nobody buys at its price gets no guests; a locked shop or one without an employee
   receives none; the weather override moves the guests (the demo).
5. Every guest of the day is booked: sold plus lost is the planned total. A crafted request
   cannot send guests or shops; a rejected action changes nothing.
6. The state keeps its fields (no new top-level field; the guests live in the queue) and survives
   a restart; the day context override works as before.
7. On the map the guests walk to their shops, show their thoughts, queue and leave; the panel
   "Today's guests" matches the server; no console errors; the frame rate with 12 guests is no
   lower than without (checked in headless Chromium: 29 to 33 frames a second before the day,
   35 to 39 with the guests).
8. The season simulation ends in the same band (table above).
9. `tests/` untouched apart from the new test file; `uv run pytest` passes. PR "Closes #22", AI
   code review done and its findings handled.

## Security

Roadmap 3a and 3b `guests`: the number of guests is capped (`MAX_CUSTOMERS` per product,
`MAX_VISIBLE_GUESTS` on the screen), and guest data comes only from the server, built from the
seed. The browser sends no guest, no choice and no position that a rule reads; a crafted field in
a request is ignored. The API sends only guests who have already set off. Thought texts come from a
fixed list and are drawn on the canvas or written with `esc()`. The seed is never exposed.
