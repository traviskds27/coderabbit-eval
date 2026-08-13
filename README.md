# orderly

A small order-management service used to exercise AI code review tooling.

## Conventions

These are project rules, not suggestions:

1. **Money is always `Decimal`.** Never `float`. Amounts are stored as integer
   cents in the database and converted at the boundary.
2. **All SQL is parameterised.** No f-strings or `%`-formatting in queries.
3. **Every endpoint that touches an order must authorise the caller** via
   `require_order_access`.
4. **Exceptions are never silently swallowed.** Log with context and re-raise,
   or handle a specific exception type.

## Layout

    db.py            thin sqlite wrapper
    orders.py        order queries and state transitions
    api.py           HTTP layer
    test_orders.py   unit tests
