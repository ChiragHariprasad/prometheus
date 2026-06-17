import uuid
import math
import random
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.core.logging import logger
from app.core.redis import RedisClient
from app.models.customer import Customer, CustomerProfile
from app.models.event import Event as CustomerEvent
from app.models.twin import CustomerTwin, Prediction as CustomerPrediction
from app.repositories.customer_repository import CustomerRepository


class PredictionService:
    def __init__(self, session: AsyncSession, redis: RedisClient | None = None):
        self.session = session
        self.redis = redis
        self.repo = CustomerRepository(session)

    async def get_churn_prediction(self, organization_id: uuid.UUID, customer_id: uuid.UUID) -> dict:
        customer, twin = await self.repo.get_with_twin(customer_id, organization_id)
        if not customer:
            raise NotFoundException("Customer", str(customer_id))

        existing = await self._get_active_prediction(customer_id, organization_id, "churn")
        if existing and existing.valid_until and existing.valid_until > datetime.now(timezone.utc):
            return self._prediction_to_dict(existing)

        churn_prob = self._compute_churn_probability(twin, customer)
        risk_level = self._risk_level(churn_prob)

        features = await self._collect_features(customer_id, organization_id)
        explanation = self._explain_churn(churn_prob, twin, features)

        prediction = CustomerPrediction(
            customer_id=customer_id,
            organization_id=organization_id,
            prediction_type="churn",
            prediction_value=churn_prob,
            prediction_probability=churn_prob,
            prediction_label=risk_level,
            prediction_explanation=explanation,
            feature_importance=features.get("importance", {}),
            confidence_score=self._compute_confidence(twin),
            input_features=features.get("raw", {}),
            valid_until=datetime.now(timezone.utc) + timedelta(days=7),
            is_active=True,
        )
        self.session.add(prediction)
        await self.session.flush()
        await self.session.refresh(prediction)

        return self._prediction_to_dict(prediction)

    async def get_intent_prediction(self, organization_id: uuid.UUID, customer_id: uuid.UUID) -> dict:
        customer, twin = await self.repo.get_with_twin(customer_id, organization_id)
        if not customer:
            raise NotFoundException("Customer", str(customer_id))

        existing = await self._get_active_prediction(customer_id, organization_id, "intent")
        if existing and existing.valid_until and existing.valid_until > datetime.now(timezone.utc):
            return self._prediction_to_dict(existing)

        purchase_intent = self._compute_purchase_intent(twin, customer)
        engagement_intent = self._compute_engagement_intent(twin, customer)

        avg_intent = (purchase_intent + engagement_intent) / 2.0

        if avg_intent > 0.7:
            label = "high_intent"
        elif avg_intent > 0.4:
            label = "medium_intent"
        else:
            label = "low_intent"

        features = await self._collect_features(customer_id, organization_id)

        prediction = CustomerPrediction(
            customer_id=customer_id,
            organization_id=organization_id,
            prediction_type="intent",
            prediction_value=avg_intent,
            prediction_probability=avg_intent,
            prediction_label=label,
            prediction_explanation={
                "purchase_intent": round(purchase_intent, 4),
                "engagement_intent": round(engagement_intent, 4),
                "driving_factors": features.get("importance", {}),
            },
            feature_importance=features.get("importance", {}),
            confidence_score=self._compute_confidence(twin),
            input_features=features.get("raw", {}),
            valid_until=datetime.now(timezone.utc) + timedelta(days=3),
            is_active=True,
        )
        self.session.add(prediction)
        await self.session.flush()
        await self.session.refresh(prediction)

        return self._prediction_to_dict(prediction)

    async def get_ltv_prediction(self, organization_id: uuid.UUID, customer_id: uuid.UUID) -> dict:
        customer, twin = await self.repo.get_with_twin(customer_id, organization_id)
        if not customer:
            raise NotFoundException("Customer", str(customer_id))

        existing = await self._get_active_prediction(customer_id, organization_id, "ltv")
        if existing and existing.valid_until and existing.valid_until > datetime.now(timezone.utc):
            return self._prediction_to_dict(existing)

        ltv_90d = self._compute_ltv_90d(twin, customer)
        confidence = self._compute_confidence(twin)

        features = await self._collect_features(customer_id, organization_id)

        prediction = CustomerPrediction(
            customer_id=customer_id,
            organization_id=organization_id,
            prediction_type="ltv",
            prediction_value=ltv_90d,
            prediction_probability=confidence,
            prediction_label="high_value" if ltv_90d > 1000 else "medium_value" if ltv_90d > 100 else "low_value",
            prediction_explanation={
                "predicted_ltv_90d": round(ltv_90d, 2),
                "current_ltv": twin.lifetime_value if twin else 0,
                "growth_potential": round(max(ltv_90d - (twin.lifetime_value or 0) / 4, 0), 2),
                "key_drivers": features.get("importance", {}),
            },
            feature_importance=features.get("importance", {}),
            confidence_score=confidence,
            input_features=features.get("raw", {}),
            valid_until=datetime.now(timezone.utc) + timedelta(days=30),
            is_active=True,
        )
        self.session.add(prediction)
        await self.session.flush()
        await self.session.refresh(prediction)

        return self._prediction_to_dict(prediction)

    async def run_batch_predictions(self, organization_id: uuid.UUID, prediction_type: str) -> int:
        stmt = select(Customer).where(
            Customer.organization_id == organization_id,
            Customer.is_active.is_(True),
        )
        result = await self.session.execute(stmt)
        customers = list(result.scalars().all())

        count = 0
        for customer in customers:
            try:
                if prediction_type == "churn":
                    await self.get_churn_prediction(organization_id, customer.id)
                elif prediction_type == "intent":
                    await self.get_intent_prediction(organization_id, customer.id)
                elif prediction_type == "ltv":
                    await self.get_ltv_prediction(organization_id, customer.id)
                count += 1
            except Exception as e:
                logger.error("Batch prediction failed",
                             extra={"customer_id": str(customer.id), "type": prediction_type, "error": str(e)})

        logger.info("Batch predictions completed",
                    extra={"org_id": str(organization_id), "type": prediction_type, "count": count})
        return count

    async def get_all_predictions(self, organization_id: uuid.UUID, customer_id: uuid.UUID) -> list[dict]:
        customer = await self.repo.get(customer_id, organization_id)
        if not customer:
            raise NotFoundException("Customer", str(customer_id))

        stmt = (
            select(CustomerPrediction)
            .where(
                CustomerPrediction.customer_id == customer_id,
                CustomerPrediction.organization_id == organization_id,
                CustomerPrediction.is_active.is_(True),
            )
            .order_by(CustomerPrediction.created_at.desc())
        )
        result = await self.session.execute(stmt)
        predictions = list(result.scalars().all())

        return [self._prediction_to_dict(p) for p in predictions]

    async def _get_active_prediction(self, customer_id: uuid.UUID, organization_id: uuid.UUID, prediction_type: str) -> CustomerPrediction | None:
        stmt = (
            select(CustomerPrediction)
            .where(
                CustomerPrediction.customer_id == customer_id,
                CustomerPrediction.organization_id == organization_id,
                CustomerPrediction.prediction_type == prediction_type,
                CustomerPrediction.is_active.is_(True),
            )
            .order_by(CustomerPrediction.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    def _compute_churn_probability(self, twin: CustomerTwin | None, customer: Customer) -> float:
        if not twin:
            return 0.5

        prob = 0.0
        staleness = twin.staleness_score or 0
        engagement = twin.engagement_score or 0
        loyalty = twin.loyalty_score or 0
        sentiment = twin.sentiment_trend or []

        prob += staleness * 0.3
        prob += (1 - engagement) * 0.25
        prob += (1 - loyalty) * 0.2

        if sentiment:
            recent = sentiment[-min(len(sentiment), 10):]
            avg_sentiment = sum(recent) / len(recent)
            prob += max(0, -avg_sentiment) * 0.15

        if customer.last_seen_at:
            days_since_last = (datetime.now(timezone.utc) - customer.last_seen_at).days
            if days_since_last > 90:
                prob += 0.1
            elif days_since_last > 30:
                prob += 0.05

        return min(max(prob, 0.01), 0.99)

    def _compute_purchase_intent(self, twin: CustomerTwin | None, customer: Customer) -> float:
        if not twin:
            return 0.3
        engagement = twin.engagement_score or 0
        loyalty = twin.loyalty_score or 0
        intent = engagement * 0.4 + loyalty * 0.3 + 0.1
        return min(max(intent, 0.01), 0.99)

    def _compute_engagement_intent(self, twin: CustomerTwin | None, customer: Customer) -> float:
        if not twin:
            return 0.4
        staleness = 1 - (twin.staleness_score or 0)
        engagement = twin.engagement_score or 0
        intent = engagement * 0.5 + staleness * 0.3 + 0.1
        return min(max(intent, 0.01), 0.99)

    def _compute_ltv_90d(self, twin: CustomerTwin | None, customer: Customer) -> float:
        if not twin:
            return 0.0
        current_ltv = twin.lifetime_value or 0
        engagement = twin.engagement_score or 0
        loyalty = twin.loyalty_score or 0

        growth_rate = (engagement + loyalty) / 2.0
        projected = current_ltv + (growth_rate * 500)
        return round(max(projected, 0), 2)

    def _compute_confidence(self, twin: CustomerTwin | None) -> float:
        if not twin:
            return 0.1
        points = 0.0
        if twin.behavior_profile:
            points += 0.2
        if twin.interest_graph:
            points += 0.15
        if twin.sentiment_trend and len(twin.sentiment_trend) > 5:
            points += 0.2
        if twin.engagement_score is not None:
            points += 0.15
        if twin.loyalty_score is not None:
            points += 0.15
        if twin.last_event_at:
            days_since = (datetime.now(timezone.utc) - twin.last_event_at).days
            if days_since < 7:
                points += 0.15
            elif days_since < 30:
                points += 0.1
        return min(points, 1.0)

    def _risk_level(self, prob: float) -> str:
        if prob >= 0.7:
            return "high"
        if prob >= 0.4:
            return "medium"
        return "low"

    def _explain_churn(self, prob: float, twin: CustomerTwin | None, features: dict) -> dict:
        reasons = []
        if twin:
            if (twin.staleness_score or 0) > 0.6:
                reasons.append("Customer has high staleness score")
            if (twin.engagement_score or 0) < 0.3:
                reasons.append("Low engagement levels")
            if (twin.loyalty_score or 0) < 0.3:
                reasons.append("Low loyalty score")
            if twin.sentiment_trend and len(twin.sentiment_trend) > 0:
                avg = sum(twin.sentiment_trend[-10:]) / len(twin.sentiment_trend[-10:])
                if avg < -0.3:
                    reasons.append("Declining sentiment trend")
        return {
            "probability": round(prob, 4),
            "risk_level": self._risk_level(prob),
            "reasons": reasons,
            "top_factors": features.get("importance", {}),
        }

    async def _collect_features(self, customer_id: uuid.UUID, organization_id: uuid.UUID) -> dict:
        now = datetime.now(timezone.utc)
        thirty_days = now - timedelta(days=30)
        ninety_days = now - timedelta(days=90)

        stmt_30d = select(func.count()).select_from(CustomerEvent).where(
            CustomerEvent.customer_id == customer_id,
            CustomerEvent.organization_id == organization_id,
            CustomerEvent.event_timestamp >= thirty_days,
        )
        events_30d = (await self.session.execute(stmt_30d)).scalar() or 0

        stmt_90d = select(func.count()).select_from(CustomerEvent).where(
            CustomerEvent.customer_id == customer_id,
            CustomerEvent.organization_id == organization_id,
            CustomerEvent.event_timestamp >= ninety_days,
        )
        events_90d = (await self.session.execute(stmt_90d)).scalar() or 0

        stmt_purchases = select(func.count(), func.coalesce(func.sum(CustomerEvent.value), 0)).where(
            CustomerEvent.customer_id == customer_id,
            CustomerEvent.organization_id == organization_id,
            CustomerEvent.event_type == "purchase",
            CustomerEvent.event_timestamp >= ninety_days,
        )
        purchases_count, purchases_value = (await self.session.execute(stmt_purchases)).one()

        stmt_types = (
            select(CustomerEvent.event_type, func.count())
            .where(
                CustomerEvent.customer_id == customer_id,
                CustomerEvent.organization_id == organization_id,
                CustomerEvent.event_timestamp >= ninety_days,
            )
            .group_by(CustomerEvent.event_type)
        )
        type_result = await self.session.execute(stmt_types)
        type_dist = {row.event_type: row.count for row in type_result.all()}

        raw = {
            "events_30d": events_30d,
            "events_90d": events_90d,
            "purchases_90d": purchases_count,
            "purchase_value_90d": float(purchases_value or 0),
            "event_type_distribution": type_dist,
        }

        importance = {
            "events_30d": events_30d * 0.01,
            "events_90d": events_90d * 0.005,
            "purchases_90d": purchases_count * 0.05,
            "purchase_value_90d": float(purchases_value or 0) * 0.0001,
        }

        return {"raw": raw, "importance": importance}

    def _prediction_to_dict(self, prediction: CustomerPrediction) -> dict:
        return {
            "id": str(prediction.id),
            "customer_id": str(prediction.customer_id),
            "prediction_type": prediction.prediction_type,
            "prediction_value": prediction.prediction_value,
            "prediction_probability": prediction.prediction_probability,
            "prediction_label": prediction.prediction_label,
            "prediction_explanation": prediction.prediction_explanation,
            "feature_importance": prediction.feature_importance,
            "confidence_score": prediction.confidence_score,
            "model_version": prediction.model_version,
            "model_name": prediction.model_name,
            "valid_until": prediction.valid_until.isoformat() if prediction.valid_until else None,
            "is_active": prediction.is_active,
            "created_at": prediction.created_at.isoformat() if hasattr(prediction, "created_at") and prediction.created_at else None,
        }
