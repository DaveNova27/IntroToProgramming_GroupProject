# Editor mode (`editor-mode`, issue #55)

Agreed with David on 2026-11-09 (scope: "ja").

## What

A local editor mode with dev/cheat tools. It is **off** unless the server was started with
`CT_EDITOR=1`, and it answers only requests from this computer. With it on, an "Editor" panel
on the campus page can:

- **Cash**: set the cash to an amount, or add an amount.
- **Weather**: fix the weather (the existing `day_override`) or clear it. It stays fixed for
  today and the following days until cleared. Events do not exist yet; the override is a
  dictionary, so `events-and-disruptions` can add a key later.
- **Skip days**: let 1 or more days pass at once (`trade_day` each, with the current prices and
  stock, no player, as the dashboard's "open the stand" does).
- **Set the state**: one validated patch sets any of: day, cash, seed, weather override, stock,
  prices, shops (unlocked and level), player position.
- **Reset the run**: a new run, optionally with a chosen seed.

The patch is the base for `demo-scenarios` (#23): loading a scenario is a patch of the whole state.

### Rules in `logic.py`

All pure, they return a new state or raise `RejectedAction`, and change nothing when refused.

- `MAX_CASH = 100_000_000` cents.
- `editor_cash(state, mode, cents)`: `mode` is `"set"` or `"add"`; `cents` a whole number (no
  bool, no float); the result must be between 0 and `MAX_CASH`.
- `editor_skip_days(state, days)`: whole number from 1 to the days left (`LAST_DAY - day + 1`);
  refused while a day is open or after the season. Calls `trade_day` that many times; all or nothing.
- `shop_at_level(shop_id, level)`: the shop entry for a level: 0 is locked; level `n` has the
  start product and the first `n - 1` window offers in window order. Max level = 1 + number of offers.
- `editor_set_state(state, patch)`: `patch` is a dictionary with only these keys (anything else is
  refused): `day` (1 to `LAST_DAY + 1`), `cash`, `seed` (0 to 2^32 - 1), `day_override` (`None` or
  `{"weather": id}`), `stock` ({product: 0..storage}), `prices` ({product: 1..`MAX_PRICE`}), `shops`
  ({shop: {"level": n}} or a full entry), `player` ({zone, x, y}, as `move_player`). Unmentioned
  fields stay. A full entry must be consistent: locked has level 0, no products, no places; unlocked
  has the start product, products only from that shop, level equals products plus places, places 0 to 2.
  Refused while a day is open. History is cut to the days before the new `day` when `day` is
  set (a day cannot have a result and still lie ahead).
  Every field is checked before anything is returned, and the storeroom limit per shop is checked for the stock as a whole.

### Server (`app.py`, `db.py`)

- `editor_switch_on()`: `CT_EDITOR=1` **and** the request comes from loopback and carries no
  `X-Forwarded-For`/`Forwarded` header (same test as the demo switch, now one shared helper).
  Checked inside every action; when off, an editor request is refused with the rule message
  "The editor is off." and the run is unchanged.
- Endpoints (all `POST`, JSON): `/api/editor/cash`, `/api/editor/weather`, `/api/editor/skip-days`,
  `/api/editor/state`, `/api/editor/reset` (needs `confirm: true`, optional `seed`).
- `GET /api/state` has `editor: true|false` and, when on, `editor_info` (weather ids and names, max levels, limits). It never contains the seed.
- Editor changes are saved with `db.save_new_run`, because they may move the day back or cut the
  history (`db.save` never removes a stored day). One transaction, as before.

### Screen

An "Editor" tool button and panel on the campus page, only shown when the state says `editor: true`.
Fields and buttons per function, answers shown as a toast. All text through `textContent`.

## Out of scope

Employees and popularity (not on `main` yet; a follow-up that only needs two more patch keys),
events, scenarios and explanation texts (`demo-scenarios`), a way to set a state while a day is open,
any change to `tests/`.

## Done when

1. Without `CT_EDITOR=1` every `/api/editor/*` call is refused and the saved run stays identical;
   the same from a non-loopback address and with a forwarding header. `GET /api/state` says `editor: false`.
2. With the switch: set and add cash work; bool, float, text, negative result and above `MAX_CASH` are refused.
3. Weather can be fixed and cleared; an unknown id is refused.
4. Skipping N days adds N history entries, moves the day by N, and equals N calls of `trade_day`;
   0, negative, too many, bool, text, a running day and a finished run are refused.
5. The patch can set every field of the state (a test sets each one and reads it back, also after
   a save and load); bad types, non-finite numbers, out-of-range values, unknown ids and unknown keys
   are refused, and a refused patch changes nothing (also when the first keys are valid).
6. Setting an earlier day cuts the history; the saved run matches after a reload.
7. Reset starts day 1 with a chosen or drawn seed and needs `confirm: true`.
8. The seed is never in an API answer. Money is integer cents everywhere. No `random` call without the seed.
9. `tests/` untouched (new file `tests/test_editor_mode.py`), `uv run pytest` passes. In the browser
   with `CT_EDITOR=1`: the panel shows and works, no console errors; without it, no editor button.
10. PR "Closes #55", AI code review done and its findings handled.

## Security

Roadmap 3a point 7 and 3b `demo-scenarios`: anything that sets the state directly is local only and
behind a switch, checked on the server, never only in the screen. Every field validated (type, whole
numbers, finite, range, ids from the fixed lists); a rejected action changes nothing; error texts are our
own rule messages. The panel draws server text with `textContent`.

## Known limits

The switch protects against the web and other computers, not against another program on this computer.
Employees and popularity cannot be set yet.
