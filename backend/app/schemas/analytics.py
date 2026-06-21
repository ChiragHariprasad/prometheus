from datetime import datetime
from uuid import UUID
from typing import Any

from pydantic import BaseModel, ConfigDict


class AnalyticsQuery(BaseModel):
    metric: str
    dimension: str
    segment_id: UUID | None = None
    date_from: datetime
    date_to: datetime
    granularity: str = "day"
    filters: dict[str, Any] = {}


class AnalyticsResponse(BaseModel):
    metric: str
    dimension: str
    granularity: str
    data: list[dict[str, Any]] = []
    summary: dict[str, Any] = {}
    total: int = 0

    model_config = ConfigDict(from_attributes=True)


class DashboardStats(BaseModel):
    total_customers: int = 0
    events_24h: int = 0
    active_campaigns: int = 0
    avg_engagement: float = 0.0
    total_revenue: float = 0.0
    revenue_growth: float = 0.0
    churn_rate: float = 0.0


class DashboardResponse(BaseModel):
    stats: DashboardStats
    engagement_trend: list[dict[str, Any]] = []
    revenue_data: list[dict[str, Any]] = []
    segment_distribution: list[dict[str, Any]] = []
    top_segments: list[dict[str, Any]] = []
    recent_activity: list[dict[str, Any]] = []
    churn_alerts: list[dict[str, Any]] = []

    model_config = ConfigDict(from_attributes=True)


class RevenueAnalyticsResponse(BaseModel):
    total_revenue: float = 0.0
    recurring_revenue: float = 0.0
    average_order_value: float | None = None
    revenue_by_channel: dict[str, Any] = {}
    revenue_trend: list[dict[str, Any]] = []
    period: str = "monthly"
    currency: str = "USD"

    model_config = ConfigDict(from_attributes=True)


class EngagementTrendResponse(BaseModel):
    overall_score: float | None = None
    trend: list[dict[str, Any]] = []
    by_channel: dict[str, Any] = {}
    by_segment: dict[str, Any] = {}
    period: str = "weekly"

    model_config = ConfigDict(from_attributes=True)


class ChurnAnalyticsResponse(BaseModel):
    churn_rate: float | None = None
    churned_customers: int = 0
    at_risk_customers: int = 0
    churn_by_segment: list[dict[str, Any]] = []
    churn_reasons: list[dict[str, Any]] = []
    retention_rate: float | None = None
    period: str = "monthly"

    model_config = ConfigDict(from_attributes=True)


class CampaignPerformanceResponse(BaseModel):
    campaign_id: UUID
    campaign_name: str
    status: str | None = None
    total_targeted: int = 0
    total_delivered: int = 0
    total_opened: int = 0
    total_clicked: int = 0
    total_converted: int = 0
    total_revenue: float = 0.0
    open_rate: float | None = None
    click_rate: float | None = None
    conversion_rate: float | None = None
    roi: float | None = None

    model_config = ConfigDict(from_attributes=True)


class SegmentAnalyticsResponse(BaseModel):
    segment_id: UUID
    segment_name: str
    customer_count: int = 0
    avg_engagement: float | None = None
    avg_loyalty: float | None = None
    total_ltv: float = 0.0
    churn_rate: float | None = None
    growth_rate: float | None = None
    top_interests: list[dict[str, Any]] = []

    model_config = ConfigDict(from_attributes=True)
