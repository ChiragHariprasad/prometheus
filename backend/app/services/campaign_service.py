import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ValidationException
from app.core.logging import logger
from app.core.redis import RedisClient
from app.models.campaign import Campaign, CampaignTarget, CampaignResult
from app.models.customer import Customer, CustomerSegmentMapping
from app.models.twin import CustomerTwin
from app.schemas.campaign import (
    CampaignCreate, CampaignUpdate, CampaignResponse,
    CampaignResultResponse,
)
from app.repositories.base import AsyncRepository


class CampaignService:
    def __init__(self, session: AsyncSession, redis: RedisClient | None = None):
        self.session = session
        self.redis = redis
        self.repo = AsyncRepository(Campaign, session)
        self.target_repo = AsyncRepository(CampaignTarget, session)
        self.result_repo = AsyncRepository(CampaignResult, session)

    async def get_campaign(self, campaign_id: uuid.UUID, organization_id: uuid.UUID) -> Campaign:
        campaign = await self.repo.get(campaign_id, organization_id)
        if not campaign:
            raise NotFoundException("Campaign", str(campaign_id))
        return campaign

    async def get_campaigns(
        self,
        organization_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
        filters: dict | None = None,
    ) -> tuple[list[Campaign], int]:
        scoped = dict(filters or {})
        return await self.repo.get_multi(
            skip=skip, limit=limit, filters=scoped,
            organization_id=organization_id,
        )

    async def create_campaign(self, organization_id: uuid.UUID, data: CampaignCreate | dict, created_by: uuid.UUID | None = None) -> Campaign:
        if isinstance(data, dict):
            payload = data
        else:
            payload = data.model_dump(exclude_unset=True)

        payload["organization_id"] = organization_id
        payload["status"] = "draft"
        if created_by:
            payload["created_by"] = created_by

        campaign = Campaign(**payload)
        self.session.add(campaign)
        await self.session.flush()
        await self.session.refresh(campaign)

        logger.info("Campaign created", extra={
            "campaign_id": str(campaign.id), "org_id": str(organization_id),
        })
        return campaign

    async def update_campaign(self, campaign_id: uuid.UUID, organization_id: uuid.UUID, data: CampaignUpdate | dict) -> Campaign:
        campaign = await self.repo.update(campaign_id, data, organization_id)
        if not campaign:
            raise NotFoundException("Campaign", str(campaign_id))
        return campaign

    async def delete_campaign(self, campaign_id: uuid.UUID, organization_id: uuid.UUID) -> bool:
        campaign = await self.repo.get(campaign_id, organization_id)
        if not campaign:
            raise NotFoundException("Campaign", str(campaign_id))
        result = await self.repo.delete(campaign_id, soft=False, organization_id=organization_id)
        return result

    async def launch_campaign(self, campaign_id: uuid.UUID) -> None:
        campaign = await self._get_campaign_or_404(campaign_id)
        if campaign.status != "draft":
            raise ValidationException(f"Cannot launch campaign with status '{campaign.status}'")

        campaign.status = "launching"
        await self.session.flush()

        try:
            targets = await self._build_targets(campaign)
            distributed = await self._distribute_to_targets(campaign, targets)

            campaign.status = "active"
            campaign.executed_at = datetime.now(timezone.utc)

            result = CampaignResult(
                campaign_id=campaign.id,
                organization_id=campaign.organization_id,
                total_targeted=len(targets),
                total_delivered=distributed,
            )
            self.session.add(result)
            await self.session.flush()

            logger.info("Campaign launched", extra={
                "campaign_id": str(campaign_id), "targets": len(targets),
            })

        except Exception as e:
            campaign.status = "failed"
            await self.session.flush()
            logger.error("Campaign launch failed", extra={"campaign_id": str(campaign_id), "error": str(e)})
            raise

    async def pause_campaign(self, campaign_id: uuid.UUID) -> None:
        campaign = await self._get_campaign_or_404(campaign_id)
        if campaign.status != "active":
            raise ValidationException(f"Cannot pause campaign with status '{campaign.status}'")
        campaign.status = "paused"
        await self.session.flush()

    async def cancel_campaign(self, campaign_id: uuid.UUID) -> None:
        campaign = await self._get_campaign_or_404(campaign_id)
        if campaign.status in ("completed", "cancelled"):
            raise ValidationException(f"Cannot cancel campaign with status '{campaign.status}'")
        campaign.status = "cancelled"
        await self.session.flush()

    async def get_campaign_results(self, campaign_id: uuid.UUID) -> CampaignResultResponse:
        campaign = await self._get_campaign_or_404(campaign_id)
        result_stmt = select(CampaignResult).where(
            CampaignResult.campaign_id == campaign_id,
            CampaignResult.organization_id == campaign.organization_id,
        )
        result = await self.session.execute(result_stmt)
        result_obj = result.scalar_one_or_none()

        if not result_obj:
            result_obj = await self._compute_results(campaign)

        return CampaignResultResponse(
            id=result_obj.id,
            campaign_id=result_obj.campaign_id,
            total_targeted=result_obj.total_targeted,
            total_delivered=result_obj.total_delivered,
            total_opened=result_obj.total_opened,
            total_clicked=result_obj.total_clicked,
            total_converted=result_obj.total_converted,
            total_revenue=float(result_obj.total_revenue or 0),
            total_cost=float(result_obj.total_cost or 0),
            open_rate=result_obj.open_rate,
            click_rate=result_obj.click_rate,
            conversion_rate=result_obj.conversion_rate,
            bounce_rate=result_obj.bounce_rate,
            unsubscribe_rate=result_obj.unsubscribe_rate,
            roi=result_obj.roi,
            engagement_distribution=result_obj.engagement_distribution or {},
            channel_performance=result_obj.channel_performance or {},
            segment_performance=result_obj.segment_performance or {},
            hourly_breakdown=list(result_obj.hourly_breakdown.values()) if isinstance(result_obj.hourly_breakdown, dict) else [],
            daily_breakdown=list(result_obj.daily_breakdown.values()) if isinstance(result_obj.daily_breakdown, dict) else [],
            ab_test_results=result_obj.ab_test_results or {},
            control_group_results=result_obj.control_group_results or {},
            treatment_group_results=result_obj.treatment_group_results or {},
            computed_at=result_obj.computed_at,
        )

    async def compute_campaign_roi(self, campaign_id: uuid.UUID) -> float:
        campaign = await self._get_campaign_or_404(campaign_id)
        result_stmt = select(CampaignResult).where(
            CampaignResult.campaign_id == campaign_id,
            CampaignResult.organization_id == campaign.organization_id,
        )
        result = await self.session.execute(result_stmt)
        result_obj = result.scalar_one_or_none()

        if not result_obj:
            return 0.0

        total_revenue = float(result_obj.total_revenue or 0)
        total_cost = float(result_obj.total_cost or 0)

        if total_cost <= 0:
            return 0.0
        return round((total_revenue - total_cost) / total_cost, 4)

    async def _get_campaign_or_404(self, campaign_id: uuid.UUID) -> Campaign:
        campaign = await self.session.get(Campaign, campaign_id)
        if not campaign:
            raise NotFoundException("Campaign", str(campaign_id))
        return campaign

    async def _build_targets(self, campaign: Campaign) -> list[Customer]:
        stmt = select(Customer).where(
            Customer.organization_id == campaign.organization_id,
            Customer.is_active.is_(True),
        )

        if campaign.segments:
            segment_ids = []
            for seg in campaign.segments:
                try:
                    segment_ids.append(uuid.UUID(seg))
                except (ValueError, TypeError):
                    continue
            if segment_ids:
                stmt = (
                    stmt.join(CustomerSegmentMapping, CustomerSegmentMapping.customer_id == Customer.id)
                    .where(
                        CustomerSegmentMapping.segment_id.in_(segment_ids),
                        CustomerSegmentMapping.organization_id == campaign.organization_id,
                    )
                )

        if campaign.target_customers:
            target_ids = []
            for tid in campaign.target_customers:
                try:
                    target_ids.append(uuid.UUID(tid))
                except (ValueError, TypeError):
                    continue
            if target_ids:
                stmt = stmt.where(Customer.id.in_(target_ids))

        if campaign.exclude_customers:
            exclude_ids = []
            for eid in campaign.exclude_customers:
                try:
                    exclude_ids.append(uuid.UUID(eid))
                except (ValueError, TypeError):
                    continue
            if exclude_ids:
                stmt = stmt.where(Customer.id.notin_(exclude_ids))

        result = await self.session.execute(stmt)
        customers = list(result.scalars().all())

        campaign_targets = []
        for customer in customers:
            target = CampaignTarget(
                campaign_id=campaign.id,
                customer_id=customer.id,
                organization_id=campaign.organization_id,
                status="pending",
            )
            self.session.add(target)
            campaign_targets.append(target)

        await self.session.flush()
        return customers

    async def _distribute_to_targets(self, campaign: Campaign, customers: list[Customer]) -> int:
        channel = campaign.channel
        distributed = 0
        customer_ids = [c.id for c in customers]

        twin_stmt = select(CustomerTwin).where(
            CustomerTwin.customer_id.in_(customer_ids),
            CustomerTwin.organization_id == campaign.organization_id,
        )
        twin_result = await self.session.execute(twin_stmt)
        twin_map = {t.customer_id: t for t in twin_result.scalars().all()}

        target_stmt = select(CampaignTarget).where(
            CampaignTarget.campaign_id == campaign.id,
            CampaignTarget.customer_id.in_(customer_ids),
            CampaignTarget.organization_id == campaign.organization_id,
        )
        target_result = await self.session.execute(target_stmt)
        targets = list(target_result.scalars().all())

        for target in targets:
            target.status = "delivered"
            target.delivered_at = datetime.now(timezone.utc)
            twin = twin_map.get(target.customer_id)
            if twin:
                target.engagement_score = twin.engagement_score
            distributed += 1

        await self.session.flush()
        return distributed

    async def _compute_results(self, campaign: Campaign) -> CampaignResult:
        stmt = select(CampaignTarget).where(
            CampaignTarget.campaign_id == campaign.id,
            CampaignTarget.organization_id == campaign.organization_id,
        )
        result = await self.session.execute(stmt)
        targets = list(result.scalars().all())

        total = len(targets)
        delivered = sum(1 for t in targets if t.status in ("delivered", "opened", "clicked", "converted"))
        opened = sum(1 for t in targets if t.status in ("opened", "clicked", "converted"))
        clicked = sum(1 for t in targets if t.status in ("clicked", "converted"))
        converted = sum(1 for t in targets if t.status == "converted")
        revenue = sum(float(t.revenue or 0) for t in targets)

        cost = float(campaign.budget or 0)
        roi = (revenue - cost) / cost if cost > 0 else 0

        result_obj = CampaignResult(
            campaign_id=campaign.id,
            organization_id=campaign.organization_id,
            total_targeted=total,
            total_delivered=delivered,
            total_opened=opened,
            total_clicked=clicked,
            total_converted=converted,
            total_revenue=revenue,
            total_cost=cost,
            open_rate=round(opened / delivered, 4) if delivered > 0 else 0,
            click_rate=round(clicked / opened, 4) if opened > 0 else 0,
            conversion_rate=round(converted / clicked, 4) if clicked > 0 else 0,
            roi=round(roi, 4),
            computed_at=datetime.now(timezone.utc),
        )
        self.session.add(result_obj)
        await self.session.flush()
        await self.session.refresh(result_obj)
        return result_obj
