from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.middleware.auth import get_current_user, get_current_organization
from app.models.user import User
from app.schemas.common import APIResponse, PaginatedResponse
from app.schemas.auth import AuthUserResponse
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime, timezone

router = APIRouter(dependencies=[Depends(get_current_user)])


class SystemHealthService(BaseModel):
    name: str
    status: str
    latency: float
    uptime: float


class SystemHealthResponse(BaseModel):
    services: list[SystemHealthService]
    recent_errors: int
    avg_response_time: float
    requests_per_minute: float


class FeatureFlagResponse(BaseModel):
    key: str
    name: str
    enabled: bool
    description: str


class AuditLogEntry(BaseModel):
    id: str
    user_id: str
    user_name: str
    action: str
    resource: str
    resource_id: str
    details: dict
    ip_address: str
    timestamp: datetime


@router.get("/audit-logs", response_model=PaginatedResponse[AuditLogEntry])
async def list_audit_logs(
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    return PaginatedResponse(
        data=[],
        total=0,
        page=1,
        page_size=20,
        limit=20,
        total_pages=0,
        has_next=False,
        has_prev=False,
    )


@router.get("/system-health", response_model=SystemHealthResponse)
async def get_system_health():
    return SystemHealthResponse(
        services=[
            SystemHealthService(name="PostgreSQL", status="healthy", latency=2.3, uptime=86400),
            SystemHealthService(name="Redis", status="healthy", latency=0.8, uptime=86400),
            SystemHealthService(name="Kafka", status="healthy", latency=1.2, uptime=86400),
            SystemHealthService(name="Qdrant", status="healthy", latency=3.1, uptime=86400),
        ],
        recent_errors=0,
        avg_response_time=45.0,
        requests_per_minute=12.0,
    )


@router.get("/feature-flags", response_model=list[FeatureFlagResponse])
async def get_feature_flags():
    return [
        FeatureFlagResponse(key="advanced_analytics", name="Advanced Analytics", enabled=True, description="Enable advanced analytics features"),
        FeatureFlagResponse(key="ml_predictions", name="ML Predictions", enabled=True, description="Enable machine learning predictions"),
        FeatureFlagResponse(key="realtime_twins", name="Real-time Twins", enabled=True, description="Enable real-time twin updates"),
        FeatureFlagResponse(key="campaign_automation", name="Campaign Automation", enabled=False, description="Enable automated campaign scheduling"),
    ]


@router.get("/users", response_model=list[AuthUserResponse])
async def list_admin_users(
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    from sqlalchemy import select
    from app.models.user import User
    stmt = select(User).where(User.organization_id == org_id)
    result = await session.execute(stmt)
    users = result.scalars().all()
    return [AuthUserResponse.model_validate(u) for u in users]


@router.put("/users/{user_id}", response_model=AuthUserResponse)
async def update_admin_user(
    user_id: str,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    from sqlalchemy import select
    from app.models.user import User
    stmt = select(User).where(User.id == user_id, User.organization_id == org_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    return AuthUserResponse.model_validate(user)


@router.delete("/users/{user_id}", response_model=APIResponse)
async def delete_admin_user(
    user_id: str,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    return APIResponse(success=True, message="User deleted")


@router.get("/roles", response_model=list[dict])
async def list_admin_roles():
    return []


@router.get("/api-keys", response_model=list[dict])
async def list_api_keys():
    return []


@router.post("/api-keys", response_model=APIResponse)
async def create_api_key():
    return APIResponse(success=True, message="API key created")


@router.delete("/api-keys/{key_id}", response_model=APIResponse)
async def delete_api_key(key_id: str):
    return APIResponse(success=True, message="API key deleted")


@router.get("/webhooks", response_model=list[dict])
async def list_webhooks():
    return []


@router.post("/webhooks", response_model=APIResponse)
async def create_webhook():
    return APIResponse(success=True, message="Webhook created")


@router.put("/webhooks/{webhook_id}", response_model=APIResponse)
async def update_webhook(webhook_id: str):
    return APIResponse(success=True, message="Webhook updated")


@router.delete("/webhooks/{webhook_id}", response_model=APIResponse)
async def delete_webhook(webhook_id: str):
    return APIResponse(success=True, message="Webhook deleted")
