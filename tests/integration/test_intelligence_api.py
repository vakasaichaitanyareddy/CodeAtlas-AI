import os
import tempfile
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from workers.tasks.ingestion import run_ingestion_pipeline


@pytest.mark.asyncio
async def test_intelligence_endpoints_and_isolation(client: AsyncClient, db_session: AsyncSession):
    # 1. Register User A and create Repository A
    res_a = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "intel_user_a@codeatlas.dev",
            "password": "Password123!",
            "full_name": "Intel Alpha",
        },
    )
    token_a = res_a.json()["tokens"]["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    create_a = await client.post(
        "/api/v1/repositories",
        json={
            "github_url": "https://github.com/intel-org/service-alpha.git",
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
            "email": "intel_user_b@codeatlas.dev",
            "password": "Password123!",
            "full_name": "Intel Beta",
        },
    )
    token_b = res_b.json()["tokens"]["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 3. Populate Repository A with real code via the ingestion pipeline
    with tempfile.TemporaryDirectory() as temp_dir:
        models_file = os.path.join(temp_dir, "db.py")
        with open(models_file, "w", encoding="utf-8") as f:
            f.write('''
from sqlalchemy.orm import DeclarativeBase

class BaseModel(DeclarativeBase):
    pass

class UserModel(BaseModel):
    __tablename__ = "users"
    def get_display_name(self):
        return "Alice"

class UserHelper:
    def format_name(self, name: str):
        return name.title()
''')

        service_file = os.path.join(temp_dir, "service.py")
        with open(service_file, "w", encoding="utf-8") as f:
            f.write('''
from db import UserModel

def fetch_user_profile(user_id: int):
    user = UserModel()
    return user.get_display_name()
''')

        api_file = os.path.join(temp_dir, "api.py")
        with open(api_file, "w", encoding="utf-8") as f:
            f.write('''
from fastapi import APIRouter
from service import fetch_user_profile

router = APIRouter()

@router.get("/users/{user_id}")
async def get_user_route(user_id: int):
    return fetch_user_profile(user_id)
''')

        # Run ingestion synchronously inside the test database session
        await run_ingestion_pipeline(
            repository_id=repo_a_id,
            commit_sha="a1b2c3d4e5f6",
            source_directory=temp_dir,
            session=db_session,
        )

    # 4. Verify Files API
    files_res = await client.get(f"/api/v1/repositories/{repo_a_id}/files", headers=headers_a)
    assert files_res.status_code == 200
    files = files_res.json()
    assert len(files) == 3
    file_map = {f["path"]: f["id"] for f in files}
    assert "db.py" in file_map
    assert "service.py" in file_map
    assert "api.py" in file_map

    # 5. Verify File Details & AST Symbol Inspection
    db_file_id = file_map["db.py"]
    file_details_res = await client.get(
        f"/api/v1/repositories/{repo_a_id}/files/{db_file_id}",
        headers=headers_a,
    )
    assert file_details_res.status_code == 200
    file_details = file_details_res.json()
    assert file_details["path"] == "db.py"
    assert file_details["language"] == "python"
    symbol_names = [s["name"] for s in file_details["symbols"]]
    assert "UserModel" in symbol_names
    assert "get_display_name" in symbol_names

    # 6. Verify Symbols API with Filtering
    symbols_res = await client.get(f"/api/v1/repositories/{repo_a_id}/symbols", headers=headers_a)
    assert symbols_res.status_code == 200
    all_symbols = symbols_res.json()
    assert len(all_symbols) >= 3

    # Filter by query
    query_res = await client.get(
        f"/api/v1/repositories/{repo_a_id}/symbols?query=fetch_user",
        headers=headers_a,
    )
    assert query_res.status_code == 200
    assert len(query_res.json()) == 1
    assert query_res.json()[0]["name"] == "fetch_user_profile"

    # Filter by symbol type
    class_res = await client.get(
        f"/api/v1/repositories/{repo_a_id}/symbols?symbol_type=CLASS",
        headers=headers_a,
    )
    assert class_res.status_code == 200
    classes = class_res.json()
    assert any(c["name"] == "UserHelper" for c in classes)

    # 7. Verify Dependency Graph API
    graph_res = await client.get(f"/api/v1/repositories/{repo_a_id}/graph", headers=headers_a)
    assert graph_res.status_code == 200
    graph_data = graph_res.json()
    assert graph_data["nodes_count"] > 0
    assert graph_data["edges_count"] > 0
    assert len(graph_data["nodes"]) == graph_data["nodes_count"]
    assert len(graph_data["edges"]) == graph_data["edges_count"]

    # 8. Verify Blast-Radius Impact Analysis API
    impact_res = await client.get(
        f"/api/v1/repositories/{repo_a_id}/graph/impact?symbol=get_display_name",
        headers=headers_a,
    )
    assert impact_res.status_code == 200
    impact = impact_res.json()
    assert impact["target_name"] == "get_display_name"
    assert impact["impact_score"] > 0
    assert impact["upstream_callers_count"] >= 1
    assert any("fetch_user_profile" in s for s in impact["impacted_symbols"])

    # 9. Verify Shortest Call Path API
    path_res = await client.get(
        f"/api/v1/repositories/{repo_a_id}/graph/path?source_symbol=get_user_route&target_symbol=get_display_name",
        headers=headers_a,
    )
    assert path_res.status_code == 200
    path_data = path_res.json()
    assert path_data["path_exists"] is True
    assert path_data["path_length"] >= 2
    assert len(path_data["call_chain"]) >= 3

    # 10. Verify Indexing Trigger & Job Progress Check
    index_res = await client.post(f"/api/v1/repositories/{repo_a_id}/index", headers=headers_a)
    assert index_res.status_code == 202
    job_info = index_res.json()
    assert "job_id" in job_info
    assert job_info["status"] == "QUEUED"
    job_id = job_info["job_id"]

    job_status_res = await client.get(
        f"/api/v1/repositories/{repo_a_id}/jobs/{job_id}",
        headers=headers_a,
    )
    assert job_status_res.status_code == 200
    job_status = job_status_res.json()
    assert job_status["id"] == job_id
    assert job_status["repository_id"] == repo_a_id

    # 11. Multi-Tenant Isolation Checks (User B attempting unauthorized access to Repo A)
    # File details
    cross_file = await client.get(
        f"/api/v1/repositories/{repo_a_id}/files/{db_file_id}",
        headers=headers_b,
    )
    assert cross_file.status_code == 403

    # Symbols list
    cross_sym = await client.get(
        f"/api/v1/repositories/{repo_a_id}/symbols",
        headers=headers_b,
    )
    assert cross_sym.status_code == 403

    # Graph
    cross_graph = await client.get(
        f"/api/v1/repositories/{repo_a_id}/graph",
        headers=headers_b,
    )
    assert cross_graph.status_code == 403

    # Impact analysis
    cross_impact = await client.get(
        f"/api/v1/repositories/{repo_a_id}/graph/impact?symbol=get_display_name",
        headers=headers_b,
    )
    assert cross_impact.status_code == 403

    # Index trigger
    cross_index = await client.post(
        f"/api/v1/repositories/{repo_a_id}/index",
        headers=headers_b,
    )
    assert cross_index.status_code == 403
