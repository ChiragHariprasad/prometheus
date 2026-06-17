"""
Prediction Worker - Runs ML inference on events and customer updates.
"""
import asyncio
from app.core.kafka import kafka_client
from app.core.database import async_session_factory
from app.core.redis import redis_client
from app.core.logging import logger
from app.services.prediction_service import PredictionService


async def process_prediction_request(event: dict):
    async with async_session_factory() as session:
        service = PredictionService(session, redis_client, kafka_client)
        try:
            if event.get("type") == "batch":
                count = await service.run_batch_predictions(
                    event.get("organization_id"),
                    event.get("prediction_type"),
                )
                logger.info(f"Batch prediction complete: {count} customers")
            else:
                result = await service.get_churn_prediction(
                    event.get("organization_id"),
                    event.get("customer_id"),
                )
                logger.debug(f"Prediction complete for customer {event.get('customer_id')}")
        except Exception as e:
            logger.error(f"Prediction error: {e}", exc_info=True)


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
