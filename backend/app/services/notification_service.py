import uuid
from datetime import datetime, timezone

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.core.logging import logger
from app.models.notification import Notification


class NotificationService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_notification(
        self, org_id: uuid.UUID, customer_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None, type: str = "general",
        title: str = "", body: str | None = None,
        channel: str = "in_app", priority: int = 0,
        template_id: str | None = None, template_data: dict | None = None,
        campaign_id: uuid.UUID | None = None,
        scheduled_at: datetime | None = None,
    ) -> Notification:
        notification = Notification(
            organization_id=org_id,
            customer_id=customer_id,
            user_id=user_id,
            type=type,
            title=title,
            body=body,
            channel=channel,
            priority=priority,
            template_id=template_id,
            template_data=template_data,
            campaign_id=campaign_id,
            scheduled_at=scheduled_at,
        )
        self.session.add(notification)
        await self.session.flush()
        await self.session.refresh(notification)
        return notification

    async def get_notification(
        self, notification_id: uuid.UUID, org_id: uuid.UUID,
    ) -> Notification:
        result = await self.session.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.organization_id == org_id,
            )
        )
        notification = result.scalar_one_or_none()
        if not notification:
            raise NotFoundException("Notification", str(notification_id))
        return notification

    async def list_notifications(
        self, org_id: uuid.UUID, page: int = 1, page_size: int = 20,
        customer_id: uuid.UUID | None = None,
        status: str | None = None, channel: str | None = None,
    ) -> tuple[list[Notification], int]:
        stmt = select(Notification).where(Notification.organization_id == org_id)
        count_stmt = select(func.count()).select_from(Notification).where(
            Notification.organization_id == org_id,
        )
        if customer_id:
            stmt = stmt.where(Notification.customer_id == customer_id)
            count_stmt = count_stmt.where(Notification.customer_id == customer_id)
        if status:
            stmt = stmt.where(Notification.status == status)
            count_stmt = count_stmt.where(Notification.status == status)
        if channel:
            stmt = stmt.where(Notification.channel == channel)
            count_stmt = count_stmt.where(Notification.channel == channel)
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar() or 0
        stmt = stmt.order_by(Notification.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(stmt)
        notifications = result.scalars().all()
        return list(notifications), total

    async def mark_read(self, notification_id: uuid.UUID, org_id: uuid.UUID) -> None:
        notification = await self.get_notification(notification_id, org_id)
        notification.status = "read"
        await self.session.flush()

    async def mark_all_read(self, org_id: uuid.UUID, user_id: uuid.UUID | None = None) -> int:
        stmt = (
            update(Notification)
            .where(
                Notification.organization_id == org_id,
                Notification.status.in_(["sent", "delivered"]),
            )
            .values(status="read")
        )
        if user_id:
            stmt = stmt.where(Notification.user_id == user_id)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount

    async def get_unread_count(
        self, org_id: uuid.UUID, user_id: uuid.UUID | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(Notification).where(
            Notification.organization_id == org_id,
            Notification.status.in_(["sent", "delivered"]),
        )
        if user_id:
            stmt = stmt.where(Notification.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def send(self, notification: Notification) -> None:
        notification.status = "sending"
        notification.sent_at = datetime.now(timezone.utc)
        await self.session.flush()
        try:
            await self._dispatch(notification)
            notification.status = "sent"
            await self.session.flush()
            logger.info(
                "Notification sent",
                extra={
                    "notification_id": str(notification.id),
                    "channel": notification.channel,
                    "type": notification.type,
                },
            )
        except Exception as e:
            notification.status = "failed"
            notification.failure_reason = str(e)
            await self.session.flush()
            logger.error(f"Notification send failed: {e}", exc_info=True)

    async def retry(self, notification: Notification) -> None:
        if notification.retry_count >= notification.max_retries:
            raise RuntimeError("Max retries reached")
        notification.retry_count += 1
        notification.status = "pending"
        notification.failure_reason = None
        await self.session.flush()
        await self.send(notification)

    async def _dispatch(self, notification: Notification) -> None:
        pass
