import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select, or_, and_, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer, CustomerSegmentMapping, CustomerSegment
from app.models.event import Event as CustomerEvent
from app.models.twin import CustomerTwin
from app.repositories.base import AsyncRepository


class CustomerRepository(AsyncRepository[Customer]):
    def __init__(self, session: AsyncSession):
        super().__init__(Customer, session)

    async def search_by_email(self, email: str, organization_id: uuid.UUID, exact: bool = False) -> list[Customer]:
        stmt = select(Customer).where(
            Customer.organization_id == organization_id,
            Customer.email.ilike(email) if not exact else Customer.email == email,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def search_by_external_id(self, external_id: str, organization_id: uuid.UUID) -> Customer | None:
        stmt = select(Customer).where(
            Customer.organization_id == organization_id,
            Customer.external_id == external_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_duplicates(self, organization_id: uuid.UUID, threshold: float = 0.85) -> list[list[Customer]]:
        stmt = select(Customer).where(
            Customer.organization_id == organization_id,
            Customer.is_active.is_(True),
        )
        result = await self.session.execute(stmt)
        customers = list(result.scalars().all())

        groups: list[list[Customer]] = []
        visited: set[uuid.UUID] = set()

        for i, c1 in enumerate(customers):
            if c1.id in visited:
                continue
            group = [c1]
            for c2 in customers[i + 1:]:
                if c2.id in visited:
                    continue
                if self._is_duplicate(c1, c2):
                    group.append(c2)
                    visited.add(c2.id)
            if len(group) > 1:
                visited.add(c1.id)
                groups.append(group)

        return groups

    def _is_duplicate(self, a: Customer, b: Customer) -> bool:
        if a.email and b.email and a.email.lower() == b.email.lower():
            return True
        if a.external_id and b.external_id and a.external_id == b.external_id:
            return True
        if a.phone and b.phone and a.phone == b.phone:
            return True
        return False

    async def get_with_events(self, customer_id: uuid.UUID, organization_id: uuid.UUID, limit: int = 50) -> tuple[Customer | None, list[CustomerEvent]]:
        stmt = select(Customer).where(
            Customer.id == customer_id,
            Customer.organization_id == organization_id,
        )
        result = await self.session.execute(stmt)
        customer = result.scalar_one_or_none()
        if not customer:
            return None, []

        event_stmt = (
            select(CustomerEvent)
            .where(
                CustomerEvent.customer_id == customer_id,
                CustomerEvent.organization_id == organization_id,
            )
            .order_by(CustomerEvent.event_timestamp.desc())
            .limit(limit)
        )
        event_result = await self.session.execute(event_stmt)
        events = list(event_result.scalars().all())

        return customer, events

    async def get_with_twin(self, customer_id: uuid.UUID, organization_id: uuid.UUID) -> tuple[Customer | None, CustomerTwin | None]:
        stmt = select(Customer).where(
            Customer.id == customer_id,
            Customer.organization_id == organization_id,
        )
        result = await self.session.execute(stmt)
        customer = result.scalar_one_or_none()
        if not customer:
            return None, None

        twin_stmt = select(CustomerTwin).where(
            CustomerTwin.customer_id == customer_id,
            CustomerTwin.organization_id == organization_id,
        )
        twin_result = await self.session.execute(twin_stmt)
        twin = twin_result.scalar_one_or_none()

        return customer, twin

    async def get_by_segment(self, segment_id: uuid.UUID, organization_id: uuid.UUID, skip: int = 0, limit: int = 100) -> tuple[list[Customer], int]:
        count_stmt = (
            select(func.count())
            .select_from(CustomerSegmentMapping)
            .where(
                CustomerSegmentMapping.segment_id == segment_id,
                CustomerSegmentMapping.organization_id == organization_id,
            )
        )
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar() or 0

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
        customers = list(result.scalars().all())

        return customers, total

    async def bulk_create(self, customers: list[dict], organization_id: uuid.UUID) -> list[Customer]:
        created: list[Customer] = []
        for data in customers:
            data["organization_id"] = organization_id
            obj = Customer(**data)
            self.session.add(obj)
            created.append(obj)
        await self.session.flush()
        for obj in created:
            await self.session.refresh(obj)
        return created

    async def bulk_update_tags(self, customer_ids: list[uuid.UUID], tags: list[str], organization_id: uuid.UUID) -> int:
        stmt = (
            select(Customer)
            .where(
                Customer.id.in_(customer_ids),
                Customer.organization_id == organization_id,
            )
        )
        result = await self.session.execute(stmt)
        customers = list(result.scalars().all())

        for customer in customers:
            existing = set(customer.tags or [])
            existing.update(tags)
            customer.tags = list(existing)

        await self.session.flush()
        return len(customers)
