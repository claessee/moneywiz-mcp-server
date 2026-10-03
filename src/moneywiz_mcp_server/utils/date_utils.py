"""ISO-only, timezone-aware, start-inclusive/end-exclusive intervals."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel

from moneywiz_mcp_server.errors import MoneyWizError

EPOCH = datetime(2001, 1, 1, tzinfo=timezone.utc)


class Interval(BaseModel):
    start: datetime
    end: datetime
    timezone: str
    start_inclusive: bool = True
    end_exclusive: bool = True


def parse_iso(value: str, zone: str) -> datetime:
    try:
        tz = ZoneInfo(zone)
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            return datetime.fromisoformat(value).replace(tzinfo=tz)
        if not re.match(r"^\d{4}-\d{2}-\d{2}T", value):
            raise ValueError
        if value.endswith("Z"):
            value = f"{value[:-1]}+00:00"
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            raise ValueError
        return parsed.astimezone(tz)
    except (ValueError, ZoneInfoNotFoundError) as exc:
        raise MoneyWizError(
            "INVALID_PARAMETER",
            "Use YYYY-MM-DD or an offset-aware ISO datetime and valid IANA timezone",
        ) from exc


def interval(start: str, end: str, zone: str = "Europe/Lisbon") -> Interval:
    first, last = parse_iso(start, zone), parse_iso(end, zone)
    if first.astimezone(timezone.utc) >= last.astimezone(timezone.utc):
        raise MoneyWizError("INVALID_PARAMETER", "Start must precede exclusive end")
    return Interval(start=first, end=last, timezone=zone)


def datetime_to_core_data_timestamp(value: datetime) -> float:
    if value.tzinfo is None:
        raise MoneyWizError("INVALID_PARAMETER", "Datetime must include timezone")
    return (value.astimezone(timezone.utc) - EPOCH).total_seconds()


def core_data_timestamp_to_datetime(value: object) -> datetime:
    try:
        decimal = Decimal(str(value))
        if not decimal.is_finite():
            raise ValueError
        # Dates are not money; SQLite NSDate timestamps have microsecond resolution here.
        return EPOCH + timedelta(seconds=float(decimal))
    except (ValueError, OverflowError, ArithmeticError) as exc:
        raise MoneyWizError(
            "DATA_INTEGRITY", "Missing or invalid Core Data timestamp"
        ) from exc
