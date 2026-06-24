# PROMETHEUS — Project Knowledge Base

## Overview

PROMETHEUS is an **AI-Powered Customer Digital Twin Platform** that creates a continuously evolving AI model for every customer. Unlike traditional CRM systems, it models behavior, sentiment, preferences, intent, engagement, loyalty, communication patterns, and future actions — updated in real time from every interaction across email, web, mobile, support, social, and campaigns.

**Repository:** `https://github.com/ChiragHariprasad/prometheus`

---

## Architecture

```
Ingestion Layer (Kafka) → Feature Engineering (Redis/PostgreSQL)
                                ↓
                   Digital Twin Builder (Python)
                                ↓
        ┌───────────────────────┼──────────────────────┐
        ↓                       ↓                      ↓
Vector Memory (Qdrant)   Prediction Layer (ML)   Simulation Engine
  - Customer embeddings    - Churn (LightGBM+XGBoost) - Agent factory
  - Interest embeddings    - Intent (BART transformer) - State machine
  - Semantic memory        - LTV (quantile regression) - Monte Carlo
  - Hybrid search          - Segmentation (HDBSCAN+KMeans)
                           - Recommendations (LambdaRank)
```

The app runs in 22 Docker containers: FastAPI backend, Next.js 15 frontend, PostgreSQL 16, Redis 7, Kafka 7.7, Zookeeper, Schema Registry, Qdrant 1.11, ClickHouse (planned), MLflow (planned), Prometheus, Grafana 11.2, Traefik (planned), and 4 worker replicas.

---

## Digital Twins — Core Concept

A **Digital Twin** is a computed model of a customer's behavior profile, interests, channel affinity, engagement, loyalty, sentiment, risk indicators, and intent forecast. Every customer has one twin, built and updated in real time from events.

### Twin Data Model

```
CustomerTwin:
  - behavior_profile (BehaviorProfile): sessions, purchases, email engagement, lifecycle stage, RFM
  - interest_graph (InterestGraph): categories with interest_level, affinity_score, decay
  - channel_affinity (ChannelAffinity): per-channel engagement/response/conversion rates + optimal timing
  - engagement_score: 0.0–1.0 (sessions 30%, page depth 15%, email 20%, recency 25%, features 15%)
  - loyalty_score: 0.0–1.0 (repeat purchase 35%, longevity 20%, NPS 15%, referrals 15%, support 15%)
  - lifetime_value: total purchase value (or ML-predicted 12-month revenue)
  - sentiment_trend: rolling list of floats from event-type mapping
  - intent_forecast: purchase/churn intent at 7d/30d/90d, next best action
  - risk_indicators: churn probability, triggers, prevention actions, fatigue indicators
  - staleness_score: 0=new, 1=stale (decay: 1 - e^(-days / half_life), half_life=7 days)
  - version: incremented on each rebuild
  - confidence_score: based on data density
```

### Twin Generation Pipeline (7 steps)

1. **Event Collection** — Kafka consumer reads customer events (last 90 days, batch of 1000 customers)
2. **Feature Computation** — Session, purchase, engagement metrics + time-based features
3. **Behavior Profile Construction** — Aggregate metrics, compute RFM scores, classify lifecycle stage
4. **Interest Graph Computation** — Extract categories, compute interest levels (frequency × recency decay), detect emerging interests
5. **Channel Affinity Computation** — For each channel, compute engagement/response/conversion rates with exponential recency weighting
6. **Score Computation** — Engagement, loyalty, LTV via weighted formulas
7. **Validation & Persistence** — Validate completeness, compute confidence/staleness, persist to PostgreSQL, publish `twin.update` to Kafka

### Real-Time Twin Update Pipeline

Events arrive on Kafka → Event Router → Twin Update Dispatcher → 6 updaters (Behavior, Interest, Channel Affinity, Sentiment, LTV, Risk) → Score Recalc → Twin Store → Publish `twin.update`

Update rules by event type:
- **Page View** → behavior profile (session count, time on site)
- **Purchase** → behavior + LTV + interest graph + loyalty
- **Email Open** → channel affinity (email) + engagement
- **Email Click** → channel affinity + interest graph
- **Support Ticket** → risk indicators + sentiment
- **Session End** → behavior profile + engagement score
- **Campaign Response** → channel affinity + engagement
- **Negative Feedback/Complaint** → decrement sentiment by 0.1

### Scoring Algorithms (Implemented)

**Engagement Score** = `min(events_30d/20, 0.3) + min(sessions_30d/10, 0.2) + min(purchases_30d × 0.1, 0.2) + min(recent_ratio × 0.2, 0.2)`, clamped [0,1]

**Loyalty Score** = `min(purchases_1yr × 0.05, 0.2) + min(revenue_1yr/10000, 0.3) - min(returns × 0.1, 0.2) + min(referrals × 0.1, 0.2) + longevity_bonus`, clamped [0,1]

**LTV** = sum of all purchase event values

**Sentiment** = rolling accumulation from event-type map (purchase=+0.3, complaint=-0.5, etc.), clamped [-1,1]

**Staleness** = `1 - e^(-days_since_last_event / half_life)`, half_life = 7 days

**Lifecycle Stage** (deterministic rule-based):
- `new` = first seen ≤ 7 days
- `loyal` = 3+ purchases in 30 days
- `active` = 1+ purchase in 30 days
- `engaged` = sessions in 30 days
- `at_risk` = last seen 30–90 days ago
- `dormant` = last seen > 90 days ago

### Storage Tiers

| Tier | Technology | Access | TTL | Content |
|------|-----------|--------|-----|---------|
| Hot | Redis | 10ms | 24h | Active twin cache, session data, real-time scores |
| Warm | PostgreSQL | 50ms | None | All twin data, full profile, predictions, segments |
| Cold | S3 (planned) | 500ms | 7yr | Historical snapshots, 90d+ events |
| Vector | Qdrant | 20ms | 90d | 1024-dim embeddings for semantic search |

---

## Simulation Engine — How It Works

The simulation engine forecasts campaign outcomes using **Monte Carlo methods** at the aggregate level and an **agent-based model** at the design level.

### Input Parameters (API)

From `SimulationCreate` schema (`backend/app/schemas/simulation.py`):

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | string | required | Simulation name |
| `monte_carlo_iterations` | int | 1000 | Number of iterations (≥1) |
| `confidence_level` | float | 0.95 | Confidence level for intervals (0–1) |
| `time_horizon_days` | int | 30 | Forecast horizon in days |
| `sample_size` | int | 10000 | Number of simulated customers |
| `segment_ids` | list[str] | [] | Target customer segments |
| `include_control` | bool | True | Whether to run control group |
| `parameters` | dict | {} | `base_response_rate`, `base_conversion_rate`, `base_open_rate`, `avg_order_value`, `cost_per_contact`, `customer_count`, `fixed_cost` |
| `configuration` | dict | {} | Campaign configuration |
| `agent_configuration` | dict | {} | Agent behavior settings |
| `expected_outputs` | list[str] | [] | Desired output metrics |

### Monte Carlo Algorithm (Implemented)

In `SimulationService._execute_monte_carlo()`:

1. **Gaussian Sampling** (1000 iterations by default):
   - `response_rate` ~ N(base, base × 0.2), clipped [0.001, 1.0]
   - `conversion_rate` ~ N(base, base × 0.3), clipped [0.001, 1.0]
   - `open_rate` ~ N(base, base × 0.15), clipped [0.01, 1.0]
   - `click_rate` ~ N(0.03, 0.01), clipped [0.001, 1.0]

2. **Revenue per iteration** = `responses × conversion_rate × avg_order_value`
   where `responses = customer_count × response_rate`

3. **Cost** = `customer_count × cost_per_contact + fixed_cost`

4. **ROI** = `(mean_revenue - total_cost) / total_cost`

### Output Format

The simulation returns a `SimulationResultResponse` with these fields:

```json
{
  "aggregated_metrics": {
    "total_iterations": 1000,
    "mean_revenue": 45000.00,
    "median_revenue": 44800.00,
    "std_revenue": 5200.00,
    "min_revenue": 28500.00,
    "max_revenue": 62000.00,
    "mean_response_rate": 0.0523,
    "mean_conversion_rate": 0.0215,
    "mean_open_rate": 0.2512,
    "mean_click_rate": 0.0310,
    "total_cost": 15500.00,
    "roi": 1.9032,
    "customer_count": 10000,
    "time_horizon_days": 30,
    "confidence_level": 0.95,
    "expected_responses": 523,
    "expected_conversions": 11,
    "sensitivity": [{"parameter": "response_rate", "impact": 0.6}, ...]
  },
  "customer_projections": {
    "total_customers": 10000,
    "responders": 523,
    "converters": 11,
    "average_revenue_per_customer": 4.50
  },
  "segment_projections": {
    "overall": {"response_rate": 0.0523, "conversion_rate": 0.0215, "revenue": 45000.00}
  },
  "campaign_impact": {
    "expected_reach": 10000,
    "expected_impressions": 30000,
    "expected_engagements": 523,
    "expected_conversions": 11,
    "total_investment": 15500.00,
    "expected_roi": 1.9032
  },
  "confidence_intervals": {
    "revenue": [35000.00, 55000.00],
    "response_rate": [0.0420, 0.0625],
    "conversions": [8, 14],
    "roi": [1.25, 2.55]
  },
  "monte_carlo_distribution": {
    "histogram": [{"bin_start": 28500, "bin_end": 30250, "count": 15}, ...],
    "percentiles": {"5": 32000, "10": 35000, "25": 40000, "50": 44800, "75": 49000, "90": 52000, "95": 55000},
    "scenarios": {
      "optimistic": {"revenue": 55000, "conversions": 550, "response_rate": 0.0650},
      "most_likely": {"revenue": 45000, "conversions": 450, "response_rate": 0.0523},
      "pessimistic": {"revenue": 35000, "conversions": 350, "response_rate": 0.0400}
    }
  },
  "expected_outcomes": {
    "expected_revenue": 45000.00,
    "expected_conversions": 450,
    "expected_open_rate": 0.2512,
    "expected_click_rate": 0.0310,
    "expected_roi": 1.9032,
    "expected_cost": 15500.00,
    "expected_profit": 29500.00
  },
  "risk_assessment": {
    "probability_of_loss": 0.0234,
    "value_at_risk_95": 13000.00,
    "expected_shortfall": 8500.00,
    "upside_potential": 17000.00
  },
  "recommendations": [
    "Strong ROI projections. Consider increasing investment in this campaign."
  ]
}
```

### Agent-Based Design (Architecture Document)

The `simulation_engine_design.md` describes a more sophisticated agent-based model (not fully implemented in code):

**CustomerAgent** data model:
- `budget`, `loyalty`, `patience`, `sentiment` (core properties)
- `interests`, `price_sensitivity`, `brand_affinity`, `communication_preference`
- `state`: current_mood, fatigue_level (0–1), engagement_level, intent, in_consideration_set
- `memory`: recent_communications, recent_offers, positive/negative experiences, brand_perception
- `interaction_history`, `purchase_history`, `communication_history`
- `decision_weights`: price 0.3, relevance 0.25, timing 0.15, channel 0.15, brand 0.1, fatigue 0.05

**Agent State Machine:**
```
INACTIVE → AWARE (receive communication)
AWARE → CONSIDERING (relevance > threshold)
CONSIDERING → PURCHASE | DISMISS | DEFER
PURCHASE → SATISFIED | DISSATISFIED
DISSATISFIED → CHURNING → CHURNED
CHURNING → AWARE (win-back)
```

**Decision Engine** computes probabilities for:
- `compute_open_probability()`: channel 25%, brand 20%, relevance 25%, timing 10%, fatigue 10%, recency 10%
- `compute_click_probability()`: relevance 35%, offer value 30%, urgency 15%, historical CTR 20%
- `compute_purchase_probability()`: interest match 25%, price fit 25%, budget 20%, sentiment 10%, repeat boost 10%, patience 10%
- `compute_fatigue_increase()`: irrelevance + channel repeat + quiet hours

**Reward Function** (for optimization):
- Global reward: conversion 40%, engagement 20%, sentiment 15%, -fatigue 15%, -churn 10%
- Agent reward: relevance 30%, timing 20%, channel 20%, -fatigue 30%, +1.0 purchase bonus, -2.0 unsubscribe penalty

---

## ML Models (5 Total)

### 1. Customer Segmentation
- **Type:** HDBSCAN + KMeans ensemble (unsupervised)
- **Features (20):** session_freq, avg_session_dur, page_depth, bounce_rate, purchase_freq, aov, category_diversity, discount_usage, email_engagement, push_engagement, channel_preference, days_since_first_seen, days_since_last_purchase, rfm_scores, age_group, location_tier, device_type
- **Pipeline:** StandardScaler → PCA (n=50) → HDBSCAN(min_cluster=100) + KMeans(k=8–15) → weighted ensemble → centroid labeling
- **Monitoring:** Silhouette > 0.3, Davies-Bouldin < 1.5, segment stability

### 2. Churn Prediction
- **Type:** LightGBM + XGBoost stacking ensemble (binary classification)
- **Features (45):** engagement (15), purchase (10), sentiment (8), profile (7), interaction (5)
- **Performance:** 89% AUC, 74% precision, 83% recall
- **Risk levels:** low < 0.3, medium 0.3–0.5, high 0.5–0.7, critical ≥ 0.7
- **Training:** Weekly, 90-day window → label next 30 days, SMOTE + class weights, Optuna tuning

### 3. Intent Prediction
- **Type:** PyTorch BART transformer (multi-label classification)
- **Classes (10):** purchase, browse, compare, research, support, cancel, upgrade, downgrade, refer, churn
- **Architecture:** facebook/bart-base + 768→256→10 classification head
- **Features:** event text, page titles, search queries, support content + behavioral context
- **Performance:** 82% F1

### 4. Recommendation Engine
- **Type:** Hybrid two-stage (Qdrant candidate generation + LambdaRank ranking)
- **Stage 1:** Collaborative (ALS) + Content-based (Qdrant similarity) + Trending → 200 candidates
- **Stage 2:** LightGBM LambdaRank on customer×product cross features
- **Performance:** 215% CTR lift, NDCG@10=0.45
- **Fallback:** Popularity-based when no embedding exists

### 5. Engagement Forecasting
- **Type:** Prophet + LSTM ensemble (time series)
- **Horizon:** 7/14/30/90 days
- **Prophet:** daily/weekly/yearly seasonality, holiday effects, changepoint detection
- **LSTM:** 2 layers (128, 64), lookback 30 days, output 7-day forecast
- **Monitoring:** MAPE < 20% trigger retrain

### Drift Detection
- **Data drift:** PSI > 0.2, KS test, Chi-squared
- **Model drift:** Prediction distribution shift, AUC drop > 0.05
- **Actions:** Alert, auto-rollback, auto-retrain, shadow deploy

---

## Vector Memory (Qdrant)

5 collections:
- `customer_embeddings`: 1024d cosine, 6 shards, int8 quantization, payload has org/customer/demographics/scores/interests
- `customer_interests`: 1024d, per-interest embedding
- `product_embeddings`: 1024d, payload has name/description/price/category
- `campaign_embeddings`: 1024d
- `semantic_memory`: 1024d, memory types: conversation/preference/feedback/context/intent with TTL

**Embedding model:** BAAI/bge-large-en-v1.5 (1024d, 512 max tokens)
**Pipeline:** Data collection → Text construction (structured template) → Embedding → Storage
**Update cooldown:** 5 min between updates per customer

**Retrieval types:**
- Similar customers (lookalike): vector similarity + metadata filtering
- Semantic search: natural language query → embedding → search
- Hybrid: vector (70%) + keyword (30%) via alpha weighting

**Semantic Memory** stores episodic, semantic, procedural, and reflective memories with:
- TTL per type (30–365 days)
- Importance scoring
- Consolidation: summarizes conversations into long-term preferences

---

## API Endpoints (92 Routes)

| Module | Routes | Key Endpoints |
|--------|--------|--------------|
| Auth | 6 | POST login, register, refresh, password change/reset, verify MFA |
| Users | 6 | CRUD + role management |
| Customers | 8 | CRUD, search, merge, batch, GET by external_id |
| Twins | 6 | GET summary, GET by customer, POST rebuild, GET history, GET predictions, GET by type |
| Events | 7 | POST ingest, POST batch, search, GET by customer, summary, types |
| Campaigns | 7 | CRUD, launch, pause, cancel, GET results |
| Simulations | 10 | CRUD, POST run, GET status/results/forecast/progress/runs |
| Recommendations | 3 | GET recommendations, POST feedback |
| Notifications | 5 | POST send, retry, GET stats |
| Analytics | 6 | GET dashboard, revenue, engagement, churn, campaign performance, export |
| Segments | 6 | CRUD, POST compute, POST lookalike |

---

## Background Workers (4)

### Twin Builder
- **Topic:** `twin.cx.events.raw`
- **Group:** `twin-cx-twin-builder`
- **Scaling:** 3 replicas
- **Logic:** Consumes events → `event_service.process_event()` + `twin_service.update_twin_from_event()`
- **Extra:** Background loop every 5 min rebuilds stale twins (staleness > threshold)

### Prediction Worker
- **Topic:** `twin.cx.prediction`
- **Group:** `twin-cx-predictor`
- **Scaling:** 2 replicas
- **Logic:** Per-customer or batch ML inference via `PredictionService`

### Simulation Worker
- **Topic:** `twin.cx.simulation`
- **Group:** `twin-cx-simulator`
- **Scaling:** 4 replicas (CPU-intensive)
- **Logic:** Calls `SimulationService.run_simulation()` → `_execute_monte_carlo()`
- **Error handling:** Marks simulation as `failed` with error message

### Notification Worker
- **Topic:** `twin.cx.notification`
- **Group:** `twin-cx-notifier`
- **Scaling:** 2 replicas
- **Logic:** Calls `NotificationService.send()` for each notification

---

## Database

### PostgreSQL (65+ tables)
Key tables: `organizations`, `users`, `roles`, `permissions`, `customers` (partitioned), `customer_profiles`, `customer_twins`, `customer_events` (range-partitioned monthly), `customer_sessions`, `customer_preferences`, `customer_interests`, `customer_embeddings`, `customer_predictions`, `customer_segments`, `campaigns`, `campaign_targets`, `campaign_results`, `simulations`, `simulation_runs`, `simulation_results`, `recommendations`, `notifications`, `audit_logs`

Features: 10 custom enums, RLS on 17 tables, auto-update triggers, monthly event partitioning

### Kafka Topics (12)
- `twin.cx.events.raw` — Incoming events
- `twin.cx.twin.update` — Twin updates
- `twin.cx.prediction` — ML inference requests
- `twin.cx.simulation` — Simulation execution
- `twin.cx.notification` — Notification dispatch
- `twin.cx.embeddings.update` — Vector embedding updates
- Plus DLQ, retry, and internal topics

---

## Frontend Pages (13)

| Page | Route | Purpose |
|------|-------|---------|
| Login | `/login` | JWT authentication |
| Dashboard | `/dashboard` | Executive KPIs, charts |
| Customers | `/customers` | List + CRUD |
| Customer Detail | `/customers/[id]` | Single customer view |
| Twin Explorer | `/twins` | Twin scores, interests, affinity viz |
| Campaigns | `/campaigns` | List + CRUD |
| Campaign Detail | `/campaigns/[id]` | Campaign results |
| Campaign Builder | `/campaigns/new` | Create campaign |
| Simulation Lab | `/simulation-lab` | Config + run + results |
| Analytics | `/analytics` | Revenue, engagement, churn, segments |
| Settings | `/settings` | Org + user configuration |
| Administration | `/administration` | Audit log, system health |

**Tech:** Next.js 15, TypeScript, Tailwind CSS, shadcn/ui, Recharts, Zustand, TanStack Query

---

## Infrastructure

- **Docker Compose:** 22 containers, 9 named volumes, 1 bridge network (172.29.0.0/16)
- **Planned (not implemented):** Kubernetes/EKS, Terraform AWS (92 resources), Kong/Istio, ClickHouse, MLflow, OAuth2/SSO, GPU inference, S3, SendGrid, Twilio
- **Monitoring:** Prometheus (15s scrape), Grafana (22-panel dashboard), OpenTelemetry, Sentry

---

## Input Parameters Summary

### Creating a Twin
No direct creation — twins are auto-built on first GET request or via event ingestion. Parameters come from customer events and customer profile data.

### Running a Simulation (POST `/api/v1/simulations/{id}/run`)
Uses `parameters` from the Simulation model:
```json
{
  "base_response_rate": 0.05,
  "base_conversion_rate": 0.02,
  "base_open_rate": 0.25,
  "avg_order_value": 100.0,
  "cost_per_contact": 0.5,
  "customer_count": 10000,
  "fixed_cost": 5000
}
```

### Ingesting Events (POST `/api/v1/events/`)
```json
{
  "customer_id": "uuid",
  "event_type": "page_view|purchase|email_open|email_click|support_ticket|...",
  "channel": "email|web|mobile|in_app|sms|...",
  "value": 99.99,
  "metadata": {},
  "event_timestamp": "ISO8601"
}
```

### Creating a Simulation
```json
{
  "name": "Summer Campaign Forecast",
  "monte_carlo_iterations": 1000,
  "confidence_level": 0.95,
  "time_horizon_days": 30,
  "sample_size": 10000,
  "segment_ids": ["uuid1", "uuid2"],
  "parameters": {
    "base_response_rate": 0.05,
    "base_conversion_rate": 0.02,
    "avg_order_value": 100.0,
    "cost_per_contact": 0.5
  }
}
```

---

## Credentials (Dev/Seed)

| User | Email | Password | Role |
|------|-------|----------|------|
| Judge | `judge@texpedition.com` | `pass@123` | Admin |

Seed data: 1 org, 1 user, 10 customers, 10 twins, ~237 events across 7 types.

---

## Key Architectural Decisions

1. **Monolith with worker processes** — not microservices. This simplifies deployment while maintaining async processing via Kafka workers.
2. **Deterministic scoring** — twin scores use formula-based computation (not ML), making them auditable and explainable. ML models add predictions on top.
3. **Pessimistic locking** — twin updates use `with_for_update()` to prevent race conditions.
4. **Staleness-driven rebuild** — twins are not continuously recomputed; staleness score triggers rebuild on access or every 5 min via worker.
5. **Config-driven simulation** — Monte Carlo parameters are fully configurable per simulation, allowing what-if analysis.
