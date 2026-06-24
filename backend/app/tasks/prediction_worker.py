"""
Prediction Worker - Runs ML inference on events and customer updates.
"""
import asyncio
from app.core.kafka import kafka_client
from app.core.database import async_session_factory
from app.core.redis import redis_client
from app.core.logging import logger
from app.services.prediction_service import PredictionService
from app.tasks.worker_base import (
    acquire_processing_lock, release_processing_lock,
    safe_commit, safe_rollback, send_to_dlq, send_retry,
    record_metrics, latency_tracker,
)

WORKER_NAME = "prediction_worker"
MAX_RETRIES = 3


async def process_prediction_request(event: dict):
    retry_count = event.get("retry_count", 0)
    _start, _latency = latency_tracker()
    request_id = f"{event.get('organization_id')}:{event.get('customer_id') or 'batch'}"

    locked = await acquire_processing_lock(f"pred:{request_id}", WORKER_NAME)
    if not locked:
        logger.debug(f"Prediction request {request_id} already in progress, skipping")
        return

    try:
        async with async_session_factory() as session:
            service = PredictionService(session, redis_client)

            try:
                if event.get("type") == "batch":
                    count = await service.run_batch_predictions(
                        event.get("organization_id"),
                        event.get("prediction_type"),
                    )
                    await safe_commit(session, f"batch_pred:{request_id}")
                    latency = _latency()
                    await record_metrics(WORKER_NAME, True, latency)
                    logger.info("Batch prediction complete", extra={
                        "count": count, "latency_ms": round(latency, 2),
                    })
                else:
                    await service.get_churn_prediction(
                        event.get("organization_id"),
                        event.get("customer_id"),
                    )
                    await safe_commit(session, f"pred:{request_id}")
                    latency = _latency()
                    await record_metrics(WORKER_NAME, True, latency)
                    logger.info("Prediction complete", extra={
                        "customer_id": event.get("customer_id"),
                        "latency_ms": round(latency, 2),
                    })

            except Exception as e:
                await safe_rollback(session, f"pred:{request_id}")
                latency = _latency()
                await record_metrics(WORKER_NAME, False, latency)
                logger.error("Prediction error", extra={
                    "request_id": request_id, "error": str(e),
                    "latency_ms": round(latency, 2),
                })
                if retry_count < MAX_RETRIES:
                    await send_retry("twin.cx.prediction", event, retry_count, MAX_RETRIES)
                else:
                    await send_to_dlq("twin.cx.prediction", event, str(e))

    finally:
        await release_processing_lock(f"pred:{request_id}", WORKER_NAME)


async def main():
    await redis_client.connect()
    await kafka_client.connect()

    logger.info("Prediction Worker started")
    await kafka_client.consume(
        topic="twin.cx.prediction",
        group_id="twin-cx-predictor",
        handler=process_prediction_request,
    )


if __name__ == "__main__":
    asyncio.run(main())
