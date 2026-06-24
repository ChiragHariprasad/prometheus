import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.repositories.base import AsyncRepository


class NotificationRepository(AsyncRepository[Notification]):
    def __init__(self, session: AsyncSession):
        super().__init__(Notification, session)

    async def get_by_customer(
        self, customer_id: uuid.UUID, organization_id: uuid.UUID, skip: int = 0, limit: int = 50
    ) -> tuple[list[Notification], int]:
        count_stmt = select(func.count()).where(
            Notification.customer_id == customer_id,
            Notification.organization_id == organization_id,
        )
        total = (await self.session.execute(count_stmt)).scalar() or 0

        stmt = (
            select(Notification)
            .where(
                Notification.customer_id == customer_id,
                Notification.organization_id == organization_id,
            )
            .order_by(Notification.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_unread_count(self, customer_id: uuid.UUID, organization_id: uuid.UUID) -> int:
        stmt = select(func.count()).where(
            Notification.customer_id == customer_id,
            Notification.organization_id == organization_id,
            Notification.status == "sent",
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def mark_read(self, notification_id: uuid.UUID, organization_id: uuid.UUID) -> bool:
        stmt = select(Notification).where(
            Notification.id == notification_id,
            Notification.organization_id == organization_id,
        )
        result = await self.session.execute(stmt)
        notification = result.scalar_one_or_none()
        if not notification:
            return False
        notification.read_at = datetime.now(timezone.utc)
        notification.status = "read"
        await self.session.flush()
        return True

    async def mark_all_read(self, customer_id: uuid.UUID, organization_id: uuid.UUID) -> int:
        stmt = select(Notification).where(
            Notification.customer_id == customer_id,
            Notification.organization_id == organization_id,
            Notification.status == "sent",
        )
        result = await self.session.execute(stmt)
        notifications = list(result.scalars().all())
        now = datetime.now(timezone.utc)
        for n in notifications:
            n.read_at = now
            n.status = "read"
        await self.session.flush()
        return len(notifications)

    async def get_pending(self, organization_id: uuid.UUID, limit: int = 100) -> list[Notification]:
        stmt = (
            select(Notification)
            .where(
                Notification.organization_id == organization_id,
                Notification.status == "pending",
            )
            .order_by(Notification.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
