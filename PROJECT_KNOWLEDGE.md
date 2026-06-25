# Prometheus (TwinCX) — Project Knowledge

> **Source:** Every detail in this document is derived from reading the source code. No existing documentation was referenced.

---

## Table of Contents

1. [What Is Prometheus?](#1-what-is-prometheus)
2. [Directory Structure](#2-directory-structure)
3. [How Everything Connects](#3-how-everything-connects)
4. [Core Infrastructure Files](#4-core-infrastructure-files)
5. [Database Models — Every Table, Every Column](#5-database-models--every-table-every-column)
6. [Services — What Each One Does](#6-services--what-each-one-does)
7. [API Endpoints — Every Route](#7-api-endpoints--every-route)
8. [Background Workers — How Async Processing Works](#8-background-workers--how-async-processing-works)
9. [Schemas — Request/Response Contracts](#9-schemas--requestresponse-contracts)
10. [Repositories — Data Access Layer](#10-repositories--data-access-layer)
11. [Middleware — Request Pipeline](#11-middleware--request-pipeline)
12. [How Twins Are Created (Step by Step)](#12-how-twins-are-created-step-by-step)
13. [How Simulations Run (Step by Step)](#13-how-simulations-run-step-by-step)
14. [How Predictions Work](#14-how-predictions-work)
15. [How Recommendations Work](#15-how-recommendations-work)
16. [How Segmentation Works](#16-how-segmentation-works)
17. [How Campaigns Work](#17-how-campaigns-work)
18. [Frontend Architecture](#18-frontend-architecture)
19. [External Services Integration](#19-external-services-integration)
20. [Environment Configuration](#20-environment-configuration)

---

## 1. What Is Prometheus?

Prometheus (code-named **TwinCX**) is a **Digital Twin Customer Experience Platform**. Its core idea:

1. **Ingest** customer behavioral events (page views, purchases, email opens, etc.)
2. **Build a "Digital Twin"** — a rich, computed behavioral profile per customer containing engagement scores, loyalty, sentiment, interest graphs, channel affinity, RFM segmentation, and risk indicators
3. **Run Monte Carlo Simulations** — simulate what would happen if you launch a marketing campaign, change pricing, or offer discounts, using statistically-modeled virtual agents derived from twins
4. **Predict** — compute churn probability, purchase intent, and lifetime value using ML models (or heuristic fallbacks)
5. **Recommend** — generate personalized recommendations using collaborative filtering (Qdrant vector similarity) and content-based approaches

It is a **multi-tenant SaaS** platform where each `Organization` has its own isolated data universe.

---

## 2. Directory Structure

```
prometheus/
├── backend/
│   ├── app/
│   │   ├── api/v1/                  # FastAPI route handlers
│   │   │   ├── router.py            # Aggregates all sub-routers
│   │   │   ├── auth.py              # Authentication endpoints
│   │   │   ├── customers.py         # Customer CRUD + sub-resources
│   │   │   ├── twins.py             # Twin retrieval, rebuild, predictions
│   │   │   ├── simulations.py       # Simulation lifecycle
│   │   │   ├── events.py            # Event ingestion + queries
│   │   │   ├── analytics.py         # Dashboard, revenue, churn analytics
│   │   │   ├── campaigns.py         # Campaign management
│   │   │   ├── recommendations.py   # Personalized recommendations
│   │   │   ├── notifications.py     # Notification management
│   │   │   ├── segments.py          # Customer segments
│   │   │   ├── users.py             # User + role management
│   │   │   └── admin.py             # System admin (health, flags, audit)
│   │   │
│   │   ├── core/                    # Infrastructure setup
│   │   │   ├── config.py            # pydantic-settings configuration
│   │   │   ├── database.py          # SQLAlchemy async engine + session factory
│   │   │   ├── redis.py             # Redis async client wrapper
│   │   │   ├── kafka.py             # aiokafka producer/consumer wrapper
│   │   │   ├── qdrant.py            # Qdrant async client setup
│   │   │   ├── security.py          # JWT creation/validation, bcrypt hashing
│   │   │   ├── exceptions.py        # Custom HTTP exception hierarchy
│   │   │   └── logging.py           # structlog configuration
│   │   │
│   │   ├── middleware/              # ASGI middleware
│   │   │   ├── auth.py              # JWT extraction + dev-mode bypass + RBAC helpers
│   │   │   ├── logging_middleware.py # Request/response logging
│   │   │   └── rate_limit.py        # Rate limiting middleware
│   │   │
│   │   ├── models/                  # SQLAlchemy ORM models
│   │   │   ├── base.py              # DeclarativeBase, TimestampMixin, UUIDMixin
│   │   │   ├── organization.py      # Organization (tenant) model
│   │   │   ├── user.py              # Platform user model
│   │   │   ├── role.py              # Role, Permission, UserRole
│   │   │   ├── customer.py          # Customer + 6 related models
│   │   │   ├── twin.py              # CustomerTwin, TwinSnapshot, Prediction
│   │   │   ├── event.py             # Event (partitioned by timestamp)
│   │   │   ├── simulation.py        # Simulation, SimulationRun, SimulationResult
│   │   │   ├── campaign.py          # Campaign, CampaignTarget, CampaignResult
│   │   │   ├── recommendation.py    # Recommendation, RecommendationFeedback
│   │   │   ├── notification.py      # Notification model
│   │   │   ├── audit.py             # AuditLog model
│   │   │   └── __init__.py          # Re-exports all models
│   │   │
│   │   ├── schemas/                 # Pydantic v2 request/response models
│   │   │   ├── common.py            # APIResponse, PaginatedResponse, ErrorResponse
│   │   │   ├── auth.py              # Login/Register/Token schemas
│   │   │   ├── customer.py          # Customer CRUD + profile schemas
│   │   │   ├── twin.py              # 12+ twin-related response schemas
│   │   │   ├── simulation.py        # SimulationCreate/Response/Result/Forecast
│   │   │   ├── event.py             # Event create/response
│   │   │   ├── campaign.py          # Campaign CRUD schemas
│   │   │   ├── analytics.py         # Dashboard/Revenue/Churn analytics
│   │   │   ├── notification.py      # Notification schemas
│   │   │   ├── recommendation.py    # Recommendation schemas
│   │   │   └── user.py              # User/Role schemas
│   │   │
│   │   ├── services/                # Business logic layer
│   │   │   ├── twin_service.py      # ★ CORE: Twin building/rebuilding (55KB!)
│   │   │   ├── agent_simulation.py  # ★ CORE: Monte Carlo engine (40KB!)
│   │   │   ├── simulation_service.py# Simulation orchestration
│   │   │   ├── embedding_service.py # SentenceTransformer + Qdrant embeddings
│   │   │   ├── prediction_service.py# Churn/Intent/LTV predictions (ML + fallback)
│   │   │   ├── recommendation_service.py # Collaborative + content-based recs
│   │   │   ├── analytics_service.py # Dashboard + analytics queries
│   │   │   ├── customer_service.py  # Customer CRUD + merge + journey
│   │   │   ├── event_service.py     # Event ingestion + processing
│   │   │   ├── campaign_service.py  # Campaign launch + targeting + ROI
│   │   │   ├── segment_service.py   # Segmentation + ML clustering
│   │   │   ├── auth_service.py      # Auth logic + MFA + password reset
│   │   │   ├── notification_service.py # Notification dispatch
│   │   │   └── export_service.py    # CSV/data export
│   │   │
│   │   ├── repositories/            # Data access abstraction
│   │   │   ├── base.py              # Generic AsyncRepository with CRUD
│   │   │   ├── customer_repository.py # Customer-specific queries
│   │   │   ├── event_repository.py  # Event queries
│   │   │   ├── analytics_repository.py # Analytics aggregation queries
│   │   │   ├── segment_repository.py# Segment queries
│   │   │   └── notification_repository.py # Notification queries
│   │   │
│   │   ├── tasks/                   # Kafka consumer workers
│   │   │   ├── worker_base.py       # Shared: locks, retries, DLQ, metrics
│   │   │   ├── twin_builder.py      # Consumes twin.cx.twin.build
│   │   │   ├── simulation_worker.py # Consumes twin.cx.simulation
│   │   │   ├── prediction_worker.py # Consumes twin.cx.prediction
│   │   │   └── notification_worker.py # Consumes twin.cx.notification
│   │   │
│   │   └── main.py                  # FastAPI app factory, startup/shutdown hooks
│   │
│   ├── alembic/                     # Database migrations
│   ├── seed_data.py                 # Demo data seeder
│   └── requirements.txt             # Python dependencies
│
├── frontend/
│   ├── src/
│   │   ├── features/                # Page-level feature modules
│   │   │   ├── dashboard/           # Executive dashboard
│   │   │   ├── twin-explorer/       # Twin browsing + detail views
│   │   │   ├── simulation-lab/      # Simulation creation + monitoring
│   │   │   ├── scenario-comparison/ # Side-by-side scenario matrix
│   │   │   └── auth/                # Login page
│   │   ├── components/              # Reusable UI components (layout, charts)
│   │   ├── api/                     # Axios service layer
│   │   ├── store/                   # Zustand state stores
│   │   ├── hooks/                   # Custom React hooks
│   │   ├── types/                   # TypeScript type definitions
│   │   ├── router/                  # React Router configuration
│   │   └── utils/                   # Utility functions
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── tsconfig.json
│
├── docker-compose.yml               # Full stack orchestration
└── .env                             # Environment variables
```

---

## 3. How Everything Connects

### Request Flow

```
Browser (React SPA)
  │
  ├─ HTTP request ─→ FastAPI (uvicorn :8000)
  │                    │
  │                    ├─ AuthMiddleware: JWT → user_id, organization_id
  │                    ├─ RateLimitMiddleware: Token bucket
  │                    ├─ LoggingMiddleware: Request/Response logging
  │                    │
  │                    ├─ API Router → Service → Repository → PostgreSQL
  │                    │                  │
  │                    │                  ├─→ Redis (caching)
  │                    │                  ├─→ Qdrant (vector search)
  │                    │                  └─→ Kafka (async dispatch)
  │                    │
  │                    └─ Response ─→ Browser
  │
  └─ Kafka Messages ─→ Background Workers
                         ├─ TwinBuilder → PostgreSQL, Qdrant
                         ├─ SimulationWorker → PostgreSQL
                         ├─ PredictionWorker → PostgreSQL, MLflow
                         └─ NotificationWorker → PostgreSQL
```

### Data Dependency Chain

```
Events → Twin → Predictions
  │       │       │
  │       ├─→ Recommendations (via Qdrant similarity)
  │       ├─→ Segments (via ML clustering)
  │       └─→ Simulations (agents derived from twins)
  │
  └─→ Campaign Attribution (event.campaign_id → CampaignTarget)
```

---

## 4. Core Infrastructure Files

### `config.py` — All Configuration

Uses `pydantic-settings` to load from `.env`. Key settings:

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://...` | PostgreSQL connection |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Kafka brokers |
| `QDRANT_HOST` / `QDRANT_PORT` | `localhost` / `6333` | Qdrant connection |
| `JWT_SECRET_KEY` | Generated | JWT signing key |
| `JWT_ALGORITHM` | `HS256` | JWT algorithm |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Access token TTL |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | `30` | Refresh token TTL |
| `JWT_ISSUER` | `PROMETHEUS` | JWT issuer claim |
| `JWT_AUDIENCE` | `prometheus-api` | JWT audience claim |
| `SECURITY_BCRYPT_ROUNDS` | `12` | Password hash rounds |
| `SECURITY_MAX_LOGIN_ATTEMPTS` | `5` | Before lockout |
| `SECURITY_LOCKOUT_DURATION_MINUTES` | `30` | Lockout time |
| `SECURITY_PASSWORD_MIN_LENGTH` | `8` | Min password length |
| `SECURITY_MFA_ENABLED` | `True` | Enable MFA |
| `EMBEDDING_MODEL_NAME` | `all-MiniLM-L6-v2` | SentenceTransformer model |
| `MLFLOW_TRACKING_URI` | `http://localhost:5000` | MLflow server |
| `CACHE_TTL_RECOMMENDATION` | Configured | Recommendation cache TTL |

### `database.py` — Async SQLAlchemy

- Creates `AsyncEngine` with `create_async_engine(DATABASE_URL, pool_size=20, max_overflow=10)`
- `async_session_factory` → `async_sessionmaker` for creating database sessions
- `get_session()` → FastAPI `Depends()` that yields an auto-committing session

### `redis.py` — Redis Client Wrapper

`RedisClient` class wrapping `redis.asyncio`:
- `connect()` / `disconnect()` — lifecycle management
- `get(key)` / `set(key, value, ttl)` — JSON serialization/deserialization
- `delete(*keys)` — cache invalidation
- `setnx(key, value, ttl)` — distributed locking (returns bool)
- `keys(pattern)` — pattern matching for bulk operations

### `kafka.py` — Kafka Client Wrapper

`KafkaClient` wrapping `aiokafka`:
- `connect()` — creates `AIOKafkaProducer`
- `produce(topic, message, key)` — JSON-serialized message production
- `consume(topic, group_id, handler)` — creates `AIOKafkaConsumer`, runs handler per message in a loop
- `disconnect()` — cleanup

### `qdrant.py` — Qdrant Client

- Creates `AsyncQdrantClient(host, port)` on startup
- Used by `EmbeddingService` (write) and `RecommendationService` (read)

### `main.py` — FastAPI Application Factory

- Registers CORS middleware (allows all origins in dev)
- Registers `AuthMiddleware`, `LoggingMiddleware`, `RateLimitMiddleware`
- Startup hook: connects Redis, Kafka, initializes Qdrant collections, runs Alembic migrations
- Shutdown hook: disconnects Redis, Kafka
- `/health` and `/ready` endpoints
- Mounts the v1 API router at `/api/v1`

---

## 5. Database Models — Every Table, Every Column

### `base.py`
- **`Base`**: SQLAlchemy `DeclarativeBase` — all models inherit from this
- **`TimestampMixin`**: Adds `created_at` and `updated_at` (auto-set on insert/update)
- **`UUIDMixin`**: Adds `id` as UUID primary key (auto-generated)

### `organization.py` — `organizations` table
| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | UUIDMixin |
| `name` | String(255) | NOT NULL |
| `slug` | String(100) | UNIQUE, NOT NULL |
| `domain` | String(255) | Nullable |
| `logo_url` | Text | Nullable |
| `plan` | String(50) | Default: "enterprise" |
| `settings` | JSONB | Default: {} |
| `features` | JSONB | Default: {} |
| `max_customers` | Integer | Default: 100000 |
| `max_users` | Integer | Default: 100 |
| `is_active` | Boolean | Default: True |
| `trial_ends_at` | DateTime | Nullable |
| + TimestampMixin | | `created_at`, `updated_at` |

### `user.py` — `users` table
| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `organization_id` | UUID FK→organizations | CASCADE |
| `email` | String(255) | NOT NULL |
| `password_hash` | String(255) | bcrypt, NOT NULL |
| `first_name` | String(100) | NOT NULL |
| `last_name` | String(100) | NOT NULL |
| `avatar_url` | Text | Nullable |
| `job_title` | String(255) | Nullable |
| `department` | String(100) | Nullable |
| `phone` | String(50) | Nullable |
| `is_active` | Boolean | Default: True |
| `is_verified` | Boolean | Default: False |
| `mfa_enabled` | Boolean | Default: False |
| `mfa_secret` | Text | TOTP secret, Nullable |
| `last_login_at` | DateTime | Nullable |
| `failed_login_attempts` | Integer | Default: 0 |
| `locked_until` | DateTime | Nullable |
| `password_changed_at` | DateTime | NOT NULL |
| `password_expires_at` | DateTime | Nullable |
| `reset_token` | String(255) | Nullable |
| `reset_token_expires_at` | DateTime | Nullable |

### `role.py` — `roles`, `permissions`, `user_roles` tables

**roles:**
| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `organization_id` | UUID FK | |
| `name` | String(100) | NOT NULL |
| `description` | Text | Nullable |
| `is_system` | Boolean | Default: False |
| `priority` | Integer | Default: 0 |
| `created_at` | DateTime | |

**permissions:**
| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `role_id` | UUID FK→roles | CASCADE |
| `resource` | Enum | `customers, campaigns, simulations, analytics, users, settings, billing, integrations, segments, predictions, twins, notifications` |
| `action` | Enum | `create, read, update, delete, manage, execute` |
| `conditions` | JSONB | Nullable |

**user_roles:** (composite PK)
| Column | Type |
|---|---|
| `user_id` | UUID FK→users (PK) |
| `role_id` | UUID FK→roles (PK) |
| `assigned_by` | UUID FK→users |
| `assigned_at` | DateTime |

### `customer.py` — 7 tables

**`customers`** — the end-customer being tracked (30+ columns, see ARCHITECTURE.md for full list)

**`customer_profiles`** — enriched B2B profile data (title, company, industry, annual_revenue, linkedin, psychographic_segment, enrichment_status, etc.)

**`customer_sessions`** — web sessions (session_id, started_at, ended_at, duration, pages_viewed, device/browser info, is_bounce, conversion_value)

**`customer_preferences`** — communication preferences per channel (channel_email/sms/push/in_app booleans, frequency settings, quiet hours, preferred_categories/brands, DND flag)

**`customer_interests`** — interest categories with scores (category, subcategory, interest_level, affinity_score, interaction_count)

**`customer_embeddings`** — vector storage in PostgreSQL mirror (embedding_vector as ARRAY(Float), embedding_model, embedding_dimensions=384)

**`customer_segments`** — segment definitions (name, description, rules as JSONB, source, is_dynamic, cluster_id, ml_model_id, customer_count, refresh_interval)

**`customer_segment_mapping`** — many-to-many join (customer_id, segment_id, organization_id, confidence_score, assigned_by, assigned_at)

### `twin.py` — 3 tables

**`customer_twins`** — the digital twin (see ARCHITECTURE.md for full 25+ column breakdown)

**`twin_snapshots`** — versioned snapshots (twin_id, snapshot_type, snapshot_data as JSONB, scores as JSONB, valid_from, valid_until)

**`predictions`** — ML predictions (prediction_type, prediction_value, prediction_probability, prediction_label, prediction_explanation, feature_importance, confidence_score, model_version="v1.0", model_name="prometheus_heuristic", input_features, valid_until, is_active)

### `event.py` — `customer_events` table
Range-partitioned by `event_timestamp`. Composite PK on `(id, event_timestamp)`. Has unique partial index on `(organization_id, idempotency_key)` where `idempotency_key IS NOT NULL`. Full column list in ARCHITECTURE.md.

### `simulation.py` — 3 tables
**`simulations`**, **`simulation_runs`** (per-iteration records with runtime_seconds, cpu_usage, memory_usage_bytes, error_message), **`simulation_results`** (aggregated outcomes). Full breakdown in ARCHITECTURE.md.

### `campaign.py` — 3 tables
**`campaigns`** (full lifecycle with segments/targets/exclusions, AB test config, frequency capping, budget), **`campaign_targets`** (per-customer targeting with delivery/open/click/convert timestamps, revenue, engagement_score), **`campaign_results`** (aggregate metrics with rate calculations, ROI, channel/segment/hourly breakdowns, AB test results)

### `notification.py` — `notifications` table
Status lifecycle: pending → sent → delivered → opened → clicked | bounced | failed. Has retry_count/max_retries (default 3), template support, scheduling.

### `recommendation.py` — 2 tables
**`recommendations`** (type, title, description, score, rank, category, is_actionable, is_applied, source, expires_at) and **`recommendation_feedback`** (recommendation_id, feedback_type, timestamp).

### `audit.py` — `audit_logs` table
Tracks actor_id, action, resource_type, resource_id, changes as JSONB, ip_address, user_agent, success flag, error_message.

---

## 6. Services — What Each One Does

### `twin_service.py` (55KB — the largest file)

**Purpose:** Builds, rebuilds, and manages customer digital twins.

**Key Methods:**
- `get_or_build_twin(org_id, customer_id)` — Returns existing twin or builds from scratch
- `rebuild_twin(org_id, customer_id)` — Forces full rebuild by deleting and recreating
- `update_twin_from_event(org_id, customer_id, event)` — Incremental update when new event arrives
- `get_org_summary(org_id)` — Aggregate stats across all twins in an org

**Internal Computations (each is a private method):**
1. `_compute_behavior_profile()` — Queries all events, computes behavior_score and sub-scores (engagement, purchase_activity, session_depth, communication_response, recency), calculates sessions_per_week, avg_session_duration, bounce_rate, email_open/click rates, purchase_frequency, AOV, cart_abandonment_rate, RFM scores and segment, lifecycle_stage
2. `_compute_interest_graph()` — Groups events by category, ranks by interaction count, builds nodes with name+weight, identifies dominant_category and interest_diversity
3. `_compute_memory_profile()` — Aggregates campaign responses, purchase history by category, channel interaction history, discount sensitivity, seasonality patterns
4. `_compute_channel_affinity()` — Per-channel (email, sms, push, in_app): counts interactions, conversions, computes affinity score, identifies preferred time
5. `_compute_sentiment()` — Derives sentiment from event data, builds trending array
6. `_compute_risk_indicators()` — Calculates churn_probability, churn_risk_level, churn_triggers, engagement_decline_rate, complaint_count, support_ticket_count, unsubscribe_risk
7. `_compute_intent_forecast()` — Purchase/engagement intent at 7d and 30d horizons, churn risk projections, predicted LTV at 90d
8. `_compute_twin_output()` — Final summary: sentiment, purchase_intent, churn_probability, lifetime_value, next_best_action
9. `_compute_engagement_score()` — Weighted formula combining sub-scores
10. `_compute_loyalty_score()` — Based on tenure, purchase frequency, recency
11. `_compute_confidence_score()` — How reliable the twin data is (based on data completeness)
12. `_compute_staleness_score()` — How outdated (based on last_event_at vs now)

### `agent_simulation.py` (40KB — second largest)

**Purpose:** The Monte Carlo simulation mathematical engine.

**Key Classes:**
- `SimulationAgent` — Virtual customer with: loyalty (Beta dist), disposable_budget (LogNormal dist), engagement_base (jittered from twin), channel_preference, discount_sensitivity
- `MonteCarloEngine` — Runs N iterations, each with M agents, aggregates results

**Key Functions:**
- `generate_agents(twins, config)` — Converts customer twins into stochastic agents
- `simulate_campaign_response(agent, campaign_params)` — Sigmoid-based probability model
- `compute_churn_impact(agent, campaign_action)` — Churn delta from campaign interaction
- `aggregate_results(iterations)` — Mean, std, confidence intervals
- `compute_confidence_intervals(data, confidence_level)` — z-score based CIs

### `simulation_service.py`

**Purpose:** Orchestrates simulation lifecycle.

**Key Methods:**
- `create_simulation(org_id, data)` → creates DB record
- `run_simulation(simulation_id)` → loads config, fetches twins by segment, calls agent_simulation engine, stores results
- `get_forecast(simulation_id)` → generates forecast from results (expected_revenue, expected_roi, expected_churns, expected_conversions, sensitivity analysis)

### `embedding_service.py`

**Purpose:** Generates and stores vector embeddings using SentenceTransformers + Qdrant.

**Key Methods:**
- `initialize()` — Creates Qdrant collections (`customer_embeddings`, `event_embeddings`) with 384-dim Cosine distance
- `generate_customer_embedding(customer, twin)` — Builds text from customer attributes → encodes with `all-MiniLM-L6-v2` → upserts to Qdrant + PostgreSQL
- `embed_event(event)` — Encodes event metadata → upserts to Qdrant `event_embeddings`
- Model is loaded once (lazy singleton) via `_load_model()`

### `prediction_service.py`

**Purpose:** ML predictions for churn, purchase intent, and LTV.

**Prediction Types:**
- `get_churn_prediction()` — Tries MLflow model `prometheus_churn`, falls back to heuristic: `staleness*0.3 + (1-engagement)*0.25 + (1-loyalty)*0.2 + sentiment*0.15 + recency*0.1`. Valid 7 days.
- `get_intent_prediction()` — Tries MLflow `prometheus_intent`, falls back to engagement/loyalty formula. Valid 3 days.
- `get_ltv_prediction()` — Tries MLflow `prometheus_ltv`, falls back to `current_ltv + growth_rate * 500`. Valid 30 days.
- `run_batch_predictions(org_id, type)` — Runs predictions for all active customers

**Feature Vector (16 dimensions):**
```
[engagement_score, loyalty_score, staleness_score, lifetime_value,
 events_30d, events_90d, purchases_90d, purchase_value_90d,
 avg_sentiment, sentiment_count, behavior_score,
 sub_engagement, sub_purchase_activity, sub_session_depth,
 sub_communication_response, sub_recency]
```

### `recommendation_service.py`

**Purpose:** Personalized recommendation engine.

**Two Approaches Combined:**
1. **Collaborative Filtering** — Uses Qdrant vector similarity to find customers with similar embeddings, then surfaces their successful recommendations
2. **Content-Based** — Uses twin profile (lifecycle stage, engagement level, interests, channel affinity) to generate contextual recommendations

Results are deduplicated, ranked by score (adjusted by customer engagement), and cached in Redis.

### `analytics_service.py`

**Purpose:** Dashboard and analytics computations.

**Key Methods:**
- `get_dashboard(org_id)` — Aggregates: total_customers, total_events, total_revenue, avg_engagement, avg_loyalty, churn_rate, active_campaigns, engagement_trend, revenue_trend, top_segments, recent_events
- `get_revenue_analytics(org_id, date_from, date_to, granularity)` — Revenue over time
- `get_engagement_trend(org_id, date_from, date_to)` — Engagement scores over time
- `get_churn_analytics(org_id, date_from, date_to)` — Churn rates, at-risk counts, reasons
- `compare_campaigns(org_id, campaign_ids)` — Side-by-side campaign performance
- `get_segment_analytics(segment_id, org_id)` — Per-segment KPIs

### `customer_service.py`

**Purpose:** Customer lifecycle management.

**Key Features:**
- Standard CRUD (create, read, update, soft-delete)
- `batch_create()` — Bulk customer creation
- `merge_customers(primary, secondary)` — Merges duplicate customers: transfers events, profiles, preferences, embeddings, twins, predictions, interests, segment mappings from secondary to primary. Deactivates secondary.
- `get_customer_journey(customer_id)` — Timeline of all events + profile + segments
- `get_lookalike_candidates(seed_customer_id)` — Finds similar customers by twin confidence scores
- `search_by_rfm(org_id, rfm_segment)` — Search by RFM segment

### `event_service.py`

**Purpose:** Event ingestion and processing pipeline.

**Ingestion Flow:**
1. Validate event_type and event_name
2. Resolve customer (by email or external_id if customer_id not provided)
3. Create Event record in PostgreSQL
4. Update customer's `first_seen_at` / `last_seen_at`
5. Invalidate dashboard cache in Redis
6. Produce to Kafka topic `twin.cx.events.raw`
7. Generate event embedding via EmbeddingService → Qdrant

**Processing (called by TwinBuilder worker):**
- `process_event()` — Updates twin from event, handles purchase→campaign conversion attribution

### `campaign_service.py`

**Purpose:** Full campaign lifecycle.

**Launch Flow:**
1. Validate status is "draft"
2. Build targets: query customers by segments, include/exclude lists
3. Create CampaignTarget records for each customer
4. Distribute: mark targets as "delivered", attach twin engagement scores
5. Create CampaignResult with aggregate counts

**Other:** pause, cancel, compute ROI (`(revenue - cost) / cost`)

### `segment_service.py`

**Purpose:** Customer segmentation (rule-based + ML).

**Rule-Based:**
- `_apply_rules(segment, org_id)` — Supports rules for: tags (array contains), min_engagement (twin score), event_types (has events of type), min_events (event count threshold)
- `recalculate_membership()` — Clears and reapplies rules

**ML-Based:**
- `discover_ml_segments(org_id)` — KMeans clustering on twin features:
  - Features: engagement, loyalty, staleness, LTV (normalized), avg_sentiment, purchase_activity, session_depth, recency
  - StandardScaler preprocessing
  - Optimal k via silhouette score (k=2–8)
  - Auto-names: "Champions", "Loyal Members", "Active Users", "High Value", "Needs Attention"

**Lookalike:** `create_lookalike(seed_segment, payload)` — Creates new segment based on existing one

### `auth_service.py`

**Purpose:** Authentication, registration, password management, MFA.

**Registration Flow:**
1. Check email uniqueness
2. Generate unique org slug from org name
3. Create Organization → Create User (bcrypt hash) → Create "Admin" Role → Assign UserRole
4. Return user + org

**Login Flow:**
1. Find user by email (case-insensitive)
2. Check active, not locked
3. Verify password (bcrypt)
4. Check MFA if enabled (TOTP via pyotp)
5. Reset failed attempts, update last_login_at
6. Generate access + refresh JWT tokens

### `notification_service.py`

**Purpose:** Notification dispatch and retry management.

### `export_service.py`

**Purpose:** CSV export of analytics data (customers, events, revenue reports).

---

## 7. API Endpoints — Every Route

### Router Aggregation (`router.py`)

```python
api_router.include_router(auth_router,    prefix="/auth",            tags=["Auth"])
api_router.include_router(customer_router, prefix="/customers",      tags=["Customers"])
api_router.include_router(twin_router,     prefix="/twins",          tags=["Twins"])
api_router.include_router(simulation_router, prefix="/simulations",  tags=["Simulations"])
api_router.include_router(event_router,    prefix="/events",         tags=["Events"])
api_router.include_router(analytics_router, prefix="/analytics",     tags=["Analytics"])
api_router.include_router(campaign_router, prefix="/campaigns",      tags=["Campaigns"])
api_router.include_router(recommendation_router, prefix="/recommendations", tags=["Recommendations"])
api_router.include_router(notification_router, prefix="/notifications", tags=["Notifications"])
api_router.include_router(segment_router,  prefix="/segments",       tags=["Segments"])
api_router.include_router(user_router,     prefix="/users",          tags=["Users"])
api_router.include_router(admin_router,    prefix="/admin",          tags=["Admin"])
```

Full endpoint list with 70+ routes is in ARCHITECTURE.md sections 8.1–8.5.

---

## 8. Background Workers — How Async Processing Works

### Worker Lifecycle

Each worker is a standalone Python process that:
1. Connects to Redis and Kafka
2. Starts consuming from its Kafka topic
3. For each message: acquires a Redis distributed lock → processes → commits DB → releases lock
4. On failure: retries with exponential backoff (2^n seconds), max 3 retries, then sends to Dead Letter Queue

### `twin_builder.py` (topic: `twin.cx.twin.build`, group: `twin-cx-builder`)

Processes twin build requests:
1. Acquire lock `lock:twin_builder:{org_id}:{customer_id}`
2. Create DB session
3. Call `TwinService.get_or_build_twin(org_id, customer_id)` or `rebuild_twin()`
4. Commit, record success metrics
5. On error: rollback, retry or DLQ

### `simulation_worker.py` (topic: `twin.cx.simulation`, group: `twin-cx-simulator`)

Processes simulation execution:
1. Acquire lock `lock:simulation_worker:{simulation_id}`
2. Call `SimulationService.run_simulation(simulation_id)`
3. On completion: commit, record metrics
4. On error: update simulation status to "failed", retry or DLQ

### `prediction_worker.py` (topic: `twin.cx.prediction`, group: `twin-cx-predictor`)

Two modes:
- **Single**: `PredictionService.get_churn_prediction(org, customer)` for one customer
- **Batch**: `PredictionService.run_batch_predictions(org, type)` for all active customers

### `notification_worker.py` (topic: `twin.cx.notification`, group: `twin-cx-notifier`)

Looks up notification by ID, calls `NotificationService.send(notification)`.

---

## 9. Schemas — Request/Response Contracts

### `common.py`

- **`APIResponse[T]`** — `{success: bool, data: T?, error: str?, message: str?}`
- **`PaginatedResponse[T]`** — `{data: T[], total, page, page_size, limit, total_pages, has_next, has_prev}`
- **`ErrorResponse`** — `{success: false, error, error_code, details}`

### `simulation.py` — SimulationCreate Validators

- `monte_carlo_iterations`: Must be ≥ 1
- `confidence_level`: Must be 0 < v < 1
- `time_horizon_days`: Must be ≥ 1
- Frontend sends `iterations` → mapped to `monte_carlo_iterations` via `@model_validator`
- Frontend sends `time_horizon` → mapped to `time_horizon_days`

### `twin.py` — 12 Response Schemas

`CustomerTwinResponse` nests: `BehaviorProfileResponse`, `InterestGraphResponse`, `MemoryProfileResponse`, `ChannelAffinityResponse`, `RiskIndicatorsResponse`, `IntentForecastResponse`, `TwinOutputResponse`

`PredictionResponse` has computed fields: `timestamp` (= created_at), `confidence` (= confidence_score or prediction_probability), `value` (= prediction_value)

---

## 10. Repositories — Data Access Layer

### `base.py` — AsyncRepository (Generic)

A reusable CRUD base class parameterized on model type:
- `get(id, organization_id)` — Single fetch
- `get_multi(skip, limit, filters, sorts, organization_id)` — Paginated list with dynamic filtering
- `create(data, organization_id)` — Insert
- `update(id, data, organization_id)` — Partial update
- `delete(id, soft=True, organization_id)` — Soft or hard delete

### Specialized Repositories

- **`customer_repository.py`** — `search_by_email()`, `search_by_external_id()`, `get_with_twin()`, `get_active_count()`
- **`event_repository.py`** — `get_date_range()`, `get_by_customer()`, `get_event_counts()`
- **`analytics_repository.py`** — Complex aggregation queries for dashboard, revenue, churn
- **`segment_repository.py`** — Segment-specific queries with customer count computation
- **`notification_repository.py`** — Notification status queries and stats

---

## 11. Middleware — Request Pipeline

### `auth.py` — AuthMiddleware

1. Check if path is public (login, register, refresh, docs, health)
2. If no `Authorization` header → **dev-mode bypass**: inject hardcoded dev org/user ID
3. If Bearer token present → decode JWT, extract `sub` (user_id), `organization_id`, `roles`, `permissions`
4. Set `request.state.user_id`, `request.state.organization_id`
5. Add `X-Request-ID` header to response

**Dev-mode defaults:**
- Org: `eb35c0b4-f66b-442b-b35a-30246d8df683`
- User: `00000000-0000-0000-0000-000000000001`

### `logging_middleware.py`
Logs each request: method, path, status_code, duration.

### `rate_limit.py`
Token bucket rate limiting (configured per route/globally).

---

## 12. How Twins Are Created (Step by Step)

### Trigger Points
1. **GET `/api/v1/twins/{customer_id}`** — if no twin exists, auto-builds
2. **POST `/api/v1/twins/{customer_id}/rebuild`** — manual rebuild
3. **Kafka worker** — receives build request on `twin.cx.twin.build`
4. **Event processing** — `EventService.process_event()` calls `twin_service.update_twin_from_event()`

### Full Build Process

1. **Load Customer Data**
   - Query `customers` table for basic info
   - Query `customer_profiles` for enriched data
   - Query `customer_events` for all behavioral events
   - Query `customer_sessions` for session data
   - Query `customer_interests` for interests
   - Query `customer_preferences` for communication prefs

2. **Compute Behavior Profile** (`_compute_behavior_profile`)
   - Count events by type (page_view, purchase, email_open, etc.)
   - Calculate sessions_per_week, avg_session_duration, page_depth_avg
   - Calculate bounce_rate, cart_abandonment_rate
   - Calculate email_open_rate, email_click_rate
   - Calculate purchase_frequency, avg_order_value
   - Score sub-components: engagement, purchase_activity, session_depth, communication_response, recency
   - Compute overall behavior_score (weighted average)
   - Determine RFM segment (recency × frequency × monetary scores 1-5)
   - Determine lifecycle_stage: new → onboarding → active → engaged → loyal → champion → at_risk → churned

3. **Compute Interest Graph** (`_compute_interest_graph`)
   - Group events by category from event_properties
   - Rank categories by interaction count
   - Build interest nodes: `{name, weight, interaction_count}`
   - Calculate interest_diversity (entropy-based)
   - Identify dominant_category

4. **Compute Memory Profile** (`_compute_memory_profile`)
   - Aggregate campaign responses from events with campaign_id
   - Build purchase category history
   - Track channel interaction timeline
   - Calculate discount_sensitivity from purchase events
   - Identify seasonality_patterns (monthly/weekly)

5. **Compute Channel Affinity** (`_compute_channel_affinity`)
   - Per channel (email, sms, push, in_app):
     - Count total interactions
     - Count conversions
     - Calculate affinity score = conversions / interactions (weighted)
     - Identify preferred_time_of_day

6. **Compute Scores**
   - `engagement_score` = weighted(behavior_sub_scores, channel_affinity, recency)
   - `loyalty_score` = f(tenure_days, purchase_frequency, rfm_score, recency)
   - `confidence_score` = data completeness metric (0-1)
   - `staleness_score` = time since last event (0=fresh, 1=very stale)

7. **Compute Predictions**
   - `sentiment_trend` — array of sentiment scores over time
   - `risk_indicators` — churn_probability, triggers, decline_rate
   - `intent_forecast` — purchase/engagement intent at 7d/30d, predicted LTV 90d
   - `twin_output` — final summary (sentiment, purchase_intent, churn, LTV, next_best_action)

8. **Persist Twin**
   - UPSERT into `customer_twins`
   - INSERT snapshot into `twin_snapshots`
   - Generate embedding via `EmbeddingService` → Qdrant + PostgreSQL

---

## 13. How Simulations Run (Step by Step)

### Trigger
`POST /api/v1/simulations/{id}/run` → adds `_bg_run_simulation` as a FastAPI BackgroundTask

### Execution Flow

1. **Load Configuration**
   - Read simulation from DB (name, type, parameters, agent_configuration)
   - Get monte_carlo_iterations, confidence_level, time_horizon_days
   - Get segment_ids, sample_size

2. **Fetch Customer Twins**
   - If segment_ids specified: query twins whose customer is in those segments
   - Otherwise: sample from all built twins
   - Cap at sample_size

3. **Generate Agents** (in `agent_simulation.py`)
   - For each twin → create SimulationAgent:
     ```
     loyalty = Beta(α=2+twin.loyalty*8, β=2+(1-twin.loyalty)*8)
     budget = LogNormal(μ=ln(twin.ltv+1), σ=0.5)
     engagement = twin.engagement * uniform(0.8, 1.2)
     channel_pref = max(twin.channel_affinity)
     ```

4. **Run Monte Carlo** (N iterations)
   - Each iteration:
     a. Resample agent parameters (new random draws)
     b. For each agent, simulate campaign response:
        - `P(open) = sigmoid(k * (loyalty*engagement - midpoint))`
        - `P(click) = P(open) * ctr_factor`
        - `P(convert) = sigmoid(loyalty, budget/price, discount)`
        - If converted: `revenue = budget * conversion_factor * (1 - discount)`
     c. Compute churn impact per agent
     d. Aggregate: total_opens, clicks, conversions, revenue, churn_delta
   - Store per-iteration results

5. **Aggregate Results**
   - Mean and std across all iterations for each metric
   - Confidence intervals: `mean ± z × std/√N`
   - Build monte_carlo_distribution (histogram data)
   - Risk assessment (probability of loss, worst case)
   - Generate recommendations

6. **Persist Results**
   - INSERT `simulation_results` with all aggregated data
   - INSERT `simulation_runs` records
   - UPDATE simulation: status="completed", progress=100.0, completed_at=now

---

## 14. How Predictions Work

### Types

| Type | MLflow Model | Fallback Formula | Cache Duration |
|---|---|---|---|
| **Churn** | `prometheus_churn` | `staleness*0.3 + (1-eng)*0.25 + (1-loy)*0.2 + neg_sentiment*0.15 + inactivity*0.1` | 7 days |
| **Intent** | `prometheus_intent` | `engagement*0.4 + loyalty*0.3 + 0.1` (purchase) / `engagement*0.5 + staleness_inv*0.3 + 0.1` (engagement) | 3 days |
| **LTV** | `prometheus_ltv` | `current_ltv + growth_rate*500` | 30 days |

### Flow
1. Check for active prediction (not expired) → return cached if valid
2. Collect features from events (30d, 90d counts, purchase counts, purchase value)
3. Try ML model (MLflow → joblib fallback)
4. If no model: use heuristic formula
5. Compute confidence (based on twin data completeness)
6. Store in `predictions` table with expiry

### Labels
- Churn: "high" (≥0.7), "medium" (≥0.4), "low" (<0.4)
- Intent: "high_intent" (>0.7), "medium_intent" (>0.4), "low_intent"
- LTV: "high_value" (>$1000), "medium_value" (>$100), "low_value"

---

## 15. How Recommendations Work

### Two Strategies Combined

**1. Collaborative Filtering (via Qdrant):**
- Lookup target customer's embedding in Qdrant `customer_embeddings`
- Vector similarity search (HNSW, ef=128, cosine) to find similar customers
- Fetch those customers' successful recommendations from PostgreSQL
- Filter for actionable + recent (applied in last 30 days or not applied)

**2. Content-Based (from Twin Profile):**
- If low engagement → suggest re-engagement
- If lifecycle_stage is early → suggest onboarding
- If dominant_category exists → suggest category-specific campaigns
- If preferred channel identified → suggest channel preference
- Fill remaining slots with active campaigns

### Ranking
- Deduplicate by title
- Adjust scores by customer engagement level: `score *= (0.5 + 0.5 * engagement)`
- Sort descending, cap at limit
- Cache in Redis

---

## 16. How Segmentation Works

### Rule-Based Segments
Segments have a `rules` JSONB field. Supported rules:
- `tags`: Array containment check on customer.tags
- `min_engagement`: Twin engagement_score ≥ threshold
- `event_types`: Customer has events of specified types
- `min_events`: Customer has ≥ N total events

When rules change, `recalculate_membership()` clears all mappings and re-evaluates all customers.

### ML-Discovered Segments
`discover_ml_segments()`:
1. Load all built twins for the org
2. Build 8-dim feature vectors
3. StandardScaler normalization
4. Test KMeans for k=2..8, pick best silhouette score
5. Create CustomerSegment records with auto-generated names
6. Insert CustomerSegmentMapping for each cluster member

### Lookalike Segments
Creates a new segment with metadata referencing the seed segment. Currently stores config but doesn't auto-populate (placeholder for Qdrant-based similarity expansion).

---

## 17. How Campaigns Work

### Campaign Lifecycle
`draft` → `launching` → `active` → `paused` → `completed` / `cancelled` / `failed`

### Launch Process
1. Validate status is "draft"
2. **Build Targets:** Query customers matching segments + explicit targets - exclusions
3. **Create CampaignTarget** records (one per customer)
4. **Distribute:** Mark targets as "delivered", attach twin engagement scores
5. **Create CampaignResult** with initial aggregate counts

### Result Computation
Aggregates from CampaignTarget statuses:
- Delivered / Opened / Clicked / Converted counts
- Revenue sum
- Open rate, click rate, conversion rate
- ROI = (revenue - cost) / cost

### Campaign Simulation
`POST /{campaign_id}/simulate` — uses CampaignService to trigger a simulation specifically for that campaign.

---

## 18. Frontend Architecture

### Technology
- **React 18** with **TypeScript 5.6**
- **Vite 5** build system
- **Tailwind CSS 3** for styling
- **Radix UI** for accessible component primitives (Dialog, Dropdown, Select, Tabs, Tooltip, ScrollArea, Popover, AlertDialog, Progress, Label, Slot)
- **Recharts 2** for data visualization
- **Zustand 5** for global state management
- **TanStack React Query 5** for server state/caching
- **React Router DOM 6** with lazy-loaded routes
- **React Hook Form + Zod** for form validation
- **Lucide React** for icons

### Pages

| Route | Component | Purpose |
|---|---|---|
| `/dashboard` | DashboardPage | Executive KPIs, charts, trends |
| `/twins` | TwinExplorerPage | Browse customer twins, list view |
| `/twins/:twinId` | TwinExplorerPage | Individual twin detail (scores, interests, channels, predictions) |
| `/simulation-lab` | SimulationLabPage | Create simulations, configure params, run, view results |
| `/simulations/compare` | ScenarioComparisonPage | Compare multiple simulation scenarios side-by-side |
| `/login` | LoginPage | Email/password authentication |

### API Layer
- `api.ts` — Axios instance with base URL `http://localhost:8000/api/v1`, request interceptor adds Bearer token, response interceptor redirects to `/login` on 401
- Service files: `customers.service.ts`, `twins.service.ts`, `simulations.service.ts`, `analytics.service.ts`, `predictions.service.ts`

### State Management
- `auth-store.ts` (Zustand) — Stores `accessToken`, `refreshToken`, `user`, `organization`, persisted to localStorage

---

## 19. External Services Integration

### PostgreSQL (Primary Data Store)
- All business data persisted via SQLAlchemy async ORM
- Connection pool: size=20, max_overflow=10
- Events table is range-partitioned by timestamp
- Alembic for schema migrations

### Redis (Cache + Distributed Locks)
- Dashboard cache invalidation on new events
- Recommendation caching with configurable TTL
- Distributed processing locks (worker deduplication, 300s TTL)
- Worker metrics storage (counters + rolling latency window)

### Apache Kafka (Event Streaming)
- KRaft mode (no ZooKeeper)
- 7 topics (events.raw, twin.build, simulation, prediction, notification, retry, dead.letter)
- 4 consumer groups (one per worker type)
- JSON message serialization
- Retry queue with exponential backoff, DLQ after 3 failures

### Qdrant (Vector Database)
- 2 collections: `customer_embeddings` (384-dim, cosine), `event_embeddings` (384-dim, cosine)
- Write: EmbeddingService upserts during twin build and event ingestion
- Read: RecommendationService performs HNSW similarity search for collaborative filtering
- HNSW parameters: ef=128, exact=False, score_threshold=0.3

### SentenceTransformers
- Model: `all-MiniLM-L6-v2` (384-dimension embeddings)
- Lazy-loaded singleton (loaded once on first use)
- Used to encode customer profiles and events into vectors

### MLflow (Optional ML Model Registry)
- Tracking URI: configurable
- Models: `prometheus_churn`, `prometheus_intent`, `prometheus_ltv`
- Loads from `/Production` stage
- Falls back to local joblib files or heuristic formulas

---

## 20. Environment Configuration

### Docker Compose Services

| Service | Image | Ports | Volumes |
|---|---|---|---|
| postgres | postgres:16-alpine | 5432 | pgdata volume |
| redis | redis:7-alpine | 6379 | — |
| kafka | bitnami/kafka:latest | 9092 | kafkadata volume |
| qdrant | qdrant/qdrant:latest | 6333, 6334 | qdrantdata volume |
| backend | ./backend Dockerfile | 8000 | code mount |
| frontend | ./frontend Dockerfile | 5173 | code mount |

### Key .env Variables

```
DATABASE_URL=postgresql+asyncpg://prometheus:prometheus@localhost:5432/prometheus
REDIS_URL=redis://localhost:6379/0
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
QDRANT_HOST=localhost
QDRANT_PORT=6333
JWT_SECRET_KEY=<secret>
CORS_ORIGINS=http://localhost:5173
```
