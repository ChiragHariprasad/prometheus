from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_session
from app.schemas.recommendation import (
    RecommendationResponse,
    RecommendationFeedback,
)
from app.schemas.common import APIResponse, PaginatedResponse
from app.models.recommendation import Recommendation, RecommendationFeedback as RecFeedback
from app.models.customer import Customer
from app.middleware.auth import get_current_user, get_current_organization
from app.core.exceptions import NotFoundException
from app.services.recommendation_service import RecommendationService

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("", response_model=PaginatedResponse[RecommendationResponse])
async def list_recommendations(
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    customer_id: str | None = Query(None),
    recommendation_type: str | None = Query(None),
    status: str | None = Query(None),
    sort_by: str | None = Query(None),
    sort_order: str = Query("desc"),
):
    query = select(Recommendation).where(Recommendation.organization_id == org_id)

    if customer_id:
        query = query.where(Recommendation.customer_id == customer_id)
    if recommendation_type:
        query = query.where(Recommendation.recommendation_type == recommendation_type)
    if status:
        query = query.where(Recommendation.status == status)

    total_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(total_query)).scalar() or 0

    order_column = getattr(Recommendation, sort_by, Recommendation.created_at) if sort_by else Recommendation.created_at
    order_fn = order_column.desc if sort_order == "desc" else order_column.asc
    query = query.order_by(order_fn()).offset((page - 1) * page_size).limit(page_size)

    result = await session.execute(query)
    recommendations = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return PaginatedResponse(
        data=[RecommendationResponse.model_validate(r) for r in recommendations],
        total=total,
        page=page,
        page_size=page_size,
        limit=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )


@router.get("/{customer_id}/personalized", response_model=list[RecommendationResponse])
async def get_personalized_recommendations(
    customer_id: str,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
    limit: int = Query(10, ge=1, le=50),
):
    customer_check = await session.execute(
        select(Customer).where(
            Customer.id == customer_id,
            Customer.organization_id == org_id,
        )
    )
    if not customer_check.scalar_one_or_none():
        raise NotFoundException("Customer not found")

    service = RecommendationService(session)
    recommendations = await service.get_personalized(customer_id, org_id, limit)
    return [RecommendationResponse.model_validate(r) for r in recommendations]


@router.post("/feedback", response_model=APIResponse)
async def submit_recommendation_feedback(
    payload: RecommendationFeedback,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    feedback = RecFeedback(organization_id=org_id, **payload.model_dump())
    session.add(feedback)
    await session.commit()
    return APIResponse(message="Feedback recorded successfully")


@router.post("/{customer_id}/refresh", response_model=APIResponse)
async def refresh_customer_recommendations(
    customer_id: str,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    customer_check = await session.execute(
        select(Customer).where(
            Customer.id == customer_id,
            Customer.organization_id == org_id,
        )
    )
    if not customer_check.scalar_one_or_none():
        raise NotFoundException("Customer not found")

    service = RecommendationService(session)
    await service.refresh(customer_id, org_id)
    return APIResponse(message="Recommendations refresh triggered successfully")
