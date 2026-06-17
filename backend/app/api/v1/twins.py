from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_session
from app.schemas.twin import (
    CustomerTwinResponse,
    TwinSummary,
    TwinSnapshotResponse,
    PredictionResponse,
)
from app.schemas.common import APIResponse
from app.models.twin import CustomerTwin, TwinSnapshot, Prediction
from app.models.customer import Customer
from app.middleware.auth import get_current_user, get_current_organization
from app.core.exceptions import NotFoundException
from app.services.twin_service import TwinService

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/{customer_id}/twin", response_model=CustomerTwinResponse)
async def get_customer_twin(
    customer_id: str,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    await _verify_customer_org(customer_id, org_id, session)

    result = await session.execute(
        select(CustomerTwin).where(
            CustomerTwin.customer_id == customer_id,
            CustomerTwin.organization_id == org_id,
        )
    )
    twin = result.scalar_one_or_none()
    if not twin:
        raise NotFoundException("Twin not found for this customer")

    return CustomerTwinResponse.model_validate(twin)


@router.post("/{customer_id}/twin/rebuild", response_model=APIResponse)
async def rebuild_twin(
    customer_id: str,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    await _verify_customer_org(customer_id, org_id, session)

    service = TwinService(session)
    await service.rebuild_twin(customer_id, org_id)
    return APIResponse(message="Twin rebuild triggered successfully")


@router.get("/{customer_id}/twin/summary", response_model=TwinSummary)
async def get_twin_summary(
    customer_id: str,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    await _verify_customer_org(customer_id, org_id, session)

    service = TwinService(session)
    summary = await service.get_summary(customer_id, org_id)
    if not summary:
        raise NotFoundException("Twin summary not available")
    return TwinSummary.model_validate(summary)


@router.get("/{customer_id}/twin/history", response_model=list[TwinSnapshotResponse])
async def get_twin_history(
    customer_id: str,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
    limit: int = Query(50, ge=1, le=500),
):
    await _verify_customer_org(customer_id, org_id, session)

    result = await session.execute(
        select(TwinSnapshot)
        .where(
            TwinSnapshot.customer_id == customer_id,
            TwinSnapshot.organization_id == org_id,
        )
        .order_by(TwinSnapshot.created_at.desc())
        .limit(limit)
    )
    snapshots = result.scalars().all()
    return [TwinSnapshotResponse.model_validate(s) for s in snapshots]


@router.get("/{customer_id}/predictions", response_model=list[PredictionResponse])
async def get_predictions(
    customer_id: str,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
    prediction_type: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
):
    await _verify_customer_org(customer_id, org_id, session)

    query = select(Prediction).where(
        Prediction.customer_id == customer_id,
        Prediction.organization_id == org_id,
    )
    if prediction_type:
        query = query.where(Prediction.prediction_type == prediction_type)

    query = query.order_by(Prediction.created_at.desc()).limit(limit)
    result = await session.execute(query)
    predictions = result.scalars().all()

    return [PredictionResponse.model_validate(p) for p in predictions]


@router.get("/{customer_id}/predictions/{prediction_type}", response_model=PredictionResponse)
async def get_latest_prediction(
    customer_id: str,
    prediction_type: str,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    await _verify_customer_org(customer_id, org_id, session)

    result = await session.execute(
        select(Prediction)
        .where(
            Prediction.customer_id == customer_id,
            Prediction.organization_id == org_id,
            Prediction.prediction_type == prediction_type,
        )
        .order_by(Prediction.created_at.desc())
        .limit(1)
    )
    prediction = result.scalar_one_or_none()
    if not prediction:
        raise NotFoundException(f"No prediction found for type '{prediction_type}'")

    return PredictionResponse.model_validate(prediction)


async def _verify_customer_org(
    customer_id: str,
    org_id: str,
    session: AsyncSession,
):
    result = await session.execute(
        select(Customer).where(
            Customer.id == customer_id,
            Customer.organization_id == org_id,
        )
    )
    if not result.scalar_one_or_none():
        raise NotFoundException("Customer not found")
