"""Local reconciliation harness; no transaction dumps, networking or writes."""

import argparse
import asyncio
import json
from pathlib import Path
import sys
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

from pydantic import TypeAdapter

from .config import validate_path
from .database.connection import DatabaseManager
from .database.schema import SCHEDULED_TYPES
from .errors import MoneyWizError
from .services.account_service import AccountService, placeholders
from .services.budget_service import BudgetService
from .services.category_classification_service import (
    CategoryClassificationService,
    required_name,
)
from .services.scheduled_transaction_service import ScheduledTransactionService
from .services.transaction_service import TransactionService
from .utils.date_utils import interval


def private_path(path: Path) -> str:
    try:
        return "~/" + str(path.relative_to(Path.home()))
    except ValueError:
        return "<outside-home>/" + path.name


async def validate_classifications(db: DatabaseManager, entity: str) -> int:
    service = CategoryClassificationService(db)
    records = await service.rows(entity)
    for key, row in records.items():
        if entity == "Category":
            await service.category(key)
        else:
            required_name(row, ("ZNAME6", "ZNAME2", "ZNAME"))
    return len(records)


async def reconcile(
    db_path: str, start: str, end: str, zone: str = "UTC"
) -> dict[str, Any]:
    period = interval(start, end, zone)
    path = validate_path(db_path)
    db = DatabaseManager(str(path))
    report: dict[str, Any] = {
        "readiness": "READY FOR READ-ONLY RECONCILIATION",
        "read_only": True,
        "database_path": private_path(path),
        "interval": period,
        "sqlite_validated": False,
        "truncation_warnings": [],
        "errors": {},
        "ui_reconciliation_completed": False,
    }
    try:
        await db.initialize()
        report["sqlite_validated"] = True
        report["schema"] = db.schema.diagnostics()
        # Counts are schema-resolved factual counts, even if conversion is unsupported.
        for label, names in {
            "category_count": ["Category"],
            "tag_count": ["Tag"],
            "budget_count": ["Budget"],
            "scheduled_transaction_count": list(SCHEDULED_TYPES),
        }.items():
            ids = [
                db.schema.entities[name] for name in names if name in db.schema.entities
            ]
            if not ids:
                report[label] = None
                report["errors"][label] = {
                    "code": "UNSUPPORTED_SCHEMA",
                    "message": "Entity family unavailable",
                }
            else:
                report[label] = (
                    await db.execute_query(
                        "SELECT COUNT(*) AS n FROM ZSYNCOBJECT WHERE Z_ENT IN ("  # nosec B608
                        + placeholders(ids)
                        + ")",
                        tuple(ids),
                    )
                )[0]["n"]
        actions: dict[str, Callable[[], Awaitable[Any]]] = {
            "accounts": lambda: AccountService(db).list_accounts(True),
            "cashflow": lambda: TransactionService(db).summarize_cashflow(period),
            "budgets": lambda: BudgetService(db).get_budgets(),
            "scheduled": lambda: ScheduledTransactionService(
                db
            ).get_scheduled_transactions(),
            "categories": lambda: validate_classifications(db, "Category"),
            "tags": lambda: validate_classifications(db, "Tag"),
        }
        for label, action in actions.items():
            try:
                result = await action()
                if label in ("accounts", "cashflow"):
                    report[label] = result
                    if label == "cashflow" and result["expense_categories"].truncated:
                        groups = result["expense_categories"]
                        report["truncation_warnings"].append(
                            f"Expense category breakdown returns {groups.returned_count} "
                            f"of {groups.matched_count} groups; currency totals include "
                            "every matched transaction"
                        )
                else:
                    report[label + "_validated_count"] = (
                        result if isinstance(result, int) else len(result)
                    )
            except MoneyWizError as exc:  # noqa: PERF203 - independent diagnostic sections
                report["errors"][label] = exc.as_dict()
        report["account_count"] = len(await AccountService(db).rows())
        if report["errors"]:
            report["validation_status"] = "incomplete_explicit_errors"
        else:
            report["validation_status"] = (
                "adapter_checks_complete_ui_comparison_pending"
            )
        return report
    finally:
        await db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, help="Exact MoneyWiz SQLite path")
    parser.add_argument("--start", required=True, help="Inclusive ISO date/datetime")
    parser.add_argument("--end", required=True, help="Exclusive ISO date/datetime")
    parser.add_argument("--timezone", default="UTC")
    args = parser.parse_args()
    try:
        report = asyncio.run(reconcile(args.db, args.start, args.end, args.timezone))
        print(TypeAdapter(dict[str, Any]).dump_json(report, indent=2).decode())
        return 2 if report["errors"] else 0
    except MoneyWizError as exc:
        print(json.dumps({"error": exc.as_dict()}), file=sys.stderr)
        return 1
    except Exception:
        print(
            json.dumps(
                {
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Validation failed without exposing database contents",
                    }
                }
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
