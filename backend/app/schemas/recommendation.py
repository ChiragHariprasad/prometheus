from datetime import datetime
from uuid import UUID
from typing import Any

from pydantic import BaseModel, ConfigDict


class RecommendationResponse(BaseModel):
    id: UUID
    customer_id: UUID
    type: str
    title: str
    description: str | None = None
    score: float | None = None
    rank: int | None = None
    category: str | None = None
    metadata: dict[str, Any] = {}
    is_actionable: bool = False
    is_applied: bool = False
    applied_at: datetime | None = None
    source: str | None = None
    expires_at: datetime | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class RecommendationFeedback(BaseModel):
    recommendation_id: UUID | str
    feedback_type: str
