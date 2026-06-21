# PROMETHEUS — Windows Run Instructions (PowerShell)

[![GitHub](https://img.shields.io/badge/GitHub-ChiragHariprasad/prometheus-blue?style=flat&logo=github)](https://github.com/ChiragHariprasad/prometheus)

Step-by-step instructions to set up, configure, and run the complete PROMETHEUS platform on **Windows**.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Repository Setup](#2-repository-setup)
3. [Environment Configuration](#3-environment-configuration)
4. [Start All Services (Docker)](#4-start-all-services-docker)
5. [Database Setup](#5-database-setup)
6. [Verify Everything is Running](#6-verify-everything-is-running)
7. [Access the Application](#7-access-the-application)
8. [Seed Demo Data](#8-seed-demo-data)
9. [Running Backend (Standalone)](#9-running-backend-standalone)
10. [Running Frontend (Standalone)](#10-running-frontend-standalone)
11. [Running Background Workers](#11-running-background-workers)
12. [Running Tests](#12-running-tests)
13. [Linting and Type Checking](#13-linting-and-type-checking)
14. [Database Migrations](#14-database-migrations)
15. [Common Tasks](#15-common-tasks)
16. [Troubleshooting](#16-troubleshooting)
17. [Stopping Everything](#17-stopping-everything)
18. [Cleaning Up](#18-cleaning-up)
19. [Planned for Production](#19-planned-for-production)

---

## 1. Prerequisites

### Required Software

| Software | Minimum Version | Purpose |
|----------|----------------|---------|
| **Docker Desktop** | 24.0+ | Container runtime for all services |
| **Docker Compose** | 2.20+ | Multi-service orchestration (included in Docker Desktop) |
| **Python** | 3.12+ | Backend runtime (standalone mode) |
| **Node.js** | 20+ | Frontend runtime (standalone mode) |
| **Git** | 2.30+ | Source control |

### Check Installed Versions

```powershell
docker --version
docker compose version
python --version
node --version
git --version
```

### Install Missing Software

- **Docker Desktop** — https://docs.docker.com/get-docker/
- **Python 3.12+** — https://www.python.org/downloads/
- **Node.js 20+** — https://nodejs.org/
- **Git** — https://git-scm.com/downloads

> **Tip:** After installing Docker Desktop, enable **WSL 2 integration** in Docker Desktop Settings > Resources > WSL Integration for better performance.

---

## 2. Repository Setup

### Clone the Repository

```powershell
git clone https://github.com/ChiragHariprasad/prometheus.git
cd prometheus
```

### Verify Repository Structure

```powershell
Get-ChildItem -Force
```

Expected output:
```
ARCHITECTURE.md
backend/
database/
docker-compose.yml
frontend/
infrastructure/
judge-readme.md
linux-run.md
windows-run.md
Makefile
README.md
```

---

## 3. Environment Configuration

### Create Environment File

```powershell
Copy-Item .env.example .env
```

### Edit Required Values

Open `.env` in any text editor and set these minimum required values:

```
POSTGRES_PASSWORD=prometheus-demo-password-2026
JWT_SECRET_KEY=demo-secret-key-for-hackathon-review-only-min-32-chars
```

Or use PowerShell:

```powershell
(Get-Content .env) -replace 'POSTGRES_PASSWORD=change-me-in-production', 'POSTGRES_PASSWORD=prometheus-demo-password-2026' | Set-Content .env
(Get-Content .env) -replace 'JWT_SECRET_KEY=change-me-in-production-384-bit-minimum', 'JWT_SECRET_KEY=demo-secret-key-for-hackathon-review-only-min-32-chars' | Set-Content .env
```

---

## 4. Start All Services (Docker)

### Pull Images and Start

```powershell
docker compose pull
docker compose up -d
```

This starts **22 services** (containers):

| Service | Port | Purpose |
|---------|------|---------|
| traefik | — | API gateway (Planned — Not Implemented) |
| backend | **8004** (mapped) | FastAPI application |
| frontend | 3000 | Next.js application |
| postgres | (internal) | Primary database |
| redis | (internal) | Cache & real-time data |
| kafka | (internal) | Event streaming |
| zookeeper | (internal) | Kafka coordination |
| schema-registry | (internal) | Avro schema registry |
| qdrant | (internal) | Vector database |
| clickhouse | (internal) | Analytics DB (Planned — Not Implemented) |
| mlflow | (internal) | ML model registry (Planned — Not Implemented) |
| prometheus | (internal) | Metrics collection |
| grafana | 3001 | Monitoring dashboard |
| worker-twin-builder (x3) | — | Background twin updates |
| worker-prediction (x2) | — | Background ML inference |
| worker-simulation (x4) | — | Background simulation execution |
| worker-notification (x2) | — | Background notification delivery |

> **Note:** The backend is mapped to host port **8004** (not 8000) to avoid port conflicts.

### Monitor Startup Progress

```powershell
docker compose logs -f
```

Press `Ctrl+C` to exit log tailing.

### Check Service Status

```powershell
docker compose ps
```

Expected output — all services should show `Up` or `healthy`.

### Wait for Dependencies

Some services take longer to initialize. Wait ~60 seconds for Kafka and PostgreSQL to be ready.

```powershell
Write-Host "Waiting for services to be healthy..."
Start-Sleep -Seconds 60
docker compose ps | Select-String -Pattern "(postgres|kafka|redis|qdrant)"
```

---

## 5. Database Setup

### Apply Schema Migrations

The schema is automatically applied at first startup via `database/001_schema.sql` mounted to PostgreSQL's `docker-entrypoint-initdb.d/`. To run migrations manually:

```powershell
docker compose exec backend alembic upgrade head
```

### Verify Database Tables

```powershell
# Connect to PostgreSQL and list tables
docker compose exec postgres psql -U prometheus prometheus -c "\dt"

# Count total tables
docker compose exec postgres psql -U prometheus prometheus -c "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';"
```

Expected output: **65+ tables** including `organizations`, `users`, `customers`, `customer_twins`, `customer_events`, `campaigns`, `simulations`, etc.

---

## 6. Verify Everything is Running

### Check Backend Health

```powershell
Invoke-RestMethod -Uri http://localhost:8004/health | ConvertTo-Json
```

Expected response:
```json
{
    "status": "healthy",
    "version": "1.0.0",
    "uptime_seconds": 42.5,
    "services": {
        "redis": "connected",
        "kafka": "connected",
        "qdrant": "connected"
    }
}
```

### Check Backend Readiness

```powershell
Invoke-RestMethod -Uri http://localhost:8004/ready
```

Expected response:
```json
{"status": "ready"}
```

### Check API Documentation

Open in browser:
- **Swagger UI**: http://localhost:8004/docs
- **ReDoc**: http://localhost:8004/redoc

### Check Frontend

Open http://localhost:3000 in your browser. You should see the PROMETHEUS login page.

### Check Monitoring (Planned — Not Implemented)

- **Grafana**: http://localhost:3001 (login: admin / admin)
- **Prometheus**: http://localhost:9090

---

## 7. Access the Application

### URLs

| Interface | URL | Auth Required |
|-----------|-----|---------------|
| Frontend | http://localhost:3000 | Yes |
| Backend API | http://localhost:8004/api/v1 | Yes (JWT token) |
| API Docs (Swagger) | http://localhost:8004/docs | No |
| API Docs (ReDoc) | http://localhost:8004/redoc | No |
| Health Check | http://localhost:8004/health | No |
| Grafana | http://localhost:3001 | Yes (admin/admin) |
| Prometheus | http://localhost:9090 | No |

### Login with Judge Credentials (after seeding)

- Email: `judge@texpedition.com`
- Password: `pass@123`

### API Authentication Flow

```powershell
# Login
$response = Invoke-RestMethod -Method POST -Uri http://localhost:8004/api/v1/auth/login `
  -ContentType "application/json" `
  -Body '{"email": "judge@texpedition.com", "password": "pass@123"}'
$token = $response.access_token

# Use token for authenticated requests
$headers = @{ Authorization = "Bearer $token" }
Invoke-RestMethod -Uri http://localhost:8004/api/v1/customers -Headers $headers | ConvertTo-Json
```

---

## 8. Seed Demo Data

```powershell
docker compose exec backend python scripts/seed_data.py
```

### What the Seed Script Creates

| Data | Quantity | Description |
|------|----------|-------------|
| Organizations | 1 | TExpedition |
| Users | 1 | judge@texpedition.com (Admin) |
| Customers | 10 | Diverse customer profiles |
| Customer Twins | 10 | Digital twins with real scores |
| Events | ~237 | Cross-channel events (page views, purchases, emails, etc.) |

### Seed Data Credentials

| User | Email | Password | Role |
|------|-------|----------|------|
| Judge | `judge@texpedition.com` | `pass@123` | Admin |

---

## 9. Running Backend (Standalone)

Use this when you want to run the backend outside of Docker for development.

### Setup Python Virtual Environment

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

### Set Environment Variables

```powershell
$env:POSTGRES_HOST = "localhost"
$env:POSTGRES_PORT = "5432"
$env:POSTGRES_USER = "prometheus"
$env:POSTGRES_PASSWORD = "prometheus-demo-password-2026"
$env:POSTGRES_DB = "prometheus"
$env:REDIS_HOST = "localhost"
$env:REDIS_PORT = "6379"
$env:KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
$env:QDRANT_HOST = "localhost"
$env:QDRANT_PORT = "6333"
$env:JWT_SECRET_KEY = "demo-secret-key-for-hackathon-review-only-min-32-chars"
```

### Start the Backend Server

```powershell
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --workers 4
```

The server starts at http://localhost:8000 with hot-reload enabled.

---

## 10. Running Frontend (Standalone)

Use this when you want to run the frontend outside of Docker for development.

### Install Dependencies

```powershell
cd frontend
npm install
```

### Start Development Server

```powershell
cd frontend
npm run dev
```

The frontend starts at http://localhost:3000 with hot-reload.

### Build for Production

```powershell
cd frontend
npm run build
npm start
```

---

## 11. Running Background Workers

Workers can be run individually for development.

### Twin Builder Worker

```powershell
cd backend
python -m app.tasks.twin_builder
```

### Prediction Worker

```powershell
cd backend
python -m app.tasks.prediction_worker
```

### Simulation Worker

```powershell
cd backend
python -m app.tasks.simulation_worker
```

### Notification Worker

```powershell
cd backend
python -m app.tasks.notification_worker
```

---

## 12. Running Tests

### Backend Tests

```powershell
cd backend
pytest tests/ -v --cov=app --cov-report=term-missing

# Run specific test file
pytest tests/test_auth.py -v

# Run tests matching a pattern
pytest tests/ -k "customer" -v
```

### Frontend Tests

```powershell
cd frontend
npm run test

# Run with coverage
npm run test -- --coverage

# Run specific test file
npx jest --testPathPattern="components/Button"
```

---

## 13. Linting and Type Checking

### Backend Linting (ruff)

```powershell
cd backend
ruff check .
ruff check app/ --fix  # Auto-fix issues
```

### Backend Type Checking (mypy)

```powershell
cd backend
mypy app --ignore-missing-imports
```

### Frontend Linting

```powershell
cd frontend
npm run lint
```

### Frontend Type Checking

```powershell
cd frontend
npm run type-check
```

---

## 14. Database Migrations

### Create a New Migration

```powershell
cd backend
alembic revision --autogenerate -m "description_of_change"
```

### Apply Migrations

```powershell
# Apply all pending migrations
alembic upgrade head

# Apply specific migration
alembic upgrade abc123

# Rollback one migration
alembic downgrade -1
```

### View Migration History

```powershell
alembic history
```

### View Current Migration State

```powershell
alembic current
```

---

## 15. Common Tasks

### View Service Logs

```powershell
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f postgres

# Last 100 lines
docker compose logs --tail=100 backend

# Timestamps
docker compose logs -t backend
```

### Open Shell in a Container

```powershell
docker compose exec backend /bin/bash
docker compose exec frontend /bin/sh
docker compose exec postgres /bin/bash
docker compose exec redis /bin/sh
```

### PostgreSQL Interactive Shell

```powershell
docker compose exec postgres psql -U prometheus prometheus
```

Useful psql commands:
```sql
\dt          -- List all tables
\d+ customers -- Show table details
\di          -- List indexes
\l           -- List databases
\du          -- List users
SELECT count(*) FROM customers;
SELECT count(*) FROM customer_events;
SELECT event_type, count(*) FROM customer_events GROUP BY event_type;
```

### Redis CLI

```powershell
docker compose exec redis redis-cli

# Useful commands:
KEYS twin:*          -- List twin cache keys
DBSIZE               -- Database size
INFO stats           -- Redis statistics
```

### Kafka Topic Management

```powershell
# List all topics
docker compose exec kafka kafka-topics --bootstrap-server localhost:9092 --list

# Describe a topic
docker compose exec kafka kafka-topics --bootstrap-server localhost:9092 --describe --topic twin.cx.events.raw

# View messages (consume)
docker compose exec kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic twin.cx.events.raw --from-beginning --max-messages 10
```

### Rebuild a Service

```powershell
# Rebuild and restart a single service
docker compose up -d --build backend

# Rebuild and restart with no cache
docker compose build --no-cache backend
docker compose up -d backend
```

---

## 16. Troubleshooting

### Common Issues and Solutions

| Issue | Likely Cause | Solution |
|-------|-------------|----------|
| `docker: command not found` | Docker Desktop not installed | Install Docker Desktop (https://docs.docker.com/get-docker/) |
| `docker compose: command not found` | Docker Compose not installed | Docker Desktop includes Compose v2. Use `docker compose` (not `docker-compose`) |
| `port is already allocated` | Port conflict with existing service | Stop the conflicting service, or edit port mappings in `docker-compose.yml` |
| `PostgreSQL connection refused` | PostgreSQL not ready yet | Wait 30-60 seconds and retry. Check with `docker compose logs postgres` |
| `Kafka connection refused` | Kafka not ready yet | Kafka takes 60-90 seconds. Run `docker compose logs kafka` to monitor |
| `relation "customers" does not exist` | Migrations not applied | Run `docker compose exec backend alembic upgrade head` |
| `JWT token invalid` | Secret key mismatch | Ensure `JWT_SECRET_KEY` in `.env` matches the key used to generate the token |
| `frontend shows blank page` | Build error or API connection | Run `docker compose logs frontend` |
| `Redis connection error` | Redis not started | Run `docker compose up -d redis` and check with `docker compose logs redis` |
| `Qdrant connection error` | Qdrant not ready | Check with `curl http://localhost:6333/healthz` |
| `Out of memory` | Docker memory limit too low | Increase Docker memory to at least 8GB in Docker Desktop Settings |
| `Disk space full` | Docker accumulating data | Run `docker system prune -f` to clean unused containers, images, and volumes |

### Diagnosing Service Issues

```powershell
# Check all service statuses
docker compose ps

# View logs for a specific service
docker compose logs backend --tail=50 -f

# Check if a port is in use
netstat -ano | Select-String ":8000"
netstat -ano | Select-String ":5432"
netstat -ano | Select-String ":6379"

# Ping a service from another container
docker compose exec backend ping -n 3 postgres
docker compose exec backend ping -n 3 redis
```

### Resetting Everything

```powershell
# Stop all services (preserves data volumes)
docker compose down

# Stop all services and remove volumes (WARNING: deletes all data)
docker compose down -v

# Remove unused Docker resources
docker system prune -a -f --volumes
```

---

## 17. Stopping Everything

### Stop Services (Keep Data)

```powershell
docker compose down
```

Data volumes (PostgreSQL, Redis, Kafka, Qdrant, etc.) are preserved.

### Stop Services and Remove Volumes

```powershell
docker compose down -v
```

**WARNING**: This deletes all persistent data.

### Stop Individual Service

```powershell
docker compose stop backend
docker compose stop frontend
```

### Pause/Unpause Services

```powershell
# Pause (freeze without stopping)
docker compose pause backend

# Unpause
docker compose unpause backend
```

---

## 18. Cleaning Up

### Clean Docker Resources

```powershell
# Remove unused containers, networks, images, and build cache
docker system prune -f

# Remove everything including unused volumes
docker system prune -a -f --volumes

# Remove only specific service images
docker rmi $(docker images 'prometheus-*' -q)
```

### Clean Python Cache

```powershell
Get-ChildItem -Path . -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path . -Recurse -Filter "*.pyc" | Remove-Item -Force -ErrorAction SilentlyContinue
Remove-Item -Path .pytest_cache -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path .mypy_cache -Recurse -Force -ErrorAction SilentlyContinue
```

### Clean Node Modules

```powershell
cd frontend
Remove-Item -Path node_modules -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path .next -Recurse -Force -ErrorAction SilentlyContinue
```

---

## 19. Planned for Production

> **These sections describe production-grade deployment strategies that are NOT implemented in this build.** They are documented for future reference.

### Kubernetes Cluster (Planned — Not Implemented)

```powershell
# Apply all Kubernetes manifests
kubectl apply -f infrastructure/kubernetes/

# Check deployment status
kubectl get pods -n prometheus
kubectl get services -n prometheus
```

### Terraform AWS Infrastructure (Planned — Not Implemented)

```powershell
cd infrastructure/terraform
terraform init
terraform plan
terraform apply
```

### CI/CD Pipeline (Planned — Not Implemented)

The repository includes a GitHub Actions pipeline at `.github/workflows/ci.yml` that:
1. Lints backend (ruff, mypy) and frontend (ESLint, TypeScript)
2. Tests backend (pytest) and frontend (Jest) with coverage
3. Builds Docker images and pushes to registry
4. Deploys to staging/production

To use the CI/CD pipeline, set the following secrets in your GitHub repository:
- `KUBECONFIG_STAGING`
- `KUBECONFIG_PRODUCTION`
- `GHCR_TOKEN`

---

## Quick Reference — All Commands

| Task | Command |
|------|---------|
| Clone repo | `git clone <url>; cd prometheus` |
| Setup env | `Copy-Item .env.example .env` |
| Start services | `docker compose up -d` |
| View logs | `docker compose logs -f` |
| Check status | `docker compose ps` |
| Run migrations | `docker compose exec backend alembic upgrade head` |
| Health check | `Invoke-RestMethod http://localhost:8004/health` |
| Seed data | `docker compose exec backend python scripts/seed_data.py` |
| Run backend tests | `cd backend; pytest tests/ -v` |
| Run frontend tests | `cd frontend; npm run test` |
| Backend lint | `cd backend; ruff check .` |
| Frontend lint | `cd frontend; npm run lint` |
| Open DB shell | `docker compose exec postgres psql -U prometheus prometheus` |
| Open Redis CLI | `docker compose exec redis redis-cli` |
| Stop services | `docker compose down` |
| Stop + delete data | `docker compose down -v` |
| Rebuild service | `docker compose up -d --build backend` |
| Open backend shell | `docker compose exec backend /bin/bash` |
| Open frontend shell | `docker compose exec frontend /bin/sh` |
