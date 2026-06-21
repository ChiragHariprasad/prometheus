import uuid
import math
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import NotFoundException
from app.core.logging import logger
from app.core.redis import RedisClient
from app.models.customer import Customer, CustomerInterest, CustomerSession
from app.models.event import Event as CustomerEvent
from app.models.twin import CustomerTwin
from app.repositories.customer_repository import CustomerRepository
from app.schemas.twin import (
    CustomerTwinResponse, TwinSummary, PerCustomerTwinSummary,
    BehaviorProfileResponse, InterestGraphResponse,
    ChannelAffinityResponse, RiskIndicatorsResponse,
    IntentForecastResponse,
)


class TwinService:
    def __init__(self, session: AsyncSession, redis: RedisClient | None = None):
        self.session = session
        self.redis = redis
        self.repo = CustomerRepository(session)

    async def get_or_build_twin(self, organization_id: uuid.UUID, customer_id: uuid.UUID) -> CustomerTwinResponse:
        customer, twin = await self.repo.get_with_twin(customer_id, organization_id)
        if not customer:
            raise NotFoundException("Customer", str(customer_id))

        if twin and twin.status == "built" and not twin.recalculation_required:
            return self._to_twin_response(twin, customer)

        return await self.rebuild_twin(organization_id, customer_id)

    async def rebuild_twin(self, organization_id: uuid.UUID, customer_id: uuid.UUID) -> CustomerTwinResponse:
        customer = await self.repo.get(customer_id, organization_id)
        if not customer:
            raise NotFoundException("Customer", str(customer_id))

        twin_stmt = select(CustomerTwin).where(
            CustomerTwin.customer_id == customer_id,
            CustomerTwin.organization_id == organization_id,
        )
        twin_result = await self.session.execute(twin_stmt)
        twin = twin_result.scalar_one_or_none()

        behavior = await self._compute_behavior_profile(customer_id, organization_id)
        interests = await self._compute_interest_graph(customer_id, organization_id)
        channel_affinity = await self._compute_channel_affinity(customer_id, organization_id)
        engagement = await self.compute_engagement_score(customer_id, organization_id)
        loyalty = await self.compute_loyalty_score(customer_id, organization_id)
        sentiment = await self.compute_sentiment_trend(organization_id, customer_id, days=30)
        staleness = await self.compute_staleness(customer_id, organization_id)
        ltv = await self._compute_lifetime_value(customer_id, organization_id)

        last_event = await self._get_last_event_time(customer_id, organization_id)

        twin_data = {
            "customer_id": customer_id,
            "organization_id": organization_id,
            "status": "built",
            "version": (twin.version if twin else 0) + 1,
            "behavior_profile": behavior,
            "interest_graph": interests,
            "channel_affinity": channel_affinity,
            "engagement_score": engagement,
            "loyalty_score": loyalty,
            "lifetime_value": ltv,
            "sentiment_trend": sentiment,
            "staleness_score": staleness,
            "recalculation_required": False,
            "last_event_at": last_event,
            "built_at": datetime.now(timezone.utc),
        }

        if twin:
            for key, value in twin_data.items():
                setattr(twin, key, value)
            await self.session.flush()
            await self.session.refresh(twin)
        else:
            twin = CustomerTwin(**twin_data)
            self.session.add(twin)
            await self.session.flush()
            await self.session.refresh(twin)

        logger.info("Twin rebuilt", extra={"customer_id": str(customer_id), "version": twin.version})
        return self._to_twin_response(twin, customer)

    async def update_twin_from_event(self, organization_id: uuid.UUID, customer_id: uuid.UUID, event: CustomerEvent) -> None:
        twin_stmt = select(CustomerTwin).where(
            CustomerTwin.customer_id == customer_id,
            CustomerTwin.organization_id == organization_id,
        )
        twin_result = await self.session.execute(twin_stmt)
        twin = twin_result.scalar_one_or_none()

        if not twin:
            return

        twin.last_event_at = event.event_timestamp

        if event.event_type == "purchase" and event.value:
            current_ltv = twin.lifetime_value or 0
            twin.lifetime_value = current_ltv + event.value

        if event.event_type in ("negative_feedback", "complaint", "support_ticket"):
            sentiment = twin.sentiment_trend or []
            decay = 0.1
            new_val = (sentiment[-1] - decay) if sentiment else -0.1
            sentiment.append(max(-1.0, new_val))
            twin.sentiment_trend = sentiment[-90:]

        twin.engagement_score = await self.compute_engagement_score(customer_id, organization_id)
        twin.staleness_score = await self.compute_staleness(customer_id, organization_id)

        await self.session.flush()

    async def get_twin_summary(self, organization_id: uuid.UUID, customer_id: uuid.UUID) -> PerCustomerTwinSummary:
        twin_stmt = select(CustomerTwin).where(
            CustomerTwin.customer_id == customer_id,
            CustomerTwin.organization_id == organization_id,
        )
        twin_result = await self.session.execute(twin_stmt)
        twin = twin_result.scalar_one_or_none()

        if not twin:
            customer = await self.repo.get(customer_id, organization_id)
            if not customer:
                raise NotFoundException("Customer", str(customer_id))
            return PerCustomerTwinSummary()

        risk = twin.risk_indicators or {}
        return PerCustomerTwinSummary(
            engagement_score=twin.engagement_score,
            loyalty_score=twin.loyalty_score,
            lifetime_value=twin.lifetime_value,
            sentiment_trend=twin.sentiment_trend or [],
            churn_probability=risk.get("churn_probability"),
            churn_risk_level=risk.get("churn_risk_level"),
            lifecycle_stage=(twin.behavior_profile or {}).get("lifecycle_stage"),
            rfm_segment=(twin.behavior_profile or {}).get("rfm_segment"),
            version=twin.version,
            confidence_score=twin.confidence_score,
            staleness_score=twin.staleness_score,
            last_event_at=twin.last_event_at,
            last_prediction_at=twin.last_prediction_at,
            status=twin.status,
        )

    async def get_org_summary(self, organization_id: uuid.UUID) -> TwinSummary | None:
        stmt = select(
            func.count(CustomerTwin.id),
            func.avg(CustomerTwin.engagement_score),
            func.avg(CustomerTwin.loyalty_score),
        ).where(CustomerTwin.organization_id == organization_id)
        result = await self.session.execute(stmt)
        row = result.one_or_none()
        if not row or row[0] == 0:
            return None
        total, avg_eng, avg_loy = row
        return TwinSummary(
            total_twins=int(total),
            avg_engagement=round(float(avg_eng or 0), 2),
            avg_loyalty=round(float(avg_loy or 0), 2),
        )

    async def compute_engagement_score(self, customer_id: uuid.UUID, organization_id: uuid.UUID) -> float:
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)
        ninety_days_ago = now - timedelta(days=90)

        count_30d = await self._count_events(customer_id, organization_id, thirty_days_ago)
        count_90d = await self._count_events(customer_id, organization_id, ninety_days_ago)

        sessions_count = await self._count_sessions(customer_id, organization_id, thirty_days_ago)

        purchase_count = await self._count_event_type(customer_id, organization_id, "purchase", thirty_days_ago)

        score = 0.0
        score += min(count_30d / 20.0, 0.3)
        score += min(sessions_count / 10.0, 0.2)
        score += min(purchase_count * 0.1, 0.2)

        if count_90d > 0:
            recent_ratio = count_30d / max(count_90d, 1)
            score += min(recent_ratio * 0.2, 0.2)

        score = min(max(score, 0.0), 1.0)
        return round(score, 4)

    async def compute_loyalty_score(self, customer_id: uuid.UUID, organization_id: uuid.UUID) -> float:
        now = datetime.now(timezone.utc)
        year_ago = now - timedelta(days=365)

        purchase_count = await self._count_event_type(customer_id, organization_id, "purchase", year_ago)
        total_revenue = await self._sum_event_value(customer_id, organization_id, "purchase", year_ago)
        return_count = await self._count_event_type(customer_id, organization_id, "return", year_ago)
        referral_count = await self._count_event_type(customer_id, organization_id, "referral", year_ago)

        score = 0.0
        score += min(purchase_count * 0.05, 0.2)
        score += min((total_revenue or 0) / 10000, 0.3)
        score -= min(return_count * 0.1, 0.2)
        score += min(referral_count * 0.1, 0.2)

        customer = await self.repo.get(customer_id, organization_id)
        if customer and customer.first_seen_at:
            days_since_first = (now - customer.first_seen_at).days
            if days_since_first > 365:
                score += 0.1
            if days_since_first > 730:
                score += 0.1

        score = min(max(score, 0.0), 1.0)
        return round(score, 4)

    async def compute_sentiment_trend(self, organization_id: uuid.UUID, customer_id: uuid.UUID, days: int = 30) -> list[float]:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        stmt = (
            select(CustomerEvent)
            .where(
                CustomerEvent.customer_id == customer_id,
                CustomerEvent.organization_id == organization_id,
                CustomerEvent.event_timestamp >= since,
            )
            .order_by(CustomerEvent.event_timestamp.asc())
        )
        result = await self.session.execute(stmt)
        events = list(result.scalars().all())

        if not events:
            return []

        sentiment_map = {
            "purchase": 0.3,
            "positive_feedback": 0.5,
            "email_open": 0.1,
            "email_click": 0.2,
            "app_open": 0.1,
            "page_view": 0.05,
            "referral": 0.4,
            "support_resolved": 0.2,
            "negative_feedback": -0.4,
            "complaint": -0.5,
            "support_ticket": -0.2,
            "unsubscribe": -0.6,
            "bounce": -0.1,
            "cart_abandon": -0.2,
        }

        trend = []
        running = 0.0
        for ev in events:
            delta = sentiment_map.get(ev.event_type, 0.0)
            running = max(-1.0, min(1.0, running + delta * 0.3))
            trend.append(round(running, 4))

        if len(trend) > days:
            step = len(trend) // days
            trend = [trend[i * step] for i in range(days)]

        return trend

    async def compute_staleness(self, customer_id: uuid.UUID, organization_id: uuid.UUID) -> float:
        last_event = await self._get_last_event_time(customer_id, organization_id)
        if not last_event:
            return 1.0

        days_since = (datetime.now(timezone.utc) - last_event).days
        half_life = settings.TWIN_STALENESS_HALF_LIFE_DAYS
        staleness = 1.0 - math.exp(-days_since / half_life)
        return round(min(max(staleness, 0.0), 1.0), 4)

    async def _compute_behavior_profile(self, customer_id: uuid.UUID, organization_id: uuid.UUID) -> dict[str, Any]:
        now = datetime.now(timezone.utc)

        sessions_stmt = select(func.count(), func.avg(CustomerSession.duration_seconds)).where(
            CustomerSession.customer_id == customer_id,
            CustomerSession.organization_id == organization_id,
            CustomerSession.session_start >= now - timedelta(days=30),
        )
        sessions_result = await self.session.execute(sessions_stmt)
        sessions_count, avg_duration = sessions_result.one()

        purchases_30d = await self._count_event_type(customer_id, organization_id, "purchase", now - timedelta(days=30))
        purchase_value_30d = await self._sum_event_value(customer_id, organization_id, "purchase", now - timedelta(days=30))

        bounces = await self._count_event_type(customer_id, organization_id, "bounce", now - timedelta(days=30))
        page_views = await self._count_event_type(customer_id, organization_id, "page_view", now - timedelta(days=30))

        emails_sent = await self._count_event_type(customer_id, organization_id, "email_sent", now - timedelta(days=30))
        emails_opened = await self._count_event_type(customer_id, organization_id, "email_open", now - timedelta(days=30))
        emails_clicked = await self._count_event_type(customer_id, organization_id, "email_click", now - timedelta(days=30))

        cart_abandons = await self._count_event_type(customer_id, organization_id, "cart_abandon", now - timedelta(days=30))

        customer = await self.repo.get(customer_id, organization_id)

        return {
            "sessions_per_week": round((sessions_count or 0) / 4.0, 2),
            "avg_session_duration": round(avg_duration or 0, 2),
            "page_depth_avg": round((page_views or 0) / max(sessions_count or 1, 1), 2),
            "bounce_rate": round((bounces or 0) / max(sessions_count or 1, 1), 4),
            "purchase_frequency": round((purchases_30d or 0) / 4.0, 2),
            "avg_order_value": round((purchase_value_30d or 0) / max(purchases_30d or 1, 1), 2),
            "cart_abandonment_rate": round((cart_abandons or 0) / max((purchases_30d or 0) + (cart_abandons or 0), 1), 4),
            "email_open_rate": round((emails_opened or 0) / max(emails_sent or 1, 1), 4),
            "email_click_rate": round((emails_clicked or 0) / max(emails_opened or 1, 1), 4),
            "days_since_first_seen": (now - customer.first_seen_at).days if customer and customer.first_seen_at else None,
            "days_since_last_seen": (now - customer.last_seen_at).days if customer and customer.last_seen_at else None,
            "lifecycle_stage": self._determine_lifecycle_stage(customer, purchases_30d or 0, sessions_count or 0),
        }

    def _determine_lifecycle_stage(self, customer: Customer | None, purchases_30d: int, sessions_30d: int) -> str:
        if not customer:
            return "unknown"
        if customer.first_seen_at and (datetime.now(timezone.utc) - customer.first_seen_at).days <= 7:
            return "new"
        if purchases_30d >= 3:
            return "loyal"
        if purchases_30d >= 1:
            return "active"
        if sessions_30d > 0:
            return "engaged"
        if customer.last_seen_at and (datetime.now(timezone.utc) - customer.last_seen_at).days > 90:
            return "dormant"
        if customer.last_seen_at and (datetime.now(timezone.utc) - customer.last_seen_at).days > 30:
            return "at_risk"
        return "engaged"

    async def _compute_interest_graph(self, customer_id: uuid.UUID, organization_id: uuid.UUID) -> dict[str, Any]:
        stmt = (
            select(CustomerInterest)
            .where(
                CustomerInterest.customer_id == customer_id,
                CustomerInterest.organization_id == organization_id,
                CustomerInterest.is_active.is_(True),
            )
            .order_by(CustomerInterest.affinity_score.desc().nullslast())
        )
        result = await self.session.execute(stmt)
        interests = list(result.scalars().all())

        nodes = [
            {
                "category": i.category,
                "subcategory": i.subcategory,
                "interest_level": i.interest_level,
                "affinity_score": i.affinity_score,
                "interaction_count": i.interaction_count,
            }
            for i in interests
        ]

        dominant = interests[0].category if interests else None
        total_interactions = sum(i.interaction_count or 0 for i in interests)
        unique_categories = len(set(i.category for i in interests))
        diversity = min(unique_categories / 10.0, 1.0) if interests else 0.0

        return {
            "nodes": nodes,
            "dominant_category": dominant,
            "interest_diversity": round(diversity, 4),
            "total_interactions": total_interactions,
        }

    async def _compute_channel_affinity(self, customer_id: uuid.UUID, organization_id: uuid.UUID) -> dict[str, Any]:
        channels = ["email", "sms", "push", "in_app", "whatsapp"]
        result = {}
        for channel in channels:
            count = await self._count_channel_events(customer_id, organization_id, channel)
            if count > 0:
                result[channel] = {
                    "interaction_count": count,
                    "affinity": round(min(count / 50.0, 1.0), 4),
                }
            else:
                result[channel] = {"interaction_count": 0, "affinity": 0.0}
        return result

    async def _compute_lifetime_value(self, customer_id: uuid.UUID, organization_id: uuid.UUID) -> float:
        stmt = select(func.coalesce(func.sum(CustomerEvent.value), 0)).where(
            CustomerEvent.customer_id == customer_id,
            CustomerEvent.organization_id == organization_id,
            CustomerEvent.event_type == "purchase",
        )
        result = await self.session.execute(stmt)
        total = result.scalar() or 0.0
        return round(float(total), 2)

    async def _get_last_event_time(self, customer_id: uuid.UUID, organization_id: uuid.UUID) -> datetime | None:
        stmt = (
            select(CustomerEvent.event_timestamp)
            .where(
                CustomerEvent.customer_id == customer_id,
                CustomerEvent.organization_id == organization_id,
            )
            .order_by(CustomerEvent.event_timestamp.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _count_events(self, customer_id: uuid.UUID, organization_id: uuid.UUID, since: datetime) -> int:
        stmt = select(func.count()).select_from(CustomerEvent).where(
            CustomerEvent.customer_id == customer_id,
            CustomerEvent.organization_id == organization_id,
            CustomerEvent.event_timestamp >= since,
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def _count_event_type(self, customer_id: uuid.UUID, organization_id: uuid.UUID, event_type: str, since: datetime) -> int:
        stmt = select(func.count()).select_from(CustomerEvent).where(
            CustomerEvent.customer_id == customer_id,
            CustomerEvent.organization_id == organization_id,
            CustomerEvent.event_type == event_type,
            CustomerEvent.event_timestamp >= since,
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def _sum_event_value(self, customer_id: uuid.UUID, organization_id: uuid.UUID, event_type: str, since: datetime) -> float:
        stmt = select(func.coalesce(func.sum(CustomerEvent.value), 0)).where(
            CustomerEvent.customer_id == customer_id,
            CustomerEvent.organization_id == organization_id,
            CustomerEvent.event_type == event_type,
            CustomerEvent.event_timestamp >= since,
        )
        result = await self.session.execute(stmt)
        return float(result.scalar() or 0)

    async def _count_channel_events(self, customer_id: uuid.UUID, organization_id: uuid.UUID, channel: str) -> int:
        stmt = select(func.count()).select_from(CustomerEvent).where(
            CustomerEvent.customer_id == customer_id,
            CustomerEvent.organization_id == organization_id,
            CustomerEvent.channel == channel,
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def _count_sessions(self, customer_id: uuid.UUID, organization_id: uuid.UUID, since: datetime) -> int:
        stmt = select(func.count()).select_from(CustomerSession).where(
            CustomerSession.customer_id == customer_id,
            CustomerSession.organization_id == organization_id,
            CustomerSession.session_start >= since,
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    def _to_twin_response(self, twin: CustomerTwin, customer: Customer) -> CustomerTwinResponse:
        behavior = twin.behavior_profile or {}
        interest = twin.interest_graph or {}
        affinity = twin.channel_affinity or {}
        risk = twin.risk_indicators or {}
        intent = twin.intent_forecast or {}

        return CustomerTwinResponse(
            customer_id=twin.customer_id,
            organization_id=twin.organization_id,
            status=twin.status,
            version=twin.version,
            behavior_profile=BehaviorProfileResponse(
                sessions_per_week=behavior.get("sessions_per_week"),
                avg_session_duration=behavior.get("avg_session_duration"),
                page_depth_avg=behavior.get("page_depth_avg"),
                bounce_rate=behavior.get("bounce_rate"),
                purchase_frequency=behavior.get("purchase_frequency"),
                avg_order_value=behavior.get("avg_order_value"),
                product_category_affinity=behavior.get("product_category_affinity", {}),
                discount_sensitivity=behavior.get("discount_sensitivity"),
                cart_abandonment_rate=behavior.get("cart_abandonment_rate"),
                email_open_rate=behavior.get("email_open_rate"),
                email_click_rate=behavior.get("email_click_rate"),
                push_opt_in=behavior.get("push_opt_in"),
                preferred_time_of_day=behavior.get("preferred_time_of_day"),
                preferred_day_of_week=behavior.get("preferred_day_of_week"),
                days_since_first_seen=behavior.get("days_since_first_seen"),
                days_since_last_purchase=behavior.get("days_since_last_purchase"),
                days_since_last_engagement=behavior.get("days_since_last_engagement"),
                lifecycle_stage=behavior.get("lifecycle_stage"),
                rfm_recency=behavior.get("rfm_recency"),
                rfm_frequency=behavior.get("rfm_frequency"),
                rfm_monetary=behavior.get("rfm_monetary"),
                rfm_segment=behavior.get("rfm_segment"),
            ) if behavior else None,
            interest_graph=InterestGraphResponse(
                nodes=interest.get("nodes", []),
                dominant_category=interest.get("dominant_category"),
                interest_diversity=interest.get("interest_diversity"),
                total_interactions=interest.get("total_interactions", 0),
            ) if interest else None,
            channel_affinity=ChannelAffinityResponse(
                email=affinity.get("email", {}),
                sms=affinity.get("sms", {}),
                push=affinity.get("push", {}),
                in_app=affinity.get("in_app", {}),
            ) if affinity else None,
            engagement_score=twin.engagement_score,
            loyalty_score=twin.loyalty_score,
            lifetime_value=twin.lifetime_value,
            sentiment_trend=twin.sentiment_trend or [],
            intent_forecast=IntentForecastResponse(
                purchase_intent_7d=intent.get("purchase_intent_7d"),
                engagement_intent_7d=intent.get("engagement_intent_7d"),
                churn_risk_7d=intent.get("churn_risk_7d"),
                purchase_intent_30d=intent.get("purchase_intent_30d"),
                engagement_intent_30d=intent.get("engagement_intent_30d"),
                churn_risk_30d=intent.get("churn_risk_30d"),
                predicted_ltv_90d=intent.get("predicted_ltv_90d"),
                predicted_engagement_90d=intent.get("predicted_engagement_90d"),
                recommended_action=intent.get("recommended_action"),
                recommended_channel=intent.get("recommended_channel"),
            ) if intent else None,
            risk_indicators=RiskIndicatorsResponse(
                churn_probability=risk.get("churn_probability"),
                churn_risk_level=risk.get("churn_risk_level"),
                churn_triggers=risk.get("churn_triggers", []),
                churn_prevention_actions=risk.get("churn_prevention_actions", []),
                engagement_decline_rate=risk.get("engagement_decline_rate"),
                negative_sentiment_count=risk.get("negative_sentiment_count", 0),
                complaint_count=risk.get("complaint_count", 0),
                support_ticket_count=risk.get("support_ticket_count", 0),
                unsubscribe_risk=risk.get("unsubscribe_risk"),
                behavior_anomaly_score=risk.get("behavior_anomaly_score"),
            ) if risk else None,
            communication_preferences=twin.communication_preferences or {},
            confidence_score=twin.confidence_score,
            staleness_score=twin.staleness_score,
            built_at=twin.built_at,
        )
