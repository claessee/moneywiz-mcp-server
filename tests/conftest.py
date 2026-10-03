"""Only fabricated financial data; never discover or open a real MoneyWiz store."""

from datetime import datetime, timezone
from pathlib import Path
import sqlite3

import pytest

from moneywiz_mcp_server.database.connection import DatabaseManager
from moneywiz_mcp_server.database.schema import (
    ACCOUNT_TYPES,
    SCHEDULED_TYPES,
    TRANSACTION_TYPES,
)
from moneywiz_mcp_server.utils.date_utils import datetime_to_core_data_timestamp

NAMES = [
    "Account",
    *ACCOUNT_TYPES,
    "Transaction",
    *TRANSACTION_TYPES,
    "Category",
    "Payee",
    "Tag",
    "Budget",
    "Currency",
    "ScheduledTransactionHandler",
    *SCHEDULED_TYPES,
]
COLUMNS = {
    "Z_PK": "INTEGER PRIMARY KEY",
    "Z_ENT": "INTEGER",
    "ZGID": "TEXT",
    "ZNAME": "TEXT",
    "ZNAME2": "TEXT",
    "ZNAME5": "TEXT",
    "ZNAME6": "TEXT",
    "ZCODE": "TEXT",
    "ZCURRENCYNAME": "TEXT",
    "ZCURRENCYNAME3": "TEXT",
    "ZCURRENCY": "INTEGER",
    "ZOPENINGBALANCE": "TEXT",
    "ZCREDITLIMIT": "TEXT",
    "ZARCHIVED": "INTEGER",
    "ZAMOUNT1": "TEXT",
    "ZDATE1": "REAL",
    "ZACCOUNT2": "INTEGER",
    "ZPAYEE2": "INTEGER",
    "ZDESC2": "TEXT",
    "ZNOTES1": "TEXT",
    "ZRECONCILED": "INTEGER",
    "ZCATEGORY2": "INTEGER",
    "ZPARENTCATEGORY": "INTEGER",
    "ZAMOUNT": "TEXT",
    "ZEXECUTEDATE": "REAL",
    "ZACCOUNT1": "INTEGER",
    "ZPAYEE1": "INTEGER",
    "ZDISABLEEXECUTION": "INTEGER",
    "ZISREPEATABLE1": "INTEGER",
    "ZDESC1": "TEXT",
    "ZDURATION1": "INTEGER",
    "ZDURATIONUNITS1": "INTEGER",
    "ZEXECUTESCOUNT": "INTEGER",
    "ZOPENINGBALANCE1": "TEXT",
    "ZDURATION": "INTEGER",
    "ZDURATIONUNITS": "INTEGER",
    "ZISREPEATABLE": "INTEGER",
}


def make_database(
    path: Path, generation: int = 0, real_amounts: bool = False
) -> dict[str, int]:
    entities = {
        name: (i + 1) if generation == 0 else (len(NAMES) - i) * 7 + 100
        for i, name in enumerate(NAMES)
    }
    with sqlite3.connect(path) as conn:
        conn.execute(
            "CREATE TABLE Z_PRIMARYKEY (Z_ENT INTEGER PRIMARY KEY,Z_NAME TEXT,Z_SUPER INTEGER)"
        )
        for name, key in entities.items():
            parent = (
                "Account"
                if name in ACCOUNT_TYPES
                else "Transaction"
                if name in TRANSACTION_TYPES
                else "ScheduledTransactionHandler"
                if name in SCHEDULED_TYPES
                else None
            )
            conn.execute(
                "INSERT INTO Z_PRIMARYKEY VALUES (?,?,?)",
                (key, name, entities.get(parent)),
            )
        cols = dict(COLUMNS)
        if real_amounts:
            for c in (
                "ZAMOUNT1",
                "ZOPENINGBALANCE",
                "ZCREDITLIMIT",
                "ZAMOUNT",
                "ZOPENINGBALANCE1",
            ):
                cols[c] = "REAL"
        conn.execute(
            "CREATE TABLE ZSYNCOBJECT ("
            + ",".join(k + " " + v for k, v in cols.items())
            + ")"
        )
        conn.execute(
            "CREATE TABLE ZCATEGORYASSIGMENT (Z_PK INTEGER PRIMARY KEY,ZTRANSACTION INTEGER,ZCATEGORY INTEGER,ZBUDGET INTEGER,ZSCHEDULEDTRANSACITION INTEGER,Z31_SCHEDULEDTRANSACITION INTEGER)"
        )
        conn.execute(
            "CREATE TABLE ZACCOUNTBUDGETLINK (ZBUDGET INTEGER,ZACCOUNT INTEGER)"
        )
        for owner, field in [
            ("Transaction", "TRANSACTIONS"),
            ("ScheduledTransactionHandler", "SCHEDULEDTRANSACTIONS1"),
        ]:
            conn.execute(
                f"CREATE TABLE Z_{entities[owner]}TAGS (Z_{entities[owner]}{field} INTEGER,Z_{entities['Tag']}TAGS2 INTEGER)"
            )

        def insert(pk: int, entity: str, **values: object) -> None:
            row = {"Z_PK": pk, "Z_ENT": entities[entity], **values}
            conn.execute(
                "INSERT INTO ZSYNCOBJECT ("
                + ",".join(row)
                + ") VALUES ("
                + ",".join("?" for _ in row)
                + ")",
                tuple(row.values()),
            )

        for pk, entity, currency, opening in [
            (1, "CashAccount", "EUR", "100"),
            (2, "BankChequeAccount", "USD", "0"),
            (3, "CreditCardAccount", "EUR", "-1000"),
            (4, "BankSavingAccount", "SEK", "10000"),
        ]:
            insert(
                pk,
                entity,
                ZNAME=f"Fabricated account {pk}",
                ZGID=f"account-{pk}",
                ZCURRENCYNAME=currency,
                ZOPENINGBALANCE=opening,
                ZCREDITLIMIT="5000" if pk == 3 else None,
                ZARCHIVED=0,
            )
        insert(200, "Category", ZNAME2="Food", ZPARENTCATEGORY=None)
        insert(201, "Category", ZNAME2="Groceries", ZPARENTCATEGORY=200)
        insert(202, "Category", ZNAME2="Salary", ZPARENTCATEGORY=None)
        insert(210, "Payee", ZNAME5="Fabricated employer")
        insert(220, "Tag", ZNAME6="Fabricated recurring")
        insert(500, "Currency", ZCODE="GBP")
        timestamp = datetime_to_core_data_timestamp(
            datetime(2026, 9, 15, 12, tzinfo=timezone.utc)
        )
        transactions = [
            (100, "DepositTransaction", 1, "100"),
            (101, "WithdrawTransaction", 1, "-0.1"),
            (102, "WithdrawTransaction", 1, "-0.2"),
            (103, "WithdrawTransaction", 3, "-20"),
            (104, "TransferWithdrawTransaction", 1, "-10"),
            (105, "TransferDepositTransaction", 2, "12"),
            (106, "DepositTransaction", 2, "100"),
            (107, "WithdrawTransaction", 4, "-100"),
            (108, "RefundTransaction", 1, "5"),
            (109, "ReconcileTransaction", 1, "2"),
            (110, "InvestmentBuyTransaction", 1, "-3"),
            (111, "TransferBudgetTransaction", 1, "1"),
            (112, "DepositTransaction", 1, "0"),
            (113, "WithdrawTransaction", 1, "0"),
            (114, "WithdrawTransaction", 1, "-7"),
            (115, "WithdrawTransaction", 1, "-9"),
        ]
        for pk, entity, account, amount in transactions:
            date = (
                datetime_to_core_data_timestamp(
                    datetime(2026, 9, 1, tzinfo=timezone.utc)
                )
                - 1
                if pk == 114
                else datetime_to_core_data_timestamp(
                    datetime(2026, 10, 1, tzinfo=timezone.utc)
                )
                if pk == 115
                else timestamp
            )
            insert(
                pk,
                entity,
                ZACCOUNT2=account,
                ZAMOUNT1=amount,
                ZDATE1=date,
                ZPAYEE2=210 if pk == 100 else None,
                ZDESC2="Private fabricated description",
                ZNOTES1="Private fabricated notes",
                ZRECONCILED=0,
            )
            category = 202 if entity == "DepositTransaction" else 201
            conn.execute(
                "INSERT INTO ZCATEGORYASSIGMENT(ZTRANSACTION,ZCATEGORY) VALUES (?,?)",
                (pk, category),
            )
        conn.execute(
            f"INSERT INTO Z_{entities['Transaction']}TAGS VALUES (?,?)", (101, 220)
        )
        for pk, entity, amount in [
            (300, "ScheduledDepositTransactionHandler", "1000"),
            (301, "ScheduledWithdrawTransactionHandler", "-50"),
            (302, "ScheduledTransferTransactionHandler", "-10"),
        ]:
            insert(
                pk,
                entity,
                ZACCOUNT1=1,
                ZAMOUNT=amount,
                ZEXECUTEDATE=timestamp,
                ZCURRENCYNAME3="EUR",
                ZPAYEE1=210 if pk == 300 else None,
                ZDISABLEEXECUTION=1 if pk == 302 else 0,
                ZISREPEATABLE1=0 if pk == 302 else 1,
                ZDESC1="Fabricated schedule",
                ZDURATION1=1,
                ZDURATIONUNITS1=8,
                ZEXECUTESCOUNT=5,
            )
            conn.execute(
                "INSERT INTO ZCATEGORYASSIGMENT(ZSCHEDULEDTRANSACITION,ZCATEGORY) VALUES (?,?)",
                (pk, 202 if pk == 300 else 201),
            )
        conn.execute(
            f"INSERT INTO Z_{entities['ScheduledTransactionHandler']}TAGS VALUES (?,?)",
            (300, 220),
        )
        insert(
            400,
            "Budget",
            ZOPENINGBALANCE1="0",
            ZAMOUNT1="100",
            ZCURRENCYNAME="EUR",
            ZDURATION=1,
            ZDURATIONUNITS=8,
            ZISREPEATABLE=1,
        )
        insert(
            401,
            "Budget",
            ZOPENINGBALANCE1="-10",
            ZAMOUNT1="0",
            ZCURRENCY=500,
            ZDURATION=1,
            ZDURATIONUNITS=8,
            ZISREPEATABLE=1,
        )
        conn.execute(
            "INSERT INTO ZCATEGORYASSIGMENT(ZBUDGET,ZCATEGORY) VALUES (400,201)"
        )
        conn.execute("INSERT INTO ZACCOUNTBUDGETLINK VALUES (400,1)")
    return entities


@pytest.fixture
def synthetic(tmp_path):
    path = tmp_path / "MoneyWiz_iCloud.sqlite"
    entities = make_database(path)
    return path, entities


@pytest.fixture
async def db(synthetic):
    manager = DatabaseManager(str(synthetic[0]))
    await manager.initialize()
    yield manager
    await manager.close()
