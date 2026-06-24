from datetime import datetime
from uuid import UUID
from typing import Any

from pydantic import BaseModel, ConfigDict


class TwinSummary(BaseModel):
    total_twins: int = 0
    avg_engagement: float = 0.0
    avg_loyalty: float = 0.0
    avg_sentiment: float = 0.0
    churn_risk_distribution: dict[str, int] = {"low": 0, "medium": 0, "high": 0}
    top_interests: list[dict[str, Any]] = []

    model_config = ConfigDict(from_attributes=True)


class PerCustomerTwinSummary(BaseModel):
    engagement_score: float | None = None
    loyalty_score: float | None = None
    lifetime_value: float | None = None
    sentiment_trend: list[float] = []
    sentiment_score: float | None = None
    churn_probability: float | None = None
    churn_risk_level: str | None = None
    lifecycle_stage: str | None = None
    rfm_segment: str | None = None
    version: int | None = None
    confidence_score: float | None = None
    staleness_score: float | None = None
    last_event_at: datetime | None = None
    last_prediction_at: datetime | None = None
    status: str | None = None

    model_config = ConfigDict(from_attributes=True)


class BehaviorSubScores(BaseModel):
    engagement: float = 0.0
    purchase_activity: float = 0.0
    session_depth: float = 0.0
    communication_response: float = 0.0
    recency: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class BehaviorProfileResponse(BaseModel):
    behavior_score: float | None = None
    sub_scores: BehaviorSubScores = BehaviorSubScores()
    sessions_per_week: float | None = None
    avg_session_duration: float | None = None
    page_depth_avg: float | None = None
    bounce_rate: float | None = None
    purchase_frequency: float | None = None
    avg_order_value: float | None = None
    product_category_affinity: dict[str, Any] = {}
    discount_sensitivity: float | None = None
    cart_abandonment_rate: float | None = None
    email_open_rate: float | None = None
    email_click_rate: float | None = None
    push_opt_in: bool | None = None
    preferred_time_of_day: str | None = None
    preferred_day_of_week: str | None = None
    days_since_first_seen: int | None = None
    days_since_last_purchase: int | None = None
    days_since_last_engagement: int | None = None
    lifecycle_stage: str | None = None
    rfm_recency: int | None = None
    rfm_frequency: int | None = None
    rfm_monetary: int | None = None
    rfm_segment: str | None = None

    model_config = ConfigDict(from_attributes=True)


class InterestGraphResponse(BaseModel):
    nodes: list[dict[str, Any]] = []
    dominant_category: str | None = None
    interest_diversity: float | None = None
    total_interactions: int = 0

    model_config = ConfigDict(from_attributes=True)


class MemoryProfileResponse(BaseModel):
    campaign_responses: list[dict[str, Any]] = []
    purchase_categories: list[dict[str, Any]] = []
    channel_history: list[dict[str, Any]] = []
    discount_sensitivity: float | None = None
    historical_engagement: dict[str, Any] = {}
    seasonality_patterns: list[dict[str, Any]] = []

    model_config = ConfigDict(from_attributes=True)


class ChannelAffinityResponse(BaseModel):
    email: float = 0.0
    sms: float = 0.0
    push: float = 0.0
    in_app: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class RiskIndicatorsResponse(BaseModel):
    churn_probability: float | None = None
    churn_risk_level: str | None = None
    churn_triggers: list[str] = []
    churn_prevention_actions: list[str] = []
    engagement_decline_rate: float | None = None
    negative_sentiment_count: int = 0
    complaint_count: int = 0
    support_ticket_count: int = 0
    unsubscribe_risk: float | None = None
    behavior_anomaly_score: float | None = None

    model_config = ConfigDict(from_attributes=True)


class IntentForecastResponse(BaseModel):
    purchase_intent_7d: float | None = None
    engagement_intent_7d: float | None = None
    churn_risk_7d: float | None = None
    purchase_intent_30d: float | None = None
    engagement_intent_30d: float | None = None
    churn_risk_30d: float | None = None
    predicted_ltv_90d: float | None = None
    predicted_engagement_90d: float | None = None
    recommended_action: str | None = None
    recommended_channel: str | None = None

    model_config = ConfigDict(from_attributes=True)


class TwinOutputResponse(BaseModel):
    sentiment: float | None = None
    purchase_intent: float | None = None
    churn_probability: float | None = None
    lifetime_value: float | None = None
    next_best_action: str | None = None

    model_config = ConfigDict(from_attributes=True)


class CustomerTwinResponse(BaseModel):
    customer_id: UUID
    organization_id: UUID
    status: str | None = None
    version: int | None = None
    behavior_profile: BehaviorProfileResponse | None = None
    interest_graph: InterestGraphResponse | None = None
    memory_profile: MemoryProfileResponse | None = None
    channel_affinity: ChannelAffinityResponse | None = None
    engagement_score: float | None = None
    loyalty_score: float | None = None
    lifetime_value: float | None = None
    sentiment_trend: list[float] = []
    intent_forecast: IntentForecastResponse | None = None
    risk_indicators: RiskIndicatorsResponse | None = None
    twin_output: TwinOutputResponse | None = None
    communication_preferences: dict[str, Any] = {}
    confidence_score: float | None = None
    staleness_score: float | None = None
    built_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class TwinSnapshotResponse(BaseModel):
    id: UUID
    twin_id: UUID
    organization_id: UUID
    snapshot_type: str
    snapshot_data: dict[str, Any] = {}
    scores: dict[str, Any] = {}
    valid_from: datetime
    valid_until: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class PredictionResponse(BaseModel):
    id: UUID
    customer_id: UUID
    organization_id: UUID
    prediction_type: str
    prediction_value: float
    prediction_probability: float | None = None
    prediction_label: str | None = None
    prediction_explanation: dict[str, Any] = {}
    feature_importance: dict[str, Any] = {}
    confidence_score: float | None = None
    model_version: str
    model_name: str
    input_features: dict[str, Any] = {}
    valid_until: datetime | None = None
    is_active: bool = True
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
