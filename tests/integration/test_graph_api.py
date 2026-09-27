import os
import tempfile
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from workers.tasks.ingestion import run_ingestion_pipeline


@pytest.mark.asyncio
async def test_graph_endpoints_and_multitenant_isolation(client: AsyncClient, db_session: AsyncSession):
    # 1. Register User A and create Repository A
    res_a = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "graph_user_a@codeatlas.dev",
            "password": "Password123!",
            "full_name": "Graph Alpha",
        },
    )
    assert res_a.status_code == 201
    token_a = res_a.json()["tokens"]["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    create_a = await client.post(
        "/api/v1/repositories",
        json={
            "github_url": "https://github.com/graph-org/graph-service.git",
            "default_branch": "main",
        },
        headers=headers_a,
    )
    assert create_a.status_code == 201
    repo_a = create_a.json()
    repo_a_id = repo_a["id"]

    # 2. Register User B (for tenant boundary attacks)
    res_b = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "graph_user_b@codeatlas.dev",
            "password": "Password123!",
            "full_name": "Graph Beta",
        },
    )
    assert res_b.status_code == 201
    token_b = res_b.json()["tokens"]["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 3. Populate Repository A with code (including endpoints, models, and circular dependencies)
    with tempfile.TemporaryDirectory() as temp_dir:
        # DB Models
        with open(os.path.join(temp_dir, "db.py"), "w", encoding="utf-8") as f:
            f.write('''
from sqlalchemy.orm import DeclarativeBase

class BaseModel(DeclarativeBase):
    pass

class AccountModel(BaseModel):
    __tablename__ = "accounts"
    def get_account_balance(self):
        return 1000
''')

        # Service
        with open(os.path.join(temp_dir, "service.py"), "w", encoding="utf-8") as f:
            f.write('''
from db import AccountModel

class AccountService:
    def check_balance(self):
        acc = AccountModel()
        return acc.get_account_balance()
''')

        # API Endpoints
        with open(os.path.join(temp_dir, "api.py"), "w", encoding="utf-8") as f:
            f.write('''
from service import AccountService

@router.get("/api/v1/balance")
def get_balance_endpoint():
    svc = AccountService()
    return svc.check_balance()
''')

        # Circular import modules: cycle_x <-> cycle_y
        with open(os.path.join(temp_dir, "cycle_x.py"), "w", encoding="utf-8") as f:
            f.write('''
from cycle_y import helper_y

def helper_x():
    return helper_y()
''')

        with open(os.path.join(temp_dir, "cycle_y.py"), "w", encoding="utf-8") as f:
            f.write('''
from cycle_x import helper_x

def helper_y():
    return helper_x()
''')

        commit_sha = "c0ffee1234567890abcdef"
        await run_ingestion_pipeline(
            repository_id=repo_a_id,
            commit_sha=commit_sha,
            source_directory=temp_dir,
            session=db_session,
        )

    # 4. Verify GET /{repository_id}/graph
    graph_res = await client.get(f"/api/v1/repositories/{repo_a_id}/graph", headers=headers_a)
    assert graph_res.status_code == 200
    graph_data = graph_res.json()
    assert graph_data["nodes_count"] > 0
    assert graph_data["edges_count"] > 0
    assert len(graph_data["nodes"]) == graph_data["nodes_count"]
    assert len(graph_data["edges"]) == graph_data["edges_count"]

    # Verify nodes have in_degree, out_degree, node_key
    sample_node = graph_data["nodes"][0]
    assert "node_key" in sample_node
    assert "in_degree" in sample_node
    assert "out_degree" in sample_node
    assert "metrics" in graph_data
    assert "total_nodes" in graph_data["metrics"]

    # 5. Verify Graph Filtering
    # 5a. Filter by node_type=ENDPOINT
    endpoint_res = await client.get(
        f"/api/v1/repositories/{repo_a_id}/graph?node_type=ENDPOINT",
        headers=headers_a,
    )
    assert endpoint_res.status_code == 200
    endpoint_data = endpoint_res.json()
    assert all(n["node_type"] == "ENDPOINT" for n in endpoint_data["nodes"])
    assert any("get_balance_endpoint" in n["name"] for n in endpoint_data["nodes"])

    # 5b. Filter by file_path
    file_res = await client.get(
        f"/api/v1/repositories/{repo_a_id}/graph?file_path=service.py",
        headers=headers_a,
    )
    assert file_res.status_code == 200
    file_data = file_res.json()
    assert all("service.py" in (n.get("file_path") or "") for n in file_data["nodes"])

    # 5c. Filter by max_nodes
    max_res = await client.get(
        f"/api/v1/repositories/{repo_a_id}/graph?max_nodes=2",
        headers=headers_a,
    )
    assert max_res.status_code == 200
    assert len(max_res.json()["nodes"]) <= 2

    # 5d. Neighborhood subgraph extraction via focus_symbol
    focus_res = await client.get(
        f"/api/v1/repositories/{repo_a_id}/graph?focus_symbol=check_balance",
        headers=headers_a,
    )
    assert focus_res.status_code == 200
    focus_data = focus_res.json()
    assert focus_data["nodes_count"] > 0
    assert any("check_balance" in n["name"] for n in focus_data["nodes"])

    # 6. Verify GET /{repository_id}/graph/cycles (Tarjan's SCC cycle detection)
    cycles_res = await client.get(f"/api/v1/repositories/{repo_a_id}/graph/cycles", headers=headers_a)
    assert cycles_res.status_code == 200
    cycles_data = cycles_res.json()
    assert cycles_data["total_cycles"] >= 1
    cycle = cycles_data["cycles"][0]
    assert cycle["cycle_type"] in ("IMPORT_CYCLE", "CALL_CYCLE", "MIXED_CYCLE")
    assert cycle["length"] >= 1
    assert any("cycle_" in f for f in cycle["participating_files"])

    # 7. Verify GET /{repository_id}/graph/nodes/{node_key}
    target_key = next(n["node_key"] for n in graph_data["nodes"] if "check_balance" in n["name"])
    node_detail_res = await client.get(
        f"/api/v1/repositories/{repo_a_id}/graph/nodes/{target_key}",
        headers=headers_a,
    )
    assert node_detail_res.status_code == 200
    node_detail = node_detail_res.json()
    assert node_detail["node"]["node_key"] == target_key
    assert "in_degree" in node_detail
    assert "out_degree" in node_detail
    assert "incoming_callers" in node_detail
    assert "outgoing_callees" in node_detail
    assert node_detail["neighborhood_nodes_count"] >= 1

    # 404 for non-existent node
    nf_node_res = await client.get(
        f"/api/v1/repositories/{repo_a_id}/graph/nodes/non_existent_key_999",
        headers=headers_a,
    )
    assert nf_node_res.status_code == 404

    # 8. Verify GET /{repository_id}/graph/impact
    impact_res = await client.get(
        f"/api/v1/repositories/{repo_a_id}/graph/impact?symbol=get_account_balance",
        headers=headers_a,
    )
    assert impact_res.status_code == 200
    impact = impact_res.json()
    assert impact["target_name"] == "get_account_balance"
    assert impact["impact_score"] > 0
    assert impact["severity"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    assert impact["upstream_callers_count"] >= 1
    assert "score_breakdown" in impact
    assert "endpoints_factor" in impact["score_breakdown"]
    assert any("check_balance" in s for s in impact["impacted_symbols"])

    # 9. Verify GET /{repository_id}/graph/path
    path_res = await client.get(
        f"/api/v1/repositories/{repo_a_id}/graph/path?source_symbol=get_balance_endpoint&target_symbol=get_account_balance",
        headers=headers_a,
    )
    assert path_res.status_code == 200
    path_data = path_res.json()
    assert path_data["path_exists"] is True
    assert path_data["path_length"] >= 2
    assert len(path_data["call_chain"]) >= 3

    # 10. Multi-Tenant Security Isolation (User B cannot access User A's graph endpoints)
    # 10a. Graph topology
    cross_graph = await client.get(f"/api/v1/repositories/{repo_a_id}/graph", headers=headers_b)
    assert cross_graph.status_code == 403

    # 10b. Cycles
    cross_cycles = await client.get(f"/api/v1/repositories/{repo_a_id}/graph/cycles", headers=headers_b)
    assert cross_cycles.status_code == 403

    # 10c. Node detail
    cross_node = await client.get(f"/api/v1/repositories/{repo_a_id}/graph/nodes/{target_key}", headers=headers_b)
    assert cross_node.status_code == 403

    # 10d. Impact analysis
    cross_impact = await client.get(
        f"/api/v1/repositories/{repo_a_id}/graph/impact?symbol=get_account_balance",
        headers=headers_b,
    )
    assert cross_impact.status_code == 403

    # 10e. Path analysis
    cross_path = await client.get(
        f"/api/v1/repositories/{repo_a_id}/graph/path?source_symbol=get_balance_endpoint&target_symbol=get_account_balance",
        headers=headers_b,
    )
    assert cross_path.status_code == 403

    # 11. Commit Scoping
    # Query with matching commit sha
    commit_res = await client.get(
        f"/api/v1/repositories/{repo_a_id}/graph?commit_sha={commit_sha}",
        headers=headers_a,
    )
    assert commit_res.status_code == 200
    assert commit_res.json()["nodes_count"] > 0

    # Query with non-existent commit sha
    empty_commit_res = await client.get(
        f"/api/v1/repositories/{repo_a_id}/graph?commit_sha=nonexistent_sha_000000",
        headers=headers_a,
    )
    assert empty_commit_res.status_code == 200
    assert empty_commit_res.json()["nodes_count"] == 0
