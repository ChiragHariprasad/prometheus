import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import CustomerSegment, CustomerSegmentMapping, Customer
from app.repositories.base import AsyncRepository


class SegmentRepository(AsyncRepository[CustomerSegment]):
    def __init__(self, session: AsyncSession):
        super().__init__(CustomerSegment, session)

    async def get_by_name(self, name: str, organization_id: uuid.UUID) -> CustomerSegment | None:
        stmt = select(CustomerSegment).where(
            CustomerSegment.organization_id == organization_id,
            CustomerSegment.name == name,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_dynamic_segments(self, organization_id: uuid.UUID) -> list[CustomerSegment]:
        stmt = select(CustomerSegment).where(
            CustomerSegment.organization_id == organization_id,
            CustomerSegment.is_dynamic == True,
            CustomerSegment.is_active == True,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_members(
        self, segment_id: uuid.UUID, organization_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> tuple[list[Customer], int]:
        count_stmt = (
            select(func.count())
            .select_from(CustomerSegmentMapping)
            .where(
                CustomerSegmentMapping.segment_id == segment_id,
                CustomerSegmentMapping.organization_id == organization_id,
            )
        )
        total = (await self.session.execute(count_stmt)).scalar() or 0

        stmt = (
            select(Customer)
            .join(CustomerSegmentMapping, CustomerSegmentMapping.customer_id == Customer.id)
            .where(
                CustomerSegmentMapping.segment_id == segment_id,
                CustomerSegmentMapping.organization_id == organization_id,
                Customer.is_active.is_(True),
            )
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def add_member(self, segment_id: uuid.UUID, customer_id: uuid.UUID, organization_id: uuid.UUID) -> None:
        existing = await self.session.execute(
            select(CustomerSegmentMapping).where(
                CustomerSegmentMapping.segment_id == segment_id,
                CustomerSegmentMapping.customer_id == customer_id,
                CustomerSegmentMapping.organization_id == organization_id,
            )
        )
        if not existing.scalar_one_or_none():
            mapping = CustomerSegmentMapping(
                segment_id=segment_id,
                customer_id=customer_id,
                organization_id=organization_id,
            )
            self.session.add(mapping)
            await self.session.flush()

    async def remove_member(self, segment_id: uuid.UUID, customer_id: uuid.UUID, organization_id: uuid.UUID) -> None:
        stmt = select(CustomerSegmentMapping).where(
            CustomerSegmentMapping.segment_id == segment_id,
            CustomerSegmentMapping.customer_id == customer_id,
            CustomerSegmentMapping.organization_id == organization_id,
        )
        result = await self.session.execute(stmt)
        mapping = result.scalar_one_or_none()
        if mapping:
            await self.session.delete(mapping)
            await self.session.flush()

    async def clear_members(self, segment_id: uuid.UUID, organization_id: uuid.UUID) -> int:
        stmt = select(CustomerSegmentMapping).where(
            CustomerSegmentMapping.segment_id == segment_id,
            CustomerSegmentMapping.organization_id == organization_id,
        )
        result = await self.session.execute(stmt)
        mappings = list(result.scalars().all())
        for m in mappings:
            await self.session.delete(m)
        await self.session.flush()
        return len(mappings)
