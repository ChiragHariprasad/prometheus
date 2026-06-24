import uuid
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
from app.models.twin import CustomerTwin
from app.models.event import Event
from app.middleware.auth import get_current_user, get_current_organization
from app.core.exceptions import NotFoundException
from app.services.customer_service import CustomerService


def _validate_uuid(customer_id: str) -> None:
    try:
        uuid.UUID(customer_id)
    except ValueError:
        raise NotFoundException("Customer")

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("", response_model=PaginatedResponse[CustomerListResponse])
async def list_customers(
    session: AsyncSession = Depends(get_session),
    current_user: str = Depends(get_current_user),
    org_id: str = Depends(get_current_organization),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    limit: int | None = Query(None, description="Alias for page_size"),
    search: str | None = Query(None),
    email: str | None = Query(None),
    tags: str | None = Query(None),
    segment_ids: str | None = Query(None),
    sort_by: str | None = Query(None),
    sort_order: str = Query("desc"),
):
    if limit is not None:
        page_size = limit

    query = select(Customer).where(Customer.organization_id == org_id)

    if search:
        query = query.where(
            or_(
                Customer.email.ilike(f"%{search}%"),
                (Customer.first_name + " " + Customer.last_name).ilike(f"%{search}%"),
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

    customer_ids = [c.id for c in customers]
    twin_map: dict[str, CustomerTwin] = {}
    if customer_ids:
        twin_result = await session.execute(
            select(CustomerTwin).where(
                CustomerTwin.customer_id.in_(customer_ids),
                CustomerTwin.organization_id == org_id,
            )
        )
        twin_map = {str(t.customer_id): t for t in twin_result.scalars().all()}

    segment_map: dict[str, list[str]] = {}
    if customer_ids:
        seg_result = await session.execute(
            select(CustomerSegmentMapping).where(
                CustomerSegmentMapping.customer_id.in_(customer_ids),
                CustomerSegmentMapping.organization_id == org_id,
            )
        )
        for m in seg_result.scalars().all():
            segment_map.setdefault(str(m.customer_id), []).append(str(m.segment_id))

    items = []
    for c in customers:
        twin = twin_map.get(str(c.id))
        churn_risk = "low"
        if twin:
            if twin.engagement_score is not None and twin.engagement_score < 0.3:
                churn_risk = "high"
            elif twin.engagement_score is not None and twin.engagement_score < 0.5:
                churn_risk = "medium"
        items.append(CustomerListResponse(
            id=c.id,
            organization_id=c.organization_id,
            external_id=c.external_id,
            email=c.email,
            phone=c.phone,
            first_name=c.first_name,
            last_name=c.last_name,
            name=f"{c.first_name or ''} {c.last_name or ''}".strip() or c.email or "",
            date_of_birth=c.date_of_birth,
            gender=c.gender,
            timezone=c.timezone,
            locale=c.locale,
            location=c.location,
            tags=c.tags or [],
            custom_attributes=c.custom_attributes or {},
            is_active=c.is_active,
            consent_marketing=c.consent_marketing,
            consent_analytics=c.consent_analytics,
            consent_profiling=c.consent_profiling,
            source=c.source,
            first_seen_at=c.first_seen_at,
            last_seen_at=c.last_seen_at,
            created_at=c.created_at,
            updated_at=c.updated_at,
            engagement_score=twin.engagement_score if twin and twin.engagement_score is not None else 0.0,
            loyalty_score=twin.loyalty_score if twin and twin.loyalty_score is not None else 0.0,
            churn_risk=churn_risk,
            ltv=twin.lifetime_value if twin and twin.lifetime_value is not None else 0.0,
            last_activity=twin.last_event_at if twin else c.last_seen_at,
            segments=segment_map.get(str(c.id), []),
        ))

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return PaginatedResponse(
        data=items,
        total=total,
        page=page,
        page_size=page_size,
        limit=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )


@router.post("", response_model=APIResponse[CustomerResponse])
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


    await session.refresh(customer)
    return APIResponse(data=CustomerResponse.model_validate(customer))


@router.get("/search", response_model=list[CustomerListResponse])
async def search_customers(
    q: str = Query(""),
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
    limit: int = Query(20, ge=1, le=100),
):
    if not q:
        return []

    query = (
        select(Customer)
        .where(
            Customer.organization_id == org_id,
            Customer.is_active == True,
            or_(
                Customer.email.ilike(f"%{q}%"),
                Customer.first_name.ilike(f"%{q}%"),
                Customer.last_name.ilike(f"%{q}%"),
                Customer.external_id.ilike(f"%{q}%"),
            ),
        )
        .limit(limit)
    )
    result = await session.execute(query)
    customers = list(result.scalars().all())
    
    # We should populate CustomerListResponse correctly just like list_customers does, or use model_validate
    # Let's populate the fields using a mapping just in case, but model_validate also works now that memory_profile is fixed.
    # Wait, list_customers fetch segment maps and twin maps. Let's do model_validate as it was originally written, since it's now working.
    return [CustomerListResponse.model_validate(c) for c in customers]


@router.post("/batch", response_model=APIResponse)
async def batch_create_customers(
    payload: list[CustomerCreate],
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    service = CustomerService(session)
    count = await service.batch_create(payload, org_id)
    return APIResponse(message=f"{count} customers created successfully")


@router.get("/new")
async def new_customer():
    return {"message": "New customer template"}



@router.get("/{customer_id}", response_model=CustomerListResponse)
async def get_customer(
    customer_id: str,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    _validate_uuid(customer_id)
    result = await session.execute(
        select(Customer).where(Customer.id == customer_id, Customer.organization_id == org_id)
    )
    customer = result.scalar_one_or_none()
    if not customer:
        raise NotFoundException("Customer not found")
    twin_result = await session.execute(
        select(CustomerTwin).where(
            CustomerTwin.customer_id == customer.id,
            CustomerTwin.organization_id == org_id,
        )
    )
    twin = twin_result.scalar_one_or_none()
    churn_risk = "low"
    if twin:
        if twin.engagement_score is not None and twin.engagement_score < 0.3:
            churn_risk = "high"
        elif twin.engagement_score is not None and twin.engagement_score < 0.5:
            churn_risk = "medium"
    return CustomerListResponse(
        id=customer.id,
        organization_id=customer.organization_id,
        external_id=customer.external_id,
        email=customer.email,
        phone=customer.phone,
        first_name=customer.first_name,
        last_name=customer.last_name,
        name=f"{customer.first_name or ''} {customer.last_name or ''}".strip() or customer.email or "",
        date_of_birth=customer.date_of_birth,
        gender=customer.gender,
        timezone=customer.timezone,
        locale=customer.locale,
        location=customer.location,
        tags=customer.tags or [],
        custom_attributes=customer.custom_attributes or {},
        is_active=customer.is_active,
        consent_marketing=customer.consent_marketing,
        consent_analytics=customer.consent_analytics,
        consent_profiling=customer.consent_profiling,
        source=customer.source,
        first_seen_at=customer.first_seen_at,
        last_seen_at=customer.last_seen_at,
        created_at=customer.created_at,
        updated_at=customer.updated_at,
        engagement_score=twin.engagement_score if twin and twin.engagement_score is not None else 0.0,
        loyalty_score=twin.loyalty_score if twin and twin.loyalty_score is not None else 0.0,
        churn_risk=churn_risk,
        ltv=twin.lifetime_value if twin and twin.lifetime_value is not None else 0.0,
        last_activity=twin.last_event_at if twin else customer.last_seen_at,
    )


@router.put("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: str,
    payload: CustomerUpdate,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    _validate_uuid(customer_id)
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


    await session.refresh(customer)
    return CustomerResponse.model_validate(customer)


@router.delete("/{customer_id}", response_model=APIResponse)
async def delete_customer(
    customer_id: str,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    _validate_uuid(customer_id)
    result = await session.execute(
        select(Customer).where(Customer.id == customer_id, Customer.organization_id == org_id)
    )
    customer = result.scalar_one_or_none()
    if not customer:
        raise NotFoundException("Customer not found")

    customer.is_active = False

    return APIResponse(message="Customer deactivated successfully")


@router.get("/{customer_id}/profile", response_model=CustomerProfileResponse)
async def get_customer_profile(
    customer_id: str,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    _validate_uuid(customer_id)
    result = await session.execute(
        select(Customer).where(Customer.id == customer_id, Customer.organization_id == org_id)
    )
    customer = result.scalar_one_or_none()
    if not customer:
        raise NotFoundException("Customer not found")

    service = CustomerService(session)
    profile = await service.get_profile(uuid.UUID(customer_id), uuid.UUID(org_id))
    if not profile:
        raise NotFoundException("Customer profile not found")
    return CustomerProfileResponse.model_validate(profile)


@router.get("/{customer_id}/preferences", response_model=CustomerPreferenceResponse)
async def get_customer_preferences(
    customer_id: str,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    _validate_uuid(customer_id)
    result = await session.execute(
        select(CustomerPreference).where(
            CustomerPreference.customer_id == uuid.UUID(customer_id),
            CustomerPreference.organization_id == uuid.UUID(org_id),
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
    _validate_uuid(customer_id)
    result = await session.execute(
        select(CustomerPreference).where(
            CustomerPreference.customer_id == uuid.UUID(customer_id),
            CustomerPreference.organization_id == uuid.UUID(org_id),
        )
    )
    pref = result.scalar_one_or_none()
    if not pref:
        pref = CustomerPreference(customer_id=customer_id, organization_id=org_id)
        session.add(pref)
        await session.flush()

    for field, value in payload.items():
        setattr(pref, field, value)

    await session.refresh(pref)
    return CustomerPreferenceResponse.model_validate(pref)


@router.get("/{customer_id}/interests", response_model=list[CustomerInterestResponse])
async def get_customer_interests(
    customer_id: str,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    _validate_uuid(customer_id)
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
    _validate_uuid(customer_id)
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
        data=[EventResponse.model_validate(e) for e in events],
        total=total,
        page=page,
        page_size=page_size,
        limit=page_size,
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
    _validate_uuid(customer_id)
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
    _validate_uuid(customer_id)
    primary_uuid = uuid.UUID(customer_id)
    org_uuid = uuid.UUID(org_id)
    service = CustomerService(session)
    for dup_id in duplicate_ids:
        await service.merge_customers(
            primary_id=primary_uuid,
            secondary_id=uuid.UUID(dup_id),
            organization_id=org_uuid,
        )
    return APIResponse(message="Customers merged successfully")
