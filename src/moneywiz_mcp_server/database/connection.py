"""Permanent read-only SQLite access with one consistent snapshot per operation."""

from collections.abc import AsyncIterator
from pathlib import Path
import sqlite3
from typing import Any

import aiosqlite

from moneywiz_mcp_server.config import validate_path
from moneywiz_mcp_server.errors import MoneyWizError

from .schema import Schema


def read_authorizer(
    action: int,
    arg1: str | None,
    arg2: str | None,
    _database: str | None,
    _trigger: str | None,
) -> int:
    if action in (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_RECURSIVE):
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_FUNCTION:
        return (
            sqlite3.SQLITE_DENY
            if (arg2 or "").lower() in ("load_extension", "writefile")
            else sqlite3.SQLITE_OK
        )
    if action == sqlite3.SQLITE_PRAGMA and (
        arg1 == "table_info" or (arg1 in ("query_only", "quick_check") and arg2 is None)
    ):
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_TRANSACTION and arg1 in ("BEGIN", "ROLLBACK"):
        return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


class DatabaseManager:
    def __init__(self, db_path: str) -> None:
        self.db_path = Path(db_path)
        self._connection: aiosqlite.Connection | None = None
        self._schema: Schema | None = None

    @property
    def schema(self) -> Schema:
        if self._schema is None:
            raise MoneyWizError(
                "DATABASE_NOT_INITIALIZED", "Initialize the database first"
            )
        return self._schema

    async def initialize(self) -> None:
        if self._connection is not None:
            raise MoneyWizError(
                "DATABASE_ALREADY_OPEN", "Database is already initialized"
            )
        self.db_path = validate_path(self.db_path)
        try:
            # as_uri escapes '?' and '#' in names; do not use immutable=1 (it ignores WAL).
            self._connection = await aiosqlite.connect(
                self.db_path.as_uri() + "?mode=ro", uri=True
            )
            self._connection.row_factory = aiosqlite.Row
            await self._connection.execute("PRAGMA query_only=ON")
            await self._connection.execute("PRAGMA trusted_schema=OFF")
            await self._connection.set_authorizer(read_authorizer)
            await self._connection.execute("BEGIN")
            async with self._connection.execute("PRAGMA quick_check") as cursor:
                checks = await cursor.fetchall()
                if [r[0] for r in checks] != ["ok"]:
                    raise MoneyWizError(
                        "INVALID_DATABASE", "SQLite integrity validation failed"
                    )
            self._schema = await Schema.inspect(self)
        except (sqlite3.Error, OSError) as exc:
            await self.close()
            raise MoneyWizError(
                "INVALID_DATABASE", "Unable to read a valid SQLite MoneyWiz store"
            ) from exc
        except BaseException:
            await self.close()
            raise

    async def close(self) -> None:
        if self._connection is not None:
            await self._connection.close()
        self._connection = None
        self._schema = None

    async def iter_query(
        self, query: str, params: tuple[Any, ...] = ()
    ) -> AsyncIterator[dict[str, Any]]:
        if self._connection is None:
            raise MoneyWizError(
                "DATABASE_NOT_INITIALIZED", "Initialize the database first"
            )
        if not query.lstrip().upper().startswith("SELECT "):
            raise MoneyWizError("READ_ONLY_VIOLATION", "Only SELECT is allowed")
        try:
            async with self._connection.execute(query, params) as cursor:
                while rows := await cursor.fetchmany(256):
                    for row in rows:
                        yield dict(row)
        except sqlite3.Error as exc:
            raise MoneyWizError(
                "QUERY_ERROR", "Read query failed; inspect schema_info"
            ) from exc

    async def execute_query(
        self, query: str, params: tuple[Any, ...] | None = None
    ) -> list[dict[str, Any]]:
        return [row async for row in self.iter_query(query, params or ())]
