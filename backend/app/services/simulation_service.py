import uuid
import random
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import NotFoundException, ValidationException
from app.core.logging import logger
from app.core.redis import RedisClient
from app.models.simulation import Simulation, SimulationRun, SimulationResult
from app.schemas.simulation import (
    SimulationCreate, SimulationResultResponse, SimulationForecastResponse,
)
from app.services.agent_simulation import (
    SimulationEngine, CampaignConfig, AgentGenerator,
)


class SimulationService:
    def __init__(self, session: AsyncSession, redis: RedisClient | None = None):
        self.session = session
        self.redis = redis

    async def create_simulation(self, organization_id: uuid.UUID, config: SimulationCreate | dict, created_by: uuid.UUID | None = None) -> Simulation:
        if isinstance(config, dict):
            data = config
        else:
            data = config.model_dump(exclude_unset=True)

        data["organization_id"] = organization_id
        data["status"] = "draft"
        if created_by:
            data["created_by"] = created_by

        simulation = Simulation(**data)
        self.session.add(simulation)
        await self.session.flush()
        await self.session.refresh(simulation)

        logger.info("Simulation created", extra={
            "sim_id": str(simulation.id), "org_id": str(organization_id),
            "type": simulation.type,
        })
        return simulation

    async def run_simulation(self, simulation_id: uuid.UUID) -> None:
        simulation = await self._get_simulation_or_404(simulation_id)
        if simulation.status not in ("draft", "failed"):
            raise ValidationException(f"Simulation is already {simulation.status}")

        simulation.status = "running"
        simulation.started_at = datetime.now(timezone.utc)
        await self.session.flush()

        run = SimulationRun(
            simulation_id=simulation.id,
            organization_id=simulation.organization_id,
            run_number=await self._next_run_number(simulation.id),
            status="running",
            seed=random.randint(0, 2**31 - 1),
            agents_count=simulation.sample_size or settings.SIMULATION_DEFAULT_SAMPLE_SIZE,
            iterations_executed=0,
        )
        self.session.add(run)
        await self.session.flush()
        await self.session.refresh(run)

        try:
            result_data = await self._execute_monte_carlo(simulation, run)
            result = SimulationResult(
                simulation_id=simulation.id,
                organization_id=simulation.organization_id,
                run_id=run.id,
                **result_data,
            )
            self.session.add(result)

            run.status = "completed"
            run.iterations_executed = simulation.monte_carlo_iterations or settings.SIMULATION_DEFAULT_ITERATIONS
            run.runtime_seconds = (datetime.now(timezone.utc) - simulation.started_at).total_seconds()

            simulation.status = "completed"
            simulation.completed_at = datetime.now(timezone.utc)
            await self.session.flush()

            logger.info("Simulation completed", extra={
                "sim_id": str(simulation_id), "run_id": str(run.id),
            })

        except Exception as e:
            run.status = "failed"
            run.error_message = str(e)
            simulation.status = "failed"
            await self.session.flush()
            logger.error("Simulation failed", extra={"sim_id": str(simulation_id), "error": str(e)})
            raise

    async def get_results(self, simulation_id: uuid.UUID) -> SimulationResultResponse:
        simulation = await self._get_simulation_or_404(simulation_id)

        result_stmt = select(SimulationResult).where(
            SimulationResult.simulation_id == simulation_id,
            SimulationResult.organization_id == simulation.organization_id,
        ).order_by(SimulationResult.created_at.desc()).limit(1)
        result = await self.session.execute(result_stmt)
        result_obj = result.scalar_one_or_none()

        if not result_obj:
            raise NotFoundException("SimulationResult", f"for simulation {simulation_id}")

        return SimulationResultResponse(
            id=result_obj.id,
            simulation_id=result_obj.simulation_id,
            run_id=result_obj.run_id,
            aggregated_metrics=result_obj.aggregated_metrics or {},
            customer_projections=result_obj.customer_projections or {},
            segment_projections=result_obj.segment_projections or {},
            campaign_impact=result_obj.campaign_impact or {},
            confidence_intervals=result_obj.confidence_intervals or {},
            monte_carlo_distribution=result_obj.monte_carlo_distribution or {},
            expected_outcomes=result_obj.expected_outcomes or {},
            risk_assessment=result_obj.risk_assessment or {},
            recommendations=result_obj.recommendations or [],
        )

    async def get_forecast(self, simulation_id: uuid.UUID) -> SimulationForecastResponse:
        simulation = await self._get_simulation_or_404(simulation_id)
        result_obj = await self._get_latest_result(simulation_id, simulation.organization_id)

        if not result_obj:
            raise NotFoundException("SimulationResult", f"for simulation {simulation_id}")

        aggregated = result_obj.aggregated_metrics or {}
        intervals = result_obj.confidence_intervals or {}
        outcomes = result_obj.expected_outcomes or {}

        return SimulationForecastResponse(
            expected_revenue=outcomes.get("expected_revenue"),
            expected_conversions=outcomes.get("expected_conversions"),
            expected_open_rate=outcomes.get("expected_open_rate"),
            expected_click_rate=outcomes.get("expected_click_rate"),
            revenue_confidence_interval=intervals.get("revenue", []),
            conversion_confidence_interval=intervals.get("conversions", []),
            scenarios=result_obj.monte_carlo_distribution or {},
            sensitivity=aggregated.get("sensitivity", []),
            risk_assessment=result_obj.risk_assessment or {},
        )

    async def get_progress(self, simulation_id: uuid.UUID) -> float:
        simulation = await self._get_simulation_or_404(simulation_id)

        if simulation.status == "completed":
            return 1.0
        if simulation.status == "failed":
            return 0.0
        if simulation.status == "draft":
            return 0.0

        run_stmt = (
            select(SimulationRun)
            .where(
                SimulationRun.simulation_id == simulation_id,
                SimulationRun.organization_id == simulation.organization_id,
            )
            .order_by(SimulationRun.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(run_stmt)
        run = result.scalar_one_or_none()

        if not run:
            return 0.0

        total = simulation.monte_carlo_iterations or settings.SIMULATION_DEFAULT_ITERATIONS
        executed = run.iterations_executed or 0
        return min(executed / total, 1.0)

    async def _get_simulation_or_404(self, simulation_id: uuid.UUID) -> Simulation:
        simulation = await self.session.get(Simulation, simulation_id)
        if not simulation:
            raise NotFoundException("Simulation", str(simulation_id))
        return simulation

    async def _next_run_number(self, simulation_id: uuid.UUID) -> int:
        stmt = (
            select(func.coalesce(func.max(SimulationRun.run_number), 0))
            .where(SimulationRun.simulation_id == simulation_id)
        )
        result = await self.session.execute(stmt)
        return (result.scalar() or 0) + 1

    async def _get_latest_result(self, simulation_id: uuid.UUID, organization_id: uuid.UUID) -> SimulationResult | None:
        stmt = (
            select(SimulationResult)
            .where(
                SimulationResult.simulation_id == simulation_id,
                SimulationResult.organization_id == organization_id,
            )
            .order_by(SimulationResult.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _execute_monte_carlo(self, simulation: Simulation, run: SimulationRun) -> dict:
        iterations = simulation.monte_carlo_iterations or settings.SIMULATION_DEFAULT_ITERATIONS
        params = simulation.parameters or {}
        agent_config = simulation.agent_configuration or {}

        campaign = CampaignConfig(
            channel=agent_config.get("channel", params.get("channel", "email")),
            offer_type=agent_config.get("offer_type", params.get("offer_type", "discount")),
            discount_rate=agent_config.get("discount_rate", params.get("discount_rate", 0.1)),
            urgency=agent_config.get("urgency", params.get("urgency", "medium")),
            frequency=agent_config.get("frequency", params.get("frequency", 1)),
            creative_type=agent_config.get("creative_type", params.get("creative_type", "image")),
            avg_order_value=params.get("avg_order_value", 100.0),
            cost_per_contact=params.get("cost_per_contact", 0.5),
            fixed_cost=params.get("fixed_cost", 5000.0),
            scenario=agent_config.get("scenario", params.get("scenario", "expected_case")),
            competitor_pressure=agent_config.get("competitor_pressure", params.get("competitor_pressure", 0.0)),
        )

        agent_count = simulation.sample_size or params.get("customer_count", 10000)
        agents = AgentGenerator.synthetic(agent_count, seed=run.seed)

        engine = SimulationEngine(agents, campaign, seed=run.seed)
        result = engine.run(iterations=iterations)

        result["aggregated_metrics"]["time_horizon_days"] = simulation.time_horizon_days or settings.SIMULATION_DEFAULT_TIME_HORIZON_DAYS
        result["aggregated_metrics"]["confidence_level"] = simulation.confidence_level or settings.SIMULATION_CONFIDENCE_LEVEL

        nba = engine.compute_next_best_action(result)
        result["campaign_impact"]["next_best_action"] = nba
        result["recommendations"].append(
            f"Next best action: use channel '{nba['recommended_channel']}' "
            f"with discount {nba['recommended_discount']:.0%} "
            f"at frequency {nba['recommended_frequency']}."
        )

        return result


