from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast, Date
from datetime import date, datetime
from app.core.database import get_session
from app.schemas.event import (
    EventCreate,
    EventResponse,
    BatchEventRequest,
    EventSearchParams,
    EventTypeResponse,
    EventSummaryResponse,
)
from app.schemas.common import APIResponse, PaginatedResponse
from app.models.event import Event
from app.models.customer import Customer
from app.middleware.auth import get_current_user, get_current_organization
from app.core.exceptions import NotFoundException
from app.services.event_service import EventService

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.post("", response_model=APIResponse[EventResponse])
async def create_event(
    payload: EventCreate,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    customer_check = await session.execute(
        select(Customer).where(
            Customer.id == payload.customer_id,
            Customer.organization_id == org_id,
        )
    )
    if not customer_check.scalar_one_or_none():
        raise NotFoundException("Customer not found")

    event = Event(organization_id=org_id, **payload.model_dump())
    session.add(event)

    await session.refresh(event)
    return APIResponse(data=EventResponse.model_validate(event))


@router.post("/batch", response_model=APIResponse)
async def batch_ingest_events(
    payload: BatchEventRequest,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    service = EventService(session)
    count = await service.batch_ingest(payload.events, org_id)
    return APIResponse(message=f"{count} events ingested successfully")


@router.get("/", response_model=PaginatedResponse[EventResponse])
async def list_events(
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    customer_id: str | None = Query(None),
    event_type: str | None = Query(None),
    source: str | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    search: str | None = Query(None),
    sort_by: str | None = Query(None),
    sort_order: str = Query("desc"),
):
    query = select(Event).where(Event.organization_id == org_id)

    if customer_id:
        query = query.where(Event.customer_id == customer_id)
    if event_type:
        query = query.where(Event.event_type == event_type)
    if source:
        query = query.where(Event.source == source)
    if start_date:
        query = query.where(cast(Event.created_at, Date) >= start_date)
    if end_date:
        query = query.where(cast(Event.created_at, Date) <= end_date)
    if search:
        query = query.where(
            Event.event_properties.astext.ilike(f"%{search}%")
        )

    total_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(total_query)).scalar() or 0

    order_column = getattr(Event, sort_by, Event.created_at) if sort_by else Event.created_at
    order_fn = order_column.desc if sort_order == "desc" else order_column.asc
    query = query.order_by(order_fn()).offset((page - 1) * page_size).limit(page_size)

    result = await session.execute(query)
    events = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return PaginatedResponse(
        data=[EventResponse.model_validate(e) for e in events],
        total=total,
        page=page,
        page_size=page_size,
        limit=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: str,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    result = await session.execute(
        select(Event).where(Event.id == event_id, Event.organization_id == org_id)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise NotFoundException("Event not found")
    return EventResponse.model_validate(event)


@router.get("/types", response_model=list[EventTypeResponse])
async def list_event_types(
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    result = await session.execute(
        select(Event.event_type, func.count().label("count"))
        .where(Event.organization_id == org_id)
        .group_by(Event.event_type)
    )
    rows = result.all()
    return [EventTypeResponse(event_type=row.event_type, count=row.count) for row in rows]


@router.get("/summary", response_model=list[EventSummaryResponse])
async def get_event_summary(
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
    start_date: date = Query(...),
    end_date: date = Query(...),
):
    result = await session.execute(
        select(
            Event.event_type,
            func.count().label("count"),
        )
        .where(
            Event.organization_id == org_id,
            cast(Event.created_at, Date) >= start_date,
            cast(Event.created_at, Date) <= end_date,
        )
        .group_by(Event.event_type)
    )
    rows = result.all()
    return [
        EventSummaryResponse(event_type=row.event_type, count=row.count)
        for row in rows
    ]
