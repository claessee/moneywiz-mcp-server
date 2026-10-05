# MoneyWiz MCP Server v2.1.0

Version 2.1.0 adds a backwards-compatible tool for remaining scheduled bills due within a week, month, or other explicit period. Existing account, balance, transaction and schedule tools retain their contracts.

## Highlights

- New `list_due_bills` tool with explicit dates, IANA timezone, optional account filter, and overdue schedule state.
- Separate bill and transfer totals per currency, calculated before pagination; income and disabled schedules are excluded.
- Stored next dates and projected occurrences are labelled separately.
- Conservative monthly/yearly projections for verified simple rules, with incomplete forecast and total flags for unsupported cases.
- Bounded payment and unresolved-schedule pages with stable ordering and completeness metadata.
- Additional observed weekend/anchor fields in stored schedule metadata.
- Synthetic regression coverage for dates, DST, recurrence limits, exact amounts, filtering, pagination, read-only access, and the MCP protocol.

## Upgrade

Update the source and run `uv sync --frozen --all-extras`, then restart or reconnect the MCP client. Codex users with an `enabled_tools` allowlist must add `"list_due_bills"`. Database configuration and existing tools remain compatible.

## Known limits

The tool reports remaining schedules, not paid/skipped historical bills or bank settlement. Projections use stored amounts and require the scheduling timezone. Daily/weekly or unknown units, weekend shifts, finite endings, month-end/leap-day behavior, changed anchors, and ambiguous DST times remain unsupported. Relevant unsupported cases explicitly mark forecasts and totals incomplete while retaining known stored dates.

Balance calculations and their provisional status are unchanged. See [due-bill semantics and evidence](DUE_BILLS.md).

## Validation

The local regression suite passes 222 synthetic tests. Live MCP calls verified week/month periods, account filtering and balance retrieval, including expected unsupported-rule reporting. Private account data and reconciliation output are excluded from the repository and release artifacts.

## Attribution

This maintained derivative retains the upstream MIT license and Git history. See [ATTRIBUTION.md](../ATTRIBUTION.md). MoneyWiz is a SILVERWIZ trademark; this project remains independent and unofficial.
