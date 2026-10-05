"""Fabricated schedules only; adversarial dates, money, rules and completeness."""

from datetime import datetime, timezone
from decimal import Decimal, localcontext
import sqlite3
from zoneinfo import ZoneInfo

import pytest

from moneywiz_mcp_server.database.connection import DatabaseManager
from moneywiz_mcp_server.errors import MoneyWizError
from moneywiz_mcp_server.models.responses import ScheduledTransaction
from moneywiz_mcp_server.services.due_bill_service import DueBillService, forecast
from moneywiz_mcp_server.services.scheduled_transaction_service import (
    ScheduledTransactionService,
)
from moneywiz_mcp_server.utils.date_utils import (
    datetime_to_core_data_timestamp,
    interval,
)
from tests.conftest import make_database

REFERENCE = datetime(2026, 9, 1, tzinfo=timezone.utc)


@pytest.fixture
def db(synthetic):
    # Open a fresh snapshot only after each fabricated mutation has committed.
    return DatabaseManager(str(synthetic[0]))


def update(path, pk=301, **values):
    with sqlite3.connect(path) as conn:
        conn.execute(
            "UPDATE ZSYNCOBJECT SET "
            + ",".join(key + "=?" for key in values)
            + " WHERE Z_PK=?",
            (*values.values(), pk),
        )


async def result(db, start="2026-09-01", end="2026-10-01", **kwargs):
    await db.initialize()
    try:
        return await DueBillService(db).list_due_bills(
            interval(start, end, kwargs.pop("timezone", "UTC")),
            kwargs.pop("as_of", REFERENCE),
            **kwargs,
        )
    finally:
        await db.close()


async def schedules(db):
    await db.initialize()
    try:
        return await ScheduledTransactionService(db).get_scheduled_transactions()
    finally:
        await db.close()


async def test_week_and_month_include_next_date_only_once(db):
    week = await result(db, "2026-09-14", "2026-09-21", timezone="Europe/Lisbon")
    month = await result(db)
    assert week.projection_complete
    assert week.totals_complete
    assert week.page.matched_count == month.page.matched_count == 1
    payment = week.page.items[0]
    assert payment.schedule_id == "301"
    assert payment.account_name == "Fabricated account 1"
    assert payment.due_at == "2026-09-15T13:00:00+01:00"
    assert payment.status == "scheduled"
    assert payment.basis == "stored_next_execution"
    assert payment.money.amount == Decimal("-50")
    assert month.totals["bills_in_interval"][0].amount == 50
    assert month.totals["transfers_in_interval"] == []


async def test_monthly_projection_and_dst_preserve_local_wall_time(db):
    data = await result(
        db, "2026-10-01", "2026-12-01", timezone="Europe/Lisbon", include_overdue=False
    )
    assert data.projection_complete
    assert [p.due_at for p in data.page.items] == [
        "2026-10-15T13:00:00+01:00",
        "2026-11-15T13:00:00+00:00",
    ]
    assert {p.status for p in data.page.items} == {"projected"}
    assert data.totals["bills_in_interval"][0].amount == 100


async def test_yearly_and_multimonth_frequency(synthetic, db):
    update(synthetic[0], ZDURATIONUNITS1=4)
    annual = await result(db, "2027-09-01", "2027-10-01", include_overdue=False)
    assert [p.due_date for p in annual.page.items] == ["2027-09-15"]
    update(synthetic[0], ZDURATIONUNITS1=8, ZDURATION1=3)
    quarterly = await result(db, "2026-09-01", "2027-09-01")
    assert [p.due_date for p in quarterly.page.items] == [
        "2026-09-15",
        "2026-12-15",
        "2027-03-15",
        "2027-06-15",
    ]


async def test_date_boundaries_and_one_off(synthetic, db):
    update(
        synthetic[0],
        ZISREPEATABLE1=0,
        ZEXECUTEDATE=datetime_to_core_data_timestamp(
            datetime(2026, 9, 30, 23, 15, tzinfo=timezone.utc)
        ),
    )
    assert (await result(db)).page.items[0].due_date == "2026-09-30"
    data = await result(db, "2026-10-01", "2026-11-01", timezone="Europe/Lisbon")
    assert data.page.items[0].due_date == "2026-10-01"
    assert data.projection_complete
    excluded = await result(db, "2026-09-01", "2026-10-01", timezone="Europe/Lisbon")
    assert excluded.page.items == []


async def test_money_transfers_pagination_and_stable_order(synthetic, db):
    update(synthetic[0], ZAMOUNT="-0.10000000000000000000000000001")
    update(
        synthetic[0], pk=302, ZDISABLEEXECUTION=0, ZAMOUNT="-0.2", ZCURRENCYNAME3="USD"
    )
    with localcontext() as context:
        context.prec = 6
        first = await result(db, limit=1)
        second = await result(db, limit=1, offset=1)
    assert first.page.matched_count == 2
    assert first.page.next_offset == 1
    assert first.page.truncated
    assert second.page.next_offset is None
    assert second.page.truncated
    assert [first.page.items[0].schedule_id, second.page.items[0].schedule_id] == [
        "301",
        "302",
    ]
    assert first.totals == second.totals
    assert first.totals["bills_in_interval"][0].amount == Decimal(
        "0.10000000000000000000000000001"
    )
    assert first.totals["transfers_in_interval"][0].currency == "USD"
    assert first.totals["transfers_in_interval"][0].amount == Decimal("0.2")


async def test_overdue_is_stored_state_and_not_bank_settlement(synthetic, db):
    update(synthetic[0], ZISREPEATABLE1=0)
    as_of = datetime(2026, 10, 5, tzinfo=timezone.utc)
    data = await result(db, "2026-10-01", "2026-11-01", as_of=as_of)
    assert data.page.items[0].status == "overdue"
    assert not data.page.items[0].in_requested_interval
    assert data.totals["bills_in_interval"] == []
    assert data.totals["overdue_bills_before_interval"][0].amount == 50
    assert (
        await result(db, "2026-10-01", "2026-11-01", as_of=as_of, include_overdue=False)
    ).page.items == []
    inside = await result(db, as_of=as_of, include_overdue=False)
    assert inside.page.items[0].status == "overdue"
    assert inside.totals["bills_in_interval"][0].amount == 50


async def test_overdue_transfer_has_separate_total(synthetic, db):
    update(synthetic[0], pk=302, ZDISABLEEXECUTION=0)
    data = await result(
        db, "2026-10-01", "2026-11-01", as_of=datetime(2026, 10, 5, tzinfo=timezone.utc)
    )
    assert data.totals["overdue_transfers_before_interval"][0].amount == 10
    assert (
        not data.projection_complete
    )  # Overdue repeating bill cannot be forecast as paid.
    assert len(data.unresolved_schedules.items) == 1


async def test_filters_apply_to_payments_issues_and_totals(synthetic, db):
    update(synthetic[0], ZDURATIONUNITS1=999)
    selected = await result(db, account_ids=["account-1"])
    assert selected.page.matched_count == 1
    assert not selected.totals_complete
    for ids in ([], ["2"]):
        empty = await result(db, account_ids=ids)
        assert empty.page.matched_count == 0
        assert empty.unresolved_schedules.matched_count == 0
        assert empty.totals_complete
        assert all(not value for value in empty.totals.values())
    with pytest.raises(MoneyWizError, match="missing or ambiguous"):
        await result(db, account_ids=["missing"])


@pytest.mark.parametrize(
    ("values", "reason"),
    [
        ({"ZDURATIONUNITS1": 16}, "unit"),
        ({"ZDURATIONUNITS1": 8192}, "unit"),
        ({"ZDURATION1": 0}, "interval"),
        ({"ZDURATION1": -1}, "interval"),
        ({"ZWEEKENDSHANDLER": 1}, "Weekend"),
        ({"ZWEEKENDSHANDLER": None}, "Weekend"),
        ({"ZWEEKENDOPTION": 0}, "Weekend"),
        ({"ZONWEEKENDSEXECUTE": 0}, "Weekend"),
        ({"ZENDDATE": 0}, "end"),
        ({"ZTOTALOCCURRENCES": 4}, "end"),
        ({"ZFIRSTEXECUTEDATE": None}, "anchor"),
    ],
)
async def test_unsupported_rules_keep_known_date_but_never_claim_complete(
    synthetic, db, values, reason
):
    update(synthetic[0], **values)
    data = await result(db, "2026-09-01", "2026-11-01")
    assert data.page.matched_count == 1
    assert data.page.items[0].basis == "stored_next_execution"
    assert not data.projection_complete
    assert not data.totals_complete
    assert reason in data.unresolved_schedules.items[0].reason
    assert data.totals["bills_in_interval"][0].amount == 50
    assert any("Incomplete" in warning for warning in data.warnings)


async def test_unresolved_schedule_pagination(synthetic, db):
    update(synthetic[0], ZDURATIONUNITS1=999)
    update(
        synthetic[0], pk=302, ZDISABLEEXECUTION=0, ZISREPEATABLE1=1, ZDURATIONUNITS1=999
    )
    first = await result(db, limit=1)
    second = await result(db, limit=1, offset=1)
    assert first.unresolved_schedules.matched_count == 2
    assert first.unresolved_schedules.next_offset == 1
    assert [
        first.unresolved_schedules.items[0].schedule_id,
        second.unresolved_schedules.items[0].schedule_id,
    ] == ["301", "302"]


@pytest.mark.parametrize(
    ("base", "anchor", "unit"),
    [
        ("2026-09-30T12:00:00+00:00", "2025-09-30T12:00:00+00:00", 8),
        ("2026-02-28T12:00:00+00:00", "2024-02-29T12:00:00+00:00", 4),
        ("2026-09-15T12:00:00+00:00", "2026-09-16T12:00:00+00:00", 8),
        ("2026-09-15T12:00:00+00:00", "2025-10-15T12:00:00+00:00", 4),
    ],
)
async def test_anchor_uncertainties(synthetic, db, base, anchor, unit):
    update(
        synthetic[0],
        ZEXECUTEDATE=datetime_to_core_data_timestamp(datetime.fromisoformat(base)),
        ZFIRSTEXECUTEDATE=datetime_to_core_data_timestamp(
            datetime.fromisoformat(anchor)
        ),
        ZDURATIONUNITS1=unit,
    )
    schedule = next(s for s in await schedules(db) if s.id == "301")
    dates, reason = forecast(
        schedule,
        interval("2027-01-01", "2028-01-01"),
        datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    assert dates == []
    assert "anchor" in reason


@pytest.mark.parametrize(
    ("base", "start", "end"),
    [
        ("2026-02-08T02:30:00", "2026-02-01", "2026-04-01"),
        ("2026-10-01T01:30:00", "2026-10-01", "2026-12-01"),
    ],
)
async def test_dst_gap_and_fold_are_explicitly_unsupported(
    synthetic, db, base, start, end
):
    local = datetime.fromisoformat(base).replace(tzinfo=ZoneInfo("America/New_York"))
    update(
        synthetic[0],
        ZEXECUTEDATE=datetime_to_core_data_timestamp(local),
        ZFIRSTEXECUTEDATE=datetime_to_core_data_timestamp(local),
    )
    data = await result(
        db,
        start,
        end,
        timezone="America/New_York",
        as_of=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    assert data.page.matched_count == 1
    assert not data.projection_complete
    assert "DST" in data.unresolved_schedules.items[0].reason


async def test_missing_account_stays_null(synthetic, db):
    update(synthetic[0], ZACCOUNT1=None)
    payment = (await result(db)).page.items[0]
    assert payment.account_id is None
    assert payment.account_name is None


async def test_missing_handler_marks_completeness(synthetic, db):
    with sqlite3.connect(synthetic[0]) as conn:
        conn.execute("DELETE FROM ZSYNCOBJECT WHERE Z_PK=302")
        conn.execute(
            "DELETE FROM Z_PRIMARYKEY WHERE Z_NAME='ScheduledTransferTransactionHandler'"
        )
    # Schema is captured at initialize; reopen to observe the changed fabricated model.
    manager = DatabaseManager(str(synthetic[0]))
    try:
        data = await result(manager)
        assert not data.projection_complete
        assert any(
            "ScheduledTransferTransactionHandler" in warning
            for warning in data.warnings
        )
    finally:
        await manager.close()


@pytest.mark.parametrize("generation", [0, 1])
async def test_remapped_entities_and_read_only(tmp_path, generation):
    path = tmp_path / "fabricated.sqlite"
    make_database(path, generation=generation)
    before = path.read_bytes()
    manager = DatabaseManager(str(path))
    try:
        assert (await result(manager)).page.items[0].schedule_id == "301"
    finally:
        await manager.close()
    assert path.read_bytes() == before


async def test_bounded_interval_and_invalid_pagination(db):
    with pytest.raises(MoneyWizError, match="366 days"):
        await result(db, "2026-01-01", "2028-01-01")
    with pytest.raises(MoneyWizError):
        await result(db, limit=0)


async def test_far_future_query_jumps_to_interval(db):
    data = await result(db, "9000-10-01", "9000-11-01", include_overdue=False)
    assert data.projection_complete
    assert [p.due_date for p in data.page.items] == ["9000-10-15"]


async def test_forecast_missing_end_and_boolean_units(db):
    original = next(s for s in await schedules(db) if s.id == "301")
    period = interval("2026-09-01", "2026-11-01")
    for fields, reason in [
        (
            {k: v for k, v in original.recurrence_fields.items() if k != "ZENDDATE"},
            "end",
        ),
        ({**original.recurrence_fields, "ZDURATION1": True}, "interval"),
        ({**original.recurrence_fields, "ZDURATIONUNITS1": True}, "unit"),
    ]:
        schedule = ScheduledTransaction.model_validate(
            {**original.model_dump(), "recurrence_fields": fields}
        )
        assert reason in forecast(schedule, period, REFERENCE)[1]
