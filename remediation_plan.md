# PROMETHEUS — Remediation Plan

Based on both audit passes, organized into 4 phases. Covers ~35+ defects and architectural gaps identified across the codebase audit.

---

## Phase 1 — Production Blockers (Fix Immediately)

These can cause crashes, data corruption, duplicate processing, or completely broken features.

### Authentication

- **Fix MFA Import** — Add `import pyotp` to `auth_service.py`
- **Fix MFA Verification** — Validate return value of `verify_mfa()` and raise `ValidationException` on failure

### Router → Service Signature Fixes

- **Twin Rebuild** — Fix argument order: `await service.rebuild_twin(organization_id=org_id, customer_id=customer_id)`
- **Customer Merge** — Iterate over `duplicate_ids` and call `merge_customers()` individually with correct UUID conversion

### Missing Service Methods

- Implement `CustomerService.batch_create()`
- Implement `CustomerService.get_profile()`
- Implement `TwinService.rebuild_stale_twins()`
- Implement `NotificationService.get_notification()`

### Worker Crashes

- Fix `SimulationService(session, redis)` — remove `kafka_client`
- Fix `NotificationService(session)` — remove `redis_client`
- Fix `TwinService(session, redis)` — remove `qdrant_client` and `kafka_client`

### Kafka Event Object Fix

- Replace direct dict passthrough to `process_event()` with a DB lookup to retrieve the `CustomerEvent` model instance

### Segment Membership Constraint Failure

- Replace `_apply_rules()` in update path with `recalculate_membership()` to clear old mappings first

### Prediction API Mismatch

- Choose Option A (backend returns flat object `{ churn, ltv, next_best_action }`) or Option B (frontend accepts `PredictionResponse[]`), then align both sides

---

## Phase 2 — Data Integrity & Transaction Safety

### Remove Dual Session Managers

- Keep only `get_session()`; delete `get_db()`

### Remove Router Commits

- Delete all explicit `await session.commit()` calls from routers — transaction ownership belongs to service layer

### Merge Savepoints

- Wrap merge operations in `async with session.begin_nested():` to allow partial rollback on constraint violation

### Customer Merge Conflict Resolution

- Never reassign `obj.customer_id = primary_id` for 1:1 tables (`CustomerTwin`, `CustomerProfile`, `CustomerPreference`). Instead merge data and delete the secondary record.

### Event Processing Decoupling

- Current: `request → create event → process event → update twin` (synchronous)
- Target: `request → save event → publish kafka → return` and `worker → process event → update twin`

---

## Phase 3 — Concurrency & Distributed Systems

### Twin Row Locking

- Add `.with_for_update()` to all `select(CustomerTwin)` queries before updates

### Atomic Event Processing

- Replace `if event.processed: return` with an atomic `UPDATE ... SET processed = true WHERE id = :id AND processed = false`

### Kafka Offset Commits

- Add `await consumer.commit()` after successful message processing in all workers (`twin_builder.py`, `simulation_worker.py`, `notification_worker.py`)

### Retry Queue

- Current: `fail → DLQ`
- Target: `fail → retry_1 → retry_2 → retry_3 → DLQ` with exponential backoff

### Add Idempotency Keys

- Add `idempotency_key` column to `customer_events` table with `UNIQUE (organization_id, idempotency_key)` constraint

---

## Phase 4 — Architecture & Scalability

### Cache Invalidation

- Add invalidation hooks for `dashboard:{org}`, `customer:{id}`, `twin:{id}` on event ingestion, customer update, campaign execution, and segment recalculation

### Repository Standardization

- Create `EventRepository`, `SegmentRepository`, `NotificationRepository`, `AnalyticsRepository`
- Move all `session.execute()` calls out of services and into repositories

### Multi-Tenant Hardening

- Add `organization_id` filter to every secondary query: `CustomerTwin`, `CustomerSegmentMapping`, `Campaign`, `Simulation`, `Notification`

### N+1 Fixes

- Refactor `_distribute_to_targets` in `campaign_service.py` to batch-fetch twins and targets with `WHERE customer_id IN (...)`

### Index Migration

- Add indexes on:
  - `customer_sessions (organization_id, customer_id)`
  - `customer_interests (organization_id, customer_id)`
  - `customer_preferences (organization_id, customer_id)`
  - `customer_profiles (organization_id, customer_id)`
  - `campaigns (organization_id)`
  - `notifications (organization_id)`
  - `simulations (organization_id)`
  - `customer_segment_mapping (segment_id, organization_id)`

### Frontend ↔ Backend Contract

- Generate TypeScript types from Pydantic models using `datamodel-code-generator` or `openapi-typescript`
- Remove all manually maintained frontend interfaces
- Fix: `CustomerCreate`, `EventCreate`, `SimulationCreate`, `Segment`, `Twin`, `AnalyticsQuery`, `PredictionResponse`

---

## Final Priority Ranking

### P0 (Must Fix Before Demo)
1. MFA import (`auth_service.py`)
2. MFA bypass (`auth_service.py` + router)
3. Twin rebuild signature (`twins.py`)
4. Customer merge signature (`customers.py`)
5. Missing service methods (`CustomerService`, `TwinService`, `NotificationService`)
6. Worker constructor mismatches (`twin_builder.py`, `simulation_worker.py`, `notification_worker.py`)
7. Kafka event object mismatch (`twin_builder.py`)
8. Segment unique constraint violation (`segment_service.py`)
9. Prediction API mismatch (`api-client.ts` ↔ `twins.py`)
10. Kafka offset commits (all workers)

### P1 (Must Fix Before Production)
1. Merge conflict handling (1:1 table unique constraint violations)
2. Transaction manager cleanup (`get_db` removal, router commit removal)
3. Row locking (twin concurrent update race)
4. Atomic processed flag (event double-processing race)
5. Cache invalidation (dashboard staleness)
6. Multi-tenant hardening (secondary queries)
7. Repository standardization (services bypassing repo layer)

### P2 (Scale & Reliability)
1. N+1 query elimination (campaign distribution)
2. Retry queues (Kafka consumer retry before DLQ)
3. Idempotency keys (event deduplication)
4. Missing indexes (8+ missing database indexes)
5. Event partition strategy (proper range partitioning)
6. Type generation pipeline (Pydantic → TypeScript automation)
