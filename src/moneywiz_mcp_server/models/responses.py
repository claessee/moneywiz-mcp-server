"""Structured factual output; every list includes completeness metadata."""

from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel

from moneywiz_mcp_server.utils.date_utils import Interval

from .currency_types import Money

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    matched_count: int
    returned_count: int
    limit: int
    offset: int
    truncated: bool
    next_offset: int | None
    warnings: list[str] = []


def page(
    items: list[T],
    count: int,
    limit: int,
    offset: int,
    warnings: list[str] | None = None,
) -> Page[T]:
    more = offset + len(items) < count
    return Page(
        items=items,
        matched_count=count,
        returned_count=len(items),
        limit=limit,
        offset=offset,
        truncated=more or offset > 0,
        next_offset=offset + len(items) if more else None,
        warnings=warnings or [],
    )


class Category(BaseModel):
    id: str
    name: str
    parent_id: str | None
    hierarchy: list[str]


class Account(BaseModel):
    id: str
    name: str
    type: str
    currency: str
    archived: bool
    calculated_balance: Money | None
    balance_status: str = "provisional_unreconciled"
    balance_components: dict[str, Any]
    warnings: list[str]


class Transaction(BaseModel):
    id: str
    account_id: str
    transaction_type: str
    date: str
    money: Money
    description: str | None
    notes: str | None
    payee: str | None
    categories: list[Category]
    tags: list[str]
    reconciled: bool


class ScheduledTransaction(BaseModel):
    id: str
    transaction_type: str
    account_id: str | None
    money: Money
    next_execution: str
    disabled: bool
    repeatable: bool
    description: str | None
    payee: str | None
    categories: list[Category]
    tags: list[str]
    recurrence_fields: dict[str, Any]
    warnings: list[str] = [
        "Recurrence fields are stored values; future executions are not projected"
    ]


class Budget(BaseModel):
    id: str
    categories: list[Category]
    account_ids: list[str]
    stored_monetary_fields: dict[str, Money | None]
    duration_fields: dict[str, Any]
    warnings: list[str] = [
        "Budget limit/rollover/spending semantics require reconciliation; no inferred budget status"
    ]


class DuePayment(BaseModel):
    schedule_id: str
    transaction_type: Literal["withdraw", "transfer"]
    account_id: str | None
    account_name: str | None
    due_at: str
    due_date: str
    money: Money
    payee: str | None
    description: str | None
    basis: Literal["stored_next_execution", "projected"]
    status: Literal["overdue", "scheduled", "projected"]
    in_requested_interval: bool


class ProjectionIssue(BaseModel):
    schedule_id: str
    reason: str


class DueBillsResult(BaseModel):
    interval: Interval
    as_of: str
    scope: Literal["remaining_scheduled_payments"] = "remaining_scheduled_payments"
    page: Page[DuePayment]
    unresolved_schedules: Page[ProjectionIssue]
    projection_complete: bool
    totals_complete: bool
    totals: dict[str, list[Money]]
    warnings: list[str]
