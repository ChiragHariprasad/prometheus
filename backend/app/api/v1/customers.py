from fastapi import APIRouter, Depends, Query, Body, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from app.core.database import get_session
from app.schemas.customer import (
    CustomerCreate,
    CustomerUpdate,
    CustomerResponse,
    CustomerListResponse,
    CustomerProfileResponse,
    CustomerPreferenceResponse,
    CustomerInterestResponse,
    CustomerSegmentResponse,
)
from app.schemas.event import EventResponse
from app.schemas.common import APIResponse, PaginatedResponse
from app.models.customer import Customer, CustomerPreference, CustomerInterest, CustomerSegment, CustomerSegmentMapping
from app.models.event import Event
from app.middleware.auth import get_current_user, get_current_organization
from app.core.exceptions import NotFoundException
from app.services.customer_service import CustomerService

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/", response_model=PaginatedResponse[CustomerListResponse])
async def list_customers(
    session: AsyncSession = Depends(get_session),
    current_user: str = Depends(get_current_user),
    org_id: str = Depends(get_current_organization),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    email: str | None = Query(None),
    tags: str | None = Query(None),
    segment_ids: str | None = Query(None),
    sort_by: str | None = Query(None),
    sort_order: str = Query("desc"),
):
    query = select(Customer).where(Customer.organization_id == org_id)

    if search:
        query = query.where(
            or_(
                Customer.email.ilike(f"%{search}%"),
                Customer.full_name.ilike(f"%{search}%"),
            )
        )
    if email:
        query = query.where(Customer.email.ilike(f"%{email}%"))
    if tags:
        tag_list = [t.strip() for t in tags.split(",")]
        query = query.where(Customer.tags.contains(tag_list))
    if segment_ids:
        seg_ids = [s.strip() for s in segment_ids.split(",")]
        query = query.join(CustomerSegmentMapping).where(
            CustomerSegmentMapping.segment_id.in_(seg_ids)
        )

    total_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(total_query)).scalar() or 0

    order_column = getattr(Customer, sort_by, Customer.created_at) if sort_by else Customer.created_at
    order_fn = order_column.desc if sort_order == "desc" else order_column.asc
    query = query.order_by(order_fn()).offset((page - 1) * page_size).limit(page_size)

    result = await session.execute(query)
    customers = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return PaginatedResponse(
        items=[CustomerListResponse.model_validate(c) for c in customers],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )


@router.post("/", response_model=APIResponse[CustomerResponse])
async def create_customer(
    payload: CustomerCreate,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    existing = await session.execute(
        select(Customer).where(Customer.email == payload.email, Customer.organization_id == org_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Customer with this email already exists")

    customer = Customer(organization_id=org_id, **payload.model_dump(exclude={"segment_ids"}))
    session.add(customer)
    await session.flush()

    if payload.segment_ids:
        seg_result = await session.execute(
            select(CustomerSegment).where(
                CustomerSegment.id.in_(payload.segment_ids),
                CustomerSegment.organization_id == org_id,
            )
        )
        customer.segments = seg_result.scalars().all()

    await session.commit()
    await session.refresh(customer)
    return APIResponse(data=CustomerResponse.model_validate(customer))


@router.post("/batch", response_model=APIResponse)
async def batch_create_customers(
    payload: list[CustomerCreate],
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    service = CustomerService(session)
    count = await service.batch_create(payload, org_id)
    return APIResponse(message=f"{count} customers created successfully")


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: str,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    result = await session.execute(
        select(Customer).where(Customer.id == customer_id, Customer.organization_id == org_id)
    )
    customer = result.scalar_one_or_none()
    if not customer:
        raise NotFoundException("Customer not found")
    return CustomerResponse.model_validate(customer)


@router.put("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: str,
    payload: CustomerUpdate,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    result = await session.execute(
        select(Customer).where(Customer.id == customer_id, Customer.organization_id == org_id)
    )
    customer = result.scalar_one_or_none()
    if not customer:
        raise NotFoundException("Customer not found")

    update_data = payload.model_dump(exclude_unset=True, exclude={"segment_ids"})
    for field, value in update_data.items():
        setattr(customer, field, value)

    if payload.segment_ids is not None:
        seg_result = await session.execute(
            select(CustomerSegment).where(
                CustomerSegment.id.in_(payload.segment_ids),
                CustomerSegment.organization_id == org_id,
            )
        )
        customer.segments = seg_result.scalars().all()

    await session.commit()
    await session.refresh(customer)
    return CustomerResponse.model_validate(customer)


@router.delete("/{customer_id}", response_model=APIResponse)
async def delete_customer(
    customer_id: str,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    result = await session.execute(
        select(Customer).where(Customer.id == customer_id, Customer.organization_id == org_id)
    )
    customer = result.scalar_one_or_none()
    if not customer:
        raise NotFoundException("Customer not found")

    customer.is_active = False
    await session.commit()
    return APIResponse(message="Customer deactivated successfully")


@router.get("/{customer_id}/profile", response_model=CustomerProfileResponse)
async def get_customer_profile(
    customer_id: str,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    result = await session.execute(
        select(Customer).where(Customer.id == customer_id, Customer.organization_id == org_id)
    )
    customer = result.scalar_one_or_none()
    if not customer:
        raise NotFoundException("Customer not found")

    service = CustomerService(session)
    profile = await service.get_profile(customer_id)
    return CustomerProfileResponse.model_validate(profile)


@router.get("/{customer_id}/preferences", response_model=CustomerPreferenceResponse)
async def get_customer_preferences(
    customer_id: str,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    result = await session.execute(
        select(CustomerPreference).where(
            CustomerPreference.customer_id == customer_id,
            CustomerPreference.organization_id == org_id,
        )
    )
    pref = result.scalar_one_or_none()
    if not pref:
        raise NotFoundException("Preferences not found for customer")
    return CustomerPreferenceResponse.model_validate(pref)


@router.put("/{customer_id}/preferences", response_model=CustomerPreferenceResponse)
async def update_customer_preferences(
    customer_id: str,
    payload: dict,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    result = await session.execute(
        select(CustomerPreference).where(
            CustomerPreference.customer_id == customer_id,
            CustomerPreference.organization_id == org_id,
        )
    )
    pref = result.scalar_one_or_none()
    if not pref:
        pref = CustomerPreference(customer_id=customer_id, organization_id=org_id)
        session.add(pref)

    for field, value in payload.items():
        setattr(pref, field, value)
    await session.commit()
    await session.refresh(pref)
    return CustomerPreferenceResponse.model_validate(pref)


@router.get("/{customer_id}/interests", response_model=list[CustomerInterestResponse])
async def get_customer_interests(
    customer_id: str,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    result = await session.execute(
        select(CustomerInterest).where(
            CustomerInterest.customer_id == customer_id,
            CustomerInterest.organization_id == org_id,
        )
    )
    interests = result.scalars().all()
    return [CustomerInterestResponse.model_validate(i) for i in interests]


@router.get("/{customer_id}/events", response_model=PaginatedResponse[EventResponse])
async def get_customer_events(
    customer_id: str,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    query = select(Event).where(
        Event.customer_id == customer_id,
        Event.organization_id == org_id,
    ).order_by(Event.created_at.desc())

    total_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(total_query)).scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    events = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return PaginatedResponse(
        items=[EventResponse.model_validate(e) for e in events],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )


@router.get("/{customer_id}/segments", response_model=list[CustomerSegmentResponse])
async def get_customer_segments(
    customer_id: str,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    result = await session.execute(
        select(CustomerSegment)
        .join(CustomerSegmentMapping)
        .where(
            CustomerSegmentMapping.customer_id == customer_id,
            CustomerSegment.organization_id == org_id,
        )
    )
    segments = result.scalars().all()
    return [CustomerSegmentResponse.model_validate(s) for s in segments]


@router.post("/{customer_id}/merge", response_model=APIResponse)
async def merge_customers(
    customer_id: str,
    duplicate_ids: list[str] = Body(...),
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    service = CustomerService(session)
    await service.merge_customers(customer_id, duplicate_ids, org_id)
    return APIResponse(message="Customers merged successfully")
