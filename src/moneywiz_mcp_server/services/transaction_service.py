"""Deterministic transaction queries and exact per-currency cashflow."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from moneywiz_mcp_server.database.connection import DatabaseManager
from moneywiz_mcp_server.database.schema import TRANSACTION_TYPES
from moneywiz_mcp_server.errors import MoneyWizError
from moneywiz_mcp_server.models.currency_types import (
    Money,
    currency_code,
    decimal_value,
    exact_add,
)
from moneywiz_mcp_server.models.responses import Page, Transaction, page
from moneywiz_mcp_server.utils.date_utils import (
    EPOCH,
    Interval,
    core_data_timestamp_to_datetime,
    datetime_to_core_data_timestamp,
)

from .account_service import AccountService, placeholders
from .category_classification_service import CategoryClassificationService


def validate_page(limit: int, offset: int) -> None:
    if (
        isinstance(limit, bool)
        or isinstance(offset, bool)
        or not 1 <= limit <= 500
        or not 0 <= offset <= 10_000_000
    ):
        raise MoneyWizError(
            "INVALID_PARAMETER", "Limit must be 1..500 and offset 0..10000000"
        )


class TransactionService:
    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db = db_manager
        self.classifications = CategoryClassificationService(db_manager)
        self.accounts = AccountService(db_manager)

    async def predicate(
        self,
        period: Interval,
        account_ids: list[str] | None = None,
        categories: list[str] | None = None,
        transaction_type: str | None = None,
    ) -> tuple[str, tuple[Any, ...]]:
        types = self.db.schema.family(TRANSACTION_TYPES)
        self.db.schema.category_links("transaction")
        if "Tag" in self.db.schema.entities:
            self.db.schema.tag_join("Transaction")
        self.db.schema.require_columns(
            "ZSYNCOBJECT",
            "ZAMOUNT1",
            "ZACCOUNT2",
            "ZDATE1",
            "ZPAYEE2",
            "ZRECONCILED",
            "ZDESC2",
            "ZNOTES1",
        )
        if transaction_type is not None:
            if transaction_type not in TRANSACTION_TYPES.values():
                raise MoneyWizError("INVALID_PARAMETER", "Unsupported transaction type")
            types = {pk: role for pk, role in types.items() if role == transaction_type}
            if not types:
                raise MoneyWizError(
                    "UNSUPPORTED_SCHEMA",
                    "Requested transaction type is absent from this model",
                )
        invalid_dates = await self.db.execute_query(
            "SELECT 1 FROM ZSYNCOBJECT WHERE Z_ENT IN ("  # nosec B608
            + placeholders(types)
            + ") AND (ZDATE1 IS NULL OR typeof(ZDATE1) NOT IN ('integer','real') OR ZDATE1 < ? OR ZDATE1 > ?) LIMIT 1",
            (
                *types,
                (datetime.min.replace(tzinfo=timezone.utc) - EPOCH).total_seconds(),
                (datetime.max.replace(tzinfo=timezone.utc) - EPOCH).total_seconds(),
            ),
        )
        if invalid_dates:
            raise MoneyWizError(
                "DATA_INTEGRITY",
                "Invalid transaction dates would make interval filtering incomplete",
            )
        conditions = [
            "t.Z_ENT IN (" + placeholders(types) + ")",
            "t.ZDATE1 >= ?",
            "t.ZDATE1 < ?",
        ]
        params: list[Any] = [
            *types,
            datetime_to_core_data_timestamp(period.start),
            datetime_to_core_data_timestamp(period.end),
        ]
        if account_ids is not None:
            ids = await self.accounts.resolve_ids(account_ids)
            conditions.append(
                "t.ZACCOUNT2 IN (" + placeholders(ids) + ")" if ids else "0"
            )
            params.extend(ids)
        if categories is not None:
            self.db.schema.category_links("transaction")
            all_categories = [
                await self.classifications.category(key)
                for key in await self.classifications.rows("Category")
            ]
            names = {c.name for c in all_categories}
            if any(name not in names for name in categories):
                raise MoneyWizError("INVALID_PARAMETER", "Requested category is absent")
            ids = [
                int(c.id)
                for c in all_categories
                if set(c.hierarchy).intersection(categories)
            ]
            conditions.append(
                "EXISTS (SELECT 1 FROM ZCATEGORYASSIGMENT c WHERE c.ZTRANSACTION=t.Z_PK AND c.ZCATEGORY IN ("  # nosec B608
                + placeholders(ids)
                + "))"
                if ids
                else "0"
            )
            params.extend(ids)
        return " AND ".join(conditions), tuple(params)

    async def convert(
        self, row: dict[str, Any], accounts: dict[int, dict[str, Any]]
    ) -> Transaction:
        account = accounts.get(row["ZACCOUNT2"])
        if account is None:
            raise MoneyWizError(
                "DATA_INTEGRITY", "Transaction references an unavailable account"
            )
        if row["ZRECONCILED"] not in (0, 1):
            raise MoneyWizError("DATA_INTEGRITY", "Invalid reconciled flag")
        categories = await self.classifications.categories_for(
            "transaction", row["Z_PK"]
        )
        direct = row.get("ZCATEGORY2")
        if direct and str(direct) not in {c.id for c in categories}:
            raise MoneyWizError(
                "UNSUPPORTED_SCHEMA", "Direct/assigned transaction categories disagree"
            )
        return Transaction(
            id=str(row["Z_PK"]),
            account_id=str(row["ZACCOUNT2"]),
            transaction_type=self.db.schema.family(TRANSACTION_TYPES)[row["Z_ENT"]],
            date=core_data_timestamp_to_datetime(row["ZDATE1"]).isoformat(),
            money=Money.from_raw(row["ZAMOUNT1"], account["ZCURRENCYNAME"]),
            description=row["ZDESC2"],
            notes=row["ZNOTES1"],
            reconciled=bool(row["ZRECONCILED"]),
            payee=await self.classifications.payee(row["ZPAYEE2"]),
            categories=categories,
            tags=await self.classifications.tags_for("Transaction", row["Z_PK"]),
        )

    async def get_transactions(
        self,
        period: Interval,
        account_ids: list[str] | None = None,
        categories: list[str] | None = None,
        transaction_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Page[Transaction]:
        validate_page(limit, offset)
        predicate, params = await self.predicate(
            period, account_ids, categories, transaction_type
        )
        count = (
            await self.db.execute_query(
                "SELECT COUNT(*) AS n FROM ZSYNCOBJECT t WHERE " + predicate,  # nosec B608
                params,
            )
        )[0]["n"]
        rows = await self.db.execute_query(
            "SELECT t.* FROM ZSYNCOBJECT t WHERE "  # nosec B608
            + predicate
            + " ORDER BY t.ZDATE1 DESC,t.Z_PK DESC LIMIT ? OFFSET ?",
            (*params, limit, offset),
        )
        accounts = await self.accounts.rows()
        return page(
            [await self.convert(r, accounts) for r in rows],
            count,
            limit,
            offset,
            [
                "Pagination is stable within each call; use a frozen consistent copy across calls if MoneyWiz is changing",
                *(
                    [
                        "Tag entity is absent from this model; tag classification is unavailable"
                    ]
                    if "Tag" not in self.db.schema.entities
                    else []
                ),
            ],
        )

    async def summarize_cashflow(
        self, period: Interval, account_ids: list[str] | None = None
    ) -> dict[str, Any]:
        predicate, params = await self.predicate(period, account_ids)
        accounts = await self.accounts.rows()
        types = self.db.schema.family(TRANSACTION_TYPES)
        totals: dict[str, dict[str, Decimal]] = {}
        counts: dict[str, int] = {}
        breakdown: dict[tuple[str, str], Decimal] = {}
        category_details: dict[str, Any] = {}
        records = transfers = split_expenses = 0
        async for row in self.db.iter_query(
            "SELECT t.* FROM ZSYNCOBJECT t WHERE "  # nosec B608
            + predicate
            + " ORDER BY t.ZDATE1,t.Z_PK",
            params,
        ):
            tx = await self.convert(row, accounts)
            role = types[row["Z_ENT"]]
            currency = currency_code(tx.money.currency)
            amount = decimal_value(tx.money.amount)
            totals.setdefault(currency, {})
            if len(totals) > 500:
                raise MoneyWizError(
                    "RESULT_TOO_LARGE", "Currency grouping exceeds bounded output size"
                )
            totals[currency][role] = exact_add(
                totals[currency].get(role, Decimal(0)), amount
            )
            counts[role] = counts.get(role, 0) + 1
            records += 1
            transfers += role in ("transfer_in", "transfer_out")
            if role == "withdraw":
                if len(tx.categories) > 1:
                    split_expenses += 1
                else:
                    category = tx.categories[0].id if tx.categories else "uncategorized"
                    category_details[category] = (
                        tx.categories[0] if tx.categories else None
                    )
                    key = (currency, category)
                    breakdown[key] = exact_add(
                        breakdown.get(key, Decimal(0)), amount.copy_negate()
                    )
        grouped = {}
        for currency, by_type in sorted(totals.items()):
            income = by_type.get("deposit", Decimal(0))
            expense = by_type.get("withdraw", Decimal(0)).copy_negate()
            grouped[currency] = {
                "income": Money(amount=income, currency=currency),
                "expenses": Money(amount=expense, currency=currency),
                "net": Money(
                    amount=exact_add(income, expense.copy_negate()), currency=currency
                ),
                "stored_sums_by_type": {
                    role: Money(amount=value, currency=currency)
                    for role, value in sorted(by_type.items())
                },
            }
        return {
            "interval": period,
            "matched_count": records,
            "processed_count": records,
            "truncated": False,
            "transaction_counts_by_type": dict(sorted(counts.items())),
            "transfer_leg_count": transfers,
            "totals_by_currency": grouped,
            "expense_categories": page(
                [
                    {
                        "category": category_details[category],
                        "money": Money(amount=value, currency=currency),
                    }
                    for (currency, category), value in sorted(breakdown.items())[:500]
                ],
                len(breakdown),
                500,
                0,
            ),
            "unallocated_split_expense_count": split_expenses,
            "warnings": [
                "Income is signed deposits; expenses are negated withdrawals (reversals retain their sign). Transfers, refunds, reconciliations and investments remain separate stored sums.",
                "Split expense amounts are included in currency totals but not allocated to categories",
            ],
        }
