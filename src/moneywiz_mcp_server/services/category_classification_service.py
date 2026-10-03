"""Factual relationship resolution; no category importance/type heuristics."""

from typing import Any

from moneywiz_mcp_server.database.connection import DatabaseManager
from moneywiz_mcp_server.errors import MoneyWizError
from moneywiz_mcp_server.models.responses import Category


def required_name(row: dict[str, Any], fields: tuple[str, ...]) -> str:
    values = {
        str(row[f]) for f in fields if isinstance(row.get(f), str) and row[f].strip()
    }
    if len(values) != 1:
        raise MoneyWizError(
            "DATA_INTEGRITY", "Missing or conflicting classification name fields"
        )
    return next(iter(values))


class CategoryClassificationService:
    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db = db_manager
        self._rows: dict[str, dict[int, dict[str, Any]]] = {}

    async def rows(self, entity: str) -> dict[int, dict[str, Any]]:
        if entity not in self._rows:
            entity_id = self.db.schema.entity(entity)
            self._rows[entity] = {
                r["Z_PK"]: r
                for r in await self.db.execute_query(
                    "SELECT * FROM ZSYNCOBJECT WHERE Z_ENT = ? ORDER BY Z_PK",
                    (entity_id,),
                )
            }
        return self._rows[entity]

    async def reference(self, entity: str, key: object) -> dict[str, Any]:
        records = await self.rows(entity)
        if not isinstance(key, int) or key not in records:
            raise MoneyWizError(
                "DATA_INTEGRITY", "Dangling or invalid " + entity + " reference"
            )
        return records[key]

    async def category(self, key: int) -> Category:
        self.db.schema.require_columns("ZSYNCOBJECT", "ZNAME2", "ZPARENTCATEGORY")
        leaf = await self.reference("Category", key)
        hierarchy: list[str] = []
        visited: set[int] = set()
        current = key
        while current:
            if current in visited:
                raise MoneyWizError("DATA_INTEGRITY", "Cyclic category hierarchy")
            visited.add(current)
            row = await self.reference("Category", current)
            hierarchy.insert(0, required_name(row, ("ZNAME2",)))
            parent = row["ZPARENTCATEGORY"]
            if parent is not None and not isinstance(parent, int):
                raise MoneyWizError("DATA_INTEGRITY", "Invalid category parent")
            current = parent or 0
        return Category(
            id=str(key),
            name=hierarchy[-1],
            parent_id=str(leaf["ZPARENTCATEGORY"]) if leaf["ZPARENTCATEGORY"] else None,
            hierarchy=hierarchy,
        )

    async def categories_for(self, owner: str, key: int) -> list[Category]:
        fields = self.db.schema.category_links(owner)
        where = " OR ".join(
            self.db.schema.identifier("ZCATEGORYASSIGMENT", c) + " = ?" for c in fields
        )
        rows = await self.db.execute_query(
            "SELECT DISTINCT ZCATEGORY FROM ZCATEGORYASSIGMENT WHERE "  # nosec B608
            + where
            + " ORDER BY ZCATEGORY",
            tuple(key for _ in fields),
        )
        return [await self.category(r["ZCATEGORY"]) for r in rows]

    async def payee(self, key: object) -> str | None:
        if key is None or key == 0:
            return None
        return required_name(
            await self.reference("Payee", key), ("ZNAME5", "ZNAME2", "ZNAME")
        )

    async def tags_for(self, owner: str, key: int) -> list[str]:
        if "Tag" not in self.db.schema.entities:
            if any("TAGS" in t for t in self.db.schema.tables):
                raise MoneyWizError(
                    "SCHEMA_ERROR", "Tag relationships exist without Tag mapping"
                )
            return []
        table, owner_column, tag_column = self.db.schema.tag_join(owner)
        rows = await self.db.execute_query(
            "SELECT "  # nosec B608
            + self.db.schema.identifier(table, tag_column)
            + " AS tag FROM "
            + self.db.schema.identifier(table)
            + " WHERE "
            + self.db.schema.identifier(table, owner_column)
            + " = ? ORDER BY "
            + self.db.schema.identifier(table, tag_column),
            (key,),
        )
        return sorted(
            {
                required_name(
                    await self.reference("Tag", r["tag"]), ("ZNAME6", "ZNAME2", "ZNAME")
                )
                for r in rows
            }
        )
