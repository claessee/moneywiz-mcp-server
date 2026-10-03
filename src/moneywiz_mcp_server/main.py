"""Local stdio MCP v2 tools. No transport selection or writable capability."""

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from functools import wraps
import inspect
import json
import logging
import sys
from typing import Annotated, Any, Generic, TypeVar

from mcp.server import MCPServer
from mcp.server._otel import OpenTelemetryMiddleware
from mcp_types import ToolAnnotations
from pydantic import BaseModel, Field

from . import __version__
from .config import Config
from .database.connection import DatabaseManager
from .database.schema import SCHEDULED_TYPES
from .errors import MoneyWizError
from .models.responses import (
    Account,
    Budget,
    Category,
    Page,
    ScheduledTransaction,
    page,
)
from .services.account_service import AccountService
from .services.budget_service import BudgetService
from .services.category_classification_service import (
    CategoryClassificationService,
    required_name,
)
from .services.scheduled_transaction_service import ScheduledTransactionService
from .services.transaction_service import TransactionService, validate_page
from .utils.date_utils import interval

mcp = MCPServer(
    "moneywiz-read-only", version=__version__, log_level="ERROR", subscriptions=False
)
# Official SDK's documented opt-out recipe: remove its default tracing middleware.
mcp._lowlevel_server.middleware = [
    m
    for m in mcp._lowlevel_server.middleware
    if not isinstance(m, OpenTelemetryMiddleware)
]
READ_ONLY = ToolAnnotations(
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=False,
)
Limit = Annotated[int, Field(ge=1, le=500)]
Offset = Annotated[int, Field(ge=0, le=10_000_000)]
Identifier = Annotated[str, Field(min_length=1, max_length=256)]
Filters = Annotated[list[Identifier], Field(max_length=100)]
_config: Config | None = None
T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str
    message: str


class Reply(BaseModel, Generic[T]):
    data: T | None = None
    error: ErrorDetail | None = None


def guarded(
    function: Callable[..., Awaitable[T]],
) -> Callable[..., Awaitable[Reply[T]]]:
    @wraps(function)
    async def wrapper(*args: Any, **kwargs: Any) -> Reply[T]:
        try:
            return Reply(data=await function(*args, **kwargs))
        except MoneyWizError as exc:
            return Reply(error=ErrorDetail(**exc.as_dict()))
        except Exception:
            # No raw SQLite/Pydantic exception or tool arguments in routine logs.
            return Reply(
                error=ErrorDetail(
                    code="INTERNAL_ERROR",
                    message="Operation failed; inspect schema_info or local validation",
                )
            )

    # Tool schemas see the structured envelope, while preserving parameter signatures.
    wrapper.__annotations__ = {
        **function.__annotations__,
        "return": Reply.__class_getitem__(function.__annotations__.get("return", Any)),
    }
    # inspect.signature supports decorators that change the return envelope.
    wrapper.__signature__ = inspect.signature(function).replace(  # type: ignore[attr-defined]
        return_annotation=wrapper.__annotations__["return"]
    )
    return wrapper


@asynccontextmanager
async def database(limit: int | None = None) -> AsyncIterator[DatabaseManager]:
    config = _config or await Config.from_env()
    if limit is not None and limit > config.max_results:
        raise MoneyWizError(
            "INVALID_PARAMETER", "Requested limit exceeds configured MAX_RESULTS"
        )
    db = DatabaseManager(config.database_path)
    try:
        await db.initialize()
        yield db
    finally:
        await db.close()


def checked_limit(limit: int, offset: int) -> None:
    validate_page(limit, offset)
    if _config is not None and limit > _config.max_results:
        raise MoneyWizError(
            "INVALID_PARAMETER", "Requested limit exceeds configured MAX_RESULTS"
        )


@mcp.tool(annotations=READ_ONLY)
@guarded
async def server_status() -> dict[str, Any]:
    """Verify the configured local database. No account data or paths in this response."""
    async with database() as db:
        return {
            "version": __version__,
            "read_only": True,
            "sqlite_validated": True,
            "schema_validated": True,
            "transport": "stdio",
            "readiness": "READY FOR READ-ONLY RECONCILIATION",
            "warnings": db.schema.diagnostics()["warnings"],
        }


@mcp.tool(annotations=READ_ONLY)
@guarded
async def schema_info() -> dict[str, Any]:
    """Return observed Core Data entity/table/column mappings and unsupported features."""
    async with database() as db:
        return db.schema.diagnostics()


@mcp.tool(annotations=READ_ONLY)
@guarded
async def list_accounts(
    include_hidden: bool = False,
    account_type: str | None = None,
    limit: Limit = 100,
    offset: Offset = 0,
) -> Page[Account]:
    """List accounts with currency and provisional balance components; compare to MoneyWiz UI."""
    checked_limit(limit, offset)
    async with database(limit) as db:
        items = await AccountService(db).list_accounts(include_hidden, account_type)
        return page(items[offset : offset + limit], len(items), limit, offset)


@mcp.tool(annotations=READ_ONLY)
@guarded
async def get_account(account_id: Identifier) -> Account:
    """Get one account by returned ID or exact ZGID, with credit-card reconciliation diagnostics."""
    async with database() as db:
        return await AccountService(db).get_account(account_id)


@mcp.tool(annotations=READ_ONLY)
@guarded
async def search_transactions(
    start: Identifier,
    end: Identifier,
    timezone: str = "UTC",
    account_ids: Filters | None = None,
    categories: Filters | None = None,
    transaction_type: str | None = None,
    limit: Limit = 100,
    offset: Offset = 0,
) -> dict[str, Any]:
    """Search [start,end), YYYY-MM-DD or offset-aware ISO datetime. Types: deposit, withdraw, transfer_in, transfer_out, investment_buy/sell/exchange, refund, reconcile, transfer_budget. Category names include descendants; empty filters match nothing. Stable date DESC, ID DESC order; pagination metadata is mandatory."""
    checked_limit(limit, offset)
    period = interval(start, end, timezone)
    async with database(limit) as db:
        result = await TransactionService(db).get_transactions(
            period, account_ids, categories, transaction_type, limit, offset
        )
        return {
            "interval": period,
            "page": result,
            "filters_applied": {
                "account_ids": account_ids,
                "categories": categories,
                "transaction_type": transaction_type,
            },
        }


@mcp.tool(annotations=READ_ONLY)
@guarded
async def list_categories(limit: Limit = 100, offset: Offset = 0) -> Page[Category]:
    """List factual categories and full parent hierarchy; no inferred income/importance labels."""
    checked_limit(limit, offset)
    async with database(limit) as db:
        service = CategoryClassificationService(db)
        items = [await service.category(pk) for pk in await service.rows("Category")]
        return page(items[offset : offset + limit], len(items), limit, offset)


@mcp.tool(annotations=READ_ONLY)
@guarded
async def list_tags(limit: Limit = 100, offset: Offset = 0) -> Page[dict[str, str]]:
    """List stored tags; unsupported/missing entity schemas return explicit errors."""
    checked_limit(limit, offset)
    async with database(limit) as db:
        items = [
            {"id": str(pk), "name": required_name(row, ("ZNAME6", "ZNAME2", "ZNAME"))}
            for pk, row in (await CategoryClassificationService(db).rows("Tag")).items()
        ]
        return page(items[offset : offset + limit], len(items), limit, offset)


@mcp.tool(annotations=READ_ONLY)
@guarded
async def list_payees(limit: Limit = 100, offset: Offset = 0) -> Page[dict[str, str]]:
    """List factual payee records with bounded results."""
    checked_limit(limit, offset)
    async with database(limit) as db:
        items = [
            {"id": str(pk), "name": required_name(row, ("ZNAME5", "ZNAME2", "ZNAME"))}
            for pk, row in (
                await CategoryClassificationService(db).rows("Payee")
            ).items()
        ]
        return page(items[offset : offset + limit], len(items), limit, offset)


@mcp.tool(annotations=READ_ONLY)
@guarded
async def list_budgets(limit: Limit = 100, offset: Offset = 0) -> Page[Budget]:
    """List ALL budgets, including zero/negative amounts, and stored currency-labelled components. No guessed budget limit, rollover or spending status."""
    checked_limit(limit, offset)
    async with database(limit) as db:
        items = await BudgetService(db).get_budgets()
        return page(items[offset : offset + limit], len(items), limit, offset)


@mcp.tool(annotations=READ_ONLY)
@guarded
async def list_scheduled_transactions(
    limit: Limit = 100, offset: Offset = 0
) -> Page[ScheduledTransaction]:
    """List stored scheduled income/expense/transfer handlers, including disabled and one-off schedules. Date ASC, ID ASC order; no fabricated recurrence forecasts."""
    checked_limit(limit, offset)
    async with database(limit) as db:
        items = await ScheduledTransactionService(db).get_scheduled_transactions()
        missing = [name for name in SCHEDULED_TYPES if name not in db.schema.entities]
        return page(
            items[offset : offset + limit],
            len(items),
            limit,
            offset,
            ["Scheduled entity absent from this model: " + name for name in missing],
        )


@mcp.tool(annotations=READ_ONLY)
@guarded
async def summarize_cashflow(
    start: Identifier,
    end: Identifier,
    timezone: str = "UTC",
    account_ids: Filters | None = None,
) -> dict[str, Any]:
    """Stream ALL matching transactions over [start,end); exact per-currency signed deposits/withdrawals, separate transfer legs and other type sums. No FX, cross-currency ranking or advice. Split categories remain explicitly unallocated."""
    period = interval(start, end, timezone)
    async with database() as db:
        return await TransactionService(db).summarize_cashflow(period, account_ids)


def main() -> int:
    import asyncio

    try:
        global _config
        _config = asyncio.run(Config.from_env())
        mcp.run(transport="stdio")
        return 0
    except MoneyWizError as exc:
        print(json.dumps({"error": exc.as_dict()}), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 0
    except Exception:
        logging.getLogger(__name__).error("MoneyWiz server failed to start")
        return 1


def cli_main() -> None:
    sys.exit(main())
