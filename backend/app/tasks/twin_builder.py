"""
Twin Builder Worker - Consumes events and builds/updates digital twins.
Runs as a separate process consuming from Kafka topics.
"""
import asyncio
import uuid
import json
from app.core.kafka import kafka_client
from app.core.database import async_session_factory
from app.core.redis import redis_client
from app.core.qdrant import qdrant_client
from app.core.logging import logger
from app.services.twin_service import TwinService
from app.services.event_service import EventService


async def process_event(event: dict):
    org_id = event.get("organization_id")
    customer_id = event.get("customer_id")
    event_id = event.get("event_id")
    if not org_id or not customer_id or not event_id:
        logger.warning(f"Invalid event missing org/customer/event_id: {event}")
        return

    async with async_session_factory() as session:
        twin_service = TwinService(session, redis_client)
        event_service = EventService(session, kafka_client, redis_client)

        try:
            from app.models.event import Event as CustomerEvent
            db_event = await session.get(CustomerEvent, uuid.UUID(event_id))
            if not db_event:
                logger.warning(f"Event {event_id} not found in database, skipping")
                return
            if db_event.processed:
                logger.debug(f"Event {event_id} already processed, skipping")
                return
            await event_service.process_event(org_id, db_event)
            await twin_service.update_twin_from_event(org_id, customer_id, db_event)
            logger.debug(f"Processed event for customer {customer_id}")
        except Exception as e:
            logger.error(f"Error processing event {event.get('event_id')}: {e}", exc_info=True)


async def rebuild_stale_twins():
    """Periodically rebuild stale twins."""
    while True:
        try:
            async with async_session_factory() as session:
                twin_service = TwinService(session, redis_client)
                count = await twin_service.rebuild_stale_twins()
                if count > 0:
                    logger.info(f"Rebuilt {count} stale twins")
        except Exception as e:
            logger.error(f"Error rebuilding stale twins: {e}", exc_info=True)
        await asyncio.sleep(300)  # Every 5 minutes


async def main():
    await redis_client.connect()
    await qdrant_client.connect()
    await kafka_client.connect()

    # Start stale twin rebuild loop
    asyncio.create_task(rebuild_stale_twins())

    # Consume events
    logger.info("Twin Builder Worker started")
    await kafka_client.consume(
        topic="twin.cx.events.raw",
        group_id="twin-cx-twin-builder",
        handler=process_event,
    )


if __name__ == "__main__":
    asyncio.run(main())
