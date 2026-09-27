import pytest
import redis
import httpx
from workers.celery_app import celery_app
from workers.tasks.ingestion import ingest_repository


def test_real_celery_broker_connection():
    """Verify that Celery can communicate with the real Redis broker."""
    try:
        r = redis.Redis(host="localhost", port=6379, protocol=2, socket_timeout=1)
        r.ping()
    except Exception as exc:
        pytest.skip(f"Redis server not available on localhost:6379: {exc}")

    with celery_app.connection_or_acquire() as conn:
        conn.connect()
        assert conn.connected is True


def _create_real_test_repository() -> str:
    """Helper creating a real repository record in PostgreSQL via API."""
    import uuid
    uid = uuid.uuid4().hex[:8]
    email = f"celery_test_{uid}@codeatlas.dev"
    with httpx.Client(base_url="http://localhost:8000", timeout=10.0) as client:
        reg = client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "Password123!",
            "full_name": "Celery Tester",
        })
        assert reg.status_code == 201, f"Register failed: {reg.status_code} {reg.text}"
        token = reg.json()["tokens"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        repo_res = client.post("/api/v1/repositories", json={
            "github_url": f"https://github.com/test-org/celery-repo-{uid}.git",
            "default_branch": "main",
        }, headers=headers)
        assert repo_res.status_code == 201, f"Repo creation failed: {repo_res.status_code} {repo_res.text}"
        return repo_res.json()["id"]


def test_real_celery_task_dispatch_and_execution():
    """Verify asynchronous dispatch to real Celery worker when worker and broker are active."""
    try:
        r = redis.Redis(host="localhost", port=6379, protocol=2, socket_timeout=1)
        r.ping()
    except Exception as exc:
        pytest.skip(f"Redis server not available on localhost:6379: {exc}")

    # Ensure eager mode is OFF to test real broker dispatch
    celery_app.conf.update(task_always_eager=False)

    try:
        # Create a real repository in live PostgreSQL so the worker succeeds
        repo_id = _create_real_test_repository()

        async_res = ingest_repository.delay(repo_id, "commit-real-abc")
        assert async_res.id is not None
        assert async_res.status in ("PENDING", "SUCCESS", "STARTED")

        data = async_res.get(timeout=25)
        assert data["status"] == "completed"
        assert data["repository_id"] == repo_id
        assert async_res.status == "SUCCESS"
    finally:
        celery_app.conf.update(task_always_eager=True)


def test_real_celery_task_failure_and_worker_resilience():
    """Verify that a failing task produces a FAILURE state without killing the Celery worker."""
    try:
        r = redis.Redis(host="localhost", port=6379, protocol=2, socket_timeout=1)
        r.ping()
    except Exception as exc:
        pytest.skip(f"Redis server not available on localhost:6379: {exc}")

    celery_app.conf.update(task_always_eager=False)

    try:
        # 1. Dispatch a task with a nonexistent repo that causes worker to raise ValueError
        failing_res = ingest_repository.delay(
            "nonexistent-repo-should-fail-001",
            "commit-001",
        )
        assert failing_res.id is not None

        with pytest.raises(Exception):
            failing_res.get(timeout=10)
        assert failing_res.status == "FAILURE"

        # 2. Confirm worker is still alive and processes a subsequent valid task
        valid_repo_id = _create_real_test_repository()
        valid_res = ingest_repository.delay(valid_repo_id, "commit-after-failure")
        valid_data = valid_res.get(timeout=25)
        assert valid_res.status == "SUCCESS"
        assert valid_data["status"] == "completed"
        assert valid_data["repository_id"] == valid_repo_id
    finally:
        celery_app.conf.update(task_always_eager=True)
