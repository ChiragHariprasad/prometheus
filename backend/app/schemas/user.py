from datetime import datetime
from uuid import UUID
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    job_title: str | None = None
    department: str | None = None
    phone: str | None = None

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v


class UserUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    job_title: str | None = None
    department: str | None = None
    phone: str | None = None
    is_active: bool | None = None


class UserResponse(BaseModel):
    id: UUID
    organization_id: UUID
    email: str
    first_name: str
    last_name: str
    job_title: str | None = None
    department: str | None = None
    phone: str | None = None
    is_active: bool
    is_verified: bool
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RoleCreate(BaseModel):
    name: str
    description: str | None = None
    permissions: list[dict[str, Any]] = []


class RoleResponse(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    is_system: bool
    permissions: list[dict[str, Any]] = []

    model_config = ConfigDict(from_attributes=True)


class PermissionResponse(BaseModel):
    resource: str
    action: str
    conditions: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)
