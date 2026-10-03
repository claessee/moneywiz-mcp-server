# MoneyWiz reconciliation

The 2.x implementation has been independently reconciled against a real MoneyWiz macOS/iCloud database and MoneyWiz-produced exports for supported functionality.

This does **not** prove compatibility with every MoneyWiz release or every possible account type. MoneyWiz uses a private Core Data SQLite schema, so new schema variants must still be validated. The project's rule is to fail explicitly on unsupported or ambiguous schema conditions rather than return plausible but incomplete data.

## What was independently confirmed

For a complete September 2026 interval, an independent MoneyWiz transaction export matched the MCP exactly for:

- total transaction count
- deposits and withdrawals
- transfer-in and transfer-out legs
- transfer pairing and values
- EUR expense totals
- SEK expense totals
- SEK income
- transaction currencies
- transaction type classification
- interval boundaries
- category extraction
- reversal signs
- split-transaction detection

A separate MoneyWiz balance report was then compared with the MCP's account-control output. Every active account supported by the MCP's balance calculation matched MoneyWiz to currency precision. Investment accounts remained intentionally unsupported rather than exposing an invented market valuation.

For the validated active credit-card accounts, MoneyWiz's displayed balance matched:

```text
opening balance + stored transaction sum
```

The credit limit was not part of the displayed balance. This resolved the practical credit-card balance uncertainty for the validated database.

No real account names, balances, transaction descriptions, transaction IDs, exported CSVs, or database files are included in this repository.

## Run your own reconciliation

Use the validation CLI against your own primary MoneyWiz store:

```sh
.venv/bin/python -m moneywiz_mcp_server.validate \
  --db "$HOME/Library/Containers/com.moneywiz.personalfinance/Data/Library/Application Support/MoneyWiz_iCloud.sqlite" \
  --start 2026-09-01 --end 2026-10-01 --timezone Europe/Lisbon
```

The iCloud path above is a common current location. Verify the actual primary database on your Mac. Do not select `_shared.sqlite`, `-wal`, `-shm`, or `-journal` files as the primary database.

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