from datetime import datetime
from uuid import UUID
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


class EventCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    customer_id: str | None = None
    event_type: str
    event_name: str
    event_properties: dict[str, Any] = {}
    context: dict[str, Any] = {}
    channel: str | None = None
    source: str | None = None
    device_type: str | None = None
    device_os: str | None = None
    browser: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    referrer: str | None = None
    url: str | None = None
    geolocation: dict[str, Any] | None = None
    campaign_id: str | None = None
    value: float | None = None
    currency: str | None = None
    event_timestamp: datetime | None = None


class EventResponse(BaseModel):
    id: UUID
    organization_id: UUID
    customer_id: UUID | None = None
    session_id: str | None = None
    event_type: str
    event_name: str
    event_properties: dict[str, Any] = {}
    context: dict[str, Any] = {}
    channel: str | None = None
    source: str | None = None
    device_type: str | None = None
    device_os: str | None = None
    browser: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    referrer: str | None = None
    url: str | None = None
    geolocation: dict[str, Any] | None = None
    campaign_id: str | None = None
    value: float | None = None
    currency: str | None = None
    processed: bool = False
    event_timestamp: datetime | None = None
    ingested_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class BatchEventRequest(BaseModel):
    events: list[EventCreate]


class EventSearchParams(BaseModel):
    event_type: str | None = None
    channel: str | None = None
    source: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    customer_id: UUID | None = None
    session_id: str | None = None
    page: int = 1
    page_size: int = 20


class EventTypeResponse(BaseModel):
    event_type: str
    count: int = 0

    model_config = ConfigDict(from_attributes=True)


class EventSummaryResponse(BaseModel):
    event_type: str
    count: int = 0

    model_config = ConfigDict(from_attributes=True)
