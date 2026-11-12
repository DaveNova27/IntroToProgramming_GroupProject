"""Guests that choose a shop (specs/guests.md, issue #22): the small version.

How many people want what today is still the price logic's answer (logic.customers_today, one
number per product). This module turns that crowd into guests. Each guest has a kind (students
or visitors), a place they set off from, a taste for every shop, and is either a regular or a
guest who looks around. A guest who looks around compares the shops that run today on what the
price logic does not know: the walk there, the queue they would find, and their own taste. When
another shop is clearly better, they go there instead and buy something there.

The crowd stays the same size: guests only spread it. A shop that runs alone today gets exactly
logic.customers_today, in the same order as before (nothing to choose).

Rules only: no HTTP, nothing saved. The state is only read. All randomness comes from the seed,
random.Random(f"{seed}:{day}:guests"), so the same state gives the same guests.
"""

import random
from collections import Counter
from fractions import Fraction

import logic
import world

# All numbers are placeholders to balance (specs/guests.md, Decide 3).
CHOOSER_PERCENT = 30  # of the guests of a product this many look around (rounded down)
MAX_SPREAD = 30  # a product takes at most this many percent of its own guests from other shops
SWITCH_MARGIN = 115  # another shop must score this many percent of the wished one to switch
NEAR_LOSS = Fraction(3, 2)  # percent less for every tick of walking
NEAR_MIN = 40
QUEUE_LOSS = 3  # percent less for every guest who waits there when this one would arrive
QUEUE_MIN = 40
TASTE = (80, 120)  # a guest's taste for a shop, in whole percent
STRONG = 115  # a factor at or above this percent is worth a thought ("Rainy: ...")
MAX_VISIBLE_GUESTS = 12  # the most guests the screen draws at once
# where the guests of each kind set off from (weights; the places are world.GUESTS["starts"])
START_WEIGHTS = {
    "students": {"dorm": 55, "plaza": 30, "beach": 15},
    "visitors": {"beach": 50, "plaza": 40, "dorm": 10},
}
# how a thought names a shop
CALLED = {"cafe": "the Cafe", "beach_cafe": "the Beach Cafe", "merchandise": "the Merch shop",
          "surf_shop": "the Surf Shop"}


def guest_shops(state):
    """The shops guests can choose from today: unlocked and served today, either the player's home
    shop (logic.SHIFT_SHOPS) or a shop with a working employee. Fixed when the day opens. The player
    can take a shift in any other unlocked shop too (specs/shift-any-shop.md): it plans its guests
    alone when that shift starts (for_shop)."""
    return [shop for shop in logic.SHOPS if state["shops"][shop]["unlocked"]
            and (shop in logic.SHIFT_SHOPS
                 or any(e["shop"] == shop and e["working"] for e in state["employees"]))]


def served_shops(state):
    """The shops with a working employee: only these can receive a guest who looks around. A shop
    that only the player can run (the Cafe) may lose guests but never gains one, because nobody
    can promise at the start of the day that the player will start a shift there."""
    return [shop for shop in logic.SHOPS if state["shops"][shop]["unlocked"]
            and any(e["shop"] == shop and e["working"] for e in state["employees"])]


def _say(text):
    return text[0].upper() + text[1:]


def _kind_amounts(state, shop, kind):
    """What the guests of one kind want of each product of a shop today (exact, not rounded)."""
    percents = logic.segment_percents(state, shop)
    out = {}
    for pid in state["shops"][shop]["products"]:
        item = logic.CATALOGUE[pid]
        mix = {kind: logic.SHOP_MIX[shop][kind]}
        out[pid] = logic.segment_amounts(state["prices"][pid], item["ref_price"], mix, percents)[kind]
    return out


def _wishes(state, shops, rng, first_id=0):
    """Every guest of the day with the product they want first, in the order of the old queue:
    shop by shop, product by product (k), customer by customer (j)."""
    guests = []
    for shop in shops:
        percents = logic.segment_percents(state, shop)
        for k, pid in enumerate(state["shops"][shop]["products"]):
            count = logic.customers_today(state, pid)
            if count == 0:
                continue
            amounts = logic.segment_amounts(state["prices"][pid], logic.CATALOGUE[pid]["ref_price"],
                                            logic.SHOP_MIX[shop], percents)
            split = logic._split(amounts, count)
            kinds = [kind for kind in amounts for _ in range(split[kind])]
            rng.shuffle(kinds)
            lookers = set(rng.sample(range(count), count * CHOOSER_PERCENT // 100))
            for j in range(count):
                kind = kinds[j]
                weights = START_WEIGHTS[kind]
                guests.append({
                    "id": first_id + len(guests), "kind": kind,
                    "start": rng.choices(list(weights), weights=list(weights.values()))[0],
                    "taste": {s: rng.randint(*TASTE) for s in shops},
                    "looks": j in lookers,
                    "wish": shop, "shop": shop, "product": pid, "k": k, "j": j,
                    # the same arrival as the old queue (logic._new_shift), from the shift's start
                    "offset": min((j * logic.SHIFT_TICKS) // count + k, logic.SHIFT_TICKS - 1),
                })
    return guests


def _near(guest, shop):
    return max(Fraction(NEAR_MIN), 100 - NEAR_LOSS * world.guest_walk_ticks(guest["start"], shop))


def _queue(arrivals, shop, offset):
    """How a shop's queue looks to a guest arriving at `offset`: the guests who arrive there in the
    patience window before (they would still be waiting)."""
    waiting = sum(1 for o in arrivals[shop] if offset - logic.PATIENCE_TICKS < o <= offset)
    return max(QUEUE_MIN, 100 - QUEUE_LOSS * waiting)


def _factors(guest, arrivals, shop):
    """The three things a guest weighs, in percent: the walk, the queue, their taste."""
    return {"near": _near(guest, shop), "queue": Fraction(_queue(arrivals, shop, guest["offset"])),
            "taste": Fraction(guest["taste"][shop])}


def _score(factors):
    return factors["near"] * factors["queue"] * factors["taste"]


def _biggest(mine, other):
    """The factor where `mine` beats `other` the most (ties: near, queue, taste)."""
    return max(("near", "queue", "taste"), key=lambda f: (mine[f] / other[f], -("near", "queue", "taste").index(f)))


def _day_thoughts(state, shops):
    """The thought today's conditions give a guest of a kind at a shop, or None:
    {(shop, kind): text}. The event comes first, then the weather (worked out once per plan)."""
    context = logic.day_context(state)
    event, weather = context["event"], logic.WEATHER[context["weather"]]["name"]
    out = {}
    for shop in shops:
        _label, by_event = logic._event_factor(state, shop)
        _label, by_weather = logic._weather_factor(state, shop)
        for kind in logic.SEGMENTS:
            if event and by_event[kind] >= STRONG:
                out[shop, kind] = f"{event['name']}: off to {CALLED[shop]}"
            elif by_weather[kind] >= STRONG:
                out[shop, kind] = f"{weather}: good day for {CALLED[shop]}"
            else:
                out[shop, kind] = None
    return out


def _wish_thought(state, guest, day_thoughts):
    """Why a guest wanted their shop in the first place: the strongest thing of today, if any."""
    shop, kind, pid = guest["shop"], guest["kind"], guest["product"]
    if day_thoughts[shop, kind]:
        return day_thoughts[shop, kind]
    item = logic.CATALOGUE[pid]
    x = Fraction(state["prices"][pid] * 100, item["ref_price"])
    if logic._curve_percent(logic.SEGMENTS[kind]["curve"], x) >= STRONG:
        return f"{item['name']} is cheap today"
    return f"My usual {CALLED[shop][4:]}" if not guest["looks"] else _say(f"off to {CALLED[shop]}")


SWITCH_THOUGHTS = {
    "near": "{to} is closer",
    "queue": "Long queue at {wish}: {to} instead",
    "taste": "Feels like {to} today",
}
STAY_THOUGHTS = {
    "near": "Looked around: {wish} is closest",
    "queue": "Looked around: short queue at {wish}",
    "taste": "Looked around: {wish} it is",
}


def _decide(state, guest, shops, arrivals, room, wants, rng, day_thoughts, served):
    """One guest who looks around: stay or go to another shop. Changes guest and room."""
    own = _factors(guest, arrivals, guest["wish"])
    options = []
    for shop in shops:
        if shop == guest["wish"] or shop not in served:
            continue
        buyable = {pid: a for pid, a in wants[shop][guest["kind"]].items() if a > 0 and room[pid] > 0}
        if buyable:
            options.append((shop, _factors(guest, arrivals, shop), buyable))
    if not options:
        guest["thought"] = _wish_thought(state, guest, day_thoughts)
        return
    best, factors, buyable = max(options, key=lambda o: (_score(o[1]), -shops.index(o[0])))
    names = {"wish": CALLED[guest["wish"]], "to": CALLED[best]}
    if _score(factors) * 100 > _score(own) * SWITCH_MARGIN:
        products = list(buyable)
        pid = rng.choices(products, weights=[int(buyable[p] * 1000) + 1 for p in products])[0]
        room[pid] -= 1
        guest.update(shop=best, product=pid)
        guest["thought"] = _say(SWITCH_THOUGHTS[_biggest(factors, own)].format(**names))
    else:
        guest["thought"] = _say(STAY_THOUGHTS[_biggest(own, factors)].format(**names))


def plan_day(state, shops=None, first_id=0):
    """The guests of the day and where each one goes. shops: the shops guests come from (default
    guest_shops); only the served ones (served_shops) can receive a guest who looks around.
    first_id: the id of the first guest, so a shop planned later never reuses an id of the day.
    Returns {shop: [guest, ...]} for every one of those shops, each guest with
    id, kind, start, shop, product, offset (ticks after the shop's shift starts), wish (the shop
    they wanted first), walk (ticks from their start), thought, and k and j (their place in the
    old queue). Same state, same plan."""
    shops = guest_shops(state) if shops is None else [s for s in logic.SHOPS if s in shops]
    rng = random.Random(f"{state['seed']}:{state['day']}:guests")
    guests = _wishes(state, shops, rng, first_id)
    served = served_shops(state)
    arrivals = {shop: [] for shop in shops}
    counts = Counter(g["product"] for g in guests)
    room = {pid: min(logic.MAX_CUSTOMERS - n, n * MAX_SPREAD // 100) for pid, n in counts.items()}
    wants = {shop: {kind: _kind_amounts(state, shop, kind) for kind in logic.SEGMENTS} for shop in shops}
    day_thoughts = _day_thoughts(state, shops)
    choosing = len(shops) > 1 and bool(served)
    # the regulars are where they always are; then those who look around decide, in the order
    # they would arrive, each one seeing the queues of everyone placed before
    for guest in guests:
        if not (choosing and guest["looks"]):
            arrivals[guest["shop"]].append(guest["offset"])
            guest["thought"] = _wish_thought(state, guest, day_thoughts)
    for guest in sorted((g for g in guests if choosing and g["looks"]), key=lambda g: (g["offset"], g["id"])):
        _decide(state, guest, shops, arrivals, room, wants, rng, day_thoughts, served)
        arrivals[guest["shop"]].append(guest["offset"])
    plan = {shop: [] for shop in shops}
    for guest in guests:
        guest["walk"] = world.guest_walk_ticks(guest["start"], guest["shop"])
        del guest["taste"], guest["looks"]
        plan[guest["shop"]].append(guest)
    return plan


def _ordered(shop, mine):
    """A shop's guests in the old queue's order: its own (product by product, customer by customer),
    then those who came from another shop, by id."""
    return sorted(mine, key=lambda g: (g["wish"] != shop, g["k"] if g["wish"] == shop else 0,
                                       g["j"] if g["wish"] == shop else 0, g["id"]))


def _summary(plan, shop, mine):
    left = Counter(g["shop"] for other in plan.values() for g in other
                   if g["wish"] == shop and g["shop"] != shop)
    return {
        "total": len(mine),
        "came": dict(Counter(g["wish"] for g in mine if g["wish"] != shop)),
        "left": dict(left),
        "thoughts": [{"text": text, "count": n}
                     for text, n in Counter(g["thought"] for g in mine).most_common(3)],
    }


def day_plan(state):
    """The whole day's plan, worked out once when the day opens and stored in the shift, so queues
    made later in the day (the player's shift, a shop staffed at noon) all come from the same plan:
    {shop: {"products": [...], "guests": [...], "summary": {...}}}."""
    plan = plan_day(state)
    return {shop: {"products": list(state["shops"][shop]["products"]),
                   "guests": _ordered(shop, mine), "summary": _summary(plan, shop, mine)}
            for shop, mine in plan.items()}


def for_shop(state, shop):
    """The guests of one shop for its queue and what they did: (guests, summary).

    From the day's plan when the shift is part of an open day and the shop still sells what it
    sold when the plan was made. Otherwise (a shop that opens later, a product bought in the
    meantime, a shift without an open day) the shop plans alone, with ids after those of the day."""
    stored = (state.get("shift") or {}).get("guest_plan") or {}
    mine = stored.get(shop)
    if mine and mine["products"] == list(state["shops"][shop]["products"]):
        return mine["guests"], mine["summary"]
    first_id = 1 + max((g["id"] for part in stored.values() for g in part["guests"]), default=-1)
    alone = plan_day(state, [shop], first_id)
    guests = _ordered(shop, alone[shop])
    return guests, _summary(alone, shop, guests)
