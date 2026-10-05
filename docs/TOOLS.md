# MCP tool reference

MoneyWiz MCP Server 2.x exposes twelve read-only tools. Tool annotations describe read-only/non-destructive intent, while the SQLite boundary independently enforces it.

Successful service responses use a structured data/error envelope. MCP input-schema failures use normal MCP error status.

## `server_status`

Checks that the configured database can be opened read-only, validated as SQLite, and interpreted as a supported MoneyWiz schema. It is intended as the first connectivity check.

## `schema_info`

Returns the observed Core Data entity map, relevant table/column information, optional capability availability, and schema warnings. Entity IDs are diagnostics, not public stable identifiers.

## `list_accounts`

Lists MoneyWiz accounts with type, currency, archived state, and factual balance components. Supported balance calculations remain explicit about their components and limitations.

## `get_account`

Returns one account using an ID returned by the server or an exact stored identifier. Ambiguous identifiers fail rather than selecting an arbitrary match.

## `search_transactions`

Searches transactions using an explicit interval and optional account, category, and transaction-type filters. Supported transaction types include factual MoneyWiz transaction families such as deposit, withdrawal, transfer legs, investment operations, refunds, reconciliations, and budget transfers where present in the inspected schema.

Results use deterministic ordering and bounded pagination.

## `list_categories`

Lists category IDs, names, parent references, and resolved parent hierarchy. Category identity is preserved by ID so duplicate leaf names are not merged accidentally.

## `list_tags`

Lists stored tag IDs and names. A valid zero-count result is distinct from a missing/unsupported tag schema.

## `list_payees`

Lists factual stored payee IDs and names.

## `list_budgets`

Lists verified stored budget fields and explicit currency data. The server does not invent rollover, spending, or risk semantics that have not been demonstrated from the MoneyWiz schema.

## `list_scheduled_transactions`

Lists stored scheduled transaction definitions, including supported income, expense, and transfer handlers. Disabled and one-off records remain factual stored definitions. The server does not forecast future executions from guessed recurrence semantics.

## `list_due_bills`

Finds remaining scheduled expenses and transfers over an explicit `[start, end)` interval, with an optional account filter and earlier overdue stored payments. Income and disabled schedules are excluded. Results identify the account, local due date/time, signed stored amount, stored/projected basis, and schedule state. Overdue means the stored date precedes `as_of`, not proof of an unpaid bank invoice.

Totals separate period bills, period transfers, and overdue payments before the period, by currency. They cover every known occurrence before pagination. `projection_complete` and `totals_complete` are false when a relevant rule or handler family is unsupported. Both payments and unresolved schedules expose independent page metadata using the requested limit/offset; follow each `next_offset`.

Verified simple monthly/yearly recurrences may be projected. Other rules remain explicit limitations. Paid/skipped history is not reconstructed. See [`DUE_BILLS.md`](DUE_BILLS.md) for parameters, examples and evidence.

## `summarize_cashflow`

Produces complete deterministic cashflow aggregates for the requested interval, grouped by currency. Income and expenses remain currency-specific. Transfers and other transaction families are reported separately rather than counted as income.

The expense-category breakdown is independently bounded and exposes its own completeness metadata. Split expenses remain in complete currency totals even when category allocation cannot be represented authoritatively.

## Common semantics

### Money

Amounts are serialized as decimal strings with explicit currencies. The server performs no implicit FX conversion and never adds nominal amounts from different currencies together.

### Dates

Intervals are `[start, end)`. Date-only input resolves at midnight in the requested IANA timezone. Datetimes require an explicit offset or `Z`.

### Pagination

Bounded list tools expose matched/returned counts, limit, offset, truncation state, and a next offset where applicable. A partial page is never presented as a complete dataset.

### Errors

Unknown populated entity descendants, missing integrity-critical relationships, ambiguous mappings, invalid references, unsupported requested transaction families, and other correctness-critical schema conditions fail explicitly.

For architecture and validation details, see [`../ARCHITECTURE.md`](../ARCHITECTURE.md) and [`RECONCILIATION.md`](RECONCILIATION.md).
