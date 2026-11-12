# Popularity of the shops (`popularity`, issue #13)

Agreed by Felix on 2026-11-12 ("Ja, bauen" after draft v2). The numbers below were measured on a
throw-away prototype (not in the repo). Builds on `pricing` (#38, the socket
`FACTORS`), `events-and-disruptions` (#14), `balance-pass` (#76) and `guests` (#22). The roadmap names
Felix' `momentum` as the model (a score that follows how well the shop is run); this spec takes that
idea, not its code.

## What

Every shop has a **popularity**: a whole number from 0 to 100, 50 at the start (normal). It is the
shop's **memory of how its customers were treated**. Each day the shop that served customers gets a
**report card** from them (0 to 100); popularity then walks toward that report card, a fifth of the
way up and a third of the way down. Popularity moves the customers of the next days: 100 gives 15 %
more, 0 gives 15 % fewer.

One sentence for the whole rule: *a customer who wanted something and went home with nothing is a 0,
a customer who was served is as happy as the price was fair, and the shop's name follows the average
of that.*

It closes the loop of the game. Until now the day's numbers only flowed one way:

    weather, event, price  ->  customers  ->  stock and staff decide who is served
                                   ^                              |
                                   +---- popularity  <-- report card of the day

A party you were not ready for (150 % customers, not enough beer) does not only cost you the sales of
that day, it costs you customers on the next days. A fair price and full shelves do the opposite.

It plugs into the socket that `pricing` built: one more function in `FACTORS`. `customers_for`, the
curves and the mixes are not touched. It is calculated only on the server, from what really happened
that day, without randomness.

### The report card of a day (per shop)

The input is the day's result, `result["lines"]`: for every product of the shop `price`, `demand`
(the customers who wanted it, after weather, event and popularity) and `sold`. Everything is whole
numbers.

1. **Fairness of a price**, `fairness(price, ref_price)`: `x = price * 100 // ref_price`
   (the price in whole percent of the reference price), then `max(0, min(100, 300 - 2 * x))`.
   The reference price or less is fair (100), +25 % is half fair (50), +50 % or more is a rip-off (0).
2. **Score of the shop**, `day_score(lines)`: `demand = sum(demand)`; `happy = sum(sold * fairness)`
   over the lines; the score is `(happy + demand // 2) // demand` (half up), 0 to 100. A customer
   who was not served is in `demand` but adds nothing to `happy`: that is the empty shelf, the
   queue that was too long and the customer who gave up, all the same (Decide 7).
3. **No customers, no news.** A shop with `demand == 0` that day, and a shop that has no line (closed,
   locked, nobody worked in it), keeps its popularity.
4. **The walk**, `walk(popularity, score)`: `gap = score - popularity`. Going up it moves
   `ceil(gap / 5)`, going down `ceil(-gap / 3)`, in whole numbers, so it always arrives at the score
   and never passes it. Bad news travels faster than good news (Decide 3).

Worked example. The Cafe has popularity 50. Coffee at 2.20 EUR (ref 2.00): demand 10, sold 10,
fairness 80. Cake at 4.00 (ref 4.00): demand 6, sold 3, fairness 100. `happy = 10*80 + 3*100 = 1100`,
`demand = 16`, score `(1100 + 8) // 16 = 69`. Gap 19 goes up by `ceil(19/5) = 4`: popularity **54**.
The next day the cake is sold out all day, score 20: gap -34, down by `ceil(34/3) = 12`: popularity **42**.
At 54 the customers of the Cafe are `100 + 15 * 4 / 50 = 101.2 %`.

### What popularity settles at (measured)

If the player does the same thing every day, popularity walks to the report card of that play and
stays there. Measured on a throw-away prototype with exactly the integer rules above and the real game rules (Cafe,
30 days, whole days traded, seed 1), as the guide for the tests:

| Play | Report card | Popularity after 30 days |
|---|---|---|
| Reference price, full shelves | 100 | 100 |
| 10 % above the reference price, full shelves | 80 | 80 |
| 40 % above the reference price, full shelves | 20 | 20 |
| Reference price, half the customers served | 50 | about 50 |
| Reference price, 8 in 10 served (short on a rush) | about 80 | 73 to 78 |
| Empty shelves | 0 | 0 |

(A customer is only counted once the price was low enough to buy at all, so a greedy price lowers
popularity on top of the customers it already loses on the price curve.)

### State

- `state["popularity"]`: `{shop_id: int}` for every shop (also the locked ones, which stay at 50),
  each 0 to 100. `new_state` starts every shop at `POPULARITY_START = 50`.
- Stored in the `meta` table as JSON, like the seed and the override, so the database gets no new
  table. A save from before this spec has no entry: every read goes through
  `popularity_of(state, shop)`, which gives 50 for a missing key (old saves, states a test builds by
  hand).
- Complete and settable: the editor patch (`editor_set_state`) takes `popularity`.

### Rules in `logic.py`

- Constants, all placeholders to balance: `POPULARITY_START = 50`, `POPULARITY_EFFECT_PERCENT = 15`,
  `FAIR_PRICE_PERCENT = 100` and `GREEDY_PRICE_PERCENT = 150` (the two ends of the fairness line; the
  formula `300 - 2 * x` follows from them), `POPULARITY_RISE = 5` (a fifth) and `POPULARITY_FALL = 3`
  (a third).
- `fairness`, `day_score`, `walk` as above, pure and small, each with its own test.
- `update_popularity(new, result)`: changes `new["popularity"]` in place (the two callers hold a copy
  already, like `award_badges`) for every shop that has lines in `result`. Called by `trade_day` and
  `_close_shift` right before `award_badges`. The day's `result` is not changed, the history keeps its
  shape.
- `_popularity_factor(state, shop)`: the factor for `FACTORS`, after weather and event. Label
  `"Popularity: 62"`; both segments get `100 + POPULARITY_EFFECT_PERCENT * (popularity - 50) / 50`
  as an exact fraction (50 gives 100 %, 100 gives 115 %, 0 gives 85 %). At 50 it is 100 for both,
  so the explanation shows no line for it.
- `popularity_report(state, shop)`: the report card of the **last booked day** for a shop, from
  `history[-1]` with the same functions: `{"served": percent, "fair": percent, "score": n}` or `None`
  (no history, or the shop had no customers that day). Nothing new is saved.

### API and screen

- `GET /api/state`: `shops[].popularity` is `{"value": 62, "word": "Popular", "yesterday":
  {"served": 81, "fair": 85, "score": 69} or null}`. The words (by value): 0 to 24 "Avoided", 25 to 44
  "Unpopular", 45 to 59 "Known", 60 to 79 "Popular", 80 to 100 "Beloved". `app.py` builds the view; the
  browser decides no rule.
- The explanation of a customer number ("Why this number?") shows the line "Popularity: 62" with
  the customers after it, whenever it is not 50.
- Where the shops are shown (the shop cards of the dashboard and the shops panel of the campus): the
  value with its word and, small, why it moved: "Yesterday: 81 % served, prices 85 % fair". No other
  new screen. Texts through `textContent` or `esc()`.
- `POST /api/editor/state` with `{"patch": {"popularity": {"cafe": 80}}}`: every value a whole number
  from 0 to 100 (no bool, no float), every key a shop id; anything else is refused and nothing is
  saved. One or several shops, the rest stay as they are.

## Why

`pricing` and `events` make the customers depend on the price, the weather and the day. Popularity is
the long memory of the game: a mistake today (an empty shelf, a greedy price) is still felt in a few
days, and good work builds up. It also gives the demo and the walkthrough one more clear story:
"empty shelves lower popularity" (roadmap B4, scenario 4), and with the events a reason to read the
news before ordering. And it is honest: the report card is made only of numbers the player can see in
the evening report (demand, sold, price), so the player can always work out why a shop moved.

## Decide

1. **Per shop, not one number.** As in the issue: each shop has its own popularity. The Cafe being
   loved does not help the Surf Shop.
2. **One report card, two causes.** A single score from the customers (not points for service plus
   points for price): unserved is 0, served is as happy as the price was fair. So a shop cannot buy a
   good name with a low price and nothing on the shelf, nor with a full shelf at a rip-off price.
   Measured: a shop with nothing on the shelves falls to 0, a greedy one (40 % above) to 20.
3. **A fifth up, a third down.** Reputation is easy to lose and hard to build. The walk always arrives
   at the report card (rounded away from the current value, never past the score), so a steady player
   ends exactly where the play deserves, and there is no separate "drift" to explain.
4. **Small effect (85 to 115 %).** Popularity must not decide the season. Measured with the real
   `play_season` of `tests/test_balance.py` (two seeds, all shops, the best price every morning, which is
   often a rip-off price): the season gain moved from 5,852 and 5,067 EUR to 6,348 and 5,200 EUR,
   inside the band 3,000 to 8,000; the Cafe-only season from 1,695 and 1,694 to 1,783 and 1,764 EUR. The width is one
   constant to raise later.
5. **Fair price means the reference price.** One line, no hidden table: at the reference price or below
   the customer is happy (a lower price already pays through the price curve), +50 % is a rip-off.
6. **Volume only, same for both segments.** Like the events, popularity changes how many customers
   come, not how price-sensitive they are; students and visitors follow it the same. A weight per
   segment is a later spec.
7. **Served means served, not why.** A customer who gave up because the line was too slow counts like
   one who found an empty shelf: popularity follows what the customer got, not the cause. The
   evening report already names the cause. A shop that cannot keep up (too few staff) loses
   popularity until fewer customers come: a brake that works against the feedback of popularity itself.
8. **No news is no change.** A shop that was closed that day, or had no customers, keeps its number. It
   does not decay; only service moves it. (A decay for closed shops is a later spec if the demo needs it.)
9. **No forecast, no tips, no badges.** The evening report's tips stay weather only. Popularity is not
   hidden before the day opens: it is the player's own history, unlike the weather and the event.
10. **Not saved per day.** The number is saved in the state, not in the day's result; the report
    card of yesterday is calculated again from the history.
11. **Old tests.** Tests that play several days and pin customer numbers or the profit of a season
    (`tests/test_balance.py` bands, `test_full_run`, `test_staff`, `test_shop_scenarios`,
    `test_badges`) are checked while building. Day 1 is unchanged for every old test (popularity 50
    is 100 %). Checked while building (full suite, 1111 passed, 33 skipped): **no old test needs a
    change**, including the season bands of `tests/test_balance.py`. Only the new
    `tests/test_popularity.py` was added.

## Out of scope

- A popularity tip or forecast, rewards or badges for popularity, guests that remember a bad day
  (`specs/guests.md`), a weight per segment, a decay for closed shops.
- Popularity of single products, of the whole campus, or from staff and outfits.
- Any new screen: the value only appears where the shops are shown.

## Done when

1. **Start:** `new_state` has `popularity` 50 for every shop; a save from before this spec loads and
   `popularity_of` gives 50 everywhere; a saved value round-trips through the database; a new run resets it.
2. **Fairness:** `fairness` gives exactly 100 at 100 % and below, 80 at 110 %, 50 at 125 %, 0 at 150 %
   and above, and 100 for a price of 1 cent; never leaves 0 to 100.
3. **Report card:** `day_score` gives the worked example (69); everyone served at the reference price is
   100; nobody served is 0; the lines are weighted by customers, not by product; always 0 to 100,
   also for 0 stock and for extreme prices.
4. **Walk:** for every popularity and score from 0 to 100 the result lies between the two (never past
   the score), equals the score when the gap is small enough to close, rises by at most a fifth (rounded
   up) and falls by at most a third (rounded up), and stays 0 to 100. The worked example gives 54, then 42.
5. **Update:** after a day on which a shop sells everything at the reference price its popularity is
   higher; after a day with an empty shelf it is lower; a shop without lines or without customers keeps
   its number; the day's `result` is unchanged by it.
6. **Settling:** the table "What popularity settles at" holds on the real rules, with wide bands
   (full shelves at the reference price at least 90; 140 % of the reference price at most 35; empty shelves
   at most 5; half served between 40 and 60).
7. **Factor:** at 50 the customers equal today's; at 100 and at 0 they follow the percent of the formula
   exactly; the explanation has a "Popularity" line only away from 50; the factor stacks with weather and
   event and the cap `MAX_CUSTOMERS` still holds.
8. **One number:** `customers_today`, `start_shift`, `trade_day`, `stock_overview` and the state view show
   the same number also with a popularity that is not 50; the guests' plan uses the same percents.
9. **Both ways of booking:** `trade_day` and a played shift (`_close_shift`) change the popularity by the
   same rule for the same lines.
10. **Report:** `popularity_report` returns the card of the last booked day, `None` without history or
    without customers, and agrees with what `update_popularity` used.
11. **Editor:** the editor patch sets one or several shops; wrong types, bool, float, unknown shop, below 0
    and above 100 are refused with the saved state identical.
12. **Season guard:** `tests/test_balance.py` still passes unchanged; a new test plays a good, a greedy and
    an empty-shelf season and checks 6.
13. **Screen:** the shop cards (dashboard) and the shops panel (campus) show value, word and
    "yesterday"; text only via `textContent` or `esc()`; checked in the browser.

## Security

Computed only on the server from the day's real result, never from a request. The browser sends no
popularity; only the editor patch (`CT_EDITOR=1`, this computer only) can set it, and it validates every
field. Whole numbers only (integer arithmetic, no floats in the rules), clamped to 0 to 100. A refused
request leaves the saved state identical. No new randomness, no secrets, no unescaped text in the page.
