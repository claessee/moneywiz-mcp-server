# Implementation and validation report

Date: 2026-10-03  
Release line: **2.0.0**  
Status: **IMPLEMENTED with synthetic regression coverage and local validation tooling**

## Provenance

This 2.x implementation is based on [`jcvalerio/moneywiz-mcp-server`](https://github.com/jcvalerio/moneywiz-mcp-server) at upstream commit `d113a11df8ea475f50b5d118585c763bb4f5ba72`.

The original MIT license and Git history are retained. See [`../ATTRIBUTION.md`](../ATTRIBUTION.md).

## Main implementation changes

The hardened line preserves the useful Python/service structure while replacing assumptions that could silently produce incomplete or mathematically invalid financial output.

Major changes include:

- migration to the official MCP Python SDK v2.3.0
- permanent SQLite read-only enforcement
- central dynamic Core Data entity and relationship discovery
- deterministic database validation and safe discovery
- decimal-safe monetary handling
- explicit per-currency aggregation with no implicit FX conversion
- deterministic ISO date/time interval semantics
- explicit pagination and completeness metadata
- structured schema/service errors instead of silent fallbacks
- removal of subjective recommendation/forecast services from the factual MCP surface
- local reconciliation tooling
- expanded real SQLite and MCP protocol regression testing

## Read-only design

SQLite is opened using URI `mode=ro` with `query_only=ON`, `trusted_schema=OFF`, and a restrictive authorizer. There is no writable configuration, raw-SQL MCP tool, commit helper, or database migration path.

SQLite may use normal locking/shared-memory metadata while reading a live WAL-backed store. The implementation does not modify MoneyWiz financial rows, schema, or WAL records.

## Schema handling

Core Data numeric `Z_ENT` values are not treated as stable API identifiers. The central schema layer inspects `Z_PRIMARYKEY`, validates required entity families and columns, and discovers generated relationship structures from the actual database schema.

Unrecognized populated descendants, ambiguous mappings, missing integrity-critical relationships, and invalid references produce explicit errors rather than empty or apparently valid fallback results.

## Financial semantics

Monetary arithmetic uses decimal-safe representations and every returned amount carries an explicit currency. Different currencies are never combined without an explicit conversion operation; the 2.x server performs no automatic FX conversion.

Cashflow aggregates operate per currency. Transfers, refunds, reconciliations, and investment transactions retain their factual transaction classifications rather than being silently folded into income/expense totals.

## Automated validation

Before publication, the hardened implementation reported:

- 171 passing tests
- 94.17% overall statement coverage
- all designated critical modules above 90% coverage
- Ruff lint and format checks passing
- strict mypy passing
- Bandit passing with reviewed local SQL-assembly annotations only
- installed-package dependency audit with no known vulnerabilities at the time of testing
- locked dependency validation
- wheel and source distribution build/checks passing
- installed-wheel MCP/CLI smoke tests passing across the complete 11-tool surface

Tests use fabricated financial data. No personal MoneyWiz database or real financial export is included in the repository.

## Independent local validation

Validate the adapter against independent MoneyWiz-produced transaction and balance exports for each supported store. Compare counts, entity classifications, signs, currencies, interval boundaries, category hierarchy, split transactions, transfer legs, and account balance components.

Calculated balances use opening balance plus stored transaction amounts. Credit limits are returned separately. Investment, forex, and loan valuation remains unsupported without independently proven semantics. Synthetic tests cannot establish universal compatibility with the private MoneyWiz schema.

See [`RECONCILIATION.md`](RECONCILIATION.md).

## Remaining compatibility limits

MoneyWiz's Core Data SQLite schema is a private implementation detail. A successful local validation cannot prove universal compatibility with every MoneyWiz version or every possible account configuration.

Investment market valuation, forex valuation, loan valuation, and any other semantics not demonstrated from reproducible evidence remain intentionally non-authoritative.

The project should prefer an explicit unsupported/schema error over a plausible-looking value that has not been proven.

## Privacy

No real account names, balances, transaction descriptions, transaction IDs, exported financial CSVs, database copies, credentials, or private local paths are included in this public report.