# Deployment & Container Architecture

## Overview
CodeAtlas is engineered to run in containerized environments with zero-downtime database migrations, health probes, and horizontal worker scalability.

---

## 1. Services in Docker Compose

| Service | Image / Base | Internal Port | External Port | Role |
|---|---|---|---|---|
| `postgres` | `postgres:16-alpine` | 5432 | 5432 | Relational metadata store |
| `redis` | `redis:7-alpine` | 6379 | 6379 | Caching, rate limiting, Celery broker |
| `qdrant` | `qdrant/qdrant:latest` | 6333, 6334 | 6333, 6334 | Vector database |
| `api` | Python 3.12 (FastAPI) | 8000 | 8000 | Web & REST API gateway |
| `worker` | Python 3.12 (Celery) | - | - | Background task workers |
| `web` | Node.js 20 (Next.js 14) | 3000 | 3000 | Frontend SaaS interface |
| `prometheus` | `prom/prometheus:latest` | 9090 | 9090 | Metrics collection |
| `grafana` | `grafana/grafana:latest` | 3000 | 3001 | Observability dashboards |

---

## 2. Health Probes
- **Liveness probe**: `GET /health` returns `{ "status": "ok" }`.
- **Readiness probe**: `GET /health/ready` verifies connectivity to PostgreSQL, Redis, and Qdrant before accepting traffic.
