# 🔍 PROMETHEUS — Comprehensive Codebase Audit Report

**Date:** 2026-06-24  
**Scope:** Backend (Python/FastAPI), Frontend (Next.js/React), Database (PostgreSQL)  
**Methodology:** Automated tooling (bandit, flake8, sqlfluff, npm audit) + manual source-code review

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Backend Audit](#1-backend-pythonfastapi)
3. [Frontend Audit](#2-frontend-nextjsreact)
4. [Database Audit](#3-database-postgresql)
5. [Cross-Cutting Concerns](#4-cross-cutting-concerns)
6. [Summary Table](#5-summary-table)

---

## Executive Summary

| Severity | Backend | Frontend | Database | Total |
|----------|---------|----------|----------|-------|
| 🔴 Critical | 3 | 1 | 0 | **4** |
| 🟠 High | 6 | 3 | 2 | **11** |
| 🟡 Medium | 8 | 4 | 3 | **15** |
| 🔵 Low / Info | 5 | 3 | 2 | **10** |
| **Total** | **22** | **11** | **7** | **40** |

---

## 1. Backend (Python/FastAPI)

### 🔴 CRITICAL

#### C-B1: Hardcoded Secrets in `.env` Committed to Git
**File:** `.env` (project root)  
The `.env` file contains real credentials and is **tracked in the repository**:
- `POSTGRES_PASSWORD=chirag123` (line 13)
- `QDRANT_API_KEY=eyJhbGciOiJIUz...` — a full JWT cloud API key (line 32)
- `Cluster_Endpoint=https://95593c9f-...cloud.qdrant.io` — production Qdrant cluster URL (line 33)
- `JWT_SECRET_KEY=change-me-in-production-384-bit-minimum` (line 35)
- `GRAFANA_PASSWORD=admin` (line 73)

While `.env` is in `.gitignore`, the file currently exists in the repo. If it was ever committed, these secrets are in Git history.

**Impact:** Full database access, cloud vector DB access, JWT forgery.  
**Fix:** Rotate ALL exposed credentials immediately. Audit `git log` for past commits containing `.env`. Use a secrets manager (Vault, AWS Secrets Manager).

---

#### C-B2: CORS Wildcard with Credentials Enabled
**File:** `backend/app/core/config.py` (lines 80-83)
```python
CORS_ORIGINS: List[str] = ["*"]
CORS_ALLOW_CREDENTIALS: bool = True
```
`allow_origins=["*"]` combined with `allow_credentials=True` is a dangerous misconfiguration. Per the CORS spec, browsers reject this combination, but some clients may not. It signals a lack of proper origin restriction.

**Impact:** Cross-site request attacks could steal tokens if origins aren't narrowed.  
**Fix:** Set `CORS_ORIGINS` to specific allowed origins (`["http://localhost:3000", "https://yourdomain.com"]`).

---

#### C-B3: MFA Bypass Fallback to Static Code
**File:** `backend/app/services/auth_service.py` (lines 206-212)
```python
except ImportError:
    logger.warning("pyotp not installed, MFA verification disabled")
    return code == "000000"
```
If `pyotp` fails to import (e.g., missing from a production container), MFA degrades to accepting the static code `"000000"`. This is a **trivially exploitable backdoor**.

**Impact:** Complete MFA bypass for any account.  
**Fix:** If `pyotp` is unavailable, fail closed — raise an exception instead of accepting a hardcoded code.

---

### 🟠 HIGH

#### H-B1: `logout` Endpoint Uses Undefined `logger`
**File:** `backend/app/api/v1/auth.py` (line 155)
```python
logger.info("User logged out", extra={"user_id": str(current_user.id)})
```
`logger` is **never imported** in this file. This will raise a `NameError` at runtime, causing a 500 error on every logout attempt.

**Impact:** Users cannot log out; error gets caught by global handler and returns 500.  
**Fix:** Add `from app.core.logging import logger` to the imports.

---

#### H-B2: No Token Revocation / Blacklisting
**Files:** `security.py`, `auth_service.py`, `auth.py`  
When a user logs out (`POST /logout`), changes password, or an admin disables an account, existing JWTs remain valid until they naturally expire (15 minutes for access, 7 days for refresh). There is no token blacklist in Redis or elsewhere.

**Impact:** Stolen tokens remain usable after logout/password change.  
**Fix:** Implement a Redis-based JTI (JWT ID) blacklist. On logout or password change, add the token's `jti` to the blacklist. Check the blacklist in `decode_token`.

---

#### H-B3: `get_current_user` Creates a Separate DB Session (Session Leak)
**File:** `backend/app/middleware/auth.py` (lines 65-75)
```python
async def get_current_user(request: Request):
    ...
    async with async_session_factory() as session:
        user = await session.get(User, uuid.UUID(user_id))
```
This dependency opens a **new, independent session** for every authenticated request, separate from the `get_session` dependency used by the route handler. This leads to:
- The User object is attached to session A, but route logic uses session B → detached instance errors
- Extra connection pool pressure (2 connections per request)

**Impact:** Potential `DetachedInstanceError` in some access patterns; wasted DB connections.  
**Fix:** Use the same `get_session` dependency to look up the user within the request's session.

---

#### H-B4: Unsafe `setattr` on Customer Preferences Update
**File:** `backend/app/api/v1/customers.py` (lines 358-375)
```python
payload: dict,   # raw dict, no schema validation
...
for field, value in payload.items():
    setattr(pref, field, value)
```
The `PUT /customers/{id}/preferences` endpoint accepts an **unvalidated raw dict** and blindly sets every key-value pair as an attribute on the ORM model. An attacker can overwrite internal fields like `id`, `organization_id`, or `customer_id`.

**Impact:** Privilege escalation by overwriting `organization_id` to access another org's data.  
**Fix:** Define a Pydantic schema for the request body and only apply whitelisted fields.

---

#### H-B5: Unsafe Dynamic Column Sorting via `getattr`
**Files:** `customers.py` (line 76), `events.py` (line 92)
```python
order_column = getattr(Customer, sort_by, Customer.created_at) if sort_by else Customer.created_at
```
User-provided `sort_by` query param is used directly with `getattr` on the SQLAlchemy model. While this defaults to `created_at` if the attribute doesn't exist, it allows accessing non-column attributes (methods, properties) which could cause unexpected behavior.

**Impact:** Potential information leakage or unexpected errors.  
**Fix:** Validate `sort_by` against an explicit allowlist of sortable column names.

---

#### H-B6: `random` Module Used for Simulation (Non-Reproducible)
**File:** `backend/app/services/simulation_service.py` (lines 63, 228-242)
```python
run.seed = random.randint(0, 2**31 - 1)
...
rr = random.gauss(base_response_rate, ...)
```
The simulation uses Python's `random` module but never calls `random.seed(run.seed)` with the stored seed value. The seed is saved to the database but is **never used**, making results non-reproducible. For Monte Carlo simulations, reproducibility is essential for auditing and debugging.

**Impact:** Simulations cannot be reproduced or verified.  
**Fix:** Call `random.seed(run.seed)` before the Monte Carlo loop, or use `numpy.random.Generator` with the stored seed.

---

### 🟡 MEDIUM

#### M-B1: Rate Limiter Race Condition
**File:** `backend/app/middleware/rate_limit.py` (lines 30-34)
```python
pipe = await redis_client.pipeline()
pipe.incr(key)
pipe.expire(key, period)
results = await pipe.execute()
```
The `incr` + `expire` pipeline is not truly atomic — a crash between `incr` and `expire` leaves the key without a TTL, permanently blocking the client. The correct pattern is to use a Lua script or Redis's `SET ... NX EX` pattern.

**Fix:** Use `await redis_client._client.eval(lua_script, ...)` for atomic incr+expire.

---

#### M-B2: `/api/v1/auth/register` Has No Rate Limit Differentiation
**File:** `rate_limit.py` (line 20)  
The registration endpoint falls under the generic auth rate limit (`20/minute`), but registration should arguably have a stricter limit (e.g., `5/minute`) since it creates organizations and users. An attacker can abuse this to create many dummy orgs.

---

#### M-B3: Password Validation Only on `change_password` and `confirm_password_reset`
**Files:** `auth_service.py`  
The `register()` method (line 28) does **not validate password length or complexity**. Password validation (`len < SECURITY_PASSWORD_MIN_LENGTH`) only runs during password change (line 155) and reset confirmation (line 240). A user could register with the password `"a"`.

**Fix:** Add the same password validation to the `register()` method.

---

#### M-B4: `rebuild_stale_twins()` Has No Pagination or Limit
**File:** `backend/app/services/twin_service.py` (lines 162-179)  
The method loads **all** stale twins into memory at once (`list(result.scalars().all())`). For a large database, this could consume excessive memory and hold long database transactions.

**Fix:** Add `.limit(settings.TWIN_BUILD_BATCH_SIZE)` to the query and process in batches.

---

#### M-B5: `_dispatch()` Notification Method is a No-Op
**File:** `backend/app/services/notification_service.py` (lines 130-131)
```python
async def _dispatch(self, notification: Notification) -> None:
    pass
```
All notifications are marked "sent" but never actually dispatched to any channel (email/SMS/push). The `send()` method calls `_dispatch()` which does nothing.

**Impact:** Notifications appear sent in the database but no customer ever receives them.

---

#### M-B6: Duplicate Event Processing — `process_event` Called Twice
**File:** `backend/app/tasks/twin_builder.py` (lines 38-39)
```python
await event_service.process_event(org_id, db_event)
await twin_service.update_twin_from_event(org_id, customer_id, db_event)
```
`event_service.process_event()` internally already calls `twin_service.update_twin_from_event()` (line 167 of `event_service.py`). The worker then calls `update_twin_from_event` **again**. This double-processes every event.

**Impact:** Twin scores are incorrectly updated twice per event (e.g., LTV double-counted).

---

#### M-B7: `ExportService` Has No Size Limits — Memory DoS
**File:** `backend/app/services/export_service.py`  
All export methods load the **entire result set** into memory and build an in-memory CSV string (`io.StringIO`). For large datasets (100K+ customers, 10M+ events), this can cause OOM crashes.

**Fix:** Stream results with `yield_per()` and return a `StreamingResponse`.

---

#### M-B8: Simulation Uses Hardcoded Sensitivity Values
**File:** `simulation_service.py` (lines 318-322)
```python
"sensitivity": [
    {"parameter": "response_rate", "impact": round(0.6, 4)},
    {"parameter": "conversion_rate", "impact": round(0.3, 4)},
    {"parameter": "avg_order_value", "impact": round(0.1, 4)},
],
```
These sensitivity values are **hardcoded constants**, not computed from the actual simulation data. They should be derived via partial derivatives or variance decomposition of the Monte Carlo results.

---

### 🔵 LOW / INFO

#### L-B1: Automated Linting (flake8) — 883 Issues
Primarily `F401` (unused imports) and `E501` (line too long). Not security risks but impact code maintainability. **Fix:** Run `black` + `isort` for autoformatting.

#### L-B2: Bandit B104 — Binding to `0.0.0.0`
Expected behavior for a Docker container. Low risk when behind a reverse proxy.

#### L-B3: Missing `__all__` in `__init__.py` Files
The `app/api/v1/__init__.py` imports all route modules but doesn't use them. These are used for module registration but trigger `F401` warnings.

#### L-B4: `EMBEDDING_DEVICE` Defaults to `"cuda"` in Config
**File:** `config.py` (line 104). The config default is `cuda`, but `.env` overrides to `cpu`. If `.env` is missing, the app will crash trying to use a GPU.

#### L-B5: `Dockerfile` Missing `.dockerignore`
The backend `Dockerfile` copies the entire context. A `.dockerignore` would prevent copying `.git`, `__pycache__`, `node_modules`, etc.

---

## 2. Frontend (Next.js/React)

### 🔴 CRITICAL

#### C-F1: Tokens Stored in `localStorage` via Zustand `persist`
**File:** `frontend/src/store/auth-store.ts` (lines 54-62)
```typescript
persist(
    ...
    {
      name: "prometheus-auth",
      partialize: (state) => ({
        token: state.token,
        refreshToken: state.refreshToken,
        ...
      }),
    }
)
```
JWT access and refresh tokens are persisted to `localStorage`. This is **vulnerable to XSS attacks** — any injected script can steal tokens via `localStorage.getItem("prometheus-auth")`. The refresh token (7-day lifetime) is especially dangerous.

**Impact:** Token theft via XSS grants full account access for up to 7 days.  
**Fix:** Store tokens in `httpOnly` cookies (set by the backend). For SPAs, use the BFF (Backend-For-Frontend) pattern or in-memory storage with silent refresh.

---

### 🟠 HIGH

#### H-F1: No ESLint Configuration — Zero Code Quality Checks
ESLint is not configured for the project. There is no `eslint.config.js` or `.eslintrc.*` file. `next lint` prompts for setup interactively. This means no React/TypeScript best practices are enforced, including:
- Missing `key` props in lists
- Unsafe `any` types
- Improper effect dependencies
- Accessibility violations

**Fix:** Run `npx eslint --init` and install `eslint-config-next` for Next.js-specific rules.

---

#### H-F2: 4 Moderate NPM Dependency Vulnerabilities
From `npm audit`:
| Package | Vulnerability | Severity |
|---------|--------------|----------|
| `postcss` (transitive via `next`) | XSS via unescaped `</style>` in CSS Stringify output | Moderate |
| `js-yaml` (transitive via `@redocly/openapi-core`) | Quadratic-complexity DoS in merge key handling | Moderate |

**Fix:** Run `npm audit fix`. For `postcss`, await Next.js to update their bundled version.

---

#### H-F3: No Client-Side Route Guards — Dashboard Accessible Without Auth
**File:** `frontend/src/app/(dashboard)/layout.tsx`  
The dashboard layout does not check `isAuthenticated` before rendering. It simply wraps children in `<DashboardLayout>`. While API calls will fail with 401, the UI shell and any static content will be visible to unauthenticated users. There is no redirect to `/login`.

**Fix:** Add an auth check in the dashboard layout:
```tsx
const { isAuthenticated } = useAuth();
if (!isAuthenticated) { router.push("/login"); return null; }
```

---

### 🟡 MEDIUM

#### M-F1: No CSRF Protection
The frontend uses `axios` with bearer tokens in headers (not cookies), so traditional CSRF isn't applicable. However, the refresh token flow (`api.post("/auth/refresh", { refresh_token })`) sends the refresh token in the request body, which is safe but should be validated.

#### M-F2: API Client Has No Request Deduplication
Multiple components could trigger the same API call simultaneously (e.g., dashboard data). There's no request deduplication or caching layer beyond what TanStack Query provides.

#### M-F3: Error Messages Displayed Directly from API
**File:** `login/page.tsx` (line 39)
```typescript
setError(apiError?.response?.data?.detail || "Invalid credentials");
```
Backend error `detail` strings (e.g., `"User with id X not found"`) are displayed directly to the user. This can leak internal IDs and model names.

**Fix:** Map API error codes to user-friendly messages instead of displaying raw backend error text.

#### M-F4: No `autocomplete="current-password"` / `autocomplete="email"` on Login Form
**File:** `login/page.tsx`  
The login form inputs are missing `autocomplete` attributes, which degrades password manager support and accessibility.

---

### 🔵 LOW / INFO

#### L-F1: Hardcoded Marketing Stats on Login Page
**File:** `login/page.tsx` (lines 66-76)  
"10M+ Events Processed", "99.9% Prediction Accuracy", "3.2x Revenue Uplift" are hardcoded strings. These should either be dynamic or clearly marked as illustrative.

#### L-F2: Missing `<title>` and Meta Tags on Most Pages
Only the root layout has a title. Individual pages like `/dashboard`, `/customers`, `/analytics` don't set page-specific titles, which hurts SEO and browser tab identification.

#### L-F3: `use-realtime.ts` Hook Exists but WebSocket Connection Not Verified
The hook file exists but its actual WebSocket integration with the backend isn't confirmed. The `docker-compose.yml` sets `NEXT_PUBLIC_WS_URL=ws://localhost:8004` but no WebSocket endpoint exists on the backend.

---

## 3. Database (PostgreSQL)

### 🟠 HIGH

#### H-D1: `CREATE INDEX` Without `CONCURRENTLY` — Table Locking
**File:** `database/002_missing_indexes.sql`  
All 9 `CREATE INDEX` statements run without the `CONCURRENTLY` keyword. On a production database with active traffic, this will **lock the entire table** for the duration of the index build (potentially minutes for large tables like `customer_events`).

**Fix:** Use `CREATE INDEX CONCURRENTLY IF NOT EXISTS ...` (note: this cannot run inside a transaction, so remove the `BEGIN`/`COMMIT` wrapper or run each statement separately).

---

#### H-D2: Partitions Expire After 2026 — No Auto-Partitioning
**File:** `database/001_schema.sql` (lines 296-323)  
Monthly partitions are hardcoded for 2026 only, with a catch-all `default` partition from 2027-01-01 to 2030-01-01. After December 2026, all events will go into the default partition, negating partition pruning benefits. There is no `pg_partman` or cron job to create future partitions.

**Fix:** Install `pg_partman` for automatic partition creation, or add a scheduled script to create partitions ahead of time.

---

### 🟡 MEDIUM

#### M-D1: Twin Status Enum Mismatch Between DB and Application Code
**File:** Schema (line 25) vs. `twin_service.py` (line 67)  
- Database enum: `twin_status AS ENUM ('active', 'stale', 'archived', 'building')`
- Application code sets: `twin.status = "built"` (line 67)

The value `"built"` is not in the database enum. This will raise a PostgreSQL error when persisting unless the ORM model uses a plain `VARCHAR` instead of the enum type.

---

#### M-D2: Event Type Enum Too Restrictive
**File:** `001_schema.sql` (lines 16-23)  
The database `event_type` enum has only 20 values, but the application code references event types like `"purchase"`, `"negative_feedback"`, `"complaint"`, `"positive_feedback"`, `"support_resolved"`, `"cart_abandon"`, `"unsubscribe"`, `"bounce"`, `"return"`, `"referral"` (in `twin_service.py`). Several of these (`negative_feedback`, `complaint`, `positive_feedback`, `support_resolved`, `cart_abandon`, `unsubscribe`, `bounce`, `return`) are **not in the enum** and will cause insert failures.

**Fix:** Either add all used event types to the enum, or change the column to `VARCHAR(50)`.

---

#### M-D3: `customers_partitioned` Table Created but Unused
**File:** `001_schema.sql` (lines 183-188)  
A `customers_partitioned` table is created with `PARTITION BY HASH (id)` but no hash partitions are created, and no application code references it. It's dead schema.

---

### 🔵 LOW / INFO

#### L-D1: Schema File is 44KB — Not Using Alembic Migrations
The `001_schema.sql` file is a single monolithic 963-line file. The backend has `alembic.ini` and a `migrations/` directory, suggesting Alembic is set up, but the actual schema is managed via raw SQL. This creates drift risk between the SQL schema and Alembic's understanding of the database state.

#### L-D2: `sqlfluff` Style Issues
20+ formatting issues in `002_missing_indexes.sql`: lines too long, spacing inconsistencies, indentation problems.

---

## 4. Cross-Cutting Concerns

### 🟠 Security Architecture

| Issue | Status |
|-------|--------|
| JWT secret key is a weak default string | ⚠️ Must rotate |
| No token revocation mechanism | ⚠️ Implement Redis blacklist |
| No HTTPS enforcement in config | ⚠️ Traefik planned but not active |
| MFA has static code backdoor | 🔴 Fix immediately |
| PII fields logged without redaction | ⚠️ `email` appears in log extras |
| Redis has no password in `.env` | ⚠️ Set a password |
| `/docs` and `/openapi.json` are public | ⚠️ Disable in production |

### 🟡 Operational Gaps

| Area | Issue |
|------|-------|
| **Tests** | `backend/tests/` and `frontend/tests/` exist but are empty or minimal — no test coverage |
| **CI/CD** | No `.github/workflows/` or equivalent pipeline config found |
| **Monitoring** | Prometheus/Grafana configured in docker-compose but `/metrics` endpoint not implemented |
| **Logging** | f-string logging used (`f"Auth error: {e}"`), preventing structured log parsing |
| **Error Tracking** | `SENTRY_DSN` is empty in `.env` — Sentry is unconfigured |

---

## 5. Summary Table

| # | Severity | Layer | Issue | File(s) |
|---|----------|-------|-------|---------|
| C-B1 | 🔴 Critical | Backend | Hardcoded secrets in `.env` | `.env` |
| C-B2 | 🔴 Critical | Backend | CORS wildcard + credentials | `config.py` |
| C-B3 | 🔴 Critical | Backend | MFA bypass via hardcoded `"000000"` | `auth_service.py` |
| C-F1 | 🔴 Critical | Frontend | Tokens in `localStorage` (XSS-vulnerable) | `auth-store.ts` |
| H-B1 | 🟠 High | Backend | `logger` undefined in logout → 500 crash | `auth.py` |
| H-B2 | 🟠 High | Backend | No token revocation/blacklisting | `security.py` |
| H-B3 | 🟠 High | Backend | `get_current_user` opens separate DB session | `middleware/auth.py` |
| H-B4 | 🟠 High | Backend | Blind `setattr` from raw dict input | `customers.py` |
| H-B5 | 🟠 High | Backend | Unsafe dynamic sorting via `getattr` | `customers.py`, `events.py` |
| H-B6 | 🟠 High | Backend | Simulation seed saved but never used | `simulation_service.py` |
| H-F1 | 🟠 High | Frontend | No ESLint configuration | Project root |
| H-F2 | 🟠 High | Frontend | 4 moderate NPM vulnerabilities | `package.json` |
| H-F3 | 🟠 High | Frontend | No route guard on dashboard | `layout.tsx` |
| H-D1 | 🟠 High | Database | `CREATE INDEX` without `CONCURRENTLY` | `002_missing_indexes.sql` |
| H-D2 | 🟠 High | Database | Partitions expire after 2026 | `001_schema.sql` |
| M-B1 | 🟡 Medium | Backend | Rate limiter race condition | `rate_limit.py` |
| M-B2 | 🟡 Medium | Backend | No stricter rate limit on registration | `rate_limit.py` |
| M-B3 | 🟡 Medium | Backend | No password validation on registration | `auth_service.py` |
| M-B4 | 🟡 Medium | Backend | Unbounded stale twin rebuild query | `twin_service.py` |
| M-B5 | 🟡 Medium | Backend | Notification `_dispatch()` is a no-op | `notification_service.py` |
| M-B6 | 🟡 Medium | Backend | Twin update called twice per event | `twin_builder.py` |
| M-B7 | 🟡 Medium | Backend | Export with no size limits — OOM risk | `export_service.py` |
| M-B8 | 🟡 Medium | Backend | Hardcoded simulation sensitivity values | `simulation_service.py` |
| M-F1 | 🟡 Medium | Frontend | No CSRF token for state-changing requests | `api.ts` |
| M-F2 | 🟡 Medium | Frontend | No API request deduplication | `api-client.ts` |
| M-F3 | 🟡 Medium | Frontend | Raw backend errors shown to user | `login/page.tsx` |
| M-F4 | 🟡 Medium | Frontend | Missing `autocomplete` attributes | `login/page.tsx` |
| M-D1 | 🟡 Medium | Database | Twin status enum mismatch | `001_schema.sql` |
| M-D2 | 🟡 Medium | Database | Event type enum too restrictive | `001_schema.sql` |
| M-D3 | 🟡 Medium | Database | Unused `customers_partitioned` table | `001_schema.sql` |
| L-B1 | 🔵 Low | Backend | 883 flake8 linting issues | Entire `app/` |
| L-B2 | 🔵 Low | Backend | Binding to `0.0.0.0` | `config.py` |
| L-B3 | 🔵 Low | Backend | Missing `__all__` in init files | `__init__.py` |
| L-B4 | 🔵 Low | Backend | `EMBEDDING_DEVICE` defaults to `cuda` | `config.py` |
| L-B5 | 🔵 Low | Backend | Missing `.dockerignore` | `backend/` |
| L-F1 | 🔵 Low | Frontend | Hardcoded marketing stats | `login/page.tsx` |
| L-F2 | 🔵 Low | Frontend | Missing per-page `<title>` tags | Multiple pages |
| L-F3 | 🔵 Low | Frontend | WebSocket hook may be non-functional | `use-realtime.ts` |
| L-D1 | 🔵 Low | Database | Schema managed via raw SQL, not Alembic | `001_schema.sql` |
| L-D2 | 🔵 Low | Database | SQL formatting issues | `002_missing_indexes.sql` |

---

*End of audit report. Prioritize fixing 🔴 Critical and 🟠 High issues before any production deployment.*
