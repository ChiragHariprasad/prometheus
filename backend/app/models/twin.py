import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, Boolean, DateTime, ForeignKey, func, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, UUIDMixin, TimestampMixin


class CustomerTwin(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "customer_twins"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(50), default="building")
    version: Mapped[int] = mapped_column(Integer, default=1)
    behavior_profile: Mapped[dict] = mapped_column(JSONB, default=dict)
    interest_graph: Mapped[dict] = mapped_column(JSONB, default=dict)
    memory_profile: Mapped[dict] = mapped_column(JSONB, default=dict)
    channel_affinity: Mapped[dict] = mapped_column(JSONB, default=dict)
    engagement_score: Mapped[float | None] = mapped_column(Float, default=0.0)
    loyalty_score: Mapped[float | None] = mapped_column(Float, default=0.0)
    lifetime_value: Mapped[float | None] = mapped_column(Float, default=0.0)
    sentiment_trend: Mapped[list | None] = mapped_column(ARRAY(Float), default=list)
    intent_forecast: Mapped[dict] = mapped_column(JSONB, default=dict)
    risk_indicators: Mapped[dict] = mapped_column(JSONB, default=dict)
    communication_preferences: Mapped[dict] = mapped_column(JSONB, default=dict)
    embedding_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    last_event_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_prediction_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    twin_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)
    confidence_score: Mapped[float | None] = mapped_column(Float, default=0.0)
    staleness_score: Mapped[float | None] = mapped_column(Float, default=0.0)
    recalculation_required: Mapped[bool] = mapped_column(Boolean, default=False)
    built_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TwinSnapshot(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "twin_snapshots"

    twin_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customer_twins.id", ondelete="CASCADE"), nullable=False
    )
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE")
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    snapshot_type: Mapped[str] = mapped_column(String(50), nullable=False)
    snapshot_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    scores: Mapped[dict] = mapped_column(JSONB, default=dict)
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Prediction(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "customer_predictions"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    prediction_type: Mapped[str] = mapped_column(SAEnum('churn', 'ltv', 'conversion', 'engagement', 'sentiment', 'intent', 'next_best_action', name="prediction_target", create_type=False), nullable=False)
    prediction_value: Mapped[float] = mapped_column(Float, nullable=False)
    prediction_probability: Mapped[float | None] = mapped_column(Float)
    prediction_label: Mapped[str | None] = mapped_column(String(255))
    prediction_explanation: Mapped[dict] = mapped_column(JSONB, default=dict)
    feature_importance: Mapped[dict] = mapped_column(JSONB, default=dict)
    confidence_score: Mapped[float | None] = mapped_column(Float, default=0.0)
    model_version: Mapped[str] = mapped_column(String(100), default="1.0.0", nullable=False)
    model_name: Mapped[str] = mapped_column(String(255), default="prometheus_v1", nullable=False)
    input_features: Mapped[dict] = mapped_column(JSONB, default=dict)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
