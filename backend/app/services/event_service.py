import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import select, func, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ValidationException, NotFoundException
from app.core.kafka import KafkaClient
from app.core.logging import logger
from app.core.redis import RedisClient
from app.models.customer import Customer, CustomerSession
from app.models.event import Event as CustomerEvent
from app.models.twin import CustomerTwin
from app.schemas.event import EventCreate, EventResponse
from app.repositories.customer_repository import CustomerRepository
from app.repositories.event_repository import EventRepository


class EventService:
    def __init__(self, session: AsyncSession, kafka: KafkaClient | None = None, redis: RedisClient | None = None):
        self.session = session
        self.kafka = kafka
        self.redis = redis
        self.repo = CustomerRepository(session)
        self.event_repo = EventRepository(session)

    async def ingest_event(self, organization_id: uuid.UUID, event_data: EventCreate | dict, customer_id: uuid.UUID | None = None) -> EventResponse:
        if isinstance(event_data, dict):
            event_type = event_data.get("event_type", "")
            event_name = event_data.get("event_name", "")
            event_properties = event_data.get("event_properties", {})
            channel = event_data.get("channel")
            source = event_data.get("source")
            device_type = event_data.get("device_type")
            device_os = event_data.get("device_os")
            browser = event_data.get("browser")
            ip_address = event_data.get("ip_address")
            user_agent = event_data.get("user_agent")
            referrer = event_data.get("referrer")
            url = event_data.get("url")
            geolocation = event_data.get("geolocation")
            campaign_id = event_data.get("campaign_id")
            value = event_data.get("value")
            currency = event_data.get("currency")
            event_timestamp = event_data.get("event_timestamp")
            context = event_data.get("context", {})
        else:
            event_type = event_data.event_type
            event_name = event_data.event_name
            event_properties = event_data.event_properties
            channel = event_data.channel
            source = event_data.source
            device_type = event_data.device_type
            device_os = event_data.device_os
            browser = event_data.browser
            ip_address = event_data.ip_address
            user_agent = event_data.user_agent
            referrer = event_data.referrer
            url = event_data.url
            geolocation = event_data.geolocation
            campaign_id = event_data.campaign_id
            value = event_data.value
            currency = event_data.currency
            event_timestamp = event_data.event_timestamp
            context = event_data.context

        if not event_type or not event_name:
            raise ValidationException("event_type and event_name are required")

        if not customer_id:
            customer_id = await self._resolve_customer(organization_id, event_properties, context)

        if not event_timestamp:
            event_timestamp = datetime.now(timezone.utc)

        event = CustomerEvent(
            organization_id=organization_id,
            customer_id=customer_id,
            event_type=event_type,
            event_name=event_name,
            event_properties=event_properties or {},
            context=context or {},
            channel=channel,
            source=source,
            device_type=device_type,
            device_os=device_os,
            browser=browser,
            ip_address=ip_address,
            user_agent=user_agent,
            referrer=referrer,
            url=url,
            geolocation=geolocation,
            campaign_id=uuid.UUID(campaign_id) if campaign_id and isinstance(campaign_id, str) else campaign_id,
            value=value,
            currency=currency,
            processed=False,
            event_timestamp=event_timestamp,
        )
        self.session.add(event)
        await self.session.flush()
        await self.session.refresh(event)

        if customer_id:
            await self._update_customer_last_seen(customer_id, organization_id, event_timestamp)

        if self.redis:
            await self.redis.delete(f"dashboard:{organization_id}")

        await self._produce_to_kafka(organization_id, event)

        await self._compute_embedding(event)

        logger.info("Event ingested", extra={
            "event_id": str(event.id), "event_type": event_type, "org_id": str(organization_id),
        })

        return EventResponse(
            id=event.id,
            organization_id=event.organization_id,
            customer_id=event.customer_id,
            session_id=event.session_id,
            event_type=event.event_type,
            event_name=event.event_name,
            event_properties=event.event_properties or {},
            context=event.context or {},
            channel=event.channel,
            source=event.source,
            device_type=event.device_type,
            device_os=event.device_os,
            browser=event.browser,
            ip_address=event.ip_address,
            user_agent=event.user_agent,
            referrer=event.referrer,
            url=event.url,
            geolocation=event.geolocation,
            campaign_id=str(event.campaign_id) if event.campaign_id else None,
            value=event.value,
            currency=event.currency,
            processed=event.processed,
            event_timestamp=event.event_timestamp,
            ingested_at=event.ingested_at,
        )

    async def batch_ingest(self, events: list[EventCreate | dict], organization_id: uuid.UUID) -> int:
        return await self.ingest_batch(organization_id, events)

    async def ingest_batch(self, organization_id: uuid.UUID, events: list[EventCreate | dict]) -> int:
        count = 0
        for ev_data in events:
            try:
                await self.ingest_event(organization_id, ev_data)
                count += 1
            except Exception as e:
                logger.error("Failed to ingest batch event", extra={"error": str(e), "org_id": str(organization_id)})
        return count

    async def process_event(self, organization_id: uuid.UUID, event: CustomerEvent) -> None:
        try:
            if event.processed:
                return

            from app.services.twin_service import TwinService
            twin_service = TwinService(self.session, self.redis)

            if event.customer_id:
                try:
                    await twin_service.update_twin_from_event(organization_id, event.customer_id, event)
                except Exception as e:
                    logger.warning("Twin update failed", extra={"error": str(e), "event_id": str(event.id)})

            if event.event_type == "purchase" and event.campaign_id:
                from app.models.campaign import CampaignTarget
                update_stmt = (
                    select(CampaignTarget)
                    .where(
                        CampaignTarget.campaign_id == event.campaign_id,
                        CampaignTarget.customer_id == event.customer_id,
                        CampaignTarget.organization_id == organization_id,
                    )
                )
                result = await self.session.execute(update_stmt)
                target = result.scalar_one_or_none()
                if target:
                    target.converted_at = event.event_timestamp
                    target.revenue = (target.revenue or 0) + (event.value or 0)
                    target.status = "converted"

            await self.session.execute(
                update(CustomerEvent)
                .where(CustomerEvent.id == event.id, CustomerEvent.processed == False)
                .values(processed=True)
            )

        except Exception as e:
            logger.error("Event processing failed", extra={
                "error": str(e), "event_id": str(event.id),
                "org_id": str(organization_id),
            })

    async def get_event_summary(self, organization_id: uuid.UUID, date_from: datetime, date_to: datetime) -> dict:
        events = await self.event_repo.get_date_range(organization_id, date_from.date(), date_to.date())

        by_type: dict[str, dict] = {}
        for e in events:
            entry = by_type.setdefault(e.event_type, {"count": 0, "total_value": 0.0})
            entry["count"] += 1
            entry["total_value"] += e.value or 0

        unique_customers = len({e.customer_id for e in events if e.customer_id})
        total_events = len(events)
        total_value = sum(e.value or 0 for e in events)

        return {
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "total_events": total_events,
            "total_value": round(total_value, 2),
            "unique_customers": unique_customers,
            "events_by_type": [
                {"event_type": etype, "count": data["count"], "total_value": round(data["total_value"], 2)}
                for etype, data in by_type.items()
            ],
        }

    async def _resolve_customer(self, organization_id: uuid.UUID, event_properties: dict, context: dict) -> uuid.UUID | None:
        email = event_properties.get("email") or context.get("email")
        external_id = event_properties.get("external_id") or context.get("external_id")

        if email:
            customers = await self.repo.search_by_email(email, organization_id, exact=True)
            if customers:
                return customers[0].id
        if external_id:
            customer = await self.repo.search_by_external_id(external_id, organization_id)
            if customer:
                return customer.id
        return None

    async def _update_customer_last_seen(self, customer_id: uuid.UUID, organization_id: uuid.UUID, timestamp: datetime) -> None:
        customer = await self.repo.get(customer_id, organization_id)
        if customer:
            if not customer.first_seen_at or timestamp < customer.first_seen_at:
                customer.first_seen_at = timestamp
            if not customer.last_seen_at or timestamp > customer.last_seen_at:
                customer.last_seen_at = timestamp
            await self.session.flush()

    async def _compute_embedding(self, event: CustomerEvent) -> None:
        try:
            from app.services.embedding_service import EmbeddingService
            svc = EmbeddingService(self.session)
            await svc.embed_event(event)
        except Exception as e:
            logger.warning("Event embedding skipped", extra={"error": str(e), "event_id": str(event.id)})

    async def _produce_to_kafka(self, organization_id: uuid.UUID, event: CustomerEvent) -> None:
        if not self.kafka:
            return
        try:
            message = {
                "event_id": str(event.id),
                "organization_id": str(organization_id),
                "customer_id": str(event.customer_id) if event.customer_id else None,
                "event_type": event.event_type,
                "event_name": event.event_name,
                "event_properties": event.event_properties,
                "channel": event.channel,
                "source": event.source,
                "value": event.value,
                "currency": event.currency,
                "event_timestamp": event.event_timestamp.isoformat() if event.event_timestamp else None,
                "ingested_at": event.ingested_at.isoformat() if event.ingested_at else None,
            }
            await self.kafka.produce("twin.cx.events.raw", message, key=str(organization_id))
        except Exception as e:
            logger.warning("Failed to produce event to Kafka", extra={"error": str(e), "event_id": str(event.id)})
