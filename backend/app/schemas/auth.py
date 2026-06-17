from datetime import datetime
from uuid import UUID
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator, model_validator


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

    model_config = ConfigDict(from_attributes=True)


class LoginResponse(TokenResponse):
    user: "AuthUserResponse"

    model_config = ConfigDict(from_attributes=True)


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    mfa_code: str | None = None


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    organization_name: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def new_password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("New password must be at least 8 characters long")
        return v


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def new_password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("New password must be at least 8 characters long")
        return v


class MFASetupResponse(BaseModel):
    secret: str
    qr_code_url: str

    model_config = ConfigDict(from_attributes=True)


class MFAVerifyRequest(BaseModel):
    code: str


class AuthUserResponse(BaseModel):
    id: UUID
    email: str
    first_name: str
    last_name: str
    name: str = ""
    organization_id: UUID
    roles: list[str] = []
    permissions: list[str] = []

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def set_name(self):
        if not self.name and self.first_name:
            self.name = f"{self.first_name} {self.last_name}".strip()
        return self
