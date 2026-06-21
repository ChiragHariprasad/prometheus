"""Seed comprehensive demo data into the PROMETHEUS org.

Usage:  cd backend && python seed_data.py
"""

import asyncio
import uuid
import random
import json
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, text
from app.core.database import async_session_factory, engine
from app.models.customer import Customer
from app.models.twin import CustomerTwin
from app.models.campaign import Campaign
from app.models.simulation import Simulation, SimulationResult, SimulationRun

ORG_ID = uuid.UUID("eb35c0b4-f66b-442b-b35a-30246d8df683")
NOW = datetime.now(timezone.utc)

FIRST_NAMES = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Hank", "Iris", "Jack", "Kate", "Leo"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]


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

        # ── 2. Segments ───────────────────────────────────────────
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
            names = []
            if age < 60:
                names.append("New")
            if age > 90:
                names.append("Loyal")
            if random.random() > 0.7:
                names.append("VIP")
            if random.random() > 0.6:
                names.append("High Spenders")
            if random.random() > 0.5:
                names.append("At Risk")
            if age > 30 and random.random() > 0.7:
                names.append("Inactive")
            if not names:
                names.append("New")
            for n in names:
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

        # ── 3. Twins ──────────────────────────────────────────────
        twin_new = 0
        for cid, age in zip(cids, ages):
            if (await session.execute(select(CustomerTwin).where(CustomerTwin.customer_id == cid))).scalar_one_or_none():
                continue
            eng = round(random.uniform(15,98), 1)
            loy = round(random.uniform(10,95), 1)
            ltv = round(random.uniform(100,50000), 2)
            churn_p = round(random.uniform(0.01,0.95), 3)
            sent = round(random.uniform(0.2,0.95), 2)
            interests = random.sample(["Electronics","Fashion","Sports","Books","Music","Travel","Food","Fitness","Gaming"], k=random.randint(3,6))
            nodes = [{"name":n,"weight":round(random.uniform(0.3,1.0),3)} for n in interests]
            ca = {ch: round(random.uniform(0.0,1.0),2) for ch in ["email","sms","push","in_app","webhook"]}
            tl = min(age, 60)
            st = [round(sent + random.uniform(-0.15,0.15),3) for _ in range(tl)]
            twin = CustomerTwin(
                customer_id=cid, organization_id=ORG_ID, status="active", version=random.randint(1,5),
                behavior_profile={"sessions_per_week": round(random.uniform(1,15),1),
                    "avg_session_duration": round(random.uniform(30,600)),
                    "purchase_frequency": round(random.uniform(0.1,5),1),
                    "avg_order_value": round(random.uniform(20,200),2),
                    "cart_abandonment_rate": round(random.uniform(0.1,0.7),2),
                    "email_open_rate": round(random.uniform(0.2,0.6),2)},
                interest_graph={"nodes": nodes, "dominant_category": nodes[0]["name"] if nodes else "",
                    "interest_diversity": round(random.uniform(0.3,0.9),2), "total_interactions": random.randint(10,500)},
                channel_affinity=ca, engagement_score=eng, loyalty_score=loy, lifetime_value=ltv,
                sentiment_trend=st,
                intent_forecast={"purchase_intent_7d": round(random.uniform(0.1,0.8),2),
                    "churn_risk_7d": churn_p, "predicted_ltv_90d": round(ltv*random.uniform(1.1,2.0),2),
                    "recommended_action": random.choice(["upsell","retention_discount","re_engagement"]),
                    "recommended_channel": random.choice(["email","sms","push"])},
                risk_indicators={"churn_probability": churn_p, "current_sentiment": sent,
                    "churn_risk_level": "high" if churn_p>0.5 else "medium" if churn_p>0.25 else "low",
                    "churn_triggers": random.sample(["price_sensitivity","low_engagement","support_complaint"],k=random.randint(1,2)),
                    "engagement_decline_rate": round(random.uniform(-0.3,0.1),2),
                    "negative_sentiment_count": random.randint(0,10), "support_ticket_count": random.randint(0,8)},
                communication_preferences={"email":True,"sms":random.random()>0.5,"push":random.random()>0.3},
                confidence_score=round(random.uniform(0.7,0.99),2), staleness_score=round(random.uniform(0.0,0.4),2),
                last_event_at=NOW-timedelta(hours=random.randint(1,720)),
                built_at=NOW-timedelta(days=random.randint(0,min(age,30))),
                twin_metadata={"model_version":"2.1.0","build_source":"seed"},
            )
            session.add(twin)
            twin_new += 1
        await session.flush()
        print(f"Twins: {twin_new} new.")

        # ── 4. Events ─────────────────────────────────────────────
        ev_new = 0
        etypes = ["page_view","purchase","email_open","email_click","session","add_to_cart","search","login","app_open","review_submit"]
        for cid in cids:
            cnt = (await session.execute(
                text("SELECT count(*) FROM customer_events WHERE customer_id=:c AND organization_id=:o")
                .bindparams(c=cid,o=ORG_ID)
            )).scalar()
            if cnt and cnt > 0:
                continue
            for _ in range(random.randint(15,40)):
                ts = NOW - timedelta(days=random.randint(0,90), hours=random.randint(0,23), minutes=random.randint(0,59))
                etype = random.choice(etypes)
                channel = random.choice(["email","sms","push","in_app","webhook"])
                src = random.choice(["api","system","tracking"])
                dt = random.choice(["desktop","mobile","tablet"])
                await session.execute(
                    text("""INSERT INTO customer_events (organization_id, customer_id, event_type, event_name,
                            event_properties, context, channel, source, device_type, event_timestamp, created_at)
                            VALUES (:o, :c, CAST(:et AS event_type), :en, CAST(:ep AS jsonb), '{}'::jsonb,
                            CAST(:ch AS notification_channel), :src, :dt, :ts, now())""")
                    .bindparams(o=ORG_ID, c=cid, et=etype, en=etype,
                        ep='{"value":' + str(round(random.uniform(5,500),2)) + '}',
                        ch=channel, src=src, dt=dt, ts=ts)
                )
                ev_new += 1
        print(f"Events: {ev_new} new.")

        # ── 5. Campaigns ──────────────────────────────────────────
        existing_camps = (await session.execute(
            text("SELECT count(*) FROM campaigns WHERE organization_id=:o").bindparams(o=ORG_ID)
        )).scalar()
        if not existing_camps or existing_camps == 0:
            for name, ctype, ch, status, budget, start, end in [
                ("Summer Sale 2026","promotional","email","completed",15000, NOW-timedelta(days=45), NOW-timedelta(days=15)),
                ("VIP Loyalty Rewards","loyalty","email","active",8000, NOW-timedelta(days=7), NOW+timedelta(days=23)),
                ("New User Onboarding","onboarding","in_app","draft",3000, NOW+timedelta(days=5), NOW+timedelta(days=35)),
                ("Q3 Product Launch","promotional","push","scheduled",25000, NOW+timedelta(days=14), NOW+timedelta(days=44)),
                ("Holiday Flash Sale","promotional","sms","draft",10000, NOW+timedelta(days=60), NOW+timedelta(days=65)),
            ]:
                await session.execute(
                    text("""INSERT INTO campaigns (organization_id, name, type, channel, status, budget,
                            expected_reach, expected_conversion_rate, content, segments, target_customers,
                            start_at, end_at, frequency_cap, frequency_cap_period, created_at, updated_at)
                            VALUES (:o, :n, :t, CAST(:ch AS notification_channel),
                            CAST(:st AS campaign_status), :b,
                            :er, :ecr, CAST(:ct AS jsonb), '[]'::jsonb, CAST(:tc AS text[]),
                            :sa, :ea, 3, 'day', now(), now())""")
                    .bindparams(o=ORG_ID, n=name, t=ctype, ch=ch, st=status, b=budget,
                        er=random.randint(1000,8000), ecr=round(random.uniform(0.05,0.25),2),
                        ct=json.dumps({"subject":name,"body":f"Check out {name}!"}),
                        tc=[str(c) for c in cids[:8]], sa=start, ea=end)
                )
            await session.flush()
            print("5 campaigns created.")
        else:
            print(f"Already have {existing_camps} campaigns.")

        # ── 6. Completed simulations ─────────────────────────────
        existing_sims = (await session.execute(
            select(Simulation).where(Simulation.organization_id == ORG_ID, Simulation.status == "completed")
        )).scalars().all()
        if not existing_sims:
            seg_ids = [str(s) for s in seg_map.values()]
            for i, sname in enumerate(["Q3 Forecast","Holiday Campaign Simulation","Churn Reduction Model"]):
                base_rev = 50000 * (i + 1)
                sim = Simulation(organization_id=ORG_ID, name=sname, type="campaign", status="completed",
                    monte_carlo_iterations=5000, confidence_level=0.95, time_horizon_days=90,
                    parameters={"growth_rate":0.05*(i+1),"seasonal_factor":1.2},
                    segment_ids=seg_ids, sample_size=10000, include_control=True,
                    started_at=NOW-timedelta(days=10+i*5))
                session.add(sim)
                await session.flush()
                run = SimulationRun(simulation_id=sim.id, organization_id=ORG_ID, run_number=1,
                    status="completed", seed=random.randint(0,2**31-1), agents_count=100,
                    iterations_executed=5000, runtime_seconds=random.uniform(30,300))
                session.add(run)
                await session.flush()
                result = SimulationResult(simulation_id=sim.id, organization_id=ORG_ID, run_id=run.id,
                    aggregated_metrics={"expected_revenue":base_rev,"conversion_rate":round(0.04+0.03*i,3),
                        "sensitivity":[{"variable":"price","impact":round(random.uniform(-0.3,-0.1),2)},
                            {"variable":"ad_spend","impact":round(random.uniform(0.1,0.3),2)},
                            {"variable":"seasonality","impact":round(random.uniform(0.05,0.2),2)}]},
                    customer_projections={"total":10000,"reach":7500},
                    segment_projections={s:{"reach":random.randint(100,2000)} for s in [d[0] for d in seg_defs]},
                    campaign_impact={"incremental_revenue":round(base_rev*0.15,2),"roi":round(random.uniform(1.5,4.0),2)},
                    confidence_intervals={"revenue":[round(base_rev*0.85,2),round(base_rev*1.15,2)],
                        "conversions":[round(7500*0.04*0.85),round(7500*0.04*1.15)]},
                    monte_carlo_distribution={"best_case":{"revenue":round(base_rev*1.3,2),"conversions":450},
                        "most_likely":{"revenue":base_rev,"conversions":300},
                        "worst_case":{"revenue":round(base_rev*0.6,2),"conversions":150}},
                    expected_outcomes={"expected_revenue":base_rev,"expected_conversions":300+i*50,
                        "expected_open_rate":round(0.25+0.05*i,2),"expected_click_rate":round(0.06+0.02*i,2)},
                    risk_assessment={"level":random.choice(["low","medium","high"]),
                        "factors":random.sample(["Market volatility","New competitor","Seasonal demand","Rising CAC"],k=random.randint(2,3))},
                    recommendations=[f"Adjust pricing {i}",f"Target segment {i}"])
                session.add(result)
            await session.flush()
            print("3 completed simulations created.")
        else:
            print(f"Already have {len(existing_sims)} completed simulations.")

        # ── 7. Revenue metrics ────────────────────────────────────
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


if __name__ == "__main__":
    asyncio.run(seed())
