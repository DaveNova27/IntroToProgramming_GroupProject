# Reject non-finite prices

## What

Price input such as `Infinity`, `-Infinity`, `NaN` and `sNaN` must be refused
with a readable message and HTTP 400, rather than an uncaught server error.
Cash, stock, prices, day and history must remain unchanged in the saved run.
Valid euro amounts and the existing two-decimal rule keep their behavior.
Decimal conversion or quantization failures are also rejected actions.

## Out of scope

Graphics, catalogue, demand, storage schema and other game rules.

## Done when

1. Non-finite inputs are rejected by both the converter and price API.
2. A saved run is identical before and after each rejected request.
3. Ordinary prices and all existing tests pass.

Verification: `uv run pytest tests checks/test_finite_prices.py`.
Regression checks live in `checks/` to preserve the existing `tests/` directory.
