import uuid
import asyncio
from typing import Any
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from qdrant_client.models import PointStruct

from app.core.config import settings
from app.core.logging import logger
from app.core.qdrant import qdrant_client
from app.models.customer import CustomerEmbedding
from app.models.event import Event as CustomerEvent
from app.models.twin import CustomerTwin


_EMBEDDING_MODEL = None
_MODEL_LOCK = asyncio.Lock()


async def _get_sentence_transformer():
    global _EMBEDDING_MODEL
    if _EMBEDDING_MODEL is None:
        async with _MODEL_LOCK:
            if _EMBEDDING_MODEL is None:
                try:
                    from sentence_transformers import SentenceTransformer
                    _EMBEDDING_MODEL = SentenceTransformer(
                        settings.EMBEDDING_MODEL_NAME,
                        device=settings.EMBEDDING_DEVICE,
                    )
                    logger.info("Embedding model loaded",
                                extra={"model": settings.EMBEDDING_MODEL_NAME})
                except Exception as e:
                    logger.error("Failed to load embedding model", extra={"error": str(e)})
                    raise
    return _EMBEDDING_MODEL


def _build_event_text(event: CustomerEvent) -> str:
    props = event.event_properties or {}
    parts = [
        f"event_type: {event.event_type}",
        f"event_name: {event.event_name}",
    ]
    if event.channel:
        parts.append(f"channel: {event.channel}")
    if event.source:
        parts.append(f"source: {event.source}")
    if event.url:
        parts.append(f"url: {event.url}")
    for key in ("category", "product", "brand", "page_title", "search_query"):
        if props.get(key):
            parts.append(f"{key}: {props[key]}")
    return ". ".join(parts)


def _build_twin_text(twin: CustomerTwin) -> str:
    parts = []
    behavior = twin.behavior_profile or {}
    profile = behavior.get("sub_scores", {})
    scores = {k: round(v, 4) for k, v in profile.items()} if isinstance(profile, dict) else {}
    if scores:
        parts.append(f"behavior: {scores}")
    if twin.engagement_score is not None:
        parts.append(f"engagement: {round(twin.engagement_score, 4)}")
    if twin.loyalty_score is not None:
        parts.append(f"loyalty: {round(twin.loyalty_score, 4)}")
    if twin.lifetime_value is not None:
        parts.append(f"ltv: {round(twin.lifetime_value, 2)}")
    if twin.staleness_score is not None:
        parts.append(f"staleness: {round(twin.staleness_score, 4)}")
    interests = twin.interest_graph or {}
    nodes = interests.get("nodes", [])
    if nodes:
        top = sorted(nodes, key=lambda n: n.get("affinity_score", 0), reverse=True)[:5]
        parts.append(f"top_interests: {[n['category'] for n in top]}")
    memory = twin.memory_profile or {}
    purchase_cats = memory.get("purchase_categories", [])
    if purchase_cats:
        parts.append(f"purchase_categories: {[c['category'] for c in purchase_cats]}")
    risk = twin.risk_indicators or {}
    if risk.get("churn_probability") is not None:
        parts.append(f"churn_risk: {round(risk['churn_probability'], 4)}")
    stage = behavior.get("lifecycle_stage")
    if stage:
        parts.append(f"lifecycle: {stage}")
    return ". ".join(parts)


def _build_interest_text(twin: CustomerTwin) -> list[str]:
    interests = twin.interest_graph or {}
    nodes = interests.get("nodes", [])
    if not nodes:
        return []
    return [
        f"category: {n.get('category', 'unknown')} | subcategory: {n.get('subcategory', '')} | affinity: {n.get('affinity_score', 0)} | interactions: {n.get('interaction_count', 0)}"
        for n in nodes
        if n.get("affinity_score", 0) > 0.1
    ]


class EmbeddingService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def embed_event(self, event: CustomerEvent) -> bool:
        try:
            text = _build_event_text(event)
            if not text.strip():
                return False
            model = await _get_sentence_transformer()
            vector = await asyncio.to_thread(
                model.encode, text,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            point = PointStruct(
                id=str(event.id),
                vector=vector.tolist(),
                payload={
                    "organization_id": str(event.organization_id),
                    "customer_id": str(event.customer_id) if event.customer_id else None,
                    "event_type": event.event_type,
                    "event_name": event.event_name,
                    "channel": event.channel,
                    "source": event.source,
                    "event_timestamp": event.event_timestamp.isoformat() if event.event_timestamp else None,
                    "text": text[:1000],
                },
            )
            await qdrant_client.upsert("semantic_memory", [point])
            return True
        except Exception as e:
            logger.warning("Event embedding failed", extra={
                "event_id": str(event.id), "error": str(e),
            })
            return False

    async def embed_twin(self, twin: CustomerTwin) -> bool:
        try:
            text = _build_twin_text(twin)
            if not text.strip():
                return False
            model = await _get_sentence_transformer()
            vector = await asyncio.to_thread(
                model.encode, text,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            point_id = str(twin.customer_id)
            point = PointStruct(
                id=point_id,
                vector=vector.tolist(),
                payload={
                    "organization_id": str(twin.organization_id),
                    "customer_id": str(twin.customer_id),
                    "engagement_score": twin.engagement_score,
                    "loyalty_score": twin.loyalty_score,
                    "lifetime_value": twin.lifetime_value,
                    "lifecycle_stage": (twin.behavior_profile or {}).get("lifecycle_stage"),
                    "churn_probability": (twin.risk_indicators or {}).get("churn_probability"),
                    "version": twin.version,
                    "text": text[:1000],
                },
            )
            await qdrant_client.upsert("customer_embeddings", [point])

            embedding = CustomerEmbedding(
                customer_id=twin.customer_id,
                organization_id=twin.organization_id,
                embedding_model=settings.EMBEDDING_MODEL_NAME,
                embedding_dimensions=len(vector),
                embedding_vector={"vector": vector.tolist()},
                version=twin.version,
            )
            self.session.add(embedding)
            await self.session.flush()

            return True
        except Exception as e:
            logger.warning("Twin embedding failed", extra={
                "customer_id": str(twin.customer_id), "error": str(e),
            })
            return False

    async def embed_interests(self, twin: CustomerTwin) -> bool:
        try:
            texts = _build_interest_text(twin)
            if not texts:
                return False
            model = await _get_sentence_transformer()
            vectors = await asyncio.to_thread(
                model.encode, texts,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            points = []
            interests = twin.interest_graph or {}
            nodes = interests.get("nodes", [])
            for node, vector in zip(nodes, vectors):
                cat = node.get("category", "unknown")
                point_id = f"{twin.customer_id}_{cat}"
                points.append(PointStruct(
                    id=point_id,
                    vector=vector.tolist(),
                    payload={
                        "organization_id": str(twin.organization_id),
                        "customer_id": str(twin.customer_id),
                        "category": cat,
                        "subcategory": node.get("subcategory"),
                        "affinity_score": node.get("affinity_score"),
                    },
                ))
            if points:
                await qdrant_client.upsert("customer_interests", points)
            return True
        except Exception as e:
            logger.warning("Interest embedding failed", extra={
                "customer_id": str(twin.customer_id), "error": str(e),
            })
            return False
