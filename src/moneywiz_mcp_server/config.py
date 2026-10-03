"""Exact-path configuration and bounded, validated macOS discovery."""

from dataclasses import dataclass
import os
from pathlib import Path
import sqlite3

from .errors import MoneyWizError


def validate_path(value: str | Path) -> Path:
    path = Path(value).expanduser().absolute()
    name = path.name.lower()
    if name.endswith(("-wal", "-shm", "-journal", "_shared.sqlite")):
        raise MoneyWizError(
            "INVALID_DATABASE", "SQLite sidecars and shared stores are rejected"
        )
    if not path.is_file() or not os.access(path, os.R_OK):
        raise MoneyWizError(
            "INVALID_DATABASE", "Database must be a regular readable file"
        )
    if path.stat().st_size == 0:
        raise MoneyWizError("INVALID_DATABASE", "Database file is empty")
    # resolve symlinks as well: alias names cannot bypass the rejected-file policy.
    resolved = path.resolve()
    if resolved != path:
        return validate_path(resolved)
    return resolved


def discovery_roots(home: Path) -> list[Path]:
    containers = (
        "com.moneywiz.mac",
        "com.moneywiz.personalfinance",
        "com.moneywiz.personalfinance-setapp",
    )
    return [
        home / "Library/Containers" / c / "Data" / sub
        for c in containers
        for sub in ("Library/Application Support", "Documents")
    ] + [
        home / "Library/Application Support/MoneyWiz",
        home / "Library/Application Support/SilverWiz/MoneyWiz 2",
    ]


@dataclass(frozen=True)
class Config:
    database_path: str
    max_results: int = 500

    @classmethod
    async def from_env(cls) -> "Config":
        # Explicit env only: no searching ancestors or unexpected .env files.
        if os.getenv("MONEYWIZ_READ_ONLY", "true").lower() != "true":
            raise MoneyWizError(
                "INVALID_CONFIG", "Writable configuration is not supported"
            )
        path = os.getenv("MONEYWIZ_DB_PATH")
        if not path:
            if os.getenv("MONEYWIZ_AUTO_DISCOVER", "false").lower() != "true":
                raise MoneyWizError(
                    "INVALID_CONFIG",
                    "Set the exact MONEYWIZ_DB_PATH; discovery requires explicit opt-in",
                )
            path = await cls.find_database(discovery_roots(Path.home()))
        try:
            maximum = int(os.getenv("MAX_RESULTS", "500"))
        except ValueError as exc:
            raise MoneyWizError(
                "INVALID_CONFIG", "MAX_RESULTS must be an integer"
            ) from exc
        if not 1 <= maximum <= 500:
            raise MoneyWizError(
                "INVALID_CONFIG", "MAX_RESULTS must be between 1 and 500"
            )
        return cls(str(validate_path(path)), maximum)

    @staticmethod
    async def find_database(roots: list[Path]) -> str:
        from .database.connection import DatabaseManager
        from .database.schema import ACCOUNT_TYPES

        valid: set[Path] = set()
        for root in roots:
            if not root.is_dir():
                continue
            for candidate in sorted(root.rglob("*")):
                if candidate.suffix.lower() not in (".sqlite", ".sqlite3", ".db"):
                    continue
                db = DatabaseManager(str(candidate))
                try:
                    await db.initialize()
                    # Empty financial stores cannot be auto-selected, even under aliases.
                    ids = list(db.schema.family(ACCOUNT_TYPES))
                    count = await db.execute_query(
                        "SELECT COUNT(*) AS n FROM ZSYNCOBJECT WHERE Z_ENT IN ("  # nosec B608
                        + ",".join("?" for _ in ids)
                        + ")",
                        tuple(ids),
                    )
                    if count[0]["n"]:
                        valid.add(db.db_path)
                except (MoneyWizError, OSError, sqlite3.Error):
                    pass  # Rejected candidates are never returned as plausible stores.
                finally:
                    await db.close()
        if len(valid) != 1:
            raise MoneyWizError(
                "AMBIGUOUS_DATABASE" if valid else "DATABASE_NOT_FOUND",
                "Discovery requires exactly one validated nonempty MoneyWiz store; set MONEYWIZ_DB_PATH",
            )
        return str(next(iter(valid)))
