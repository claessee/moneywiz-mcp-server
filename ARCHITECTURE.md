# Architecture of the reconciliation fork

Local MCP client → `main.py` (official MCPServer, stdio) → factual services →
`DatabaseManager` (async SQLite, consistent read snapshot) → user's primary store.
No network server or model calls are part of this package.

The existing Python package, async manager, service separation, Pydantic responses,
CLI entry point and author attribution are preserved. Unsafe conversion/query
internals and mixed subjective analytics were replaced rather than wrapped in
compatibility fallbacks. Source history remains in Git at the starting SHA.

`database/schema.py` reads Z_PRIMARYKEY and sqlite_master once per snapshot,
validates IDs/names/inheritance/stored object keys, resolves account/transaction
families, discovers generated tag joins and scheduled category aliases, and
provides diagnostics. Fixed IDs never occur in production query logic. Unknown
populated descendants fail. Optional entity absence is visible. All interpolated
identifiers are validated against the inspected schema and double-quoted with
escaped quote characters. Data values are always bound parameters.

`database/connection.py` only accepts SELECT from service code. URI mode=ro,
query_only and a deny-by-default SQLite authorizer independently reject writes,
DDL, attach, vacuum, mutation pragmas and extension/file-writing functions.
There is no optional third-party API or write context manager. Every operation
opens BEGIN for a consistent read snapshot and closes without a commit.
WAL is respected. Cache lifetime is that operation; no stale global entity cache.

`models/currency_types.py` normalizes finite amounts to Decimal and serializes
strings with currency. Exact addition sizes its precision from operands. No
monetary calculation uses float or SQL SUM. Grouping keys include currency and
category ID. Date floats are confined to NSDate timestamp conversion.

`services/category_classification_service.py` follows factual references and
parent hierarchies. Missing rows/names/cycles/conflicting field observations fail;
no Unknown placeholders or financial importance heuristics exist.
Account/budget/scheduled/transaction services retain their original responsibilities.
Budgets and recurrence expose observed fields when derived semantics are uncertain.
Account balances expose explicit provisional components and credit-limit candidates.
Transaction counts and pages use one snapshot; aggregation streams all matches.

`main.py` validates constrained MCP inputs, carries read-only metadata and returns
structured success/error envelopes. A standard Python decorated signature preserves
typed output schemas after adding the error envelope. The SDK's documented tracing
opt-out is pinned to 2.3.0 and covered by tests. `validate.py` is an offline diagnostic
CLI with section errors and nonzero status for incomplete checks; it cannot certify
independent UI reconciliation.

Tests use actual SQLite stores with fabricated data and remapped entities, including
WAL concurrency and actual MCP client/server transports. The original mock-heavy
API tests and subjective models were retired; the metadata regression remains.
CI and the local script enforce format/lint/strict types/full security/tests/build.
