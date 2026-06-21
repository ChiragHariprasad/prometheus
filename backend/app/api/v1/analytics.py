from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import date, datetime, timezone
from app.core.database import get_session
from app.schemas.analytics import (
    DashboardResponse,
    AnalyticsQuery,
    AnalyticsResponse,
    SegmentAnalyticsResponse,
    RevenueAnalyticsResponse,
    EngagementTrendResponse,
    ChurnAnalyticsResponse,
    CampaignPerformanceResponse,
)
from app.schemas.common import APIResponse
from app.middleware.auth import get_current_user, get_current_organization
from app.core.exceptions import NotFoundException
from app.services.analytics_service import AnalyticsService
from app.services.export_service import ExportService

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    service = AnalyticsService(session)
    result = await service.get_dashboard(org_id)
    return result


@router.post("/query", response_model=AnalyticsResponse)
async def run_analytics_query(
    payload: AnalyticsQuery,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    service = AnalyticsService(session)
    result = await service.query(payload, org_id)
    return AnalyticsResponse.model_validate(result)


@router.get("/segments/{segment_id}", response_model=SegmentAnalyticsResponse)
async def get_segment_analytics(
    segment_id: str,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    service = AnalyticsService(session)
    analytics = await service.get_segment_analytics(segment_id, org_id)
    if not analytics:
        raise NotFoundException("Segment analytics not available")
    return SegmentAnalyticsResponse.model_validate(analytics)


@router.get("/revenue", response_model=RevenueAnalyticsResponse)
async def get_revenue_analytics(
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
    granularity: str = Query("monthly"),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
):
    service = AnalyticsService(session)
    date_from = datetime.combine(start_date, datetime.min.time()) if start_date else datetime(2020, 1, 1)
    date_to = datetime.combine(end_date, datetime.max.time()) if end_date else datetime.now(timezone.utc)
    revenue = await service.get_revenue_analytics(org_id, date_from, date_to, granularity)
    return RevenueAnalyticsResponse.model_validate(revenue)


@router.get("/engagement", response_model=EngagementTrendResponse)
async def get_engagement_trends(
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
    granularity: str = Query("day"),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
):
    service = AnalyticsService(session)
    date_from = datetime.combine(start_date, datetime.min.time()) if start_date else datetime(2020, 1, 1)
    date_to = datetime.combine(end_date, datetime.max.time()) if end_date else datetime.now(timezone.utc)
    trends = await service.get_engagement_trend(org_id, date_from, date_to)
    return EngagementTrendResponse(
        overall_score=None,
        trend=trends,
        by_channel={},
        by_segment={},
        period=granularity,
    )


@router.get("/churn", response_model=ChurnAnalyticsResponse)
async def get_churn_analytics(
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
    granularity: str = Query("monthly"),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
):
    service = AnalyticsService(session)
    date_from = datetime.combine(start_date, datetime.min.time()) if start_date else datetime(2020, 1, 1)
    date_to = datetime.combine(end_date, datetime.max.time()) if end_date else datetime.now(timezone.utc)
    churn = await service.get_churn_analytics(org_id, date_from, date_to)
    return ChurnAnalyticsResponse(
        churn_rate=churn.get("churn_rate"),
        churned_customers=churn.get("churned_customers", 0),
        at_risk_customers=churn.get("at_risk_customers", 0),
        churn_by_segment=churn.get("churn_by_segment", []),
        churn_reasons=churn.get("churn_reasons", []),
        retention_rate=churn.get("retention_rate"),
        period=granularity,
    )


@router.get("/campaigns", response_model=list[CampaignPerformanceResponse])
async def compare_campaign_performance(
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
    campaign_ids: str | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
):
    service = AnalyticsService(session)
    ids = campaign_ids.split(",") if campaign_ids else None
    performance = await service.compare_campaigns(org_id, ids, start_date, end_date)
    return [CampaignPerformanceResponse.model_validate(p) for p in performance]


@router.get("/export")
async def export_analytics(
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
    report_type: str = Query(...),
    format: str = Query("csv"),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
):
    service = ExportService(session)
    csv_data = await service.export_analytics(org_id, report_type, start_date, end_date)

    from fastapi.responses import StreamingResponse
    import io

    stream = io.StringIO(csv_data)
    return StreamingResponse(
        iter([stream.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={report_type}_analytics.csv"},
    )
