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

### Changed

- Subjective financial-health, savings-recommendation, trend, and forecast-style services were removed from the MCP surface in favor of factual retrieval and deterministic aggregation.
- Investment, forex, and loan valuation remain explicitly non-authoritative where MoneyWiz semantics are not proven.
- Credit-card balance handling exposes factual components. Independent reconciliation against a real MoneyWiz database confirmed that the validated active credit-card displayed balances match opening balance plus stored transactions, without adding the credit limit.

### Validation

Independent MoneyWiz exports were reconciled against the 2.x implementation for a complete real-data interval. Transaction counts/types, transfers, per-currency cashflow, categories, reversals, split-transaction detection, and supported current account balances matched. Real financial data used for reconciliation is not included in the repository.

See [`docs/RECONCILIATION.md`](docs/RECONCILIATION.md) and [`docs/IMPLEMENTATION_REPORT.md`](docs/IMPLEMENTATION_REPORT.md).

### Attribution

The project retains the upstream Git history and MIT license. See [`ATTRIBUTION.md`](ATTRIBUTION.md).