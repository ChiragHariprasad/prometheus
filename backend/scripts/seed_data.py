"""Comprehensive seed script — populates ALL tables for the PROMETHEUS app.

Creates:
  - 20 new customers (for ~32 total with existing)
  - 10 years of events (2016–2026) per customer
  - 6 segments with customer mappings
  - 10+ campaigns with results
  - 5+ simulations with runs and results
  - Customer twins with proper interest_graph & sentiment_trend

Usage:  cd backend && python -m scripts.seed_data
"""

import asyncio
import json
import uuid
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from app.core.database import async_session_factory, engine

ORG_ID = uuid.UUID("885f9275-ad3b-4fc4-92fb-550dde803fb7")
NOW = datetime.now(timezone.utc)

FIRST_NAMES = [
    "Mia", "Liam", "Olivia", "Noah", "Emma", "Oliver", "Ava", "Elijah",
    "Sophia", "Mateo", "Isabella", "Sebastian", "Luna", "James", "Harper",
    "Benjamin", "Evelyn", "Lucas", "Camila", "Gianna",
]
LAST_NAMES = [
    "Anderson", "Thomson", "Clark", "Lewis", "Walker", "Hall", "Allen",
    "Young", "King", "Wright", "Hill", "Scott", "Green", "Adams", "Baker",
    "Nelson", "Carter", "Mitchell", "Perez", "Turner",
]

EVENT_TYPES = [
    "purchase", "page_view", "email_sent", "email_open", "email_click",
    "cart_abandon", "bounce", "unsubscribe", "review_submit", "feedback",
    "positive_feedback", "negative_feedback", "complaint", "support_ticket",
    "support_resolved", "survey_response", "referral", "return", "session",
    "search", "app_open", "login",
]
CHANNELS = ["email", "sms", "push", "in_app", "webhook"]
SOURCES = ["api", "system", "tracking"]
DEVICES = ["desktop", "mobile", "tablet"]

INTEREST_CATEGORIES = [
    "Electronics", "Fashion", "Sports", "Travel", "Books",
    "Gaming", "Finance", "Health", "Automotive", "Home",
]

SEGMENT_DEFS = [
    ("VIP", "High-value loyal customers"),
    ("At Risk", "Churn signals detected"),
    ("New", "Acquired within 30 days"),
    ("Loyal", "6+ months continuous engagement"),
    ("High Spenders", "Top 20% by lifetime value"),
    ("Inactive", "No activity for 60+ days"),
]

CAMPAIGN_DEFS = [
    ("Summer Sale 2026", "promotional", "email", "completed"),
    ("VIP Loyalty Rewards", "loyalty", "email", "active"),
    ("New User Onboarding", "onboarding", "in_app", "draft"),
    ("Q3 Product Launch", "promotional", "push", "scheduled"),
    ("Holiday Flash Sale", "promotional", "sms", "draft"),
    ("Spring Clearance", "promotional", "email", "completed"),
    ("Referral Program", "referral", "email", "active"),
    ("Re-engagement Campaign", "retention", "push", "active"),
    ("Black Friday 2026", "promotional", "sms", "scheduled"),
    ("Customer Feedback", "survey", "in_app", "completed"),
    ("Birthday Rewards", "loyalty", "email", "draft"),
    ("Cross-sell Initiative", "upsell", "push", "draft"),
]

SIMULATION_DEFS = [
    ("Q3 2026 Forecast", 5000, 0.95, 90),
    ("Holiday Campaign ROI", 3000, 0.90, 60),
    ("Churn Reduction Model", 8000, 0.95, 120),
    ("New Customer Acquisition", 4000, 0.90, 45),
    ("Pricing Sensitivity Analysis", 6000, 0.95, 30),
    ("Product Launch Impact", 5000, 0.90, 90),
]


async def create_partitions(sql_session):
    """Create yearly event partitions for 2016–2025."""
    for year in range(2016, 2026):
        start = f"{year}-01-01"
        end = f"{year+1}-01-01"
        name = f"customer_events_{year}"
        try:
            await sql_session.execute(text(
                f"CREATE TABLE IF NOT EXISTS {name} PARTITION OF customer_events "
                f"FOR VALUES FROM ('{start}') TO ('{end}')"
            ))
        except Exception:
            pass  # may already exist
    # Extend default partition to cover 2016 if needed
    # The existing default covers 2027–2030, so we need a catch-all for pre-2026 too
    try:
        await sql_session.execute(text(
            "CREATE TABLE IF NOT EXISTS customer_events_legacy PARTITION OF customer_events "
            "FOR VALUES FROM ('2015-01-01') TO ('2016-01-01')"
        ))
    except Exception:
        pass
    await sql_session.commit()


async def seed():
    print("Creating event partitions for 2016–2025...")
    async with engine.begin() as conn:
        await conn.execute(text("SET app.current_org_id = '00000000-0000-0000-0000-000000000000'"))
        await create_partitions(conn)

    async with async_session_factory() as session:
        await session.execute(text("SET app.current_org_id = '00000000-0000-0000-0000-000000000000'"))

        # ── 0. Ensure judge user exists ────────────────────────
        judge = (await session.execute(
            text("SELECT id FROM users WHERE email = 'judge@texpedition.com' LIMIT 1")
        )).first()
        if not judge:
            from app.core.security import hash_password
            admin_role = (await session.execute(
                text("SELECT id FROM roles WHERE organization_id = :o AND name = 'Admin' LIMIT 1"),
                {"o": ORG_ID},
            )).first()
            if not admin_role:
                rid = uuid.uuid4()
                await session.execute(text(
                    "INSERT INTO roles (id, organization_id, name, description, is_system, priority, created_at) "
                    "VALUES (:id, :o, 'Admin', 'Administrator', true, 100, :now)"
                ), {"id": rid, "o": ORG_ID, "now": NOW})
                admin_role_ = rid
            else:
                admin_role_ = admin_role[0]

            judge_id = uuid.uuid4()
            pwh = hash_password("pass@123")
            await session.execute(text(
                "INSERT INTO users (id, organization_id, email, password_hash, first_name, last_name, is_active, is_verified, password_changed_at, created_at, updated_at) "
                "VALUES (:id, :o, 'judge@texpedition.com', :pwh, 'Judge', 'User', true, true, :now, :now, :now)"
            ), {"id": judge_id, "o": ORG_ID, "pwh": pwh, "now": NOW})
            await session.execute(text(
                "INSERT INTO user_roles (user_id, role_id, assigned_at) VALUES (:uid, :rid, :now)"
            ), {"uid": judge_id, "rid": admin_role_, "now": NOW})
            print("  Judge user created.")
        else:
            print("  Judge user exists.")

        # ── 1. Customers ──────────────────────────────────────
        existing = (await session.execute(
            text("SELECT id, first_name, last_name FROM customers WHERE organization_id = :o ORDER BY created_at"),
            {"o": ORG_ID},
        )).all()
        existing_cids = [r[0] for r in existing]
        print(f"  Existing customers: {len(existing_cids)}")

        new_customers = []
        start_idx = len(existing_cids)
        for i in range(start_idx, start_idx + 20):
            fname = FIRST_NAMES[i % len(FIRST_NAMES)]
            lname = LAST_NAMES[i % len(LAST_NAMES)]
            cid = uuid.uuid4()
            days_ago = random.randint(1, 3650)  # up to 10 years
            created = NOW - timedelta(days=days_ago)
            await session.execute(text("""
                INSERT INTO customers (id, organization_id, external_id, email, phone, first_name, last_name, timezone, locale, location, tags, is_active, consent_marketing, consent_analytics, consent_profiling, source, first_seen_at, last_seen_at, created_at, updated_at)
                VALUES (:id, :o, :ext, :email, :phone, :fn, :ln, :tz, 'en-US', CAST(:loc AS jsonb), :tags, true, :cm, true, :cp, :src, :fs, :ls, :now, :now)
            """), {
                "id": cid, "o": ORG_ID,
                "ext": f"ext-{i:04d}",
                "email": f"{fname.lower()}.{lname.lower()}{i}@example.com",
                "phone": f"+1-555-{random.randint(100,999)}-{random.randint(1000,9999)}",
                "fn": fname, "ln": lname,
                "tz": random.choice(["US/Eastern", "US/Pacific", "US/Central", "Europe/London", "Asia/Tokyo"]),
                "loc": json.dumps({"city": random.choice(["NYC","LA","Chicago","Houston","Seattle","Denver"]), "country": "US"}),
                "tags": random.sample(["newsletter", "loyalty", "premium", "beta", "vip"], k=random.randint(1, 3)),
                "cm": random.random() > 0.2,
                "cp": random.random() > 0.3,
                "src": random.choice(["api", "web", "mobile", "import"]),
                "fs": created,
                "ls": created + timedelta(days=random.randint(0, min(days_ago, 365))),
                "now": NOW,
            })
            new_customers.append(cid)
        await session.flush()
        print(f"  Created {len(new_customers)} new customers.")

        all_cids = existing_cids + new_customers
        print(f"  Total customers: {len(all_cids)}")

        # ── 2. Segments ───────────────────────────────────────
        seg_map = {}
        for name, desc in SEGMENT_DEFS:
            row = (await session.execute(
                text("SELECT id FROM customer_segments WHERE organization_id=:o AND name=:n LIMIT 1"),
                {"o": ORG_ID, "n": name},
            )).first()
            if row:
                seg_map[name] = row[0]
            else:
                sid = uuid.uuid4()
                await session.execute(text("""
                    INSERT INTO customer_segments (id, organization_id, name, description, source, is_active, is_dynamic, customer_count, created_at, updated_at)
                    VALUES (:id, :o, :n, :d, CAST('rule_based' AS segment_source), true, true, 0, :now, :now)
                """), {"id": sid, "o": ORG_ID, "n": name, "d": desc, "now": NOW})
                seg_map[name] = sid
        await session.flush()

        # Assign customers to segments
        await session.execute(
            text("DELETE FROM customer_segment_mapping WHERE organization_id = :o"),
            {"o": ORG_ID},
        )
        from app.models.customer import Customer
        from sqlalchemy import select
        db_customers = (await session.execute(
            select(Customer).where(Customer.organization_id == ORG_ID)
        )).scalars().all()
        for c in db_customers:
            age = (NOW - (c.first_seen_at or NOW)).days
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
                    await session.execute(text("""
                        INSERT INTO customer_segment_mapping (customer_id, segment_id, organization_id, assigned_at, assigned_by, score)
                        VALUES (:c, :s, :o, :now, 'seed', :sc)
                    """), {"c": c.id, "s": seg_map[n], "o": ORG_ID, "now": NOW, "sc": random.random()})
        # Update counts
        for sid in seg_map.values():
            cnt = (await session.execute(
                text("SELECT count(*) FROM customer_segment_mapping WHERE segment_id=:s"),
                {"s": sid},
            )).scalar() or 0
            await session.execute(
                text("UPDATE customer_segments SET customer_count=:c WHERE id=:s"),
                {"c": cnt, "s": sid},
            )
        await session.flush()
        print(f"  Segments: {len(seg_map)}, mappings assigned.")

        # ── 3. Twins ──────────────────────────────────────────
        twin_count = 0
        for c in db_customers:
            existing_twin = (await session.execute(
                text("SELECT id FROM customer_twins WHERE customer_id=:c AND organization_id=:o LIMIT 1"),
                {"c": c.id, "o": ORG_ID},
            )).first()
            if existing_twin:
                continue

            age_days = max((NOW - (c.first_seen_at or NOW)).days, 1)
            eng = round(random.uniform(15, 98), 1)
            loy = round(random.uniform(10, 95), 1)
            ltv = round(random.uniform(100, 50000), 2)
            churn_p = round(random.uniform(0.01, 0.95), 3)
            sent = round(random.uniform(0.2, 0.95), 2)

            interest_names = random.sample(
                ["Electronics", "Fashion", "Sports", "Books", "Music", "Travel", "Food", "Fitness", "Gaming", "Home"],
                k=random.randint(3, 6),
            )
            nodes = [{"name": n, "weight": round(random.uniform(0.3, 1.0), 3)} for n in interest_names]

            ca = {ch: round(random.uniform(0.0, 1.0), 2) for ch in ["email", "sms", "push", "in_app", "webhook"]}

            tl = min(age_days, 60)
            st = [round(sent + random.uniform(-0.15, 0.15), 3) for _ in range(tl)]

            purchase_cats = []
            for cat in random.sample(INTEREST_CATEGORIES, k=random.randint(1, 4)):
                purchase_cats.append({
                    "category": cat, "count": random.randint(1, 15),
                    "total_value": round(random.uniform(50, 5000), 2),
                    "last_purchase_at": (NOW - timedelta(days=random.randint(0, age_days))).isoformat(),
                })
            channel_history = []
            for ch in random.sample(CHANNELS, k=random.randint(2, 4)):
                channel_history.append({
                    "channel": ch, "count": random.randint(5, 100),
                    "last_interaction_at": (NOW - timedelta(days=random.randint(0, 30))).isoformat(),
                })
            campaign_responses = []
            for _ in range(random.randint(2, 8)):
                campaign_responses.append({
                    "campaign_id": str(uuid.uuid4()),
                    "event_type": random.choice(["email_open", "email_click", "purchase"]),
                    "channel": random.choice(CHANNELS),
                    "timestamp": (NOW - timedelta(days=random.randint(0, age_days))).isoformat(),
                })
            memory_profile = {
                "campaign_responses": campaign_responses,
                "purchase_categories": purchase_cats,
                "channel_history": channel_history,
                "discount_sensitivity": round(random.uniform(0.0, 0.8), 4),
                "historical_engagement": {
                    (NOW - timedelta(days=30 * i)).strftime("%Y-%m"): random.randint(5, 100)
                    for i in range(min(12, max(age_days // 30, 1)))
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
                "lifetime_value": ltv,
                "next_best_action": random.choice(["cross_sell", "upsell", "retention_offer", "re_engagement", "win_back"]),
            }

            twin_id = uuid.uuid4()
            await session.execute(text("""
                INSERT INTO customer_twins (id, customer_id, organization_id, status, version, behavior_profile, interest_graph, memory_profile, channel_affinity, engagement_score, loyalty_score, lifetime_value, sentiment_trend, intent_forecast, risk_indicators, communication_preferences, confidence_score, staleness_score, twin_metadata, last_event_at, built_at, created_at, updated_at)
                VALUES (:id, :cid, :o, CAST('built' AS twin_status), :ver, CAST(:bp AS jsonb), CAST(:ig AS jsonb), CAST(:mem AS jsonb), CAST(:ca AS jsonb), :eng, :loy, :ltv, :st, CAST(:intent AS jsonb), CAST(:risk AS jsonb), CAST(:prefs AS jsonb), :conf, :stale, CAST(:meta AS jsonb), :le, :built, :now, :now)
            """), {
                "id": twin_id, "cid": c.id, "o": ORG_ID,
                "ver": random.randint(1, 5),
                "bp": json.dumps({
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
                    "lifecycle_stage": random.choice(["engaged", "active", "loyal", "at_risk", "inactive"]),
                }),
                "ig": json.dumps({
                    "nodes": nodes,
                    "dominant_category": nodes[0]["name"],
                    "interest_diversity": round(random.uniform(0.3, 0.9), 2),
                    "total_interactions": random.randint(10, 500),
                }),
                "mem": json.dumps(memory_profile),
                "ca": json.dumps(ca),
                "eng": eng, "loy": loy, "ltv": ltv,
                "st": st,
                "intent": json.dumps({
                    "purchase_intent_7d": round(random.uniform(0.1, 0.8), 2),
                    "churn_risk_7d": churn_p,
                    "predicted_ltv_90d": round(ltv * random.uniform(1.1, 2.0), 2),
                    "recommended_action": random.choice(["upsell", "retention_discount", "re_engagement"]),
                    "recommended_channel": random.choice(["email", "sms", "push"]),
                }),
                "risk": json.dumps({
                    "churn_probability": churn_p,
                    "current_sentiment": sent,
                    "churn_risk_level": "high" if churn_p > 0.5 else "medium" if churn_p > 0.25 else "low",
                    "engagement_decline_rate": round(random.uniform(-0.3, 0.1), 2),
                    "negative_sentiment_count": random.randint(0, 10),
                    "support_ticket_count": random.randint(0, 8),
                }),
                "prefs": json.dumps({"email": True, "sms": random.random() > 0.5, "push": random.random() > 0.3}),
                "conf": round(random.uniform(0.7, 0.99), 2),
                "stale": round(random.uniform(0.0, 0.4), 2),
                "meta": json.dumps({"model_version": "2.1.0", "build_source": "seed", "twin_output": twin_output}),
                "le": NOW - timedelta(hours=random.randint(1, 720)),
                "built": NOW - timedelta(days=random.randint(0, min(age_days, 30))),
                "now": NOW,
            })
            twin_count += 1
        await session.flush()
        print(f"  Twins: {twin_count} new, {len(db_customers) - twin_count} existing.")

        # ── 4. Events (10 years: 2016–2026) ───────────────────
        ev_count = 0
        for cid in all_cids:
            existing_ev = (await session.execute(
                text("SELECT count(*) FROM customer_events WHERE customer_id=:c AND organization_id=:o"),
                {"c": cid, "o": ORG_ID},
            )).scalar()
            if existing_ev and existing_ev > 0:
                continue

            # Generate events across 10 years
            years_active = random.randint(3, 10)
            base_date = NOW - timedelta(days=365 * years_active)
            num_events = random.randint(200, 800)

            for _ in range(num_events):
                days_offset = random.randint(0, years_active * 365)
                ts = base_date + timedelta(
                    days=days_offset,
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59),
                )
                if ts > NOW:
                    continue
                etype = random.choice(EVENT_TYPES)
                channel = random.choice(CHANNELS)
                src = random.choice(SOURCES)
                device = random.choice(DEVICES)
                value = round(random.uniform(5, 500), 2) if etype in ("purchase", "return") else None

                props = {}
                if etype == "purchase":
                    props = {"value": value, "currency": "USD", "category": random.choice(INTEREST_CATEGORIES), "discount_applied": random.random() > 0.7}
                elif etype == "return":
                    props = {"value": value, "currency": "USD", "reason": random.choice(["defective", "not_wanted", "wrong_item"])}
                elif etype in ("email_sent", "email_open", "email_click"):
                    props = {"campaign": random.choice(["summer_sale", "welcome", "promo", "vip_rewards"])}
                elif etype == "search":
                    props = {"query": random.choice(["laptop", "shoes", "books", "fitness", "phone", "camera"])}
                elif etype in ("feedback", "positive_feedback", "negative_feedback", "survey_response"):
                    props = {"rating": random.randint(1, 5), "source": random.choice(["email", "in_app", "web"])}
                elif etype in ("complaint", "support_ticket"):
                    props = {"category": random.choice(["billing", "shipping", "product_quality", "account"]), "priority": random.choice(["low", "medium", "high"])}
                elif etype == "support_resolved":
                    props = {"resolution_time_hours": random.randint(1, 72), "satisfied": random.random() > 0.3}
                elif etype == "review_submit":
                    props = {"rating": random.randint(1, 5), "category": random.choice(INTEREST_CATEGORIES)}
                elif etype == "referral":
                    props = {"referral_count": random.randint(1, 3)}
                elif etype == "cart_abandon":
                    props = {"cart_value": round(random.uniform(20, 500), 2), "item_count": random.randint(1, 10)}

                await session.execute(text("""
                    INSERT INTO customer_events (organization_id, customer_id, event_type, event_name, event_properties, context, channel, source, device_type, value, currency, event_timestamp, ingested_at, created_at)
                    VALUES (:o, :c, CAST(:et AS event_type), :en, CAST(:props AS jsonb), '{}'::jsonb, :ch, :src, :dev, :val, :cur, :ts, :now, :now)
                """), {
                    "o": ORG_ID, "c": cid,
                    "et": etype,
                    "en": etype.replace("_", " ").title(),
                    "props": json.dumps(props),
                    "ch": channel,
                    "src": src,
                    "dev": device,
                    "val": value,
                    "cur": "USD" if value else None,
                    "ts": ts,
                    "now": NOW,
                })
                ev_count += 1
        await session.flush()
        print(f"  Events: {ev_count} new.")

        # ── 5. Campaigns ──────────────────────────────────────
        camp_count = 0
        for name, ctype, channel, status in CAMPAIGN_DEFS:
            existing_camp = (await session.execute(
                text("SELECT id FROM campaigns WHERE organization_id=:o AND name=:n LIMIT 1"),
                {"o": ORG_ID, "n": name},
            )).first()
            if existing_camp:
                continue

            budget = random.randint(3000, 50000)
            start_offset = {"draft": 60, "scheduled": 14, "active": -7, "completed": -45}.get(status, 0)
            duration = random.randint(14, 45)
            start_at = NOW + timedelta(days=start_offset)
            end_at = start_at + timedelta(days=duration)

            camp_id = uuid.uuid4()
            tz = random.choice(["US/Eastern", "US/Pacific", "Europe/London"])
            await session.execute(text("""
                INSERT INTO campaigns (id, organization_id, name, type, goal, status, channel, segments, target_customers, content, schedule, budget, expected_reach, expected_conversion_rate, start_at, end_at, created_at, updated_at)
                VALUES (:id, :o, :n, :t, :g, CAST(:st AS campaign_status), CAST(:ch AS notification_channel), CAST(:seg AS jsonb), :tc, CAST(:ct AS jsonb), CAST(:sched AS jsonb), :b, :er, :ecr, :sa, :ea, :now, :now)
            """), {
                "id": camp_id, "o": ORG_ID, "n": name, "t": ctype,
                "g": f"Drive {ctype} results via {channel}",
                "st": status, "ch": channel,
                "seg": json.dumps([]),
                "tc": [str(c) for c in random.sample(all_cids, min(len(all_cids), random.randint(5, 20)))],
                "ct": json.dumps({"subject": name, "body": f"Check out {name}!"}),
                "sched": json.dumps({
                    "start": start_at.isoformat(),
                    "end": end_at.isoformat(),
                    "frequency": random.choice(["daily", "weekly", "monthly"]),
                    "timezone": tz,
                }),
                "b": budget,
                "er": random.randint(500, 10000),
                "ecr": round(random.uniform(0.03, 0.25), 2),
                "sa": start_at, "ea": end_at,
                "now": NOW,
            })

            # Create campaign results for completed/active campaigns
            if status in ("completed", "active"):
            # see if result exists
                existing_result = (await session.execute(
                    text("SELECT id FROM campaign_results WHERE campaign_id=:c LIMIT 1"),
                    {"c": camp_id},
                )).first()
                if not existing_result:
                    total = random.randint(1000, 8000)
                    delivered = int(total * random.uniform(0.85, 0.98))
                    opened = int(delivered * random.uniform(0.2, 0.5))
                    clicked = int(opened * random.uniform(0.1, 0.4))
                    converted = int(clicked * random.uniform(0.05, 0.2))
                    revenue = converted * random.uniform(20, 200)
                    cost = budget or 3000
                    await session.execute(text("""
                        INSERT INTO campaign_results (id, campaign_id, organization_id, total_targeted, total_delivered, total_opened, total_clicked, total_converted, total_revenue, total_cost, open_rate, click_rate, conversion_rate, roi, computed_at, created_at)
                        VALUES (:id, :c, :o, :tt, :td, :to, :tc_, :tconv, :tr, :tcost, :or_, :cr, :convr, :roi, :now, :now)
                    """), {
                        "id": uuid.uuid4(), "c": camp_id, "o": ORG_ID,
                        "tt": total, "td": delivered, "to": opened,
                        "tc_": clicked, "tconv": converted, "tr": round(revenue, 2),
                        "tcost": round(float(cost), 2),
                        "or_": round(opened / delivered, 4) if delivered else 0,
                        "cr": round(clicked / delivered, 4) if delivered else 0,
                        "convr": round(converted / delivered, 4) if delivered else 0,
                        "roi": round((revenue - cost) / cost, 4) if cost else 0,
                        "now": NOW,
                    })
            camp_count += 1
        await session.flush()
        print(f"  Campaigns: {camp_count} new.")

        # ── 6. Simulations ────────────────────────────────────
        sim_count = 0
        all_seg_ids = [str(s) for s in seg_map.values()]
        for name, iterations, confidence, horizon in SIMULATION_DEFS:
            existing_sim = (await session.execute(
                text("SELECT id FROM simulations WHERE organization_id=:o AND name=:n LIMIT 1"),
                {"o": ORG_ID, "n": name},
            )).first()
            if existing_sim:
                continue

            base_rev = random.randint(30000, 150000)
            sim_id = uuid.uuid4()
            await session.execute(text("""
                INSERT INTO simulations (id, organization_id, name, type, status, monte_carlo_iterations, confidence_level, time_horizon_days, segment_ids, sample_size, include_control, parameters, started_at, completed_at, created_at, updated_at)
                VALUES (:id, :o, :n, 'campaign', CAST('completed' AS simulation_status), :iter, :conf, :horizon, :sids, :sample, true, CAST(:params AS jsonb), :started, :completed, :now, :now)
            """), {
                "id": sim_id, "o": ORG_ID, "n": name,
                "iter": iterations, "conf": confidence, "horizon": horizon,
                "sids": all_seg_ids,
                "sample": 10000,
                "params": json.dumps({
                    "growth_rate": round(random.uniform(0.02, 0.08), 3),
                    "seasonal_factor": round(random.uniform(1.0, 1.3), 2),
                }),
                "started": NOW - timedelta(days=random.randint(5, 30)),
                "completed": NOW - timedelta(days=random.randint(0, 4)),
                "now": NOW,
            })

            # Run
            run_id = uuid.uuid4()
            await session.execute(text("""
                INSERT INTO simulation_runs (id, simulation_id, organization_id, run_number, status, seed, agents_count, iterations_executed, runtime_seconds, created_at)
                VALUES (:id, :sid, :o, 1, 'completed', :seed, :agents, :iter, :rt, :now)
            """), {
                "id": run_id, "sid": sim_id, "o": ORG_ID,
                "seed": random.randint(0, 2**31 - 1),
                "agents": 100,
                "iter": iterations,
                "rt": round(random.uniform(30, 300), 2),
                "now": NOW,
            })

            # Result
            conv_rate = round(random.uniform(0.03, 0.08), 3)
            await session.execute(text("""
                INSERT INTO simulation_results (id, simulation_id, organization_id, run_id, aggregated_metrics, customer_projections, segment_projections, campaign_impact, confidence_intervals, monte_carlo_distribution, expected_outcomes, risk_assessment, recommendations, created_at)
                VALUES (:id, :sid, :o, :rid, CAST(:agg AS jsonb), CAST(:cp AS jsonb), CAST(:sp AS jsonb), CAST(:ci AS jsonb), CAST(:confint AS jsonb), CAST(:mcd AS jsonb), CAST(:eo AS jsonb), CAST(:ra AS jsonb), :rec, :now)
            """), {
                "id": uuid.uuid4(), "sid": sim_id, "o": ORG_ID, "rid": run_id,
                "rec": ["Adjust pricing tiers", "Increase ad spend on high-performing channels"],
                "agg": json.dumps({
                    "expected_revenue": base_rev,
                    "conversion_rate": conv_rate,
                    "sensitivity": [
                        {"variable": "price", "impact": round(random.uniform(-0.3, -0.1), 2)},
                        {"variable": "ad_spend", "impact": round(random.uniform(0.1, 0.3), 2)},
                        {"variable": "seasonality", "impact": round(random.uniform(0.05, 0.2), 2)},
                    ],
                }),
                "cp": json.dumps({"total": 10000, "reach": 7500}),
                "sp": json.dumps({s: {"reach": random.randint(100, 2000)} for s, _ in SEGMENT_DEFS}),
                "ci": json.dumps({
                    "incremental_revenue": round(base_rev * 0.15, 2),
                    "roi": round(random.uniform(1.5, 4.0), 2),
                }),
                "confint": json.dumps({
                    "revenue": [round(base_rev * 0.85, 2), round(base_rev * 1.15, 2)],
                    "conversions": [round(7500 * conv_rate * 0.85), round(7500 * conv_rate * 1.15)],
                }),
                "mcd": json.dumps({
                    "best_case": {"revenue": round(base_rev * 1.3, 2), "conversions": 450},
                    "most_likely": {"revenue": base_rev, "conversions": 300},
                    "worst_case": {"revenue": round(base_rev * 0.6, 2), "conversions": 150},
                }),
                "eo": json.dumps({
                    "expected_revenue": base_rev,
                    "expected_conversions": 300,
                    "expected_open_rate": round(random.uniform(0.2, 0.4), 2),
                    "expected_click_rate": round(random.uniform(0.05, 0.12), 2),
                }),
                "ra": json.dumps({
                    "level": random.choice(["low", "medium", "high"]),
                    "factors": random.sample(
                        ["Market volatility", "New competitor", "Seasonal demand", "Rising CAC"],
                        k=random.randint(2, 3),
                    ),
                }),
                "now": NOW,
            })
            sim_count += 1
        await session.flush()
        print(f"  Simulations: {sim_count} new.")

        await session.commit()
        print("\n=== Seed complete! ===")
        print(f"  Customers: {len(all_cids)} total")
        print(f"  Events: {ev_count} new")
        print(f"  Campaigns: {camp_count}")
        print(f"  Simulations: {sim_count}")


if __name__ == "__main__":
    asyncio.run(seed())
