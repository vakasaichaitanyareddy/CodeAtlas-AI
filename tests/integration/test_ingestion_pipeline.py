import os
import tempfile
import pytest
from sqlalchemy import select

from tests.conftest import TestSessionLocal
from apps.api.app.models import (
    User,
    Repository,
    IndexJob,
    RepositoryFile,
    CodeSymbol,
    CodeChunk,
    GraphNode,
    GraphEdge,
)
from workers.tasks.ingestion import run_ingestion_pipeline


@pytest.mark.anyio
async def test_full_repository_ingestion_pipeline(db_session):
    # 1. Create test owner and repository using db_session
    user = User(
        email="pipeline_tester@codeatlas.dev",
        hashed_password="dummy_hashed_password",
        full_name="Pipeline Tester",
    )
    db_session.add(user)
    await db_session.flush()

    repo = Repository(
        owner_id=user.id,
        name="ecommerce-core",
        full_name="org/ecommerce-core",
        github_url="https://github.com/org/ecommerce-core.git",
        default_branch="main",
        is_indexed=False,
    )
    db_session.add(repo)
    await db_session.commit()
    repo_id = repo.id

    # 2. Create temporary repository directory with real source files
    with tempfile.TemporaryDirectory() as temp_dir:
        models_path = os.path.join(temp_dir, "models.py")
        with open(models_path, "w", encoding="utf-8") as f:
            f.write('''
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

class ProductModel(Base):
    __tablename__ = "products"
    def get_sku(self):
        return "SKU-001"
''')

        service_path = os.path.join(temp_dir, "service.py")
        with open(service_path, "w", encoding="utf-8") as f:
            f.write('''
from models import ProductModel

class CatalogService:
    """Manages product catalog."""
    def lookup_product(self, prod_id: str):
        prod = ProductModel()
        return prod.get_sku()
''')

        ts_client_path = os.path.join(temp_dir, "client.ts")
        with open(ts_client_path, "w", encoding="utf-8") as f:
            f.write('''
export interface ProductDTO {
    sku: string;
}

export const fetchProduct = async (id: string): Promise<ProductDTO> => {
    return { sku: "SKU-001" };
};
''')

        commit_sha = "c0ffee1234567890abcdef"
        result = await run_ingestion_pipeline(
            repository_id=repo_id,
            commit_sha=commit_sha,
            source_directory=temp_dir,
            session=db_session,
        )

        assert result["status"] == "completed"
        stats = result["stats"]
        assert stats["files_count"] == 3
        assert stats["symbols_count"] >= 3
        assert stats["nodes_count"] >= 3
        assert stats["chunks_count"] >= 3

    # 3. Verify database persistence using db_session
    # Verify IndexJob
    job_res = await db_session.execute(
        select(IndexJob).where(
            IndexJob.repository_id == repo_id,
            IndexJob.commit_sha == commit_sha,
        )
    )
    job = job_res.scalar_one()
    assert job.status == "COMPLETED"
    assert job.progress_percent == 100
    assert job.error_message is None

    # Verify Repository state
    repo_res = await db_session.execute(select(Repository).where(Repository.id == repo_id))
    updated_repo = repo_res.scalar_one()
    assert updated_repo.is_indexed is True
    assert updated_repo.current_commit_sha == commit_sha
    assert updated_repo.status == "ACTIVE"

    # Verify RepositoryFiles
    files_res = await db_session.execute(
        select(RepositoryFile).where(RepositoryFile.repository_id == repo_id)
    )
    files = files_res.scalars().all()
    assert len(files) == 3
    paths = {f.path for f in files}
    assert "models.py" in paths
    assert "service.py" in paths
    assert "client.ts" in paths

    # Verify CodeSymbols
    syms_res = await db_session.execute(
        select(CodeSymbol).where(CodeSymbol.repository_id == repo_id)
    )
    symbols = syms_res.scalars().all()
    sym_names = {s.name for s in symbols}
    assert "ProductModel" in sym_names
    assert "CatalogService" in sym_names
    assert "lookup_product" in sym_names
    assert "fetchProduct" in sym_names

    # Verify GraphNodes and GraphEdges
    nodes_res = await db_session.execute(
        select(GraphNode).where(GraphNode.repository_id == repo_id)
    )
    nodes = nodes_res.scalars().all()
    assert len(nodes) >= 3

    edges_res = await db_session.execute(
        select(GraphEdge).where(GraphEdge.repository_id == repo_id)
    )
    edges = edges_res.scalars().all()
    assert len(edges) >= 2

    # Verify CodeChunks
    chunks_res = await db_session.execute(
        select(CodeChunk).where(CodeChunk.repository_id == repo_id)
    )
    chunks = chunks_res.scalars().all()
    assert len(chunks) >= 3
    for ch in chunks:
        assert ch.start_line > 0
        assert ch.end_line >= ch.start_line
        assert len(ch.content) > 0
        assert len(ch.content_hash) == 64

