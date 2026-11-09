# Employees: hire, level up, wages (`staff`, issue #20)

Agreed with David in the session on 2026-11-09. Built on the branch `staff`.

## What

A shop can have employees. The flow is the one the team asked for: buy the shop
(`shop-unlock`), buy an employee place in its window (**this hires the employee at once**, no
second fee), then pay to level the employee up. An
employee costs a daily wage in cents. The wage is deducted at the end of the day and
shown in the day report.

An employee does the same two actions as the player in `shop-process`: **refill** (storeroom
to counter) and **sell** (counter to the first waiting customer). Employees run on the
server, tick by tick, with no randomness. The browser only shows them.

An employee is also a **person in the game**: a named figure (drawn with `drawPersonFigure`)
who stands and walks in the shop while working. The player can also **fire** an employee.
If the wage cannot be paid the employee does not leave: they just **stop working**.

### Places and jobs (data per shop)

- A **place** is what the player buys in the shop window (`staff_1`, `staff_2`, €60,
  `shop-unlock`). **Buying a place hires the employee of that place straight away** (level 1,
  working), for the place price only; `buy_upgrade` does it, but only for shops in
  `STAFF_SHOPS` (every shop) and places that have a job. The place purchase itself is unchanged. `state["shops"][shop]["staff_places"]`
  says how many places the shop has bought; the shop's level limits it as before.
- Each shop lists its jobs as data: `SHOPS[shop]["jobs"] = ["refiller", "seller"]`. Place `n`
  has job `jobs[n-1]`. So the Cafe's first place is a refiller and the second a seller.
  Another shop can list other jobs (data only, no code change). A shop with 1 job
  has only one place that makes sense; places beyond `len(jobs)` cannot be hired.
- `JOBS` is one table with the numbers per level (all placeholders to balance):

  | Job | Level 1 | Level 2 | Level 3 |
  |---|---|---|---|
  | refiller: units carried per tick | 1 | 2 | 3 |
  | seller: sells one unit every N ticks | 4 | 3 | 2 |
  | wage per day (cents) | 800 | 1_200 | 1_800 |

  Constants: `HIRE_PRICE = 3_000`, `EMPLOYEE_MAX_LEVEL = 3`,
  `UPGRADE_PRICES = {2: 5_000, 3: 8_000}` (price to reach that level).

### State

`state["employees"]` is a list of plain dicts, complete and settable, `[]` at the start:

```
{"id": 1, "name": "Mia", "shop": "cafe", "place": 1, "job": "refiller", "level": 1,
 "working": true}
```

`id` is a whole number from a counter in the state (`employee_seq`, saved in `db.py`), so an id is never used twice, not even after someone was dismissed: a stale request for an old id cannot hit a newer employee (no randomness, no clock). `name`
comes from a fixed list in the data, by `(id - 1) % len(list)`, so it is the same for the same
state. One employee per place. `working` is `false` while the wage could not be paid (see
"Close of the day"). An old save loads with `employees = []`.

### Actions (pure functions that return a new state, like `buy`)

- `hire(state, shop, place)`: only for a **free** bought place, i.e. one that was emptied by
  `fire_employee` (buying a place already hires). Shop id from `SHOPS`, shop in `STAFF_SHOPS` (all four shops), shop unlocked, `place` a whole number
  (not bool) with `1 <= place <= staff_places` and `place <= len(jobs)`, place still free,
  run not finished, `HIRE_PRICE` affordable. Cash - `HIRE_PRICE`, new employee on level 1.
- `upgrade_employee(state, employee_id)`: whole number id of an existing employee, level
  below `EMPLOYEE_MAX_LEVEL`, price `UPGRADE_PRICES[level + 1]` affordable. Cash - price,
  level + 1. The wage rises with the level, so the next day costs more.
- `fire_employee(state, employee_id)`: whole number id of an existing employee. The employee
  is removed, the place stays bought and is free again, nothing is refunded, the level is
  lost (hiring again costs `HIRE_PRICE` and starts on level 1). A fired employee earns no
  wage for that day. Allowed any time, also during a running day.
- `tick(state)` is extended (see "Day"): after the clock advances, employees act.

### Day (how staff fit into `open_day`, `start_shift`, `skip_shift`)

1. **Who is working.** Employees with `working = true` work while the day is open, also when
   the player starts no shift. A shop with no employee and no player shift sells nothing, as in `shop-process`
   and `shop-skip` (roadmap 3c: without staff it stays closed).
2. **`open_day`.** The shift starts automatically when the day starts. If a shop in
   `SHIFT_SHOPS` has at least one working employee, the server opens that shop's shift at
   tick 0 by itself (the same queue, counter and `SHIFT_TICKS` as
   `start_shift`), marked `shift["staffed"] = True`. Then the player is in the shift too:
   `refill` and `sell` by the player are allowed next to the employees, and `start_shift`
   is refused ("A shift is already running"), as it is today for any open shift.
   Without employees `open_day` is unchanged.

   **Every shop with employees (added after the first merge).** `STAFF_SHOPS` is every shop;
   `SHIFT_SHOPS` stays where the *player* can play a shift (the Cafe until `shop-walk`). The
   state holds one player shift, `state["shift"]`. Every other staffed shop runs in
   `state["shift"]["extra"][shop]`: the same fields as a shift (counter, queue, planned,
   sold, lost, clock), built by the same code, run only by its employees. The first shop of
   `SHIFT_SHOPS` takes the player's shift if it is free, all others go to `extra`. Each
   `tick` runs every crew through the same `refill` and `sell` rules on the shared stock and
   cash, in shop order. When the day opens, or when someone is hired or a place is bought on
   an open day and a whole shift still fits, the shop's shift starts; later it does not.
   `start_shift` by the player keeps the crews running. Without a second staffed shop the
   state has no `extra` key and nothing changes.
   **Editor mode (`specs/editor-mode.md`).** Its state patch and day skipping are refused while
   a day is open, so a crew in `extra` is never patched half way. Lowering a shop there
   dismisses the employees whose place is gone, in every shop. The editor does not hire: a
   place set by a patch is hired through `hire`.
3. **`start_shift`.** Unchanged for a shop with no employees. On a shop with employees it
   is only reached through `open_day`; the shift is the same one.
4. **Each tick**, after the tick counter went up and before impatient customers leave, in
   this fixed order: the refillers, then the sellers, each in order of `id`.
   **One employee covers the missing job:** if the shop has no working refiller, its working
   employees refill too; if it has no working seller, they sell too. They do the covered job
   at the speed of their own level. So a single employee runs the counter alone; with
   two employees each keeps his own job.
   - *Refiller*: moves up to its units-per-tick from the storeroom to the counter, only products
     somebody wants at the shift's prices (planned customers > 0), the one with the fewest units
     on the counter first (ties in `CATALOGUE` order), stopping at
     the storeroom stock and at the counter space. It calls the same checks as `refill`.
   - *Seller*: only on ticks where `tick % N == 0` (N from its level). Sells one unit to the
     first waiting customer whose product is on the counter, through the rules of `sell`.
     If nobody can be served it does nothing (no refusal, no error).
   - Employees act only while the shift is running (not after `_end_shift`, not after the
     last day).
5. **`skip_shift`.** Still only runs the ticks. With employees the ticks now include their
   work, so the staffed shop sells; without employees nobody is served, exactly as before.
6. **`trade_day`.** Unchanged: the day without a player. Employees neither work nor get a
   wage there (named as a known issue in the README, decided with `pricing`/`demo-scenarios`).
7. **Close of the day (`_close_shift`).** Wages are paid after the sales are booked.
   Only employees with `working = true` earn a wage, paid in order of `id`. An employee whose
   wage the cash cannot cover is **not paid and stops working** (`working = false`): they stay
   hired with their place and level, but do not act on the following days and earn no wage
   while they are not working. After the wages, every non-working employee whose wage the
   remaining cash covers (in order of `id`, cash not reduced) starts working again for the
   next day; their wage is charged at that next close. Cash never goes below 0.
   The day result gets new fields: `wages` (cents paid), `wages_unpaid` (list of ids who
   stopped), `net` (`gross_profit - wages`); `cash_after` is after wages. Existing fields keep
   their meaning.

### API and screen

`POST /api/staff/hire` `{"shop", "place"}`, `POST /api/staff/upgrade` `{"employee_id"}` and
`POST /api/staff/fire` `{"employee_id"}`; each takes JSON, validates every field, answers with
the new state. `GET /api/state` shows `employees` (id, name, shop, place, job, level, working,
today's wage) and the places still free. The shop window in `static/world/ui.js` lists the
employees, a Hire button on each free place, an Upgrade and a Fire button on each employee,
with the price. Names and texts through `textContent`. The day report shows the wages and
anyone who stopped working.

**Employees as people on the map.** Each employee is drawn in the Cafe as its own figure
(`drawPersonFigure`, the walk and the poses from `world-art`, a look that differs per `id`).
A working refiller walks between a storeroom spot and the counter spot, a working seller
stands at the counter, a non-working employee sits or stands idle at the break spot. The
spots are data in `world.py` (added for the Cafe if missing, next to `cafe-counter`). What a
figure does is taken only from the state the server sent (job, working, and the last
refill or sale of the tick); the browser decides no rule. The figures do not collide with
the player's rules: they are decoration of server facts and read no position.

## Out of scope

Outfits (#21), popularity changes, customers with their own choices (#22 `guests`),
shifts and shift factors, maintenance, moving an employee to another place or shop, staff in
`trade_day` with staff, the world (work spots, figures) for the shops other than the Cafe, balancing the numbers, employees that
talk or have their own moods, different outfits (#21), employees who walk through the whole
Nova or outside the shop.

## Done when

1. A refiller and a seller in the Cafe, and also a lone employee, run a whole day with no
   player action: stock
   goes to the counter, units are sold, cash rises, and the wages are deducted at the end.
2. Buying a place hires its employee for the place price only; `hire` (a free place), `upgrade_employee` and the wage cost exactly the listed prices, in integer cents.
   `fire_employee` frees the place, refunds nothing and drops the level.
3. Refused, and the saved run stays identical: unknown or locked shop, place not bought, place
   without a job, place already taken, unknown or non-whole employee id, bool/float/string/
   negative/zero ids, level already at the maximum, too little cash for hiring or upgrading,
   firing an employee that does not exist, anything after the last day.
4. Cash never goes negative at the end of the day: with too little cash the employees who
   cannot be paid stop working (they stay hired), in order of `id`, and the day still closes.
   They work again once the remaining cash covers their wage. Tested, also the case of two
   employees where only the first can be paid.
5. A shop with no employee behaves exactly as before (`skip_shift` sells nothing,
   `start_shift` and `open_day` unchanged). `trade_day` is unchanged.
6. Employees work in a fixed order with no `random` call; the same state gives the same day.
7. A crafted request cannot hire above the shop's bought places, cannot upgrade past level 3,
   cannot make an employee act outside a running shift.
8. Employees survive a restart (`db.py`, an `employees` table); a save from before this spec
   loads with no employees. The state is complete and settable.
9. `uv run pytest` passes; `tests/` is untouched (no test exception planned; if a day
   result test conflicts with the new fields, stop and name it here before changing it).
   New checks go in a new file, `tests/test_staff.py`.
10. In the browser: hire, upgrade, fire, a staffed day and the wage line in the report work,
    the employees are visible as named figures in the Cafe and move as the server says,
    refused actions show why, no console errors.
11. PR "Closes #20", AI code review done and its findings handled.
12. (Staff in every shop) Employees work in all four shops on the same day; the day result
    has the lines, revenue, lost and wages of every crew that ran, and `shops` when more
    than one ran. Wages are paid only for shops that ran. The crews share stock, cash and the
    clock; `stock_value` counts every counter. Tested in `tests/test_staff_all_shops.py`.

## Decide: test change for staff in every shop

One old test referred to data this change moves on purpose (which shops have staff). Confirmed
by David (owner of the spec) in the session on 2026-11-09:

- `test_a_place_in_a_shop_without_staff_work_hires_nobody` in `tests/test_staff.py` bought a
  place in the Beach Cafe and expected no employee. It is now
  `test_a_place_in_any_shop_hires_its_employee` and expects the employee of that shop. Reason:
  the Beach Cafe (and every shop) has staff work now. Nothing is weakened, skipped or deleted.

New checks are in `tests/test_staff_all_shops.py`.
