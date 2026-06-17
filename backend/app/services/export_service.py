import csv
import io
import uuid
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign, CampaignResult
from app.models.customer import Customer
from app.models.twin import CustomerTwin
from app.models.event import Event
from app.models.simulation import Simulation, SimulationResult


class ExportService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def export_customers(
        self, org_id: uuid.UUID, start_date: date | None = None, end_date: date | None = None
    ) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "id", "email", "first_name", "last_name", "phone",
            "external_id", "is_active", "tags", "source",
            "first_seen_at", "last_seen_at", "created_at",
        ])
        stmt = select(Customer).where(Customer.organization_id == org_id)
        if start_date:
            stmt = stmt.where(Customer.created_at >= datetime.combine(start_date, datetime.min.time()))
        if end_date:
            stmt = stmt.where(Customer.created_at <= datetime.combine(end_date, datetime.max.time()))
        result = await self.session.execute(stmt)
        customers = result.scalars().all()
        for c in customers:
            writer.writerow([
                str(c.id), c.email, c.first_name, c.last_name, c.phone,
                c.external_id, c.is_active, ",".join(c.tags or []), c.source,
                c.first_seen_at.isoformat() if c.first_seen_at else "",
                c.last_seen_at.isoformat() if c.last_seen_at else "",
                c.created_at.isoformat() if c.created_at else "",
            ])
        return output.getvalue()

    async def export_campaigns(
        self, org_id: uuid.UUID, start_date: date | None = None, end_date: date | None = None
    ) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "id", "name", "status", "type", "channel",
            "budget", "start_date", "end_date", "created_at",
        ])
        stmt = select(Campaign).where(Campaign.organization_id == org_id)
        if start_date:
            stmt = stmt.where(Campaign.created_at >= datetime.combine(start_date, datetime.min.time()))
        if end_date:
            stmt = stmt.where(Campaign.created_at <= datetime.combine(end_date, datetime.max.time()))
        result = await self.session.execute(stmt)
        campaigns = result.scalars().all()
        for c in campaigns:
            writer.writerow([
                str(c.id), c.name, c.status, c.type, c.channel,
                c.budget, c.start_date, c.end_date,
                c.created_at.isoformat() if c.created_at else "",
            ])
        return output.getvalue()

    async def export_simulation_results(
        self, org_id: uuid.UUID, start_date: date | None = None, end_date: date | None = None
    ) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "simulation_id", "simulation_name", "status",
            "metric", "value", "confidence", "created_at",
        ])
        stmt = (
            select(SimulationResult, Simulation.name)
            .join(Simulation, SimulationResult.simulation_id == Simulation.id)
            .where(Simulation.organization_id == org_id)
        )
        if start_date:
            stmt = stmt.where(SimulationResult.created_at >= datetime.combine(start_date, datetime.min.time()))
        if end_date:
            stmt = stmt.where(SimulationResult.created_at <= datetime.combine(end_date, datetime.max.time()))
        result = await self.session.execute(stmt)
        rows = result.all()
        for sr, sim_name in rows:
            writer.writerow([
                str(sr.simulation_id), sim_name, sr.status,
                sr.metric, sr.value, sr.confidence,
                sr.created_at.isoformat() if sr.created_at else "",
            ])
        return output.getvalue()

    async def export_analytics(
        self, org_id: uuid.UUID, report_type: str,
        start_date: date | None = None, end_date: date | None = None,
    ) -> str:
        if report_type == "customers":
            return await self.export_customers(org_id, start_date, end_date)
        elif report_type == "campaigns":
            return await self.export_campaigns(org_id, start_date, end_date)
        elif report_type in ("simulations", "simulation_results"):
            return await self.export_simulation_results(org_id, start_date, end_date)
        elif report_type == "events":
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow([
                "id", "customer_id", "event_type", "event_name",
                "channel", "source", "value", "event_timestamp",
            ])
            stmt = select(Event).where(Event.organization_id == org_id)
            if start_date:
                stmt = stmt.where(Event.created_at >= datetime.combine(start_date, datetime.min.time()))
            if end_date:
                stmt = stmt.where(Event.created_at <= datetime.combine(end_date, datetime.max.time()))
            stmt = stmt.order_by(Event.created_at.desc())
            result = await self.session.execute(stmt)
            events = result.scalars().all()
            for ev in events:
                writer.writerow([
                    str(ev.id), str(ev.customer_id) if ev.customer_id else "",
                    ev.event_type, ev.event_name, ev.channel, ev.source,
                    ev.value, ev.event_timestamp.isoformat() if ev.event_timestamp else "",
                ])
            return output.getvalue()
        elif report_type == "twins":
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow([
                "customer_id", "engagement_score", "loyalty_score",
                "lifetime_value", "confidence_score", "staleness_score",
                "last_event_at", "status",
            ])
            stmt = select(CustomerTwin).where(CustomerTwin.organization_id == org_id)
            result = await self.session.execute(stmt)
            twins = result.scalars().all()
            for t in twins:
                writer.writerow([
                    str(t.customer_id), t.engagement_score, t.loyalty_score,
                    t.lifetime_value, t.confidence_score, t.staleness_score,
                    t.last_event_at.isoformat() if t.last_event_at else "",
                    t.status,
                ])
            return output.getvalue()
        return ""
