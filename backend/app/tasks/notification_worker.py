"""
Notification Worker - Sends notifications via appropriate channels.
"""
import asyncio
from app.core.kafka import kafka_client
from app.core.database import async_session_factory
from app.core.redis import redis_client
from app.core.logging import logger
from app.services.notification_service import NotificationService


async def process_notification(event: dict):
    async with async_session_factory() as session:
        service = NotificationService(session, redis_client)
        try:
            await service.send_notification(event)
            logger.debug(f"Notification sent: {event.get('notification_id')}")
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
