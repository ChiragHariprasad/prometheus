import uuid
from datetime import datetime, date
from typing import Any

from sqlalchemy import func, select, cast, Date, extract
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer, CustomerSegmentMapping, CustomerSegment
from app.models.event import Event
from app.models.twin import CustomerTwin
from app.models.campaign import Campaign, CampaignTarget, CampaignResult
from app.repositories.base import AsyncRepository


class AnalyticsRepository(AsyncRepository[Customer]):
    def __init__(self, session: AsyncSession):
        super().__init__(Customer, session)

    async def get_dashboard_stats(self, organization_id: uuid.UUID) -> dict:
        total_customers = await self._count_customers(organization_id)
        events_24h = await self._count_events_since(organization_id, 24)
        campaigns_stmt = select(func.count()).where(
            Campaign.organization_id == organization_id,
            Campaign.status == "active",
        )
        active_campaigns = (await self.session.execute(campaigns_stmt)).scalar() or 0

        twin_stats_stmt = select(
            func.avg(CustomerTwin.engagement_score),
            func.avg(CustomerTwin.lifetime_value),
        ).where(CustomerTwin.organization_id == organization_id)
        twin_row = (await self.session.execute(twin_stats_stmt)).one()
        avg_engagement = float(twin_row[0]) if twin_row[0] else 0.0
        total_revenue = float(twin_row[1]) if twin_row[1] else 0.0

        churn_stmt = select(func.count()).where(
            CustomerTwin.organization_id == organization_id,
            CustomerTwin.engagement_score < 0.2,
        )
        churned = (await self.session.execute(churn_stmt)).scalar() or 0
        churn_rate = round(churned / total_customers * 100, 2) if total_customers > 0 else 0.0

        return {
            "total_customers": total_customers,
            "events_24h": events_24h,
            "active_campaigns": active_campaigns,
            "avg_engagement": round(avg_engagement, 4),
            "total_revenue": round(total_revenue, 2),
            "churn_rate": churn_rate,
        }

    async def get_engagement_trend(self, organization_id: uuid.UUID, days: int = 30) -> list[dict]:
        stmt = (
            select(
                func.date_trunc("day", Event.event_timestamp).label("day"),
                func.count().label("count"),
            )
            .where(
                Event.organization_id == organization_id,
                Event.event_timestamp >= func.now() - func.make_interval(days=days),
            )
            .group_by(func.date_trunc("day", Event.event_timestamp))
            .order_by(func.date_trunc("day", Event.event_timestamp))
        )
        result = await self.session.execute(stmt)
        return [{"date": str(row.day), "count": row.count} for row in result.all()]

    async def get_segment_distribution(self, organization_id: uuid.UUID) -> list[dict]:
        stmt = (
            select(CustomerSegment.name, func.count(CustomerSegmentMapping.customer_id))
            .join(CustomerSegmentMapping, CustomerSegmentMapping.segment_id == CustomerSegment.id)
            .where(
                CustomerSegment.organization_id == organization_id,
                CustomerSegment.is_active == True,
            )
            .group_by(CustomerSegment.name)
        )
        result = await self.session.execute(stmt)
        return [{"name": row[0], "count": row[1]} for row in result.all()]

    async def get_revenue_data(self, organization_id: uuid.UUID, days: int = 30) -> list[dict]:
        stmt = (
            select(
                cast(Event.event_timestamp, Date).label("day"),
                func.sum(Event.value).label("revenue"),
                func.count().label("transactions"),
            )
            .where(
                Event.organization_id == organization_id,
                Event.event_type == "purchase",
                Event.event_timestamp >= func.now() - func.make_interval(days=days),
            )
            .group_by(cast(Event.event_timestamp, Date))
            .order_by(cast(Event.event_timestamp, Date))
        )
        result = await self.session.execute(stmt)
        return [
            {"date": str(row.day), "revenue": float(row.revenue or 0), "transactions": row.transactions}
            for row in result.all()
        ]

    async def _count_customers(self, organization_id: uuid.UUID) -> int:
        stmt = select(func.count()).where(
            Customer.organization_id == organization_id,
            Customer.is_active == True,
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def _count_events_since(self, organization_id: uuid.UUID, hours: int) -> int:
        stmt = select(func.count()).where(
            Event.organization_id == organization_id,
            Event.event_timestamp >= func.now() - func.make_interval(hours=hours),
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0
