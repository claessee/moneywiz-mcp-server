# Local MoneyWiz reconciliation

Classification is **READY FOR READ-ONLY RECONCILIATION** until independent UI
comparisons are completed. No real store has been read in this implementation.

The current session's environment is already installed. From macOS:

```sh
cd /Users/macmini2/Scripts/Codex-files/moneywiz-mcp-server
.venv/bin/python -m moneywiz_mcp_server.validate \
  --db "$HOME/Library/Containers/com.moneywiz.personalfinance/Data/Library/Application Support/MoneyWiz_iCloud.sqlite" \
  --start 2026-09-01 --end 2026-10-01 --timezone Europe/Lisbon
```

That is the reported iCloud candidate, not a verified path on this Mac. Replace
`--db` with the exact installation's primary store or a known consistent copy.
Prefer a MoneyWiz-produced SQLite backup, or quit MoneyWiz and obtain a consistent
store snapshot using your established backup procedure. Do not copy only the main
file while a live WAL exists. Do not select `_shared.sqlite`, -wal or -shm files.
The harness never creates backups or changes your database.

For a second deterministic period covering the 2026 Lisbon spring DST transition:

```sh
.venv/bin/python -m moneywiz_mcp_server.validate \
  --db "/absolute/path/to/your/consistent/MoneyWiz.sqlite" \
  --start 2026-03-01 --end 2026-04-01 --timezone Europe/Lisbon
```

The complete JSON report remains on your terminal. Optional local capture:

```sh
umask 077
.venv/bin/python -m moneywiz_mcp_server.validate \
  --db "/absolute/path/to/your/consistent/MoneyWiz.sqlite" \
  --start 2026-09-01 --end 2026-10-01 --timezone Europe/Lisbon \
  > reconciliation-2026-09.json
```

Inspect the exit code and `errors`. Exit 0 means the adapter's checks completed,
not that the UI agrees. Exit 1 is a fundamental validation failure; exit 2 preserves
successful sections alongside explicit unsupported-schema/data errors. No individual
transaction descriptions, notes or payees are dumped. Counts and components can
still be private; keep the report local and never add it to Git.

Compare with MoneyWiz using the same store snapshot and exact local interval:

1. Account count, names/types/currencies, archived-account inclusion and balances.
2. Per-account transaction counts; income/expense totals separately per currency.
   Income/expense definitions here are the signed deposit/withdraw entity sums;
   UI reports may treat refunds/reconciliations differently. Compare the separately
   labelled stored type sums to explain these differences, not an invented total.
3. Transfer **leg counts**; do not confuse these with transfer pair counts.
4. Category/tag counts and selected hierarchy/tag relationships via the paginated
   factual tools. Confirm leaf names with their IDs/parent hierarchy.
5. Stored scheduled salary, expense and transfer records, including disabled and
   one-off handlers; stored recurrence fields without forecast assumptions.
6. Budget count, zero/negative definitions, linked categories/accounts and stored
   amount/currency fields. Budget spending/rollover/limit interpretation remains a
   separate documented uncertainty, not an inferred answer.
7. Any schema/errors/truncation warnings. All relevant sections must be compared;
   do not label partial results as complete.

For a credit card, compare the UI's balance meaning (debt/outstanding/available
credit), opening balance, credit limit and stored transaction sums by type. The
report includes candidates `opening_plus_transactions` and
`opening_plus_transactions_plus_limit`. Competing explanations from #48 are a
net-of-limit opening value, a conditional nonzero-opening offset, or a different
UI balance definition. Test cards with and without nonzero opening balances;
check transfers/payments/signs and relevant statements. Do not change a formula
based on one account. Record unresolved differences explicitly.

Only after independent balances, counts, classifications and per-currency sums
have been compared, discrepancies resolved or explicitly documented, can this
checkout's deployment be labelled **RECONCILED**. The harness intentionally never
assigns that label itself. Repeat these comparisons after upgrades.
