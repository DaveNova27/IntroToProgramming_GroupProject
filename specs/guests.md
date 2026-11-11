# Guests that choose a shop (`guests`, issue #22), small version

Written 2026-11-11 after the talk with the professor: he is happy with the game and the map;
the one thing he wants is that **the people think for themselves**. This is the small version of
`guests`: each guest decides where to go, and you can see it. No needs, no moods, no groups.
Builds on `pricing` (#62, who buys how much), `events-and-disruptions` (#91) and the walkers of
`world-art` (the decorative people, `static/world/walkers.js`).

## What

Today a customer is a number. `customers_today` says "7 coffees today" and `_new_shift`
spreads them over the shift. Nobody chooses anything, and the people on the map are decoration
that buys nothing.

After this spec the crowd of a day is a list of **guests**. A guest has a kind (student or
visitor, from `pricing`), a start place, and a taste. The guest **chooses a shop** by a score,
walks there on the map, and joins its queue when it arrives. The screen shows why
("Rain, the Beach Cafe is far, short queue at the Cafe").

```
score(guest, shop) = share(kind, shop)        what the guest's kind wants at this shop today
                   x taste(guest, shop)       80 to 120 %, a personal preference, from the seed
                   x near(start, shop)        100 % at the door, falling with the walk (in ticks)
                   x queue(shop)              100 % with no queue, falling for every waiting guest
chooses the shop by a seeded weighted draw over the shops that are open
```

- `share(kind, shop)` is what `pricing` already works out (price curve x weather x event x mix).
  It is **not** counted a second time: the weather and the price already live there.
- The new thinking is what `pricing` lacks: **distance**, **personal taste** and **the queue
  the guest sees**. Two guests of the same kind on the same day can now go to different shops.
- A guest whose best score is too low (everything too expensive or too far) **stays home**:
  it is not in the queue and counts as nothing. This is the new "lost before arriving".
- Then the guest picks a product of that shop, weighted by the product's share today.

### Where the numbers come from

All in a new module `guests.py` (rules, no HTTP):

| Function | What |
|---|---|
| `make_guests(state)` | The guests of the day, from `state["seed"]`, `state["day"]` and the day context only. `random.Random(f"{seed}:{day}:guests")`, same style as `make_event`. Same state gives the same guests. |
| `choose(state, guest, queues)` | The shop and the product of one guest and the reason (a fixed id from a list). Pure. |
| `plan_day(state)` | Goes through the guests in id order, each one sees the queues of those before. Returns for every shop its guests with product, arrival tick and reason. |

`_new_shift` takes the queue of its shop from `plan_day` instead of `customers_today`
(the arrival tick keeps the shape it has: spread over the shift, plus the walk).

The crowd size of the day stays what `pricing` computes: the sum of `customers_today` over the
open shops, split by kind. Guests **spread** this crowd; they do not make it bigger.

### What the player sees

- On the map the guests of today walk from their start (Dorm, beach way, Nova entrance) to the
  door of their shop with `findPath`, queue there and leave. They replace the decorative
  walkers while the day is open (the walkers stay in the morning and the evening).
- At most `MAX_VISIBLE_GUESTS` (12) are drawn at once; the others exist on the server only.
  Drawing is a pure function of the server list and the tick: no `Math.random`.
- A thought bubble above a guest for a moment when it decides: "Cheap coffee", "Too far",
  "Long queue, Cafe instead", "It rains". Text from a fixed list, through `textContent`.
- A panel "Today's guests": how many chose which shop, how many stayed home, and the most common
  reason, so the player can react (a shop with a long queue loses guests; a lower price or a
  second employee changes the next day).
- Everything is in the API answer the screen already reads (the day context); no new endpoint
  is needed to play.

### What it changes in the game

A shop with a long queue loses guests to the next shop; a shop far from the Dorm gets fewer
students and more visitors; a shop nobody likes today gets less. The player learns that
service speed matters, which makes staff (`staff`) matter more. For the demo (3 minutes) this
is visible: the guests split between the Cafe and the Beach Cafe and change when the player
changes a price or the weather is forced.

## Decide

1. **Does the crowd size stay?** Recommendation: yes, guests only spread the crowd that
   `pricing` computes. Then the balance of `balance-pass` holds and only the split between
   shops moves. Alternative: guests also decide how many come. Larger and it breaks the
   balance guard.
2. **Tests.** `customers_today` and `customers_for` stay as they are, so `tests/test_pricing.py`
   stays untouched. Tests that count the queue of a shop and compare it to `customers_today`
   (`tests/test_shop_process.py`, `test_shop_scenarios.py`, `test_shop_skip.py`,
   `test_staff.py`, `test_hidden_weather.py`, `test_events.py`, `test_balance.py`) may no longer
   hold when guests move between shops. Recommendation: first build so that **no old test
   changes**. Per shop the guests may deviate by at most `MAX_SPREAD` (30 %) from
   `customers_today`, and a day with a single open shop (the start) gives exactly
   `customers_today`, because there is nothing to choose. Most tests run on that day-1 case. If
   a test still has to change, the owner confirms it in their own words, the test and the
   reason are written here and into the PR (rule in `AGENTS.md`), and nothing is weakened.
3. **Constants.** `near`, `queue` and `taste` curves, `MAX_SPREAD`, "too low" threshold: all
   placeholders, set once in `guests.py` and tuned with a simulation like `balance-pass`
   (a season must still end in the same band).
4. **Who plays the other shops?** Not decided here. Only the Cafe has a played shift
   (`SHIFT_SHOPS`); guests that choose another shop are served by its staff or lost, as
   today. If a shop has no staff, its guests are lost: the thought says "Nobody serves here".
5. **Walk time on the server.** The server gets a fixed table of walk ticks from each start
   to each shop (data in `world.py`, no pathfinding on the server). The browser draws the
   walk to match it. The position of a guest decides no rule.
6. **Felix.** The walkers are his code (`walkers.js`). He should agree that real guests
   replace them while the day is open.

## Out of scope

Needs and moods (hunger, thirst, boredom), groups of friends, guests buying several products,
guests that remember a bad day (`popularity`), outfits, a new endpoint, changing prices or the
price curves of `pricing`, the walk of the player's own shift (`shop-walk`), disruptions,
the demo scenarios (`demo-scenarios` only reads the guests).

## Done when

1. `make_guests` / `plan_day` are deterministic: same seed, day and state give the same list;
   another seed gives another one (new test file `tests/test_guests.py`).
2. The crowd of a day is conserved: the sum over the shops equals the sum of
   `customers_today` of the open shops, minus the guests that stayed home (counted).
3. On a day with one open shop the queue equals today's (no choice, no change).
4. A long queue sends later guests to another shop; a shop with a very high price gets fewer
   of the price-sensitive kind; a locked shop gets none. Each in a test.
5. Rejected and crafted input: the new numbers are never taken from the request; a crafted
   request changes nothing, as before.
6. The state stays complete and settable (guests are rebuilt from seed, day and state, they
   are not stored) and the day context override still works, so the demo can force a weather
   and show the guests change.
7. On the map: the guests walk to their shops, show their thoughts, queue and leave; the
   panel "Today's guests" matches the server; no console errors; desktop and phone width; the
   frame time stays about 50 fps with 12 guests.
8. A season simulation (like `balance-pass`) ends in the same band; the numbers are pasted.
9. `tests/` untouched apart from the new test file (unless Decide 2 happens); `uv run pytest`
   passes. PR "Closes #22", AI code review done and its findings handled.

## Security

Roadmap 3a and 3b `guests`: the number of guests is capped (`MAX_CUSTOMERS`, `MAX_VISIBLE_GUESTS`),
and guest data comes only from the server, built from the seed. The browser sends no guest,
no choice, no position that a rule reads. Thought texts are a fixed list written with
`textContent`. The seed is never exposed (as in `outlook`).
