import uuid
import asyncio
from datetime import datetime, timezone

from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.core.logging import logger
from app.models.customer import (
    Customer, CustomerSegment, CustomerSegmentMapping,
)
from app.models.twin import CustomerTwin
from app.models.event import Event
from app.repositories.segment_repository import SegmentRepository


class SegmentService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = SegmentRepository(session)

    async def create_segment(
        self, org_id: uuid.UUID, name: str, description: str | None = None,
        rules: dict | None = None, is_dynamic: bool = False,
        created_by: uuid.UUID | None = None,
    ) -> CustomerSegment:
        segment = CustomerSegment(
            organization_id=org_id,
            name=name,
            description=description,
            rules=rules,
            is_dynamic=is_dynamic,
            created_by=created_by,
        )
        self.session.add(segment)
        await self.session.flush()
        if rules:
            await self._apply_rules(segment, org_id)
        await self.session.refresh(segment)
        return segment

    async def get_segment(self, segment_id: uuid.UUID, org_id: uuid.UUID) -> CustomerSegment:
        segment = await self.repo.get(segment_id, org_id)
        if not segment:
            raise NotFoundException("Segment", str(segment_id))
        return segment

    async def update_segment(
        self, segment_id: uuid.UUID, org_id: uuid.UUID, **kwargs,
    ) -> CustomerSegment:
        segment = await self.repo.get(segment_id, org_id)
        if not segment:
            raise NotFoundException("Segment", str(segment_id))
        for field, value in kwargs.items():
            if hasattr(segment, field):
                setattr(segment, field, value)
        await self.session.flush()
        if kwargs.get("rules") is not None:
            await self.recalculate_membership(segment.id, org_id)
        await self.session.refresh(segment)
        return segment

    async def delete_segment(self, segment_id: uuid.UUID, org_id: uuid.UUID) -> None:
        segment = await self.repo.get(segment_id, org_id)
        if not segment:
            raise NotFoundException("Segment", str(segment_id))
        await self.session.delete(segment)
        await self.session.flush()

    async def list_segments(
        self, org_id: uuid.UUID, page: int = 1, page_size: int = 20,
        search: str | None = None,
    ) -> tuple[list[CustomerSegment], int]:
        filters = {}
        if search:
            filters["name"] = {"op": "ilike", "value": f"%{search}%"}
        return await self.repo.get_multi(
            skip=(page - 1) * page_size, limit=page_size,
            filters=filters, organization_id=org_id,
        )
        stmt = stmt.order_by(CustomerSegment.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(stmt)
        segments = result.scalars().all()
        return list(segments), total

    async def get_segment_customers(
        self, segment_id: uuid.UUID, org_id: uuid.UUID,
        page: int = 1, page_size: int = 20,
    ) -> tuple[list[Customer], int]:
        stmt = (
            select(Customer)
            .join(CustomerSegmentMapping, CustomerSegmentMapping.customer_id == Customer.id)
            .where(
                CustomerSegmentMapping.segment_id == segment_id,
                Customer.organization_id == org_id,
            )
        )
        count_stmt = (
            select(func.count())
            .select_from(CustomerSegmentMapping)
            .where(
                CustomerSegmentMapping.segment_id == segment_id,
                CustomerSegmentMapping.organization_id == org_id,
            )
        )
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar() or 0
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(stmt)
        customers = result.scalars().all()
        return list(customers), total

    async def recalculate_membership(self, segment_id: uuid.UUID, org_id: uuid.UUID) -> int:
        segment = await self.get_segment(segment_id, org_id)
        await self.session.execute(
            delete(CustomerSegmentMapping).where(
                CustomerSegmentMapping.segment_id == segment_id,
                CustomerSegmentMapping.organization_id == org_id,
            )
        )
        if not segment.rules:
            segment.customer_count = 0
            await self.session.flush()
            return 0
        await self._apply_rules(segment, org_id)
        count_stmt = select(func.count()).select_from(CustomerSegmentMapping).where(
            CustomerSegmentMapping.segment_id == segment_id,
            CustomerSegmentMapping.organization_id == org_id,
        )
        count_result = await self.session.execute(count_stmt)
        count = count_result.scalar() or 0
        segment.customer_count = count
        segment.last_refreshed_at = datetime.now(timezone.utc)
        await self.session.flush()
        return count

    async def create_lookalike(
        self, seed_segment: CustomerSegment, payload: dict, org_id: uuid.UUID,
    ) -> CustomerSegment:
        name = payload.get("name", f"{seed_segment.name} (Lookalike)")
        lookalike = CustomerSegment(
            organization_id=org_id,
            name=name,
            description=payload.get("description"),
            source="lookalike",
            ml_model_id=seed_segment.ml_model_id,
            segment_metadata={
                "seed_segment_id": str(seed_segment.id),
                "seed_segment_name": seed_segment.name,
                "lookalike_size": payload.get("size", 1000),
            },
            is_dynamic=False,
        )
        self.session.add(lookalike)
        await self.session.flush()
        return lookalike

    async def compute_all(self, org_id: uuid.UUID) -> dict[str, int]:
        result = await self.session.execute(
            select(CustomerSegment).where(
                CustomerSegment.organization_id == org_id,
                CustomerSegment.is_active.is_(True),
            )
        )
        segments = result.scalars().all()
        tasks = [self.recalculate_membership(segment.id, org_id) for segment in segments]
        results = await asyncio.gather(*tasks)
        return {str(segment.id): count for segment, count in zip(segments, results)}

    async def discover_ml_segments(self, org_id: uuid.UUID) -> list[CustomerSegment]:
        try:
            import numpy as np
        except ImportError:
            logger.warning("NumPy not available for ML clustering")
            return []

        stmt = select(CustomerTwin).where(
            CustomerTwin.organization_id == org_id,
            CustomerTwin.status == "built",
        )
        result = await self.session.execute(stmt)
        twins = list(result.scalars().all())

        if len(twins) < 10:
            logger.info("Not enough twins for clustering", extra={"org_id": str(org_id), "count": len(twins)})
            return []

        features = []
        customer_ids = []
        for twin in twins:
            if twin.engagement_score is None:
                continue
            vec = [
                twin.engagement_score or 0,
                twin.loyalty_score or 0,
                twin.staleness_score or 0,
                min((twin.lifetime_value or 0) / 10000.0, 1.0),
            ]
            sentiment = twin.sentiment_trend or []
            avg_s = sum(sentiment) / len(sentiment) if sentiment else 0.0
            vec.append(float(avg_s))
            profile = twin.behavior_profile or {}
            subs = profile.get("sub_scores", {}) or {}
            for key in ("purchase_activity", "session_depth", "recency"):
                vec.append(float(subs.get(key, 0)))
            features.append(vec)
            customer_ids.append(twin.customer_id)

        if len(features) < 10:
            return []

        X = np.array(features)
        segments_created = []

        try:
            from sklearn.preprocessing import StandardScaler
            from sklearn.cluster import KMeans
            from sklearn.metrics import silhouette_score

            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)

            best_k = 0
            best_score = -1
            for k in range(max(2, min(len(X_scaled) // 10, 3)), min(8, len(X_scaled) // 5) + 1):
                km = KMeans(n_clusters=k, random_state=42, n_init="auto")
                labels = km.fit_predict(X_scaled)
                if len(set(labels)) > 1:
                    score = silhouette_score(X_scaled, labels)
                    if score > best_score:
                        best_score = score
                        best_k = k

            if best_k < 2:
                return []

            final_kmeans = KMeans(n_clusters=best_k, random_state=42, n_init="auto")
            cluster_labels = final_kmeans.fit_predict(X_scaled).tolist()

            cluster_profiles: dict[int, dict] = {}
            for cid, label in zip(customer_ids, cluster_labels):
                if label not in cluster_profiles:
                    cluster_profiles[label] = {"customer_ids": [], "engagement": [], "loyalty": [], "ltv": []}
                cluster_profiles[label]["customer_ids"].append(cid)

            for label, profile in cluster_profiles.items():
                name = self._cluster_name(label, profile, twins, customer_ids)
                segment = CustomerSegment(
                    organization_id=org_id,
                    name=name,
                    description=f"ML-discovered segment (cluster {label}) from KMeans",
                    source="ml_auto",
                    cluster_id=int(label),
                    ml_model_id="kmeans_v1",
                    segment_metadata={
                        "algorithm": "kmeans",
                        "cluster_label": int(label),
                        "customer_count": len(profile["customer_ids"]),
                        "silhouette_score": round(float(best_score), 4),
                    },
                    is_dynamic=True,
                )
                self.session.add(segment)
                await self.session.flush()

                for cid in profile["customer_ids"]:
                    mapping = CustomerSegmentMapping(
                        customer_id=cid,
                        segment_id=segment.id,
                        organization_id=org_id,
                        assigned_by="ml_clustering",
                    )
                    self.session.add(mapping)
                await self.session.flush()
                segment.customer_count = len(profile["customer_ids"])
                segments_created.append(segment)

            logger.info("ML segments discovered", extra={
                "org_id": str(org_id), "count": len(segments_created), "k": best_k,
            })

        except Exception as e:
            logger.warning("ML clustering failed, using fallback", extra={"error": str(e)})

        await self.session.flush()
        return segments_created

    def _cluster_name(self, label: int, profile: dict, twins: list, customer_ids: list) -> str:
        twin_map = {str(t.customer_id): t for t in twins}
        eng, loy, ltv = [], [], []
        for cid in profile["customer_ids"]:
            t = twin_map.get(str(cid))
            if t:
                eng.append(t.engagement_score or 0)
                loy.append(t.loyalty_score or 0)
                ltv.append(t.lifetime_value or 0)

        avg_eng = sum(eng) / len(eng) if eng else 0
        avg_loy = sum(loy) / len(loy) if loy else 0
        avg_ltv = sum(ltv) / len(ltv) if ltv else 0

        if avg_eng > 0.7 and avg_loy > 0.7:
            return f"Champions (Cluster {label})"
        elif avg_eng > 0.5 and avg_loy > 0.5:
            return f"Loyal Members (Cluster {label})"
        elif avg_eng > 0.3:
            return f"Active Users (Cluster {label})"
        elif avg_ltv > 1000:
            return f"High Value (Cluster {label})"
        else:
            return f"Needs Attention (Cluster {label})"

    async def _apply_rules(self, segment: CustomerSegment, org_id: uuid.UUID) -> None:
        rules = segment.rules or {}
        query = select(Customer.id).where(Customer.organization_id == org_id)
        if rules.get("tags"):
            query = query.where(Customer.tags.contains(rules["tags"]))
        if rules.get("min_engagement"):
            twin_subq = (
                select(CustomerTwin.customer_id)
                .where(
                    CustomerTwin.organization_id == org_id,
                    CustomerTwin.engagement_score >= rules["min_engagement"],
                )
            )
            query = query.where(Customer.id.in_(twin_subq))
        if rules.get("event_types"):
            event_subq = (
                select(Event.customer_id)
                .where(
                    Event.organization_id == org_id,
                    Event.event_type.in_(rules["event_types"]),
                )
                .distinct()
            )
            query = query.where(Customer.id.in_(event_subq))
        if rules.get("min_events"):
            from sqlalchemy import func as f
            event_count_subq = (
                select(Event.customer_id, f.count().label("cnt"))
                .where(Event.organization_id == org_id)
                .group_by(Event.customer_id)
                .having(f.count() >= rules["min_events"])
            )
            query = query.where(Customer.id.in_(
                select(event_count_subq.c.customer_id).select_from(event_count_subq)
            ))
        result = await self.session.execute(query)
        customer_ids = result.scalars().all()
        for cid in customer_ids:
            mapping = CustomerSegmentMapping(
                customer_id=cid,
                segment_id=segment.id,
                organization_id=org_id,
                assigned_by="system",
            )
            self.session.add(mapping)
        await self.session.flush()
