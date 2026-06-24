import time
from datetime import datetime, timezone
from typing import Any, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.core.redis import redis_client
from app.core.kafka import kafka_client


LOCK_TTL = 300
METRICS_PREFIX = "worker:metrics"
RETRY_TOPIC = "twin.cx.retry"


async def acquire_processing_lock(event_id: str, worker: str) -> bool:
    if not redis_client:
        return True
    key = f"lock:{worker}:{event_id}"
    return await redis_client.setnx(key, "1", ttl=LOCK_TTL)


async def release_processing_lock(event_id: str, worker: str):
    if not redis_client:
        return
    key = f"lock:{worker}:{event_id}"
    try:
        await redis_client.delete(key)
    except Exception:
        pass


async def safe_commit(session: AsyncSession, label: str = ""):
    try:
        await session.commit()
    except Exception as e:
        await session.rollback()
        logger.error("Transaction commit failed, rolled back", extra={
            "label": label, "error": str(e),
        })
        raise


async def safe_rollback(session: AsyncSession, label: str = ""):
    try:
        await session.rollback()
    except Exception:
        pass


async def send_to_dlq(original_topic: str, message: dict, error: str):
    dlq_message = {
        "original_topic": original_topic,
        "message": message,
        "error": error,
        "failed_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        await kafka_client.produce("twin.cx.dead.letter", dlq_message)
    except Exception as e:
        logger.error("Failed to send to DLQ", extra={"error": str(e)})


async def send_retry(original_topic: str, message: dict, retry_count: int, max_retries: int = 3):
    if retry_count >= max_retries:
        await send_to_dlq(original_topic, message, f"Exceeded {max_retries} retries")
        return
    retry_message = {
        **message,
        "retry_count": retry_count + 1,
        "original_topic": original_topic,
        "retry_at": time.time() + (2 ** (retry_count + 1)),
    }
    try:
        await kafka_client.produce(RETRY_TOPIC, retry_message)
    except Exception as e:
        logger.error("Failed to send retry", extra={"error": str(e)})


async def record_metrics(worker: str, success: bool, latency_ms: float):
    if not redis_client:
        return
    key = f"{METRICS_PREFIX}:{worker}"
    try:
        pipe = redis_client._client.pipeline()
        pipe.incr(f"{key}:total")
        pipe.incr(f"{key}:success" if success else f"{key}:failure")
        pipe.lpush(f"{key}:latency", latency_ms)
        pipe.ltrim(f"{key}:latency", 0, 999)
        await pipe.execute()
    except Exception as e:
        logger.warning("Metrics recording failed", extra={"error": str(e)})


async def get_worker_metrics(worker: str) -> dict[str, Any]:
    if not redis_client:
        return {"worker": worker, "total": 0, "success": 0, "failure": 0, "success_rate": 0.0}
    key = f"{METRICS_PREFIX}:{worker}"
    total = int(await redis_client._client.get(f"{key}:total") or 0)
    success = int(await redis_client._client.get(f"{key}:success") or 0)
    failure = int(await redis_client._client.get(f"{key}:failure") or 0)
    return {
        "worker": worker,
        "total": total,
        "success": success,
        "failure": failure,
        "success_rate": round(success / max(total, 1), 4),
    }


def latency_tracker() -> tuple[float, Callable[[], float]]:
    start = time.monotonic()
    return start, lambda: (time.monotonic() - start) * 1000
