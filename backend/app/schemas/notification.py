from datetime import datetime
from uuid import UUID
from typing import Any

from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    id: UUID
    customer_id: UUID | None = None
    user_id: UUID | None = None
    type: str
    title: str
    body: str
    channel: str
    status: str | None = None
    priority: str | None = None
    campaign_id: str | None = None
    scheduled_at: datetime | None = None
    sent_at: datetime | None = None
    delivered_at: datetime | None = None
    opened_at: datetime | None = None
    clicked_at: datetime | None = None
    failed_at: datetime | None = None
    failure_reason: str | None = None
    retry_count: int = 0
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class NotificationSendRequest(BaseModel):
    type: str
    title: str
    body: str
    channel: str
    customer_ids: list[str]
    template_id: str | None = None
    template_data: dict[str, Any] = {}
    scheduled_at: datetime | None = None


class NotificationStatsResponse(BaseModel):
    total: int = 0
    sent: int = 0
    delivered: int = 0
    opened: int = 0
    delivery_rate: float = 0.0
    open_rate: float = 0.0
