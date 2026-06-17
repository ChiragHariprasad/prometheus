import uuid
from typing import Any, Generic, TypeVar

from pydantic import BaseModel
from sqlalchemy import func, select, or_, and_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

T = TypeVar("T")


class AsyncRepository(Generic[T]):
    def __init__(self, model: type[T], session: AsyncSession):
        self.model = model
        self.session = session

    def _apply_organization_scope(self, stmt: Select, organization_id: uuid.UUID | None = None) -> Select:
        if organization_id is not None and hasattr(self.model, "organization_id"):
            stmt = stmt.where(self.model.organization_id == organization_id)
        return stmt

    def _apply_filters(self, stmt: Select, filters: dict[str, Any] | None) -> Select:
        if not filters:
            return stmt
        for key, value in filters.items():
            if hasattr(self.model, key):
                if value is None:
                    stmt = stmt.where(getattr(self.model, key).is_(None))
                elif isinstance(value, list):
                    stmt = stmt.where(getattr(self.model, key).in_(value))
                elif isinstance(value, dict):
                    op = value.get("op", "eq")
                    val = value.get("value")
                    col = getattr(self.model, key)
                    if op == "eq":
                        stmt = stmt.where(col == val)
                    elif op == "ne":
                        stmt = stmt.where(col != val)
                    elif op == "gt":
                        stmt = stmt.where(col > val)
                    elif op == "gte":
                        stmt = stmt.where(col >= val)
                    elif op == "lt":
                        stmt = stmt.where(col < val)
                    elif op == "lte":
                        stmt = stmt.where(col <= val)
                    elif op == "like":
                        stmt = stmt.where(col.like(val))
                    elif op == "ilike":
                        stmt = stmt.where(col.ilike(val))
                    elif op == "in":
                        stmt = stmt.where(col.in_(val))
                    elif op == "not_in":
                        stmt = stmt.where(col.notin_(val))
                    elif op == "is_null":
                        stmt = stmt.where(col.is_(None))
                    elif op == "is_not_null":
                        stmt = stmt.where(col.isnot(None))
                else:
                    stmt = stmt.where(getattr(self.model, key) == value)
        return stmt

    def _apply_sorts(self, stmt: Select, sorts: list[dict[str, str]] | None) -> Select:
        if not sorts:
            return stmt
        for sort in sorts:
            field = sort.get("field", "created_at")
            direction = sort.get("direction", "desc")
            if hasattr(self.model, field):
                col = getattr(self.model, field)
                stmt = stmt.order_by(col.desc() if direction.lower() == "desc" else col.asc())
        return stmt

    async def get(self, id: uuid.UUID, organization_id: uuid.UUID | None = None) -> T | None:
        stmt = select(self.model).where(self.model.id == id)
        stmt = self._apply_organization_scope(stmt, organization_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: dict[str, Any] | None = None,
        sorts: list[dict[str, str]] | None = None,
        organization_id: uuid.UUID | None = None,
    ) -> tuple[list[T], int]:
        count_stmt = select(func.count()).select_from(self.model)
        count_stmt = self._apply_organization_scope(count_stmt, organization_id)
        count_stmt = self._apply_filters(count_stmt, filters)
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar() or 0

        list_stmt = select(self.model)
        list_stmt = self._apply_organization_scope(list_stmt, organization_id)
        list_stmt = self._apply_filters(list_stmt, filters)
        list_stmt = self._apply_sorts(list_stmt, sorts)
        list_stmt = list_stmt.offset(skip).limit(limit)
        result = await self.session.execute(list_stmt)
        items = list(result.scalars().all())

        return items, total

    async def create(self, obj_in: dict | BaseModel, organization_id: uuid.UUID | None = None) -> T:
        if isinstance(obj_in, BaseModel):
            data = obj_in.model_dump(exclude_unset=True)
        else:
            data = dict(obj_in)
        if organization_id is not None and hasattr(self.model, "organization_id"):
            data.setdefault("organization_id", organization_id)
        db_obj = self.model(**data)
        self.session.add(db_obj)
        await self.session.flush()
        await self.session.refresh(db_obj)
        return db_obj

    async def update(self, id: uuid.UUID, obj_in: dict | BaseModel, organization_id: uuid.UUID | None = None) -> T | None:
        db_obj = await self.get(id, organization_id)
        if not db_obj:
            return None
        if isinstance(obj_in, BaseModel):
            data = obj_in.model_dump(exclude_unset=True)
        else:
            data = dict(obj_in)
        for field, value in data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        await self.session.flush()
        await self.session.refresh(db_obj)
        return db_obj

    async def delete(self, id: uuid.UUID, soft: bool = True, organization_id: uuid.UUID | None = None) -> bool:
        db_obj = await self.get(id, organization_id)
        if not db_obj:
            return False
        if soft and hasattr(db_obj, "is_active"):
            db_obj.is_active = False
            await self.session.flush()
        else:
            await self.session.delete(db_obj)
            await self.session.flush()
        return True
