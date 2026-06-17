from pydantic import BaseModel, ConfigDict
from typing import Any, Generic, TypeVar
from datetime import datetime

T = TypeVar('T')


class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 20
    sort_by: str | None = None
    sort_order: str = "desc"


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


class APIResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T | None = None
    error: str | None = None
    message: str | None = None
    request_id: str | None = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    error_code: str | None = None
    details: dict[str, Any] | None = None
    request_id: str | None = None


class HealthResponse(BaseModel):
    status: str
    version: str
    uptime_seconds: float
    services: dict[str, str]
