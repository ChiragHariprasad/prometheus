# PROMETHEUS Architecture Document

> **Note:** The architecture below describes the **planned production deployment** with microservices, service mesh, and cloud infrastructure. The current implementation runs as a **single FastAPI monolith** with **Docker Compose** (22 containers). See [judge-readme.md](judge-readme.md) for the actual architecture diagram.

## 1. High-Level Architecture (Planned — Not Implemented)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Next.js  │  │   REST   │  │ GraphQL  │  │ Mobile   │  │   SDK    │   │
│  │   App    │  │   API    │  │  Gateway │  │   Apps   │  │ External │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
└───────┼─────────────┼──────────────┼─────────────┼──────────────┼─────────┘
        │             │              │             │              │
┌───────┼─────────────┼──────────────┼─────────────┼──────────────┼─────────┐
│       │      API GATEWAY (Kong/Traefik)          │              │         │
│       │      Rate Limiting │ Auth │ Routing      │              │         │
│       └──────────────────────┬───────────────────────           │         │
│                              │                                   │         │
│                    ┌─────────▼──────────┐                        │         │
│                    │  SERVICE MESH      │                        │         │
│                    │  (Istio/Linkerd)   │                        │         │
│                    └─────────┬──────────┘                        │         │
│                              │                                   │         │
│       ┌──────────────────────┼──────────────────────────────┐    │         │
│       │              MICROSERVICES LAYER                    │    │         │
│       │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐│    │         │
│       │  │  Auth    │ │  User    │ │Customer │ │  Twin  ││    │         │
│       │  │ Service  │ │ Service  │ │ Service  │ │Service ││    │         │
│       │  └──────────┘ └──────────┘ └──────────┘ └────────┘│    │         │
│       │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐│    │         │
│       │  │Prediction│ │Recommend │ │Simulation│ │Campaign││    │         │
│       │  │ Service  │ │ Service  │ │ Service  │ │Service ││    │         │
│       │  └──────────┘ └──────────┘ └──────────┘ └────────┘│    │         │
│       │  ┌──────────┐ ┌──────────┐                         │    │         │
│       │  │Analytics │ │Notification                       │    │         │
│       │  │ Service  │ │ Service   │                         │    │         │
│       │  └──────────┘ └──────────┘                         │    │         │
│       └──────────────────────┬──────────────────────────────┘    │         │
│                              │                                   │         │
│       ┌──────────────────────┼──────────────────────────────┐    │         │
│       │              DATA LAYER                             │    │         │
│       │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐│    │         │
│       │  │PostgreSQL│ │  Redis   │ │  Qdrant  │ │  S3    ││    │         │
│       │  │  (Main)  │ │ (Cache)  │ │(Vectors) │ │(Storage)││    │         │
│       │  └──────────┘ └──────────┘ └──────────┘ └────────┘│    │         │
│       │  ┌──────────┐ ┌──────────┐ ┌──────────┐           │    │         │
│       │  │  Kafka   │ │ ClickHouse│ │  MLflow  │           │    │         │
│       │  │(Events)  │ │(Analytics)│ │(Registry)│           │    │         │
│       │  └──────────┘ └──────────┘ └──────────┘           │    │         │
│       └────────────────────────────────────────────────────┘    │         │
└─────────────────────────────────────────────────────────────────┘
```

## 2. Microservice Architecture (Planned — Not Implemented)

| Service | Responsibility | Language | Database | Scale |
|---------|---------------|----------|----------|-------|
| auth-service | Authentication, JWT, OAuth2, SSO | Python/FastAPI | PostgreSQL | 3-5 pods |
| user-service | User management, RBAC, teams | Python/FastAPI | PostgreSQL | 3-5 pods |
| customer-service | Customer CRUD, profiles, segments | Python/FastAPI | PostgreSQL | 5-10 pods |
| twin-service | Digital twin generation, updates | Python/FastAPI | PostgreSQL, Qdrant, Redis | 10-20 pods |
| event-ingestion | Kafka consumer, event processing | Python/FastAPI | Kafka, PostgreSQL | 10-20 pods |
| prediction-service | ML inference, batch predictions | Python/FastAPI | PostgreSQL, MLflow | 5-10 pods |
| recommendation-service | Product/content recommendations | Python/FastAPI | Qdrant, PostgreSQL | 5-10 pods |
| simulation-service | Campaign simulation engine | Python/FastAPI | PostgreSQL, Redis | 10-20 pods |
| campaign-service | Campaign CRUD, targeting, execution | Python/FastAPI | PostgreSQL | 5-10 pods |
| analytics-service | Aggregation, reporting, dashboards | Python/FastAPI | ClickHouse | 3-5 pods |
| notification-service | Email, SMS, push notifications | Python/FastAPI | Redis, PostgreSQL | 3-5 pods |

## 3. Event-Driven Architecture (Planned — Not Implemented)

```
                    ┌─────────────────────┐
                    │   Event Producers   │
                    │  (SDK, Web, Mobile) │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │  Kafka REST Proxy   │
                    │  /topics/{topic}    │
                    └──────────┬──────────┘
                               │
┌──────────────────────────────┼──────────────────────────────┐
│                     KAFKA CLUSTER                           │
│  ┌──────────────────────────┼──────────────────────────┐   │
│  │  Topics:                 │                           │   │
│  │  twin.cx.events.raw     │  (Partitions: 12)         │   │
│  │  twin.cx.events.pageview│  (Partitions: 12)         │   │
│  │  twin.cx.events.purchase│  (Partitions: 12)         │   │
│  │  twin.cx.events.email   │  (Partitions: 6)          │   │
│  │  twin.cx.events.session │  (Partitions: 12)         │   │
│  │  twin.cx.events.support │  (Partitions: 6)          │   │
│  │  twin.cx.events.campaign│  (Partitions: 6)          │   │
│  │  twin.cx.events.social  │  (Partitions: 6)          │   │
│  │  twin.cx.twin.update    │  (Partitions: 12)         │   │
│  │  twin.cx.prediction     │  (Partitions: 6)          │   │
│  │  twin.cx.simulation     │  (Partitions: 6)          │   │
│  │  twin.cx.notification   │  (Partitions: 6)          │   │
│  │  twin.cx.dead.letter    │  (Partitions: 3)          │   │
│  └─────────────────────────────────────────────────────┘   │
└──────────────────────────────┬──────────────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │  Kafka Consumers    │
                    │  (Group per service)│
                    └──────────┬──────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
  ┌───────▼───────┐   ┌───────▼───────┐   ┌───────▼───────┐
  │ Event Router  │   │  Twin Builder │   │  Prediction   │
  │ (raw → typed) │   │  (aggregation) │   │  (inference)  │
  └───────────────┘   └───────────────┘   └───────────────┘
          │                    │                    │
  ┌───────▼───────┐   ┌───────▼───────┐   ┌───────▼───────┐
  │  Enrichment   │   │  Vector Store │   │  Alert Engine │
  │  (geo, device)│   │  (embeddings) │   │  (thresholds) │
  └───────────────┘   └───────────────┘   └───────────────┘
```

## 4. Service Communication (Planned — Not Implemented)

```
┌──────────┐     HTTP/gRPC     ┌──────────┐
│ Service A │ ◄──────────────► │ Service B │
└──────────┘                   └──────────┘
      │                              │
      │  Kafka (async)               │  Kafka (async)
      ▼                              ▼
┌──────────┐                   ┌──────────┐
│  Redis   │                   │  Redis   │
└──────────┘                   └──────────┘

Communication Patterns:
- Synchronous: HTTP/gRPC for real-time queries
- Asynchronous: Kafka for event propagation
- Cache: Redis for distributed caching
- Streaming: Kafka for real-time data flow
```

## 5. Database Architecture (Planned — Not Implemented)

```
┌─────────────────────────────────────────────────────────────┐
│                    DATABASE STRATEGY                        │
├─────────────┬──────────────────┬────────────┬──────────────┤
│  PostgreSQL │     Redis        │  Qdrant    │  ClickHouse  │
│  (Primary)  │    (Cache)       │ (Vectors)  │ (Analytics)  │
├─────────────┼──────────────────┼────────────┼──────────────┤
│ Structured  │ Session store    │ Embeddings │ Event logs   │
│ Relational  │ Rate limiting    │ Similarity │ Aggregations │
│ ACID        │ Pub/Sub          │ Semantic   │ Time-series  │
│ Transactions│ Distributed lock │ Memory     │ OLAP queries │
│ Partitioned │ API cache        │ Hybrid     │ Materialized │
│ by org_id   │ Job queue        │ search     │ views        │
└─────────────┴──────────────────┴────────────┴──────────────┘

PostgreSQL Topology:
- Primary: Write-heavy operations
- Replicas: Read-heavy operations (3x replicas)
- Citus: Distributed across shards for 100M+ rows
- Partitioning: Range by org_id + hash by customer_id
```

## 6. AI Architecture (Planned — Not Implemented)

```
┌─────────────────────────────────────────────────────────────┐
│                      AI PIPELINE                            │
│                                                             │
│  ┌─────────┐   ┌──────────┐   ┌────────┐   ┌──────────┐  │
│  │ Event   │──►│ Feature  │──►│ Model  │──►│  Twin    │  │
│  │ Stream  │   │ Pipeline │   │ Infer  │   │  Update  │  │
│  └─────────┘   └──────────┘   └────────┘   └──────────┘  │
│       │              │             │              │        │
│       ▼              ▼             ▼              ▼        │
│  ┌─────────┐   ┌──────────┐   ┌────────┐   ┌──────────┐  │
│  │ Feature │   │ Embedding│   │ MLflow │   │  Vector  │  │
│  │ Store   │   │  Gen     │   │Registry│   │  Store   │  │
│  └─────────┘   └──────────┘   └────────┘   └──────────┘  │
│                                                             │
│  Models Deployed:                                           │
│  - Customer Segmentation (KMeans + HDBSCAN)                 │
│  - Churn Prediction (LightGBM + XGBoost ensemble)           │
│  - Intent Classification (PyTorch BERT)                    │
│  - Recommendation (Matrix Factorization + LLM)             │
│  - Engagement Forecasting (Prophet + LSTM)                 │
│  - Sentiment Analysis (Fine-tuned BART)                    │
│  - LTV Prediction (Quantile Regression)                    │
└─────────────────────────────────────────────────────────────┘
```

## 7. ML Architecture (Planned — Not Implemented)

```
┌──────────────────────────────────────────────────────────┐
│                    ML PIPELINE                            │
│                                                          │
│  ┌────────────┐    ┌────────────┐    ┌────────────┐    │
│  │ Data       │───►│ Feature    │───►│ Training   │    │
│  │ Ingestion  │    │ Engineering│    │ Pipeline   │    │
│  └────────────┘    └────────────┘    └──────┬─────┘    │
│                                              │          │
│  ┌────────────┐    ┌────────────┐           │          │
│  │ Drift      │◄───│ Monitoring │◄──────────┘          │
│  │ Detection  │    │ Dashboard  │                       │
│  └────────────┘    └────────────┘                       │
│       │                                                 │
│       ▼                                                 │
│  ┌────────────┐    ┌────────────┐    ┌────────────┐    │
│  │ Model      │───►│ A/B Test   │───►│ Production │    │
│  │ Registry   │    │ Framework  │    │ Deployment │    │
│  └────────────┘    └────────────┘    └────────────┘    │
│                                                          │
│  Feature Store: Redis + PostgreSQL                       │
│  Model Registry: MLflow                                  │
│  Training: Kubeflow Pipelines                            │
│  Inference: TorchServe + Triton                          │
│  Monitoring: Prometheus + Grafana + WhyLabs             │
└──────────────────────────────────────────────────────────┘
```

## 8. Deployment Architecture (Planned — Not Implemented)

```
┌──────────────────────────────────────────────────────────┐
│                      AWS CLOUD                            │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │          VPC (10.0.0.0/16)                      │   │
│  │                                                  │   │
│  │  ┌──────────────┐  ┌──────────────┐            │   │
│  │  │  Public      │  │  Private     │            │   │
│  │  │  Subnets     │  │  Subnets     │            │   │
│  │  │  - ALB       │  │  - EKS       │            │   │
│  │  │  - NAT GW    │  │  - RDS       │            │   │
│  │  │  - Bastion   │  │  - ElastiCache│           │   │
│  │  └──────────────┘  │  - MSK       │            │   │
│  │                    │  - Qdrant    │            │   │
│  │                    │  - S3 VPCE   │            │   │
│  │                    └──────────────┘            │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │  EKS Cluster (Kubernetes 1.28+)                 │   │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐  │   │
│  │  │ Node Group │ │ Node Group │ │ Node Group │  │   │
│  │  │ (CPU: 8-32)│ │ (GPU: A10G)│ │ (Spot: 4-16) │  │   │
│  │  │ Services   │ │ ML Infer   │ │ Batch Jobs │  │   │
│  │  └────────────┘ └────────────┘ └────────────┘  │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  Auto Scaling:                                           │
│  - HPA: CPU > 70%, Memory > 80%, Custom Metrics        │
│  - VPA: Recommended limits                              │
│  - Cluster Autoscaler: 3-50 nodes                       │
│  - Karpenter: Spot + On-Demand mix                      │
└──────────────────────────────────────────────────────────┘
```

## 9. Security Architecture (Planned — Not Implemented)

```
┌──────────────────────────────────────────────────────────┐
│                   SECURITY LAYERS                        │
│                                                          │
│  1. Network Security:                                    │
│     - VPC with public/private subnets                    │
│     - Security Groups (least privilege)                  │
│     - Network ACLs                                      │
│     - AWS WAF (SQL injection, XSS, DDoS)                │
│     - API Gateway with rate limiting                     │
│                                                          │
│  2. Authentication:                                      │
│     - JWT (HS256) with short expiry (15min)  # TODO: Production — change to RS256 with key pair             │
│     - Refresh tokens (7 day rotation)                    │
│     - OAuth 2.0 + OIDC                                   │
│     - MFA via TOTP                                      │
│     - SSO (SAML 2.0, Azure AD, Google Workspace)        │
│                                                          │
│  3. Authorization:                                       │
│     - RBAC (Role-Based Access Control)                   │
│     - ABAC (Attribute-Based Access Control)              │
│     - Row-level security in PostgreSQL                   │
│     - API scope-based permissions                        │
│                                                          │
│  4. Data Security:                                       │
│     - Encryption at rest (AES-256)                       │
│     - Encryption in transit (TLS 1.3)                   │
│     - Vault for secrets (HashiCorp Vault / AWS Secrets) │
│     - PII masking in logs                                │
│     - Data retention policies                            │
│                                                          │
│  5. Audit & Compliance:                                  │
│     - Complete audit trail                               │
│     - SOC 2 compliance ready                            │
│     - GDPR data deletion pipeline                        │
│     - HIPAA-compliant logging (if needed)                │
│     - Penetration testing automation                     │
└──────────────────────────────────────────────────────────┘
```

## 10. Monitoring Architecture (Planned — Not Implemented)

```
┌──────────────────────────────────────────────────────────┐
│                   MONITORING STACK                        │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Metrics                                          │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐       │   │
│  │  │Prometheus│  │  Grafana │  │  Alert   │       │   │
│  │  │Scrape    │──►│Dashboards│──►│ Manager  │       │   │
│  │  └──────────┘  └──────────┘  └──────────┘       │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Logging                                         │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐       │   │
│  │  │Fluent Bit│──►│OpenSearch│──►│  Kibana  │       │   │
│  │  │DaemonSet │  │  Cluster │  │Dashboards│       │   │
│  │  └──────────┘  └──────────┘  └──────────┘       │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Tracing                                         │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐       │   │
│  │  │OpenTeleme│──►│  Jaeger │──►│  Tempo   │       │   │
│  │  │try Agent │  │  (Trace) │  │ (Storage)│       │   │
│  │  └──────────┘  └──────────┘  └──────────┘       │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  Key Metrics:                                            │
│  - p50/p95/p99 latency per endpoint                      │
│  - Event throughput (msg/sec)                            │
│  - Twin update latency                                    │
│  - Model inference time                                  │
│  - Prediction accuracy drift                             │
│  - Kafka consumer lag                                    │
│  - CPU/Memory per pod                                    │
│  - Error rate by service                                 │
│  - SLO/SLI tracking                                     │
└──────────────────────────────────────────────────────────┘
```

## Data Flow Diagram

```
Customer Action
      │
      ▼
SDK/API Event ──► Kafka ──► Event Router
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼             ▼
            Feature Store    Embedding Gen    Raw Store
                    │             │             │
                    └─────────────┼─────────────┘
                                  │
                                  ▼
                         Twin Update Pipeline
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼             ▼
               Predictions    Segments     Recommendations
                    │             │             │
                    └─────────────┼─────────────┘
                                  │
                                  ▼
                         Campaign Simulation
                                  │
                                  ▼
                         Action/Notification
```

## Technology Stack Summary

| Layer | Technology | Rationale | Status |
|-------|-----------|-----------|--------|
| Frontend | Next.js 15, TypeScript, Tailwind, ShadCN | SSR, SEO, type safety | Implemented |
| Backend | Python 3.12+, FastAPI | Async, Pydantic, perf | Implemented |
| API Gateway | Traefik | Rate limiting, auth, routing | Planned |
| Service Mesh | Istio | mTLS, traffic mgmt | Planned |
| Events | Kafka (single broker) | Durability, replay, scale | Implemented |
| Main DB | PostgreSQL 16 | ACID, JSONB, extensions | Implemented |
| Cache | Redis 7 | Sub-ms latency | Implemented |
| Vectors | Qdrant v1.11 | High-perf ANN, filtering | Implemented |
| Analytics | ClickHouse | Columnar, real-time OLAP | Planned |
| ML Registry | MLflow | Experiment tracking | Planned |
| ML Serving | In-process | Direct model inference | Implemented |
| Container | Docker Compose | Local orchestration | Implemented |
| Orchestration | Kubernetes/EKS | Production scaling | Planned |
| IaC | Terraform | AWS provisioning | Planned |
| CI/CD | GitHub Actions | Pipeline automation | Planned |
| Monitoring | Prometheus + Grafana | Metrics & alerting | Implemented |
| Logging | JSON logs (stdout) | Centralized logging | Implemented |
| Tracing | OpenTelemetry | Distributed tracing | Planned |
| Secrets | .env file | Config management | Implemented |
