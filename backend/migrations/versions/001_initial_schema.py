"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-06-16
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS uuid-ossp")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gin")
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    op.create_table(
        "organizations",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), unique=True, nullable=False),
        sa.Column("domain", sa.String(255)),
        sa.Column("logo_url", sa.Text),
        sa.Column("plan", sa.String(50), default="enterprise"),
        sa.Column("settings", JSONB, default=dict),
        sa.Column("features", JSONB, default=dict),
        sa.Column("max_customers", sa.Integer, default=100000),
        sa.Column("max_users", sa.Integer, default=100),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("trial_ends_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "users",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("avatar_url", sa.Text),
        sa.Column("job_title", sa.String(255)),
        sa.Column("department", sa.String(100)),
        sa.Column("phone", sa.String(50)),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("is_verified", sa.Boolean, default=False),
        sa.Column("mfa_enabled", sa.Boolean, default=False),
        sa.Column("mfa_secret", sa.Text),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.Column("failed_login_attempts", sa.Integer, default=0),
        sa.Column("locked_until", sa.DateTime(timezone=True)),
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("password_expires_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("organization_id", "email"),
    )

    op.create_table(
        "customers",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_id", sa.String(255)),
        sa.Column("email", sa.String(255)),
        sa.Column("phone", sa.String(50)),
        sa.Column("first_name", sa.String(100)),
        sa.Column("last_name", sa.String(100)),
        sa.Column("date_of_birth", sa.Date),
        sa.Column("gender", sa.String(20)),
        sa.Column("timezone", sa.String(50), default="UTC"),
        sa.Column("locale", sa.String(10), default="en-US"),
        sa.Column("location", JSONB, default=dict),
        sa.Column("tags", ARRAY(sa.String), default=[]),
        sa.Column("custom_attributes", JSONB, default=dict),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("is_test", sa.Boolean, default=False),
        sa.Column("consent_marketing", sa.Boolean, default=False),
        sa.Column("consent_analytics", sa.Boolean, default=True),
        sa.Column("consent_profiling", sa.Boolean, default=False),
        sa.Column("data_retention_days", sa.Integer, default=730),
        sa.Column("source", sa.String(50), default="api"),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("organization_id", "external_id"),
        sa.UniqueConstraint("organization_id", "email"),
    )

    op.create_index("idx_customers_org", "customers", ["organization_id"])
    op.create_index("idx_customers_email", "customers", ["organization_id", "email"])
    op.create_index("idx_customers_active", "customers", ["organization_id", "is_active"],
                    postgresql_where=sa.text("is_active = true"))

    op.create_table(
        "customer_twins",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("customer_id", UUID, sa.ForeignKey("customers.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("organization_id", UUID, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(50), default="building"),
        sa.Column("version", sa.Integer, default=1),
        sa.Column("behavior_profile", JSONB, default=dict),
        sa.Column("interest_graph", JSONB, default=dict),
        sa.Column("channel_affinity", JSONB, default=dict),
        sa.Column("engagement_score", sa.Float, default=0.0),
        sa.Column("loyalty_score", sa.Float, default=0.0),
        sa.Column("lifetime_value", sa.Float, default=0.0),
        sa.Column("sentiment_trend", ARRAY(sa.Float), default=[]),
        sa.Column("intent_forecast", JSONB, default=dict),
        sa.Column("risk_indicators", JSONB, default=dict),
        sa.Column("communication_preferences", JSONB, default=dict),
        sa.Column("embedding_id", UUID),
        sa.Column("last_event_at", sa.DateTime(timezone=True)),
        sa.Column("last_prediction_at", sa.DateTime(timezone=True)),
        sa.Column("twin_metadata", JSONB, default=dict),
        sa.Column("confidence_score", sa.Float, default=0.0),
        sa.Column("staleness_score", sa.Float, default=0.0),
        sa.Column("recalculation_required", sa.Boolean, default=False),
        sa.Column("built_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index("idx_customer_twins_org", "customer_twins", ["organization_id"])
    op.create_index("idx_customer_twins_engagement", "customer_twins", ["organization_id", "engagement_score"])

    op.create_table(
        "customer_events",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID, nullable=False),
        sa.Column("customer_id", UUID, nullable=False),
        sa.Column("session_id", UUID),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("event_name", sa.String(255), nullable=False),
        sa.Column("event_properties", JSONB, default=dict),
        sa.Column("context", JSONB, default=dict),
        sa.Column("channel", sa.String(50)),
        sa.Column("source", sa.String(50)),
        sa.Column("device_type", sa.String(100)),
        sa.Column("device_os", sa.String(100)),
        sa.Column("browser", sa.String(100)),
        sa.Column("ip_address", sa.String(45)),
        sa.Column("user_agent", sa.Text),
        sa.Column("referrer", sa.Text),
        sa.Column("url", sa.Text),
        sa.Column("geolocation", JSONB, default=dict),
        sa.Column("campaign_id", UUID),
        sa.Column("value", sa.Float),
        sa.Column("currency", sa.String(3)),
        sa.Column("processed", sa.Boolean, default=False),
        sa.Column("processing_latency_ms", sa.Integer),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index("idx_events_org_customer", "customer_events", ["organization_id", "customer_id"])
    op.create_index("idx_events_timestamp", "customer_events", ["organization_id", "event_timestamp"])
    op.create_index("idx_events_unprocessed", "customer_events", ["organization_id", "processed"],
                    postgresql_where=sa.text("processed = false"))

    op.execute("""
        CREATE TABLE IF NOT EXISTS customer_events_default PARTITION OF customer_events
        FOR VALUES FROM ('2027-01-01') TO ('2030-01-01')
    """)

    op.create_table(
        "customer_segments",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("rules", JSONB, default=dict),
        sa.Column("ml_model_id", sa.String(255)),
        sa.Column("cluster_id", sa.Integer),
        sa.Column("customer_count", sa.Integer, default=0),
        sa.Column("segment_metadata", JSONB, default=dict),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("is_dynamic", sa.Boolean, default=True),
        sa.Column("refresh_interval_minutes", sa.Integer, default=60),
        sa.Column("last_refreshed_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", UUID, sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("organization_id", "name"),
    )

    op.create_table(
        "campaigns",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("goal", sa.String(255)),
        sa.Column("status", sa.String(50), default="draft"),
        sa.Column("channel", sa.String(50), nullable=False),
        sa.Column("segments", JSONB, default=[]),
        sa.Column("target_customers", ARRAY(sa.String), default=[]),
        sa.Column("exclude_customers", ARRAY(sa.String), default=[]),
        sa.Column("content", JSONB, nullable=False),
        sa.Column("schedule", JSONB, default=dict),
        sa.Column("budget", sa.Numeric(15, 2)),
        sa.Column("expected_reach", sa.Integer),
        sa.Column("expected_conversion_rate", sa.Float),
        sa.Column("ab_test_config", JSONB, default=dict),
        sa.Column("frequency_cap", sa.Integer, default=3),
        sa.Column("frequency_cap_period", sa.String(20), default="day"),
        sa.Column("start_at", sa.DateTime(timezone=True)),
        sa.Column("end_at", sa.DateTime(timezone=True)),
        sa.Column("executed_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", UUID, sa.ForeignKey("users.id")),
        sa.Column("approved_by", UUID, sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "simulations",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("type", sa.String(50), default="campaign"),
        sa.Column("status", sa.String(50), default="draft"),
        sa.Column("campaign_id", UUID, sa.ForeignKey("campaigns.id")),
        sa.Column("configuration", JSONB, default=dict),
        sa.Column("parameters", JSONB, default=dict),
        sa.Column("agent_configuration", JSONB, default=dict),
        sa.Column("monte_carlo_iterations", sa.Integer, default=1000),
        sa.Column("confidence_level", sa.Float, default=0.95),
        sa.Column("time_horizon_days", sa.Integer, default=30),
        sa.Column("segment_ids", ARRAY(sa.String), default=[]),
        sa.Column("sample_size", sa.Integer, default=10000),
        sa.Column("include_control", sa.Boolean, default=True),
        sa.Column("expected_outputs", ARRAY(sa.String), default=[]),
        sa.Column("created_by", UUID, sa.ForeignKey("users.id")),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID, sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_id", UUID),
        sa.Column("actor_type", sa.String(50), default="user"),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=False),
        sa.Column("resource_id", UUID),
        sa.Column("resource_data", JSONB, default=dict),
        sa.Column("changes", JSONB, default=dict),
        sa.Column("ip_address", sa.String(45)),
        sa.Column("user_agent", sa.Text),
        sa.Column("session_id", UUID),
        sa.Column("request_id", UUID),
        sa.Column("success", sa.Boolean, default=True),
        sa.Column("error_message", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index("idx_audit_org", "audit_logs", ["organization_id"])
    op.create_index("idx_audit_actor", "audit_logs", ["organization_id", "actor_id"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("simulations")
    op.drop_table("campaigns")
    op.drop_table("customer_segments")
    op.drop_table("customer_events_default")
    op.drop_table("customer_events")
    op.drop_table("customer_twins")
    op.drop_table("customers")
    op.drop_table("users")
    op.drop_table("organizations")
