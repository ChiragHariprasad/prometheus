"""
Simulation Worker - Executes campaign simulations as background jobs.
Consumes from twin.cx.simulation topic and runs Monte Carlo simulations.
"""
import asyncio
from datetime import datetime, timezone
from app.core.kafka import kafka_client
from app.core.database import async_session_factory
from app.core.redis import redis_client
from app.core.logging import logger
from app.services.simulation_service import SimulationService
from app.models.simulation import Simulation
from app.tasks.worker_base import (
    acquire_processing_lock, release_processing_lock,
    safe_commit, safe_rollback, send_to_dlq, send_retry,
    record_metrics, latency_tracker,
)

WORKER_NAME = "simulation_worker"
MAX_RETRIES = 3


async def run_simulation_job(job: dict):
    simulation_id = job.get("simulation_id")
    if not simulation_id:
        logger.warning("Simulation job missing simulation_id")
        return

    retry_count = job.get("retry_count", 0)
    _start, _latency = latency_tracker()

    locked = await acquire_processing_lock(f"sim:{simulation_id}", WORKER_NAME)
    if not locked:
        logger.debug(f"Simulation {simulation_id} already running, skipping")
        return

    try:
        async with async_session_factory() as session:
            service = SimulationService(session, redis_client)

            try:
                await service.run_simulation(simulation_id)
                await safe_commit(session, f"sim:{simulation_id}")

                latency = _latency()
                await record_metrics(WORKER_NAME, True, latency)
                logger.info("Simulation completed", extra={
                    "simulation_id": simulation_id,
                    "latency_ms": round(latency, 2),
                })

            except Exception as e:
                await safe_rollback(session, f"sim:{simulation_id}")

                try:
                    sim = await session.get(Simulation, simulation_id)
                    if sim:
                        sim.status = "failed"
                        sim.completed_at = datetime.now(timezone.utc)
                        await safe_commit(session, f"sim_fail:{simulation_id}")
                except Exception:
                    await safe_rollback(session, f"sim_fail:{simulation_id}")

                latency = _latency()
                await record_metrics(WORKER_NAME, False, latency)
                logger.error("Simulation failed", extra={
                    "simulation_id": simulation_id, "error": str(e),
                    "latency_ms": round(latency, 2),
                })

                if retry_count < MAX_RETRIES:
                    await send_retry("twin.cx.simulation", job, retry_count, MAX_RETRIES)
                else:
                    await send_to_dlq("twin.cx.simulation", job, str(e))

    finally:
        await release_processing_lock(f"sim:{simulation_id}", WORKER_NAME)


async def main():
    await redis_client.connect()
    await kafka_client.connect()

    logger.info("Simulation Worker started")
    await kafka_client.consume(
        topic="twin.cx.simulation",
        group_id="twin-cx-simulator",
        handler=run_simulation_job,
    )


if __name__ == "__main__":
    asyncio.run(main())
