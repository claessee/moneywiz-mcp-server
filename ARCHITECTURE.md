# Architecture

<p align="center">
  <img src="docs/assets/moneywiz-mcp-architecture.jpg" alt="MoneyWiz MCP Server architecture" width="100%">
</p>

MoneyWiz MCP Server is a local stdio MCP service that reads a MoneyWiz Core Data SQLite database without modifying it.

```text
MCP client
   │ stdio
   ▼
MCP server (`main.py`)
   ▼
Factual services
   ▼
Schema resolver (`database/schema.py`)
   ▼
Read-only SQLite manager (`database/connection.py`)
   ▼
MoneyWiz Core Data database
```

The package performs no model calls and exposes no network server.

## Schema resolution

MoneyWiz uses Core Data. Numeric entity identifiers such as `Z_ENT` are implementation details and are not assumed to be stable across compiled model versions.

`database/schema.py` inspects `Z_PRIMARYKEY`, `sqlite_master`, inheritance, required columns, populated entity families, generated relationship tables, and scheduled/category relationship aliases. The resulting mapping is scoped to the active connection/snapshot and discarded when that operation closes.

Production SQL therefore resolves logical entity names dynamically rather than depending on fixed numeric IDs.

Dynamic identifiers discovered from the inspected schema are validated and quoted before use. Data values use bound parameters.

## Read-only database boundary

`database/connection.py` opens SQLite using URI `mode=ro`, enables `query_only`, disables trusted schema behavior, and installs a restrictive authorizer. Write statements, schema changes, attach operations, vacuum operations, mutation pragmas, and other write-capable operations are denied.

There is no writable configuration switch, commit helper, write transaction helper, or raw-SQL MCP tool.

Each service operation reads one consistent SQLite snapshot. WAL content is visible because `immutable=1` is intentionally not used. SQLite may still use normal shared-memory/locking metadata while reading a live WAL database; the application does not modify MoneyWiz financial rows, schema, or WAL records.

## Financial representation

`models/currency_types.py` converts supported stored amounts into decimal-safe representations and serializes amounts as strings with explicit currency codes.

Financial aggregation is performed per currency. The server does not add nominal EUR, SEK, USD, or other values together and performs no implicit FX conversion.

Where a MoneyWiz stored `REAL` has already lost decimal precision, the adapter cannot reconstruct information that SQLite no longer contains. It preserves the deterministic decimal representation of the stored value.

## Services

The service layer remains factual and deterministic:

- accounts and balance components
- transactions and transaction-type classification
- categories and parent hierarchy
- tags and payees
- budgets using verified stored fields
- scheduled transaction definitions
- remaining due bills and transfers with explicitly bounded recurrence projections
- per-currency cashflow summaries

The 2.x line intentionally removed subjective financial-health scores, savings recommendations, vague importance rankings, and guessed recurrence forecasts. The due-bill service supports only verified simple monthly/yearly rules and reports incomplete commitments whenever it encounters unsupported rules. Stored due dates and projections remain distinct; no payment history or bank settlement is inferred.

## Error model

Integrity-critical schema ambiguity is not converted into empty data, zero balances, or `Unknown` placeholders. Service failures return structured errors. MCP input-schema failures use normal MCP error status.

This is deliberate: for personal financial data, a visible unsupported condition is safer than a plausible but incomplete answer.

## Dates and pagination

Intervals use `[start, end)` semantics. Date-only input resolves in an explicit IANA timezone; datetimes require an explicit offset or `Z`.

Potentially large list results use stable ordering and bounded pagination with explicit matched/returned counts and truncation metadata. Aggregates that promise complete totals stream all matching rows rather than summing only a paginated page.

## Reconciliation CLI

`validate.py` provides a local, read-only reconciliation harness. It reports schema capability, account control data, transaction counts, per-currency totals, and relevant warnings without dumping individual transaction descriptions by default.

Synthetic tests validate implementation behavior. Independent MoneyWiz-produced exports remain the strongest acceptance check for newly observed MoneyWiz schema semantics. See [`docs/RECONCILIATION.md`](docs/RECONCILIATION.md).

## Trust boundary

The server itself keeps the data path local and uses stdio. Once a connected MCP client requests a tool result, that client controls whether the returned data is sent to an external model provider. Client/provider privacy behavior is therefore outside this server's process boundary.
