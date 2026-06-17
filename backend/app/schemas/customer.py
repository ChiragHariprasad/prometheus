from datetime import datetime, date
from uuid import UUID
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


class CustomerCreate(BaseModel):
    external_id: str | None = None
    email: str | None = None
    phone: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    timezone: str = "UTC"
    locale: str = "en-US"
    location: dict[str, Any] | None = None
    tags: list[str] = []
    custom_attributes: dict[str, Any] = {}
    consent_marketing: bool = False
    consent_analytics: bool = True
    consent_profiling: bool = False


class CustomerUpdate(BaseModel):
    external_id: str | None = None
    email: str | None = None
    phone: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    timezone: str | None = None
    locale: str | None = None
    location: dict[str, Any] | None = None
    tags: list[str] | None = None
    custom_attributes: dict[str, Any] | None = None
    is_active: bool | None = None
    consent_marketing: bool | None = None
    consent_analytics: bool | None = None
    consent_profiling: bool | None = None


class CustomerResponse(BaseModel):
    id: UUID
    organization_id: UUID
    external_id: str | None = None
    email: str | None = None
    phone: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    timezone: str
    locale: str
    location: dict[str, Any] | None = None
    tags: list[str] = []
    custom_attributes: dict[str, Any] = {}
    is_active: bool
    consent_marketing: bool
    consent_analytics: bool
    consent_profiling: bool
    source: str | None = None
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustomerProfileResponse(BaseModel):
    id: UUID
    customer_id: UUID
    title: str | None = None
    company: str | None = None
    industry: str | None = None
    annual_revenue: float | None = None
    employee_count: int | None = None
    website: str | None = None
    linkedin_url: str | None = None
    twitter_handle: str | None = None
    bio: str | None = None
    avatar_url: str | None = None
    preferred_language: str | None = None
    communication_style: str | None = None
    personality_traits: dict[str, Any] | None = None
    psychographic_segment: str | None = None
    enrichment_status: str | None = None
    last_enriched_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class CustomerPreferenceResponse(BaseModel):
    id: UUID
    customer_id: UUID
    channel_email: bool = True
    channel_sms: bool = True
    channel_push: bool = True
    channel_in_app: bool = True
    email_frequency: str | None = None
    sms_frequency: str | None = None
    push_frequency: str | None = None
    quiet_hours_start: str | None = None
    quiet_hours_end: str | None = None
    timezone: str | None = None
    preferred_categories: list[str] = []
    preferred_brands: list[str] = []
    excluded_categories: list[str] = []
    max_communications_per_day: int | None = None
    do_not_disturb: bool = False

    model_config = ConfigDict(from_attributes=True)


class CustomerInterestResponse(BaseModel):
    id: UUID
    customer_id: UUID
    category: str
    subcategory: str | None = None
    interest_level: float | None = None
    affinity_score: float | None = None
    interaction_count: int = 0
    last_interaction_at: datetime | None = None
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class CustomerSegmentResponse(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    source: str | None = None
    rules: dict[str, Any] | None = None
    customer_count: int = 0
    is_active: bool = True
    is_dynamic: bool = False
    refresh_interval_minutes: int | None = None
    last_refreshed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class CustomerListResponse(CustomerResponse):
    twin_summary: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)
