from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from ...database import get_db_session
from ...schemas.repository import (
    RepositoryCreateRequest,
    RepositoryResponse,
    SearchRequest,
    SearchResponse,
    GraphTopologyResponse,
    CircularDependencyResponse,
    GraphNodeDetailResponse,
    GraphImpactResponse,
    GraphPathResponse,
)
from ...services.repository_service import RepositoryService
from ...dependencies import get_current_user
from ...models.user import User

router = APIRouter(prefix="/repositories", tags=["Repositories"])


@router.post("", response_model=RepositoryResponse, status_code=status.HTTP_201_CREATED)
async def create_repository(
    request: RepositoryCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Register and connect a new GitHub repository."""
    repo = await RepositoryService.create_repository(
        session=session,
        user=current_user,
        github_url=request.github_url,
        default_branch=request.default_branch or "main",
        is_private=request.is_private,
    )
    return RepositoryResponse.model_validate(repo)


@router.get("", response_model=List[RepositoryResponse])
async def list_repositories(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """List all repositories owned by the currently authenticated user."""
    repos = await RepositoryService.list_repositories(session, current_user)
    return [RepositoryResponse.model_validate(r) for r in repos]


@router.get("/{repository_id}", response_model=RepositoryResponse)
async def get_repository(
    repository_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Fetch repository details with server-side multi-tenancy authorization."""
    repo = await RepositoryService.get_repository_by_id(session, repository_id, current_user)
    return RepositoryResponse.model_validate(repo)


@router.delete("/{repository_id}", status_code=status.HTTP_200_OK)
async def delete_repository(
    repository_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Delete a repository with server-side multi-tenancy authorization."""
    await RepositoryService.delete_repository(session, repository_id, current_user)
    return {"message": f"Repository '{repository_id}' deleted successfully."}


@router.get("/{repository_id}/files")
async def get_repository_files(
    repository_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Get repository files with multi-tenant isolation."""
    files = await RepositoryService.get_repository_files(session, repository_id, current_user)
    return [{"id": f.id, "path": f.path, "language": f.language} for f in files]


@router.get("/{repository_id}/conversations")
async def get_repository_conversations(
    repository_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Get repository conversations with multi-tenant isolation."""
    convs = await RepositoryService.get_repository_conversations(session, repository_id, current_user)
    return [{"id": c.id, "title": c.title} for c in convs]


@router.get("/{repository_id}/graph", response_model=GraphTopologyResponse)
async def get_repository_graph(
    repository_id: str,
    node_type: Optional[str] = Query(None, description="Filter by node type (FILE, FUNCTION, CLASS, ENDPOINT, MODEL)"),
    file_path: Optional[str] = Query(None, description="Filter by file path substring"),
    max_nodes: int = Query(500, ge=1, le=2000, description="Max nodes to return"),
    focus_symbol: Optional[str] = Query(None, description="Focus symbol name for neighborhood extraction"),
    commit_sha: Optional[str] = Query(None, description="Optional target commit SHA"),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Get repository dependency graph with multi-tenant isolation and query filters."""
    graph = await RepositoryService.get_repository_graph(
        session=session,
        repository_id=repository_id,
        user=current_user,
        node_type=node_type,
        file_path=file_path,
        max_nodes=max_nodes,
        focus_symbol=focus_symbol,
        commit_sha=commit_sha,
    )
    return GraphTopologyResponse.model_validate(graph)


@router.get("/{repository_id}/graph/cycles", response_model=CircularDependencyResponse)
async def get_repository_cycles(
    repository_id: str,
    commit_sha: Optional[str] = Query(None, description="Optional target commit SHA"),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Detect circular dependencies (import cycles, call cycles, mixed cycles) using Tarjan's SCC."""
    result = await RepositoryService.get_repository_cycles(
        session=session,
        repository_id=repository_id,
        user=current_user,
        commit_sha=commit_sha,
    )
    return CircularDependencyResponse.model_validate(result)


@router.get("/{repository_id}/graph/nodes/{node_key:path}", response_model=GraphNodeDetailResponse)
async def get_graph_node_details(
    repository_id: str,
    node_key: str,
    commit_sha: Optional[str] = Query(None, description="Optional target commit SHA"),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Get detailed node information, callers, callees, and bounded neighborhood."""
    details = await RepositoryService.get_graph_node_details(
        session=session,
        repository_id=repository_id,
        node_key=node_key,
        user=current_user,
        commit_sha=commit_sha,
    )
    return GraphNodeDetailResponse.model_validate(details)


@router.post("/{repository_id}/index", status_code=status.HTTP_202_ACCEPTED)
async def trigger_indexing(
    repository_id: str,
    commit_sha: Optional[str] = None,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Trigger background repository indexing job."""
    job = await RepositoryService.trigger_indexing(
        session=session,
        repository_id=repository_id,
        user=current_user,
        commit_sha=commit_sha,
    )
    return {
        "job_id": job.id,
        "repository_id": job.repository_id,
        "status": job.status,
        "current_step": job.current_step,
        "progress_percent": job.progress_percent,
    }


@router.get("/{repository_id}/jobs/{job_id}")
async def get_indexing_job(
    repository_id: str,
    job_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Get status and progress of an indexing job."""
    job = await RepositoryService.get_indexing_job(
        session=session,
        repository_id=repository_id,
        job_id=job_id,
        user=current_user,
    )
    return {
        "id": job.id,
        "repository_id": job.repository_id,
        "commit_sha": job.commit_sha,
        "status": job.status,
        "current_step": job.current_step,
        "progress_percent": job.progress_percent,
        "error_message": job.error_message,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }


@router.get("/{repository_id}/symbols")
async def list_symbols(
    repository_id: str,
    query: Optional[str] = Query(None, description="Filter symbols by name"),
    symbol_type: Optional[str] = Query(None, description="Filter by symbol type (e.g. FUNCTION, CLASS, ENDPOINT)"),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """List extracted AST symbols for the repository."""
    symbols = await RepositoryService.get_repository_symbols(
        session=session,
        repository_id=repository_id,
        user=current_user,
        query=query,
        symbol_type=symbol_type,
    )
    return [
        {
            "id": s.id,
            "name": s.name,
            "symbol_type": s.symbol_type,
            "signature": s.signature,
            "start_line": s.start_line,
            "end_line": s.end_line,
            "file_id": s.file_id,
            "parent_symbol_id": s.parent_symbol_id,
            "docstring": s.docstring,
        }
        for s in symbols
    ]


@router.get("/{repository_id}/files/{file_id}")
async def get_file_details(
    repository_id: str,
    file_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Fetch file metadata and AST-extracted symbols."""
    details = await RepositoryService.get_file_details(
        session=session,
        repository_id=repository_id,
        file_id=file_id,
        user=current_user,
    )
    return {
        "id": details["id"],
        "path": details["path"],
        "language": details["language"],
        "loc": details["loc"],
        "size_bytes": details["size_bytes"],
        "content_hash": details["content_hash"],
        "symbols": [
            {
                "id": s.id,
                "name": s.name,
                "symbol_type": s.symbol_type,
                "signature": s.signature,
                "start_line": s.start_line,
                "end_line": s.end_line,
                "docstring": s.docstring,
            }
            for s in details["symbols"]
        ],
    }


@router.get("/{repository_id}/graph/impact", response_model=GraphImpactResponse)
async def get_graph_impact(
    repository_id: str,
    symbol: str = Query(..., description="Target symbol name or qualified name"),
    commit_sha: Optional[str] = Query(None, description="Optional target commit SHA"),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Compute blast radius impact analysis for a symbol."""
    impact = await RepositoryService.compute_graph_impact(
        session=session,
        repository_id=repository_id,
        symbol_name=symbol,
        user=current_user,
        commit_sha=commit_sha,
    )
    return GraphImpactResponse(
        target_node_id=impact.target_node_id,
        target_name=impact.target_name,
        impact_score=impact.impact_score,
        severity=impact.severity,
        upstream_callers_count=impact.upstream_callers_count,
        impacted_files_count=impact.impacted_files_count,
        affected_endpoints=impact.affected_endpoints,
        affected_endpoints_details=impact.affected_endpoints_details,
        impacted_symbols=impact.impacted_symbols,
        traversal_depth=impact.traversal_depth,
        score_breakdown=impact.score_breakdown,
    )


@router.get("/{repository_id}/graph/path", response_model=GraphPathResponse)
async def get_graph_path(
    repository_id: str,
    source_symbol: str = Query(..., description="Source symbol name"),
    target_symbol: str = Query(..., description="Target symbol name"),
    commit_sha: Optional[str] = Query(None, description="Optional target commit SHA"),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Find shortest directed execution path between two symbols."""
    path_result = await RepositoryService.compute_graph_path(
        session=session,
        repository_id=repository_id,
        source_symbol=source_symbol,
        target_symbol=target_symbol,
        user=current_user,
        commit_sha=commit_sha,
    )
    return GraphPathResponse(
        source_node_id=path_result.source_node_id,
        target_node_id=path_result.target_node_id,
        path_exists=path_result.path_exists,
        path_length=path_result.path_length,
        call_chain=path_result.call_chain,
        nodes=[
            {
                "node_id": n.node_id,
                "name": n.name,
                "node_type": n.node_type,
                "file_path": n.file_path,
                "qualified_name": n.qualified_name,
            }
            for n in path_result.nodes
        ],
    )


@router.post("/{repository_id}/search", response_model=SearchResponse)
async def search_repository(
    repository_id: str,
    request: SearchRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """Execute multi-tenant hybrid lexical & dense vector search over repository code chunks."""
    result = await RepositoryService.search_repository(
        session=session,
        repository_id=repository_id,
        query=request.query,
        user=current_user,
        mode=request.mode,
        top_k=request.top_k,
        rerank=request.rerank,
        symbol_type=request.symbol_type,
        file_pattern=request.file_pattern,
    )
    return SearchResponse.model_validate(result)
