"""
Twin Builder Worker - Consumes events and builds/updates digital twins.
Runs as a separate process consuming from Kafka topics.
"""
import asyncio
import uuid
from app.core.kafka import kafka_client
from app.core.database import async_session_factory
from app.core.redis import redis_client
from app.core.qdrant import qdrant_client
from app.core.logging import logger
from app.services.twin_service import TwinService
from app.services.event_service import EventService
from app.tasks.worker_base import (
    acquire_processing_lock, release_processing_lock,
    safe_commit, safe_rollback, send_to_dlq, send_retry,
    record_metrics, latency_tracker,
)

WORKER_NAME = "twin_builder"
MAX_RETRIES = 3


async def process_event(event: dict):
    org_id = event.get("organization_id")
    customer_id = event.get("customer_id")
    event_id = event.get("event_id")
    if not org_id or not customer_id or not event_id:
        logger.warning(f"Invalid event missing org/customer/event_id: {event}")
        return

    retry_count = event.get("retry_count", 0)
    _start, _latency = latency_tracker()

    locked = await acquire_processing_lock(event_id, WORKER_NAME)
    if not locked:
        logger.debug(f"Event {event_id} already being processed by another worker, skipping")
        return

    try:
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
                await safe_commit(session, f"event:{event_id}")

                latency = _latency()
                await record_metrics(WORKER_NAME, True, latency)
                logger.info("Event processed", extra={
                    "event_id": event_id, "customer_id": customer_id,
                    "latency_ms": round(latency, 2),
                })

            except Exception as e:
                await safe_rollback(session, f"event:{event_id}")
                latency = _latency()
                await record_metrics(WORKER_NAME, False, latency)
                logger.error("Error processing event", extra={
                    "event_id": event_id, "error": str(e), "latency_ms": round(latency, 2),
                })
                if retry_count < MAX_RETRIES:
                    await send_retry("twin.cx.events.raw", event, retry_count, MAX_RETRIES)
                else:
                    await send_to_dlq("twin.cx.events.raw", event, str(e))

    finally:
        await release_processing_lock(event_id, WORKER_NAME)


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
        await asyncio.sleep(300)


async def main():
    await redis_client.connect()
    await qdrant_client.connect()
    await kafka_client.connect()

    asyncio.create_task(rebuild_stale_twins())

    logger.info("Twin Builder Worker started")
    await kafka_client.consume(
        topic="twin.cx.events.raw",
        group_id="twin-cx-twin-builder",
        handler=process_event,
    )


if __name__ == "__main__":
    asyncio.run(main())
