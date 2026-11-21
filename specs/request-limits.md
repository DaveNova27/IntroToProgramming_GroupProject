# Small requests only, and who the visitor is (`request-limits`)

Asked for by Christopher on 2026-11-21, items B2 and B3 of the audit of 2026-11-21. Builds on
`deploy-ready` (public mode, rate limits, `CT_PROXY`) and `player-cap`.

## Why

1. **B2: a request may be of any size.** Flask reads the whole body of a request into memory
   (`request.get_json()`), and neither Flask (`MAX_CONTENT_LENGTH` is not set) nor gunicorn limits
   it. The public server has 512 MB. A few very large requests can make it run out of memory; Render
   then restarts it and every player who is playing gets errors. No real request of the game is
   larger than a few KB.
2. **B3: which address the server sees behind Cloudflare is not known.** With `CT_PROXY=1`,
   `client_address()` takes the last entry of `X-Forwarded-For`, "the address our proxy saw". Live,
   Cloudflare stands in front of Render (`server: cloudflare`, `cf-ray`). If the last entry is an
   address of Cloudflare or of Render instead of the visitor, the limit of `NEW_PLAYER_LIMIT = 60` new
   players per address and minute is shared by many visitors. Render's and Cloudflare's documentation
   do not say for sure which headers reach our app on Render, so we measure it before we change it.

## What

1. **At most 64 KB per request.** `app.config["MAX_CONTENT_LENGTH"] = MAX_REQUEST_BYTES = 64 * 1024`,
   in local and in public mode. A larger body is refused with 413 before the rule runs; on `/api/` the
   answer is JSON like every other API error (`unexpected_error`): "The request is too large." Nothing
   is saved.
2. **One log line about the proxy chain (measuring B3).** In public mode with `CT_PROXY=1`, the first
   page request (`/` or `/map`) after a start writes one WARNING line, once per process, with:
   the number of entries in `X-Forwarded-For`, whether `CF-Connecting-IP`, `True-Client-IP` and
   `Forwarded` are present, and which entry of `X-Forwarded-For` (first, last, another, none) equals
   `CF-Connecting-IP`. Never an address. Example:
   `proxy chain: X-Forwarded-For has 2 entries; CF-Connecting-IP present (the first entry); True-Client-IP absent; Forwarded absent`
3. **`client_address()` does not change yet.** After the deploy, Felix (owner of the Render account,
   `specs/deploy.md`) reads the line in Render's log. The change of the address, if one is needed, is a
   small follow-up spec, and then the log line goes again.

## Decide

1. **64 KB.** The largest real requests are a few hundred bytes (an order of several products, an
   editor patch); the longest inputs in the tests are 10,000 characters. 64 KB leaves room for every
   one of them and stops a body of megabytes. In local mode too: one rule, nothing to switch.
2. **Measure, do not guess.** Changing `client_address()` to `CF-Connecting-IP` without knowing whether
   every request passes Cloudflare would let anybody who reaches Render directly write their own
   address into that header. The last `X-Forwarded-For` entry cannot be forged (that is good), it may
   just be too coarse. So first one line in the log, then the decision.
3. **Once per process, no address.** Render's log must not hold visitors' addresses (`deploy.md`), and
   one line is enough to see the chain. The health check (`/healthz`) does not count: it may come from
   Render itself, not through Cloudflare.
4. **Long inputs in error messages stay.** Messages like "Unknown product '…'" repeat what was sent;
   with the 64 KB cap that is at most 64 KB back, sent as text (`textContent`), never as HTML. Cutting
   them is not needed for safety.
5. **No old test changes.** New checks go in the new file `tests/test_request_limits.py`.

## Out of scope

- Changing `client_address()` or `NEW_PLAYER_LIMIT` (the follow-up, after the measurement).
- A smaller tick answer (audit B5), the Café takeover (audit B1), anything else in the audit.
- Limits in gunicorn or in Render (the app's limit is enough and is tested here).

## Done when

1. A body larger than 64 KB on an API endpoint gets 413 and a JSON error, and the saved run is
   unchanged (local mode and public mode).
2. A body just under the limit is read as before (a rule answers, here with its normal refusal).
3. A real request of the game (an order) still works.
4. Public mode with `CT_PROXY=1`: the first page request writes exactly one WARNING line about the
   chain; a second page request writes none; the line holds no address that was sent.
5. The line says which entry equals `CF-Connecting-IP` (first, last, none) and counts the entries.
6. Without `CT_PROXY=1`, or on `/healthz`, no such line.
7. The full suite passes; no old test changed.

## Security

This removes a cheap way to make the public server run out of memory. It adds no input and no
endpoint. The new log line holds header names and counts, never an address or a player id.
