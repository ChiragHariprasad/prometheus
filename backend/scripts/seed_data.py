"""Seed script using raw SQL — bypass ORM/enum mismatches."""
import asyncio
import json
import uuid
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from app.core.database import async_session_factory
from app.core.security import hash_password


async def seed():
    async with async_session_factory() as session:
        org_id = uuid.uuid4()
        judge_id = uuid.uuid4()
        admin_role_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        await session.execute(text("""
            INSERT INTO organizations (id, name, slug, plan, settings, features, max_customers, max_users, is_active, created_at, updated_at)
            VALUES (:id, :name, :slug, 'enterprise', '{}', '{}', 100000, 100, true, :now, :now)
        """), {"id": org_id, "name": "TExpedition", "slug": "texpedition", "now": now})

        await session.execute(text("""
            INSERT INTO roles (id, organization_id, name, description, is_system, priority, created_at)
            VALUES (:id, :org_id, 'Admin', 'Administrator', true, 100, :now)
        """), {"id": admin_role_id, "org_id": org_id, "now": now})

        pwh = hash_password("pass@123")
        await session.execute(text("""
            INSERT INTO users (id, organization_id, email, password_hash, first_name, last_name, is_active, is_verified, password_changed_at, created_at, updated_at)
            VALUES (:id, :org_id, 'judge@texpedition.com', :pwh, 'Judge', 'User', true, true, :now, :now, :now)
        """), {"id": judge_id, "org_id": org_id, "pwh": pwh, "now": now})

        await session.execute(text("""
            INSERT INTO user_roles (user_id, role_id, assigned_at)
            VALUES (:uid, :rid, :now)
        """), {"uid": judge_id, "rid": admin_role_id, "now": now})

        first_names = ["Alice", "Bob", "Carol", "Dave", "Eve", "Frank", "Grace", "Henry", "Iris", "Jack"]
        last_names = ["Smith", "Jones", "Brown", "Davis", "Wilson", "Moore", "Taylor", "Anderson", "Thomas", "Jackson"]
        domains = ["gmail.com", "yahoo.com", "outlook.com", "company.com", "example.org"]
        cities = ["New York", "San Francisco", "London", "Berlin", "Tokyo"]
        countries = ["US", "US", "UK", "DE", "JP"]
        tzs = ["America/New_York", "America/Los_Angeles", "Europe/London", "Europe/Berlin", "Asia/Tokyo"]

        customer_ids = []
        for i in range(10):
            cid = uuid.uuid4()
            customer_ids.append(cid)
            email = f"{first_names[i].lower()}.{last_names[i].lower()}{i}@{domains[i % len(domains)]}"
            tags = random.sample(["vip", "new", "returning", "high_value", "at_risk", "mobile_user"], k=random.randint(1, 3))
            location = {"city": cities[i % 5], "country": countries[i % 5], "timezone": tzs[i % 5]}

            await session.execute(text("""
                INSERT INTO customers (id, organization_id, external_id, email, first_name, last_name, is_active, consent_marketing, consent_analytics, consent_profiling, first_seen_at, last_seen_at, location, tags, created_at, updated_at)
                VALUES (:id, :org_id, :ext_id, :email, :fn, :ln, true, true, true, true, :first_seen, :last_seen, CAST(:loc AS jsonb), :tags, :now, :now)
            """), {
                "id": cid, "org_id": org_id,
                "ext_id": f"ext-{i:04d}", "email": email,
                "fn": first_names[i], "ln": last_names[i],
                "first_seen": now - timedelta(days=random.randint(30, 180)),
                "last_seen": now - timedelta(hours=random.randint(0, 72)),
                "loc": json.dumps(location), "tags": tags, "now": now,
            })

            await session.execute(text("""
                INSERT INTO customer_profiles (id, customer_id, organization_id, company, industry, annual_revenue, employee_count, created_at, updated_at)
                VALUES (:id, :cid, :org_id, :company, :industry, :revenue, :emp, :now, :now)
            """), {
                "id": uuid.uuid4(), "cid": cid, "org_id": org_id,
                "company": random.choice(["Acme Corp", "Globex Inc", "Initech", "Hooli", "Stark Industries"]),
                "industry": random.choice(["Technology", "Finance", "Healthcare", "Retail", "Manufacturing"]),
                "revenue": random.uniform(100000, 10000000),
                "emp": random.randint(10, 10000),
                "now": now,
            })

        await session.flush()

        for cid in customer_ids:
            behavior = {
                "avg_session_duration": random.uniform(30, 600),
                "pages_per_session": random.uniform(1, 10),
                "purchase_frequency": random.uniform(0.1, 5.0),
                "bounce_rate": random.uniform(0.1, 0.7),
            }
            interests = random.sample(
                ["electronics", "fashion", "home", "sports", "books", "music", "travel", "food"],
                k=random.randint(2, 5),
            )
            channel = {
                "email": random.uniform(0, 1),
                "sms": random.uniform(0, 1),
                "push": random.uniform(0, 1),
                "in_app": random.uniform(0, 1),
            }
            sentiment = [random.uniform(-1, 1) for _ in range(10)]
            intent = {"next_best_action": random.choice(["email_offer", "push_discount", "retention_call"])}
            risk = {"churn_risk": random.uniform(0, 1)}

            await session.execute(text("""
                INSERT INTO customer_twins (id, customer_id, organization_id, status, behavior_profile, interest_graph, channel_affinity, engagement_score, loyalty_score, lifetime_value, sentiment_trend, intent_forecast, risk_indicators, communication_preferences, confidence_score, built_at, created_at, updated_at)
                VALUES (:id, :cid, :org_id, CAST('active' AS twin_status), CAST(:behavior AS jsonb), CAST(:interests AS jsonb), CAST(:channel AS jsonb), :engagement, :loyalty, :ltv, :sentiment, CAST(:intent AS jsonb), CAST(:risk AS jsonb), CAST(:prefs AS jsonb), :confidence, :built_at, :now, :now)
            """), {
                "id": uuid.uuid4(), "cid": cid, "org_id": org_id,
                "behavior": json.dumps(behavior),
                "interests": json.dumps({"categories": interests}),
                "channel": json.dumps(channel),
                "engagement": random.uniform(0, 100),
                "loyalty": random.uniform(0, 100),
                "ltv": random.uniform(100, 50000),
                "sentiment": sentiment,  # array, asyncpg handles it
                "intent": json.dumps(intent),
                "risk": json.dumps(risk),
                "prefs": json.dumps({"email": True, "push": True, "sms": False}),
                "confidence": random.uniform(0.5, 1.0),
                "built_at": now - timedelta(days=random.randint(0, 30)),
                "now": now,
            })

        await session.flush()

        event_types = ["page_view", "purchase", "email_open", "email_click", "add_to_cart", "search", "login", "session"]
        total_events = 0
        for cid in customer_ids:
            for _ in range(random.randint(10, 30)):
                et = random.choice(event_types)
                ts = now - timedelta(
                    days=random.randint(0, 60),
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59),
                )
                props = {}
                if et in ("purchase", "add_to_cart"):
                    props = {"value": round(random.uniform(10, 500), 2), "currency": "USD",
                             "page": random.choice(["/products", "/cart", "/checkout"])}
                await session.execute(text("""
                    INSERT INTO customer_events (id, organization_id, customer_id, event_type, event_name, event_properties, channel, source, device_type, processed, event_timestamp, ingested_at, created_at)
                    VALUES (:id, :org_id, :cid, CAST(:et AS event_type), :name, CAST(:props AS jsonb), :channel, :source, :device, false, :ts, :now, :now)
                """), {
                    "id": uuid.uuid4(), "org_id": org_id, "cid": cid,
                    "et": et,
                    "name": et.replace("_", " ").title(),
                    "props": json.dumps(props),
                    "channel": random.choice(["web", "mobile", "email"]),
                    "source": random.choice(["direct", "organic", "paid", "referral"]),
                    "device": random.choice(["desktop", "mobile", "tablet"]),
                    "ts": ts,
                    "now": now,
                })
                total_events += 1

        await session.commit()
        print(f"Seed complete: org={org_id}, judge={judge_id}, customers=10, events={total_events}")


if __name__ == "__main__":
    asyncio.run(seed())
