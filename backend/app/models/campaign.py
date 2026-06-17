import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, Integer, Float, Boolean, DateTime, Numeric, ForeignKey, Enum as SAEnum, func
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, UUIDMixin
import enum


class Campaign(Base, UUIDMixin):
    __tablename__ = "campaigns"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    goal: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(
        SAEnum("draft", "scheduled", "active", "paused", "completed", "cancelled", name="campaign_status", create_type=False),
        default="draft",
    )
    channel: Mapped[str | None] = mapped_column(String(50))
    segments: Mapped[dict | None] = mapped_column(JSONB)
    target_customers: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    exclude_customers: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    content: Mapped[dict | None] = mapped_column(JSONB)
    schedule: Mapped[dict | None] = mapped_column(JSONB)
    budget: Mapped[float | None] = mapped_column(Numeric(14, 2))
    expected_reach: Mapped[int | None] = mapped_column(Integer)
    expected_conversion_rate: Mapped[float | None] = mapped_column(Float)
    ab_test_config: Mapped[dict | None] = mapped_column(JSONB)
    frequency_cap: Mapped[int | None] = mapped_column(Integer)
    frequency_cap_period: Mapped[str | None] = mapped_column(String(50))
    start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )


class CampaignTarget(Base, UUIDMixin):
    __tablename__ = "campaign_targets"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    segment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customer_segments.id", ondelete="SET NULL")
    )
    treatment: Mapped[str | None] = mapped_column(String(100))
    score: Mapped[float | None] = mapped_column(Float)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    clicked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    converted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revenue: Mapped[float | None] = mapped_column(Numeric(14, 2))
    engagement_score: Mapped[float | None] = mapped_column(Float)


class CampaignResult(Base, UUIDMixin):
    __tablename__ = "campaign_results"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    total_targeted: Mapped[int] = mapped_column(Integer, default=0)
    total_delivered: Mapped[int] = mapped_column(Integer, default=0)
    total_opened: Mapped[int] = mapped_column(Integer, default=0)
    total_clicked: Mapped[int] = mapped_column(Integer, default=0)
    total_converted: Mapped[int] = mapped_column(Integer, default=0)
    total_revenue: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    total_cost: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    open_rate: Mapped[float | None] = mapped_column(Float)
    click_rate: Mapped[float | None] = mapped_column(Float)
    conversion_rate: Mapped[float | None] = mapped_column(Float)
    bounce_rate: Mapped[float | None] = mapped_column(Float)
    unsubscribe_rate: Mapped[float | None] = mapped_column(Float)
    roi: Mapped[float | None] = mapped_column(Float)
    engagement_distribution: Mapped[dict | None] = mapped_column(JSONB)
    channel_performance: Mapped[dict | None] = mapped_column(JSONB)
    segment_performance: Mapped[dict | None] = mapped_column(JSONB)
    hourly_breakdown: Mapped[dict | None] = mapped_column(JSONB)
    daily_breakdown: Mapped[dict | None] = mapped_column(JSONB)
    ab_test_results: Mapped[dict | None] = mapped_column(JSONB)
    control_group_results: Mapped[dict | None] = mapped_column(JSONB)
    treatment_group_results: Mapped[dict | None] = mapped_column(JSONB)
    computed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
