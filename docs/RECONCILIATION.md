# MoneyWiz reconciliation

Use the local validation CLI with independent MoneyWiz-produced exports to check the adapter against your own store. Keep the database, financial exports, and validation results private.

MoneyWiz uses a private Core Data SQLite schema, so new schema variants must be validated. The project's rule is to fail explicitly on unsupported or ambiguous schema conditions rather than return plausible but incomplete data. Synthetic regression tests do not prove compatibility with every MoneyWiz release or account type.

## Run your own reconciliation

Use the validation CLI against your own primary MoneyWiz store:

```sh
.venv/bin/python -m moneywiz_mcp_server.validate \
  --db "$HOME/Library/Containers/com.moneywiz.personalfinance/Data/Library/Application Support/MoneyWiz_iCloud.sqlite" \
  --start 2025-01-01 --end 2025-02-01
```

The dates above are illustrative; choose the interval covered by your export. Date-only inputs default to UTC; pass `--timezone` with an explicit IANA zone if needed. The iCloud path above is a common current location. Verify the actual primary database on your Mac. Do not select `_shared.sqlite`, `-wal`, `-shm`, or `-journal` files as the primary database.

The harness is read-only and does not create backups or change the database. If you validate a live WAL-mode database, keep the main database and its WAL/SHM state consistent. A MoneyWiz-produced backup or a consistent local snapshot is preferable for repeatable multi-page comparisons.

## What to compare

Use MoneyWiz itself as the independent reference for the same database state and interval. Compare account metadata and supported balances, transaction counts and types, per-currency income/expense totals, transfer legs/pairs, category hierarchy, tags, budgets, and scheduled transactions relevant to your data.

A zero validator exit code means the adapter checks completed successfully. It does not automatically prove that your specific MoneyWiz schema and UI semantics have been independently reconciled.

## Privacy

The default validation report avoids individual transaction descriptions, notes, and payees, but account/control totals are still private financial information. Keep validation output local and do not attach a real database or reconciliation report to a public GitHub issue.

## When to repeat reconciliation

Repeat a focused independent comparison after any change to:

- MoneyWiz's database schema or major app version
- schema/entity discovery
- transaction classification
- monetary calculations
- date/time semantics
- account balance logic
- MCP tool contracts

Synthetic tests protect known behavior; independent MoneyWiz comparison remains the final acceptance check for newly observed schema semantics.