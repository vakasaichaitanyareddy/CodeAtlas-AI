from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class RepositoryCreateRequest(BaseModel):
    github_url: str = Field(..., description="GitHub HTTPS or SSH repository URL")
    default_branch: Optional[str] = Field(default="main", description="Target git branch to track")
    is_private: bool = Field(default=False, description="Whether repository requires credentials")


class RepositoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_id: str
    name: str
    full_name: str
    github_url: str
    default_branch: str
    is_private: bool
    is_indexed: bool
    current_commit_sha: Optional[str] = None
    index_version: int
    status: str
    created_at: datetime
    updated_at: datetime


class IndexJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    repository_id: str
    commit_sha: str
    status: str
    current_step: Optional[str] = None
    progress_percent: int
    error_message: Optional[str] = None
    stats_json: Optional[Dict[str, Any]] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Search query string")
    mode: str = Field(default="hybrid", description="Search mode: hybrid, lexical, semantic")
    top_k: int = Field(default=10, ge=1, le=50, description="Maximum results to return")
    rerank: bool = Field(default=True, description="Whether to apply cross-encoder reranker")
    symbol_type: Optional[str] = Field(default=None, description="Optional symbol type filter")
    file_pattern: Optional[str] = Field(default=None, description="Optional file path pattern filter")


class SearchHit(BaseModel):
    chunk_id: str
    repository_id: str
    file_id: str
    file_path: str
    start_line: int
    end_line: int
    symbol_name: Optional[str] = None
    symbol_type: Optional[str] = None
    content: str
    score: float
    lexical_score: Optional[float] = None
    vector_score: Optional[float] = None
    rrf_score: Optional[float] = None
    rerank_score: Optional[float] = None


class SearchResponse(BaseModel):
    query: str
    mode: str
    total_candidates: int
    results: list[SearchHit]
    execution_time_ms: float


# --- Milestone 5: Graph Engine Schemas ---

class GraphNodeResponse(BaseModel):
    id: str
    node_key: str
    node_type: str
    name: str
    file_path: Optional[str] = None
    in_degree: Optional[int] = None
    out_degree: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GraphEdgeResponse(BaseModel):
    id: Optional[str] = None
    source: str
    target: str
    edge_type: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GraphTopologyResponse(BaseModel):
    repository_id: str
    commit_sha: Optional[str] = None
    nodes: List[GraphNodeResponse]
    edges: List[GraphEdgeResponse]
    nodes_count: int
    edges_count: int
    metrics: Dict[str, Any] = Field(default_factory=dict)


class CircularDependencyCycle(BaseModel):
    cycle_type: str
    nodes: List[str]
    cycle_path: List[str]
    length: int
    participating_files: List[str]
    edge_types: List[str]


class CircularDependencyResponse(BaseModel):
    repository_id: str
    commit_sha: Optional[str] = None
    total_cycles: int
    cycles: List[CircularDependencyCycle]


class GraphNodeDetailResponse(BaseModel):
    node: GraphNodeResponse
    in_degree: int
    out_degree: int
    centrality: float
    incoming_callers: List[GraphNodeResponse]
    outgoing_callees: List[GraphNodeResponse]
    neighborhood_nodes_count: int
    neighborhood_edges_count: int


class GraphImpactResponse(BaseModel):
    target_node_id: str
    target_name: str
    impact_score: float
    severity: str
    upstream_callers_count: int
    impacted_files_count: int
    affected_endpoints: List[str]
    affected_endpoints_details: List[Dict[str, Any]] = Field(default_factory=list)
    impacted_symbols: List[str]
    traversal_depth: int
    score_breakdown: Dict[str, float] = Field(default_factory=dict)


class GraphPathResponse(BaseModel):
    source_node_id: str
    target_node_id: str
    path_exists: bool
    path_length: int
    call_chain: List[str]
    nodes: List[Dict[str, Any]]
