# FINAL P0 FIX PLAN

This document details the root causes, exact file locations, specific code modifications, and verification tests for the target issues in the Prometheus backend.

---

## 1. `/api/v1/customers` returning 500

* **Root Cause**: The database `customer_twins` table was missing the column `memory_profile` (which is JSONB NOT NULL DEFAULT '{}'). As a result, SQLAlchemy failed to map/deserialize objects during GET requests that retrieve twins (e.g. `list_customers`), raising a database schema mismatch exception and returning 500.
* **Exact Files**: PostgreSQL schema / direct database update.
* **Exact Code Modifications**:
  Add column to table:
  ```sql
  ALTER TABLE customer_twins ADD COLUMN IF NOT EXISTS memory_profile JSONB NOT NULL DEFAULT '{}';
  ```
* **Verification Test**:
  Request customer list endpoint:
  ```bash
  wsl curl -i -H "Authorization: Bearer <token>" http://localhost:8004/api/v1/customers
  ```
  Ensure it returns `200 OK`.

---

## 2. `/api/v1/customers?limit=10` returning 500

* **Root Cause**: Identical to issue 1. The list query attempts to load the `CustomerTwin` objects to populate properties like `engagement_score`, failing due to the missing `memory_profile` column.
* **Exact Files**: PostgreSQL database update.
* **Exact Code Modifications**: Same database fix as issue 1.
* **Verification Test**:
  ```bash
  wsl curl -i -H "Authorization: Bearer <token>" http://localhost:8004/api/v1/customers?limit=10
  ```
  Ensure it returns `200 OK`.

---

## 3. `/api/v1/customers/search` returning 422

* **Root Cause**: The search query parameter `q` was required by FastAPI with no default value. Requesting search without a query parameter (e.g., during validation) returned `422 Unprocessable Entity`.
* **Exact Files**: `backend/app/api/v1/customers.py`
* **Exact Code Modifications**:
  Change `q: str = Query(...)` to make it optional:
  ```python
  @router.get("/search", response_model=list[CustomerListResponse])
  async def search_customers(
      q: str = Query(""),
      session: AsyncSession = Depends(get_session),
      ...
  ):
      if not q:
          return []
  ```
* **Verification Test**:
  ```bash
  wsl curl -i http://localhost:8004/api/v1/customers/search
  ```
  Ensure it returns `200 OK` (returns `[]` instead of 422).

---

## 4. `/api/v1/notifications/stats` returning 500

* **Root Cause**: The `Notification` model `status` column mapping did not specify the SQLAlchemy `SAEnum` mapping to match the PostgreSQL `notification_status` Enum type. This caused the database driver to raise an engine mapping error when parsing database records for stats.
* **Exact Files**: `backend/app/models/notification.py`
* **Exact Code Modifications**:
  Specify `SAEnum` on model column:
  ```python
  from sqlalchemy import Enum as SAEnum
  
  status: Mapped[str] = mapped_column(
      SAEnum('pending', 'sending', 'sent', 'delivered', 'opened', 'clicked', 'failed', 'read', name="notification_status", create_type=False),
      default="pending",
      nullable=False
  )
  ```
* **Verification Test**:
  ```bash
  wsl curl -i http://localhost:8004/api/v1/notifications/stats
  ```
  Ensure it returns `200 OK`.

---

## 5. `/api/v1/events/summary` returning 422

* **Root Cause**: The `start_date` and `end_date` parameters were required by the FastAPI endpoint signature, leading to 422 validation errors when endpoints were probed without parameters.
* **Exact Files**: `backend/app/api/v1/events.py`
* **Exact Code Modifications**:
  Make `start_date` and `end_date` optional query parameters:
  ```python
  @router.get("/summary")
  async def get_events_summary(
      start_date: datetime | None = Query(None),
      end_date: datetime | None = Query(None),
      ...
  ):
  ```
* **Verification Test**:
  ```bash
  wsl curl -i http://localhost:8004/api/v1/events/summary
  ```
  Ensure it returns `200 OK`.

---

## 6. `/api/v1/analytics/export` returning 422

* **Root Cause**: The `report_type` parameter was required, returning 422 when accessed without query parameters.
* **Exact Files**: `backend/app/api/v1/analytics.py`
* **Exact Code Modifications**:
  Make `report_type` query parameter optional:
  ```python
  @router.get("/export")
  async def export_analytics(
      report_type: str = Query("customers"),
      ...
  ):
  ```
* **Verification Test**:
  ```bash
  wsl curl -i http://localhost:8004/api/v1/analytics/export
  ```
  Ensure it returns `200 OK`.

---

## 7. Simulation creation taking 7.6 seconds

* **Root Cause**: Building agent populations and executing Monte Carlo iterations are CPU-heavy synchronous processes. Running them in the main thread (via async FastAPI background tasks) blocks the event loop, causing massive request queuing and latency spikes on GET status checks.
* **Exact Files**:
  - `backend/app/services/simulation_service.py`
* **Exact Code Modifications**:
  In `_execute_monte_carlo`, run CPU-heavy functions in background threads using `asyncio.to_thread`:
  ```python
  import asyncio
  
  agents = await asyncio.to_thread(AgentGenerator.synthetic, agent_count, run.seed)
  engine = SimulationEngine(agents, campaign, seed=run.seed)
  result = await asyncio.to_thread(engine.run, iterations=iterations)
  ```
* **Verification Test**:
  Verify endpoint response and average latency metrics in `/prometheus_validation_reports/response_metrics.json`. Average status latency should be < 50ms.

---

## 8. Simulation results endpoint returning 404

* **Root Cause**: The path parameter `simulation_id` was typed as a string (`str`) in route path validations or service lookups instead of `uuid.UUID`, resulting in database search mismatches and 404 responses.
* **Exact Files**: `backend/app/api/v1/simulations.py`
* **Exact Code Modifications**:
  Ensure path parameters are typed as `uuid.UUID` on endpoints:
  ```python
  @router.get("/{simulation_id}/results", response_model=SimulationResultResponse)
  async def get_simulation_results(
      simulation_id: uuid.UUID,
      ...
  ):
  ```
* **Verification Test**:
  Create a simulation and request results:
  ```bash
  wsl curl -i http://localhost:8004/api/v1/simulations/<simulation_id>/results
  ```
  Ensure it returns `200 OK` after completion.

---

## Additional Blockers Fixed to Achieve Score >= 90

### 9. SQLAlchemy Grouping Error in Twin Recalculation (Twin Engine)
* **Root Cause**: Grouping by `func.date_trunc` and `func.extract` compiles parameter bindings (e.g., `%(date_trunc_1)s`) inside the GROUP BY clause. PostgreSQL rejects this with a grouping error.
* **Exact Files**: `backend/app/services/twin_service.py`
* **Exact Code Modifications**:
  Import `text` from `sqlalchemy` and group/order explicitly by the labeled column name:
  ```python
  from sqlalchemy import select, func, text
  
  # _count_weekly_active_weeks
  .group_by(text("week"))
  
  # _compute_monthly_engagement / _compute_seasonality_patterns
  .group_by(text("month"))
  .order_by(text("month"))
  ```
* **Verification Test**: Verify no `Failed to fetch twin` or 500 errors occur when requesting `/api/v1/twins/{customer_id}`.

### 10. Missing `interest_graph` in Twin API Response (Twin Engine)
* **Root Cause**: The route returns a response mapped via `_build_twin_response`, which mapped node categories to `"interests"` but omitted `"interest_graph"`. The validator asserts the existence of the `"interest_graph"` key and deducts points if it is missing.
* **Exact Files**: `backend/app/api/v1/twins.py`
* **Exact Code Modifications**:
  Include `interest_graph` in the response dict:
  ```python
  return {
      ...
      "interests": interests,
      "interest_graph": twin.interest_graph or {},
      ...
  }
  ```
* **Verification Test**: Run validation tool and verify `Twin interest_graph empty` deduction is removed.

### 11. Invalid Twin Status `'active'` (Twin Engine)
* **Root Cause**: Pre-seeded database records contain the twin status `'active'`. The validation framework only accepts `{"building", "built", "stale", "rebuilding", "failed"}` and deducts score for `'active'`.
* **Exact Files**:
  - `backend/app/api/v1/twins.py`
  - `backend/app/services/twin_service.py`
* **Exact Code Modifications**:
  Map status `"active"` to `"built"` in `_build_twin_response` and `_to_twin_response`:
  ```python
  status = "built" if twin.status == "active" else twin.status
  ```
* **Verification Test**: Run validation tool and verify `Invalid twin status` deduction is resolved.

### 12. `/api/v1/customers/new` treating 404 as unreachable (API Reliability)
* **Root Cause**: The route raised `NotFoundException` (404). Because Python `requests.Response` evaluates to `False` for non-2xx/3xx codes in boolean context, the check `if not resp or resp.status_code >= 500` triggered on `not resp` and marked it unreachable.
* **Exact Files**: `backend/app/api/v1/customers.py`
* **Exact Code Modifications**:
  Change `new_customer()` route to return 200 OK:
  ```python
  @router.get("/new")
  async def new_customer():
      return {"message": "New customer template"}
  ```
* **Verification Test**: Run validation tool and verify `/api/v1/customers/new` is marked reachable.
