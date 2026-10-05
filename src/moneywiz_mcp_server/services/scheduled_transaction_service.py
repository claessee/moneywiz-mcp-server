"""Stored scheduled handlers, including income; no guessed forecasts."""

from moneywiz_mcp_server.database.connection import DatabaseManager
from moneywiz_mcp_server.database.schema import SCHEDULED_TYPES
from moneywiz_mcp_server.errors import MoneyWizError
from moneywiz_mcp_server.models.currency_types import Money
from moneywiz_mcp_server.models.responses import ScheduledTransaction
from moneywiz_mcp_server.utils.date_utils import core_data_timestamp_to_datetime

from .account_service import AccountService, placeholders
from .category_classification_service import CategoryClassificationService


class ScheduledTransactionService:
    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db = db_manager

    async def get_scheduled_transactions(self) -> list[ScheduledTransaction]:
        types = self.db.schema.family(SCHEDULED_TYPES)
        self.db.schema.require_columns(
            "ZSYNCOBJECT",
            "ZAMOUNT",
            "ZEXECUTEDATE",
            "ZCURRENCYNAME3",
            "ZACCOUNT1",
            "ZPAYEE1",
            "ZDISABLEEXECUTION",
            "ZISREPEATABLE1",
            "ZDESC1",
        )
        self.db.schema.category_links("scheduled")
        if "Tag" in self.db.schema.entities:
            self.db.schema.tag_join("ScheduledTransactionHandler")
        classifications = CategoryClassificationService(self.db)
        accounts = await AccountService(self.db).rows()
        rows = await self.db.execute_query(
            "SELECT * FROM ZSYNCOBJECT WHERE Z_ENT IN ("  # nosec B608
            + placeholders(types)
            + ") ORDER BY ZEXECUTEDATE,Z_PK",
            tuple(types),
        )
        output = []
        for row in rows:
            if row["ZACCOUNT1"] is not None and row["ZACCOUNT1"] not in accounts:
                raise MoneyWizError(
                    "DATA_INTEGRITY", "Scheduled account reference is unavailable"
                )
            if row["ZDISABLEEXECUTION"] not in (0, 1) or row["ZISREPEATABLE1"] not in (
                0,
                1,
            ):
                raise MoneyWizError("DATA_INTEGRITY", "Invalid schedule flags")
            categories = await classifications.categories_for("scheduled", row["Z_PK"])
            direct = {
                str(row[c])
                for c in ("ZCATEGORY", "ZCATEGORY1", "ZCATEGORY2")
                if row.get(c)
            }
            if direct - {c.id for c in categories}:
                raise MoneyWizError(
                    "UNSUPPORTED_SCHEMA",
                    "Direct/assigned scheduled categories disagree",
                )
            output.append(
                ScheduledTransaction(
                    id=str(row["Z_PK"]),
                    transaction_type=types[row["Z_ENT"]],
                    account_id=str(row["ZACCOUNT1"])
                    if row["ZACCOUNT1"] is not None
                    else None,
                    money=Money.from_raw(row["ZAMOUNT"], row["ZCURRENCYNAME3"]),
                    next_execution=core_data_timestamp_to_datetime(
                        row["ZEXECUTEDATE"]
                    ).isoformat(),
                    disabled=bool(row["ZDISABLEEXECUTION"]),
                    repeatable=bool(row["ZISREPEATABLE1"]),
                    description=row["ZDESC1"],
                    payee=await classifications.payee(row["ZPAYEE1"]),
                    categories=categories,
                    tags=await classifications.tags_for(
                        "ScheduledTransactionHandler", row["Z_PK"]
                    ),
                    recurrence_fields={
                        c: row[c]
                        for c in (
                            "ZDURATION1",
                            "ZDURATIONUNITS1",
                            "ZEXECUTESCOUNT",
                            "ZONWEEKENDSEXECUTE",
                            "ZENDDATE",
                            "ZTOTALOCCURRENCES",
                            "ZWEEKENDSHANDLER",
                            "ZWEEKENDOPTION",
                            "ZFIRSTEXECUTEDATE",
                        )
                        if c in row
                    },
                )
            )
        return output
