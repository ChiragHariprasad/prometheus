from datetime import datetime
from uuid import UUID
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


class CampaignCreate(BaseModel):
    name: str
    description: str | None = None
    type: str
    goal: str | None = None
    channel: str
    segments: list[str] = []
    target_customers: list[str] = []
    exclude_customers: list[str] = []
    content: dict[str, Any] = {}
    schedule: dict[str, Any] = {}
    budget: float | None = None
    expected_reach: int | None = None
    expected_conversion_rate: float | None = None
    ab_test_config: dict[str, Any] = {}
    frequency_cap: int = 3
    frequency_cap_period: str = "day"
    start_at: datetime | None = None
    end_at: datetime | None = None


class CampaignUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    type: str | None = None
    goal: str | None = None
    channel: str | None = None
    segments: list[str] | None = None
    target_customers: list[str] | None = None
    exclude_customers: list[str] | None = None
    content: dict[str, Any] | None = None
    schedule: dict[str, Any] | None = None
    budget: float | None = None
    expected_reach: int | None = None
    expected_conversion_rate: float | None = None
    ab_test_config: dict[str, Any] | None = None
    frequency_cap: int | None = None
    frequency_cap_period: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None


class CampaignResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    description: str | None = None
    type: str
    goal: str | None = None
    status: str | None = None
    channel: str
    segments: Any = {}
    target_customers: list[str] = []
    exclude_customers: list[str] = []
    content: dict[str, Any] = {}
    schedule: dict[str, Any] = {}
    budget: float | None = None
    expected_reach: int | None = None
    expected_conversion_rate: float | None = None
    ab_test_config: dict[str, Any] = {}
    frequency_cap: int = 3
    frequency_cap_period: str = "day"
    start_at: datetime | None = None
    end_at: datetime | None = None
    executed_at: datetime | None = None
    completed_at: datetime | None = None
    created_by: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class CampaignResultResponse(BaseModel):
    id: UUID
    campaign_id: UUID
    total_targeted: int = 0
    total_delivered: int = 0
    total_opened: int = 0
    total_clicked: int = 0
    total_converted: int = 0
    total_revenue: float = 0.0
    total_cost: float = 0.0
    open_rate: float | None = None
    click_rate: float | None = None
    conversion_rate: float | None = None
    bounce_rate: float | None = None
    unsubscribe_rate: float | None = None
    roi: float | None = None
    engagement_distribution: dict[str, Any] = {}
    channel_performance: dict[str, Any] = {}
    segment_performance: dict[str, Any] = {}
    hourly_breakdown: list[dict[str, Any]] = []
    daily_breakdown: list[dict[str, Any]] = []
    ab_test_results: dict[str, Any] = {}
    control_group_results: dict[str, Any] = {}
    treatment_group_results: dict[str, Any] = {}
    computed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class CampaignTargetResponse(BaseModel):
    id: UUID
    customer_id: UUID
    treatment: str | None = None
    score: float | None = None
    priority: int | None = None
    status: str | None = None
    delivered_at: datetime | None = None
    opened_at: datetime | None = None
    clicked_at: datetime | None = None
    converted_at: datetime | None = None
    revenue: float | None = None
    engagement_score: float | None = None

    model_config = ConfigDict(from_attributes=True)


class CampaignMetricsResponse(BaseModel):
    sent: int = 0
    delivered: int = 0
    opened: int = 0
    clicked: int = 0
    converted: int = 0
    revenue: float = 0.0
    roi: float = 0.0


class CampaignListResponse(CampaignResponse):
    result_summary: dict[str, Any] | None = None
    metrics: CampaignMetricsResponse | None = None

    model_config = ConfigDict(from_attributes=True)
