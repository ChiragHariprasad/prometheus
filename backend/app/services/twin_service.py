import uuid
import math
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import select, func, text
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
    BehaviorProfileResponse, BehaviorSubScores,
    InterestGraphResponse, MemoryProfileResponse,
    ChannelAffinityResponse, RiskIndicatorsResponse,
    IntentForecastResponse, TwinOutputResponse,
)


EVENT_WEIGHTS = {
    "purchase": 10,
    "email_click": 4,
    "email_open": 2,
    "page_view": 1,
    "login": 1,
}

RECENCY_HALF_LIFE_DAYS = 30
INTEREST_DECAY_DAYS = 90

SENTIMENT_SOURCES = {
    "positive_feedback": 0.8,
    "review_submit": 0.6,
    "support_resolved": 0.4,
    "survey_response": 0.5,
    "feedback": 0.0,
    "negative_feedback": -0.8,
    "complaint": -1.0,
    "support_ticket": -0.5,
}

SENTIMENT_HALF_LIFE_DAYS = 30


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
        ).with_for_update()
        twin_result = await self.session.execute(twin_stmt)
        twin = twin_result.scalar_one_or_none()

        behavior = await self._compute_behavior_profile(customer_id, organization_id)
        interests = await self._compute_interest_graph(customer_id, organization_id)
        memory = await self._compute_memory_profile(customer_id, organization_id)
        channel_affinity = await self._compute_channel_affinity(customer_id, organization_id)
        engagement = await self.compute_engagement_score(customer_id, organization_id)
        loyalty_data = await self.compute_loyalty_score(customer_id, organization_id, twin)
        sentiment_data = await self.compute_sentiment(organization_id, customer_id, days=90)
        staleness = await self.compute_staleness(customer_id, organization_id)
        ltv = await self._compute_lifetime_value(customer_id, organization_id)

        last_event = await self._get_last_event_time(customer_id, organization_id)

        behavior_score = behavior.get("behavior_score", 0.0)
        lifecycle_stage = behavior.get("lifecycle_stage", "inactive")
        loyalty_score = loyalty_data["score"]

        intent_forecast, risk_indicators = self._compute_predictions(
            behavior_score, engagement, loyalty_score, ltv, sentiment_data["trend"], staleness, lifecycle_stage
        )

        data_completeness = self._compute_data_completeness(behavior, interests, memory, customer)
        prediction_agreement = self._compute_prediction_agreement(intent_forecast, risk_indicators)
        recency_score = 1.0 - staleness
        confidence = self._compute_confidence_score(data_completeness, recency_score, prediction_agreement)

        twin_output = self._build_twin_output(sentiment_data["trend"], risk_indicators, ltv, lifecycle_stage)

        twin_data = {
            "customer_id": customer_id,
            "organization_id": organization_id,
            "status": "built",
            "twin_metadata": {
                "twin_output": twin_output,
                "current_sentiment": sentiment_data["current"],
                "sentiment_velocity": sentiment_data["velocity"],
                "sentiment_volatility": sentiment_data["volatility"],
                "loyalty_segment": loyalty_data["segment"],
                "loyalty_trend": loyalty_data["trend"],
                "loyalty_sub_scores": loyalty_data["sub_scores"],
                "loyalty_score_prior": loyalty_score,
            },
            "version": (twin.version if twin else 0) + 1,
            "behavior_profile": behavior,
            "interest_graph": interests,
            "memory_profile": memory,
            "channel_affinity": channel_affinity,
            "engagement_score": engagement,
            "loyalty_score": loyalty_score,
            "lifetime_value": ltv,
            "sentiment_trend": sentiment_data["trend"],
            "intent_forecast": intent_forecast,
            "risk_indicators": risk_indicators,
            "confidence_score": confidence,
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

        if self.redis:
            await self.redis.delete(f"twin:{customer_id}", f"org:{organization_id}:twins")
        logger.info("Twin rebuilt", extra={"customer_id": str(customer_id), "version": twin.version})
        return self._to_twin_response(twin, customer)

    def _compute_predictions(
        self,
        behavior_score: float,
        engagement: float,
        loyalty: float,
        ltv: float,
        sentiment_trend: list[float],
        staleness: float,
        lifecycle_stage: str,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        avg_sentiment = round(sum(sentiment_trend) / len(sentiment_trend), 4) if sentiment_trend else 0.0
        churn_probability = round(
            max(0.0, min(1.0, (1.0 - engagement) * 0.5 + staleness * 0.3 + max(0, -avg_sentiment) * 0.2)), 4
        )
        risk_level = "low"
        if churn_probability > 0.5:
            risk_level = "high"
        elif churn_probability > 0.25:
            risk_level = "medium"

        purchase_intent = round(max(0.0, min(1.0, behavior_score * 0.4 + engagement * 0.3 + loyalty * 0.3)), 4)
        engagement_intent = round(max(0.0, min(1.0, engagement * 0.5 + (1.0 - staleness) * 0.5)), 4)
        predicted_ltv = round(ltv * (1.0 + engagement * 0.3 + loyalty * 0.2 - churn_probability * 0.5), 2)

        action_map = {
            "dormant": ("re_engagement_campaign", "email"),
            "at_risk": ("retention_discount", "email"),
            "inactive": ("reactivation_offer", "sms"),
            "active": ("cross_sell", "push"),
            "loyal": ("loyalty_reward", "in_app"),
        }
        recommended_action, recommended_channel = action_map.get(lifecycle_stage, ("engagement_nurture", "email"))

        return {
            "purchase_intent_7d": purchase_intent,
            "engagement_intent_7d": engagement_intent,
            "churn_risk_7d": churn_probability,
            "purchase_intent_30d": round(purchase_intent * 0.8, 4),
            "engagement_intent_30d": round(engagement_intent * 0.85, 4),
            "churn_risk_30d": round(churn_probability * 1.2, 4),
            "predicted_ltv_90d": predicted_ltv,
            "predicted_engagement_90d": round(engagement * 0.7 + 0.2, 4),
            "recommended_action": recommended_action,
            "recommended_channel": recommended_channel,
        }, {
            "churn_probability": churn_probability,
            "churn_risk_level": risk_level,
            "churn_triggers": [],
            "churn_prevention_actions": [],
            "engagement_decline_rate": 0.0,
            "negative_sentiment_count": sum(1 for s in sentiment_trend if s < 0),
            "complaint_count": 0,
            "support_ticket_count": 0,
            "unsubscribe_risk": round(churn_probability * 0.7, 4),
            "behavior_anomaly_score": round(1.0 - abs(engagement - behavior_score), 4),
        }

    def _build_twin_output(
        self,
        sentiment_trend: list[float],
        risk_indicators: dict[str, Any],
        ltv: float,
        lifecycle_stage: str,
    ) -> dict[str, Any]:
        sentiment = round(sum(sentiment_trend) / len(sentiment_trend), 4) if sentiment_trend else 0.0
        churn = risk_indicators.get("churn_probability", 0.0)
        action_map = {
            "dormant": "re_engagement",
            "at_risk": "retention_offer",
            "inactive": "win_back",
            "engaged": "cross_sell",
            "active": "upsell",
            "loyal": "referral_request",
        }
        return {
            "sentiment": sentiment,
            "purchase_intent": round(1.0 - churn * 0.5, 4),
            "churn_probability": churn,
            "lifetime_value": ltv,
            "next_best_action": action_map.get(lifecycle_stage, "engage"),
        }

    async def update_twin_from_event(self, organization_id: uuid.UUID, customer_id: uuid.UUID, event: CustomerEvent) -> None:
        twin_stmt = select(CustomerTwin).where(
            CustomerTwin.customer_id == customer_id,
            CustomerTwin.organization_id == organization_id,
        ).with_for_update()
        twin_result = await self.session.execute(twin_stmt)
        twin = twin_result.scalar_one_or_none()

        if not twin:
            return

        twin.last_event_at = event.event_timestamp

        if event.event_type == "purchase" and event.value:
            current_ltv = twin.lifetime_value or 0
            twin.lifetime_value = current_ltv + event.value

            memory = twin.memory_profile or {}
            purchase_cats = memory.get("purchase_categories", [])
            category = (event.event_properties or {}).get("category", "uncategorized")
            existing = next((c for c in purchase_cats if c["category"] == category), None)
            if existing:
                existing["count"] = existing.get("count", 0) + 1
                existing["total_value"] = existing.get("total_value", 0) + (event.value or 0)
                existing["last_purchase_at"] = event.event_timestamp.isoformat()
            else:
                purchase_cats.append({
                    "category": category,
                    "count": 1,
                    "total_value": event.value or 0,
                    "last_purchase_at": event.event_timestamp.isoformat(),
                })
            memory["purchase_categories"] = purchase_cats

            discount_used = (event.event_properties or {}).get("discount_applied", False)
            if discount_used:
                ds = memory.get("discount_sensitivity", 0.0)
                memory["discount_sensitivity"] = round(min(1.0, ds + 0.05), 4)
            twin.memory_profile = memory

        if event.event_type in SENTIMENT_SOURCES:
            base_impact = SENTIMENT_SOURCES[event.event_type]
            rating = (event.event_properties or {}).get("rating")
            if rating is not None and event.event_type in ("review_submit", "survey_response", "feedback"):
                adjusted = (rating - 3) / 2.0
                base_impact = max(-1.0, min(1.0, adjusted))

            trend = twin.sentiment_trend or []
            previous = trend[-1] if trend else 0.0
            new_val = max(-1.0, min(1.0, previous + base_impact * 0.3))
            trend.append(round(new_val, 4))
            twin.sentiment_trend = trend[-90:]

            twin_meta = twin.twin_metadata or {}
            twin_meta["current_sentiment"] = round(new_val, 4)

            recent = trend[-min(len(trend), 10):]
            if len(recent) >= 2:
                deltas = [recent[i] - recent[i - 1] for i in range(1, len(recent))]
                twin_meta["sentiment_velocity"] = round(sum(deltas) / len(deltas), 4)
                avg_delta = sum(deltas) / len(deltas)
                twin_meta["sentiment_volatility"] = round(
                    math.sqrt(sum((d - avg_delta) ** 2 for d in deltas) / len(deltas)), 4
                )
            twin.twin_metadata = twin_meta

        if event.campaign_id:
            memory = twin.memory_profile or {}
            campaign_responses = memory.get("campaign_responses", [])
            campaign_responses.append({
                "campaign_id": str(event.campaign_id),
                "event_type": event.event_type,
                "channel": event.channel,
                "timestamp": event.event_timestamp.isoformat(),
            })
            memory["campaign_responses"] = campaign_responses[-100:]
            twin.memory_profile = memory

        memory = twin.memory_profile or {}
        channel_history = memory.get("channel_history", [])
        if event.channel:
            existing_ch = next((ch for ch in channel_history if ch["channel"] == event.channel), None)
            if existing_ch:
                existing_ch["count"] = existing_ch.get("count", 0) + 1
                existing_ch["last_interaction_at"] = event.event_timestamp.isoformat()
            else:
                channel_history.append({
                    "channel": event.channel,
                    "count": 1,
                    "last_interaction_at": event.event_timestamp.isoformat(),
                })
        memory["channel_history"] = channel_history
        twin.memory_profile = memory

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
        trend = twin.sentiment_trend or []
        sentiment_score = round(sum(trend) / len(trend), 4) if trend else None
        return PerCustomerTwinSummary(
            engagement_score=twin.engagement_score,
            loyalty_score=twin.loyalty_score,
            lifetime_value=twin.lifetime_value,
            sentiment_trend=trend,
            sentiment_score=sentiment_score,
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

    async def rebuild_stale_twins(self) -> int:
        stmt = select(CustomerTwin).where(
            CustomerTwin.staleness_score > settings.TWIN_STALENESS_THRESHOLD,
            CustomerTwin.status == "built",
        )
        result = await self.session.execute(stmt)
        stale_twins = list(result.scalars().all())
        count = 0
        for twin in stale_twins:
            try:
                await self.rebuild_twin(twin.organization_id, twin.customer_id)
                count += 1
            except Exception as e:
                logger.warning("Failed to rebuild stale twin", extra={
                    "customer_id": str(twin.customer_id), "error": str(e),
                })
        logger.info("Stale twins rebuilt", extra={"count": count})
        return count

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

    async def compute_loyalty_score(
        self, customer_id: uuid.UUID, organization_id: uuid.UUID,
        twin: CustomerTwin | None = None,
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        year_ago = now - timedelta(days=365)

        customer = await self.repo.get(customer_id, organization_id)

        purchase_timestamps = await self._get_purchase_timestamps(customer_id, organization_id, year_ago)
        purchase_count = len(purchase_timestamps)
        total_revenue = await self._sum_event_value(customer_id, organization_id, "purchase", year_ago)
        return_count = await self._count_event_type(customer_id, organization_id, "return", year_ago)
        referral_count = await self._count_event_type(customer_id, organization_id, "referral", year_ago)
        campaign_count = await self._count_campaign_events(customer_id, organization_id, year_ago)
        active_weeks = await self._count_weekly_active_weeks(customer_id, organization_id, 12)

        interval_score = 0.0
        if purchase_count >= 2:
            intervals = [(purchase_timestamps[i + 1] - purchase_timestamps[i]).days for i in range(purchase_count - 1)]
            avg_interval = sum(intervals) / len(intervals)
            interval_score = math.exp(-avg_interval / 60.0)

        tenure_score = 0.0
        if customer and customer.first_seen_at:
            tenure_days = min((now - customer.first_seen_at).days, 1095)
            tenure_score = tenure_days / 1095.0

        campaign_score = min(campaign_count / 20.0, 1.0)
        consistency_score = active_weeks / 12.0
        referral_score = min(referral_count * 0.2, 1.0)
        return_rate = return_count / max(purchase_count, 1)
        return_rate_score = 1.0 - min(return_rate, 1.0)
        revenue_score = min((total_revenue or 0) / 5000.0, 1.0)

        score = (
            interval_score * 0.20 +
            tenure_score * 0.10 +
            campaign_score * 0.10 +
            consistency_score * 0.20 +
            referral_score * 0.10 +
            return_rate_score * 0.10 +
            revenue_score * 0.20
        )
        score = min(max(score, 0.0), 1.0)

        if score >= 0.8:
            segment = "champion"
        elif score >= 0.6:
            segment = "loyal"
        elif score >= 0.4:
            segment = "regular"
        elif score >= 0.2:
            segment = "at_risk"
        else:
            segment = "inactive"

        prior_score = None
        if twin and twin.twin_metadata:
            prior_score = twin.twin_metadata.get("loyalty_score_prior")
        trend = "stable"
        if prior_score is not None:
            delta = score - prior_score
            if delta > 0.05:
                trend = "increasing"
            elif delta < -0.05:
                trend = "decreasing"

        return {
            "score": round(score, 4),
            "segment": segment,
            "trend": trend,
            "sub_scores": {
                "repeat_purchase_interval": round(interval_score, 4),
                "customer_tenure": round(tenure_score, 4),
                "campaign_participation": round(campaign_score, 4),
                "engagement_consistency": round(consistency_score, 4),
                "referral_behavior": round(referral_score, 4),
                "return_rate": round(return_rate_score, 4),
                "revenue_contribution": round(revenue_score, 4),
            },
        }

    async def _get_purchase_timestamps(
        self, customer_id: uuid.UUID, organization_id: uuid.UUID, since: datetime,
    ) -> list[datetime]:
        stmt = (
            select(CustomerEvent.event_timestamp)
            .where(
                CustomerEvent.customer_id == customer_id,
                CustomerEvent.organization_id == organization_id,
                CustomerEvent.event_type == "purchase",
                CustomerEvent.event_timestamp >= since,
            )
            .order_by(CustomerEvent.event_timestamp.asc())
        )
        result = await self.session.execute(stmt)
        return [row[0] for row in result.all()]

    async def _count_campaign_events(
        self, customer_id: uuid.UUID, organization_id: uuid.UUID, since: datetime,
    ) -> int:
        stmt = select(func.count()).select_from(CustomerEvent).where(
            CustomerEvent.customer_id == customer_id,
            CustomerEvent.organization_id == organization_id,
            CustomerEvent.campaign_id.is_not(None),
            CustomerEvent.event_timestamp >= since,
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def _count_weekly_active_weeks(
        self, customer_id: uuid.UUID, organization_id: uuid.UUID, weeks: int,
    ) -> int:
        now = datetime.now(timezone.utc)
        since = now - timedelta(weeks=weeks)
        stmt = (
            select(
                func.date_trunc("week", CustomerEvent.event_timestamp).label("week"),
            )
            .where(
                CustomerEvent.customer_id == customer_id,
                CustomerEvent.organization_id == organization_id,
                CustomerEvent.event_timestamp >= since,
            )
            .group_by(text("week"))
        )
        result = await self.session.execute(stmt)
        return len(result.all())

    async def compute_sentiment(self, organization_id: uuid.UUID, customer_id: uuid.UUID, days: int = 90) -> dict[str, Any]:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        stmt = (
            select(CustomerEvent)
            .where(
                CustomerEvent.customer_id == customer_id,
                CustomerEvent.organization_id == organization_id,
                CustomerEvent.event_type.in_(list(SENTIMENT_SOURCES.keys())),
                CustomerEvent.event_timestamp >= since,
            )
            .order_by(CustomerEvent.event_timestamp.asc())
        )
        result = await self.session.execute(stmt)
        events = list(result.scalars().all())

        now = datetime.now(timezone.utc)
        trend = []
        running = 0.0
        for ev in events:
            base = SENTIMENT_SOURCES[ev.event_type]
            rating = (ev.event_properties or {}).get("rating")
            if rating is not None and ev.event_type in ("review_submit", "survey_response", "feedback"):
                adjusted = (rating - 3) / 2.0
                base = max(-1.0, min(1.0, adjusted))

            days_since = max(0, (now - ev.event_timestamp).days)
            decay = math.exp(-days_since / SENTIMENT_HALF_LIFE_DAYS)
            impact = base * decay

            running += impact * 0.3
            running = max(-1.0, min(1.0, running))
            trend.append(round(running, 4))

        if not trend:
            return {"trend": [], "current": 0.0, "velocity": 0.0, "volatility": 0.0}

        current = trend[-1]
        velocity = 0.0
        volatility = 0.0

        if len(trend) >= 2:
            deltas = [trend[i] - trend[i - 1] for i in range(1, len(trend))]
            velocity = round(sum(deltas) / len(deltas), 4)
            mean_delta = sum(deltas) / len(deltas)
            volatility = round(math.sqrt(sum((d - mean_delta) ** 2 for d in deltas) / len(deltas)), 4)

        return {"trend": trend, "current": current, "velocity": velocity, "volatility": volatility}

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

        last_event = await self._get_last_event_time(customer_id, organization_id)
        days_since_last_engagement = (now - last_event).days if last_event else None

        events_90d = await self._get_weighted_events(customer_id, organization_id, days=90)
        weighted_sum = sum(ev["weight"] for ev in events_90d)

        engagement = min(weighted_sum / 50.0, 1.0)
        purchase_activity = min((purchases_30d or 0) * 0.2, 1.0)
        session_depth_val = min(((sessions_count or 0) / 20.0) * 0.5 + ((avg_duration or 0) / 600.0) * 0.5, 1.0)
        email_response_rate = (emails_clicked or 0) / max(emails_sent or 1, 1)
        communication_response = min(email_response_rate * 2.0, 1.0)
        recency_val = 0.0
        if days_since_last_engagement is not None:
            recency_val = math.exp(-days_since_last_engagement / RECENCY_HALF_LIFE_DAYS)

        behavior_score = round(
            engagement * 0.25 + purchase_activity * 0.25 + session_depth_val * 0.15
            + communication_response * 0.15 + recency_val * 0.20,
            4,
        )

        return {
            "behavior_score": behavior_score,
            "sub_scores": {
                "engagement": round(engagement, 4),
                "purchase_activity": round(purchase_activity, 4),
                "session_depth": round(session_depth_val, 4),
                "communication_response": round(communication_response, 4),
                "recency": round(recency_val, 4),
            },
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
            "days_since_last_engagement": days_since_last_engagement,
            "lifecycle_stage": self._determine_lifecycle_stage(
                customer,
                purchases_30d or 0,
                sessions_count or 0,
                days_since_last_engagement,
            ),
        }

    def _determine_lifecycle_stage(
        self,
        customer: Customer | None,
        purchases_30d: int,
        sessions_30d: int,
        days_since_last_engagement: int | None,
    ) -> str:
        if not customer:
            return "inactive"

        if days_since_last_engagement is not None and days_since_last_engagement > 180:
            return "dormant"
        if days_since_last_engagement is not None and days_since_last_engagement > 90:
            return "at_risk"
        if days_since_last_engagement is not None and days_since_last_engagement > 30:
            return "inactive"
        if purchases_30d >= 3:
            return "loyal"
        if purchases_30d >= 1:
            return "active"
        if sessions_30d > 0:
            return "engaged"
        return "inactive"

    async def _compute_interest_graph(self, customer_id: uuid.UUID, organization_id: uuid.UUID) -> dict[str, Any]:
        now = datetime.now(timezone.utc)

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

        nodes = []
        for i in interests:
            decay = 1.0
            if i.last_interaction_at:
                days_since = (now - i.last_interaction_at).days
                decay = math.exp(-days_since / INTEREST_DECAY_DAYS)

            new_weight = (i.affinity_score or 0.5) * decay
            if i.interaction_count and i.interaction_count > 0:
                new_weight += (i.interaction_count * 0.01)

            new_weight = min(new_weight, 1.0)

            nodes.append({
                "category": i.category,
                "subcategory": i.subcategory,
                "interest_level": round(new_weight, 4),
                "affinity_score": round(new_weight, 4),
                "interaction_count": i.interaction_count,
                "decayed_score": round(i.affinity_score * decay if i.affinity_score else 0.0, 4),
            })

        nodes.sort(key=lambda n: n["affinity_score"], reverse=True)

        dominant = nodes[0]["category"] if nodes else None
        total_interactions = sum(i.interaction_count or 0 for i in interests)
        unique_categories = len(set(i.category for i in interests))
        diversity = min(unique_categories / 10.0, 1.0) if interests else 0.0

        return {
            "nodes": nodes,
            "dominant_category": dominant,
            "interest_diversity": round(diversity, 4),
            "total_interactions": total_interactions,
        }

    async def _compute_memory_profile(self, customer_id: uuid.UUID, organization_id: uuid.UUID) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        year_ago = now - timedelta(days=365)

        campaign_events = await self._get_campaign_events(customer_id, organization_id, year_ago)
        purchase_events = await self._get_purchase_events_with_category(customer_id, organization_id, year_ago)
        channel_events = await self._get_channel_event_counts(customer_id, organization_id, year_ago)

        discount_purchases = await self._count_event_type_with_prop(
            customer_id, organization_id, "purchase", "discount_applied", year_ago
        )
        total_purchases = await self._count_event_type(customer_id, organization_id, "purchase", year_ago)
        discount_sensitivity = round(
            discount_purchases / max(total_purchases, 1), 4
        ) if total_purchases > 0 else 0.0

        monthly_engagement = await self._compute_monthly_engagement(customer_id, organization_id, year_ago)
        seasonality = await self._compute_seasonality_patterns(customer_id, organization_id, year_ago)

        return {
            "campaign_responses": campaign_events,
            "purchase_categories": purchase_events,
            "channel_history": channel_events,
            "discount_sensitivity": discount_sensitivity,
            "historical_engagement": monthly_engagement,
            "seasonality_patterns": seasonality,
        }

    async def _get_weighted_events(self, customer_id: uuid.UUID, organization_id: uuid.UUID, days: int) -> list[dict[str, Any]]:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        stmt = (
            select(CustomerEvent.event_type, CustomerEvent.event_timestamp)
            .where(
                CustomerEvent.customer_id == customer_id,
                CustomerEvent.organization_id == organization_id,
                CustomerEvent.event_timestamp >= since,
            )
            .order_by(CustomerEvent.event_timestamp.asc())
        )
        result = await self.session.execute(stmt)
        rows = result.all()

        weighted = []
        now = datetime.now(timezone.utc)
        for event_type, event_ts in rows:
            base_weight = EVENT_WEIGHTS.get(event_type, 0.5)
            days_old = max(0, (now - event_ts).days)
            decayed_weight = base_weight * math.exp(-days_old / RECENCY_HALF_LIFE_DAYS)
            weighted.append({"event_type": event_type, "weight": decayed_weight})
        return weighted

    async def _get_campaign_events(self, customer_id: uuid.UUID, organization_id: uuid.UUID, since: datetime) -> list[dict[str, Any]]:
        stmt = (
            select(CustomerEvent.event_type, CustomerEvent.channel, CustomerEvent.event_timestamp, CustomerEvent.campaign_id)
            .where(
                CustomerEvent.customer_id == customer_id,
                CustomerEvent.organization_id == organization_id,
                CustomerEvent.event_timestamp >= since,
                CustomerEvent.campaign_id.is_not(None),
            )
            .order_by(CustomerEvent.event_timestamp.desc())
            .limit(100)
        )
        result = await self.session.execute(stmt)
        return [
            {
                "event_type": row.event_type,
                "channel": row.channel,
                "timestamp": row.event_timestamp.isoformat(),
                "campaign_id": str(row.campaign_id) if row.campaign_id else None,
            }
            for row in result.all()
        ]

    async def _get_purchase_events_with_category(self, customer_id: uuid.UUID, organization_id: uuid.UUID, since: datetime) -> list[dict[str, Any]]:
        stmt = (
            select(CustomerEvent.event_properties, CustomerEvent.value, CustomerEvent.event_timestamp)
            .where(
                CustomerEvent.customer_id == customer_id,
                CustomerEvent.organization_id == organization_id,
                CustomerEvent.event_type == "purchase",
                CustomerEvent.event_timestamp >= since,
            )
            .order_by(CustomerEvent.event_timestamp.desc())
            .limit(100)
        )
        result = await self.session.execute(stmt)
        cats: dict[str, dict[str, Any]] = {}
        for props, value, ts in result.all():
            category = (props or {}).get("category", "uncategorized")
            if category not in cats:
                cats[category] = {"category": category, "count": 0, "total_value": 0.0, "last_purchase_at": None}
            cats[category]["count"] += 1
            cats[category]["total_value"] += value or 0
            if cats[category]["last_purchase_at"] is None or (ts and ts.isoformat() > cats[category]["last_purchase_at"]):
                cats[category]["last_purchase_at"] = ts.isoformat() if ts else None
        return list(cats.values())

    async def _get_channel_event_counts(self, customer_id: uuid.UUID, organization_id: uuid.UUID, since: datetime) -> list[dict[str, Any]]:
        stmt = (
            select(CustomerEvent.channel, func.count(), func.max(CustomerEvent.event_timestamp))
            .where(
                CustomerEvent.customer_id == customer_id,
                CustomerEvent.organization_id == organization_id,
                CustomerEvent.event_timestamp >= since,
                CustomerEvent.channel.is_not(None),
            )
            .group_by(CustomerEvent.channel)
        )
        result = await self.session.execute(stmt)
        return [
            {
                "channel": row.channel,
                "count": row[1],
                "last_interaction_at": row[2].isoformat() if row[2] else None,
            }
            for row in result.all()
        ]

    async def _count_event_type_with_prop(self, customer_id: uuid.UUID, organization_id: uuid.UUID, event_type: str, prop_key: str, since: datetime) -> int:
        from sqlalchemy import Boolean
        stmt = (
            select(func.count())
            .select_from(CustomerEvent)
            .where(
                CustomerEvent.customer_id == customer_id,
                CustomerEvent.organization_id == organization_id,
                CustomerEvent.event_type == event_type,
                CustomerEvent.event_timestamp >= since,
                CustomerEvent.event_properties[prop_key].astext.cast(Boolean).is_(True),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def _compute_monthly_engagement(self, customer_id: uuid.UUID, organization_id: uuid.UUID, since: datetime) -> dict[str, Any]:
        stmt = (
            select(
                func.date_trunc("month", CustomerEvent.event_timestamp).label("month"),
                func.count().label("event_count"),
            )
            .where(
                CustomerEvent.customer_id == customer_id,
                CustomerEvent.organization_id == organization_id,
                CustomerEvent.event_timestamp >= since,
            )
            .group_by(text("month"))
            .order_by(text("month"))
        )
        result = await self.session.execute(stmt)
        months = {}
        for row in result.all():
            month_str = row.month.strftime("%Y-%m") if row.month else "unknown"
            months[month_str] = row.event_count
        return months

    async def _compute_seasonality_patterns(self, customer_id: uuid.UUID, organization_id: uuid.UUID, since: datetime) -> list[dict[str, Any]]:
        stmt = (
            select(
                func.extract("month", CustomerEvent.event_timestamp).label("month"),
                func.count().label("event_count"),
            )
            .where(
                CustomerEvent.customer_id == customer_id,
                CustomerEvent.organization_id == organization_id,
                CustomerEvent.event_timestamp >= since,
            )
            .group_by(text("month"))
            .order_by(text("month"))
        )
        result = await self.session.execute(stmt)
        month_names = [
            "Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
        ]
        total = 0
        patterns: dict[int, int] = {}
        for row in result.all():
            m = int(row.month)
            patterns[m] = row.event_count
            total += row.event_count
        return [
            {
                "month": month_names[m - 1],
                "count": patterns.get(m, 0),
                "share": round(patterns.get(m, 0) / max(total, 1), 4),
            }
            for m in range(1, 13)
            if patterns.get(m, 0) > 0
        ]

    def _compute_data_completeness(self, behavior: dict, interests: dict, memory: dict, customer: Customer | None) -> float:
        checks = 0
        passed = 0

        if behavior:
            checks += 1
            if behavior.get("behavior_score") is not None:
                passed += 1

        if interests:
            checks += 1
            if interests.get("nodes"):
                passed += 1

        if memory:
            checks += 1
            if any(memory.get(k) for k in ("campaign_responses", "purchase_categories", "channel_history")):
                passed += 1

        if customer:
            if customer.email:
                checks += 1
                passed += 1
            else:
                checks += 1
            if customer.first_name:
                checks += 1
                passed += 1
            else:
                checks += 1

        return passed / max(checks, 1)

    def _compute_prediction_agreement(self, intent_forecast: dict, risk_indicators: dict) -> float:
        agreement = 1.0
        purchase_intent = intent_forecast.get("purchase_intent_7d", 0.0)
        churn_prob = risk_indicators.get("churn_probability", 0.0)

        if purchase_intent > 0.5 and churn_prob > 0.5:
            agreement -= 0.3

        risk_level = risk_indicators.get("churn_risk_level", "low")
        if risk_level == "high" and churn_prob < 0.3:
            agreement -= 0.2
        elif risk_level == "low" and churn_prob > 0.7:
            agreement -= 0.2

        return max(0.0, agreement)

    def _compute_confidence_score(self, data_completeness: float, recency_score: float, prediction_agreement: float) -> float:
        return round(
            data_completeness * 0.5 + recency_score * 0.3 + prediction_agreement * 0.2,
            4,
        )

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
        memory = twin.memory_profile or {}
        affinity = twin.channel_affinity or {}
        risk = twin.risk_indicators or {}
        intent = twin.intent_forecast or {}
        twin_output = twin.twin_metadata.get("twin_output", {}) if twin.twin_metadata else {}

        return CustomerTwinResponse(
            customer_id=twin.customer_id,
            organization_id=twin.organization_id,
            status="built" if twin.status == "active" else twin.status,
            version=twin.version,
            behavior_profile=BehaviorProfileResponse(
                behavior_score=behavior.get("behavior_score"),
                sub_scores=BehaviorSubScores(**behavior.get("sub_scores", {})),
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
            memory_profile=MemoryProfileResponse(
                campaign_responses=memory.get("campaign_responses", []),
                purchase_categories=memory.get("purchase_categories", []),
                channel_history=memory.get("channel_history", []),
                discount_sensitivity=memory.get("discount_sensitivity"),
                historical_engagement=memory.get("historical_engagement", {}),
                seasonality_patterns=memory.get("seasonality_patterns", []),
            ) if memory else None,
            channel_affinity=ChannelAffinityResponse(
                email=affinity.get("email", {}).get("affinity", 0.0) if isinstance(affinity.get("email"), dict) else affinity.get("email", 0.0),
                sms=affinity.get("sms", {}).get("affinity", 0.0) if isinstance(affinity.get("sms"), dict) else affinity.get("sms", 0.0),
                push=affinity.get("push", {}).get("affinity", 0.0) if isinstance(affinity.get("push"), dict) else affinity.get("push", 0.0),
                in_app=affinity.get("in_app", {}).get("affinity", 0.0) if isinstance(affinity.get("in_app"), dict) else affinity.get("in_app", 0.0),
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
            twin_output=TwinOutputResponse(
                sentiment=twin_output.get("sentiment"),
                purchase_intent=twin_output.get("purchase_intent"),
                churn_probability=twin_output.get("churn_probability"),
                lifetime_value=twin_output.get("lifetime_value"),
                next_best_action=twin_output.get("next_best_action"),
            ) if twin_output else None,
            communication_preferences=twin.communication_preferences or {},
            confidence_score=twin.confidence_score,
            staleness_score=twin.staleness_score,
            built_at=twin.built_at,
        )
