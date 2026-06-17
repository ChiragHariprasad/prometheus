import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ConflictException, ValidationException
from app.core.logging import logger
from app.core.redis import RedisClient
from app.models.customer import (
    Customer, CustomerProfile,
    CustomerSegment, CustomerSegmentMapping, CustomerInterest,
    CustomerPreference,
)
from app.models.event import Event as CustomerEvent
from app.models.twin import CustomerTwin, Prediction as CustomerPrediction
from app.repositories.customer_repository import CustomerRepository
from app.schemas.customer import CustomerCreate, CustomerUpdate


class CustomerService:
    def __init__(self, session: AsyncSession, redis: RedisClient | None = None):
        self.session = session
        self.redis = redis
        self.repo = CustomerRepository(session)

    async def get_customer(self, customer_id: uuid.UUID, organization_id: uuid.UUID) -> Customer:
        customer = await self.repo.get(customer_id, organization_id)
        if not customer:
            raise NotFoundException("Customer", str(customer_id))
        return customer

    async def get_customers(
        self,
        organization_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
        filters: dict | None = None,
        sorts: list | None = None,
    ) -> tuple[list[Customer], int]:
        scoped_filters = dict(filters or {})
        items, total = await self.repo.get_multi(
            skip=skip, limit=limit,
            filters=scoped_filters, sorts=sorts,
            organization_id=organization_id,
        )
        return items, total

    async def create_customer(self, organization_id: uuid.UUID, data: CustomerCreate | dict) -> Customer:
        if isinstance(data, dict):
            email = data.get("email")
            external_id = data.get("external_id")
        else:
            email = data.email
            external_id = data.external_id

        if email:
            existing = await self.repo.search_by_email(email, organization_id, exact=True)
            if existing:
                raise ConflictException(f"Customer with email {email} already exists")
        if external_id:
            existing = await self.repo.search_by_external_id(external_id, organization_id)
            if existing:
                raise ConflictException(f"Customer with external_id {external_id} already exists")

        customer = await self.repo.create(data, organization_id=organization_id)
        logger.info("Customer created", extra={"customer_id": str(customer.id), "org_id": str(organization_id)})
        return customer

    async def update_customer(self, customer_id: uuid.UUID, organization_id: uuid.UUID, data: CustomerUpdate | dict) -> Customer:
        customer = await self.repo.update(customer_id, data, organization_id)
        if not customer:
            raise NotFoundException("Customer", str(customer_id))
        logger.info("Customer updated", extra={"customer_id": str(customer_id), "org_id": str(organization_id)})
        return customer

    async def delete_customer(self, customer_id: uuid.UUID, organization_id: uuid.UUID, soft: bool = True) -> bool:
        customer = await self.repo.get(customer_id, organization_id)
        if not customer:
            raise NotFoundException("Customer", str(customer_id))
        result = await self.repo.delete(customer_id, soft=soft, organization_id=organization_id)
        logger.info("Customer deleted", extra={"customer_id": str(customer_id), "soft": soft})
        return result

    async def merge_customers(self, primary_id: uuid.UUID, secondary_id: uuid.UUID, organization_id: uuid.UUID) -> Customer:
        primary = await self.repo.get(primary_id, organization_id)
        if not primary:
            raise NotFoundException("Primary customer", str(primary_id))
        secondary = await self.repo.get(secondary_id, organization_id)
        if not secondary:
            raise NotFoundException("Secondary customer", str(secondary_id))

        if primary.id == secondary.id:
            raise ValidationException("Cannot merge a customer with itself")

        if not primary.email and secondary.email:
            primary.email = secondary.email
        if not primary.phone and secondary.phone:
            primary.phone = secondary.phone
        if not primary.external_id and secondary.external_id:
            primary.external_id = secondary.external_id
        if not primary.first_name and secondary.first_name:
            primary.first_name = secondary.first_name
        if not primary.last_name and secondary.last_name:
            primary.last_name = secondary.last_name

        existing_tags = set(primary.tags or [])
        existing_tags.update(secondary.tags or [])
        primary.tags = list(existing_tags)

        if secondary.location:
            if primary.location:
                primary.location = {**secondary.location, **primary.location}
            else:
                primary.location = secondary.location

        if secondary.custom_attributes:
            if primary.custom_attributes:
                primary.custom_attributes = {**secondary.custom_attributes, **primary.custom_attributes}
            else:
                primary.custom_attributes = secondary.custom_attributes

        tables_to_reassign = [
            CustomerEvent, CustomerTwin, CustomerProfile,
            CustomerSegmentMapping, CustomerInterest, CustomerPreference,
            CustomerPrediction,
        ]
        for model_cls in tables_to_reassign:
            stmt = (
                select(model_cls)
                .where(
                    model_cls.customer_id == secondary_id,
                    model_cls.organization_id == organization_id,
                )
            )
            result = await self.session.execute(stmt)
            for obj in result.scalars().all():
                obj.customer_id = primary_id

        secondary.is_active = False
        await self.session.flush()
        await self.session.refresh(primary)

        logger.info("Customers merged",
                    extra={"primary_id": str(primary_id), "secondary_id": str(secondary_id)})
        return primary

    async def search_by_rfm(self, organization_id: uuid.UUID, rfm_segment: str) -> list[Customer]:
        stmt = (
            select(Customer)
            .join(CustomerTwin, CustomerTwin.customer_id == Customer.id)
            .where(
                CustomerTwin.organization_id == organization_id,
                CustomerTwin.rfm_segment == rfm_segment,
                Customer.is_active.is_(True),
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_customer_journey(self, organization_id: uuid.UUID, customer_id: uuid.UUID) -> dict:
        customer = await self.repo.get(customer_id, organization_id)
        if not customer:
            raise NotFoundException("Customer", str(customer_id))

        event_stmt = (
            select(CustomerEvent)
            .where(
                CustomerEvent.customer_id == customer_id,
                CustomerEvent.organization_id == organization_id,
            )
            .order_by(CustomerEvent.event_timestamp.asc())
        )
        event_result = await self.session.execute(event_stmt)
        events = list(event_result.scalars().all())

        profile_stmt = select(CustomerProfile).where(
            CustomerProfile.customer_id == customer_id,
            CustomerProfile.organization_id == organization_id,
        )
        profile_result = await self.session.execute(profile_stmt)
        profile = profile_result.scalar_one_or_none()

        segments_stmt = (
            select(CustomerSegment)
            .join(CustomerSegmentMapping, CustomerSegmentMapping.segment_id == CustomerSegment.id)
            .where(
                CustomerSegmentMapping.customer_id == customer_id,
                CustomerSegmentMapping.organization_id == organization_id,
            )
        )
        segments_result = await self.session.execute(segments_stmt)
        segments = list(segments_result.scalars().all())

        timeline = []
        for ev in events:
            timeline.append({
                "id": str(ev.id),
                "type": "event",
                "event_type": ev.event_type,
                "event_name": ev.event_name,
                "channel": ev.channel,
                "value": ev.value,
                "timestamp": ev.event_timestamp.isoformat() if ev.event_timestamp else None,
            })

        return {
            "customer_id": str(customer_id),
            "first_seen_at": customer.first_seen_at.isoformat() if customer.first_seen_at else None,
            "last_seen_at": customer.last_seen_at.isoformat() if customer.last_seen_at else None,
            "total_events": len(events),
            "profile": {
                "title": profile.title if profile else None,
                "company": profile.company if profile else None,
                "industry": profile.industry if profile else None,
            } if profile else None,
            "segments": [
                {"id": str(s.id), "name": s.name} for s in segments
            ],
            "timeline": timeline,
        }

    async def get_lookalike_candidates(self, organization_id: uuid.UUID, seed_customer_id: uuid.UUID, limit: int = 20) -> list[Customer]:
        seed = await self.repo.get(seed_customer_id, organization_id)
        if not seed:
            raise NotFoundException("Seed customer", str(seed_customer_id))

        seed_twin_stmt = select(CustomerTwin).where(
            CustomerTwin.customer_id == seed_customer_id,
            CustomerTwin.organization_id == organization_id,
        )
        seed_twin_result = await self.session.execute(seed_twin_stmt)
        seed_twin = seed_twin_result.scalar_one_or_none()
        if not seed_twin:
            return []

        all_twins_stmt = (
            select(CustomerTwin)
            .where(
                CustomerTwin.organization_id == organization_id,
                CustomerTwin.customer_id != seed_customer_id,
                CustomerTwin.confidence_score.isnot(None),
            )
            .order_by(CustomerTwin.confidence_score.desc())
            .limit(limit)
        )
        all_twins_result = await self.session.execute(all_twins_stmt)
        twins = list(all_twins_result.scalars().all())

        candidate_ids = [t.customer_id for t in twins]
        if not candidate_ids:
            return []

        customers_stmt = select(Customer).where(
            Customer.id.in_(candidate_ids),
            Customer.organization_id == organization_id,
            Customer.is_active.is_(True),
        )
        customers_result = await self.session.execute(customers_stmt)
        customers_map = {c.id: c for c in customers_result.scalars().all()}

        scored = []
        for twin in twins:
            c = customers_map.get(twin.customer_id)
            if c:
                score = self._compute_lookalike_score(seed_twin, twin)
                scored.append((score, c))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored[:limit]]

    def _compute_lookalike_score(self, seed_twin: CustomerTwin, candidate_twin: CustomerTwin) -> float:
        score = 0.0
        if seed_twin.behavior_profile and candidate_twin.behavior_profile:
            score += 0.3
        if seed_twin.interest_graph and candidate_twin.interest_graph:
            score += 0.3
        if seed_twin.channel_affinity and candidate_twin.channel_affinity:
            score += 0.2
        if candidate_twin.confidence_score:
            score *= candidate_twin.confidence_score
        return score
