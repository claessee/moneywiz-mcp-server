# MoneyWiz MCP Server v2.0.0

Version 2.0.0 is the first public release of the hardened MCP v2 line.

This project is based on the MIT-licensed [`jcvalerio/moneywiz-mcp-server`](https://github.com/jcvalerio/moneywiz-mcp-server) and retains the upstream Git history. See [`../ATTRIBUTION.md`](../ATTRIBUTION.md).

## Highlights

- Migrated to the official MCP Python SDK v2.3.0.
- Made MoneyWiz database access permanently read-only at the SQLite boundary.
- Replaced fixed Core Data `Z_ENT` assumptions with dynamic schema/entity discovery.
- Added safe explicit database validation and opt-in discovery for current MoneyWiz/iCloud layouts.
- Reworked monetary calculations around decimal-safe values and explicit currencies.
- Removed implicit cross-currency arithmetic and automatic FX assumptions.
- Added deterministic ISO date/time semantics and explicit result completeness/pagination.
- Made UTC the default timezone while retaining explicit IANA timezone support.
- Fixed category filters for MoneyWiz names containing non-breaking spaces and other Unicode whitespace, preserving stored names in output. The compatibility issue was identified in [HigorLoren's commit](https://github.com/HigorLoren/moneywiz-mcp-server/commit/077d7337d2f011023d81de7517d9024bed753a19); see the [fork delta audit](FORK_DELTA_AUDIT.md).
- Replaced silent schema fallbacks with structured errors.
- Added local real-database reconciliation tooling.
- Expanded regression coverage across SQLite, WAL, schema remapping, write denial, dates, currencies, pagination, and the actual MCP protocol.

## Local validation

Use the validation CLI and MoneyWiz-produced exports to compare transaction counts/types, transfer legs, per-currency cashflow, categories, split transactions, and supported account balance components for your own store. The credit limit is returned separately from opening balance and stored transaction sums.

Financial exports, account data, and validation results must remain private.

## Breaking changes from upstream 1.x

Version 2.0.0 intentionally changes tool/configuration contracts. Writable mode is removed. Money values are structured as decimal strings with explicit currencies. Date handling is explicit rather than natural-language/locale dependent. Pagination and completeness metadata are part of the contract. Subjective analytics/recommendation services were removed from the factual MCP surface.

Users upgrading from upstream 1.x should treat this as a new MCP configuration and re-run reconciliation against their own MoneyWiz store.

## Known limits

MoneyWiz uses a private Core Data SQLite schema, so universal compatibility cannot be guaranteed. Unknown or ambiguous schema conditions are designed to fail explicitly.

Investment market valuation, forex valuation, loan valuation, implicit FX conversion, and other semantics not proven from reproducible evidence remain intentionally non-authoritative.

## Installation

See the repository [`README.md`](../README.md) for installation and MCP client configuration.

## License and trademarks

The project remains MIT licensed. MoneyWiz™ is a registered trademark of SILVERWIZ LLC. This project is independent, unofficial, and is not affiliated with, sponsored by, or endorsed by SILVERWIZ LLC.
