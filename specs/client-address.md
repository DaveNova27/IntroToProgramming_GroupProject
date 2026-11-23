# The visitor's address behind Cloudflare (`client-address`)

Asked for by Felix on 2026-11-23, item B3 of the audit of 2026-11-21: the follow-up that
`request-limits` (#134, Christopher) prepared by measuring. Christopher cannot work on it today, so
Felix takes it over. Builds on `deploy-ready` (`CT_PROXY`, the limit of new players per address).

## Why

With `CT_PROXY=1`, `client_address()` takes the **last** entry of `X-Forwarded-For`. The measurement of
`request-limits` in Render's log (8 lines, 2026-11-21 to 2026-11-23) shows the chain:

- 6 times, every real visit: `X-Forwarded-For has 3 entries; CF-Connecting-IP present (the first
  entry); True-Client-IP present; Forwarded absent`;
- 2 times, each about 2 s after a restart: `X-Forwarded-For has 0 entries; CF-Connecting-IP absent;
  ...` (a call from inside Render, not through Cloudflare).

So the last entry is a proxy of Render, not the visitor: every visitor counts as the same address, and
the limit of `NEW_PLAYER_LIMIT = 60` new players a minute is shared by everybody. One script can use it
up for all, and a single attacker is not braked on their own.

## What

1. **Count the trusted hops from the right.** Behind the proxy the visitor is the entry that Cloudflare
   wrote: the third from the right (`PROXY_HOPS = 2` entries after it are Render's). What a visitor
   writes into `X-Forwarded-For` themselves lands further left, so it never moves that entry.
2. **Shorter chains keep the old rule.** With one or two entries the last entry is taken, as today (a
   chain that did not come the measured way); with none, the address of the connection
   (`request.remote_addr`), as today.
3. **One form per address.** The entry is read with `ipaddress`: the same address written two ways
   counts once; an IPv6 address counts by its /64 network (one connection usually holds a whole /64);
   an entry that is no address falls back to the last entry.
4. **`CF-Connecting-IP` is not used.** It holds the same address, but anybody who reached Render without
   Cloudflare could write it themselves; the count from the right needs no header a visitor controls.
5. Without `CT_PROXY=1` nothing changes: the headers are ignored, as today.

## Decide

1. **Hops from the right, not `CF-Connecting-IP`** (point 3a of `request-limits`: a header a visitor can
   write must not decide). Checked against the measurement: the visitor is the first of three entries,
   which is the third from the right.
2. **`PROXY_HOPS = 2` as a constant in `app.py`**, written next to the measurement. If Render's chain
   ever changes, the proxy-chain line of `request-limits` (still in the log, 5 lines per start) shows it.
3. **The proxy-chain line stays.** Its checks are old tests of `request-limits` now
   (`tests/test_request_limits.py`), and removing them would delete tests; five lines per start cost
   nothing and keep watching the chain.
4. **`NEW_PLAYER_LIMIT` stays 60.** A class on the school's network shares one public address, so the
   limit must stay high enough for a whole room.
5. **No old test changes.** `tests/test_deploy_ready.py::test_behind_a_proxy_the_address_and_https_come_
   from_the_proxy_only_when_trusted` sends one entry and stays true (rule 2). New checks go in the new
   file `tests/test_client_address.py`.
6. **After the AI review (2026-11-23), all four findings fixed:**
   - **Only a chain Render received from Cloudflare is trusted.** The entry `PROXY_HOPS` from the right is
     written by Render: the address it received the request from. The visitor's entry is used only when
     that is in Cloudflare's published ranges (`CLOUDFLARE_NETWORKS`, from
     https://www.cloudflare.com/ips-v4 and /ips-v6, fetched 2026-11-23); otherwise the old, coarse rule.
     A request that reached Render without Cloudflare cannot choose its address, not even by writing a
     Cloudflare address itself (Render adds the sender's real address after it).
   - **First visits from many addresses cannot fill the counters.** Once half of `MAX_KEYS` is in use,
     a first visit from a new address is counted under one shared key (`("new", "many addresses")`), so
     the other half stays for the players' own keys and nobody gets "busy" because of strangers.
   - **A port written with an entry is dropped** (`203.0.113.7:51234`, `[2001:db8::1]:443`).
   - **The measurement line's docstring** says it stays (Decide 3), and a second line, also without an
     address, says what `client_address()` makes of the chain (`client address: entry 2 from the right is
     a Cloudflare address; the visitor is taken from entry 3 from the right`). After the deploy, Render's
     log shows whether the rule takes the visitor; if it says "not a Cloudflare address", the rule simply
     stays on the old behaviour and `PROXY_HOPS` is adjusted in a follow-up.

## Out of scope

The rate limits' numbers, the proxy-chain line, `local_request()` (the editor's check, unchanged), any
other audit item.

## Done when

1. Behind the proxy, `203.0.113.7, 198.51.100.1, 10.0.0.1` counts as `203.0.113.7`; two visitors behind
   the same proxies count separately; one visitor through different edges counts once.
2. Entries a visitor adds on the left (`1.1.1.1, 203.0.113.7, 198.51.100.1, 10.0.0.1`) and a forged
   `CF-Connecting-IP` do not change the address.
3. One or two entries: the last one; none: the connection's address; not trusted: the connection's
   address.
4. IPv6: two addresses of one /64 count once; an entry that is no address falls back to the last entry.
5. End to end: with `NEW_PLAYER_LIMIT = 1` behind the measured chain, a second visitor still gets a
   cookie and the first one's second visit gets 429.
6. The full suite passes; no old test changed.

7. If the deploy shows that entry 2 from the right is no Cloudflare address, nothing breaks: every
   visitor counts as before (the last entry), and the second log line says so.

## Security

The limit of new players now brakes each visitor on their own instead of all visitors together. The rule
reads only entries that Cloudflare and Render write; nothing a visitor sends decides the address. No
address is logged or stored (the count lives in memory, keyed by the address, as before).
