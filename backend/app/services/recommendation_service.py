import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue, SearchParams

from app.core.config import settings
from app.core.exceptions import NotFoundException, ValidationException
from app.core.logging import logger
from app.core.redis import RedisClient
from app.models.twin import CustomerTwin
from app.models.recommendation import Recommendation
from app.models.campaign import Campaign
from app.repositories.customer_repository import CustomerRepository


class RecommendationService:
    def __init__(
        self,
        session: AsyncSession,
        qdrant: AsyncQdrantClient | None = None,
        redis: RedisClient | None = None,
    ):
        self.session = session
        self.qdrant = qdrant
        self.redis = redis
        self.repo = CustomerRepository(session)

    async def get_personalized(self, organization_id: uuid.UUID, customer_id: uuid.UUID, limit: int = 20) -> list[dict]:
        cache_key = f"recommendations:{organization_id}:{customer_id}:{limit}"
        if self.redis:
            cached = await self.redis.get(cache_key)
            if cached:
                return cached

        customer = await self.repo.get(customer_id, organization_id)
        if not customer:
            raise NotFoundException("Customer", str(customer_id))

        twin_stmt = select(CustomerTwin).where(
            CustomerTwin.customer_id == customer_id,
            CustomerTwin.organization_id == organization_id,
        )
        twin_result = await self.session.execute(twin_stmt)
        twin = twin_result.scalar_one_or_none()

        recommendations: list[dict] = []
        recommendations.extend(await self._get_collaborative_recommendations(organization_id, customer_id, twin, limit // 2))
        recommendations.extend(await self._get_content_based_recommendations(organization_id, customer_id, twin, limit // 2))

        recommendations = self._rank_and_dedup(recommendations, twin, limit)

        if self.redis:
            await self.redis.set(cache_key, recommendations, ttl=settings.CACHE_TTL_RECOMMENDATION)

        return recommendations

    async def refresh_recommendations(self, organization_id: uuid.UUID, customer_id: uuid.UUID) -> list[dict]:
        cache_key = f"recommendations:{organization_id}:{customer_id}:*"
        if self.redis:
            keys = await self.redis.keys(cache_key)
            for key in keys:
                await self.redis.delete(key)

        return await self.get_personalized(organization_id, customer_id, limit=20)

    async def record_feedback(self, recommendation_id: uuid.UUID, feedback_type: str, organization_id: uuid.UUID | None = None) -> None:
        if feedback_type not in ("click", "dismiss", "convert", "hide"):
            raise ValidationException(f"Invalid feedback type: {feedback_type}")

        stmt = select(Recommendation).where(Recommendation.id == recommendation_id)
        if organization_id:
            stmt = stmt.where(Recommendation.organization_id == organization_id)
        result = await self.session.execute(stmt)
        rec = result.scalar_one_or_none()
        if not rec:
            raise NotFoundException("Recommendation", str(recommendation_id))

        metadata = rec.metadata_ or {}
        feedback = metadata.get("feedback", [])
        feedback.append({
            "type": feedback_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        metadata["feedback"] = feedback
        rec.metadata_ = metadata

        if feedback_type == "convert":
            rec.is_applied = True
            rec.applied_at = datetime.now(timezone.utc)

        await self.session.flush()

        logger.info("Recommendation feedback recorded",
                    extra={"rec_id": str(recommendation_id), "feedback": feedback_type})

    async def _get_collaborative_recommendations(
        self,
        organization_id: uuid.UUID,
        customer_id: uuid.UUID,
        twin: CustomerTwin | None,
        limit: int,
    ) -> list[dict]:
        if not self.qdrant or not twin:
            return []

        if not twin.embedding_id:
            return []

        try:
            search_result = await self.qdrant.search(
                collection_name="customer_embeddings",
                query_filter=Filter(
                    must=[
                        FieldCondition(key="organization_id", match=MatchValue(str(organization_id))),
                    ]
                ),
                search_params=SearchParams(hnsw_ef=128, exact=False),
                with_payload=True,
                limit=limit + 5,
                score_threshold=0.3,
            )
        except Exception as e:
            logger.warning("Qdrant collaborative search failed", extra={"error": str(e)})
            return []

        similar_customer_ids = []
        for scored_point in search_result:
            payload = scored_point.payload or {}
            similar_id = payload.get("customer_id")
            if similar_id and uuid.UUID(similar_id) != customer_id:
                similar_customer_ids.append(uuid.UUID(similar_id))

        if not similar_customer_ids:
            return []

        similar_recs_stmt = (
            select(Recommendation)
            .where(
                Recommendation.customer_id.in_(similar_customer_ids),
                Recommendation.organization_id == organization_id,
                Recommendation.is_actionable.is_(True),
                or_(
                    Recommendation.is_applied.is_(False),
                    Recommendation.applied_at >= datetime.now(timezone.utc) - timedelta(days=30),
                ),
            )
            .order_by(Recommendation.score.desc())
            .limit(limit * 2)
        )
        similar_recs_result = await self.session.execute(similar_recs_stmt)
        similar_recs = list(similar_recs_result.scalars().all())

        return [
            self._rec_to_dict(r, source="collaborative")
            for r in similar_recs
        ]

    async def _get_content_based_recommendations(
        self,
        organization_id: uuid.UUID,
        customer_id: uuid.UUID,
        twin: CustomerTwin | None,
        limit: int,
    ) -> list[dict]:
        recommendations = []

        if not twin:
            return await self._get_default_recommendations(organization_id, limit)

        behavior = twin.behavior_profile or {}
        interests = twin.interest_graph or {}
        affinity = twin.channel_affinity or {}

        if behavior.get("lifecycle_stage") == "engaged" and behavior.get("behavior_score", 1.0) < 0.3:
            recommendations.append({
                "type": "onboarding",
                "title": "Complete your profile",
                "description": "Fill in your preferences to get personalized recommendations",
                "score": 0.9,
                "category": "onboarding",
            })

        if (twin.engagement_score or 0) < 0.3:
            recommendations.append({
                "type": "re_engagement",
                "title": "Come back and explore",
                "description": "Check out what's new - we've missed you!",
                "score": 0.8,
                "category": "engagement",
            })

        if interests.get("dominant_category"):
            rec = await self._get_category_recommendation(organization_id, interests["dominant_category"])
            if rec:
                recommendations.append(rec)

        preferred_channels = [ch for ch, data in affinity.items() if isinstance(data, dict) and data.get("affinity", 0) > 0.5]
        if preferred_channels:
            recommendations.append({
                "type": "channel_preference",
                "title": f"We recommend {preferred_channels[0].replace('_', ' ').title()} communications",
                "description": "Based on your engagement patterns",
                "score": 0.7,
                "category": "preferences",
            })

        existing_recs_stmt = (
            select(Recommendation)
            .where(
                Recommendation.customer_id == customer_id,
                Recommendation.organization_id == organization_id,
                Recommendation.is_actionable.is_(True),
                Recommendation.source == "content_based",
            )
            .order_by(Recommendation.score.desc())
            .limit(limit)
        )
        existing_result = await self.session.execute(existing_recs_stmt)
        existing = list(existing_result.scalars().all())

        recommendations.extend(self._rec_to_dict(r) for r in existing)

        if len(recommendations) < limit:
            defaults = await self._get_default_recommendations(organization_id, limit - len(recommendations))
            recommendations.extend(defaults)

        return recommendations

    async def _get_category_recommendation(self, organization_id: uuid.UUID, category: str) -> dict | None:
        campaigns_stmt = (
            select(Campaign)
            .where(
                Campaign.organization_id == organization_id,
                Campaign.status == "active",
                Campaign.type.ilike(f"%{category}%"),
            )
            .limit(1)
        )
        result = await self.session.execute(campaigns_stmt)
        campaign = result.scalar_one_or_none()

        if campaign:
            return {
                "type": "campaign",
                "title": f"Check out our {category} offers",
                "description": campaign.description or f"Special {category} campaign for you",
                "score": 0.75,
                "category": category,
                "metadata": {"campaign_id": str(campaign.id)},
            }
        return None

    async def _get_default_recommendations(self, organization_id: uuid.UUID, limit: int) -> list[dict]:
        stmt = (
            select(Campaign)
            .where(
                Campaign.organization_id == organization_id,
                Campaign.status == "active",
            )
            .order_by(Campaign.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        campaigns = list(result.scalars().all())

        return [
            {
                "type": "campaign",
                "title": c.name,
                "description": c.description or "Check out this campaign",
                "score": 0.5,
                "category": c.type,
                "metadata": {"campaign_id": str(c.id)},
            }
            for c in campaigns
        ]

    def _rank_and_dedup(self, recommendations: list[dict], twin: CustomerTwin | None, limit: int) -> list[dict]:
        seen_titles: set[str] = set()
        ranked = []

        for rec in recommendations:
            title = rec.get("title", "")
            if title in seen_titles:
                continue
            seen_titles.add(title)

            score = rec.get("score", 0.5)
            if twin and twin.engagement_score:
                score *= (0.5 + 0.5 * twin.engagement_score)
            rec["score"] = round(score, 4)
            ranked.append(rec)

        ranked.sort(key=lambda x: x.get("score", 0), reverse=True)
        return ranked[:limit]

    def _rec_to_dict(self, rec: Recommendation | dict, source: str | None = None) -> dict:
        if isinstance(rec, dict):
            result = dict(rec)
            if source:
                result["source"] = source
            return result

        return {
            "id": str(rec.id),
            "customer_id": str(rec.customer_id),
            "type": rec.type,
            "title": rec.title,
            "description": rec.description,
            "score": rec.score,
            "rank": rec.rank,
            "category": rec.category,
            "metadata": rec.metadata_ or {},
            "is_actionable": rec.is_actionable,
            "is_applied": rec.is_applied,
            "source": source or rec.source or "system",
            "expires_at": rec.expires_at.isoformat() if rec.expires_at else None,
        }
