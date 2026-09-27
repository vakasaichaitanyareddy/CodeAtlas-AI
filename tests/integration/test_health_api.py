import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_liveness_endpoint(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "service" in data


@pytest.mark.asyncio
async def test_metrics_endpoint_increments_on_requests(client: AsyncClient):
    # Make requests to generate metrics
    await client.get("/health")
    await client.get("/health")

    # Scrape metrics endpoint
    resp = await client.get("/metrics")
    assert resp.status_code == 200
    metrics_output = resp.text

    assert "codeatlas_http_requests_total" in metrics_output
    assert "codeatlas_http_request_duration_seconds" in metrics_output
    assert 'endpoint="/health"' in metrics_output
    assert 'method="GET"' in metrics_output
    assert 'status_code="200"' in metrics_output


@pytest.mark.asyncio
async def test_health_readiness_all_healthy(client: AsyncClient, monkeypatch):
    async def mock_ping_db():
        return True

    async def mock_check_redis():
        return "healthy"

    async def mock_check_qdrant():
        return "healthy"

    monkeypatch.setattr("apps.api.app.api.v1.health.ping_db", mock_ping_db)
    monkeypatch.setattr("apps.api.app.api.v1.health.check_redis_health", mock_check_redis)
    monkeypatch.setattr("apps.api.app.api.v1.health.check_qdrant_health", mock_check_qdrant)

    resp = await client.get("/health/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ready"
    assert data["dependencies"]["postgres"] == "healthy"
    assert data["dependencies"]["redis"] == "healthy"
    assert data["dependencies"]["qdrant"] == "healthy"


@pytest.mark.asyncio
async def test_health_readiness_individual_failures(client: AsyncClient, monkeypatch):
    async def mock_ping_db():
        return True

    async def mock_check_redis():
        return "healthy"

    # Simulate Qdrant failure
    async def mock_check_qdrant_fail():
        return "unreachable"

    monkeypatch.setattr("apps.api.app.api.v1.health.ping_db", mock_ping_db)
    monkeypatch.setattr("apps.api.app.api.v1.health.check_redis_health", mock_check_redis)
    monkeypatch.setattr("apps.api.app.api.v1.health.check_qdrant_health", mock_check_qdrant_fail)

    resp = await client.get("/health/ready")
    assert resp.status_code == 503
    data = resp.json()
    assert data["status"] == "degraded"
    assert data["dependencies"]["qdrant"] == "unreachable"
    assert data["dependencies"]["postgres"] == "healthy"
    assert data["dependencies"]["redis"] == "healthy"

    # Simulate Postgres failure
    async def mock_ping_db_fail():
        return False

    async def mock_check_qdrant_ok():
        return "healthy"

    monkeypatch.setattr("apps.api.app.api.v1.health.ping_db", mock_ping_db_fail)
    monkeypatch.setattr("apps.api.app.api.v1.health.check_qdrant_health", mock_check_qdrant_ok)

    resp_pg_fail = await client.get("/health/ready")
    assert resp_pg_fail.status_code == 503
    assert resp_pg_fail.json()["dependencies"]["postgres"] == "unreachable"
