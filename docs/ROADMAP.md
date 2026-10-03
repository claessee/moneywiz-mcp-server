# Roadmap

The 2.x baseline is implemented and independently reconciled for the currently supported MoneyWiz functionality. Future work should extend compatibility only from reproducible evidence.

## Priorities

- Track MoneyWiz schema changes and add new variants through the central schema resolver with regression tests.
- Improve split-category allocation only when the underlying stored semantics are proven.
- Expand factual budget and scheduled-transaction semantics where MoneyWiz behavior can be independently demonstrated.
- Add further real-world reconciliation coverage across additional MoneyWiz installations and schema generations without collecting or publishing private financial data.
- Keep MCP SDK and dependencies current through deliberate pinned upgrades and full regression/reconciliation checks.
- Improve installation diagnostics and documentation while preserving explicit database selection and permanent read-only guarantees.

## Deliberately out of scope unless redesigned explicitly

- writable MoneyWiz operations
- raw SQL tools
- implicit FX conversion
- speculative investment/forex/loan valuation
- subjective financial-advice scoring in the server
- recurrence forecasting based on guessed calendar semantics
- remote/tunneled database access by default

The project should prefer explicit unsupported states over guessed compatibility.