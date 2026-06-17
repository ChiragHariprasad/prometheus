import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, Integer, Float, Boolean, DateTime, Numeric, BigInteger, ForeignKey, func, Time
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, UUIDMixin, TimestampMixin


class Customer(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "customers"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    external_id: Mapped[str | None] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(50))
    first_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100))
    date_of_birth: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    gender: Mapped[str | None] = mapped_column(String(50))
    timezone: Mapped[str | None] = mapped_column(String(50))
    locale: Mapped[str | None] = mapped_column(String(20))
    location: Mapped[dict | None] = mapped_column(JSONB)
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    custom_attributes: Mapped[dict | None] = mapped_column(JSONB)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_test: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_marketing: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_analytics: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_profiling: Mapped[bool] = mapped_column(Boolean, default=False)
    data_retention_days: Mapped[int | None] = mapped_column(Integer)
    source: Mapped[str | None] = mapped_column(String(100))
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CustomerProfile(Base, UUIDMixin):
    __tablename__ = "customer_profiles"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str | None] = mapped_column(String(100))
    company: Mapped[str | None] = mapped_column(String(255))
    industry: Mapped[str | None] = mapped_column(String(100))
    annual_revenue: Mapped[float | None] = mapped_column(Numeric(14, 2))
    employee_count: Mapped[int | None] = mapped_column(Integer)
    website: Mapped[str | None] = mapped_column(String(255))
    linkedin_url: Mapped[str | None] = mapped_column(String(255))
    twitter_handle: Mapped[str | None] = mapped_column(String(100))
    bio: Mapped[str | None] = mapped_column(Text)
    avatar_url: Mapped[str | None] = mapped_column(String(255))
    preferred_language: Mapped[str | None] = mapped_column(String(20))
    communication_style: Mapped[str | None] = mapped_column(String(50))
    personality_traits: Mapped[dict | None] = mapped_column(JSONB)
    psychographic_segment: Mapped[str | None] = mapped_column(String(100))
    enrichment_data: Mapped[dict | None] = mapped_column(JSONB)
    enrichment_status: Mapped[str | None] = mapped_column(String(50))
    last_enriched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))




class CustomerSession(Base, UUIDMixin):
    __tablename__ = "customer_sessions"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    session_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    session_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    page_views: Mapped[int | None] = mapped_column(Integer)
    events_count: Mapped[int | None] = mapped_column(Integer)
    channel: Mapped[str | None] = mapped_column(String(50))
    device_type: Mapped[str | None] = mapped_column(String(50))
    device_os: Mapped[str | None] = mapped_column(String(50))
    browser: Mapped[str | None] = mapped_column(String(100))
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(Text)
    referrer: Mapped[str | None] = mapped_column(String(255))
    landing_url: Mapped[str | None] = mapped_column(String(255))
    exit_url: Mapped[str | None] = mapped_column(String(255))
    is_bounce: Mapped[bool] = mapped_column(Boolean, default=False)
    utm_source: Mapped[str | None] = mapped_column(String(255))
    utm_medium: Mapped[str | None] = mapped_column(String(255))
    utm_campaign: Mapped[str | None] = mapped_column(String(255))
    utm_content: Mapped[str | None] = mapped_column(String(255))
    utm_term: Mapped[str | None] = mapped_column(String(255))
    session_data: Mapped[dict | None] = mapped_column(JSONB)


class CustomerPreference(Base, UUIDMixin):
    __tablename__ = "customer_preferences"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    channel_email: Mapped[bool] = mapped_column(Boolean, default=True)
    channel_sms: Mapped[bool] = mapped_column(Boolean, default=True)
    channel_push: Mapped[bool] = mapped_column(Boolean, default=True)
    channel_in_app: Mapped[bool] = mapped_column(Boolean, default=True)
    channel_webhook: Mapped[bool] = mapped_column(Boolean, default=True)
    channel_whatsapp: Mapped[bool] = mapped_column(Boolean, default=True)
    email_frequency: Mapped[str | None] = mapped_column(String(50))
    sms_frequency: Mapped[str | None] = mapped_column(String(50))
    push_frequency: Mapped[str | None] = mapped_column(String(50))
    quiet_hours_start: Mapped[datetime | None] = mapped_column(Time)
    quiet_hours_end: Mapped[datetime | None] = mapped_column(Time)
    timezone: Mapped[str | None] = mapped_column(String(50))
    preferred_categories: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    preferred_brands: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    excluded_categories: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    max_communications_per_day: Mapped[int | None] = mapped_column(Integer)
    do_not_disturb: Mapped[bool] = mapped_column(Boolean, default=False)


class CustomerInterest(Base, UUIDMixin):
    __tablename__ = "customer_interests"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    subcategory: Mapped[str | None] = mapped_column(String(100))
    interest_level: Mapped[float | None] = mapped_column(Float)
    affinity_score: Mapped[float | None] = mapped_column(Float)
    interaction_count: Mapped[int | None] = mapped_column(Integer)
    last_interaction_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_detected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source: Mapped[str | None] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    decay_factor: Mapped[float | None] = mapped_column(Float, default=1.0)


class CustomerEmbedding(Base, UUIDMixin):
    __tablename__ = "customer_embeddings"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    embedding_model: Mapped[str] = mapped_column(String(255), nullable=False)
    embedding_dimensions: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding_vector: Mapped[dict] = mapped_column(JSONB, nullable=False)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)
    version: Mapped[int | None] = mapped_column(Integer)



class CustomerSegment(Base, UUIDMixin):
    __tablename__ = "customer_segments"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(100))
    rules: Mapped[dict | None] = mapped_column(JSONB)
    ml_model_id: Mapped[str | None] = mapped_column(String(255))
    cluster_id: Mapped[int | None] = mapped_column(Integer)
    customer_count: Mapped[int] = mapped_column(Integer, default=0)
    segment_metadata: Mapped[dict | None] = mapped_column(JSONB)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_dynamic: Mapped[bool] = mapped_column(Boolean, default=False)
    refresh_interval_minutes: Mapped[int | None] = mapped_column(Integer)
    last_refreshed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )


class CustomerSegmentMapping(Base, UUIDMixin):
    __tablename__ = "customer_segment_mapping"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), primary_key=True
    )
    segment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customer_segments.id", ondelete="CASCADE"), primary_key=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    assigned_by: Mapped[str | None] = mapped_column(String(255))
    score: Mapped[float | None] = mapped_column(Float)
