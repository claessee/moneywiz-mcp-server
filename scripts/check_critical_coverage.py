"""Require at least 90% statement coverage in each financial correctness module."""

from pathlib import Path

from coverage import Coverage

coverage = Coverage()
coverage.load()
root = Path(__file__).resolve().parents[1]
modules = [
    "database/connection.py",
    "database/schema.py",
    "models/currency_types.py",
    "services/account_service.py",
    "services/transaction_service.py",
    "services/category_classification_service.py",
    "services/budget_service.py",
    "services/scheduled_transaction_service.py",
    "utils/date_utils.py",
    "main.py",
]
failures = []
for module in modules:
    _, statements, excluded, missing, _ = coverage.analysis2(
        str(root / "src/moneywiz_mcp_server" / module)
    )
    percent = 100 * (len(statements) - len(missing)) / len(statements)
    print(f"{module}: {percent:.2f}%")
    if percent < 90:
        failures.append(module)
if failures:
    raise SystemExit("Critical coverage below 90%: " + ", ".join(failures))
