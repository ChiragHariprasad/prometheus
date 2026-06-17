from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import date
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
    period: str = Query("monthly"),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
):
    service = AnalyticsService(session)
    revenue = await service.get_revenue(org_id, period, start_date, end_date)
    return RevenueAnalyticsResponse.model_validate(revenue)


@router.get("/engagement", response_model=EngagementTrendResponse)
async def get_engagement_trends(
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
    period: str = Query("weekly"),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
):
    service = AnalyticsService(session)
    trends = await service.get_engagement(org_id, period, start_date, end_date)
    return EngagementTrendResponse.model_validate(trends)


@router.get("/churn", response_model=ChurnAnalyticsResponse)
async def get_churn_analytics(
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
    period: str = Query("monthly"),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
):
    service = AnalyticsService(session)
    churn = await service.get_churn(org_id, period, start_date, end_date)
    return ChurnAnalyticsResponse.model_validate(churn)


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
