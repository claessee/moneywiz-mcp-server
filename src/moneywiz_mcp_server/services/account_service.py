"""Account retrieval with explicit provisional balance components."""

from decimal import Decimal
from typing import Any

from moneywiz_mcp_server.database.connection import DatabaseManager
from moneywiz_mcp_server.database.schema import ACCOUNT_TYPES, TRANSACTION_TYPES
from moneywiz_mcp_server.errors import MoneyWizError
from moneywiz_mcp_server.models.currency_types import (
    Money,
    currency_code,
    decimal_value,
    exact_add,
)
from moneywiz_mcp_server.models.responses import Account

from .category_classification_service import required_name


def placeholders(values: dict[int, str] | list[int]) -> str:
    if not values:
        raise MoneyWizError("SCHEMA_ERROR", "Empty entity set")
    return ",".join("?" for _ in values)


class AccountService:
    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db = db_manager

    async def rows(self) -> dict[int, dict[str, Any]]:
        roles = self.db.schema.family(ACCOUNT_TYPES)
        self.db.schema.require_columns(
            "ZSYNCOBJECT", "ZNAME", "ZCURRENCYNAME", "ZOPENINGBALANCE", "ZARCHIVED"
        )
        return {
            r["Z_PK"]: r
            for r in await self.db.execute_query(
                "SELECT * FROM ZSYNCOBJECT WHERE Z_ENT IN ("  # nosec B608
                + placeholders(roles)
                + ") ORDER BY Z_PK",
                tuple(roles),
            )
        }

    async def resolve_ids(self, ids: list[str]) -> list[int]:
        rows = await self.rows()
        resolved = []
        for value in ids:
            matches = [
                pk
                for pk, row in rows.items()
                if str(pk) == value or row.get("ZGID") == value
            ]
            if len(matches) != 1:
                raise MoneyWizError(
                    "INVALID_PARAMETER", "Account identifier is missing or ambiguous"
                )
            resolved.append(matches[0])
        return sorted(set(resolved))

    async def list_accounts(
        self, include_hidden: bool = False, account_type: str | None = None
    ) -> list[Account]:
        if account_type is not None and account_type not in ACCOUNT_TYPES.values():
            raise MoneyWizError("INVALID_PARAMETER", "Unsupported account type")
        types = self.db.schema.family(ACCOUNT_TYPES)
        transaction_types = self.db.schema.family(TRANSACTION_TYPES)
        self.db.schema.require_columns("ZSYNCOBJECT", "ZAMOUNT1", "ZACCOUNT2")
        accounts = await self.rows()
        totals: dict[int, dict[str, Decimal]] = {pk: {} for pk in accounts}
        counts: dict[int, dict[str, int]] = {pk: {} for pk in accounts}
        async for row in self.db.iter_query(
            "SELECT Z_ENT, ZACCOUNT2, ZAMOUNT1 FROM ZSYNCOBJECT WHERE Z_ENT IN ("  # nosec B608
            + placeholders(transaction_types)
            + ")",
            tuple(transaction_types),
        ):
            key = row["ZACCOUNT2"]
            if key not in accounts:
                raise MoneyWizError(
                    "DATA_INTEGRITY", "Transaction references an unavailable account"
                )
            role = transaction_types[row["Z_ENT"]]
            totals[key][role] = exact_add(
                totals[key].get(role, Decimal(0)), decimal_value(row["ZAMOUNT1"])
            )
            counts[key][role] = counts[key].get(role, 0) + 1
        output = []
        for key, row in accounts.items():
            kind = types[row["Z_ENT"]]
            if row["ZARCHIVED"] not in (0, 1):
                raise MoneyWizError("DATA_INTEGRITY", "Invalid account archive flag")
            if (not include_hidden and row["ZARCHIVED"]) or (
                account_type is not None and kind != account_type
            ):
                continue
            currency = currency_code(row["ZCURRENCYNAME"])
            total = Decimal(0)
            for amount in totals[key].values():
                total = exact_add(total, amount)
            opening = (
                decimal_value(row["ZOPENINGBALANCE"])
                if row["ZOPENINGBALANCE"] is not None
                else None
            )
            credit = (
                decimal_value(row["ZCREDITLIMIT"])
                if row.get("ZCREDITLIMIT") is not None
                else None
            )
            candidate = exact_add(opening, total) if opening is not None else None
            warnings = [
                "Calculated balance is opening plus stored account amounts; compare with MoneyWiz UI"
            ]
            if kind == "credit_card":
                warnings.append(
                    "Credit-card opening balance/limit semantics unresolved (upstream #48)"
                )
            if opening is None:
                warnings.append(
                    "Opening balance is null; no calculated balance is claimed"
                )
            if kind in ("investment", "forex", "loan"):
                warnings.append(
                    "Valuation/loan semantics unsupported; component sum is diagnostic only"
                )
            output.append(
                Account(
                    id=str(key),
                    name=required_name(row, ("ZNAME",)),
                    type=kind,
                    currency=currency,
                    archived=bool(row["ZARCHIVED"]),
                    calculated_balance=Money(amount=candidate, currency=currency)
                    if candidate is not None
                    and kind not in ("investment", "forex", "loan")
                    else None,
                    balance_components={
                        "opening_balance": Money(amount=opening, currency=currency)
                        if opening is not None
                        else None,
                        "transaction_sum": Money(amount=total, currency=currency),
                        "transaction_sums_by_type": {
                            t: Money(amount=v, currency=currency)
                            for t, v in sorted(totals[key].items())
                        },
                        "transaction_counts_by_type": counts[key],
                        "credit_limit": Money(amount=credit, currency=currency)
                        if credit is not None
                        else None,
                        "opening_plus_transactions": Money(
                            amount=candidate, currency=currency
                        )
                        if candidate is not None
                        else None,
                        "opening_plus_transactions_plus_limit": Money(
                            amount=exact_add(candidate, credit), currency=currency
                        )
                        if candidate is not None
                        and credit is not None
                        and kind == "credit_card"
                        else None,
                    },
                    warnings=warnings,
                )
            )
        return output

    async def get_account(self, account_id: str) -> Account:
        key = (await self.resolve_ids([account_id]))[0]
        return next(a for a in await self.list_accounts(True) if a.id == str(key))
