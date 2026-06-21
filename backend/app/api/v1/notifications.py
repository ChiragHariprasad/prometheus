from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_session
from app.schemas.notification import (
    NotificationResponse,
    NotificationSendRequest,
    NotificationStatsResponse,
)
from app.schemas.common import APIResponse, PaginatedResponse
from app.models.notification import Notification
from app.middleware.auth import get_current_user, get_current_organization
from app.core.exceptions import NotFoundException
from app.services.notification_service import NotificationService

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("", response_model=PaginatedResponse[NotificationResponse])
async def list_notifications(
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    customer_id: str | None = Query(None),
    status: str | None = Query(None),
    channel: str | None = Query(None),
    sort_by: str | None = Query(None),
    sort_order: str = Query("desc"),
):
    query = select(Notification).where(Notification.organization_id == org_id)

    if customer_id:
        query = query.where(Notification.customer_id == customer_id)
    if status:
        query = query.where(Notification.status == status)
    if channel:
        query = query.where(Notification.channel == channel)

    total_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(total_query)).scalar() or 0

    order_column = getattr(Notification, sort_by, Notification.created_at) if sort_by else Notification.created_at
    order_fn = order_column.desc if sort_order == "desc" else order_column.asc
    query = query.order_by(order_fn()).offset((page - 1) * page_size).limit(page_size)

    result = await session.execute(query)
    notifications = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return PaginatedResponse(
        data=[NotificationResponse.model_validate(n) for n in notifications],
        total=total,
        page=page,
        page_size=page_size,
        limit=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )


@router.post("", response_model=APIResponse)
async def send_notification(
    payload: NotificationSendRequest,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    notification = Notification(organization_id=org_id, **payload.model_dump())
    session.add(notification)
    await session.commit()
    await session.refresh(notification)

    service = NotificationService(session)
    await service.send(notification)

    return APIResponse(message="Notification sent successfully")


@router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(
    notification_id: str,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    result = await session.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.organization_id == org_id,
        )
    )
    notification = result.scalar_one_or_none()
    if not notification:
        raise NotFoundException("Notification not found")
    return NotificationResponse.model_validate(notification)


@router.post("/{notification_id}/retry", response_model=APIResponse)
async def retry_notification(
    notification_id: str,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    result = await session.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.organization_id == org_id,
        )
    )
    notification = result.scalar_one_or_none()
    if not notification:
        raise NotFoundException("Notification not found")

    service = NotificationService(session)
    await service.retry(notification)
    return APIResponse(message="Notification retry initiated")


@router.get("/stats", response_model=NotificationStatsResponse)
async def get_notification_stats(
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    total_query = select(func.count()).select_from(
        select(Notification).where(Notification.organization_id == org_id).subquery()
    )
    total = (await session.execute(total_query)).scalar() or 0

    sent_query = select(func.count()).select_from(
        select(Notification).where(
            Notification.organization_id == org_id,
            Notification.status == "sent",
        ).subquery()
    )
    sent = (await session.execute(sent_query)).scalar() or 0

    delivered_query = select(func.count()).select_from(
        select(Notification).where(
            Notification.organization_id == org_id,
            Notification.status == "delivered",
        ).subquery()
    )
    delivered = (await session.execute(delivered_query)).scalar() or 0

    opened_query = select(func.count()).select_from(
        select(Notification).where(
            Notification.organization_id == org_id,
            Notification.status == "opened",
        ).subquery()
    )
    opened = (await session.execute(opened_query)).scalar() or 0

    return NotificationStatsResponse(
        total=total,
        sent=sent,
        delivered=delivered,
        opened=opened,
        delivery_rate=(delivered / total * 100) if total > 0 else 0.0,
        open_rate=(opened / delivered * 100) if delivered > 0 else 0.0,
    )
