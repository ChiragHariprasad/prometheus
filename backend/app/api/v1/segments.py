from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_session
from app.schemas.customer import CustomerSegmentResponse, CustomerResponse
from app.schemas.common import APIResponse, PaginatedResponse
from app.models.customer import CustomerSegment, Customer, CustomerSegmentMapping
from app.middleware.auth import get_current_user, get_current_organization
from app.core.exceptions import NotFoundException
from app.services.segment_service import SegmentService

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/", response_model=PaginatedResponse[CustomerSegmentResponse])
async def list_segments(
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    sort_by: str | None = Query(None),
    sort_order: str = Query("desc"),
):
    query = select(CustomerSegment).where(CustomerSegment.organization_id == org_id)

    if search:
        query = query.where(CustomerSegment.name.ilike(f"%{search}%"))

    total_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(total_query)).scalar() or 0

    order_column = getattr(CustomerSegment, sort_by, CustomerSegment.created_at) if sort_by else CustomerSegment.created_at
    order_fn = order_column.desc if sort_order == "desc" else order_column.asc
    query = query.order_by(order_fn()).offset((page - 1) * page_size).limit(page_size)

    result = await session.execute(query)
    segments = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return PaginatedResponse(
        items=[CustomerSegmentResponse.model_validate(s) for s in segments],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )


@router.post("/", response_model=APIResponse[CustomerSegmentResponse])
async def create_segment(
    payload: dict,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    segment = CustomerSegment(organization_id=org_id, **payload)
    session.add(segment)
    await session.commit()
    await session.refresh(segment)

    service = SegmentService(session)
    await service.recalculate_membership(segment.id, org_id)

    return APIResponse(data=CustomerSegmentResponse.model_validate(segment))


@router.get("/{segment_id}", response_model=CustomerSegmentResponse)
async def get_segment(
    segment_id: str,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    result = await session.execute(
        select(CustomerSegment).where(
            CustomerSegment.id == segment_id,
            CustomerSegment.organization_id == org_id,
        )
    )
    segment = result.scalar_one_or_none()
    if not segment:
        raise NotFoundException("Segment not found")
    return CustomerSegmentResponse.model_validate(segment)


@router.put("/{segment_id}", response_model=CustomerSegmentResponse)
async def update_segment(
    segment_id: str,
    payload: dict,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    result = await session.execute(
        select(CustomerSegment).where(
            CustomerSegment.id == segment_id,
            CustomerSegment.organization_id == org_id,
        )
    )
    segment = result.scalar_one_or_none()
    if not segment:
        raise NotFoundException("Segment not found")

    for field, value in payload.items():
        setattr(segment, field, value)
    await session.commit()
    await session.refresh(segment)
    return CustomerSegmentResponse.model_validate(segment)


@router.delete("/{segment_id}", response_model=APIResponse)
async def delete_segment(
    segment_id: str,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    result = await session.execute(
        select(CustomerSegment).where(
            CustomerSegment.id == segment_id,
            CustomerSegment.organization_id == org_id,
        )
    )
    segment = result.scalar_one_or_none()
    if not segment:
        raise NotFoundException("Segment not found")

    await session.delete(segment)
    await session.commit()
    return APIResponse(message="Segment deleted successfully")


@router.post("/{segment_id}/refresh", response_model=APIResponse)
async def refresh_segment(
    segment_id: str,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    result = await session.execute(
        select(CustomerSegment).where(
            CustomerSegment.id == segment_id,
            CustomerSegment.organization_id == org_id,
        )
    )
    segment = result.scalar_one_or_none()
    if not segment:
        raise NotFoundException("Segment not found")

    service = SegmentService(session)
    await service.recalculate_membership(segment.id, org_id)
    return APIResponse(message="Segment membership recalculated")


@router.get("/{segment_id}/customers", response_model=PaginatedResponse[CustomerResponse])
async def get_segment_customers(
    segment_id: str,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    query = (
        select(Customer)
        .join(CustomerSegmentMapping)
        .where(
            CustomerSegmentMapping.segment_id == segment_id,
            Customer.organization_id == org_id,
        )
    )

    total_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(total_query)).scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    customers = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return PaginatedResponse(
        items=[CustomerResponse.model_validate(c) for c in customers],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )


@router.post("/{segment_id}/lookalike", response_model=APIResponse[CustomerSegmentResponse])
async def create_lookalike_segment(
    segment_id: str,
    payload: dict,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    result = await session.execute(
        select(CustomerSegment).where(
            CustomerSegment.id == segment_id,
            CustomerSegment.organization_id == org_id,
        )
    )
    seed_segment = result.scalar_one_or_none()
    if not seed_segment:
        raise NotFoundException("Seed segment not found")

    service = SegmentService(session)
    lookalike = await service.create_lookalike(seed_segment, payload, org_id)
    return APIResponse(data=CustomerSegmentResponse.model_validate(lookalike))


@router.post("/compute", response_model=APIResponse)
async def compute_all_segments(
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    service = SegmentService(session)
    await service.compute_all(org_id)
    return APIResponse(message="Segmentation computation triggered")
