# Price, customers and the day's conditions (`pricing`, issue #38)

Agreed by Felix on 2026-11-09 and built in two commits: part 1 (everything except the weather, no existing test touched) and part 2 (the weather factor and the changes to old tests, confirmed by Felix in his own words the same day, see Decide 4).

## What

Today the price decides the customers with three fixed steps (`demand()`: 10 up to the
reference price, 5 up to twice it, 0 above). That is the solo project's placeholder. This spec
replaces it with a real demand system, in **one function**, `customers_for`, which `shop-process`
already made the single place that turns a price into customers.

The idea in one sentence: **not one anonymous crowd, but two kinds of customers who react to the
price in different ways, mixed differently in every shop, and moved by the day's conditions.**
That one idea gives every shop its own character, makes the best price depend on the shop and on
the day, and gives the later specs (events, trend, popularity, outfit, guests) a place to plug in.

```
customers(product, today) = round( sum over segments of
      shop_mix[shop][segment]  x  curve[segment](price / reference price)  x  today's percents[segment] )
      at most MAX_CUSTOMERS
```

### Part 1: two segments, each with its own price curve

| segment | who | how it reacts to the price |
|---|---|---|
| `students` | the campus crowd: many, on a budget | steep: cheap draws a crowd, above the reference price they melt away, nothing above 200 % |
| `visitors` | beach and Nova guests: fewer, relaxed | flat: hardly notice a higher price, but even they stop at 250 % |

Customers per segment as a share of its base, at a price given as % of the reference price
(straight lines between the points, flat below 50 %, zero above the last point):

| price % of reference | 50 | 75 | 100 | 125 | 150 | 175 | 200 | 225 | 250 |
|---|---|---|---|---|---|---|---|---|---|
| students | 170 % | 135 % | 100 % | 65 % | 28 % | 8 % | 0 | 0 | 0 |
| visitors | 115 % | 107 % | 100 % | 95 % | 85 % | 70 % | 50 % | 20 % | 0 |

### Part 2: every shop has its own mix of the two (the shop's character)

Units per product per day at the reference price in neutral conditions. Both numbers add up to
10 in every shop, the same 10 as today, so nothing at the reference price changes.

| shop | students | visitors | character |
|---|---|---|---|
| Cafe | 8 | 2 | volume business: the best price is only 9 to 13 % above the reference price |
| Merchandise | 5 | 5 | in the middle: 24 to 30 % above |
| Beach cafe | 6 | 4 | in the middle: 20 to 25 % above |
| Surf shop | 3 | 7 | premium business for visitors: the best price is 38 to 43 % above (up to 53 % with the rounding of whole customers) |

What a shop sells at each price (both segments added, neutral conditions, before rounding):

| price % of reference | 50 | 75 | 100 | 125 | 150 | 175 | 200 | 225 | 250 |
|---|---|---|---|---|---|---|---|---|---|
| Cafe | 15.9 | 12.9 | 10.0 | 7.1 | 3.9 | 2.0 | 1.0 | 0.4 | 0 |
| Merchandise | 14.2 | 12.1 | 10.0 | 8.0 | 5.7 | 3.9 | 2.5 | 1.0 | 0 |
| Beach cafe | 14.8 | 12.4 | 10.0 | 7.7 | 5.1 | 3.3 | 2.0 | 0.8 | 0 |
| Surf shop | 13.2 | 11.5 | 10.0 | 8.6 | 6.8 | 5.1 | 3.5 | 1.4 | 0 |

Example, coffee in the Cafe (reference €2.00, cost €0.80), neutral day, one day:

| price | €1.00 | €2.00 | €2.25 | €2.50 | €3.00 | €3.50 | €4.00 | €5.00 |
|---|---|---|---|---|---|---|---|---|
| customers | 16 | 10 | 9 | 7 | 4 | 2 | 1 | 0 |
| profit | €3.20 | €12.00 | **€13.05** | €11.90 | €8.80 | €5.40 | €3.20 | €0 |

Cheaper brings more people but little profit; a little above the reference price earns the most;
it falls off slowly, not off a cliff. In the old rule the best price was always exactly twice the
reference price (5 customers at the last cent before the cliff), a trick.

### Part 3: the day's conditions move the segments

The factors are whole percents per segment. All factors multiply, in any order. **Now there is
one: the weather.**

- The shop's weather percent stays exactly as it is in `WEATHER[...]["demand_percent"][shop]` (the
  single source, the `outlook` PR reads the same table) and applies to both segments. The percents
  are combined as exact fractions, never with integer division, so a later table value that is not
  a multiple of 10 cannot be cut off silently.
- **Visitors react to the weather more than students**: an extra percent for the visitors only,
  `VISITOR_WEATHER`: sun 130, heat 120, rain 70, storm 100. A student goes to the lecture hall
  anyway, a visitor stays at the beach or stays away. Storm is 100 because the shop table already
  holds the whole storm effect (cafe 100 %, surf shop 20 %).
- So the weather changes **how many** customers come and also **who** comes. The mix moves, and with
  it the best price: sun and heat bring visitors, a shop with many visitors can charge more; rain
  leaves the students, it pays to stay cheaper. Worked out for the first product of each shop:

| best price in % of reference (customers at the reference price) | neutral | sun | rain | heat | storm |
|---|---|---|---|---|---|
| Cafe (coffee) | 113 (10) | 115 (8.5) | 111 (13.2) | 114 (6.2) | 113 (10) |
| Merchandise (hoodie) | 130 (10) | 135 (11.5) | 125 (10.2) | 134 (8.8) | 130 (10) |
| Beach cafe (beer) | 123 (10) | 124 (16.8) | 117 (3.5) | 124 (19.4) | 123 (2) |
| Surf shop (surfboard) | 143 (10) | 151 (15.7) | 136 (4.0) | 148 (13.7) | 143 (2) |

  These are calculated on the exact values, before the customers are rounded to whole people; in
  play the whole numbers make the best price a little noisier, most of all in the surf shop where
  few customers are left. The weather mostly decides the volume; the best price moves up to 15
  points in the shops with many visitors and hardly in the Cafe. All of it is tuning knobs.

### Part 4: slots for what comes next

`FACTORS` is a list of small functions `state, shop -> {segment: percent}`; `segment_percents`
multiplies them. This spec registers one (weather). Later specs add theirs and touch nothing else:
events ("orientation week": students 150 %, "regatta": visitors 160 %), trend, popularity of a
shop (all segments), outfit. A factor that names only one segment leaves the other at 100.

**How an event would plug in (a note for `events-and-disruptions`, #14; nothing of it is built
here):** the event is rolled from the seed into the day context like the weather (a field `event`
next to `weather`), the demo override can fix it, the browser never can. A function
`event_percents(state, shop)` returns a percent per segment and is added to `FACTORS`; the curves,
the mixes and `customers_for` stay untouched. Because it works per segment, an event can aim:
"exam period" students 150 %, visitors 70 %; "party" both 150 %. The explanation of Part 5 gets
one more line ("Event: Party") and `outlook` can forecast it from the same table. Example,
beach cafe on a hot party day at the reference price: students 6 x 1.8 x 1.5 = 16.2, visitors
4 x (1.8 x 1.2) x 1.5 = 13.0, together 29 customers (today 10); this stacking is what `MAX_CUSTOMERS`
is for. Two points for that spec to settle:

- **The tests of group A must not be edited a second time.** A day on which an event is rolled would
  break them again. Recommendation: an override that names no event means "no event" (the part of
  the day context that the override does not name is neutral, not rolled), so the one storm line
  that group A gets in this spec is enough then.
- **Volume only.** Percents change how many customers come, not how price-sensitive they are. An
  event that shifts the price tolerance itself ("rich guests": visitors accept 120 % as if it were
  100 %) needs a second kind of factor (a shift on the price axis). Add it only when a concrete event
  needs it.

Disruptions (strike, outage) are a stock or staff matter and do not go through the customer count;
that is for #14 to decide.

### Part 5: the player can see why

A price that gives "7 customers" without a reason is a black box. The server explains every number:

```
Coffee at €2.50, Cafe, hot day
  base                          10
  your price (125 % of ref.)     7    (students 5, visitors 2)
     students keep 65 % of their normal amount at this price, visitors 95 %
  weather: Hot                   4
  customers today                4    (students 3, visitors 1)
  expected profit              4 x €1.70 = €6.80   (if the stock lasts)
```

Each line is the running whole number after that step (computed from the exact value and rounded
at the end of every step, so the last line is exactly the real customers). The split into students
and visitors adds up to the total (largest remainder, ties to students). The weather line and
later ones are only shown if the factor is not 100 %. Two lines are there to teach, not only to
report: "students keep 65 %, visitors 95 %" shows *why* the price hits the Cafe harder than the
surf shop, and the expected profit shows the trade-off in money (fewer customers at a higher
margin against more customers at a lower one). The profit is `min(customers, stock) x (price -
cost)`, the same stock limit as `stock_overview`. The screen never tells the player the best price;
it shows the numbers and the player finds it, with the live preview.

### Where the number is used (all through the same function)

`customers_today(state, product)` takes today's price, the reference price, the product's shop mix
and today's segment percents. Used by:

- `start_shift`: the queue of a played day (the `planned` numbers),
- `trade_day`: the day without a player (the numbers in its result lines, `demand`),
- `stock_overview`: `sells_today`,
- the screen (below).

If one of them kept the old rule, the screen would promise something else than the shift delivers.
Therefore all four switch together. The queue entries stay as they are (no segment in them; who a
single customer is belongs to `guests`, #22).

### The screen

The browser decides no rule, so the screen shows server numbers only. Today the old rule is copied
into the browser twice (`zoneFor` in `static/app.js` and `previewDemand` in `static/world/ui.js`,
both read `demand_levels`); after this spec neither copy exists.

- `GET /api/state` gets, per product, `customers` (today's number) and `customer_breakdown` (the
  lines of Part 5), and a top-level `price_curves` per shop (the second table above, as points, for
  drawing the meter). `demand_levels` and `products[].demand` go away. Their readers are the
  dashboard (`static/app.js`) and the price panel of the campus page (`static/world/ui.js`); both
  are changed. No test reads them.
- Dashboard product card: "sells up to 10/day" becomes "about 4 customers today", with a "why?"
  line that opens the breakdown. The three-zone meter becomes a curve-shaped meter of the
  product's shop with the marker at the price.
- Campus price panel: the note "Customers buy 10 a day at or below the reference price..." and the
  line "Sells up to N a day" show the same "about N customers today" and the breakdown.
- Live preview while typing: a new **read-only** `POST /api/price_preview` with `{product, price}`
  answers `{customers, customer_breakdown}`; it saves nothing. Both screens call it (a short pause
  after typing) and show "not saved yet · about 5 customers". One server rule, no copy in either
  script.

## Decide (my recommendations)

1. **One crowd or two segments.** Recommendation: two segments with a mix per shop. A single curve
   times a weather percent is a lookup table: every shop behaves the same, the weather only turns
   a volume knob, and there is nothing to learn. Two segments cost one more number per shop and
   give: shop identity (cafe cheap and busy, surf shop expensive), a best price that moves with the
   day, and clear sockets for events and popularity. Alternative: one curve (simpler to read, but
   exactly that lookup table). Two segments is the most I would put in now: three would add
   numbers nobody can tune before the first real play test.
2. **The numbers.** All curve points, mixes and `VISITOR_WEATHER` are placeholders to balance. The
   design promises only these properties, which tests guard: every shop sells exactly 10 at the
   reference price; customers never rise as the price rises; nobody buys at 250 % or more; the
   best price of a product sits in a band per shop (cafe 105 to 125 %, beach cafe 115 to 135 %,
   merchandise 120 to 140 %, surf shop 130 to 160 %) and never at or below the cost.
3. **Where the weather applies.** Recommendation: in all four places above, so that the shift, the
   day without a player, the stock hint and the screen always agree. This is what `day-context`
   Decide 1 handed to this spec. Price: **23 existing tests change** (next point), because a fresh
   run has the seed's weather on day 1 (seed 1: heat, cafe 60 %). *Fallback if you do not want that
   many test changes:* build parts 1, 2, 4, 5 and the screen now (0 tests change, I ran it: 486
   passed) and add the weather together with the events in a later spec. Then `day-context`
   Decide 1 moves to that spec. I would still do the weather now: it is the core of the roadmap's
   B1/B2 loop and the table already exists. The build is two commits: first everything without the
   weather (no test changes), then the weather (the test changes).
4. **Old tests (needs your own words, see rule in AGENTS.md).** I ran the whole suite with this
   exact model in a copy of the repo: without the weather nothing fails (486 passed); with the
   weather these 23 fail, all for the same reason (they pin counts of a fresh seed-1 run, and day 1
   is heat), never because a check got weaker. Three groups:

   **Group A, 16 tests: they mean "a normal day" and only pin 10 customers per product.** Cafe and
   merchandise are both at exactly 100 % in a storm (and the visitor percent of a storm is 100,
   which is why I chose it that way), so the fix is one line in each test's setup: fix the weather
   with the existing `day_override` to a storm. I tried exactly that (storm forced for every
   fresh run): all 16 pass again with their old numbers. Nothing else in the test changes.
   - `test_shop_process.py` (4): `test_a_shift_starts_in_the_cafe_with_an_even_queue_and_an_empty_counter`,
     `test_selling_takes_one_unit_and_pays_the_price_in_cents`,
     `test_the_closed_day_is_booked_in_the_history_like_trade_day`,
     `test_waiting_customers_leave_after_their_patience`
   - `test_shop_scenarios.py` (4): `test_every_shop_sells_every_product_in_a_full_day[cafe]` and
     `[merchandise]`, `test_a_day_without_stock_loses_every_customer[cafe]` and `[merchandise]`
   - `test_shop_skip.py` (2): `test_skipping_keeps_what_was_sold_before`,
     `test_the_shift_clock_starts_with_the_shift_not_with_the_day`
   - `test_stock_overview.py` (2): `test_overview_shows_units_value_and_todays_sales`,
     `test_nothing_sells_on_a_complete_run`
   - `test_first_feature.py` (2): `test_trading_one_day_reconciles`,
     `test_restart_restores_state_with_one_history_record`
   - `test_full_run.py` (2): `test_full_run_gives_the_final_result`,
     `test_complete_run_survives_a_restart`

   Alternative for group A: change the expected numbers to the heat numbers instead (cafe 60 %, so
   6 instead of 10 customers). I advise against it: the tests would then be about heat without
   saying so.

   **Group B, 6 tests: a storm does not help, so their numbers change.** Surf shop and beach cafe
   are at 20 % in a storm, and no weather is 100 % for all four shops. These tests walk through
   every shop, so each shop's expected number becomes that shop's own number from the formula (day
   1 of seed 1 is heat). The checks stay the same, only the number they compare to changes; the new
   numbers are written next to the old ones in the PR description. As built: a product at the
   reference price has 14 customers in the surf shop and 19 in the beach cafe on that hot day; the
   price test of the beach cafe expects 19, 10 and 0 customers at 100 %, 150 % and 300 % (before 10,
   5, 0); the Cafe and Merchandise rows of the same tests get the storm line and keep their 10.
   - `test_shop_scenarios.py`: `test_every_shop_sells_every_product_in_a_full_day[surf_shop]` and
     `[beach_cafe]`, `test_a_day_without_stock_loses_every_customer[surf_shop]` and `[beach_cafe]`,
     `test_the_price_decides_how_many_customers_come[1.0-10]` and `[1.5-5]`

   **Group C, 1 test: it pins the opposite of this spec on purpose.**
   `test_day_context.py::test_the_weather_does_not_change_the_customers_yet`: its name says "yet".
   It becomes its successor: the weather changes the customers by the percent of the shop.

   Two tests also pin the function itself, and the model respects both: `customers_for(200, 200)
   == 10` is called with two arguments (so the shop mix is an optional third argument with a neutral
   default mix), and a cake at 225 % of its reference price must sell 0 in the Cafe (so the
   visitors' curve is already below half a customer there). `demand()` stays in `logic.py`
   untouched, because `test_first_feature.py::test_demand_boundaries` pins it; it is the solo
   project's rule CT R1, no longer used by the game, with a comment saying so.
5. **Reference prices.** Recommendation: they stay as they are. The reference price now means "the
   price at which a shop sells 10 of it to a neutral day", the cost margin at it is 48 to 68 %, and
   the best price (about 110 to 150 %) leaves every product with a profit. All catalogue tests stay valid.
   A reference price that moves (trend, inflation) is the job of the trend spec.
6. **The cap (`MAX_CUSTOMERS`).** It is the most customers of one product in one shift or day;
   the result of the formula is `min(30, result)`. Why it exists: the factors multiply, so a cheap
   price (x1.6), a hot day at the beach cafe (x1.8) and later a party (x1.5) together would give
   40 to 50 customers of one product. They would all be put into the queue and spread over the 90
   ticks of a shift (one every two ticks), while the counter holds only 20 units. Everything above
   30 is simply not created. Recommendation: 30. With the weather alone the cap is never reached
   (checked: the largest number anywhere is 28, beach cafe in heat at half price); it is a safety
   net for the day events and popularity arrive. It is one number in one place, to be raised by
   the spec that needs more.
7. **Selling below cost.** Recommendation: allowed (the player learns it). The balance guard in
   "Done when" 6 checks that the best price is never at or below the cost.
8. **A new endpoint for the live preview.** Recommendation: yes, read-only, so the browser never
   holds the rule. Alternative: each screen interpolates the published points itself (fewer
   requests, but then the rounding rule lives in two scripts plus the server, and can drift apart;
   today the old rule is already copied twice).
9. **What I did not put in, and why.** Each of these is a real idea; each would add state or
   numbers that cannot be tuned yet, or belongs to another issue:
   - *Price memory* (customers get used to your prices, a sudden rise hurts, slow rises do not).
     Needs state per product and a check that it cannot be gamed by flipping prices. Good next
     spec once this one is played.
   - *Weather per product* (cold drinks up in the heat, hot coffee down). Needs a second table next
     to `WEATHER` that `outlook` does not know. The segments already give most of this effect.
   - *A "fair price" label* (cheap, fair, pricey): `popularity` (#13) needs its own measure of fair
  (B1 step 5: it rises with fair prices, falls with too high ones). The price as % of the
  reference price is the natural input, but where "too high" starts differs by shop (the surf
  shop's best price is 140 %), so that spec has to decide it with the shop mix in hand.
- *Customers who know their segment* in the queue: that is `guests` (#22).
   - *Events, trend, popularity, outfit*: their own issues; Part 4 is their socket.
   - *Rivals and a price index*: no rivals exist yet.

## Out of scope

Events, trend, popularity, outfit (their own specs; they plug in as one more factor), the look of
weather in the world (#16), how a day runs and the shift (#36), staff behaviour, individual guests
and their choices (#22), forecast of the weather (`outlook`, #45), saving the weather or the mix in
the history of a day, price memory, per-product weather, price changes during a shift (prices stay
fixed while a shift runs, as now), changing `WEATHER`, the reference prices or the catalogue.

## Done when

1. `customers_for(price, ref, mix, percents)`: with the default mix and no percents it gives the
   neutral number; every answer is an `int`; half up; at most 30. The curve points of both segments
   give exactly the numbers above, a straight line between the points, flat below 50 %, zero from
   200 % (students) and 250 % (visitors).
2. Every shop's mix adds up to 10: every shop sells exactly 10 of every product at the reference
   price in neutral conditions. Customers never rise as the price rises (checked for every price
   from 1 cent to 3x the reference price, every product, every shop, every weather). Nothing sells
   at 250 % or more; a cake at 225 % in the Cafe sells 0 in every weather. (Checked in the
   prototype for every cent of every product in every shop and weather: no price ever sells more
   than a lower one, and the largest number is 28.)
3. The percents multiply and the order does not matter; a factor of 0 gives 0; a factor that names
   one segment leaves the other unchanged; an unknown segment is ignored.
4. The queue of `start_shift`, the lines of `trade_day`, `sells_today` of `stock_overview` and
   `customers` of the screen are the same number for the same state (one test over all four).
5. The weather decides: the same price gives different customers in sun, rain, heat and storm,
   built from the table percent of that product's own shop and the visitor percent; `day_override`
   changes it; in a storm the cafe and merchandise sell exactly their neutral numbers.
6. Balance guard: for every catalogue product the price with the highest profit per day lies inside
   its shop's band (Decide 2) in neutral conditions, and no price at or below the cost is the best.
7. The explanation: its customers line is exactly `customers`; the segment split adds up to the total;
   the "keep" percents are the two curve values at that price; the expected profit is
   `min(customers, stock) x (price - cost)` in whole cents; a factor at 100 % has no line; the same state always gives the same text. No `random`, all numbers
   whole, no floats anywhere (exact fractions), same state gives the same queue; state stays
   complete and settable; saves from before this spec still load (the spec adds no state).
8. `POST /api/price_preview` returns the customers and the explanation for a product and price and
   changes nothing (the saved run is identical before and after); unknown product, a product the
   player does not own yet, a price that `/api/price` would refuse (typed in euros like there: more than two
   decimals, not a number, zero, negative, above the maximum, `NaN`/`Infinity`, wrong types): refused with a readable message and HTTP 400.
9. Old tests: the 23 listed above are changed only as written in "Decide" 4 (16 get one weather line,
   6 get new numbers, 1 is replaced by its successor) and confirmed by the owner of this PR in
   their own words; nothing else in `tests/` is touched; new checks are in `tests/test_pricing.py`.
   `uv run pytest` passes (it runs `tests/` and `checks/`).
10. In the browser, on the dashboard and in the price panel of the campus page: the customers of
    today are shown with the "why" lines, the dashboard meter shows the curve of the product's shop,
    the live preview changes while typing and after "Save" the number is the saved price's;
    switching the weather with the demo override changes the numbers and the lines; `README.md`
    names the new rule instead of `demand` and its note about staff ("levels only matter once
    pricing brings more customers") is brought up to date; no console errors.
11. PR "Closes #38", AI code review done and its findings handled.

## Security

The price preview is read-only and validates its input with the same rules as `set_price`; the
product must be one of the catalogue ids and owned. A rejected request changes nothing. Error texts
are our own rule messages. The curves, the mixes and the factors are constants on the server; the
browser only shows what the server sends. The explanation is built from numbers and our own fixed
texts (the weather name comes from the `WEATHER` table), never from client input.
