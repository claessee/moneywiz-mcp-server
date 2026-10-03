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
- Replaced silent schema fallbacks with structured errors.
- Added local real-database reconciliation tooling.
- Expanded regression coverage across SQLite, WAL, schema remapping, write denial, dates, currencies, pagination, and the actual MCP protocol.

## Real MoneyWiz validation

The 2.x implementation was independently compared with MoneyWiz-produced exports from a real macOS/iCloud MoneyWiz database.

Supported transaction counts/types, transfer legs/pairs, per-currency cashflow, category extraction, split-transaction detection, and current supported account balances reconciled with MoneyWiz. For the validated active credit cards, MoneyWiz displayed balances matched opening balance plus stored transaction sum without adding the credit limit.

Private financial exports and account data are not included in this repository.

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