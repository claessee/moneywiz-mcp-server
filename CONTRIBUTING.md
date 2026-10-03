# Contributing

Contributions are welcome when they preserve the project's core guarantees: permanent read-only behavior, explicit currencies, deterministic schema handling, and transparent completeness/error semantics.

## Development setup

```sh
git clone https://github.com/claessee/moneywiz-mcp-server.git
cd moneywiz-mcp-server
uv sync --frozen --all-extras
```

Run the full project checks before opening a pull request:

```sh
uv run --frozen pytest
uv run --frozen python scripts/check_critical_coverage.py
uv run --frozen ruff check .
uv run --frozen ruff format --check .
uv run --frozen mypy src/
uv run --frozen bandit -r src/
uv run --frozen pip-audit --local --skip-editable
uv build --no-sources
uv run --frozen twine check dist/*
```

## Financial-data rules

Use fabricated SQLite fixtures only. Never commit a real MoneyWiz database, WAL/SHM files, reconciliation output, account names, balances, transaction descriptions, credentials, or other private financial data.

Financial calculations must use explicit currencies and decimal-safe arithmetic. Do not add implicit FX conversion or combine nominal amounts from different currencies.

## MoneyWiz schema changes

MoneyWiz uses a private Core Data SQLite schema. New compatibility work must be evidence-driven.

Do not add hard-coded Core Data entity IDs. Resolve entities through the central schema layer. New entity/relationship assumptions should include tests with more than one numeric entity map and explicit malformed/unsupported-schema cases.

Do not turn an unresolved schema condition into an empty result, zero balance, `Unknown` placeholder, or other apparently valid output.

## Read-only guarantee

Do not add writable helpers, write-capable configuration, raw-SQL tools, database migration code, or financial-data telemetry. Changes to the database/SQLite boundary require focused regression tests proving representative writes remain blocked.

## Pull requests

Keep changes focused. Explain the behavior being changed, the evidence supporting any MoneyWiz schema assumption, and the exact validation performed. Add regression tests for financial logic, schema handling, date boundaries, pagination/completeness, and errors where relevant.

If compatibility cannot be demonstrated from synthetic/reproducible evidence, document the limitation rather than guessing.