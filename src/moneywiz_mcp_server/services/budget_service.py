"""Factual budget components without invented currency, limit or status."""

from moneywiz_mcp_server.database.connection import DatabaseManager
from moneywiz_mcp_server.errors import MoneyWizError
from moneywiz_mcp_server.models.currency_types import Money, currency_code
from moneywiz_mcp_server.models.responses import Budget

from .account_service import AccountService
from .category_classification_service import CategoryClassificationService


class BudgetService:
    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db = db_manager

    async def get_budgets(self) -> list[Budget]:
        entity = self.db.schema.entity("Budget")
        self.db.schema.category_links("budget")
        classifications = CategoryClassificationService(self.db)
        accounts = await AccountService(self.db).rows()
        self.db.schema.require_columns("ZACCOUNTBUDGETLINK", "ZBUDGET", "ZACCOUNT")
        rows = await self.db.execute_query(
            "SELECT * FROM ZSYNCOBJECT WHERE Z_ENT=? ORDER BY Z_PK", (entity,)
        )
        output = []
        for row in rows:
            linked = await self.db.execute_query(
                "SELECT DISTINCT ZACCOUNT FROM ZACCOUNTBUDGETLINK WHERE ZBUDGET=? ORDER BY ZACCOUNT",
                (row["Z_PK"],),
            )
            ids = [r["ZACCOUNT"] for r in linked]
            if any(key not in accounts for key in ids):
                raise MoneyWizError(
                    "DATA_INTEGRITY", "Budget references unavailable account"
                )
            codes = {
                currency_code(row[c])
                for c in (
                    "ZCURRENCYNAME",
                    "ZCURRENCYNAME1",
                    "ZCURRENCYNAME2",
                    "ZCURRENCYNAME3",
                )
                if row.get(c) is not None
            }
            if row.get("ZCURRENCY") is not None:
                currency_row = await classifications.reference(
                    "Currency", row["ZCURRENCY"]
                )
                self.db.schema.require_columns("ZSYNCOBJECT", "ZCODE")
                codes.add(currency_code(currency_row["ZCODE"]))
            # Do not infer a budget currency from its linked accounts.
            if len(codes) != 1:
                raise MoneyWizError(
                    "UNSUPPORTED_SCHEMA",
                    "Budget currency cannot be resolved unambiguously; inspect schema_info",
                )
            currency = next(iter(codes))
            fields = [
                c
                for c in ("ZOPENINGBALANCE1", "ZAMOUNT1")
                if c in self.db.schema.tables["ZSYNCOBJECT"]
            ]
            if not fields:
                raise MoneyWizError(
                    "SCHEMA_ERROR", "Missing observed budget monetary fields"
                )
            output.append(
                Budget(
                    id=str(row["Z_PK"]),
                    categories=await classifications.categories_for(
                        "budget", row["Z_PK"]
                    ),
                    account_ids=[str(key) for key in ids],
                    stored_monetary_fields={
                        c: Money.from_raw(row[c], currency)
                        if row[c] is not None
                        else None
                        for c in fields
                    },
                    duration_fields={
                        c: row[c]
                        for c in ("ZDURATION", "ZDURATIONUNITS", "ZISREPEATABLE")
                        if c in row
                    },
                )
            )
        return output
