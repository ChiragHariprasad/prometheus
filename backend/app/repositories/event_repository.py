import uuid
from datetime import datetime, date
from typing import Any

from sqlalchemy import func, select, cast, Date
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.repositories.base import AsyncRepository


class EventRepository(AsyncRepository[Event]):
    def __init__(self, session: AsyncSession):
        super().__init__(Event, session)

    async def get_by_customer(
        self, customer_id: uuid.UUID, organization_id: uuid.UUID, skip: int = 0, limit: int = 50
    ) -> tuple[list[Event], int]:
        count_stmt = select(func.count()).where(
            Event.customer_id == customer_id,
            Event.organization_id == organization_id,
        )
        total = (await self.session.execute(count_stmt)).scalar() or 0

        stmt = (
            select(Event)
            .where(
                Event.customer_id == customer_id,
                Event.organization_id == organization_id,
            )
            .order_by(Event.event_timestamp.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_by_type(
        self, event_type: str, organization_id: uuid.UUID, skip: int = 0, limit: int = 50
    ) -> tuple[list[Event], int]:
        count_stmt = select(func.count()).where(
            Event.event_type == event_type,
            Event.organization_id == organization_id,
        )
        total = (await self.session.execute(count_stmt)).scalar() or 0

        stmt = (
            select(Event)
            .where(
                Event.event_type == event_type,
                Event.organization_id == organization_id,
            )
            .order_by(Event.event_timestamp.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_date_range(
        self, organization_id: uuid.UUID, start: date, end: date
    ) -> list[Event]:
        stmt = (
            select(Event)
            .where(
                Event.organization_id == organization_id,
                cast(Event.event_timestamp, Date) >= start,
                cast(Event.event_timestamp, Date) <= end,
            )
            .order_by(Event.event_timestamp.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_unprocessed(self, organization_id: uuid.UUID, limit: int = 100) -> list[Event]:
        stmt = (
            select(Event)
            .where(
                Event.organization_id == organization_id,
                Event.processed == False,
            )
            .order_by(Event.event_timestamp.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def mark_processed(self, event_id: uuid.UUID) -> None:
        event = await self.get(event_id)
        if event:
            event.processed = True
            await self.session.flush()
