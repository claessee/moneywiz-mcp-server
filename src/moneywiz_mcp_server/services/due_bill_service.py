"""Remaining scheduled payments, with conservative, evidence-bounded projections."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from moneywiz_mcp_server.database.connection import DatabaseManager
from moneywiz_mcp_server.database.schema import SCHEDULED_TYPES
from moneywiz_mcp_server.errors import MoneyWizError
from moneywiz_mcp_server.models.currency_types import Money, exact_add
from moneywiz_mcp_server.models.responses import (
    DueBillsResult,
    DuePayment,
    ProjectionIssue,
    ScheduledTransaction,
    page,
)
from moneywiz_mcp_server.utils.date_utils import (
    Interval,
    core_data_timestamp_to_datetime,
)

from .account_service import AccountService
from .category_classification_service import required_name
from .scheduled_transaction_service import ScheduledTransactionService
from .transaction_service import validate_page

UTC = timezone.utc
MAX_INTERVAL_DAYS = 366
# Verified against local MoneyWiz recurrence forms; see docs/DUE_BILLS.md.
VERIFIED_MONTH_UNITS = {8: 1, 4: 12}


def utc(value: datetime) -> datetime:
    return value.astimezone(UTC)


def forecast(  # noqa: PLR0911 - explicit unsupported states are the financial boundary
    schedule: ScheduledTransaction, period: Interval, as_of: datetime
) -> tuple[list[datetime], str | None]:
    """Do not backcast, invent weekend/end rules, or infer settlement from forecasts."""
    if not schedule.repeatable:
        return [], None
    fields = schedule.recurrence_fields
    duration, unit = fields.get("ZDURATION1"), fields.get("ZDURATIONUNITS1")
    if (
        type(duration) is not int
        or duration <= 0
        or type(unit) is not int
        or unit not in VERIFIED_MONTH_UNITS
    ):
        return [], "Recurrence interval/unit has not been verified"
    zone = ZoneInfo(period.timezone)
    base = datetime.fromisoformat(schedule.next_execution).astimezone(zone)
    step = duration * VERIFIED_MONTH_UNITS[unit]
    if fields.get("ZWEEKENDSHANDLER") != 0 or any(
        fields.get(name) is not None
        for name in ("ZWEEKENDOPTION", "ZONWEEKENDSEXECUTE")
    ):
        return [], "Weekend adjustment semantics have not been verified"

    base_month = base.year * 12 + base.month - 1
    first_month = base_month + step
    year, month = divmod(first_month, 12)
    # Nothing can occur in an earlier month when weekends are explicitly unchanged.
    if year > 9999 or utc(datetime(year, month + 1, 1, tzinfo=zone)) >= utc(period.end):
        return [], None
    if utc(base) < utc(as_of):
        return [], "Overdue repeating schedule needs reconciliation before projection"
    if (
        "ZENDDATE" not in fields
        or fields["ZENDDATE"] is not None
        or fields.get("ZTOTALOCCURRENCES") is not None
    ):
        return [], "Finite or unavailable recurrence end semantics are unsupported"
    if fields.get("ZFIRSTEXECUTEDATE") is None:
        return [], "Original recurrence anchor is unavailable"
    anchor = core_data_timestamp_to_datetime(fields["ZFIRSTEXECUTEDATE"]).astimezone(
        zone
    )
    if (
        base.day > 28
        or anchor.day != base.day
        or (unit == 4 and anchor.month != base.month)
        or utc(anchor) > utc(base)
    ):
        return [], "Month-end, leap-day or changed recurrence anchor is unsupported"

    # Jump near the interval rather than walking decades of irrelevant occurrences.
    local_start = period.start.astimezone(zone)
    distance = local_start.year * 12 + local_start.month - 1 - base_month
    first_month = base_month + max(1, distance // step) * step
    year, month = divmod(first_month, 12)
    dates: list[datetime] = []
    while year <= 9999:
        candidate = base.replace(year=year, month=month + 1, fold=0)
        if utc(candidate) >= utc(period.end):
            break
        # Both nonexistent and ambiguous local wall times require independent proof.
        if candidate.replace(fold=1).utcoffset() != candidate.utcoffset() or utc(
            candidate
        ).astimezone(zone).replace(tzinfo=None) != candidate.replace(tzinfo=None):
            return dates, "DST transition wall-time semantics are unsupported"
        if utc(candidate) >= utc(period.start):
            dates.append(candidate)
        first_month += step
        year, month = divmod(first_month, 12)
    return dates, None


class DueBillService:
    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db = db_manager

    async def list_due_bills(
        self,
        period: Interval,
        as_of: datetime,
        account_ids: list[str] | None = None,
        include_overdue: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> DueBillsResult:
        validate_page(limit, offset)
        if utc(period.end) - utc(period.start) > timedelta(days=MAX_INTERVAL_DAYS):
            raise MoneyWizError(
                "INVALID_PARAMETER", "Due-bill interval exceeds 366 days"
            )
        accounts_service = AccountService(self.db)
        selected = (
            {str(pk) for pk in await accounts_service.resolve_ids(account_ids)}
            if account_ids is not None
            else None
        )
        accounts = await accounts_service.rows()
        schedules = await ScheduledTransactionService(
            self.db
        ).get_scheduled_transactions()
        zone = ZoneInfo(period.timezone)
        payments: list[DuePayment] = []
        issues: list[ProjectionIssue] = []
        totals: dict[str, dict[str, Decimal]] = {
            "bills_in_interval": {},
            "transfers_in_interval": {},
            "overdue_bills_before_interval": {},
            "overdue_transfers_before_interval": {},
        }

        def add(
            schedule: ScheduledTransaction, date: datetime, projected: bool
        ) -> None:
            inside = utc(period.start) <= utc(date) < utc(period.end)
            overdue = not projected and utc(date) < utc(as_of)
            if not inside and not (
                include_overdue and overdue and utc(date) < utc(period.start)
            ):
                return
            kind = "bills" if schedule.transaction_type == "withdraw" else "transfers"
            bucket = (
                kind + "_in_interval"
                if inside
                else "overdue_" + kind + "_before_interval"
            )
            currency = schedule.money.currency
            totals[bucket][currency] = exact_add(
                totals[bucket].get(currency, Decimal(0)),
                schedule.money.amount.copy_abs(),
            )
            account = (
                accounts.get(int(schedule.account_id)) if schedule.account_id else None
            )
            payments.append(
                DuePayment(
                    schedule_id=schedule.id,
                    transaction_type="withdraw" if kind == "bills" else "transfer",
                    account_id=schedule.account_id,
                    account_name=required_name(account, ("ZNAME",))
                    if account
                    else None,
                    due_at=date.astimezone(zone).isoformat(),
                    due_date=date.astimezone(zone).date().isoformat(),
                    money=schedule.money,
                    payee=schedule.payee,
                    description=schedule.description,
                    basis="projected" if projected else "stored_next_execution",
                    status="projected"
                    if projected
                    else "overdue"
                    if overdue
                    else "scheduled",
                    in_requested_interval=inside,
                )
            )

        for schedule in schedules:
            if (
                schedule.disabled
                or schedule.transaction_type == "deposit"
                or (selected is not None and schedule.account_id not in selected)
            ):
                continue
            next_date = datetime.fromisoformat(schedule.next_execution)
            if utc(next_date) >= utc(period.end):
                continue
            add(schedule, next_date, False)
            dates, reason = forecast(schedule, period, as_of)
            for date in dates:
                add(schedule, date, True)
            if reason:
                issues.append(ProjectionIssue(schedule_id=schedule.id, reason=reason))

        payments.sort(
            key=lambda p: (utc(datetime.fromisoformat(p.due_at)), int(p.schedule_id))
        )
        issues.sort(key=lambda issue: int(issue.schedule_id))
        missing = [
            name for name in SCHEDULED_TYPES if name not in self.db.schema.entities
        ]
        complete = not issues and not missing
        warnings = [
            "Remaining schedules only; paid/skipped historical occurrences are not reconstructed",
            "Stored dates are schedule state, not proof of bank settlement; projections use stored amounts",
            "Projection wall-time assumes the requested timezone matches MoneyWiz's scheduling timezone",
            "Totals cover all known occurrences before pagination; currencies remain separate",
        ]
        warnings.extend(
            "Scheduled entity absent from this model: " + name for name in missing
        )
        if not complete:
            warnings.append(
                "Incomplete forecast: totals are known amounts only, not complete commitments"
            )
        return DueBillsResult(
            interval=period,
            as_of=utc(as_of).isoformat(),
            page=page(payments[offset : offset + limit], len(payments), limit, offset),
            unresolved_schedules=page(
                issues[offset : offset + limit], len(issues), limit, offset
            ),
            projection_complete=complete,
            totals_complete=complete,
            totals={
                bucket: [
                    Money(amount=amount, currency=currency)
                    for currency, amount in sorted(values.items())
                ]
                for bucket, values in totals.items()
            },
            warnings=warnings,
        )
