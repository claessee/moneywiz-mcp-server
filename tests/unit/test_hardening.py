from datetime import datetime, timezone
from decimal import Decimal, localcontext
import hashlib
import json
from pathlib import Path
import sqlite3

import pytest

from moneywiz_mcp_server.config import Config, discovery_roots, validate_path
from moneywiz_mcp_server.database.connection import DatabaseManager
from moneywiz_mcp_server.database.schema import quote_identifier
from moneywiz_mcp_server.errors import MoneyWizError
from moneywiz_mcp_server.models.currency_types import Money, decimal_value, exact_add
from moneywiz_mcp_server.services.account_service import AccountService, placeholders
from moneywiz_mcp_server.services.budget_service import BudgetService
from moneywiz_mcp_server.services.scheduled_transaction_service import (
    ScheduledTransactionService,
)
from moneywiz_mcp_server.services.transaction_service import TransactionService
from moneywiz_mcp_server.utils.date_utils import (
    core_data_timestamp_to_datetime,
    datetime_to_core_data_timestamp,
    interval,
)
from moneywiz_mcp_server.validate import reconcile
from tests.conftest import make_database

PERIOD = interval("2026-09-01T00:00:00Z", "2026-10-01T00:00:00Z", "UTC")


def mutate(path, sql, params=()):
    with sqlite3.connect(path) as conn:
        conn.execute(sql, params)


@pytest.mark.parametrize("generation", [0, 1])
async def test_remapped_full_schema(tmp_path, generation):
    path = tmp_path / "store.sqlite"
    mapping = make_database(path, generation)
    db = DatabaseManager(str(path))
    try:
        await db.initialize()
        assert db.schema.entity("WithdrawTransaction") == mapping["WithdrawTransaction"]
        result = await TransactionService(db).get_transactions(PERIOD)
        assert result.matched_count == 14
        assert result.returned_count == 14
        assert not result.truncated
        assert [t.id for t in result.items] == list(map(str, range(113, 99, -1)))
        assert next(t for t in result.items if t.id == "101").tags == [
            "Fabricated recurring"
        ]
        assert (
            next(t for t in result.items if t.id == "100").payee
            == "Fabricated employer"
        )
        assert next(t for t in result.items if t.id == "101").categories[
            0
        ].hierarchy == ["Food", "Groceries"]
        schedules = await ScheduledTransactionService(db).get_scheduled_transactions()
        assert [s.transaction_type for s in schedules] == [
            "deposit",
            "withdraw",
            "transfer",
        ]
        assert schedules[0].categories[0].name == "Salary"
        assert schedules[0].tags == ["Fabricated recurring"]
        assert schedules[-1].disabled
        assert not schedules[-1].repeatable
        budgets = await BudgetService(db).get_budgets()
        assert len(budgets) == 2
        assert budgets[1].stored_monetary_fields["ZAMOUNT1"].currency == "GBP"
        assert budgets[1].stored_monetary_fields["ZOPENINGBALANCE1"].amount == -10
    finally:
        await db.close()


@pytest.mark.parametrize(
    "name",
    ["Transaction", "DepositTransaction", "WithdrawTransaction", "Category", "Payee"],
)
async def test_missing_required_mapping(synthetic, name):
    mutate(synthetic[0], "DELETE FROM Z_PRIMARYKEY WHERE Z_NAME=?", (name,))
    manager = DatabaseManager(str(synthetic[0]))
    with pytest.raises(MoneyWizError, match="Missing entity"):
        await manager.initialize()
    assert manager._connection is None


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE Z_PRIMARYKEY SET Z_NAME='Category' WHERE Z_NAME='Payee'",
        "UPDATE Z_PRIMARYKEY SET Z_NAME='' WHERE Z_NAME='Payee'",
        "UPDATE Z_PRIMARYKEY SET Z_SUPER=999 WHERE Z_NAME='Payee'",
        "UPDATE Z_PRIMARYKEY SET Z_SUPER=Z_ENT WHERE Z_NAME='Payee'",
        "UPDATE ZSYNCOBJECT SET Z_ENT=999 WHERE Z_PK=100",
        "UPDATE Z_PRIMARYKEY SET Z_NAME='RenamedWithdrawal' WHERE Z_NAME='RefundTransaction'",
    ],
)
async def test_invalid_schema_mapping(synthetic, sql):
    mutate(synthetic[0], sql)
    with pytest.raises(MoneyWizError):
        await DatabaseManager(str(synthetic[0])).initialize()


async def test_missing_optional_entity_is_explicit(synthetic):
    path, mapping = synthetic
    mutate(path, "DELETE FROM ZSYNCOBJECT WHERE Z_ENT=?", (mapping["Budget"],))
    mutate(path, "DELETE FROM Z_PRIMARYKEY WHERE Z_NAME='Budget'")
    manager = DatabaseManager(str(path))
    try:
        await manager.initialize()
        assert "Budget" in manager.schema.diagnostics()["missing_optional_entities"]
        with pytest.raises(MoneyWizError, match="Missing entity: Budget"):
            await BudgetService(manager).get_budgets()
    finally:
        await manager.close()


async def test_relationship_discovery_and_cache(db, synthetic):
    first = db.schema.tag_join("Transaction")
    assert first == db.schema.tag_join("Transaction")
    assert str(synthetic[1]["Transaction"]) in first[0]
    assert db.schema.tag_join("ScheduledTransactionHandler") != first
    with pytest.raises(MoneyWizError):
        db.schema.tag_join("Payee")


@pytest.mark.parametrize("mode", ["missing", "ambiguous"])
async def test_bad_tag_relationship(synthetic, mode):
    path, mapping = synthetic
    table = f"Z_{mapping['Transaction']}TAGS"
    mutate(
        path,
        f"DROP TABLE {table}"
        if mode == "missing"
        else f"CREATE TABLE {table}2 (Z_{mapping['Transaction']}TRANSACTIONS INTEGER,Z_{mapping['Tag']}TAGS INTEGER)",
    )
    manager = DatabaseManager(str(path))
    try:
        await manager.initialize()
        with pytest.raises(MoneyWizError, match="tag relationship"):
            await TransactionService(manager).get_transactions(PERIOD)
    finally:
        await manager.close()


@pytest.mark.parametrize(
    "identifier", ["plain", "space name", 'quote"name', 'x"; DROP TABLE ZSYNCOBJECT;--']
)
async def test_identifier_quoting(db, identifier):
    assert quote_identifier(identifier) == '"' + identifier.replace('"', '""') + '"'
    with pytest.raises(MoneyWizError):
        db.schema.identifier(identifier)


async def test_hostile_schema_table_is_safe(synthetic):
    path = synthetic[0]
    name = 'strange"; DROP TABLE ZSYNCOBJECT; --'
    mutate(path, "CREATE TABLE " + quote_identifier(name) + ' ("quoted""column" TEXT)')
    manager = DatabaseManager(str(path))
    try:
        await manager.initialize()
        assert manager.schema.identifier(name) == quote_identifier(name)
        assert await manager.execute_query(
            "SELECT COUNT(*) AS n FROM " + manager.schema.identifier(name)
        ) == [{"n": 0}]
        assert "ZSYNCOBJECT" in manager.schema.tables
    finally:
        await manager.close()


@pytest.mark.parametrize("suffix", ["-wal", "-shm", "-journal", "_shared.sqlite"])
async def test_rejected_files(tmp_path, suffix):
    path = tmp_path / ("MoneyWiz.sqlite" + suffix)
    path.write_bytes(b"x" * 10)
    with pytest.raises(MoneyWizError):
        await DatabaseManager(str(path)).initialize()


@pytest.mark.parametrize(
    "kind", ["missing", "empty", "invalid", "unrelated", "directory"]
)
async def test_invalid_database(tmp_path, kind):
    path = tmp_path / "store.sqlite"
    if kind == "empty":
        path.touch()
    elif kind == "invalid":
        path.write_bytes(b"not SQLite")
    elif kind == "unrelated":
        mutate(path, "CREATE TABLE unrelated(id INTEGER)")
    elif kind == "directory":
        path.mkdir()
    with pytest.raises(MoneyWizError):
        await DatabaseManager(str(path)).initialize()


async def test_regular_readable_file_required(synthetic, monkeypatch):
    monkeypatch.setattr("moneywiz_mcp_server.config.os.access", lambda *_: False)
    with pytest.raises(MoneyWizError):
        validate_path(synthetic[0])


async def test_explicit_special_filename(tmp_path):
    path = tmp_path / "store?# ü.sqlite"
    make_database(path)
    manager = DatabaseManager(str(path))
    try:
        await manager.initialize()
        assert len(await AccountService(manager).rows()) == 4
    finally:
        await manager.close()


async def test_discovery_icloud_and_ambiguity(tmp_path):
    roots = discovery_roots(tmp_path)
    root = next(
        r
        for r in roots
        if str(r).endswith(
            "com.moneywiz.personalfinance/Data/Library/Application Support"
        )
    )
    root.mkdir(parents=True)
    make_database(root / "MoneyWiz_iCloud_shared.sqlite")
    with pytest.raises(MoneyWizError):
        await Config.find_database(roots)
    primary = root / "MoneyWiz_iCloud.sqlite"
    make_database(primary)
    for name in [
        "MoneyWiz_iCloud.sqlite-wal",
        "MoneyWiz_iCloud.sqlite-shm",
        "zero.sqlite",
        "invalid.db",
    ]:
        (root / name).write_bytes(b"" if name == "zero.sqlite" else b"invalid")
    # Sidecars with invalid bytes prevent SQLite from reading the primary store;
    # remove fabricated corrupt sidecars before testing valid discovery.
    (root / "MoneyWiz_iCloud.sqlite-wal").unlink()
    (root / "MoneyWiz_iCloud.sqlite-shm").unlink()
    assert await Config.find_database(roots) == str(primary)
    make_database(root / "another.sqlite")
    with pytest.raises(MoneyWizError) as failure:
        await Config.find_database(roots)
    assert failure.value.code == "AMBIGUOUS_DATABASE"


async def test_discovery_rejects_empty_financial_store(synthetic):
    mutate(synthetic[0], "DELETE FROM ZSYNCOBJECT")
    with pytest.raises(MoneyWizError):
        await Config.find_database([synthetic[0].parent])


async def test_symlink_rejection(tmp_path):
    primary = tmp_path / "store_shared.sqlite"
    make_database(primary)
    alias = tmp_path / "alias.sqlite"
    alias.symlink_to(primary)
    with pytest.raises(MoneyWizError):
        validate_path(alias)


@pytest.mark.parametrize("value", ["false", "0", "yes", "FALSE"])
async def test_writable_environment_rejected(synthetic, monkeypatch, value):
    monkeypatch.setenv("MONEYWIZ_DB_PATH", str(synthetic[0]))
    monkeypatch.setenv("MONEYWIZ_READ_ONLY", value)
    with pytest.raises(MoneyWizError):
        await Config.from_env()


async def test_explicit_configuration(synthetic, monkeypatch):
    monkeypatch.setenv("MONEYWIZ_DB_PATH", str(synthetic[0]))
    assert (await Config.from_env()).database_path == str(synthetic[0])
    monkeypatch.delenv("MONEYWIZ_DB_PATH")
    with pytest.raises(MoneyWizError, match="exact MONEYWIZ_DB_PATH"):
        await Config.from_env()


@pytest.mark.parametrize("value", ["0", "501", "oops", "-1"])
async def test_invalid_max_results(synthetic, monkeypatch, value):
    monkeypatch.setenv("MONEYWIZ_DB_PATH", str(synthetic[0]))
    monkeypatch.setenv("MAX_RESULTS", value)
    with pytest.raises(MoneyWizError):
        await Config.from_env()


MUTATIONS = [
    "INSERT INTO ZSYNCOBJECT(Z_PK) VALUES(999)",
    "UPDATE ZSYNCOBJECT SET ZAMOUNT1='0'",
    "DELETE FROM ZSYNCOBJECT",
    "CREATE TABLE new_table(id INTEGER)",
    "DROP TABLE ZSYNCOBJECT",
    "ALTER TABLE ZSYNCOBJECT ADD COLUMN X TEXT",
    "REPLACE INTO ZSYNCOBJECT(Z_PK) VALUES(1)",
    "ATTACH DATABASE ':memory:' AS other",
    "VACUUM",
    "PRAGMA query_only=OFF",
    "PRAGMA user_version=99",
    "PRAGMA journal_mode=DELETE",
]


@pytest.mark.parametrize("sql", MUTATIONS)
async def test_all_write_routes_rejected(db, sql):
    before = hashlib.sha256(db.db_path.read_bytes()).hexdigest()
    with pytest.raises(MoneyWizError):
        await db.execute_query(sql)
    with pytest.raises(sqlite3.DatabaseError):
        await db._connection.execute(sql)
    assert hashlib.sha256(db.db_path.read_bytes()).hexdigest() == before
    assert not hasattr(db, "transaction")
    assert not hasattr(db, "commit")
    assert not hasattr(db, "api")


async def test_uri_is_readonly_even_without_query_guard(db):
    # Keep authorizer permitting all and query_only OFF only to probe mode=ro itself.
    await db._connection.set_authorizer(None)
    await db._connection.execute("PRAGMA query_only=OFF")
    with pytest.raises(sqlite3.OperationalError, match="readonly"):
        await db._connection.execute("DELETE FROM ZSYNCOBJECT")


async def test_connection_lifecycle(synthetic):
    manager = DatabaseManager(str(synthetic[0]))
    with pytest.raises(MoneyWizError):
        _ = manager.schema
    with pytest.raises(MoneyWizError):
        await manager.execute_query("SELECT 1")
    await manager.initialize()
    with pytest.raises(MoneyWizError):
        await manager.initialize()
    await manager.close()
    assert manager._schema is None
    await manager.initialize()
    await manager.close()


@pytest.mark.parametrize(
    ("kind", "expected"),
    [
        ("deposit", 3),
        ("withdraw", 5),
        ("transfer_in", 1),
        ("transfer_out", 1),
        ("refund", 1),
        ("reconcile", 1),
        ("investment_buy", 1),
        ("transfer_budget", 1),
    ],
)
async def test_type_filter_really_applied(db, kind, expected):
    result = await TransactionService(db).get_transactions(
        PERIOD, transaction_type=kind
    )
    assert result.matched_count == expected
    assert {t.transaction_type for t in result.items} == {kind}


@pytest.mark.parametrize(
    ("ids", "expected"),
    [(["1"], 10), (["account-3"], 1), (["1", "account-1"], 10), ([], 0)],
)
async def test_account_filter(db, ids, expected):
    result = await TransactionService(db).get_transactions(PERIOD, account_ids=ids)
    assert result.matched_count == expected


@pytest.mark.parametrize(
    ("categories", "expected"),
    [(["Food"], 11), (["Groceries"], 11), (["Salary"], 3), ([], 0)],
)
async def test_category_filter_before_pagination(db, categories, expected):
    result = await TransactionService(db).get_transactions(
        PERIOD, categories=categories, limit=1
    )
    assert result.matched_count == expected
    assert result.returned_count == min(1, expected)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"account_ids": ["missing"]},
        {"categories": ["missing"]},
        {"transaction_type": "income"},
        {"limit": 0},
        {"limit": 501},
        {"offset": -1},
    ],
)
async def test_invalid_query_parameter(db, kwargs):
    with pytest.raises(MoneyWizError):
        await TransactionService(db).get_transactions(PERIOD, **kwargs)


async def test_pagination_complete_and_stable(db):
    service = TransactionService(db)
    offset = 0
    ids = []
    while True:
        result = await service.get_transactions(PERIOD, limit=3, offset=offset)
        ids.extend(t.id for t in result.items)
        assert result.matched_count == 14
        if result.next_offset is None:
            break
        assert result.truncated
        offset = result.next_offset
    assert len(ids) == len(set(ids)) == 14
    assert ids == list(map(str, range(113, 99, -1)))
    after = await service.get_transactions(PERIOD, offset=20)
    assert after.returned_count == 0
    assert after.truncated
    assert after.next_offset is None


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE ZSYNCOBJECT SET ZACCOUNT2=999 WHERE Z_PK=100",
        "UPDATE ZSYNCOBJECT SET ZPAYEE2=999 WHERE Z_PK=100",
        "UPDATE ZCATEGORYASSIGMENT SET ZCATEGORY=999 WHERE ZTRANSACTION=100",
        "UPDATE ZSYNCOBJECT SET ZPARENTCATEGORY=201 WHERE Z_PK=200",
        "UPDATE ZSYNCOBJECT SET ZAMOUNT1=NULL WHERE Z_PK=100",
        "UPDATE ZSYNCOBJECT SET ZCURRENCYNAME=NULL WHERE Z_PK=1",
        "UPDATE ZSYNCOBJECT SET ZNAME5=NULL WHERE Z_PK=210",
        "UPDATE ZSYNCOBJECT SET ZNAME6=NULL WHERE Z_PK=220",
        "UPDATE ZSYNCOBJECT SET ZNAME2=NULL WHERE Z_PK=201",
        "UPDATE ZSYNCOBJECT SET ZCATEGORY2=200 WHERE Z_PK=101",
        "UPDATE ZSYNCOBJECT SET ZRECONCILED=NULL WHERE Z_PK=100",
    ],
)
async def test_integrity_failure_is_not_partial_success(synthetic, sql):
    mutate(synthetic[0], sql)
    manager = DatabaseManager(str(synthetic[0]))
    try:
        await manager.initialize()
        with pytest.raises(MoneyWizError):
            await TransactionService(manager).get_transactions(PERIOD)
        with pytest.raises(MoneyWizError):
            await TransactionService(manager).summarize_cashflow(PERIOD)
    finally:
        await manager.close()


async def test_currency_totals_never_implicitly_added(db):
    result = await TransactionService(db).summarize_cashflow(PERIOD)
    currencies = result["totals_by_currency"]
    assert set(currencies) == {"EUR", "USD", "SEK"}
    assert currencies["EUR"]["income"].amount == 100
    assert currencies["EUR"]["expenses"].amount == Decimal("20.3")
    assert currencies["USD"]["income"].amount == 100
    assert currencies["SEK"]["expenses"].amount == 100
    assert currencies["EUR"]["net"].amount == Decimal("79.7")
    assert result["transfer_leg_count"] == 2
    assert result["processed_count"] == 14
    assert not result["truncated"]
    assert "total" not in result
    assert "primary_currency" not in result
    assert currencies["EUR"]["stored_sums_by_type"]["refund"].amount == 5


async def test_split_categories_explicitly_unallocated(synthetic):
    mutate(
        synthetic[0],
        "INSERT INTO ZCATEGORYASSIGMENT(ZTRANSACTION,ZCATEGORY) VALUES(103,202)",
    )
    manager = DatabaseManager(str(synthetic[0]))
    try:
        await manager.initialize()
        result = await TransactionService(manager).summarize_cashflow(PERIOD)
        assert result["unallocated_split_expense_count"] == 1
        assert result["totals_by_currency"]["EUR"]["expenses"].amount == Decimal("20.3")
        assert sum(
            r["money"].amount
            for r in result["expense_categories"].items
            if r["money"].currency == "EUR"
        ) == Decimal("0.3")
    finally:
        await manager.close()


@pytest.mark.parametrize(
    "value", [None, "NaN", "Infinity", "-Infinity", "bad", "1e101"]
)
def test_invalid_money(value):
    with pytest.raises(MoneyWizError):
        decimal_value(value)


@pytest.mark.parametrize(
    "value",
    [
        "0",
        "-0.01",
        "0.123456789012345678901234567890123456789",
        "123456789012345678901234567890.000000001",
    ],
)
def test_precision_serialization(value):
    result = Money.from_raw(value, "EUR")
    assert json.loads(result.model_dump_json()) == {"amount": value, "currency": "EUR"}
    with localcontext() as context:
        context.prec = 5
        assert exact_add(result.amount, Decimal("0")) == Decimal(value)


async def test_real_sqlite_amounts(tmp_path):
    path = tmp_path / "real.sqlite"
    make_database(path, real_amounts=True)
    manager = DatabaseManager(str(path))
    try:
        await manager.initialize()
        assert (await TransactionService(manager).summarize_cashflow(PERIOD))[
            "totals_by_currency"
        ]["EUR"]["expenses"].amount == Decimal("20.3")
    finally:
        await manager.close()


async def test_balance_components_and_credit_uncertainty(db):
    accounts = await AccountService(db).list_accounts()
    cash = next(a for a in accounts if a.id == "1")
    assert cash.calculated_balance.amount == Decimal("178.7")
    assert cash.balance_components["transaction_sum"].amount == Decimal("78.7")
    card = next(a for a in accounts if a.id == "3")
    assert card.calculated_balance.amount == -1020
    assert card.balance_status == "provisional_unreconciled"
    assert (
        card.balance_components["opening_plus_transactions_plus_limit"].amount == 3980
    )
    assert any("unresolved" in w for w in card.warnings)
    assert (await AccountService(db).get_account("account-3")).id == "3"


@pytest.mark.parametrize(
    ("start", "end", "hours"),
    [
        ("2026-03-29", "2026-03-30", 23),
        ("2026-10-25", "2026-10-26", 25),
        ("2026-09-30", "2026-10-01", 24),
    ],
)
def test_lisbon_date_boundaries(start, end, hours):
    p = interval(start, end)
    assert (
        datetime_to_core_data_timestamp(p.end)
        - datetime_to_core_data_timestamp(p.start)
        == hours * 3600
    )
    assert p.start_inclusive
    assert p.end_exclusive


@pytest.mark.parametrize(
    ("start", "end", "zone"),
    [
        ("10/03/2026", "2026-10-04", "Europe/Lisbon"),
        ("2026-10-03T10:00", "2026-10-04", "UTC"),
        ("2026-02-30", "2026-03-01", "UTC"),
        ("2026-10-03", "2026-10-03", "UTC"),
        ("2026-10-04", "2026-10-03", "UTC"),
        ("2026-10-03", "2026-10-04", "Invalid/Zone"),
    ],
)
def test_bad_dates(start, end, zone):
    with pytest.raises(MoneyWizError):
        interval(start, end, zone)


def test_core_data_epoch_utc_zero():
    assert core_data_timestamp_to_datetime(0) == datetime(
        2001, 1, 1, tzinfo=timezone.utc
    )
    assert (
        datetime_to_core_data_timestamp(datetime(2001, 1, 1, tzinfo=timezone.utc)) == 0
    )
    with pytest.raises(MoneyWizError):
        datetime_to_core_data_timestamp(datetime(2001, 1, 1))
    with pytest.raises(MoneyWizError):
        core_data_timestamp_to_datetime(None)


async def test_safe_reconciliation_report(synthetic):
    report = await reconcile(
        str(synthetic[0]), "2026-09-01T00:00:00Z", "2026-10-01T00:00:00Z", "UTC"
    )
    assert not report["errors"]
    assert report["account_count"] == 4
    assert report["category_count"] == 3
    assert report["tag_count"] == 1
    assert report["scheduled_transaction_count"] == 3
    assert report["budget_count"] == 2
    assert report["categories_validated_count"] == 3
    assert report["tags_validated_count"] == 1
    assert report["cashflow"]["matched_count"] == 14
    assert report["readiness"] == "READY FOR READ-ONLY RECONCILIATION"
    assert not report["ui_reconciliation_completed"]
    assert "Private fabricated description" not in str(report)
    assert "Private fabricated notes" not in str(report)


@pytest.mark.parametrize("entity", ["Category", "Tag"])
async def test_harness_checks_unreferenced_classifications(synthetic, entity):
    path, mapping = synthetic
    mutate(
        path,
        "INSERT INTO ZSYNCOBJECT(Z_PK,Z_ENT) VALUES(999,?)",
        (mapping[entity],),
    )
    report = await reconcile(str(path), "2026-09-01", "2026-10-01")
    section = "categories" if entity == "Category" else "tags"
    assert report["errors"][section]["code"] == "DATA_INTEGRITY"
    assert report["validation_status"] == "incomplete_explicit_errors"


async def test_harness_reports_truncated_groups_with_complete_totals(synthetic):
    path, mapping = synthetic
    with sqlite3.connect(path) as writer:
        timestamp = writer.execute(
            "SELECT ZDATE1 FROM ZSYNCOBJECT WHERE Z_PK=101"
        ).fetchone()[0]
        for i in range(501):
            writer.execute(
                "INSERT INTO ZSYNCOBJECT(Z_PK,Z_ENT,ZNAME2) VALUES(?,?,?)",
                (1000 + i, mapping["Category"], f"Fabricated category {i}"),
            )
            writer.execute(
                "INSERT INTO ZSYNCOBJECT(Z_PK,Z_ENT,ZAMOUNT1,ZDATE1,ZACCOUNT2,ZRECONCILED) VALUES(?,?,'-1',?,1,0)",
                (2000 + i, mapping["WithdrawTransaction"], timestamp),
            )
            writer.execute(
                "INSERT INTO ZCATEGORYASSIGMENT(ZTRANSACTION,ZCATEGORY) VALUES(?,?)",
                (2000 + i, 1000 + i),
            )
    report = await reconcile(
        str(path), "2026-09-01T00:00:00Z", "2026-10-01T00:00:00Z", "UTC"
    )
    assert not report["errors"]
    assert report["truncation_warnings"]
    assert report["cashflow"]["expense_categories"].truncated
    assert report["cashflow"]["processed_count"] == 515
    assert report["cashflow"]["totals_by_currency"]["EUR"][
        "expenses"
    ].amount == Decimal("521.3")


async def test_empty_in_clause_prevented():
    with pytest.raises(MoneyWizError):
        placeholders([])


async def test_wal_snapshot_reads_committed_wal_and_stays_consistent(synthetic):
    path, _ = synthetic
    writer = sqlite3.connect(path)
    try:
        assert writer.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
        writer.execute("UPDATE ZSYNCOBJECT SET ZAMOUNT1='200' WHERE Z_PK=100")
        writer.commit()
        wal_before = Path(str(path) + "-wal").read_bytes()
        manager = DatabaseManager(str(path))
        try:
            await manager.initialize()
            assert (await TransactionService(manager).summarize_cashflow(PERIOD))[
                "totals_by_currency"
            ]["EUR"]["income"].amount == 200
            assert Path(str(path) + "-wal").read_bytes() == wal_before
            writer.execute("UPDATE ZSYNCOBJECT SET ZAMOUNT1='300' WHERE Z_PK=100")
            writer.commit()
            # Count/conversion/aggregates in this operation see the same snapshot.
            assert (await TransactionService(manager).summarize_cashflow(PERIOD))[
                "totals_by_currency"
            ]["EUR"]["income"].amount == 200
            await manager.close()
            await manager.initialize()
            assert (await TransactionService(manager).summarize_cashflow(PERIOD))[
                "totals_by_currency"
            ]["EUR"]["income"].amount == 300
        finally:
            await manager.close()
    finally:
        writer.close()


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE ZSYNCOBJECT SET ZAMOUNT1='0.1' WHERE Z_PK=101",
        "UPDATE ZSYNCOBJECT SET ZAMOUNT1='-100' WHERE Z_PK=100",
    ],
)
async def test_reversals_retain_signed_semantics(synthetic, sql):
    mutate(synthetic[0], sql)
    manager = DatabaseManager(str(synthetic[0]))
    try:
        await manager.initialize()
        totals = (await TransactionService(manager).summarize_cashflow(PERIOD))[
            "totals_by_currency"
        ]["EUR"]
        assert totals["expenses"].amount == (
            Decimal("20.1") if "101" in sql else Decimal("20.3")
        )
        assert totals["income"].amount == (100 if "101" in sql else -100)
    finally:
        await manager.close()


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE ZSYNCOBJECT SET ZOPENINGBALANCE=NULL WHERE Z_PK=1",
        "UPDATE ZSYNCOBJECT SET ZARCHIVED=NULL WHERE Z_PK=1",
        "UPDATE ZSYNCOBJECT SET ZACCOUNT1=999 WHERE Z_PK=300",
        "UPDATE ZSYNCOBJECT SET ZDISABLEEXECUTION=NULL WHERE Z_PK=300",
        "UPDATE ZSYNCOBJECT SET ZCATEGORY2=200 WHERE Z_PK=300",
        "UPDATE ZACCOUNTBUDGETLINK SET ZACCOUNT=999 WHERE ZBUDGET=400",
        "UPDATE ZSYNCOBJECT SET ZCURRENCYNAME=NULL WHERE Z_PK=400",
    ],
)
async def test_account_schedule_budget_uncertainties(synthetic, sql):
    mutate(synthetic[0], sql)
    manager = DatabaseManager(str(synthetic[0]))
    try:
        await manager.initialize()
        if "ZOPENINGBALANCE" in sql:
            account = await AccountService(manager).get_account("1")
            assert account.calculated_balance is None
            assert any("null" in warning for warning in account.warnings)
        elif "ZARCHIVED" in sql:
            with pytest.raises(MoneyWizError):
                await AccountService(manager).list_accounts()
        elif "ZACCOUNT1" in sql or "ZDISABLEEXECUTION" in sql or "300" in sql:
            with pytest.raises(MoneyWizError):
                await ScheduledTransactionService(manager).get_scheduled_transactions()
        else:
            with pytest.raises(MoneyWizError):
                await BudgetService(manager).get_budgets()
    finally:
        await manager.close()


async def test_partial_validation_report_keeps_errors(synthetic):
    mutate(synthetic[0], "UPDATE ZSYNCOBJECT SET ZCURRENCYNAME=NULL WHERE Z_PK=400")
    report = await reconcile(str(synthetic[0]), "2026-09-01", "2026-10-01")
    assert report["errors"]["budgets"]["code"] == "UNSUPPORTED_SCHEMA"
    assert report["budget_count"] == 2
    assert report["validation_status"] == "incomplete_explicit_errors"
    assert not report["ui_reconciliation_completed"]


async def test_missing_relationship_with_no_transactions_is_still_error(synthetic):
    mutate(synthetic[0], "DELETE FROM ZSYNCOBJECT WHERE ZACCOUNT2 IS NOT NULL")
    mutate(synthetic[0], "DROP TABLE ZCATEGORYASSIGMENT")
    manager = DatabaseManager(str(synthetic[0]))
    try:
        await manager.initialize()
        with pytest.raises(MoneyWizError, match="Missing table"):
            await TransactionService(manager).get_transactions(PERIOD)
    finally:
        await manager.close()


async def test_optional_tags_absent_without_relationship_is_visible(synthetic):
    path, mapping = synthetic
    for owner in ("Transaction", "ScheduledTransactionHandler"):
        mutate(path, f"DROP TABLE Z_{mapping[owner]}TAGS")
    mutate(path, "DELETE FROM ZSYNCOBJECT WHERE Z_ENT=?", (mapping["Tag"],))
    mutate(path, "DELETE FROM Z_PRIMARYKEY WHERE Z_NAME='Tag'")
    manager = DatabaseManager(str(path))
    try:
        await manager.initialize()
        assert "Tag" in manager.schema.diagnostics()["missing_optional_entities"]
        result = await TransactionService(manager).get_transactions(PERIOD)
        assert all(not t.tags for t in result.items)
    finally:
        await manager.close()


@pytest.mark.parametrize("name", ["", "\x00evil"])
def test_invalid_identifiers_fail(name):
    with pytest.raises(MoneyWizError):
        quote_identifier(name)


@pytest.mark.parametrize(
    ("table", "column"), [("Z_PRIMARYKEY", "Z_NAME"), ("ZSYNCOBJECT", "Z_ENT")]
)
async def test_required_table_columns(synthetic, table, column):
    mutate(synthetic[0], f"ALTER TABLE {table} RENAME COLUMN {column} TO unsupported")
    with pytest.raises(MoneyWizError, match="Missing columns"):
        await DatabaseManager(str(synthetic[0])).initialize()


async def test_no_classification_or_filters_sql_injection(db):
    with pytest.raises(MoneyWizError):
        await TransactionService(db).get_transactions(
            PERIOD, categories=["Food' OR 1=1--"]
        )
    with pytest.raises(MoneyWizError):
        await AccountService(db).get_account("1' OR 1=1--")
    assert len(await AccountService(db).rows()) == 4


async def test_multiple_assignment_aliases_deduplicated(synthetic):
    mutate(
        synthetic[0],
        "UPDATE ZCATEGORYASSIGMENT SET Z31_SCHEDULEDTRANSACITION=300 WHERE ZSCHEDULEDTRANSACITION=300",
    )
    manager = DatabaseManager(str(synthetic[0]))
    try:
        await manager.initialize()
        assert (
            len(
                (
                    await ScheduledTransactionService(
                        manager
                    ).get_scheduled_transactions()
                )[0].categories
            )
            == 1
        )
    finally:
        await manager.close()


@pytest.mark.parametrize("value", [None, "not a timestamp", 1e300])
async def test_malformed_dates_cannot_disappear_behind_filters(synthetic, value):
    mutate(synthetic[0], "UPDATE ZSYNCOBJECT SET ZDATE1=? WHERE Z_PK=100", (value,))
    manager = DatabaseManager(str(synthetic[0]))
    try:
        await manager.initialize()
        with pytest.raises(MoneyWizError, match="interval filtering incomplete"):
            await TransactionService(manager).get_transactions(PERIOD)
    finally:
        await manager.close()


async def test_identical_leaf_names_remain_distinct(synthetic):
    path, mapping = synthetic
    mutate(
        path,
        "INSERT INTO ZSYNCOBJECT(Z_PK,Z_ENT,ZNAME2,ZPARENTCATEGORY) VALUES(203,?,'Groceries',NULL)",
        (mapping["Category"],),
    )
    mutate(path, "UPDATE ZCATEGORYASSIGMENT SET ZCATEGORY=203 WHERE ZTRANSACTION=103")
    manager = DatabaseManager(str(path))
    try:
        await manager.initialize()
        result = await TransactionService(manager).summarize_cashflow(PERIOD)
        euro = [
            r
            for r in result["expense_categories"].items
            if r["money"].currency == "EUR"
        ]
        assert {r["category"].id for r in euro} == {"201", "203"}
    finally:
        await manager.close()


async def test_generated_scheduled_assignment_column_is_remapped(synthetic):
    path, mapping = synthetic
    mutate(
        path,
        f"ALTER TABLE ZCATEGORYASSIGMENT RENAME COLUMN Z31_SCHEDULEDTRANSACITION TO Z{mapping['ScheduledTransactionHandler']}_SCHEDULEDTRANSACITION",
    )
    mutate(
        path,
        f"UPDATE ZCATEGORYASSIGMENT SET Z{mapping['ScheduledTransactionHandler']}_SCHEDULEDTRANSACITION=ZSCHEDULEDTRANSACITION, ZSCHEDULEDTRANSACITION=NULL",
    )
    manager = DatabaseManager(str(path))
    try:
        await manager.initialize()
        assert (
            await ScheduledTransactionService(manager).get_scheduled_transactions()
        )[0].categories[0].name == "Salary"
    finally:
        await manager.close()


async def test_empty_unhandled_entity_definition_does_not_hide_data(synthetic):
    mutate(
        synthetic[0],
        "INSERT INTO Z_PRIMARYKEY(Z_ENT,Z_NAME,Z_SUPER) VALUES(999,'InvestmentTransaction',?)",
        (synthetic[1]["Transaction"],),
    )
    manager = DatabaseManager(str(synthetic[0]))
    try:
        await manager.initialize()
        assert (
            await TransactionService(manager).get_transactions(PERIOD)
        ).matched_count == 14
    finally:
        await manager.close()
    mutate(synthetic[0], "UPDATE ZSYNCOBJECT SET Z_ENT=999 WHERE Z_PK=100")
    with pytest.raises(MoneyWizError, match="Unrecognized"):
        await manager.initialize()


def test_writable_constructor_options_removed(synthetic):
    with pytest.raises(TypeError):
        DatabaseManager(str(synthetic[0]), read_only=False)
    with pytest.raises(TypeError):
        Config(str(synthetic[0]), read_only=False)
