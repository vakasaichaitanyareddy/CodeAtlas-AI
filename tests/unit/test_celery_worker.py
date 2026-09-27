from unittest.mock import patch, AsyncMock
import pytest
from workers.celery_app import celery_app
from workers.tasks.ingestion import ingest_repository


def test_celery_task_execution_eager():
    """Verify Celery task pipeline executes, binds arguments, and returns state."""
    celery_app.conf.update(task_always_eager=True)
    try:
        mock_result = {
            "status": "COMPLETED",
            "repository_id": "test-repo-uuid",
            "commit_sha": "commit-sha-7890",
            "indexed_files": 5,
            "symbols_count": 25,
            "nodes_count": 25,
            "edges_count": 10,
            "chunks_count": 30,
        }

        with patch("workers.tasks.ingestion.run_ingestion_pipeline", new_callable=AsyncMock) as mock_pipeline:
            mock_pipeline.return_value = mock_result
            result = ingest_repository.apply(args=["test-repo-uuid", "commit-sha-7890"])

            assert result.status == "SUCCESS"
            assert result.result["status"] == "COMPLETED"
            assert result.result["repository_id"] == "test-repo-uuid"
            assert result.result["commit_sha"] == "commit-sha-7890"
            mock_pipeline.assert_called_once_with(
                repository_id="test-repo-uuid",
                commit_sha="commit-sha-7890",
                source_directory=None,
                job_id=None,
            )
    finally:
        celery_app.conf.update(task_always_eager=False)
