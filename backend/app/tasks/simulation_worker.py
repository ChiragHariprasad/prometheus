"""
Simulation Worker - Executes campaign simulations as background jobs.
Consumes from twin.cx.simulation topic and runs Monte Carlo simulations.
"""
import asyncio
import json
from datetime import datetime, timezone
from app.core.kafka import kafka_client
from app.core.database import async_session_factory
from app.core.redis import redis_client
from app.core.logging import logger
from app.services.simulation_service import SimulationService
from app.models.simulation import Simulation


async def run_simulation_job(job: dict):
    simulation_id = job.get("simulation_id")
    if not simulation_id:
        logger.warning("Simulation job missing simulation_id")
        return

    logger.info(f"Starting simulation: {simulation_id}")

    async with async_session_factory() as session:
        service = SimulationService(session, redis_client)
        try:
            result = await service.run_simulation(simulation_id)
            logger.info(f"Simulation {simulation_id} completed: {result.get('status')}")
        except Exception as e:
            logger.error(f"Simulation {simulation_id} failed: {e}", exc_info=True)
            # Mark simulation as failed
            sim = await session.get(Simulation, simulation_id)
            if sim:
                sim.status = "failed"
                sim.completed_at = datetime.now(timezone.utc)
                await session.commit()


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
