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
