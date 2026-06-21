import uuid
import csv
import io
from datetime import datetime, timezone, timedelta, date
from typing import Any

from sqlalchemy import select, func, and_, or_, text, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import NotFoundException
from app.core.logging import logger
from app.core.redis import RedisClient
from app.models.customer import (
    Customer, CustomerSegment,
    CustomerSegmentMapping,
)
from app.models.event import Event as CustomerEvent
from app.models.twin import CustomerTwin, Prediction as CustomerPrediction
from app.models.campaign import Campaign, CampaignResult
from app.schemas.analytics import (
    AnalyticsQuery, AnalyticsResponse,
    DashboardResponse, DashboardStats, SegmentAnalyticsResponse,
)


class AnalyticsService:
    def __init__(self, session: AsyncSession, redis: RedisClient | None = None):
        self.session = session
        self.redis = redis

    async def get_dashboard(self, organization_id: uuid.UUID) -> DashboardResponse:
        cache_key = f"dashboard:{organization_id}"
        if self.redis:
            cached = await self.redis.get(cache_key)
            if cached:
                return DashboardResponse(**cached)

        now = datetime.now(timezone.utc)
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        thirty_days_ago = now - timedelta(days=30)

        customer_count = await self._count_customers(organization_id)
        event_count_24h = await self._count_events_since(organization_id, now - timedelta(hours=24))
        active_campaigns = await self._count_active_campaigns(organization_id)

        avg_engagement = await self._avg_twin_field(organization_id, CustomerTwin.engagement_score)
        avg_loyalty = await self._avg_twin_field(organization_id, CustomerTwin.loyalty_score)

        revenue_30d = await self._sum_event_value_since(organization_id, "purchase", thirty_days_ago)
        churn_rate_30d = await self._compute_churn_rate(organization_id, thirty_days_ago)

        conversions_stmt = (
            select(func.count(func.distinct(CustomerEvent.customer_id)))
            .where(
                CustomerEvent.organization_id == organization_id,
                CustomerEvent.event_type == "purchase",
                CustomerEvent.event_timestamp >= thirty_days_ago,
            )
        )
        conversions_result = await self.session.execute(conversions_stmt)
        conversions_30d = conversions_result.scalar() or 0

        total_customers = customer_count if customer_count > 0 else 1
        conversion_rate_30d = round(conversions_30d / total_customers, 4)

        top_segments = await self._get_top_segments(organization_id, limit=5)
        engagement_trend = await self._get_daily_trend(organization_id, "engagement", thirty_days_ago)
        revenue_trend = await self._get_daily_trend(organization_id, "revenue", thirty_days_ago)
        segment_distribution = await self._get_segment_distribution(organization_id)

        stats = DashboardStats(
            total_customers=customer_count,
            events_24h=event_count_24h,
            active_campaigns=active_campaigns,
            avg_engagement=avg_engagement or 0.0,
            total_revenue=round(revenue_30d, 2),
            revenue_growth=0.0,
            churn_rate=churn_rate_30d or 0.0,
        )
        result = DashboardResponse(
            stats=stats,
            engagement_trend=engagement_trend,
            revenue_data=revenue_trend,
            segment_distribution=segment_distribution,
            top_segments=top_segments,
            recent_activity=[],
            churn_alerts=[],
        )

        if self.redis:
            await self.redis.set(cache_key, result.model_dump(), ttl=settings.CACHE_TTL_DEFAULT)

        return result

    async def query_analytics(self, organization_id: uuid.UUID, query: AnalyticsQuery) -> AnalyticsResponse:
        granularity_map = {
            "hour": "hour",
            "day": "day",
            "week": "week",
            "month": "month",
        }
        trunc = granularity_map.get(query.granularity, "day")

        date_field = func.date_trunc(trunc, CustomerEvent.event_timestamp)

        if query.metric == "events":
            value_col = func.count().label("value")
        elif query.metric == "revenue":
            value_col = func.coalesce(func.sum(CustomerEvent.value), 0).label("value")
        elif query.metric == "unique_customers":
            value_col = func.count(func.distinct(CustomerEvent.customer_id)).label("value")
        else:
            value_col = func.count().label("value")

        stmt = (
            select(
                date_field.label("period"),
                value_col,
            )
            .where(
                CustomerEvent.organization_id == organization_id,
                CustomerEvent.event_timestamp >= query.date_from,
                CustomerEvent.event_timestamp <= query.date_to,
            )
        )

        if query.segment_id:
            stmt = stmt.join(
                CustomerSegmentMapping,
                CustomerSegmentMapping.customer_id == CustomerEvent.customer_id,
            ).where(CustomerSegmentMapping.segment_id == query.segment_id)

        if query.filters:
            for key, value in query.filters.items():
                if hasattr(CustomerEvent, key):
                    if isinstance(value, list):
                        stmt = stmt.where(getattr(CustomerEvent, key).in_(value))
                    else:
                        stmt = stmt.where(getattr(CustomerEvent, key) == value)

        if query.dimension and hasattr(CustomerEvent, query.dimension):
            stmt = stmt.group_by("period", getattr(CustomerEvent, query.dimension))
            stmt = stmt.order_by("period", getattr(CustomerEvent, query.dimension))
        else:
            stmt = stmt.group_by("period").order_by("period")

        result = await self.session.execute(stmt)
        rows = result.all()

        data = []
        for row in rows:
            if row.period is None:
                continue
            entry = {
                "period": row.period.isoformat(),
                "value": float(row.value) if row.value is not None else 0,
            }
            if query.dimension and hasattr(CustomerEvent, query.dimension):
                entry[query.dimension] = getattr(row, query.dimension)
            data.append(entry)

        total = sum(d["value"] for d in data)

        return AnalyticsResponse(
            metric=query.metric,
            dimension=query.dimension,
            granularity=query.granularity,
            data=data,
            summary={
                "total": total,
                "avg": round(total / len(data), 2) if data else 0,
                "min": min(d["value"] for d in data) if data else 0,
                "max": max(d["value"] for d in data) if data else 0,
            },
            total=len(data),
        )

    async def get_segment_analytics(self, organization_id: uuid.UUID, segment_id: uuid.UUID) -> SegmentAnalyticsResponse:
        segment = await self.session.get(CustomerSegment, segment_id)
        if not segment or segment.organization_id != organization_id:
            raise NotFoundException("Segment", str(segment_id))

        mapping_stmt = select(func.count()).select_from(CustomerSegmentMapping).where(
            CustomerSegmentMapping.segment_id == segment_id,
            CustomerSegmentMapping.organization_id == organization_id,
        )
        mapping_result = await self.session.execute(mapping_stmt)
        customer_count = mapping_result.scalar() or 0

        avg_engagement = await self._segment_avg_twin_field(
            segment_id, organization_id, CustomerTwin.engagement_score
        )
        avg_loyalty = await self._segment_avg_twin_field(
            segment_id, organization_id, CustomerTwin.loyalty_score
        )
        total_ltv = await self._segment_sum_twin_field(
            segment_id, organization_id, CustomerTwin.lifetime_value
        )

        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        churn_stmt = (
            select(func.count(func.distinct(CustomerTwin.customer_id)))
            .join(CustomerSegmentMapping, CustomerSegmentMapping.customer_id == CustomerTwin.customer_id)
            .where(
                CustomerSegmentMapping.segment_id == segment_id,
                CustomerSegmentMapping.organization_id == organization_id,
                CustomerTwin.organization_id == organization_id,
                or_(
                    CustomerTwin.staleness_score > 0.7,
                    (CustomerTwin.engagement_score < 0.2),
                ),
            )
        )
        churn_result = await self.session.execute(churn_stmt)
        at_risk = churn_result.scalar() or 0
        churn_rate = round(at_risk / customer_count, 4) if customer_count > 0 else 0

        now = datetime.now(timezone.utc)
        previous_period = now - timedelta(days=60)
        current_count = customer_count

        previous_stmt = select(func.count(func.distinct(CustomerSegmentMapping.customer_id))).where(
            CustomerSegmentMapping.segment_id == segment_id,
            CustomerSegmentMapping.organization_id == organization_id,
            CustomerSegmentMapping.assigned_at < previous_period,
        )
        previous_result = await self.session.execute(previous_stmt)
        previous_customers = previous_result.scalar() or 0
        growth_rate = round((current_count - previous_customers) / max(previous_customers, 1), 4)

        top_interests = await self._segment_top_interests(segment_id, organization_id)

        return SegmentAnalyticsResponse(
            segment_id=segment_id,
            segment_name=segment.name,
            customer_count=customer_count,
            avg_engagement=avg_engagement,
            avg_loyalty=avg_loyalty,
            total_ltv=round(float(total_ltv or 0), 2),
            churn_rate=churn_rate,
            growth_rate=growth_rate,
            top_interests=top_interests,
        )

    async def get_revenue_analytics(
        self,
        organization_id: uuid.UUID,
        date_from: datetime,
        date_to: datetime,
        granularity: str,
    ) -> dict:
        trunc_map = {"hour": "hour", "day": "day", "week": "week", "month": "month"}
        trunc = trunc_map.get(granularity, "day")

        stmt = (
            select(
                func.date_trunc(trunc, CustomerEvent.event_timestamp).label("period"),
                func.coalesce(func.sum(CustomerEvent.value), 0).label("revenue"),
                func.count().label("transactions"),
                func.count(func.distinct(CustomerEvent.customer_id)).label("unique_customers"),
                func.avg(CustomerEvent.value).label("avg_order_value"),
            )
            .where(
                CustomerEvent.organization_id == organization_id,
                CustomerEvent.event_type == "purchase",
                CustomerEvent.event_timestamp >= date_from,
                CustomerEvent.event_timestamp <= date_to,
            )
            .group_by(text("period"))
            .order_by(text("period"))
        )
        result = await self.session.execute(stmt)
        rows = result.all()

        total_revenue = sum(r.revenue for r in rows)
        total_transactions = sum(r.transactions for r in rows)

        return {
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "granularity": granularity,
            "total_revenue": round(float(total_revenue), 2),
            "total_transactions": int(total_transactions),
            "revenue_trend": [
                {
                    "period": r.period.isoformat(),
                    "revenue": round(float(r.revenue), 2),
                    "transactions": int(r.transactions),
                    "unique_customers": int(r.unique_customers),
                    "avg_order_value": round(float(r.avg_order_value or 0), 2),
                }
                for r in rows if r.period is not None
            ],
        }

    async def get_engagement_trend(self, organization_id: uuid.UUID, date_from: datetime, date_to: datetime) -> list[dict]:
        stmt = (
            select(
                func.date_trunc("day", CustomerEvent.event_timestamp).label("date"),
                func.count().label("events"),
                func.count(func.distinct(CustomerEvent.customer_id)).label("active_users"),
            )
            .where(
                CustomerEvent.organization_id == organization_id,
                CustomerEvent.event_timestamp >= date_from,
                CustomerEvent.event_timestamp <= date_to,
            )
            .group_by(text("date"))
            .order_by(text("date"))
        )
        result = await self.session.execute(stmt)
        rows = result.all()

        return [
            {
                "date": r.date.isoformat(),
                "events": int(r.events),
                "active_users": int(r.active_users),
                "events_per_user": round(r.events / r.active_users, 2) if r.active_users > 0 else 0,
            }
            for r in rows if r.date is not None
        ]

    async def get_churn_analytics(self, organization_id: uuid.UUID, date_from: datetime, date_to: datetime) -> dict:
        total_customers = await self._count_customers(organization_id)

        churned_stmt = (
            select(func.count())
            .select_from(CustomerTwin)
            .where(
                CustomerTwin.organization_id == organization_id,
                or_(
                    CustomerTwin.staleness_score > 0.8,
                    and_(
                        CustomerTwin.engagement_score < 0.2,
                        CustomerTwin.last_event_at < date_from,
                    ),
                ),
            )
        )
        churned_result = await self.session.execute(churned_stmt)
        churned_count = churned_result.scalar() or 0

        at_risk_stmt = (
            select(func.count())
            .select_from(CustomerTwin)
            .where(
                CustomerTwin.organization_id == organization_id,
                CustomerTwin.engagement_score < 0.3,
                CustomerTwin.staleness_score > 0.5,
                CustomerTwin.staleness_score <= 0.8,
            )
        )
        at_risk_result = await self.session.execute(at_risk_stmt)
        at_risk_count = at_risk_result.scalar() or 0

        healthy_stmt = (
            select(func.count())
            .select_from(CustomerTwin)
            .where(
                CustomerTwin.organization_id == organization_id,
                CustomerTwin.engagement_score >= 0.3,
            )
        )
        healthy_result = await self.session.execute(healthy_stmt)
        healthy_count = healthy_result.scalar() or 0

        churn_by_segment = []
        segments_stmt = select(CustomerSegment).where(
            CustomerSegment.organization_id == organization_id,
        )
        segments_result = await self.session.execute(segments_stmt)
        segments = list(segments_result.scalars().all())

        for segment in segments:
            seg_churn = await self._segment_at_risk_count(segment.id, organization_id)
            seg_total = await self._segment_customer_count(segment.id, organization_id)
            churn_by_segment.append({
                "segment_id": str(segment.id),
                "segment_name": segment.name,
                "total_customers": seg_total,
                "at_risk": seg_churn,
                "churn_rate": round(seg_churn / seg_total, 4) if seg_total > 0 else 0,
            })

        return {
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "total_customers": total_customers,
            "churned_customers": churned_count,
            "churn_rate": round(churned_count / total_customers, 4) if total_customers > 0 else 0,
            "at_risk_customers": at_risk_count,
            "healthy_customers": healthy_count,
            "churn_by_segment": churn_by_segment,
        }

    async def export_data(self, organization_id: uuid.UUID, query_params: dict) -> bytes:
        output = io.StringIO()
        writer = csv.writer(output)

        export_type = query_params.get("type", "customers")

        if export_type == "customers":
            writer.writerow([
                "id", "email", "first_name", "last_name", "phone",
                "external_id", "is_active", "tags", "source",
                "first_seen_at", "last_seen_at", "created_at",
            ])
            stmt = select(Customer).where(
                Customer.organization_id == organization_id,
            )
            if "date_from" in query_params and "date_to" in query_params:
                date_from = datetime.fromisoformat(query_params["date_from"])
                date_to = datetime.fromisoformat(query_params["date_to"])
                stmt = stmt.where(
                    Customer.created_at >= date_from,
                    Customer.created_at <= date_to,
                )
            result = await self.session.execute(stmt)
            customers = list(result.scalars().all())
            for c in customers:
                writer.writerow([
                    str(c.id), c.email, c.first_name, c.last_name, c.phone,
                    c.external_id, c.is_active, ",".join(c.tags or []), c.source,
                    c.first_seen_at.isoformat() if c.first_seen_at else "",
                    c.last_seen_at.isoformat() if c.last_seen_at else "",
                    c.created_at.isoformat() if c.created_at else "",
                ])

        elif export_type == "events":
            writer.writerow([
                "id", "customer_id", "event_type", "event_name",
                "channel", "source", "value", "event_timestamp",
            ])
            stmt = select(CustomerEvent).where(
                CustomerEvent.organization_id == organization_id,
            )
            if "date_from" in query_params and "date_to" in query_params:
                date_from = datetime.fromisoformat(query_params["date_from"])
                date_to = datetime.fromisoformat(query_params["date_to"])
                stmt = stmt.where(
                    CustomerEvent.event_timestamp >= date_from,
                    CustomerEvent.event_timestamp <= date_to,
                )
            stmt = stmt.order_by(CustomerEvent.event_timestamp.desc())
            result = await self.session.execute(stmt)
            events = list(result.scalars().all())
            for ev in events:
                writer.writerow([
                    str(ev.id), str(ev.customer_id) if ev.customer_id else "",
                    ev.event_type, ev.event_name, ev.channel, ev.source,
                    ev.value, ev.event_timestamp.isoformat() if ev.event_timestamp else "",
                ])

        elif export_type == "twins":
            writer.writerow([
                "customer_id", "engagement_score", "loyalty_score",
                "lifetime_value", "confidence_score", "staleness_score",
                "last_event_at", "status",
            ])
            stmt = select(CustomerTwin).where(
                CustomerTwin.organization_id == organization_id,
            )
            result = await self.session.execute(stmt)
            twins = list(result.scalars().all())
            for t in twins:
                writer.writerow([
                    str(t.customer_id), t.engagement_score, t.loyalty_score,
                    t.lifetime_value, t.confidence_score, t.staleness_score,
                    t.last_event_at.isoformat() if t.last_event_at else "",
                    t.status,
                ])

        else:
            raise NotFoundException("Export type", export_type)

        return output.getvalue().encode("utf-8")

    async def _count_customers(self, organization_id: uuid.UUID) -> int:
        stmt = select(func.count()).select_from(Customer).where(
            Customer.organization_id == organization_id,
            Customer.is_active.is_(True),
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def _count_events_since(self, organization_id: uuid.UUID, since: datetime) -> int:
        stmt = select(func.count()).select_from(CustomerEvent).where(
            CustomerEvent.organization_id == organization_id,
            CustomerEvent.event_timestamp >= since,
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def _count_active_campaigns(self, organization_id: uuid.UUID) -> int:
        stmt = select(func.count()).select_from(Campaign).where(
            Campaign.organization_id == organization_id,
            Campaign.status == "active",
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def _avg_twin_field(self, organization_id: uuid.UUID, field: Any) -> float | None:
        stmt = select(func.avg(field)).where(
            CustomerTwin.organization_id == organization_id,
            field.isnot(None),
        )
        result = await self.session.execute(stmt)
        val = result.scalar()
        return round(float(val), 4) if val is not None else None

    async def _segment_avg_twin_field(self, segment_id: uuid.UUID, organization_id: uuid.UUID, field: Any) -> float | None:
        stmt = (
            select(func.avg(field))
            .join(CustomerSegmentMapping, CustomerSegmentMapping.customer_id == CustomerTwin.customer_id)
            .where(
                CustomerSegmentMapping.segment_id == segment_id,
                CustomerTwin.organization_id == organization_id,
                field.isnot(None),
            )
        )
        result = await self.session.execute(stmt)
        val = result.scalar()
        return round(float(val), 4) if val is not None else None

    async def _segment_sum_twin_field(self, segment_id: uuid.UUID, organization_id: uuid.UUID, field: Any) -> float:
        stmt = (
            select(func.coalesce(func.sum(field), 0))
            .join(CustomerSegmentMapping, CustomerSegmentMapping.customer_id == CustomerTwin.customer_id)
            .where(
                CustomerSegmentMapping.segment_id == segment_id,
                CustomerTwin.organization_id == organization_id,
            )
        )
        result = await self.session.execute(stmt)
        return float(result.scalar() or 0)

    async def _sum_event_value_since(self, organization_id: uuid.UUID, event_type: str, since: datetime) -> float:
        stmt = select(func.coalesce(func.sum(CustomerEvent.value), 0)).where(
            CustomerEvent.organization_id == organization_id,
            CustomerEvent.event_type == event_type,
            CustomerEvent.event_timestamp >= since,
        )
        result = await self.session.execute(stmt)
        return float(result.scalar() or 0)

    async def _compute_churn_rate(self, organization_id: uuid.UUID, since: datetime) -> float | None:
        total = await self._count_customers(organization_id)
        if total == 0:
            return None

        churned_stmt = (
            select(func.count())
            .select_from(CustomerTwin)
            .where(
                CustomerTwin.organization_id == organization_id,
                or_(
                    CustomerTwin.staleness_score > 0.8,
                    and_(
                        CustomerTwin.engagement_score < 0.2,
                        CustomerTwin.last_event_at < since,
                    ),
                ),
            )
        )
        result = await self.session.execute(churned_stmt)
        churned = result.scalar() or 0
        return round(churned / total, 4)

    async def _get_top_segments(self, organization_id: uuid.UUID, limit: int) -> list[dict]:
        stmt = (
            select(
                CustomerSegment.id,
                CustomerSegment.name,
                func.count(CustomerSegmentMapping.customer_id).label("count"),
            )
            .outerjoin(
                CustomerSegmentMapping,
                CustomerSegmentMapping.segment_id == CustomerSegment.id,
            )
            .where(CustomerSegment.organization_id == organization_id)
            .group_by(CustomerSegment.id, CustomerSegment.name)
            .order_by(text("count desc"))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        rows = result.all()
        return [
            {
                "id": str(r.id), "name": r.name,
                "customer_count": int(r.count),
                "avg_engagement": 0.0,
                "revenue": 0.0,
            }
            for r in rows
        ]

    async def _get_daily_trend(self, organization_id: uuid.UUID, trend_type: str, since: datetime) -> list[dict]:
        if trend_type == "engagement":
            stmt = (
                select(
                    func.date_trunc("day", CustomerTwin.built_at).label("date"),
                    func.avg(CustomerTwin.engagement_score).label("value"),
                )
                .where(
                    CustomerTwin.organization_id == organization_id,
                    CustomerTwin.engagement_score.isnot(None),
                    CustomerTwin.built_at >= since,
                )
                .group_by(text("date"))
                .order_by(text("date"))
            )
        elif trend_type == "revenue":
            stmt = (
                select(
                    func.date_trunc("day", CustomerEvent.event_timestamp).label("date"),
                    func.coalesce(func.sum(CustomerEvent.value), 0).label("value"),
                )
                .where(
                    CustomerEvent.organization_id == organization_id,
                    CustomerEvent.event_type == "purchase",
                    CustomerEvent.event_timestamp >= since,
                )
                .group_by(text("date"))
                .order_by(text("date"))
            )
        else:
            return []

        result = await self.session.execute(stmt)
        rows = result.all()
        return [
            {
                "date": r.date.isoformat(),
                "value": round(float(r.value), 4) if r.value is not None else 0,
            }
            for r in rows if r.date is not None
        ]

    async def _get_segment_distribution(self, organization_id: uuid.UUID) -> list[dict]:
        stmt = (
            select(
                CustomerSegment.name,
                func.count(CustomerSegmentMapping.customer_id).label("count"),
            )
            .outerjoin(
                CustomerSegmentMapping,
                CustomerSegmentMapping.segment_id == CustomerSegment.id,
            )
            .where(CustomerSegment.organization_id == organization_id)
            .group_by(CustomerSegment.name)
            .order_by(text("count desc"))
        )
        result = await self.session.execute(stmt)
        rows = result.all()
        return [
            {"name": r.name, "value": int(r.count)}
            for r in rows
        ]

    async def _segment_customer_count(self, segment_id: uuid.UUID, organization_id: uuid.UUID) -> int:
        stmt = select(func.count()).select_from(CustomerSegmentMapping).where(
            CustomerSegmentMapping.segment_id == segment_id,
            CustomerSegmentMapping.organization_id == organization_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def _segment_at_risk_count(self, segment_id: uuid.UUID, organization_id: uuid.UUID) -> int:
        stmt = (
            select(func.count(func.distinct(CustomerTwin.customer_id)))
            .join(CustomerSegmentMapping, CustomerSegmentMapping.customer_id == CustomerTwin.customer_id)
            .where(
                CustomerSegmentMapping.segment_id == segment_id,
                CustomerTwin.organization_id == organization_id,
                or_(
                    CustomerTwin.staleness_score > 0.7,
                    CustomerTwin.engagement_score < 0.2,
                ),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def _segment_top_interests(self, segment_id: uuid.UUID, organization_id: uuid.UUID) -> list[dict]:
        from app.models.customer import CustomerInterest

        stmt = (
            select(
                CustomerInterest.category,
                func.count().label("count"),
                func.avg(CustomerInterest.affinity_score).label("avg_affinity"),
            )
            .join(CustomerSegmentMapping, CustomerSegmentMapping.customer_id == CustomerInterest.customer_id)
            .where(
                CustomerSegmentMapping.segment_id == segment_id,
                CustomerInterest.organization_id == organization_id,
                CustomerInterest.is_active.is_(True),
            )
            .group_by(CustomerInterest.category)
            .order_by(text("count desc"))
            .limit(10)
        )
        result = await self.session.execute(stmt)
        rows = result.all()
        return [
            {
                "category": r.category,
                "customer_count": int(r.count),
                "avg_affinity": round(float(r.avg_affinity or 0), 4),
            }
            for r in rows
        ]
