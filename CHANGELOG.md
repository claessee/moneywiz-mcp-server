# Changelog

## 2.0.0 — 2026-10-03

First public release of the hardened 2.x line, based on upstream `jcvalerio/moneywiz-mcp-server` at commit `d113a11df8ea475f50b5d118585c763bb4f5ba72`.

### Added

- Official MCP Python SDK v2.3.0 integration and local stdio server.
- Central dynamic Core Data schema/entity resolver using `Z_PRIMARYKEY` and inspected relationship tables.
- Permanent read-only SQLite enforcement with `mode=ro`, `query_only=ON`, `trusted_schema=OFF`, and a restrictive authorizer.
- Exact database validation and safe opt-in MoneyWiz discovery.
- Decimal-safe monetary models with explicit currencies and per-currency aggregation.
- Deterministic ISO date/time intervals with explicit timezone semantics.
- Pagination, truncation, and completeness metadata for bounded result sets.
- Structured service/schema error envelopes.
- Local reconciliation CLI.
- Real MCP protocol tests and regression coverage for schema remapping, WAL behavior, write denial, currency handling, dates, pagination, and malformed schemas.

### Fixed

- Hard-coded Core Data entity IDs that could omit or misclassify real MoneyWiz records.
- `transaction_type` being exposed but not applied to transaction queries.
- iCloud database discovery gaps and unsafe consideration of SQLite sidecar/shared stores.
- Silent classification and relationship fallbacks that could make incomplete results appear valid.
- Cross-currency nominal arithmetic and floating-point aggregation.
- Incomplete scheduled income handling and ignored scheduled filtering semantics.
- Budget filtering/default assumptions that could hide valid stored definitions.
- Locale/naive/fallback date handling and unstable completeness semantics.
- Category-name filtering for stored non-breaking spaces and Unicode whitespace, without changing displayed names or case-sensitive matching.

### Changed

- Subjective financial-health, savings-recommendation, trend, and forecast-style services were removed from the MCP surface in favor of factual retrieval and deterministic aggregation.
- Investment, forex, and loan valuation remain explicitly non-authoritative where MoneyWiz semantics are not proven.
- Credit-card balance handling exposes opening balance, stored transaction sums, and credit limit as separate factual components for local validation.
- UTC is the default timezone for MCP date filters and the validation CLI; callers may supply an explicit IANA timezone.
- Release artifacts are published to GitHub only; the inherited upstream PyPI publishing workflow was removed.

### Validation

Synthetic tests cover transaction counts/types, transfers, per-currency cashflow, categories, reversals, split-transaction detection, and supported account balance components. Independent MoneyWiz-produced exports should be used for local acceptance checks; financial data and validation results must remain private.

See [`docs/RECONCILIATION.md`](docs/RECONCILIATION.md) and [`docs/IMPLEMENTATION_REPORT.md`](docs/IMPLEMENTATION_REPORT.md).

### Attribution

The project retains the upstream Git history and MIT license. See [`ATTRIBUTION.md`](ATTRIBUTION.md).
