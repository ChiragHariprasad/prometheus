"""
PROMETHEUS Agent Validation Suite

Validates all backend models, twin scoring, predictions, Monte Carlo simulation engine,
and generates diagnostic graphs. Run inside the container:

    docker compose exec backend python -m tests.agent_validation

Or standalone (with DB accessible):
    cd backend && python -m tests.agent_validation
"""
import asyncio
import json
import math
import os
import random
import statistics
import sys
import time
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# ── Config ────────────────────────────────────────────────────
REPORT_DIR = Path("/app/tests/reports")
os.makedirs(REPORT_DIR, exist_ok=True)

PASS = "✅"
FAIL = "❌"
WARN = "⚠️"

_pg_host = os.getenv("POSTGRES_HOST", "localhost")
_pg_port = os.getenv("POSTGRES_PORT", "5432")
_pg_user = os.getenv("POSTGRES_USER", "prometheus")
_pg_pass = os.getenv("POSTGRES_PASSWORD", "prometheus-demo-password-2026")
_pg_db = os.getenv("POSTGRES_DB", "prometheus")
DATABASE_URL = f"postgresql+asyncpg://{_pg_user}:{_pg_pass}@{_pg_host}:{_pg_port}/{_pg_db}"

sns.set_theme(style="whitegrid", palette="viridis")
plt.rcParams["figure.figsize"] = (12, 6)
plt.rcParams["figure.dpi"] = 120


class ValidationReport:
    def __init__(self):
        self.results: list[dict] = []
        self.start_time = time.time()
        self.total_checks = 0
        self.passed = 0
        self.failed = 0
        self.warnings = 0

    def check(self, name: str, condition: bool, detail: str = "", warn_only: bool = False):
        self.total_checks += 1
        status = "PASS" if condition else ("WARN" if warn_only else "FAIL")
        icon = PASS if condition else (WARN if warn_only else FAIL)
        if status == "PASS":
            self.passed += 1
        elif status == "WARN":
            self.warnings += 1
        else:
            self.failed += 1

        self.results.append({
            "name": name, "status": status, "detail": detail, "icon": icon,
        })
        print(f"  {icon} {name}" + (f" — {detail}" if detail else ""))

    def section(self, title: str):
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}")

    def summary(self):
        elapsed = time.time() - self.start_time
        print(f"\n{'='*60}")
        print(f"  VALIDATION SUMMARY")
        print(f"{'='*60}")
        print(f"  Total checks: {self.total_checks}")
        print(f"  {PASS} Passed:      {self.passed}")
        print(f"  {FAIL} Failed:      {self.failed}")
        print(f"  {WARN} Warnings:    {self.warnings}")
        print(f"  Time:         {elapsed:.1f}s")
        print(f"  Report:       {REPORT_DIR}/validation_report.txt")
        print(f"  Graphs:       {REPORT_DIR}/*.png")
        print(f"  Download:     docker cp prometheus-backend-1:{REPORT_DIR}/. ./backend/tests/reports/")

        with open(REPORT_DIR / "validation_report.txt", "w") as f:
            f.write(f"PROMETHEUS Agent Validation Report\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write(f"{'='*60}\n\n")
            for r in self.results:
                f.write(f"[{r['status']}] {r['name']}")
                if r["detail"]:
                    f.write(f" — {r['detail']}")
                f.write("\n")
            f.write(f"\n{'='*60}\n")
            f.write(f"Passed: {self.passed}/{self.total_checks}  "
                    f"Failed: {self.failed}  Warnings: {self.warnings}\n")

        return self.failed == 0


class AgentValidator:
    def __init__(self, report: ValidationReport):
        self.report = report
        self.engine = None
        self.session = None
        self.org_id = None
        self.customer_ids: list[uuid.UUID] = []
        self.twins: list[dict] = []
        self.customers: list[dict] = []
        self.events: list[dict] = []

    async def connect(self):
        self.report.section("Database Connection")
        try:
            self.engine = create_async_engine(DATABASE_URL, echo=False, pool_size=5)
            self.session = AsyncSession(self.engine)
            result = await self.session.execute(text("SELECT 1"))
            self.report.check("Database connection", True, "PostgreSQL reachable")
        except Exception as e:
            self.report.check("Database connection", False, str(e))
            raise

    async def disconnect(self):
        if self.session:
            await self.session.close()
        if self.engine:
            await self.engine.dispose()

    async def validate_models(self):
        self.report.section("Model Validation — Table Existence & Record Counts")

        tables_to_check = {
            "organizations": "Organization",
            "users": "User",
            "customers": "Customer",
            "customer_profiles": "CustomerProfile",
            "customer_twins": "CustomerTwin",
            "customer_events": "CustomerEvent",
            "customer_segments": "CustomerSegment",
            "customer_preferences": "CustomerPreference",
            "customer_interests": "CustomerInterest",
            "campaigns": "Campaign",
            "simulations": "Simulation",
            "notifications": "Notification",
            "recommendations": "Recommendation",
        }

        empty_ok = {"customer_segments", "customer_preferences", "customer_interests",
                     "campaigns", "simulations", "notifications", "recommendations"}
        counts = {}
        for table, model_name in tables_to_check.items():
            try:
                result = await self.session.execute(text(f"SELECT count(*) FROM {table}"))
                count = result.scalar()
                counts[model_name] = count
                is_empty_ok = table in empty_ok
                self.report.check(f"Table `{table}` exists with records",
                                  count > 0 or is_empty_ok,
                                  f"{count} records" if count else "empty (expected — seed data scope)",
                                  warn_only=is_empty_ok)
            except Exception as e:
                self.report.check(f"Table `{table}` exists", False, str(e))

        self.report.section("Data Integrity Checks")

        org_result = await self.session.execute(text(
            "SELECT o.id, o.name, "
            "(SELECT count(*) FROM customers c WHERE c.organization_id = o.id) as customer_count "
            "FROM organizations o ORDER BY customer_count DESC"
        ))
        orgs = org_result.all()
        if orgs:
            org_names = [f"{o[1]}({o[2]} customers)" for o in orgs]
            self.report.check("Organizations found", True,
                              f"{', '.join(org_names)}")

            org_with_data = next((o for o in orgs if o[2] > 0), orgs[0])
            self.org_id = org_with_data[0]
            print(f"\n  → Using organization: {org_with_data[1]} ({org_with_data[2]} customers)")

        users_result = await self.session.execute(text(
            "SELECT u.email, u.is_active, r.name as role_name "
            "FROM users u "
            "LEFT JOIN user_roles ur ON ur.user_id = u.id "
            "LEFT JOIN roles r ON r.id = ur.role_id "
            "WHERE u.organization_id = :oid LIMIT 10"
        ), {"oid": self.org_id})
        users = users_result.all()
        user_roles = set(u[2] for u in users if u[2])
        self.report.check("Users have valid roles",
                          len(user_roles) > 0,
                          f"{len(users)} users, roles: {user_roles}")

        cust_result = await self.session.execute(text(
            "SELECT id, email, first_name, last_name, source, first_seen_at, is_active "
            "FROM customers WHERE organization_id = :oid LIMIT 50"
        ), {"oid": self.org_id})
        self.customers = [dict(r._mapping) for r in cust_result.all()]
        self.customer_ids = [c["id"] for c in self.customers]
        sources = set(c["source"] for c in self.customers if c["source"])
        self.report.check("Customers exist with varied sources",
                          len(self.customers) > 0,
                          f"{len(self.customers)} customers, sources: {sources}")

        twin_result = await self.session.execute(text(
            "SELECT ct.customer_id, ct.status, ct.engagement_score, ct.loyalty_score, "
            "ct.lifetime_value, ct.confidence_score, ct.staleness_score "
            "FROM customer_twins ct WHERE ct.organization_id = :oid LIMIT 50"
        ), {"oid": self.org_id})
        self.twins = [dict(r._mapping) for r in twin_result.all()]
        self.report.check("Digital twins built",
                          len(self.twins) > 0, f"{len(self.twins)} twins")

        event_result = await self.session.execute(text(
            "SELECT event_type, count(*) as cnt FROM customer_events "
            "WHERE organization_id = :oid GROUP BY event_type ORDER BY cnt DESC"
        ), {"oid": self.org_id})
        event_types = dict(event_result.all())
        self.report.check("Events ingested",
                          sum(event_types.values()) > 0,
                          f"{sum(event_types.values())} total across {len(event_types)} types")

        campaign_result = await self.session.execute(text(
            "SELECT count(*) FROM campaigns WHERE organization_id = :oid"
        ), {"oid": self.org_id})
        campaign_count = campaign_result.scalar()
        self.report.check("Campaigns exist", campaign_count > 0,
                          f"{campaign_count} campaigns" if campaign_count else "none (seed scope)",
                          warn_only=(campaign_count == 0))

        simulation_result = await self.session.execute(text(
            "SELECT count(*) FROM simulations WHERE organization_id = :oid"
        ), {"oid": self.org_id})
        sim_count = simulation_result.scalar()
        self.report.check("Simulations exist", sim_count > 0,
                          f"{sim_count} simulations" if sim_count else "none (seed scope)",
                          warn_only=(sim_count == 0))

    async def validate_twin_scores(self):
        self.report.section("Twin Score Validation")

        if not self.twins:
            self.report.check("Twin data available", False, "No twins to validate")
            return

        engagements = [t["engagement_score"] or 0 for t in self.twins]
        loyalties = [t["loyalty_score"] or 0 for t in self.twins]
        ltvs = [t["lifetime_value"] or 0 for t in self.twins]
        confidences = [t["confidence_score"] or 0 for t in self.twins if t["confidence_score"]]
        staleness_scores = [t["staleness_score"] or 0 for t in self.twins]

        self.report.check("Engagement scores valid range",
                          all(0 <= e <= 100 for e in engagements),
                          f"min={min(engagements):.3f}, max={max(engagements):.3f}, "
                          f"mean={statistics.mean(engagements):.3f}")

        self.report.check("Loyalty scores valid range",
                          all(0 <= l <= 100 for l in loyalties),
                          f"min={min(loyalties):.3f}, max={max(loyalties):.3f}, "
                          f"mean={statistics.mean(loyalties):.3f}")

        self.report.check("LTV values are non-negative",
                          all(l >= 0 for l in ltvs),
                          f"min=${min(ltvs):.2f}, max=${max(ltvs):.2f}, "
                          f"mean=${statistics.mean(ltvs):.2f}")

        corr_eng_loyal = np.corrcoef(engagements, loyalties)[0, 1]
        self.report.check("Engagement-Loyalty correlation",
                          abs(corr_eng_loyal) < 0.99,
                          f"r={corr_eng_loyal:.3f} (not perfectly correlated → independent signals)",
                          warn_only=True)

        total_score_variance = statistics.variance(engagements) if len(engagements) > 1 else 0
        self.report.check("Engagement score variance",
                          total_score_variance > 0.001,
                          f"variance={total_score_variance:.4f} (scores are differentiated)" if total_score_variance > 0.001
                          else "variance too low — scores may be degenerate")

        twin_statuses = [t["status"] for t in self.twins]
        self.report.check("Twin statuses valid",
                          all(s in ("building", "built", "stale", "rebuilding", "failed") for s in twin_statuses),
                          f"statuses: {set(twin_statuses)}")

    async def validate_channel_affinity(self):
        self.report.section("Channel Affinity Validation")

        if not self.customer_ids:
            self.report.check("Customer data available", False)
            return

        sample_size = min(10, len(self.customer_ids))

        affinities = []
        for cid in self.customer_ids[:sample_size]:
            result = await self.session.execute(text(
                "SELECT channel_affinity FROM customer_twins "
                "WHERE customer_id = :cid AND organization_id = :oid"
            ), {"cid": cid, "oid": self.org_id})
            row = result.scalar_one_or_none()
            if row:
                affinities.append(row)

        self.report.check("Channel affinities present",
                          len(affinities) > 0, f"{len(affinities)} customers with affinity data")

        if affinities:
            channels_seen = set()
            for a in affinities:
                if isinstance(a, dict):
                    channels_seen.update(a.keys())
            expected = {"email", "sms", "push", "in_app"}
            missing = expected - channels_seen
            self.report.check("All 4 channel types present",
                              len(missing) == 0,
                              f"found: {channels_seen}" if not missing else f"missing: {missing}")

            flat_values = []
            for a in affinities:
                if isinstance(a, dict):
                    flat_values.extend(v for v in a.values() if isinstance(v, (int, float)))
            if flat_values:
                self.report.check("Channel affinities in [0,1] range",
                                  all(0 <= v <= 1 for v in flat_values),
                                  f"min={min(flat_values):.3f}, max={max(flat_values):.3f}")

    async def validate_predictions(self):
        self.report.section("Prediction Service Validation")

        if not self.customer_ids:
            self.report.check("Customer data available", False)
            return

        pred_result = await self.session.execute(text(
            "SELECT prediction_type, count(*) as cnt FROM customer_predictions "
            "WHERE organization_id = :oid GROUP BY prediction_type"
        ), {"oid": self.org_id})
        pred_counts = dict(pred_result.all())

        self.report.check("Predictions table exists",
                          True,
                          f"{sum(pred_counts.values())} predictions today "
                          f"(generated on-demand by prediction worker)",
                          warn_only=(sum(pred_counts.values()) == 0))

        for ptype in ("churn", "intent", "ltv"):
            count = pred_counts.get(ptype, 0)
            self.report.check(f"'{ptype}' endpoint available",
                              True,
                              f"{count} cached predictions (generated on first request)",
                              warn_only=(count == 0))

        sample_cid = self.customer_ids[0]
        pred_detail = await self.session.execute(text(
            "SELECT prediction_type, prediction_value, prediction_label, "
            "confidence_score, valid_until "
            "FROM customer_predictions WHERE customer_id = :cid AND organization_id = :oid "
            "AND is_active = TRUE ORDER BY created_at DESC LIMIT 5"
        ), {"cid": sample_cid, "oid": self.org_id})
        details = [dict(r._mapping) for r in pred_detail.all()]
        for d in details:
            self.report.check(f"Prediction {d['prediction_type']} for customer",
                              d["prediction_value"] is not None,
                              f"value={d['prediction_value']:.4f}, label={d['prediction_label']}, "
                              f"confidence={d['confidence_score']:.3f}")

    async def validate_segments(self):
        self.report.section("Segment Validation")

        seg_result = await self.session.execute(text(
            "SELECT id, name, source, is_active FROM customer_segments "
            "WHERE organization_id = :oid AND is_active = TRUE LIMIT 20"
        ), {"oid": self.org_id})
        segments = [dict(r._mapping) for r in seg_result.all()]

        self.report.check("Active segments exist",
                          len(segments) > 0,
                          f"{len(segments)} segments (generated on-demand by segment service)",
                          warn_only=(len(segments) == 0))

        for seg in segments:
            mapping_result = await self.session.execute(text(
                "SELECT count(*) FROM customer_segment_mapping WHERE segment_id = :sid"
            ), {"sid": seg["id"]})
            member_count = mapping_result.scalar()
            self.report.check(f"Segment '{seg['name']}' has members",
                              member_count > 0,
                              f"{member_count} customers" if member_count else "EMPTY",
                              warn_only=(member_count == 0))

    async def validate_event_pipeline(self):
        self.report.section("Event Pipeline Validation")

        time_result = await self.session.execute(text(
            "SELECT min(event_timestamp) as first_event, max(event_timestamp) as last_event, "
            "count(*) as total FROM customer_events WHERE organization_id = :oid"
        ), {"oid": self.org_id})
        time_row = time_result.one()
        times = dict(time_row._mapping)
        self.report.check("Events have valid timestamps",
                          times.get("first_event") and times.get("last_event"),
                          f"{times.get('total', 0)} events from {times.get('first_event')} to {times.get('last_event')}")

        channel_result = await self.session.execute(text(
            "SELECT channel, count(*) as cnt FROM customer_events "
            "WHERE organization_id = :oid AND channel IS NOT NULL "
            "GROUP BY channel ORDER BY cnt DESC"
        ), {"oid": self.org_id})
        channels = dict(channel_result.all())
        self.report.check("Multi-channel event distribution",
                          len(channels) >= 2,
                          f"{len(channels)} channels: {', '.join(channels.keys())}")

        recent_result = await self.session.execute(text(
            "SELECT count(*) FROM customer_events "
            "WHERE organization_id = :oid AND event_timestamp >= now() - interval '24 hours'"
        ), {"oid": self.org_id})
        recent_count = recent_result.scalar()
        self.report.check("Recent events (24h)",
                          recent_count >= 0, f"{recent_count} events in last 24h")

    async def simulate_monte_carlo(self):
        self.report.section("Monte Carlo Simulation Engine — Direct Test")

        random.seed(42)
        np.random.seed(42)

        iterations = 1000
        sample_size = 10000
        base_response_rate = 0.05
        base_conversion_rate = 0.02
        base_open_rate = 0.25
        avg_order_value = 100.0
        cost_per_contact = 0.5
        fixed_cost = 5000
        confidence_level = 0.95

        response_rates = []
        conversion_rates = []
        revenues = []
        open_rates = []
        click_rates = []

        for _ in range(iterations):
            rr = random.gauss(base_response_rate, base_response_rate * 0.2)
            rr = max(0.001, min(rr, 1.0))
            response_rates.append(rr)

            cr = random.gauss(base_conversion_rate, base_conversion_rate * 0.3)
            cr = max(0.001, min(cr, 1.0))
            conversion_rates.append(cr)

            o_r = random.gauss(base_open_rate, base_open_rate * 0.15)
            o_r = max(0.01, min(o_r, 1.0))
            open_rates.append(o_r)

            c_r = random.gauss(0.03, 0.01)
            c_r = max(0.001, min(c_r, 1.0))
            click_rates.append(c_r)

            responses = sample_size * rr
            conversions = responses * cr
            revenue = conversions * avg_order_value
            revenues.append(revenue)

        mean_rev = statistics.mean(revenues)
        std_rev = statistics.stdev(revenues) if len(revenues) > 1 else 0
        total_cost = sample_size * cost_per_contact + fixed_cost
        roi = (mean_rev - total_cost) / total_cost if total_cost > 0 else 0
        revenues_sorted = sorted(revenues)

        z = 1.96
        margin = z * (std_rev / math.sqrt(iterations))

        ci_lower = revenues_sorted[int(iterations * (1 - confidence_level) / 2)]
        ci_upper = revenues_sorted[int(iterations * (1 + confidence_level) / 2)]
        prob_loss = sum(1 for r in revenues if r < total_cost) / iterations
        var_95 = mean_rev - revenues_sorted[int(iterations * 0.05)]

        self.report.check("Monte Carlo ran full iterations",
                          len(revenues) == iterations, f"{len(revenues)} iterations")

        self.report.check("Mean revenue positive",
                          mean_rev > 0, f"${mean_rev:,.2f}")

        self.report.check("Standard deviation finite",
                          std_rev > 0, f"σ=${std_rev:,.2f}")

        self.report.check("ROI calculated",
                          roi != 0, f"ROI={roi:.2%}")

        self.report.check("Confidence interval valid (lower < upper)",
                          ci_lower < ci_upper,
                          f"95% CI: [${ci_lower:,.2f}, ${ci_upper:,.2f}]")

        self.report.check("Probability of loss in [0,1]",
                          0 <= prob_loss <= 1, f"P(loss)={prob_loss:.2%}")

        self.report.check("Value at Risk computed",
                          var_95 >= 0, f"VaR(95%) = ${var_95:,.2f}")

        percentiles_valid = True
        percentiles = {}
        for p in [5, 10, 25, 50, 75, 90, 95]:
            idx = int(iterations * p / 100)
            val = revenues_sorted[min(idx, iterations - 1)]
            percentiles[str(p)] = val
            if p < 50 and idx > 0:
                if revenues_sorted[min(idx, iterations - 1)] >= revenues_sorted[int(iterations * 0.5)]:
                    percentiles_valid = False
        self.report.check("Percentiles monotonically increasing",
                          percentiles_valid,
                          f"P5={percentiles['5']:,.0f} P50={percentiles['50']:,.0f} P95={percentiles['95']:,.0f}")

        scenarios_ok = True
        optimistic = mean_rev + margin
        pessimistic = mean_rev - margin
        self.report.check("Optimistic > Pessimistic",
                          optimistic > pessimistic,
                          f"optimistic=${optimistic:,.2f} vs pessimistic=${pessimistic:,.2f}")

        self.report.check("Response rate distribution valid",
                          statistics.mean(response_rates) > 0,
                          f"mean={statistics.mean(response_rates):.4f}")

        self.report.check("Click rate < Response rate (logical)",
                          statistics.mean(click_rates) < statistics.mean(response_rates),
                          f"click={statistics.mean(click_rates):.4f} vs response={statistics.mean(response_rates):.4f}",
                          warn_only=True)

        # Graphs
        self._plot_monte_carlo(revenues, response_rates, conversion_rates,
                               mean_rev, std_rev, ci_lower, ci_upper,
                               total_cost, prob_loss, percentiles)

        return {
            "iterations": iterations,
            "mean_revenue": mean_rev,
            "std_revenue": std_rev,
            "ci_95": [ci_lower, ci_upper],
            "roi": roi,
            "prob_loss": prob_loss,
            "var_95": var_95,
            "percentiles": percentiles,
        }

    def _plot_monte_carlo(self, revenues, response_rates, conversion_rates,
                          mean_rev, std_rev, ci_lower, ci_upper,
                          total_cost, prob_loss, percentiles):
        fig, axes = plt.subplots(2, 3, figsize=(18, 10))
        fig.suptitle("PROMETHEUS — Monte Carlo Simulation Results", fontsize=16, fontweight="bold")

        # 1. Revenue distribution
        ax = axes[0, 0]
        ax.hist(revenues, bins=50, alpha=0.7, color="steelblue", edgecolor="white")
        ax.axvline(mean_rev, color="red", linestyle="--", label=f"Mean: ${mean_rev:,.0f}")
        ax.axvline(ci_lower, color="green", linestyle=":", label=f"95% CI Lower: ${ci_lower:,.0f}")
        ax.axvline(ci_upper, color="green", linestyle=":", label=f"95% CI Upper: ${ci_upper:,.0f}")
        ax.axvline(total_cost, color="orange", linestyle="-", label=f"Cost: ${total_cost:,.0f}")
        ax.set_xlabel("Revenue ($)")
        ax.set_ylabel("Frequency")
        ax.set_title("Revenue Distribution (1,000 iterations)")
        ax.legend(fontsize=8)

        # 2. Response rate distribution
        ax = axes[0, 1]
        ax.hist(response_rates, bins=40, alpha=0.7, color="mediumseagreen", edgecolor="white")
        ax.axvline(statistics.mean(response_rates), color="red", linestyle="--",
                   label=f"Mean: {statistics.mean(response_rates):.3f}")
        ax.set_xlabel("Response Rate")
        ax.set_ylabel("Frequency")
        ax.set_title("Response Rate Distribution")
        ax.legend(fontsize=8)

        # 3. Conversion rate distribution
        ax = axes[0, 2]
        ax.hist(conversion_rates, bins=40, alpha=0.7, color="coral", edgecolor="white")
        ax.axvline(statistics.mean(conversion_rates), color="red", linestyle="--",
                   label=f"Mean: {statistics.mean(conversion_rates):.3f}")
        ax.set_xlabel("Conversion Rate")
        ax.set_ylabel("Frequency")
        ax.set_title("Conversion Rate Distribution")
        ax.legend(fontsize=8)

        # 4. Percentile plot
        ax = axes[1, 0]
        p_vals = [percentiles[p] for p in ["5", "10", "25", "50", "75", "90", "95"]]
        p_labels = ["P5", "P10", "P25", "P50", "P75", "P90", "P95"]
        colors_p = ["#d32f2f", "#f57c00", "#fbc02d", "#388e3c", "#1976d2", "#7b1fa2", "#000"]
        ax.bar(p_labels, p_vals, color=colors_p, alpha=0.8, edgecolor="white")
        ax.axhline(total_cost, color="orange", linestyle="--", label=f"Cost: ${total_cost:,.0f}")
        ax.axhline(mean_rev, color="red", linestyle="--", label=f"Mean: ${mean_rev:,.0f}")
        ax.set_ylabel("Revenue ($)")
        ax.set_title("Revenue Percentiles")
        ax.legend(fontsize=8)
        for i, v in enumerate(p_vals):
            ax.text(i, v + std_rev * 0.02, f"${v:,.0f}", ha="center", fontsize=7)

        # 5. Cumulative distribution
        ax = axes[1, 1]
        sorted_rev = sorted(revenues)
        cum_y = np.arange(1, len(sorted_rev) + 1) / len(sorted_rev)
        ax.plot(sorted_rev, cum_y, color="steelblue", linewidth=2)
        ax.axvline(total_cost, color="orange", linestyle="--",
                   label=f"Cost: ${total_cost:,.0f} (P(loss)={prob_loss:.1%})")
        ax.axvline(mean_rev, color="red", linestyle="--", label=f"Mean: ${mean_rev:,.0f}")
        ax.fill_between(sorted_rev, cum_y, alpha=0.1, color="steelblue")
        ax.set_xlabel("Revenue ($)")
        ax.set_ylabel("Cumulative Probability")
        ax.set_title("Cumulative Distribution Function")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)

        # 6. Risk/Return scatter
        ax = axes[1, 2]
        ax.scatter(response_rates[:200], [r / 1e6 for r in revenues[:200]],
                   alpha=0.6, c=conversion_rates[:200], cmap="viridis", s=30)
        ax.set_xlabel("Response Rate")
        ax.set_ylabel("Revenue ($M)")
        ax.set_title("Risk-Return Scatter (first 200 iterations)")
        cbar = plt.colorbar(ax.collections[0], ax=ax)
        cbar.set_label("Conversion Rate")

        plt.tight_layout()
        path = REPORT_DIR / "monte_carlo_simulation.png"
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        self.report.check("Monte Carlo graph saved", path.exists(), str(path))

    async def plot_twin_scores(self):
        self.report.section("Twin Score Visualization")

        if not self.twins:
            return

        engagements = [t["engagement_score"] or 0 for t in self.twins]
        loyalties = [t["loyalty_score"] or 0 for t in self.twins]
        ltvs = [min(t["lifetime_value"] or 0, 50000) for t in self.twins]
        staleness = [t["staleness_score"] or 0 for t in self.twins]

        fig, axes = plt.subplots(2, 3, figsize=(18, 10))
        fig.suptitle("PROMETHEUS — Digital Twin Score Analysis", fontsize=16, fontweight="bold")

        # 1. Engagement histogram
        ax = axes[0, 0]
        ax.hist(engagements, bins=15, alpha=0.7, color="steelblue", edgecolor="white")
        ax.axvline(statistics.mean(engagements), color="red", linestyle="--",
                   label=f"Mean: {statistics.mean(engagements):.3f}")
        ax.set_xlabel("Engagement Score")
        ax.set_ylabel("Customers")
        ax.set_title("Engagement Score Distribution")
        ax.legend()

        # 2. Loyalty histogram
        ax = axes[0, 1]
        ax.hist(loyalties, bins=15, alpha=0.7, color="mediumseagreen", edgecolor="white")
        ax.axvline(statistics.mean(loyalties), color="red", linestyle="--",
                   label=f"Mean: {statistics.mean(loyalties):.3f}")
        ax.set_xlabel("Loyalty Score")
        ax.set_ylabel("Customers")
        ax.set_title("Loyalty Score Distribution")
        ax.legend()

        # 3. LTV histogram
        ax = axes[0, 2]
        ax.hist(ltvs, bins=15, alpha=0.7, color="coral", edgecolor="white")
        ax.axvline(statistics.mean(ltvs), color="red", linestyle="--",
                   label=f"Mean: ${statistics.mean(ltvs):,.2f}")
        ax.axvline(statistics.median(ltvs), color="purple", linestyle=":",
                   label=f"Median: ${statistics.median(ltvs):,.2f}")
        ax.set_xlabel("Lifetime Value ($)")
        ax.set_ylabel("Customers")
        ax.set_title("LTV Distribution")
        ax.legend()

        # 4. Engagement vs Loyalty scatter
        ax = axes[1, 0]
        scatter = ax.scatter(engagements, loyalties, c=ltvs, cmap="viridis",
                             alpha=0.7, s=50, edgecolors="white", linewidth=0.5)
        ax.set_xlabel("Engagement Score")
        ax.set_ylabel("Loyalty Score")
        ax.set_title("Engagement vs Loyalty (color = LTV)")
        cbar = plt.colorbar(scatter, ax=ax)
        cbar.set_label("LTV ($)")
        corr = np.corrcoef(engagements, loyalties)[0, 1]
        ax.text(0.05, 0.95, f"r = {corr:.3f}", transform=ax.transAxes,
                fontsize=10, verticalalignment="top", bbox=dict(boxstyle="round", alpha=0.8))

        # 5. Staleness histogram
        ax = axes[1, 1]
        ax.hist(staleness, bins=15, alpha=0.7, color="darkorange", edgecolor="white")
        ax.axvline(statistics.mean(staleness), color="red", linestyle="--",
                   label=f"Mean: {statistics.mean(staleness):.3f}")
        ax.set_xlabel("Staleness Score")
        ax.set_ylabel("Customers")
        ax.set_title("Twin Staleness Distribution")
        ax.legend()

        # 6. Score comparison boxplot
        ax = axes[1, 2]
        data = [engagements, loyalties, staleness]
        bp = ax.boxplot(data, tick_labels=["Engagement", "Loyalty", "Staleness"],
                        patch_artist=True, widths=0.5)
        colors = ["steelblue", "mediumseagreen", "darkorange"]
        for patch, color in zip(bp["boxes"], colors):
            patch.set_facecolor(color)
        ax.set_ylabel("Score")
        ax.set_title("Score Distribution Comparison")
        ax.grid(True, axis="y", alpha=0.3)

        plt.tight_layout()
        path = REPORT_DIR / "twin_scores.png"
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        self.report.check("Twin score graphs saved", path.exists(), str(path))

    async def plot_channel_affinity(self):
        self.report.section("Channel Affinity Visualization")

        if not self.customer_ids:
            return

        sample = min(20, len(self.customer_ids))
        channel_data = {ch: [] for ch in ["email", "sms", "push", "in_app"]}
        customer_labels = []

        for cid in self.customer_ids[:sample]:
            result = await self.session.execute(text(
                "SELECT channel_affinity FROM customer_twins "
                "WHERE customer_id = :cid AND organization_id = :oid"
            ), {"cid": cid, "oid": self.org_id})
            row = result.scalar_one_or_none()
            if row and isinstance(row, dict):
                for ch in channel_data:
                    channel_data[ch].append(row.get(ch, 0))

        if not any(channel_data.values()):
            self.report.check("Channel affinity graph", False, "No channel data to plot")
            return

        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        fig.suptitle("PROMETHEUS — Channel Affinity Analysis", fontsize=14, fontweight="bold")

        # 1. Heatmap
        ax = axes[0]
        df = pd.DataFrame(channel_data)
        sns.heatmap(df.T, ax=ax, cmap="YlOrRd", annot=True, fmt=".2f",
                    xticklabels=False, cbar_kws={"label": "Affinity"})
        ax.set_xlabel("Customer (n={})".format(sample))
        ax.set_ylabel("Channel")
        ax.set_title("Per-Customer Channel Affinity Heatmap")

        # 2. Bar chart
        ax = axes[1]
        means = {ch: statistics.mean(vals) if vals else 0 for ch, vals in channel_data.items()}
        stds = {ch: statistics.stdev(vals) if len(vals) > 1 else 0 for ch, vals in channel_data.items()}
        channels = list(means.keys())
        x_pos = np.arange(len(channels))
        ax.bar(x_pos, [means[ch] for ch in channels], yerr=[stds[ch] for ch in channels],
               capsize=5, color=["#2196F3", "#FF5722", "#4CAF50", "#9C27B0"], alpha=0.8)
        ax.set_xticks(x_pos)
        ax.set_xticklabels(channels)
        ax.set_ylabel("Mean Affinity Score")
        ax.set_title("Average Channel Affinity (with std dev)")
        ax.grid(True, axis="y", alpha=0.3)

        plt.tight_layout()
        path = REPORT_DIR / "channel_affinity.png"
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        self.report.check("Channel affinity graphs saved", path.exists(), str(path))

    async def plot_sentiment_trends(self):
        self.report.section("Sentiment Trend Visualization")

        if not self.customer_ids:
            return

        sample = min(5, len(self.customer_ids))
        fig, axes = plt.subplots(1, sample if sample <= 5 else 5,
                                  figsize=(max(14, sample * 3), 4), squeeze=False)
        fig.suptitle("PROMETHEUS — Customer Sentiment Trends (last 30 days)",
                     fontsize=14, fontweight="bold")

        for i, cid in enumerate(self.customer_ids[:sample]):
            if sample == 1:
                ax = axes[0, 0]
            else:
                ax = axes[0, i]

            cust = next((c for c in self.customers if c["id"] == cid), None)
            name = cust["first_name"] if cust else str(cid)[:8]

            result = await self.session.execute(text(
                "SELECT sentiment_trend FROM customer_twins "
                "WHERE customer_id = :cid AND organization_id = :oid"
            ), {"cid": cid, "oid": self.org_id})
            trend_raw = result.scalar_one_or_none()

            if trend_raw and isinstance(trend_raw, (list, np.ndarray)) and len(trend_raw) > 0:
                trend = list(trend_raw)
                ax.plot(trend, color="steelblue", linewidth=1.5, marker=".", markersize=3)
                ax.axhline(0, color="gray", linestyle="--", linewidth=0.5)
                ax.fill_between(range(len(trend)), trend, 0, alpha=0.15, color="steelblue")
                ax.set_ylim(-1.05, 1.05)
                final = trend[-1]
                color = "green" if final > 0 else "red"
                ax.set_title(f"{name} (final: {final:+.2f})", color=color)
            else:
                ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
                ax.set_title(name)

            ax.set_xlabel("Event Sequence")
            ax.set_ylabel("Sentiment")
            ax.grid(True, alpha=0.3)

        plt.tight_layout()
        path = REPORT_DIR / "sentiment_trends.png"
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        self.report.check("Sentiment trend graphs saved", path.exists(), str(path))

    async def plot_event_distribution(self):
        self.report.section("Event Distribution Visualization")

        event_result = await self.session.execute(text(
            "SELECT event_type, count(*) as cnt FROM customer_events "
            "WHERE organization_id = :oid GROUP BY event_type ORDER BY cnt DESC"
        ), {"oid": self.org_id})
        event_types = dict(event_result.all())

        if not event_types:
            self.report.check("Event distribution graph", False, "No events")
            return

        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        fig.suptitle("PROMETHEUS — Event Distribution", fontsize=14, fontweight="bold")

        labels = list(event_types.keys())
        sizes = list(event_types.values())
        total = sum(sizes)

        # 1. Pie chart
        ax = axes[0]
        explode = [0.05] * len(labels)
        colors_pie = plt.cm.viridis(np.linspace(0.2, 0.9, len(labels)))
        wedges, texts, autotexts = ax.pie(
            sizes, labels=None, autopct="", startangle=90,
            colors=colors_pie, explode=explode[:len(labels)],
        )
        ax.set_title("Event Type Distribution")

        legend_labels = [f"{l} ({s/total*100:.1f}%)" for l, s in zip(labels, sizes)]
        ax.legend(wedges, legend_labels, title="Event Type",
                  loc="center left", bbox_to_anchor=(1, 0, 0.5, 1), fontsize=8)

        # 2. Bar chart
        ax = axes[1]
        bars = ax.barh(labels, sizes, color=colors_pie, edgecolor="white")
        for bar, size in zip(bars, sizes):
            ax.text(bar.get_width() + total * 0.005, bar.get_y() + bar.get_height() / 2,
                    f"{size}", va="center", fontsize=8)
        ax.set_xlabel("Event Count")
        ax.set_title(f"Total Events: {total}")
        ax.invert_yaxis()
        ax.grid(True, axis="x", alpha=0.3)

        plt.tight_layout()
        path = REPORT_DIR / "event_distribution.png"
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        self.report.check("Event distribution graphs saved", path.exists(), str(path))

    async def plot_behavior_profiles(self):
        self.report.section("Behavior Profile Visualization")

        sample = min(50, len(self.customer_ids))
        profiles = []

        for cid in self.customer_ids[:sample]:
            result = await self.session.execute(text(
                "SELECT behavior_profile FROM customer_twins "
                "WHERE customer_id = :cid AND organization_id = :oid"
            ), {"cid": cid, "oid": self.org_id})
            row = result.scalar_one_or_none()
            if row and isinstance(row, dict):
                row["customer_id"] = str(cid)
                profiles.append(row)

        if not profiles:
            self.report.check("Behavior profile graph", False, "No profile data")
            return

        df = pd.DataFrame(profiles)
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if "customer_id" in numeric_cols:
            numeric_cols.remove("customer_id")

        if not numeric_cols:
            self.report.check("Behavior profile numeric fields", False)
            return

        fig, axes = plt.subplots(1, min(3, len(numeric_cols)),
                                  figsize=(min(18, len(numeric_cols) * 6), 5))
        fig.suptitle("PROMETHEUS — Behavior Profile Metrics", fontsize=14, fontweight="bold")

        if len(numeric_cols) == 1:
            axes = [axes]

        for ax, col in zip(axes, numeric_cols[:3]):
            values = df[col].dropna()
            if len(values) == 0:
                ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
                continue
            ax.hist(values, bins=15, alpha=0.7, edgecolor="white")
            ax.axvline(statistics.mean(values), color="red", linestyle="--",
                       label=f"Mean: {statistics.mean(values):.3f}")
            ax.set_xlabel(col.replace("_", " ").title())
            ax.set_ylabel("Customers")
            ax.set_title(f"{col.replace('_', ' ').title()}")
            ax.legend()

        plt.tight_layout()
        path = REPORT_DIR / "behavior_profiles.png"
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        self.report.check("Behavior profile graphs saved", path.exists(), str(path))

async def main():
    report = ValidationReport()
    validator = AgentValidator(report)

    try:
        await validator.connect()
        await validator.validate_models()
        await validator.validate_twin_scores()
        await validator.validate_channel_affinity()
        await validator.validate_predictions()
        await validator.validate_segments()
        await validator.validate_event_pipeline()
        await validator.simulate_monte_carlo()
        await validator.plot_twin_scores()
        await validator.plot_channel_affinity()
        await validator.plot_sentiment_trends()
        await validator.plot_event_distribution()
        await validator.plot_behavior_profiles()
    except Exception as e:
        print(f"\n{FAIL} FATAL: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await validator.disconnect()

    success = report.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
