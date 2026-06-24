import uuid
from datetime import datetime, timezone

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.core.logging import logger
from app.models.notification import Notification
from app.repositories.notification_repository import NotificationRepository


class NotificationService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = NotificationRepository(session)

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
        notification = await self.repo.get(notification_id, org_id)
        if not notification:
            raise NotFoundException("Notification", str(notification_id))
        return notification

    async def list_notifications(
        self, org_id: uuid.UUID, page: int = 1, page_size: int = 20,
        customer_id: uuid.UUID | None = None,
        status: str | None = None, channel: str | None = None,
    ) -> tuple[list[Notification], int]:
        filters = {}
        if customer_id:
            filters["customer_id"] = str(customer_id)
        if status:
            filters["status"] = status
        if channel:
            filters["channel"] = channel
        return await self.repo.get_multi(
            skip=(page - 1) * page_size, limit=page_size,
            filters=filters, sorts=[{"field": "created_at", "direction": "desc"}],
            organization_id=org_id,
        )

    async def mark_read(self, notification_id: uuid.UUID, org_id: uuid.UUID) -> None:
        notification = await self.repo.get(notification_id, org_id)
        if not notification:
            raise NotFoundException("Notification", str(notification_id))
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
        return await self.repo.get_unread_count(org_id) if not user_id else 0

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
