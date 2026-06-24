# PROMETHEUS Backend Freeze Audit & Contract

This document serves as the **final backend contract** for PROMETHEUS. It details the status of all route groups, stable request/response schemas, database models, known integration risks, and deprecated endpoints. 

> [!IMPORTANT]
> **Frontend integration must only use SAFE routes.** Any future schema or route changes must be formally documented as modifications to this contract.

---

## Route Group Risk Assignments

Each API route group has been audited against the frontend `api-client.ts` definitions and backend implementation.

| Route Group | Base Prefix | Status | Summary of Contract Alignment |
| :--- | :--- | :--- | :--- |
| **Authentication** | `/api/v1/auth` | **SAFE** | Fully aligned. Core endpoints (`login`, `register`, `refresh`, `logout`, `me`) match. |
| **Users** | `/api/v1/users` | **SAFE** | Core user & role endpoints match backend schemas. |
| **Customers** | `/api/v1/customers` | **SAFE** | Core CRUD endpoints match. *Note minor caution on twin score scaling differences.* |
| **Digital Twins** | `/api/v1/twins` | **CAUTION** | Core twin retrieval, rebuilding, and predictions exist, but have critical field omissions and type mismatches. |
| **Events** | `/api/v1/events` | **SAFE** | Core single and batch ingestion endpoints are fully implemented and aligned. |
| **Campaigns** | `/api/v1/campaigns` | **SAFE** | CRUD, launching, pausing, cancelling, and results endpoints match. |
| **Simulations** | `/api/v1/simulations` | **SAFE** | Fully aligned. Monte Carlo config parameters are mapped correctly on both ends. |
| **Notifications** | `/api/v1/notifications` | **SAFE** | Core sending, listing, retrying, and stat endpoints match. |
| **Analytics** | `/api/v1/analytics` | **SAFE** | Core dashboards, custom queries, revenue, engagement, and churn trend endpoints are stable. |
| **Segments** | `/api/v1/segments` | **CAUTION** | Listing, retrieving, creating, and lookalikes match, but the specific segment compute route is mismatched. |
| **Recommendations**| `/api/v1/recommendations` | **UNSTABLE** | Critical route mismatch on personalized retrieval. Calling this will result in 404s in frontend. |
| **Administration** | `/api/v1/admin` | **CAUTION** | Standard user and config routes are aligned, but feature-flag editing, job logs, and rate-limits are missing. |

---

## 1. Stable Routes (SAFE to Use)

The following endpoints are verified, fully implemented in the backend, and directly aligned with frontend expectations.

### Authentication (`/api/v1/auth`)
* `POST /api/v1/auth/login` — Authenticates user credentials.
* `POST /api/v1/auth/register` — Registers a new user and organization.
* `POST /api/v1/auth/refresh` — Refreshes the JWT access token.
* `POST /api/v1/auth/logout` — Revokes/invalidates the session.
* `GET /api/v1/auth/me` — Retrieves current user profile.

### Customers (`/api/v1/customers`)
* `GET /api/v1/customers` — Lists customers with search/filtering parameters.
* `POST /api/v1/customers` — Creates a new customer.
* `GET /api/v1/customers/search` — Performs database queries for customer auto-complete.
* `POST /api/v1/customers/batch` — Bulk customer ingestion.
* `GET /api/v1/customers/{customer_id}` — Retrieves customer detail.
* `PUT /api/v1/customers/{customer_id}` — Updates customer properties.
* `DELETE /api/v1/customers/{customer_id}` — Deactivates customer (soft-delete).
* `GET /api/v1/customers/{customer_id}/events` — Paginated event timeline for a customer.
* `GET /api/v1/customers/{customer_id}/segments` — List of segments a customer belongs to.

### Events (`/api/v1/events`)
* `POST /api/v1/events` — Ingests a single behavioral event.
* `POST /api/v1/events/batch` — Ingests multiple events in batch.
* `GET /api/v1/events` — Query and list ingested event streams.
* `GET /api/v1/events/summary` — Event type and channel aggregates.

### Campaigns (`/api/v1/campaigns`)
* `GET /api/v1/campaigns` — Lists marketing campaigns.
* `POST /api/v1/campaigns` — Creates a campaign.
* `GET /api/v1/campaigns/{campaign_id}` — Campaign properties and configurations.
* `PUT /api/v1/campaigns/{campaign_id}` — Updates a campaign.
* `POST /api/v1/campaigns/{campaign_id}/launch` — Deploys campaign.
* `POST /api/v1/campaigns/{campaign_id}/pause` — Pauses campaign execution.
* `POST /api/v1/campaigns/{campaign_id}/cancel` — Aborts campaign.
* `GET /api/v1/campaigns/{campaign_id}/results` — Aggregated metrics and variant response splits.

### Simulations (`/api/v1/simulations`)
* `GET /api/v1/simulations` — Lists simulation runs.
* `POST /api/v1/simulations` — Creates and schedules a Monte Carlo simulation.
* `GET /api/v1/simulations/{simulation_id}` — Retrieves configuration and results.
* `POST /api/v1/simulations/{simulation_id}/run` — Forces a simulation run.
* `GET /api/v1/simulations/{simulation_id}/results` — Detailed outputs (expected ROI, revenue intervals).
* `GET /api/v1/simulations/{simulation_id}/forecast` — Forecast timeline dates and lower/upper bounds.

### Notifications (`/api/v1/notifications`)
* `GET /api/v1/notifications` — Audit notification dispatch history.
* `POST /api/v1/notifications` — Dispatches message (email/SMS/push).
* `GET /api/v1/notifications/stats` — Metrics on delivery rates and error logs.
* `GET /api/v1/notifications/{notification_id}` — Retrieves dispatch record status.
* `POST /api/v1/notifications/{notification_id}/retry` — Retries a failed notification.

### Analytics (`/api/v1/analytics`)
* `GET /api/v1/analytics/dashboard` — Retrieves aggregate business metrics (active users, total revenue, churn trends).
* `POST /api/v1/analytics/query` — Runs custom database analytical aggregations.
* `GET /api/v1/analytics/revenue` — Revenue growth metrics and channel splits.
* `GET /api/v1/analytics/engagement` — Active user trends and communication response logs.
* `GET /api/v1/analytics/churn` — Churn predictions and segment retention splits.

---

## 2. Stable Schemas

The following schemas are declared final. Any additions or changes will break JSON serializers.

### Customer Schemas
* **`CustomerResponse`**: Declares standard profile schemas (`id`, `email`, `phone`, `first_name`, `last_name`, `timezone`, `locale`, `tags`, `custom_attributes`, `consent_marketing`, `consent_analytics`, `consent_profiling`).
* **`CustomerListResponse`**: Extends `CustomerResponse` to add fields pre-computed from the Twin engine: `engagement_score`, `loyalty_score`, `churn_risk`, `ltv`, `last_activity`, `segments`.

### Simulation Schemas
* **`SimulationCreate`**: Accepts input fields (`name`, `iterations`, `time_horizon`, `confidence_level`, `segment_ids`, `parameters`). The backend maps `iterations` to `monte_carlo_iterations` and `time_horizon` to `time_horizon_days` automatically.
* **`SimulationResponse`**: Returns the nested `config` structure (`iterations`, `time_horizon`, `confidence_level`, `segment_ids`, `parameters`) matching the frontend's TypeScript interface.
* **`SimulationResultResponse`**: Structures Monte Carlo simulation output (`aggregated_metrics`, `confidence_intervals`, `monte_carlo_distribution`, `expected_outcomes`, `risk_assessment`).

---

## 3. Stable Models

The backend utilizes SQLAlchemy models mapping to Postgres tables. The following tables have frozen schemas:

* **`Customer`** (`customers`): Primary registry for demographic details and consent logs.
* **`CustomerTwin`** (`customer_twins`): Stores twin behavior summaries (`behavior_profile`, `interest_graph`, `memory_profile`, `channel_affinity`, `engagement_score`, `loyalty_score`, `lifetime_value`, `sentiment_trend`).
* **`Prediction`** (`customer_predictions`): Prediction logs (`prediction_type` mapped to enum: `churn`, `ltv`, `conversion`, `engagement`, `sentiment`, `intent`, `next_best_action`).
* **`Simulation`** (`simulations`): Monte carlo inputs and target metrics.
* **`SimulationResult`** (`simulation_results`): Outputs including confidence boundaries.

---

## 4. Known Contract Risks (CAUTION / UNSTABLE)

The following gaps present significant risks to frontend operation.

### 4.1 Recommendations Endpoint Mismatch (UNSTABLE)
* **Risk**: Frontend calls `GET /api/v1/recommendations/{customer_id}` to retrieve personalized recommendation cards.
* **Backend Truth**: The backend implements `GET /api/v1/recommendations/{customer_id}/personalized`. Calling the frontend's current path will yield **404 Not Found**.
* **Impact**: The recommendations screen in the customer profile will be completely broken.

### 4.2 Segment Computation Mismatch (CAUTION)
* **Risk**: Frontend invokes `POST /api/v1/segments/{segment_id}/compute` to recalculate member rules.
* **Backend Truth**: The backend expects `POST /api/v1/segments/{segment_id}/refresh`. Calling the frontend's path will throw a **404 Not Found**.
* **Impact**: Recalculating customer segmentation will fail on the UI.

### 4.3 Twin Scores Scale Discrepancy (CAUTION)
* **Risk**: The backend twin service returns all scores (`engagement_score`, `loyalty_score`, `confidence_score`, `staleness_score`) scaled to `0.0 - 1.0` (e.g. `0.85`).
* **Frontend UI**: The React `ScoreGauge` renders these scores using `{Math.round(value)}%` assuming a `0 - 100` range. 
* **Impact**: The UI gauge will render a score of `1%` instead of `85%`. In contrast, the `/customers` index list correctly scales the scores out of `100.0`.

### 4.4 Twin Object Missing Fields (CAUTION)
* **Risk**: The backend `GET /api/v1/twins/{customer_id}` route uses a custom helper dictionary representation rather than `CustomerTwinResponse`.
* **Backend Truth**: It entirely omits `organization_id`, `lifetime_value`, and `version` from the JSON dictionary. It also returns the ISO format date in `last_rebuilt` instead of `built_at`.
* **Impact**: These properties will return `undefined` to the frontend, breaking UI components depending on twin lifecycle metadata.

### 4.5 sentiment_trend Type Contract Break (CAUTION)
* **Risk**: Frontend defines `sentiment_trend` in the `Twin` interface as `number[]`.
* **Backend Truth**: The backend returns `sentiment_trend` as an array of dictionaries: `[{"date": "day-0", "score": 0.8}, ...]`.
* **Impact**: While the frontend's chart has a fallback type check to handle both shapes, typescript compiles may raise flags if strict typing is enforced.

### 4.6 Missing Administration Endpoints (CAUTION)
* **Risk**: Frontend exposes pages to edit feature flags, view job queues, and monitor rate limits, calling:
  - `PUT /api/v1/admin/feature-flags/{key}`
  - `GET /api/v1/admin/jobs`
  - `GET /api/v1/admin/rate-limits`
* **Backend Truth**: The backend does **not** implement these endpoints.
* **Impact**: Triggering feature flag updates, visiting background job status, or inspecting rate limits on the admin dashboard will return **404/405 Errors**.

---

## 5. Deprecated Endpoints

* **`GET /api/v1/customers/new`**
  - **Status**: Deprecated.
  - **Reason**: Returns a static template dictionary `{"message": "New customer template"}`. The frontend uses client-side route templates and does not fetch from this endpoint.
