import os
import tempfile
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from workers.tasks.ingestion import run_ingestion_pipeline
from packages.graph.models import GraphNodeDTO
from packages.retrieval.vector import VectorIndex
from packages.ai import MockEmbeddingProvider
from apps.api.app.services.repository_service import RepositoryService


@pytest.mark.asyncio
async def test_multirepo_graph_scoping_and_collision_isolation(client: AsyncClient, db_session: AsyncSession):
    """Test that two repositories with identical filenames (app.py) maintain complete graph and impact isolation."""
    # 1. Register User
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "scoping_owner@codeatlas.dev",
            "password": "Password123!",
            "full_name": "Scoping Owner",
        },
    )
    assert res.status_code == 201
    token = res.json()["tokens"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create Repo Alpha
    res_a = await client.post(
        "/api/v1/repositories",
        json={
            "github_url": "https://github.com/mock-org/repo-alpha.git",
            "default_branch": "main",
        },
        headers=headers,
    )
    assert res_a.status_code == 201
    repo_a = res_a.json()
    repo_a_id = repo_a["id"]

    # 3. Create Repo Beta
    res_b = await client.post(
        "/api/v1/repositories",
        json={
            "github_url": "https://github.com/mock-org/repo-beta.git",
            "default_branch": "main",
        },
        headers=headers,
    )
    assert res_b.status_code == 201
    repo_b = res_b.json()
    repo_b_id = repo_b["id"]

    # 4. Ingest Repo Alpha with app.py containing AlphaCore and run_alpha
    with tempfile.TemporaryDirectory() as dir_a:
        with open(os.path.join(dir_a, "app.py"), "w", encoding="utf-8") as f:
            f.write('''
class AlphaCore:
    def execute(self):
        return "alpha_core_executed"

def run_alpha():
    core = AlphaCore()
    return core.execute()
''')
        await run_ingestion_pipeline(
            repository_id=repo_a_id,
            commit_sha="main",
            source_directory=dir_a,
            session=db_session,
        )

    # 5. Ingest Repo Beta with app.py containing BetaCore and run_beta
    with tempfile.TemporaryDirectory() as dir_b:
        with open(os.path.join(dir_b, "app.py"), "w", encoding="utf-8") as f:
            f.write('''
class BetaCore:
    def execute(self):
        return "beta_core_executed"

def run_beta():
    core = BetaCore()
    return core.execute()
''')
        await run_ingestion_pipeline(
            repository_id=repo_b_id,
            commit_sha="main",
            source_directory=dir_b,
            session=db_session,
        )

    # 6. Verify Graph A contains AlphaCore and NOT BetaCore
    graph_a_res = await client.get(f"/api/v1/repositories/{repo_a_id}/graph", headers=headers)
    assert graph_a_res.status_code == 200
    graph_a = graph_a_res.json()
    node_names_a = [n["name"] for n in graph_a["nodes"]]
    assert "AlphaCore" in node_names_a
    assert "run_alpha" in node_names_a
    assert "BetaCore" not in node_names_a
    assert "run_beta" not in node_names_a
    # Ensure no CodeAtlas internal code leaked in
    assert not any("apps/api" in (n.get("file_path") or "") for n in graph_a["nodes"])

    # 7. Verify Graph B contains BetaCore and NOT AlphaCore
    graph_b_res = await client.get(f"/api/v1/repositories/{repo_b_id}/graph", headers=headers)
    assert graph_b_res.status_code == 200
    graph_b = graph_b_res.json()
    node_names_b = [n["name"] for n in graph_b["nodes"]]
    assert "BetaCore" in node_names_b
    assert "run_beta" in node_names_b
    assert "AlphaCore" not in node_names_b
    assert "run_alpha" not in node_names_b
    assert not any("apps/api" in (n.get("file_path") or "") for n in graph_b["nodes"])

    # 8. Impact Analysis Isolation on Repo A for "app.py"
    impact_a = await client.get(f"/api/v1/repositories/{repo_a_id}/graph/impact?symbol=app.py", headers=headers)
    assert impact_a.status_code == 200
    data_a = impact_a.json()
    assert "app.py" in data_a["target_name"]
    for sym in data_a["impacted_symbols"]:
        assert "beta" not in sym.lower()

    # 9. Cross-repo rejection: querying run_beta in Repo A must return 404
    cross_res = await client.get(f"/api/v1/repositories/{repo_a_id}/graph/impact?symbol=run_beta", headers=headers)
    assert cross_res.status_code == 404

    # 10. CodeAtlas internal symbol rejection: querying graph.py in Repo A must return 404
    internal_res = await client.get(f"/api/v1/repositories/{repo_a_id}/graph/impact?symbol=graph.py", headers=headers)
    assert internal_res.status_code == 404

    # 11. Shortest path cross-repo rejection
    path_res = await client.get(
        f"/api/v1/repositories/{repo_a_id}/graph/path?source_symbol=AlphaCore&target_symbol=BetaCore",
        headers=headers,
    )
    assert path_res.status_code == 404


@pytest.mark.asyncio
async def test_symbol_matching_prioritization():
    """Verify _find_matching_node algorithm ranks non-test core files over test files."""
    nodes = [
        GraphNodeDTO(
            node_id="file::tests/test_apps/cliapp/app.py",
            node_type="FILE",
            name="app.py",
            qualified_name="file::tests/test_apps/cliapp/app.py",
            file_path="tests/test_apps/cliapp/app.py",
        ),
        GraphNodeDTO(
            node_id="file::src/flask/app.py",
            node_type="FILE",
            name="app.py",
            qualified_name="file::src/flask/app.py",
            file_path="src/flask/app.py",
        ),
        GraphNodeDTO(
            node_id="class::src/flask/app.py::Flask",
            node_type="CLASS",
            name="Flask",
            qualified_name="class::src/flask/app.py::Flask",
            file_path="src/flask/app.py",
        ),
    ]

    # Exact name "app.py" should resolve to src/flask/app.py over tests/
    match_app = RepositoryService._find_matching_node(nodes, "app.py")
    assert match_app is not None
    assert match_app.node_id == "file::src/flask/app.py"

    # Exact path "src/flask/app.py"
    match_path = RepositoryService._find_matching_node(nodes, "src/flask/app.py")
    assert match_path is not None
    assert match_path.node_id == "file::src/flask/app.py"

    # Exact symbol "Flask"
    match_flask = RepositoryService._find_matching_node(nodes, "Flask")
    assert match_flask is not None
    assert match_flask.node_id == "class::src/flask/app.py::Flask"

    # Nonexistent symbol
    match_none = RepositoryService._find_matching_node(nodes, "NonexistentSymbol")
    assert match_none is None


@pytest.mark.asyncio
async def test_vector_index_delete_by_repository():
    """Verify VectorIndex.delete_by_repository purges memory and repository points cleanly."""
    embed_provider = MockEmbeddingProvider()
    vec_index = VectorIndex(embedding_provider=embed_provider, prefer_memory_fallback=True)

    chunks = [
        {
            "id": "chunk_1",
            "file_id": "f1",
            "file_path": "src/main.py",
            "content": "def main(): pass",
            "symbol_name": "main",
        },
        {
            "id": "chunk_2",
            "file_id": "f2",
            "file_path": "src/utils.py",
            "content": "def util(): pass",
            "symbol_name": "util",
        },
    ]

    await vec_index.upsert_chunks("repo_x", "sha_1", chunks)
    await vec_index.upsert_chunks("repo_y", "sha_1", chunks)

    # Search repo_x
    res_x = await vec_index.search("repo_x", "main")
    assert len(res_x) > 0

    # Delete repo_x
    deleted = await vec_index.delete_by_repository("repo_x")
    assert deleted > 0

    # Search repo_x must be empty now
    res_x_after = await vec_index.search("repo_x", "main")
    assert len(res_x_after) == 0

    # Search repo_y must still exist untouched
    res_y_after = await vec_index.search("repo_y", "main")
    assert len(res_y_after) > 0
