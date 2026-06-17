.PHONY: help setup check-dns pull build up down restart \
        logs logs-backend logs-frontend logs-worker \
        status psql redis-cli kafka-topics \
        migrate migrate-show seed \
        test test-backend test-frontend \
        lint lint-backend lint-frontend \
        clean clean-all prune \
        shell-backend shell-frontend shell-postgres \
        export-check urls

SHELL := /bin/bash

help:
	@echo "╔══════════════════════════════════════════════════════════╗"
	@echo "║            PROMETHEUS  Management Commands               ║"
	@echo "╚══════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "── Setup & Prerequisites ──"
	@echo "  make setup        Copy .env.example -> .env (first time)"
	@echo "  make check-dns    Verify Docker DNS resolution"
	@echo "  make pull         Pull all base Docker images"
	@echo ""
	@echo "── Build & Run ──"
	@echo "  make build        Build all Docker images"
	@echo "  make up           Start all services (detached)"
	@echo "  make down         Stop all services"
	@echo "  make restart      Restart all services"
	@echo "  make status       Show container status"
	@echo ""
	@echo "── Logs ──"
	@echo "  make logs         Tail all logs"
	@echo "  make logs-backend   Tail backend logs"
	@echo "  make logs-frontend  Tail frontend logs"
	@echo "  make logs-worker    Tail worker logs"
	@echo ""
	@echo "── Database ──"
	@echo "  make migrate      Run Alembic migrations"
	@echo "  make migrate-show Show migration history"
	@echo "  make seed         Seed database with sample data"
	@echo "  make psql         Open psql shell"
	@echo ""
	@echo "── Infrastructure Shells ──"
	@echo "  make redis-cli    Open redis-cli"
	@echo "  make kafka-topics List Kafka topics"
	@echo "  make shell-backend   Bash in backend container"
	@echo "  make shell-frontend  Sh in frontend container"
	@echo "  make shell-postgres  Psql as postgres superuser"
	@echo ""
	@echo "── Testing & Linting ──"
	@echo "  make test         Run all tests"
	@echo "  make test-backend Run backend tests"
	@echo "  make test-frontend Run frontend tests"
	@echo "  make lint         Run all linters"
	@echo ""
	@echo "── Cleanup ──"
	@echo "  make clean        Stop services (keep volumes)"
	@echo "  make clean-all    Stop + remove volumes + prune"
	@echo "  make prune        Docker system prune"
	@echo ""
	@echo "── Export ──"
	@echo "  make export-check Verify everything is ready for deployment"
	@echo "  make urls         Show all service URLs and ports"
	@echo ""
	@echo "── Quick Start ──"
	@echo "  make setup && make pull && make build && make up"
	@echo ""

setup:
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "Created .env from .env.example — edit passwords before running"; \
	else \
		echo ".env already exists"; \
	fi

check-dns:
	bash scripts/fix-docker-dns.sh

pull:
	docker pull postgres:16-alpine
	docker pull redis:7-alpine
	docker pull confluentinc/cp-kafka:7.7.0
	docker pull confluentinc/cp-zookeeper:7.7.0
	docker pull confluentinc/cp-schema-registry:7.7.0
	docker pull qdrant/qdrant:v1.11.0
	docker pull clickhouse/clickhouse-server:24.8-alpine
	docker pull prom/prometheus:v2.54.0
	docker pull grafana/grafana:11.2.0
	docker pull traefik:v3.1
	docker pull python:3.12-slim
	docker pull node:20-alpine
	@echo "All base images pulled"

build:
	docker compose build

up:
	docker compose up -d
	@echo ""
	@echo "Services starting — run 'make status' to check, 'make urls' for endpoints"

down:
	docker compose down

restart: down up

status:
	@echo "── Container Status ──"
	@docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || docker compose ps
	@echo ""
	@echo "── Health Checks ──"
	@echo ""
	@for svc in postgres redis kafka qdrant; do \
		status=$$(docker compose ps --format "{{.Status}}" $$svc 2>/dev/null); \
		if echo "$$status" | grep -q "(healthy)"; then \
			echo "  [✓] $$svc"; \
		elif echo "$$status" | grep -q "(unhealthy)"; then \
			echo "  [✗] $$svc (unhealthy)"; \
		else \
			echo "  [?] $$svc ($$status)"; \
		fi; \
	done

logs:
	docker compose logs -f

logs-backend:
	docker compose logs -f backend

logs-frontend:
	docker compose logs -f frontend

logs-worker:
	docker compose logs -f worker-twin-builder worker-prediction worker-simulation worker-notification

migrate:
	docker compose exec -T backend alembic upgrade head

migrate-show:
	docker compose exec -T backend alembic history

seed:
	docker compose exec -T backend python -m app.tasks.seed_data

psql:
	docker compose exec -e PGPASSWORD=$$(grep POSTGRES_PASSWORD .env | cut -d= -f2) postgres psql -U prometheus prometheus

redis-cli:
	docker compose exec redis redis-cli

kafka-topics:
	docker compose exec kafka kafka-topics --bootstrap-server localhost:9092 --list

shell-backend:
	docker compose exec backend /bin/bash

shell-frontend:
	docker compose exec frontend /bin/sh

shell-postgres:
	docker compose exec postgres psql -U postgres

test-backend:
	docker compose exec backend pytest tests/ -v --cov=app --cov-report=term-missing

test-frontend:
	cd frontend && npm run test

test: test-backend test-frontend

lint-backend:
	cd backend && ruff check . && mypy app --ignore-missing-imports

lint-frontend:
	cd frontend && npm run lint && npm run typecheck

lint: lint-backend lint-frontend

clean:
	docker compose down

clean-all:
	docker compose down -v
	docker system prune -af --volumes
	rm -rf frontend/.next frontend/node_modules
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

prune:
	docker system prune -af --volumes

export-check:  # TODO: Production — expand to include K8s/Terraform readiness
	@echo "╔════════════════════════════════════════════╗"
	@echo "║      PROMETHEUS  Deployment Readiness        ║"
	@echo "╚════════════════════════════════════════════╝"
	@errors=0; \
	\
	echo ""; \
	echo "── Files ──"; \
	for f in docker-compose.yml .env.example Makefile; do \
		if [ -f "$$f" ]; then echo "  [✓] $$f"; else echo "  [✗] $$f"; errors=$$((errors+1)); fi; \
	done; \
	\
	echo ""; \
	echo "── Backend ──"; \
	for f in backend/Dockerfile backend/requirements.txt backend/app/main.py; do \
		if [ -f "$$f" ]; then echo "  [✓] $$f"; else echo "  [✗] $$f"; errors=$$((errors+1)); fi; \
	done; \
	\
	echo ""; \
	echo "── Frontend ──"; \
	for f in frontend/Dockerfile frontend/package.json frontend/next.config.ts; do \
		if [ -f "$$f" ]; then echo "  [✓] $$f"; else echo "  [✗] $$f"; errors=$$((errors+1)); fi; \
	done; \
	\
	echo ""; \
	echo "── Database ──"; \
	if [ -f database/001_schema.sql ]; then echo "  [✓] schema.sql"; else echo "  [✗] schema.sql"; errors=$$((errors+1)); fi; \
	\
	echo ""; \
	echo "── Infra ──"; \
	for f in infrastructure/kubernetes infrastructure/terraform infrastructure/monitoring; do \
		if [ -d "$$f" ]; then echo "  [✓] $$f/"; else echo "  [✗] $$f/"; errors=$$((errors+1)); fi; \
	done; \
	\
	echo ""; \
	echo "── CI/CD ──"; \
	if [ -f .github/workflows/ci.yml ]; then echo "  [✓] CI pipeline"; else echo "  [✗] CI pipeline"; errors=$$((errors+1)); fi; \
	\
	echo ""; \
	echo "── Environment ──"; \
	if [ -f .env ]; then \
		has_pw=$$(grep -c "change-me" .env || true); \
		if [ "$$has_pw" -gt 0 ]; then \
			echo "  [⚠] .env has default passwords — change before production"; \
		else \
			echo "  [✓] .env configured"; \
		fi; \
	else \
		echo "  [✗] .env missing — run 'make setup'"; \
		errors=$$((errors+1)); \
	fi; \
	\
	echo ""; \
	if [ "$$errors" -gt 0 ]; then \
		echo "  Found $$errors issue(s) — fix before deploying"; \
	else \
		echo "  All checks passed — ready for deployment"; \
	fi; \
	echo ""

urls:
	@echo "╔══════════════════════════════════════════════════════════╗"
	@echo "║              PROMETHEUS-X  Service Endpoints                ║"
	@echo "╚══════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "  Service               URL / Port"
	@echo "  ───────────────────────────────────────────────────────────"
	@echo "  Frontend              http://localhost:3000"
	@echo "  Backend API           http://localhost:8004"
	@echo "  Swagger UI            http://localhost:8004/docs"
	@echo "  ReDoc                 http://localhost:8004/redoc"
	@echo "  OpenAPI JSON          http://localhost:8004/openapi.json"
	@echo "  Health Check          http://localhost:8004/health"
	@echo "  Ready Check           http://localhost:8004/ready"
	@echo "  Traefik Dashboard     http://localhost:8080"
	@echo "  PostgreSQL            5432 (internal)"
	@echo "  Redis                 6379 (internal)"
	@echo "  Kafka                 9092 (internal)"
	@echo "  Schema Registry       8081 (internal)"
	@echo "  Qdrant HTTP           6333 (internal)"
	@echo "  Qdrant gRPC           6334 (internal)"
	@echo "  MLflow                5000 (internal)"
	@echo "  ClickHouse HTTP       8123 (internal)"
	@echo "  ClickHouse Native     9000 (internal)"
	@echo "  Prometheus            9090 (internal)"
	@echo "  Grafana               http://localhost:3001  (admin:$${GRAFANA_PASSWORD:-admin})"
	@echo ""
	@echo "── API Test Commands ──"
	@echo ""
	@echo "  Health:"
	@echo "    curl -s http://localhost:8004/health | jq ."
	@echo ""
	@echo "  Ready:"
	@echo "    curl -s http://localhost:8004/ready | jq ."
	@echo ""
	@echo "  Register:"
	@echo '    curl -s -X POST http://localhost:8004/api/v1/auth/register \'
	@echo '      -H "Content-Type: application/json" \'
	@echo '      -d "{\"email\":\"admin@prometheus.ai\",\"password\":\"Test1234!\",\"name\":\"Admin\",\"organization_name\":\"PROMETHEUS\"}" | jq .'
	@echo ""
	@echo "  Login:"
	@echo '    TOKEN=$$(curl -s -X POST http://localhost:8004/api/v1/auth/login \'
	@echo '      -H "Content-Type: application/json" \'
	@echo '      -d "{\"email\":\"admin@prometheus.ai\",\"password\":\"Test1234!\"}" | jq -r ".data.access_token")'
	@echo '    echo "$$TOKEN"'
	@echo ""
	@echo "  Authorized Request:"
	@echo "    curl -s http://localhost:8004/api/v1/customers/ \\"
	@echo '      -H "Authorization: Bearer $$TOKEN" | jq .'
	@echo ""
	@echo "  Dashboard:"
	@echo "    curl -s http://localhost:8004/api/v1/analytics/dashboard \\"
	@echo '      -H "Authorization: Bearer $$TOKEN" | jq .'
	@echo ""
	@echo "  Metrics:"
	@echo "    curl -s http://localhost:8004/metrics"
	@echo ""
