import uuid
import math
import random
import statistics
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import NotFoundException, ValidationException
from app.core.logging import logger
from app.core.redis import RedisClient
from app.models.simulation import Simulation, SimulationRun, SimulationResult
from app.schemas.simulation import (
    SimulationCreate, SimulationResponse,
    SimulationResultResponse, SimulationForecastResponse,
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
        time_horizon = simulation.time_horizon_days or settings.SIMULATION_DEFAULT_TIME_HORIZON_DAYS
        confidence = simulation.confidence_level or settings.SIMULATION_CONFIDENCE_LEVEL

        params = simulation.parameters or {}
        base_response_rate = params.get("base_response_rate", 0.05)
        base_conversion_rate = params.get("base_conversion_rate", 0.02)
        base_open_rate = params.get("base_open_rate", 0.25)
        avg_order_value = params.get("avg_order_value", 100.0)
        customer_count = simulation.sample_size or params.get("customer_count", 10000)
        cost_per_contact = params.get("cost_per_contact", 0.5)

        response_rates: list[float] = []
        conversion_rates: list[float] = []
        revenues: list[float] = []
        open_rates: list[float] = []
        click_rates: list[float] = []

        for _ in range(iterations):
            rr = random.gauss(base_response_rate, base_response_rate * 0.2)
            rr = max(0.001, min(rr, 1.0))
            response_rates.append(rr)

            cr = random.gauss(base_conversion_rate, base_conversion_rate * 0.3)
            cr = max(0.001, min(cr, 1.0))
            conversion_rates.append(cr)

            o_r = random.gauss(base_open_rate, base_open_rate * 0.15)
            o_r = max(0.01, min(o_r, 1.0))
            open_rates.append(o_r)

            c_r = random.gauss(0.03, 0.01)
            c_r = max(0.001, min(c_r, 1.0))
            click_rates.append(c_r)

            responses = customer_count * rr
            conversions = responses * cr
            revenue = conversions * avg_order_value
            revenues.append(revenue)

        mean_revenue = statistics.mean(revenues)
        std_revenue = statistics.stdev(revenues) if len(revenues) > 1 else 0

        total_cost = customer_count * cost_per_contact
        total_cost_with_fixed = total_cost + params.get("fixed_cost", 5000)
        roi = (mean_revenue - total_cost_with_fixed) / total_cost_with_fixed if total_cost_with_fixed > 0 else 0

        z_score = 1.96
        margin = z_score * (std_revenue / math.sqrt(iterations))

        revenues_sorted = sorted(revenues)
        ci_lower = revenues_sorted[int(iterations * (1 - confidence) / 2)]
        ci_upper = revenues_sorted[int(iterations * (1 + confidence) / 2)]

        percentiles = {}
        for p in [5, 10, 25, 50, 75, 90, 95]:
            idx = int(iterations * p / 100)
            percentiles[str(p)] = round(revenues_sorted[min(idx, iterations - 1)], 2)

        scenarios = {
            "optimistic": {
                "revenue": round(mean_revenue + margin, 2),
                "conversions": round((mean_revenue + margin) / avg_order_value, 0),
                "response_rate": round(statistics.mean(response_rates) + statistics.stdev(response_rates), 4),
            },
            "most_likely": {
                "revenue": round(mean_revenue, 2),
                "conversions": round(mean_revenue / avg_order_value, 0),
                "response_rate": round(statistics.mean(response_rates), 4),
            },
            "pessimistic": {
                "revenue": round(mean_revenue - margin, 2),
                "conversions": round(max((mean_revenue - margin) / avg_order_value, 0), 0),
                "response_rate": round(max(statistics.mean(response_rates) - statistics.stdev(response_rates), 0), 4),
            },
        }

        risk_assessment = {
            "probability_of_loss": round(
                sum(1 for r in revenues if r < total_cost_with_fixed) / iterations, 4
            ),
            "value_at_risk_95": round(
                mean_revenue - revenues_sorted[int(iterations * 0.05)], 2
            ),
            "expected_shortfall": round(
                mean_revenue - statistics.mean(revenues_sorted[:int(iterations * 0.05)]), 2
            ) if iterations > 20 else 0,
            "upside_potential": round(revenues_sorted[int(iterations * 0.95)] - mean_revenue, 2),
        }

        return {
            "aggregated_metrics": {
                "total_iterations": iterations,
                "mean_revenue": round(mean_revenue, 2),
                "median_revenue": round(statistics.median(revenues), 2),
                "std_revenue": round(std_revenue, 2),
                "min_revenue": round(min(revenues), 2),
                "max_revenue": round(max(revenues), 2),
                "mean_response_rate": round(statistics.mean(response_rates), 4),
                "mean_conversion_rate": round(statistics.mean(conversion_rates), 4),
                "mean_open_rate": round(statistics.mean(open_rates), 4),
                "mean_click_rate": round(statistics.mean(click_rates), 4),
                "total_cost": round(total_cost_with_fixed, 2),
                "roi": round(roi, 4),
                "customer_count": int(customer_count),
                "time_horizon_days": time_horizon,
                "confidence_level": confidence,
                "expected_responses": int(customer_count * statistics.mean(response_rates)),
                "expected_conversions": int(customer_count * statistics.mean(response_rates) * statistics.mean(conversion_rates)),
                "sensitivity": [
                    {"parameter": "response_rate", "impact": round(0.6, 4)},
                    {"parameter": "conversion_rate", "impact": round(0.3, 4)},
                    {"parameter": "avg_order_value", "impact": round(0.1, 4)},
                ],
            },
            "customer_projections": {
                "total_customers": int(customer_count),
                "responders": int(customer_count * statistics.mean(response_rates)),
                "converters": int(customer_count * statistics.mean(response_rates) * statistics.mean(conversion_rates)),
                "average_revenue_per_customer": round(mean_revenue / customer_count, 2) if customer_count > 0 else 0,
            },
            "segment_projections": {
                "overall": {
                    "response_rate": round(statistics.mean(response_rates), 4),
                    "conversion_rate": round(statistics.mean(conversion_rates), 4),
                    "revenue": round(mean_revenue, 2),
                },
            },
            "campaign_impact": {
                "expected_reach": int(customer_count),
                "expected_impressions": int(customer_count * 3),
                "expected_engagements": int(customer_count * statistics.mean(response_rates)),
                "expected_conversions": int(customer_count * statistics.mean(response_rates) * statistics.mean(conversion_rates)),
                "total_investment": round(total_cost_with_fixed, 2),
                "expected_roi": round(roi, 4),
            },
            "confidence_intervals": {
                "revenue": [round(ci_lower, 2), round(ci_upper, 2)],
                "response_rate": [
                    round(statistics.mean(response_rates) - 1.96 * statistics.stdev(response_rates), 4),
                    round(statistics.mean(response_rates) + 1.96 * statistics.stdev(response_rates), 4),
                ],
                "conversions": [
                    round(max(ci_lower / avg_order_value, 0), 0),
                    round(ci_upper / avg_order_value, 0),
                ],
                "roi": [
                    round((ci_lower - total_cost_with_fixed) / total_cost_with_fixed, 4),
                    round((ci_upper - total_cost_with_fixed) / total_cost_with_fixed, 4),
                ],
            },
            "monte_carlo_distribution": {
                "histogram": self._build_histogram(revenues, 20),
                "percentiles": percentiles,
                "scenarios": scenarios,
            },
            "expected_outcomes": {
                "expected_revenue": round(mean_revenue, 2),
                "expected_conversions": round(mean_revenue / avg_order_value, 0),
                "expected_open_rate": round(statistics.mean(open_rates), 4),
                "expected_click_rate": round(statistics.mean(click_rates), 4),
                "expected_roi": round(roi, 4),
                "expected_cost": round(total_cost_with_fixed, 2),
                "expected_profit": round(mean_revenue - total_cost_with_fixed, 2),
            },
            "risk_assessment": risk_assessment,
            "recommendations": self._generate_recommendations(risk_assessment, roi, scenarios),
        }

    def _build_histogram(self, values: list[float], bins: int) -> list[dict]:
        if not values:
            return []
        min_v, max_v = min(values), max(values)
        if max_v == min_v:
            return [{"bin_start": min_v, "bin_end": max_v, "count": len(values)}]
        bin_width = (max_v - min_v) / bins
        histogram = []
        for i in range(bins):
            start = min_v + i * bin_width
            end = start + bin_width
            count = sum(1 for v in values if start <= v < end)
            histogram.append({
                "bin_start": round(start, 2),
                "bin_end": round(end, 2),
                "count": count,
            })
        last = histogram[-1]
        last["count"] += sum(1 for v in values if v >= end)
        return histogram

    def _generate_recommendations(self, risk: dict, roi: float, scenarios: dict) -> list[str]:
        recs = []
        if roi < 0:
            recs.append("Current campaign parameters show negative ROI. Consider reducing budget or improving targeting.")
        if risk.get("probability_of_loss", 0) > 0.3:
            recs.append("High probability of loss detected. Consider running a smaller-scale test first.")
        if scenarios.get("optimistic", {}).get("revenue", 0) > scenarios.get("pessimistic", {}).get("revenue", 0) * 3:
            recs.append("Large variance between optimistic and pessimistic scenarios. Consider gathering more data.")
        if roi > 2:
            recs.append("Strong ROI projections. Consider increasing investment in this campaign.")
        if not recs:
            recs.append("Campaign shows balanced risk-reward profile. Proceed with planned execution.")
        return recs
