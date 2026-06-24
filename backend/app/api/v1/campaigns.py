from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_session
from app.schemas.campaign import (
    CampaignCreate,
    CampaignUpdate,
    CampaignResponse,
    CampaignListResponse,
    CampaignResultResponse,
    CampaignTargetResponse,
)
from app.schemas.common import APIResponse, PaginatedResponse
from app.models.campaign import Campaign, CampaignTarget, CampaignResult
from app.middleware.auth import get_current_user, get_current_organization
from app.core.exceptions import NotFoundException
from app.services.campaign_service import CampaignService

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("", response_model=PaginatedResponse[CampaignListResponse])
async def list_campaigns(
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    search: str | None = Query(None),
    sort_by: str | None = Query(None),
    sort_order: str = Query("desc"),
):
    query = select(Campaign).where(Campaign.organization_id == org_id)

    if status:
        query = query.where(Campaign.status == status)
    if search:
        query = query.where(Campaign.name.ilike(f"%{search}%"))

    total_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(total_query)).scalar() or 0

    order_column = getattr(Campaign, sort_by, Campaign.created_at) if sort_by else Campaign.created_at
    order_fn = order_column.desc if sort_order == "desc" else order_column.asc
    query = query.order_by(order_fn()).offset((page - 1) * page_size).limit(page_size)

    result = await session.execute(query)
    campaigns = result.scalars().all()

    campaign_ids = [c.id for c in campaigns]
    results_map = {}
    if campaign_ids:
        from app.models.campaign import CampaignResult
        r_stmt = select(CampaignResult).where(
            CampaignResult.campaign_id.in_(campaign_ids),
            CampaignResult.organization_id == org_id,
        )
        r_result = await session.execute(r_stmt)
        for cr in r_result.scalars().all():
            results_map[str(cr.campaign_id)] = cr

    data = []
    for c in campaigns:
        c_dict = CampaignListResponse.model_validate(c).model_dump()
        cr = results_map.get(str(c.id))
        if cr:
            c_dict["metrics"] = {
                "sent": cr.total_targeted or 0,
                "delivered": cr.total_delivered or 0,
                "opened": cr.total_opened or 0,
                "clicked": cr.total_clicked or 0,
                "converted": cr.total_converted or 0,
                "revenue": float(cr.total_revenue or 0),
                "roi": float(cr.roi or 0),
            }
        data.append(c_dict)

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return PaginatedResponse(
        data=data,
        total=total,
        page=page,
        page_size=page_size,
        limit=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )


@router.post("", response_model=APIResponse[CampaignResponse])
async def create_campaign(
    payload: CampaignCreate,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    campaign = Campaign(organization_id=org_id, **payload.model_dump())
    session.add(campaign)

    await session.refresh(campaign)
    return APIResponse(data=CampaignResponse.model_validate(campaign))


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: str,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    result = await session.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.organization_id == org_id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise NotFoundException("Campaign not found")
    return CampaignResponse.model_validate(campaign)


@router.put("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: str,
    payload: CampaignUpdate,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    result = await session.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.organization_id == org_id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise NotFoundException("Campaign not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(campaign, field, value)

    await session.refresh(campaign)
    return CampaignResponse.model_validate(campaign)


@router.delete("/{campaign_id}", response_model=APIResponse)
async def delete_campaign(
    campaign_id: str,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    result = await session.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.organization_id == org_id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise NotFoundException("Campaign not found")

    campaign.status = "cancelled"

    return APIResponse(message="Campaign deleted successfully")


@router.post("/{campaign_id}/launch", response_model=APIResponse)
async def launch_campaign(
    campaign_id: str,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    result = await session.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.organization_id == org_id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise NotFoundException("Campaign not found")

    service = CampaignService(session)
    await service.launch(campaign, org_id)
    return APIResponse(message="Campaign launched successfully")


@router.post("/{campaign_id}/pause", response_model=APIResponse)
async def pause_campaign(
    campaign_id: str,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    result = await session.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.organization_id == org_id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise NotFoundException("Campaign not found")

    campaign.status = "paused"

    return APIResponse(message="Campaign paused successfully")


@router.post("/{campaign_id}/cancel", response_model=APIResponse)
async def cancel_campaign(
    campaign_id: str,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    result = await session.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.organization_id == org_id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise NotFoundException("Campaign not found")

    campaign.status = "cancelled"

    return APIResponse(message="Campaign cancelled successfully")


@router.get("/{campaign_id}/results", response_model=CampaignResultResponse)
async def get_campaign_results(
    campaign_id: str,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    result = await session.execute(
        select(CampaignResult).where(
            CampaignResult.campaign_id == campaign_id,
            CampaignResult.organization_id == org_id,
        )
    )
    campaign_result = result.scalar_one_or_none()
    if not campaign_result:
        raise NotFoundException("Campaign results not available")

    return CampaignResultResponse.model_validate(campaign_result)


@router.get("/{campaign_id}/targets", response_model=PaginatedResponse[CampaignTargetResponse])
async def get_campaign_targets(
    campaign_id: str,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    query = select(CampaignTarget).where(
        CampaignTarget.campaign_id == campaign_id,
        CampaignTarget.organization_id == org_id,
    )

    total_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(total_query)).scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    targets = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return PaginatedResponse(
        data=[CampaignTargetResponse.model_validate(t) for t in targets],
        total=total,
        page=page,
        page_size=page_size,
        limit=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )


@router.post("/{campaign_id}/simulate", response_model=APIResponse)
async def simulate_campaign(
    campaign_id: str,
    session: AsyncSession = Depends(get_session),
    org_id: str = Depends(get_current_organization),
):
    result = await session.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.organization_id == org_id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise NotFoundException("Campaign not found")

    service = CampaignService(session)
    await service.simulate(campaign, org_id)
    return APIResponse(message="Campaign simulation triggered successfully")
