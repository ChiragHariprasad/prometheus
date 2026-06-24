import uuid
from typing import Any
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
from app.services.prediction_service import PredictionService

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/summary", response_model=TwinSummary)
async def get_twin_summary(
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    service = TwinService(session)
    summary = await service.get_org_summary(org_id)
    if not summary:
        raise NotFoundException("Twin summary not available")
    return TwinSummary.model_validate(summary)


def _build_twin_response(twin: CustomerTwin) -> dict[str, Any]:
    ig = twin.interest_graph or {}
    ca = twin.channel_affinity or {}
    ri = twin.risk_indicators or {}
    st = twin.sentiment_trend or []

    interests = []
    for node in (ig.get("nodes") or ig.get("interests") or ig.get("categories") or []):
        if isinstance(node, dict):
            interests.append({
                "name": node.get("name") or node.get("topic", ""),
                "weight": node.get("weight", 0.0) or node.get("score", 0.0),
            })

    if not interests:
        interests = [{"name": k, "weight": v} for k, v in (ig.items() if isinstance(ig, dict) else {}.items())
                     if k not in ("nodes", "dominant_category", "interest_diversity", "total_interactions")]

    channel_affinity = {}
    if isinstance(ca, dict):
        for k, v in ca.items():
            val = v.get("affinity", 0.0) if isinstance(v, dict) else v
            channel_affinity[k] = float(val) if val is not None else 0.0

    sentiment_trend = []
    for i, s in enumerate(st):
        if isinstance(s, dict):
            sentiment_trend.append({
                "date": s.get("date", ""),
                "score": float(s.get("score", 0) or 0),
            })
        elif isinstance(s, (int, float)):
            sentiment_trend.append({
                "date": f"day-{i}",
                "score": float(s),
            })

    def scale_score(val):
        if val is None:
            return 0.0
        # If val is between 0 and 100, and is greater than 1.0, scale it to 0.0-1.0
        return float(val / 100.0 if val > 1.0 else val)

    return {
        "id": str(twin.customer_id),
        "customer_id": str(twin.customer_id),
        "status": "built" if twin.status == "active" else (twin.status or "built"),
        "engagement_score": scale_score(twin.engagement_score),
        "loyalty_score": scale_score(twin.loyalty_score),
        "confidence_score": scale_score(twin.confidence_score),
        "staleness_score": scale_score(twin.staleness_score),
        "sentiment_score": scale_score((ri.get("current_sentiment") if isinstance(ri, dict) else 0) or 0),
        "churn_probability": scale_score((ri.get("churn_probability") if isinstance(ri, dict) else 0) or 0),
        "interests": interests,
        "interest_graph": twin.interest_graph or {},
        "channel_affinity": channel_affinity,
        "sentiment_trend": sentiment_trend,
        "last_rebuilt": twin.built_at.isoformat() if twin.built_at else None,
        "created_at": twin.updated_at.isoformat() if twin.updated_at else None,
    }


@router.get("/{customer_id}")
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
        service = TwinService(session)
        await service.get_or_build_twin(
            organization_id=uuid.UUID(org_id),
            customer_id=uuid.UUID(customer_id),
        )
        result = await session.execute(
            select(CustomerTwin).where(
                CustomerTwin.customer_id == customer_id,
                CustomerTwin.organization_id == org_id,
            )
        )
        twin = result.scalar_one()

    return _build_twin_response(twin)


@router.post("/{customer_id}/rebuild", response_model=APIResponse)
async def rebuild_twin(
    customer_id: str,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    await _verify_customer_org(customer_id, org_id, session)

    service = TwinService(session)
    await service.rebuild_twin(organization_id=org_id, customer_id=customer_id)
    return APIResponse(message="Twin rebuild triggered successfully")


@router.get("/{customer_id}/history", response_model=list[TwinSnapshotResponse])
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

    if not predictions:
        pred_service = PredictionService(session)
        try:
            await pred_service.get_churn_prediction(
                organization_id=uuid.UUID(org_id),
                customer_id=uuid.UUID(customer_id),
            )
        except Exception:
            pass
        try:
            await pred_service.get_ltv_prediction(
                organization_id=uuid.UUID(org_id),
                customer_id=uuid.UUID(customer_id),
            )
        except Exception:
            pass
        try:
            await pred_service.get_intent_prediction(
                organization_id=uuid.UUID(org_id),
                customer_id=uuid.UUID(customer_id),
            )
        except Exception:
            pass
        requery = select(Prediction).where(
            Prediction.customer_id == customer_id,
            Prediction.organization_id == org_id,
        )
        if prediction_type:
            requery = requery.where(Prediction.prediction_type == prediction_type)
        requery = requery.order_by(Prediction.created_at.desc()).limit(limit)
        result = await session.execute(requery)
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
    try:
        uuid.UUID(customer_id)
    except ValueError:
        raise NotFoundException("Customer")
    result = await session.execute(
        select(Customer).where(
            Customer.id == customer_id,
            Customer.organization_id == org_id,
        )
    )
    if not result.scalar_one_or_none():
        raise NotFoundException("Customer not found")
