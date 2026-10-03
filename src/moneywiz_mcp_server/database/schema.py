"""Bounded adapter for observed MoneyWiz Core Data stores, never fixed IDs."""

from dataclasses import dataclass, field
import re
from typing import TYPE_CHECKING

from moneywiz_mcp_server.errors import MoneyWizError

if TYPE_CHECKING:
    from .connection import DatabaseManager

ACCOUNT_TYPES = {
    "BankChequeAccount": "checking",
    "BankSavingAccount": "savings",
    "CashAccount": "cash",
    "CreditCardAccount": "credit_card",
    "LoanAccount": "loan",
    "InvestmentAccount": "investment",
    "ForexAccount": "forex",
}
TRANSACTION_TYPES = {
    "DepositTransaction": "deposit",
    "WithdrawTransaction": "withdraw",
    "TransferDepositTransaction": "transfer_in",
    "TransferWithdrawTransaction": "transfer_out",
    "InvestmentBuyTransaction": "investment_buy",
    "InvestmentSellTransaction": "investment_sell",
    "InvestmentExchangeTransaction": "investment_exchange",
    "RefundTransaction": "refund",
    "ReconcileTransaction": "reconcile",
    "TransferBudgetTransaction": "transfer_budget",
}
SCHEDULED_TYPES = {
    "ScheduledDepositTransactionHandler": "deposit",
    "ScheduledWithdrawTransactionHandler": "withdraw",
    "ScheduledTransferTransactionHandler": "transfer",
}


def quote_identifier(value: str) -> str:
    """Quote even hostile SQLite identifiers; values still use bound parameters."""
    if not value or "\x00" in value:
        raise MoneyWizError("SCHEMA_ERROR", "Invalid SQLite identifier")
    return '"' + value.replace('"', '""') + '"'


@dataclass
class Schema:
    entities: dict[str, int]
    tables: dict[str, frozenset[str]]
    _joins: dict[tuple[str, str], tuple[str, str, str]] = field(default_factory=dict)

    @classmethod
    async def inspect(cls, db: "DatabaseManager") -> "Schema":
        tables = {}
        for row in await db.execute_query(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ):
            name = row["name"]
            columns = await db.execute_query(
                "SELECT name FROM pragma_table_info(?)", (name,)
            )
            tables[name] = frozenset(c["name"] for c in columns)
        if len(tables) > 500 or any(len(c) > 1000 for c in tables.values()):
            raise MoneyWizError(
                "UNSUPPORTED_SCHEMA", "Schema exceeds diagnostic size bounds"
            )
        schema = cls({}, tables)
        schema.require_columns("Z_PRIMARYKEY", "Z_ENT", "Z_NAME")
        schema.require_columns("ZSYNCOBJECT", "Z_PK", "Z_ENT")
        rows = await db.execute_query("SELECT * FROM Z_PRIMARYKEY")
        if len(rows) > 500:
            raise MoneyWizError(
                "UNSUPPORTED_SCHEMA", "Entity map exceeds diagnostic size bound"
            )
        for row in rows:
            name, entity = row["Z_NAME"], row["Z_ENT"]
            if (
                not isinstance(name, str)
                or not name
                or not isinstance(entity, int)
                or entity <= 0
                or name in schema.entities
                or entity in schema.entities.values()
            ):
                raise MoneyWizError(
                    "SCHEMA_ERROR", "Invalid or duplicate Z_PRIMARYKEY mapping"
                )
            schema.entities[name] = entity
        for required in (
            "Transaction",
            "DepositTransaction",
            "WithdrawTransaction",
            "Category",
            "Payee",
        ):
            schema.entity(required)
        if not set(ACCOUNT_TYPES).intersection(schema.entities):
            raise MoneyWizError("SCHEMA_ERROR", "Missing supported account entities")
        by_id = {r["Z_ENT"]: r for r in rows}
        for row in rows:
            seen: set[int] = set()
            current = row
            while current.get("Z_SUPER"):
                parent = current["Z_SUPER"]
                if parent not in by_id or parent in seen:
                    raise MoneyWizError(
                        "SCHEMA_ERROR", "Invalid Core Data inheritance mapping"
                    )
                seen.add(parent)
                current = by_id[parent]
        invalid_pk = await db.execute_query(
            "SELECT COUNT(*) AS n FROM ZSYNCOBJECT WHERE Z_PK IS NULL OR typeof(Z_PK) != 'integer' OR Z_PK <= 0"
        )
        duplicate_pk = await db.execute_query(
            "SELECT Z_PK FROM ZSYNCOBJECT GROUP BY Z_PK HAVING COUNT(*) > 1 LIMIT 1"
        )
        if invalid_pk[0]["n"] or duplicate_pk:
            raise MoneyWizError(
                "SCHEMA_ERROR", "Invalid or duplicate Core Data object keys"
            )
        present = await db.execute_query("SELECT DISTINCT Z_ENT FROM ZSYNCOBJECT")
        if any(r["Z_ENT"] not in schema.entities.values() for r in present):
            raise MoneyWizError(
                "SCHEMA_ERROR", "Stored entity absent from Z_PRIMARYKEY"
            )
        base_ids = {
            schema.entities[n]
            for n in ("Account", "Transaction", "ScheduledTransactionHandler")
            if n in schema.entities
        }
        if any(r["Z_ENT"] in base_ids for r in present):
            raise MoneyWizError(
                "UNSUPPORTED_SCHEMA",
                "Unclassified base account/transaction instances are present",
            )
        # Reject unknown descendants even when their names do not follow the convention.
        allowed = set(ACCOUNT_TYPES) | set(TRANSACTION_TYPES) | set(SCHEDULED_TYPES)
        bases = {"Account", "Transaction", "ScheduledTransactionHandler"}
        for row in rows:
            name = row["Z_NAME"]
            current = row
            ancestors = set()
            while current.get("Z_SUPER"):
                current = by_id[current["Z_SUPER"]]
                ancestors.add(current["Z_NAME"])
            relevant = name.endswith(
                ("Account", "Transaction", "TransactionHandler")
            ) or bool(ancestors & bases)
            if (
                relevant
                and name not in allowed | bases
                and row["Z_ENT"] in {r["Z_ENT"] for r in present}
            ):
                raise MoneyWizError(
                    "UNSUPPORTED_SCHEMA",
                    "Unrecognized account/transaction entity: " + name,
                )
        return schema

    def entity(self, name: str) -> int:
        if name not in self.entities:
            raise MoneyWizError("SCHEMA_ERROR", "Missing entity: " + name)
        return self.entities[name]

    def family(self, names: dict[str, str]) -> dict[int, str]:
        result = {
            self.entities[n]: role for n, role in names.items() if n in self.entities
        }
        if not result:
            raise MoneyWizError(
                "UNSUPPORTED_SCHEMA", "Requested entity family is unavailable"
            )
        return result

    def require_columns(self, table: str, *columns: str) -> None:
        if table not in self.tables:
            raise MoneyWizError("SCHEMA_ERROR", "Missing table: " + table)
        missing = set(columns) - self.tables[table]
        if missing:
            raise MoneyWizError(
                "SCHEMA_ERROR",
                "Missing columns in " + table + ": " + ", ".join(sorted(missing)),
            )

    def identifier(self, table: str, column: str | None = None) -> str:
        self.require_columns(table, *([column] if column else []))
        return quote_identifier(column or table)

    def tag_join(self, owner: str) -> tuple[str, str, str]:
        key = (owner, "Tag")
        if key in self._joins:
            return self._joins[key]
        owner_id, tag_id = self.entity(owner), self.entity("Tag")
        matches = []
        for table, columns in self.tables.items():
            if not re.fullmatch(r"Z_\d+TAGS\d*", table):
                continue
            owners = [
                c
                for c in columns
                if re.fullmatch(
                    rf"Z_{owner_id}(TRANSACTIONS|SCHEDULEDTRANSACTIONS)\d*", c
                )
            ]
            tags = [c for c in columns if re.fullmatch(rf"Z_{tag_id}TAGS\d*", c)]
            if len(owners) == len(tags) == 1:
                matches.append((table, owners[0], tags[0]))
        if len(matches) != 1:
            raise MoneyWizError(
                "SCHEMA_ERROR", "Missing or ambiguous tag relationship for " + owner
            )
        self._joins[key] = matches[0]
        return matches[0]

    def category_links(self, owner: str) -> list[str]:
        self.require_columns("ZCATEGORYASSIGMENT", "ZCATEGORY")
        candidates = {
            "transaction": ["ZTRANSACTION"],
            "budget": ["ZBUDGET"],
            "scheduled": [
                "ZSCHEDULEDTRANSACITION",
                *[
                    column
                    for column in self.tables["ZCATEGORYASSIGMENT"]
                    if re.fullmatch(r"Z\d+_SCHEDULEDTRANSACITION", column)
                ],
            ],
        }[owner]
        found = [c for c in candidates if c in self.tables["ZCATEGORYASSIGMENT"]]
        if not found:
            raise MoneyWizError(
                "SCHEMA_ERROR", "Missing category relationship for " + owner
            )
        return found

    def diagnostics(self) -> dict[str, object]:
        optional = [
            n for n in ("Tag", "Budget", *SCHEDULED_TYPES) if n not in self.entities
        ]
        return {
            "entities": dict(sorted(self.entities.items())),
            "tables": {t: sorted(c) for t, c in sorted(self.tables.items())},
            "missing_optional_entities": optional,
            "warnings": [
                "Private Core Data schema adapter; MoneyWiz UI reconciliation required"
            ],
        }
