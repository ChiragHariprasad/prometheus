"""
Notification Worker - Sends notifications via appropriate channels.
"""
import asyncio
from app.core.kafka import kafka_client
from app.core.database import async_session_factory
from app.core.redis import redis_client
from app.core.logging import logger
from app.services.notification_service import NotificationService


import uuid
from app.models.notification import Notification


async def process_notification(event: dict):
    notification_id = event.get("notification_id")
    org_id = event.get("organization_id")
    if not notification_id or not org_id:
        logger.warning(f"Invalid notification event missing id/org: {event}")
        return

    async with async_session_factory() as session:
        service = NotificationService(session)
        try:
            notification = await service.get_notification(uuid.UUID(notification_id), uuid.UUID(org_id))
            await service.send(notification)
            logger.debug(f"Notification sent: {notification_id}")
        except Exception as e:
            logger.error(f"Notification failed: {e}", exc_info=True)


async def main():
    await redis_client.connect()
    await kafka_client.connect()

    logger.info("Notification Worker started")
    await kafka_client.consume(
        topic="twin.cx.notification",
        group_id="twin-cx-notifier",
        handler=process_notification,
    )


if __name__ == "__main__":
    asyncio.run(main())
