"""Exact decimal money, serialized as strings with explicit currency."""

from decimal import Decimal, InvalidOperation, localcontext
import re

from pydantic import BaseModel, ConfigDict, field_serializer

from moneywiz_mcp_server.errors import MoneyWizError


def decimal_value(value: object) -> Decimal:
    try:
        result = Decimal(str(value))
        exponent = result.as_tuple().exponent
        if (
            not result.is_finite()
            or not isinstance(exponent, int)
            or len(result.as_tuple().digits) > 100
            or abs(exponent) > 100
        ):
            raise ValueError
        return result
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise MoneyWizError(
            "DATA_INTEGRITY", "Missing or invalid monetary value"
        ) from exc


def exact_add(left: Decimal, right: Decimal) -> Decimal:
    with localcontext() as context:
        first, second = left.as_tuple(), right.as_tuple()
        if not isinstance(first.exponent, int) or not isinstance(second.exponent, int):
            raise MoneyWizError("DATA_INTEGRITY", "Non-finite decimal calculation")
        scale = min(first.exponent, second.exponent)
        context.prec = (
            max(
                len(first.digits) + first.exponent - scale,
                len(second.digits) + second.exponent - scale,
            )
            + 1
        )
        return left + right


def currency_code(value: object) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Z]{3}", value):
        raise MoneyWizError("DATA_INTEGRITY", "Missing or invalid currency code")
    return value


class Money(BaseModel):
    model_config = ConfigDict(frozen=True)
    amount: Decimal
    currency: str

    @field_serializer("amount")
    def serialize_amount(self, value: Decimal) -> str:
        return format(value, "f")

    @classmethod
    def from_raw(cls, value: object, currency: object) -> "Money":
        return cls(amount=decimal_value(value), currency=currency_code(currency))
