import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, Integer, Float, Boolean, DateTime, BigInteger, ForeignKey, func, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, UUIDMixin, TimestampMixin


class Simulation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "simulations"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(SAEnum('draft', 'running', 'completed', 'failed', 'cancelled', name="simulation_status", create_type=False), default="draft")
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="SET NULL")
    )
    configuration: Mapped[dict | None] = mapped_column(JSONB)
    parameters: Mapped[dict | None] = mapped_column(JSONB)
    agent_configuration: Mapped[dict | None] = mapped_column(JSONB)
    monte_carlo_iterations: Mapped[int | None] = mapped_column(Integer)
    confidence_level: Mapped[float | None] = mapped_column(Float)
    time_horizon_days: Mapped[int | None] = mapped_column(Integer)
    segment_ids: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    sample_size: Mapped[int | None] = mapped_column(Integer)
    include_control: Mapped[bool] = mapped_column(Boolean, default=False)
    expected_outputs: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SimulationRun(Base, UUIDMixin):
    __tablename__ = "simulation_runs"

    simulation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("simulations.id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    run_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(SAEnum('draft', 'running', 'completed', 'failed', 'cancelled', name="simulation_status", create_type=False), default="pending")
    seed: Mapped[int | None] = mapped_column(Integer)
    agents_count: Mapped[int] = mapped_column(Integer, default=0)
    iterations_executed: Mapped[int] = mapped_column(Integer, default=0)
    runtime_seconds: Mapped[float | None] = mapped_column(Float)
    cpu_usage: Mapped[float | None] = mapped_column(Float)
    memory_usage_bytes: Mapped[int | None] = mapped_column(BigInteger)
    error_message: Mapped[str | None] = mapped_column(Text)
    logs: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class SimulationResult(Base, UUIDMixin):
    __tablename__ = "simulation_results"

    simulation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("simulations.id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("simulation_runs.id", ondelete="SET NULL")
    )
    aggregated_metrics: Mapped[dict | None] = mapped_column(JSONB)
    customer_projections: Mapped[dict | None] = mapped_column(JSONB)
    segment_projections: Mapped[dict | None] = mapped_column(JSONB)
    campaign_impact: Mapped[dict | None] = mapped_column(JSONB)
    confidence_intervals: Mapped[dict | None] = mapped_column(JSONB)
    monte_carlo_distribution: Mapped[dict | None] = mapped_column(JSONB)
    expected_outcomes: Mapped[dict | None] = mapped_column(JSONB)
    risk_assessment: Mapped[dict | None] = mapped_column(JSONB)
    recommendations: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
