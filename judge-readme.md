# PROMETHEUS — Judge Evaluation Guide

[![GitHub](https://img.shields.io/badge/GitHub-ChiragHariprasad/prometheus-blue?style=flat&logo=github)]( )

## What is PROMETHEUS?

PROMETHEUS is an **AI-Powered Customer Digital Twin Platform** that creates a continuously evolving AI model for every customer. Unlike traditional CRM systems that store static records, PROMETHEUS models customer behavior, sentiment, preferences, intent, engagement, loyalty, communication patterns, and future actions — updated in real time from every interaction across email, web, mobile, support, social, and campaigns.

**Key capabilities demonstrated in this build:**
- Real-time event ingestion via Kafka streaming pipeline
- Digital twin generation with computed engagement, loyalty, LTV, sentiment, and churn scores
- Monte Carlo simulation engine for campaign forecasting
- Customer segmentation with ML-based rules
- Personalized recommendation engine
- Executive analytics dashboard
- Full RBAC with JWT authentication (HS256)

---

## Quick Start

1. **Clone the repo**
2. **Follow [linux-run.md](linux-run.md)** (Linux/macOS) or **[windows-run.md](windows-run.md)** (Windows PowerShell)
3. **Login with judge credentials** after seeding:
   - Email: `judge@texpedition.com`
   - Password: `pass@123`

---

## System Architecture

### Current Implementation (Docker Compose)

```
┌──────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                              │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Next.js 15 Frontend (TypeScript, Tailwind, shadcn/ui)     │  │
│  │  Port 3000 — Login, Dashboard, Customer/Twin/Campaign/Sim  │  │
│  └────────────────────────┬───────────────────────────────────┘  │
│                           │ HTTP (/api/v1/*)                     │
│                           ▼                                      │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  FastAPI Backend (Python 3.12, SQLAlchemy 2.0, Pydantic v2)│  │
│  │  Port 8004 (mapped) — 92 endpoints across 11 route files   │  │
│  │  Middleware: JWT auth, rate limiting, structured logging    │  │
│  └───┬───────┬───────┬───────┬───────┬───────┬───────┬───────┘  │
│      │       │       │       │       │       │       │          │
│      ▼       ▼       ▼       ▼       ▼       ▼       ▼          │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────────┐ │
│  │Auth │ │User │ │Cust │ │Twin │ │Event│ │Camp │ │Simul    │ │
│  │Svc  │ │Svc  │ │Svc  │ │Svc  │ │Svc  │ │Svc  │ │Svc      │ │
│  └─────┘ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘ └─────────┘ │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐                     │
│  │Recmd│ │Seg  │ │Pred │ │Notif│ │Anal │                     │
│  │Svc  │ │Svc  │ │Svc  │ │Svc  │ │Svc  │                     │
│  └─────┘ └─────┘ └─────┘ └─────┘ └─────┘                     │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  DATA INFRASTRUCTURE                                       │  │
│  │  ┌──────────┐ ┌────────┐ ┌──────────┐ ┌───────┐         │  │
│  │  │PostgreSQL│ │ Redis  │ │  Qdrant  │ │ Kafka │         │  │
│  │  │  (Main)  │ │ (Cache)│ │(Vectors) │ │(Events)│         │  │
│  │  └──────────┘ └────────┘ └──────────┘ └───────┘         │  │
│  │  ┌──────────┐ ┌────────┐ ┌──────────┐                   │  │
│  │  │ ClickHse │ │ MLflow │ │  Traefik │  ← Planned        │  │
│  │  │ (Planned)│ │(Planned)│ │ (Planned)│                   │  │
│  │  └──────────┘ └────────┘ └──────────┘                   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  BACKGROUND WORKERS (4)                                    │  │
│  │  ┌──────────────┐ ┌─────────────┐ ┌──────────────┐       │  │
│  │  │Twin Builder  │ │  Prediction │ │  Simulation  │       │  │
│  │  │(Kafka→Twin)  │ │  (ML Infer) │ │  (MonteCarlo)│       │  │
│  │  └──────────────┘ └─────────────┘ └──────────────┘       │  │
│  │  ┌──────────────────┐                                     │  │
│  │  │  Notification    │                                     │  │
│  │  │  (Send alerts)   │                                     │  │
│  │  └──────────────────┘                                     │  │
│  └──────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

### 22 Docker Containers Running

| Service | Container | Port | Purpose |
|---------|-----------|------|---------|
| Backend | FastAPI + 11 services | 8004 | Core API server |
| Frontend | Next.js 15 | 3000 | Web UI |
| PostgreSQL 16 | Primary DB | (int) | All relational data |
| Redis 7 | Cache + pub/sub | (int) | Session, rate limit, job queue |
| Kafka | Event streaming | (int) | Real-time event pipeline |
| Zookeeper | Kafka coordination | (int) | Cluster management |
| Schema Registry | Avro schemas | (int) | Event schema validation |
| Qdrant | Vector DB | (int) | Customer embeddings |
| ClickHouse | Analytics DB | (int) | Planned — Not Implemented |
| MLflow | ML model registry | (int) | Planned — Not Implemented |
| Prometheus | Metrics | (int) | Monitoring |
| Grafana | Dashboards | 3001 | Visualization |
| Traefik | Reverse proxy | (int) | API gateway (planned) |
| Worker x4 | Background jobs | — | Twin, prediction, sim, notif |

> **Note:** ClickHouse, MLflow, and Traefik are provisioned but not fully integrated in this build. See "Planned for Production" sections.

---

## Core Files & Their Purpose

### Backend (`backend/app/`)

| File/Directory | Purpose |
|----------------|---------|
| `api/v1/auth.py` | Login, register, token refresh, password change, password reset (6 routes) |
| `api/v1/customers.py` | Customer CRUD, search, merge, batch operations |
| `api/v1/twins.py` | Get/build/rebuild digital twin, predictions |
| `api/v1/events.py` | Event ingestion, batch import, search, summary |
| `api/v1/campaigns.py` | Campaign CRUD, launch, pause, cancel, results |
| `api/v1/simulations.py` | Simulation CRUD, run, results, forecast, progress |
| `api/v1/recommendations.py` | Get recommendations, record feedback |
| `api/v1/notifications.py` | Queue/send notifications, retry, stats |
| `api/v1/analytics.py` | Dashboard, revenue, engagement, churn, campaign performance |
| `api/v1/segments.py` | Segment CRUD, compute, lookalike |
| `api/v1/users.py` | User CRUD, role management |
| `core/config.py` | All environment config (139+ settings) |
| `core/security.py` | JWT (HS256), bcrypt password hashing |
| `core/database.py` | Async SQLAlchemy engine, session factory |
| `core/redis.py` | Redis client (cache, pub/sub, streams) |
| `core/kafka.py` | Kafka producer + consumer + DLQ |
| `core/qdrant.py` | Qdrant vector DB client |
| `models/` | 19 SQLAlchemy ORM models |
| `schemas/` | 50+ Pydantic v2 request/response models |
| `services/` | 12 business logic services |
| `services/twin_service.py` | Twin build, rebuild, score computation (engagement, loyalty, LTV, sentiment, channel affinity, behavior, interests, staleness) |
| `services/simulation_service.py` | Monte Carlo campaign simulation (1000 iterations, 95% CI, risk assessment) |
| `services/prediction_service.py` | Churn/intent/segmentation predictions |
| `middleware/auth.py` | JWT verification, organization isolation |
| `tasks/twin_builder.py` | Kafka consumer — processes events → updates twins |
| `tasks/prediction_worker.py` | Kafka consumer — runs ML inference |
| `tasks/simulation_worker.py` | Kafka consumer — executes simulations |
| `tasks/notification_worker.py` | Kafka consumer — sends notifications |

### Frontend (`frontend/src/`)

| File/Directory | Purpose |
|----------------|---------|
| `app/(auth)/login/page.tsx` | Login page (simplified, no OAuth/register) |
| `app/(dashboard)/dashboard/` | Executive dashboard with stats, charts |
| `app/(dashboard)/customers/` | Customer list and detail view |
| `app/(dashboard)/twins/` | Twin explorer with scores, interests, affinity |
| `app/(dashboard)/campaigns/` | Campaign builder, list, detail |
| `app/(dashboard)/simulation-lab/` | Simulation config and results |
| `app/(dashboard)/analytics/` | Analytics center |
| `components/` | 25+ React components (shadcn/ui based) |
| `lib/api.ts` | API client with auth token management |
| `store/` | Zustand state (auth + UI) |

### Infrastructure

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Orchestrates all 22 containers |
| `backend/Dockerfile` | Python 3.12-slim, uvicorn with uvloop |
| `frontend/Dockerfile` | Node 20, multi-stage build, standalone output |
| `database/001_schema.sql` | Full PostgreSQL schema (65+ tables, 10 custom enums, RLS) |
| `infrastructure/monitoring/` | Prometheus config + Grafana dashboards |
| `scripts/fix-docker-dns.sh` | DNS resolution fix for Docker |

---

## Data Flow Walkthrough

```
1.  User Action (web/mobile)
        │
2.      ▼
    Event Ingestion API → Kafka topic (twin.cx.events.raw)
        │
3.      ▼
    Twin Builder Worker (Kafka consumer)
    ├── event_service.process_event() — saves to customer_events
    └── twin_service.update_twin_from_event()
        ├── Updates LTV (for purchases)
        ├── Updates sentiment (for negative events)
        ├── Recalculates engagement score
        └── Recalculates staleness score
        │
4.      ▼
    API Request (GET /customers/{id}/twin)
    └── twin_service.get_or_build_twin()
        ├── If twin exists and fresh → return cached
        ├── If stale/missing → rebuild_twin()
        │   ├── _compute_behavior_profile() — 10+ metrics from events
        │   ├── _compute_interest_graph() — category affinity from events
        │   ├── _compute_channel_affinity() — per-channel engagement
        │   ├── compute_engagement_score() — weighted from sessions, purchases, recency
        │   ├── compute_loyalty_score() — from purchase frequency, recency, value
        │   ├── compute_sentiment_trend() — rolling 30-day sentiment
        │   ├── compute_staleness() — days since last event
        │   └── _compute_lifetime_value() — total purchase value
        └── Returns CustomerTwinResponse
        │
5.      ▼
    Campaign Simulation (POST /simulations/{id}/run)
    └── simulation_service.run_simulation()
        └── _execute_monte_carlo()
            ├── 1000 iterations (default)
            ├── Gaussian sampling: response_rate, conversion_rate, open_rate, click_rate
            ├── Statistics: mean, median, stdev, percentiles
            ├── 95% confidence intervals
            ├── Risk assessment: VaR 95%, probability of loss, expected shortfall
            └── Scenarios: optimistic, most_likely, pessimistic
        │
6.      ▼
    Analytics Dashboard (GET /analytics/dashboard)
    └── Aggregates: customer count, event count, active campaigns,
        avg engagement/loyalty, total revenue, top segments
```

---

## Validation Checklist

Use these checks to verify the system is running correctly.

### 1. Container Health
```bash
docker compose ps
# All 22 containers should show "Up" or "healthy"
```

### 2. Backend Health
```bash
curl -s http://localhost:8004/health | python3 -m json.tool
```
Expected:
```json
{
    "status": "healthy",
    "version": "1.0.0",
    "services": {
        "redis": "connected",
        "kafka": "connected",
        "qdrant": "connected"
    }
}
```

### 3. Login
```bash
TOKEN=$(curl -s -X POST http://localhost:8004/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"judge@texpedition.com","password":"pass@123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
echo "Token: ${TOKEN:0:20}..."
```

### 4. Verify Seed Data
```bash
# Customers: 10
curl -s http://localhost:8004/api/v1/customers/ \
  -H "Authorization: Bearer $TOKEN" | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print(f'Customers: {d[\"total\"]}')"

# Events: 237
curl -s http://localhost:8004/api/v1/events/?limit=1 \
  -H "Authorization: Bearer $TOKEN" | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print(f'Events: {d[\"total\"]}')"

# Pick a customer and view their twin
CID=$(curl -s http://localhost:8004/api/v1/customers/ \
  -H "Authorization: Bearer $TOKEN" | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print(d['items'][0]['id'])")
curl -s "http://localhost:8004/api/v1/customers/$CID/twin" \
  -H "Authorization: Bearer $TOKEN" | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print(f'Twin: status={d[\"status\"]}, engagement={d[\"engagement_score\"]:.1f}, loyalty={d[\"loyalty_score\"]:.1f}, LTV=\${d[\"lifetime_value\"]:.2f}')"
```

### 5. Analytics Dashboard
```bash
curl -s "http://localhost:8004/api/v1/analytics/dashboard" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

### 6. Frontend
Open http://localhost:3000 in a browser. You should see the PROMETHEUS login page.

### 7. API Documentation
Open http://localhost:8004/docs (Swagger UI) or http://localhost:8004/redoc (ReDoc).

### 8. Monitoring (Planned — Not Implemented)
- Grafana: http://localhost:3001 (admin/admin) — dashboards provisioned
- Prometheus: http://localhost:9090 — metrics available

---

## Worker Agents — Logic Verification

### Twin Builder (`app/tasks/twin_builder.py`)
- **Purpose**: Consumes events from `twin.cx.events.raw` Kafka topic, processes them to update digital twins in real time
- **Key methods**: `process_event()` → `EventService.process_event()` + `TwinService.update_twin_from_event()`
- **Stale rebuild**: Background loop every 5 minutes calls `TwinService.rebuild_stale_twins()`
- **Dependencies**: PostgreSQL, Redis, Qdrant, Kafka
- **Scaling**: 3 replicas in docker-compose, horizontal scaling via consumer group

### Prediction Worker (`app/tasks/prediction_worker.py`)
- **Purpose**: Consumes from `twin.cx.prediction` topic, runs ML inference
- **Key methods**: `process_prediction_request()` → batch or per-customer predictions via `PredictionService`
- **Dependencies**: PostgreSQL, Redis, Kafka
- **Scaling**: 2 replicas

### Simulation Worker (`app/tasks/simulation_worker.py`)
- **Purpose**: Consumes from `twin.cx.simulation` topic, executes Monte Carlo simulations
- **Key methods**: `run_simulation_job()` → `SimulationService.run_simulation()` → `_execute_monte_carlo()`
- **Monte Carlo engine** (in `simulation_service.py`):
  - 1000 iterations (configurable)
  - 10,000 agents (configurable sample size)
  - Gaussian sampling for: response rate, conversion rate, open rate, click rate
  - All values clipped to valid ranges (0.0–1.0)
  - Computes: mean, median, stdev, min, max, percentiles (5/10/25/50/75/90/95)
  - 95% confidence intervals (z-score = 1.96)
  - Risk assessment: probability of loss, Value at Risk 95%, expected shortfall, upside potential
  - 3 scenarios: optimistic, most_likely, pessimistic
  - Revenue histogram with 20 bins
  - Automated recommendations based on ROI and risk
- **Error handling**: Marks simulation as `failed` with error message on exception
- **Scaling**: 4 replicas (CPU-intensive)

### Notification Worker (`app/tasks/notification_worker.py`)
- **Purpose**: Consumes from `twin.cx.notification` topic, sends notifications
- **Key methods**: `process_notification()` → `NotificationService.send_notification()`
- **Dependencies**: PostgreSQL, Redis, Kafka
- **Scaling**: 2 replicas

---

## Planned for Production (Not Implemented in This Build)

The following components are **architected and prepared** but not fully implemented in this demonstration build:

| Component | Status | Location |
|-----------|--------|----------|
| Kubernetes/EKS orchestration | Manifests written, not deployed | `infrastructure/kubernetes/` |
| Terraform AWS IaC | 92 resources defined | `infrastructure/terraform/` |
| Kong API Gateway | Planned — using Traefik basic config | `infrastructure/traefik/` |
| Istio Service Mesh | Architecture designed | ARCHITECTURE.md |
| ClickHouse analytics queries | Container running, not queried | `docker-compose.yml` |
| MLflow model training | Container running, not connected | `infrastructure/mlflow/` |
| OAuth2/SSO (Google, GitHub) | Routes stubbed, UI removed | Login page simplified |
| SMTP/SendGrid email delivery | Config present, not wired | `.env.example` |
| SMS (Twilio) notifications | Config present, not wired | `.env.example` |
| S3 artifact storage | Config present, not wired | `.env.example` |
| Production GPU inference | CPU-only in this build | Backend config |
| Multi-region deployment | Architecture designed | ARCHITECTURE.md |

---

## Credentials

| User | Email | Password | Role |
|------|-------|----------|------|
| Judge | `judge@texpedition.com` | `pass@123` | Admin (full access) |
