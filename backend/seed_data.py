"""Seed comprehensive demo data into the PROMETHEUS org.

Generates realistic data exercising every analytics endpoint,
twin computation, prediction engine, and simulation engine.

Usage:  cd backend && python seed_data.py
"""

import asyncio
import uuid
import random
import json
import math
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, text
from app.core.database import async_session_factory, engine
from app.models.customer import Customer, CustomerInterest, CustomerProfile, CustomerPreference
from app.models.twin import CustomerTwin, Prediction
from app.models.simulation import Simulation, SimulationResult, SimulationRun

ORG_ID = uuid.UUID("eb35c0b4-f66b-442b-b35a-30246d8df683")
NOW = datetime.now(timezone.utc)

FIRST_NAMES = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Hank", "Iris", "Jack", "Kate", "Leo"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]

ALL_EVENT_TYPES = [
    "purchase", "page_view", "email_sent", "email_open", "email_click",
    "cart_abandon", "bounce", "unsubscribe", "review_submit", "feedback",
    "positive_feedback", "negative_feedback", "complaint", "support_ticket",
    "support_resolved", "survey_response", "referral", "return", "session",
    "search", "app_open", "login",
]

INTEREST_CATEGORIES = [
    "Electronics", "Fashion", "Sports", "Travel", "Books",
    "Gaming", "Finance", "Health", "Automotive", "Home",
]

CHANNELS = ["email", "sms", "push", "in_app", "webhook"]

EVENT_WEIGHTS = {
    "purchase": 10, "email_click": 4, "email_open": 2,
    "page_view": 1, "login": 1,
}

SENTIMENT_MAP = {
    "purchase": 0.3, "positive_feedback": 0.5, "referral": 0.4,
    "email_open": 0.1, "email_click": 0.2, "app_open": 0.1,
    "page_view": 0.05, "support_resolved": 0.2, "survey_response": 0.1,
    "review_submit": 0.15, "feedback": 0.05,
    "negative_feedback": -0.4, "complaint": -0.5, "support_ticket": -0.2,
    "unsubscribe": -0.6, "bounce": -0.1, "cart_abandon": -0.2,
    "return": -0.1,
}


def exp_decay_weight(base: float, days_old: int, half_life: int = 30) -> float:
    return base * math.exp(-days_old / half_life)


async def seed():
    async with engine.begin() as conn:
        await conn.execute(text("SET app.current_org_id = '00000000-0000-0000-0000-000000000000'"))

    async with async_session_factory() as session:
        await session.execute(text("SET app.current_org_id = '00000000-0000-0000-0000-000000000000'"))

        # ── 1. Customers ──────────────────────────────────────────
        existing = (await session.execute(
            select(Customer).where(Customer.organization_id == ORG_ID)
        )).scalars().all()
        if existing:
            print(f"Already have {len(existing)} customers — skipping.")
            customers = existing
        else:
            customers = []
            for i in range(12):
                fname = FIRST_NAMES[i % len(FIRST_NAMES)]
                lname = LAST_NAMES[i % len(LAST_NAMES)]
                days_ago = random.randint(1, 180)
                created = NOW - timedelta(days=days_ago)
                c = Customer(
                    organization_id=ORG_ID, external_id=f"ext-{i:04d}",
                    email=f"{fname.lower()}.{lname.lower()}{i}@example.com",
                    phone=f"+1-555-{random.randint(100,999)}-{random.randint(1000,9999)}",
                    first_name=fname, last_name=lname,
                    timezone=random.choice(["US/Eastern","US/Pacific","US/Central","Europe/London","Asia/Tokyo"]),
                    locale="en-US",
                    location={"city": random.choice(["NYC","LA","Chicago","Houston"]), "country":"US"},
                    tags=random.sample(["newsletter","loyalty","premium","beta"], k=random.randint(1,3)),
                    is_active=True, consent_marketing=random.random() > 0.2,
                    consent_analytics=True, consent_profiling=random.random() > 0.3,
                    source=random.choice(["api","web","mobile","import"]),
                    first_seen_at=created,
                    last_seen_at=created + timedelta(days=random.randint(0, days_ago)),
                )
                session.add(c)
                customers.append(c)
            await session.flush()
            print(f"Created {len(customers)} customers.")

        cids = [c.id for c in customers]
        ages = [(NOW - (c.first_seen_at or NOW)).days for c in customers]

        # ── 2. Customer Profiles ──────────────────────────────────
        existing_profiles = (await session.execute(
            text("SELECT count(*) FROM customer_profiles WHERE organization_id=:o").bindparams(o=ORG_ID)
        )).scalar()
        if not existing_profiles or existing_profiles == 0:
            profile_count = 0
            for c in customers:
                cp = CustomerProfile(
                    customer_id=c.id, organization_id=ORG_ID,
                    title=random.choice(["Mr.", "Ms.", "Dr.", ""]),
                    company=random.choice(["Acme Corp", "Globex", "Initech", "Umbrella", "Stark Ind"]),
                    industry=random.choice(["Technology", "Finance", "Healthcare", "Retail", "Manufacturing"]),
                    annual_revenue=round(random.uniform(50000, 500000), 2),
                    employee_count=random.randint(1, 1000),
                    website=f"https://{c.first_name.lower()}{c.last_name.lower()}.com",
                    bio=f"{c.first_name} {c.last_name} — loyal customer since 2025.",
                    preferred_language="en",
                    communication_style=random.choice(["formal", "casual", "direct"]),
                    personality_traits={
                        "openness": round(random.uniform(0.3, 0.9), 2),
                        "conscientiousness": round(random.uniform(0.4, 1.0), 2),
                        "extraversion": round(random.uniform(0.2, 0.9), 2),
                        "agreeableness": round(random.uniform(0.4, 1.0), 2),
                        "neuroticism": round(random.uniform(0.1, 0.6), 2),
                    },
                    psychographic_segment=random.choice(["achiever", "explorer", "socialite", "traditionalist"]),
                    enrichment_status="enriched",
                    last_enriched_at=NOW - timedelta(days=random.randint(0, 30)),
                )
                session.add(cp)
                profile_count += 1
            await session.flush()
            print(f"Customer profiles: {profile_count} created.")
        else:
            print(f"Customer profiles: {existing_profiles} existing.")

        # ── 3. Customer Preferences ───────────────────────────────
        existing_prefs = (await session.execute(
            text("SELECT count(*) FROM customer_preferences WHERE organization_id=:o").bindparams(o=ORG_ID)
        )).scalar()
        if not existing_prefs or existing_prefs == 0:
            pref_count = 0
            for c in customers:
                pref = CustomerPreference(
                    customer_id=c.id, organization_id=ORG_ID,
                    channel_email=random.random() > 0.1,
                    channel_sms=random.random() > 0.3,
                    channel_push=random.random() > 0.3,
                    channel_in_app=random.random() > 0.2,
                    channel_webhook=random.random() > 0.6,
                    channel_whatsapp=random.random() > 0.5,
                    email_frequency=random.choice(["daily", "weekly", "monthly", "never"]),
                    sms_frequency=random.choice(["weekly", "monthly", "never"]),
                    push_frequency=random.choice(["daily", "weekly", "never"]),
                    quiet_hours_start=None,
                    quiet_hours_end=None,
                    timezone=c.timezone,
                    preferred_categories=random.sample(INTEREST_CATEGORIES, k=random.randint(2, 5)),
                    preferred_brands=random.sample(["Nike", "Apple", "Samsung", "Sony", "Adidas"], k=random.randint(1, 3)),
                    excluded_categories=random.sample(INTEREST_CATEGORIES, k=random.randint(0, 2)),
                    max_communications_per_day=random.choice([1, 2, 3, 5]),
                    do_not_disturb=random.random() > 0.8,
                )
                session.add(pref)
                pref_count += 1
            await session.flush()
            print(f"Customer preferences: {pref_count} created.")
        else:
            print(f"Customer preferences: {existing_prefs} existing.")

        # ── 4. Customer Interests ────────────────────────────────
        existing_interests = (await session.execute(
            text("SELECT count(*) FROM customer_interests WHERE organization_id=:o").bindparams(o=ORG_ID)
        )).scalar()
        if not existing_interests or existing_interests == 0:
            interest_count = 0
            for c in customers:
                num_interests = random.randint(3, 7)
                categories = random.sample(INTEREST_CATEGORIES, k=num_interests)
                for cat in categories:
                    last_interaction = NOW - timedelta(days=random.randint(0, max(ages[customers.index(c)], 1)))
                    days_since = (NOW - last_interaction).days
                    base_score = random.uniform(0.3, 0.95)
                    ci = CustomerInterest(
                        customer_id=c.id, organization_id=ORG_ID,
                        category=cat,
                        subcategory=random.choice([None, f"{cat} Premium", f"{cat} Budget"]),
                        interest_level=round(base_score, 4),
                        affinity_score=round(base_score * math.exp(-days_since / 90), 4),
                        interaction_count=random.randint(1, 50),
                        last_interaction_at=last_interaction,
                        first_detected_at=last_interaction - timedelta(days=random.randint(1, 90)),
                        source=random.choice(["event_tracking", "purchase_history", "survey", "import"]),
                        is_active=True,
                        decay_factor=round(random.uniform(0.7, 1.0), 4),
                    )
                    session.add(ci)
                    interest_count += 1
            await session.flush()
            print(f"Customer interests: {interest_count} created.")
        else:
            print(f"Customer interests: {existing_interests} existing.")

        # ── 5. Segments ───────────────────────────────────────────
        seg_defs = [
            ("VIP","High-value loyal customers"), ("At Risk","Churn signals"),
            ("New","Acquired <30d"), ("Loyal","6m+ engagement"),
            ("High Spenders","Top 20% LTV"), ("Inactive","No activity 60d+"),
        ]
        seg_map = {}
        for name, desc in seg_defs:
            row = (await session.execute(
                text("SELECT id FROM customer_segments WHERE organization_id=:o AND name=:n").bindparams(o=ORG_ID, n=name)
            )).first()
            if row:
                seg_map[name] = row[0]
            else:
                sid = uuid.uuid4()
                await session.execute(
                    text("""INSERT INTO customer_segments (id, organization_id, name, description, source, is_active, is_dynamic, customer_count, created_at, updated_at)
                            VALUES (:id, :o, :n, :d, 'rule_based'::segment_source, true, true, 0, now(), now())""")
                    .bindparams(id=sid, o=ORG_ID, n=name, d=desc)
                )
                seg_map[name] = sid
        await session.flush()

        await session.execute(text("DELETE FROM customer_segment_mapping WHERE organization_id = :o").bindparams(o=ORG_ID))
        for cid, age in zip(cids, ages):
            names = set()
            if age < 60:
                names.add("New")
            if age > 90:
                names.add("Loyal")
            if random.random() > 0.7:
                names.add("VIP")
            if random.random() > 0.6:
                names.add("High Spenders")
            if random.random() > 0.5:
                names.add("At Risk")
            if age > 30 and random.random() > 0.7:
                names.add("Inactive")
            if not names:
                names.add("New")
            for n in names:
                if n in seg_map:
                    await session.execute(
                        text("""INSERT INTO customer_segment_mapping (customer_id, segment_id, organization_id, assigned_at, assigned_by, score)
                                VALUES (:c, :s, :o, :a, 'seed', :sc)""")
                        .bindparams(c=cid, s=seg_map[n], o=ORG_ID, a=NOW, sc=random.random())
                    )
        for sid in seg_map.values():
            cnt = (await session.execute(
                text("SELECT count(*) FROM customer_segment_mapping WHERE segment_id=:s").bindparams(s=sid)
            )).scalar() or 0
            await session.execute(
                text("UPDATE customer_segments SET customer_count=:c WHERE id=:s").bindparams(c=cnt, s=sid)
            )
        await session.flush()
        print(f"Segments: {len(seg_map)}, mappings created.")

        # ── 6. Twins ──────────────────────────────────────────────
        twin_new = 0
        for cid, age in zip(cids, ages):
            if (await session.execute(select(CustomerTwin).where(CustomerTwin.customer_id == cid))).scalar_one_or_none():
                continue
            eng = round(random.uniform(15, 98), 1)
            loy = round(random.uniform(10, 95), 1)
            total_ltv = round(random.uniform(100, 50000), 2)
            churn_p = round(random.uniform(0.01, 0.95), 3)
            sent = round(random.uniform(0.2, 0.95), 2)
            interest_names = random.sample(INTEREST_CATEGORIES, k=random.randint(3, 6))
            nodes = [{"name": n, "weight": round(random.uniform(0.3, 1.0), 3)} for n in interest_names]
            ca = {ch: round(random.uniform(0.0, 1.0), 2) for ch in CHANNELS + ["webhook"]}
            tl = min(age, 60)
            st = [round(sent + random.uniform(-0.15, 0.15), 3) for _ in range(tl)]

            purchase_cats = []
            for cat in random.sample(INTEREST_CATEGORIES, k=random.randint(1, 4)):
                purchase_cats.append({
                    "category": cat,
                    "count": random.randint(1, 15),
                    "total_value": round(random.uniform(50, 5000), 2),
                    "last_purchase_at": (NOW - timedelta(days=random.randint(0, age))).isoformat(),
                })
            channel_history = []
            for ch in random.sample(CHANNELS, k=random.randint(2, 4)):
                channel_history.append({
                    "channel": ch,
                    "count": random.randint(5, 100),
                    "last_interaction_at": (NOW - timedelta(days=random.randint(0, 30))).isoformat(),
                })
            campaign_responses = []
            for _ in range(random.randint(2, 8)):
                campaign_responses.append({
                    "campaign_id": str(uuid.uuid4()),
                    "event_type": random.choice(["email_open", "email_click", "purchase"]),
                    "channel": random.choice(CHANNELS),
                    "timestamp": (NOW - timedelta(days=random.randint(0, age))).isoformat(),
                })

            memory_profile = {
                "campaign_responses": campaign_responses,
                "purchase_categories": purchase_cats,
                "channel_history": channel_history,
                "discount_sensitivity": round(random.uniform(0.0, 0.8), 4),
                "historical_engagement": {
                    (NOW - timedelta(days=30 * i)).strftime("%Y-%m"): random.randint(5, 100)
                    for i in range(min(12, max(age // 30, 1)))
                },
                "seasonality_patterns": [
                    {"month": m, "count": random.randint(5, 50), "share": round(random.uniform(0.05, 0.15), 4)}
                    for m in ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
                ],
            }

            twin_output = {
                "sentiment": round(sum(st) / len(st), 4) if st else 0.0,
                "purchase_intent": round(1.0 - churn_p * 0.5, 4),
                "churn_probability": churn_p,
                "lifetime_value": total_ltv,
                "next_best_action": random.choice(["cross_sell", "upsell", "retention_offer", "re_engagement", "win_back"]),
            }

            twin = CustomerTwin(
                customer_id=cid, organization_id=ORG_ID, status="built", version=random.randint(1, 5),
                behavior_profile={
                    "behavior_score": round(eng / 100.0, 4),
                    "sub_scores": {
                        "engagement": round(eng / 100.0 * 0.8, 4),
                        "purchase_activity": round(random.uniform(0.2, 0.9), 4),
                        "session_depth": round(random.uniform(0.3, 0.8), 4),
                        "communication_response": round(random.uniform(0.1, 0.7), 4),
                        "recency": round(random.uniform(0.3, 1.0), 4),
                    },
                    "sessions_per_week": round(random.uniform(1, 15), 1),
                    "avg_session_duration": round(random.uniform(30, 600)),
                    "purchase_frequency": round(random.uniform(0.1, 5), 1),
                    "avg_order_value": round(random.uniform(20, 200), 2),
                    "cart_abandonment_rate": round(random.uniform(0.1, 0.7), 2),
                    "email_open_rate": round(random.uniform(0.2, 0.6), 2),
                    "email_click_rate": round(random.uniform(0.05, 0.3), 4),
                    "days_since_last_engagement": random.randint(0, 30),
                    "lifecycle_stage": random.choice(["engaged", "active", "loyal", "at_risk", "inactive"]),
                },
                interest_graph={"nodes": nodes, "dominant_category": nodes[0]["name"] if nodes else "",
                    "interest_diversity": round(random.uniform(0.3, 0.9), 2), "total_interactions": random.randint(10, 500)},
                memory_profile=memory_profile,
                channel_affinity=ca, engagement_score=eng, loyalty_score=loy, lifetime_value=total_ltv,
                sentiment_trend=st,
                intent_forecast={"purchase_intent_7d": round(random.uniform(0.1, 0.8), 2),
                    "churn_risk_7d": churn_p, "predicted_ltv_90d": round(total_ltv * random.uniform(1.1, 2.0), 2),
                    "recommended_action": random.choice(["upsell", "retention_discount", "re_engagement"]),
                    "recommended_channel": random.choice(["email", "sms", "push"])},
                risk_indicators={"churn_probability": churn_p, "current_sentiment": sent,
                    "churn_risk_level": "high" if churn_p > 0.5 else "medium" if churn_p > 0.25 else "low",
                    "churn_triggers": random.sample(["price_sensitivity", "low_engagement", "support_complaint"], k=random.randint(1, 2)),
                    "engagement_decline_rate": round(random.uniform(-0.3, 0.1), 2),
                    "negative_sentiment_count": random.randint(0, 10), "support_ticket_count": random.randint(0, 8)},
                communication_preferences={"email": True, "sms": random.random() > 0.5, "push": random.random() > 0.3},
                confidence_score=round(random.uniform(0.7, 0.99), 2), staleness_score=round(random.uniform(0.0, 0.4), 2),
                last_event_at=NOW - timedelta(hours=random.randint(1, 720)),
                built_at=NOW - timedelta(days=random.randint(0, min(age, 30))),
                twin_metadata={"model_version": "2.1.0", "build_source": "seed", "twin_output": twin_output},
            )
            session.add(twin)
            twin_new += 1
        await session.flush()
        print(f"Twins: {twin_new} new.")

        # ── 7. Events ─────────────────────────────────────────────
        ev_new = 0
        for cid, age in zip(cids, ages):
            cnt = (await session.execute(
                text("SELECT count(*) FROM customer_events WHERE customer_id=:c AND organization_id=:o")
                .bindparams(c=cid, o=ORG_ID)
            )).scalar()
            if cnt and cnt > 0:
                continue

            age_days = max(age, 30)
            num_events = random.randint(60, 150)

            purchase_intervals = sorted(random.sample(range(0, age_days), min(random.randint(3, 8), age_days)))

            for _ in range(num_events):
                days_offset = random.randint(0, age_days)
                ts = NOW - timedelta(days=days_offset, hours=random.randint(0, 23), minutes=random.randint(0, 59))

                # Choose event type with weighted distribution
                etype = random.choices(ALL_EVENT_TYPES, weights=[
                    8,   # purchase
                    20,  # page_view
                    12,  # email_sent
                    15,  # email_open
                    10,  # email_click
                    3,   # cart_abandon
                    3,   # bounce
                    1,   # unsubscribe
                    3,   # review_submit
                    2,   # feedback
                    2,   # positive_feedback
                    3,   # negative_feedback
                    1,   # complaint
                    2,   # support_ticket
                    1,   # support_resolved
                    2,   # survey_response
                    1,   # referral
                    2,   # return
                    5,   # session
                    8,   # search
                    8,   # app_open
                    10,  # login
                ])[0]

                channel = random.choice(CHANNELS)
                src = random.choice(["api", "system", "tracking"])
                device = random.choice(["desktop", "mobile", "tablet"])

                value = None
                if etype == "purchase":
                    value = round(random.uniform(10, 500), 2)
                elif etype == "return":
                    value = round(random.uniform(10, 300), 2)

                props = {}
                if etype == "purchase":
                    props = {
                        "value": value,
                        "currency": "USD",
                        "category": random.choice(INTEREST_CATEGORIES),
                        "discount_applied": random.random() > 0.7,
                    }
                elif etype in ("email_open", "email_click", "email_sent"):
                    props = {"campaign": random.choice(["summer_sale", "welcome", "promo", "vip_rewards"])}
                elif etype == "search":
                    props = {"query": random.choice(["laptop", "shoes", "books", "fitness", "phone", "camera"])}
                elif etype in ("feedback", "positive_feedback", "negative_feedback", "survey_response"):
                    props = {"rating": random.randint(1, 5), "source": random.choice(["email", "in_app", "web"])}
                elif etype in ("complaint", "support_ticket"):
                    props = {"category": random.choice(["billing", "shipping", "product_quality", "account"]),
                             "priority": random.choice(["low", "medium", "high"])}
                elif etype == "support_resolved":
                    props = {"resolution_time_hours": random.randint(1, 72), "satisfied": random.random() > 0.3}
                elif etype == "review_submit":
                    props = {"rating": random.randint(1, 5), "category": random.choice(INTEREST_CATEGORIES)}
                elif etype == "referral":
                    props = {"referral_count": random.randint(1, 3)}
                elif etype == "cart_abandon":
                    props = {"cart_value": round(random.uniform(20, 500), 2), "item_count": random.randint(1, 10)}

                await session.execute(
                    text("""INSERT INTO customer_events (organization_id, customer_id, event_type, event_name,
                            event_properties, context, channel, source, device_type, value, currency, event_timestamp, created_at)
                            VALUES (:o, :c, CAST(:et AS event_type), :en, CAST(:ep AS jsonb), '{}'::jsonb,
                            CAST(:ch AS notification_channel), :src, :dt, :val, :cur, :ts, now())""")
                    .bindparams(
                        o=ORG_ID, c=cid, et=etype, en=etype.replace("_", " ").title(),
                        ep=json.dumps(props), ch=channel, src=src, dt=device,
                        val=value, cur="USD" if value else None, ts=ts,
                    )
                )
                ev_new += 1

            # Add repeat purchase events for loyalty pattern
            for day_offset in purchase_intervals:
                ts = NOW - timedelta(days=day_offset)
                val = round(random.uniform(15, 400), 2)
                props = {
                    "value": val, "currency": "USD",
                    "category": random.choice(INTEREST_CATEGORIES),
                    "discount_applied": random.random() > 0.7,
                }
                await session.execute(
                    text("""INSERT INTO customer_events (organization_id, customer_id, event_type, event_name,
                            event_properties, context, channel, source, device_type, value, currency, event_timestamp, created_at)
                            VALUES (:o, :c, 'purchase'::event_type, 'Repeat Purchase',
                            CAST(:ep AS jsonb), '{}'::jsonb, 'email'::notification_channel, 'system', 'desktop',
                            :val, 'USD', :ts, now())""")
                    .bindparams(o=ORG_ID, c=cid, ep=json.dumps(props), val=val, ts=ts)
                )
                ev_new += 1
        print(f"Events: {ev_new} new.")

        # ── 8. Campaigns ──────────────────────────────────────────
        existing_camps = (await session.execute(
            text("SELECT count(*) FROM campaigns WHERE organization_id=:o").bindparams(o=ORG_ID)
        )).scalar()
        camp_ids = []
        if not existing_camps or existing_camps == 0:
            for name, ctype, ch, status, budget, start, end in [
                ("Summer Sale 2026", "promotional", "email", "completed", 15000, NOW - timedelta(days=45), NOW - timedelta(days=15)),
                ("VIP Loyalty Rewards", "loyalty", "email", "active", 8000, NOW - timedelta(days=7), NOW + timedelta(days=23)),
                ("New User Onboarding", "onboarding", "in_app", "draft", 3000, NOW + timedelta(days=5), NOW + timedelta(days=35)),
                ("Q3 Product Launch", "promotional", "push", "scheduled", 25000, NOW + timedelta(days=14), NOW + timedelta(days=44)),
                ("Holiday Flash Sale", "promotional", "sms", "draft", 10000, NOW + timedelta(days=60), NOW + timedelta(days=65)),
                ("Spring Clearance", "promotional", "email", "completed", 12000, NOW - timedelta(days=90), NOW - timedelta(days=60)),
                ("Referral Program", "referral", "email", "active", 5000, NOW - timedelta(days=14), NOW + timedelta(days=30)),
                ("Re-engagement Campaign", "retention", "push", "active", 7000, NOW - timedelta(days=5), NOW + timedelta(days=25)),
                ("Customer Feedback", "survey", "in_app", "completed", 3000, NOW - timedelta(days=30), NOW - timedelta(days=5)),
            ]:
                cid_ = uuid.uuid4()
                await session.execute(
                    text("""INSERT INTO campaigns (id, organization_id, name, type, channel, status, budget,
                            expected_reach, expected_conversion_rate, content, segments, target_customers,
                            start_at, end_at, frequency_cap, frequency_cap_period, created_at, updated_at)
                            VALUES (:id, :o, :n, :t, CAST(:ch AS notification_channel),
                            CAST(:st AS campaign_status), :b,
                            :er, :ecr, CAST(:ct AS jsonb), '[]'::jsonb, CAST(:tc AS text[]),
                            :sa, :ea, 3, 'day', now(), now())""")
                    .bindparams(
                        id=cid_, o=ORG_ID, n=name, t=ctype, ch=ch, st=status, b=budget,
                        er=random.randint(1000, 8000), ecr=round(random.uniform(0.05, 0.25), 2),
                        ct=json.dumps({"subject": name, "body": f"Check out {name}!"}),
                        tc=[str(c) for c in random.sample(cids, min(len(cids), random.randint(5, 10)))],
                        sa=start, ea=end,
                    )
                )
                camp_ids.append(cid_)

                if status in ("completed", "active"):
                    total = random.randint(1000, 5000)
                    delivered = int(total * random.uniform(0.85, 0.98))
                    opened = int(delivered * random.uniform(0.2, 0.5))
                    clicked = int(opened * random.uniform(0.1, 0.4))
                    converted = int(clicked * random.uniform(0.05, 0.2))
                    revenue = converted * random.uniform(20, 200)
                    await session.execute(
                        text("""INSERT INTO campaign_results (id, campaign_id, organization_id, total_targeted,
                                total_delivered, total_opened, total_clicked, total_converted, total_revenue,
                                total_cost, open_rate, click_rate, conversion_rate, roi, computed_at, created_at)
                                VALUES (:id, :c, :o, :tt, :td, :to, :tc_, :tconv, :tr, :tcost,
                                :or_, :cr, :convr, :roi, :now, now())""")
                        .bindparams(
                            id=uuid.uuid4(), c=cid_, o=ORG_ID,
                            tt=total, td=delivered, to=opened, tc_=clicked, tconv=converted,
                            tr=round(revenue, 2), tcost=float(budget),
                            or_=round(opened / max(delivered, 1), 4),
                            cr=round(clicked / max(delivered, 1), 4),
                            convr=round(converted / max(delivered, 1), 4),
                            roi=round((revenue - budget) / max(budget, 1), 4),
                            now=NOW,
                        )
                    )

            # Campaign participation: events that reference campaign_id
            for cid_ in cids:
                for camp_id in random.sample(camp_ids, min(len(camp_ids), random.randint(2, 5))):
                    for _ in range(random.randint(1, 4)):
                        ts = NOW - timedelta(days=random.randint(0, 60))
                        etype = random.choice(["email_open", "email_click", "purchase"])
                        await session.execute(
                            text("""INSERT INTO customer_events (organization_id, customer_id, event_type, event_name,
                                    event_properties, context, channel, source, device_type, campaign_id, event_timestamp, created_at)
                                    VALUES (:o, :c, CAST(:et AS event_type), :en, '{}'::jsonb, '{}'::jsonb,
                                    'email'::notification_channel, 'campaign', 'desktop', :camp_id, :ts, now())""")
                            .bindparams(o=ORG_ID, c=cid_, et=etype, en=etype.replace("_", " ").title(),
                                        camp_id=camp_id, ts=ts)
                        )
                        ev_new += 1

            await session.flush()
            print(f"Campaigns: {len(camp_ids)} created with results and participation events.")
        else:
            print(f"Already have {existing_camps} campaigns.")

        # ── 9. Predictions ────────────────────────────────────────
        existing_preds = (await session.execute(
            text("SELECT count(*) FROM customer_predictions WHERE organization_id=:o").bindparams(o=ORG_ID)
        )).scalar()
        if not existing_preds or existing_preds == 0:
            pred_count = 0
            for cid_ in cids:
                for ptype in ["churn", "ltv", "intent", "engagement", "next_best_action"]:
                    val_map = {
                        "churn": random.uniform(0.01, 0.95),
                        "ltv": random.uniform(100, 50000),
                        "intent": random.uniform(0.1, 0.9),
                        "engagement": random.uniform(0.1, 0.95),
                        "next_best_action": random.uniform(0, 1),
                    }
                    label_map = {
                        "churn": "high" if random.random() > 0.5 else "low",
                        "next_best_action": random.choice(["cross_sell", "upsell", "retention_offer", "re_engagement"]),
                    }
                    pred_val = val_map.get(ptype, 0.5)
                    pred_label = label_map.get(ptype)
                    p = Prediction(
                        customer_id=cid_, organization_id=ORG_ID,
                        prediction_type=ptype,
                        prediction_value=round(pred_val, 4),
                        prediction_probability=round(random.uniform(0.6, 0.98), 4),
                        prediction_label=pred_label,
                        prediction_explanation={
                            "top_features": random.sample(
                                ["engagement_score", "purchase_frequency", "recency", "sentiment", "ltv"],
                                k=3,
                            ),
                            "shap_values": [round(random.uniform(-0.2, 0.3), 4) for _ in range(3)],
                        },
                        feature_importance={
                            "engagement_score": round(random.uniform(0.1, 0.4), 4),
                            "purchase_frequency": round(random.uniform(0.1, 0.3), 4),
                            "recency": round(random.uniform(0.1, 0.3), 4),
                            "sentiment": round(random.uniform(0.05, 0.2), 4),
                        },
                        confidence_score=round(random.uniform(0.7, 0.99), 4),
                        model_version="2.1.0",
                        model_name=f"prometheus-{ptype}-v2",
                        input_features={
                            "engagement_score": round(random.uniform(0.1, 0.9), 4),
                            "purchase_frequency": round(random.uniform(0.1, 0.5), 4),
                            "recency_score": round(random.uniform(0.0, 1.0), 4),
                            "lifetime_value": round(random.uniform(100, 50000), 2),
                        },
                        valid_until=NOW + timedelta(days=random.randint(1, 30)),
                        is_active=True,
                    )
                    session.add(p)
                    pred_count += 1
            await session.flush()
            print(f"Predictions: {pred_count} created.")
        else:
            print(f"Predictions: {existing_preds} existing.")

        # ── 10. Completed simulations ─────────────────────────────
        existing_sims = (await session.execute(
            select(Simulation).where(Simulation.organization_id == ORG_ID, Simulation.status == "completed")
        )).scalars().all()
        if not existing_sims:
            seg_ids = [str(s) for s in seg_map.values()]
            for i, sname in enumerate(["Q3 Forecast", "Holiday Campaign Simulation", "Churn Reduction Model"]):
                base_rev = 50000 * (i + 1)
                sim = Simulation(organization_id=ORG_ID, name=sname, type="campaign", status="completed",
                    monte_carlo_iterations=5000, confidence_level=0.95, time_horizon_days=90,
                    parameters={"growth_rate": 0.05 * (i + 1), "seasonal_factor": 1.2},
                    segment_ids=seg_ids, sample_size=10000, include_control=True,
                    started_at=NOW - timedelta(days=10 + i * 5))
                session.add(sim)
                await session.flush()
                run = SimulationRun(simulation_id=sim.id, organization_id=ORG_ID, run_number=1,
                    status="completed", seed=random.randint(0, 2 ** 31 - 1), agents_count=100,
                    iterations_executed=5000, runtime_seconds=random.uniform(30, 300))
                session.add(run)
                await session.flush()
                result = SimulationResult(simulation_id=sim.id, organization_id=ORG_ID, run_id=run.id,
                    aggregated_metrics={"expected_revenue": base_rev, "conversion_rate": round(0.04 + 0.03 * i, 3),
                        "sensitivity": [{"variable": "price", "impact": round(random.uniform(-0.3, -0.1), 2)},
                            {"variable": "ad_spend", "impact": round(random.uniform(0.1, 0.3), 2)},
                            {"variable": "seasonality", "impact": round(random.uniform(0.05, 0.2), 2)}]},
                    customer_projections={"total": 10000, "reach": 7500},
                    segment_projections={s: {"reach": random.randint(100, 2000)} for s in [d[0] for d in seg_defs]},
                    campaign_impact={"incremental_revenue": round(base_rev * 0.15, 2), "roi": round(random.uniform(1.5, 4.0), 2)},
                    confidence_intervals={"revenue": [round(base_rev * 0.85, 2), round(base_rev * 1.15, 2)],
                        "conversions": [round(7500 * 0.04 * 0.85), round(7500 * 0.04 * 1.15)]},
                    monte_carlo_distribution={"best_case": {"revenue": round(base_rev * 1.3, 2), "conversions": 450},
                        "most_likely": {"revenue": base_rev, "conversions": 300},
                        "worst_case": {"revenue": round(base_rev * 0.6, 2), "conversions": 150}},
                    expected_outcomes={"expected_revenue": base_rev, "expected_conversions": 300 + i * 50,
                        "expected_open_rate": round(0.25 + 0.05 * i, 2), "expected_click_rate": round(0.06 + 0.02 * i, 2)},
                    risk_assessment={"level": random.choice(["low", "medium", "high"]),
                        "factors": random.sample(["Market volatility", "New competitor", "Seasonal demand", "Rising CAC"], k=random.randint(2, 3))},
                    recommendations=[f"Adjust pricing {i}", f"Target segment {i}"])
                session.add(result)
            await session.flush()
            print("3 completed simulations created.")
        else:
            print(f"Already have {len(existing_sims)} completed simulations.")

        # ── 11. Revenue metrics ──────────────────────────────────
        existing_metrics = (await session.execute(text("SELECT count(*) FROM metrics WHERE key='revenue_daily'"))).scalar()
        if not existing_metrics or existing_metrics == 0:
            exp_id = (await session.execute(text("SELECT experiment_id FROM experiments LIMIT 1"))).scalar()
            if exp_id:
                run_u = str(uuid.uuid4())[:32]
                await session.execute(
                    text("INSERT INTO runs (run_uuid, experiment_id, name, source_type, status, start_time, artifact_uri) "
                         "VALUES (:u, :e, 'Seed Revenue', 'LOCAL', 'FINISHED', :t, '/tmp/mlflow')")
                    .bindparams(u=run_u, e=exp_id, t=int(NOW.timestamp()))
                )
                base = 80000
                for day_offset in range(90):
                    d = NOW - timedelta(days=89 - day_offset)
                    daily = base + random.randint(-10000, 15000) + day_offset * 200
                    await session.execute(
                        text("INSERT INTO metrics (key, value, timestamp, run_uuid) VALUES ('revenue_daily', :v, :ts, :ru)")
                        .bindparams(v=float(daily), ts=int(d.timestamp()), ru=run_u)
                    )
                print("90 days of revenue metrics created.")
            else:
                print("No experiment found — skipping metrics.")
        else:
            print("Revenue metrics already exist.")

        await session.commit()
        print("\n=== Seed complete! ===")
        print(f"  Customers: {len(customers)}")
        print(f"  Events: {ev_new} new")
        print(f"  Campaigns: {len(camp_ids)}" if camp_ids else "  Campaigns: existing")
        print(f"  Twins: {twin_new} new")


if __name__ == "__main__":
    asyncio.run(seed())
