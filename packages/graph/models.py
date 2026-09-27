from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class CycleType(str, Enum):
    IMPORT_CYCLE = "IMPORT_CYCLE"
    CALL_CYCLE = "CALL_CYCLE"
    MIXED_CYCLE = "MIXED_CYCLE"


class GraphNodeDTO(BaseModel):
    node_id: str
    node_type: str  # FILE, MODULE, CLASS, FUNCTION, METHOD, ENDPOINT, MODEL
    name: str
    qualified_name: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GraphEdgeDTO(BaseModel):
    source_id: str
    target_id: str
    edge_type: str  # IMPORTS, CALLS, INHERITS, IMPLEMENTS, DEPENDS_ON, EXPOSES, QUERIES
    weight: float = 1.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CycleResult(BaseModel):
    cycle_type: CycleType
    nodes: List[str] = Field(default_factory=list)
    cycle_path: List[str] = Field(default_factory=list)
    length: int
    participating_files: List[str] = Field(default_factory=list)
    edge_types: List[str] = Field(default_factory=list)


class GraphMetricsDTO(BaseModel):
    total_nodes: int = 0
    total_edges: int = 0
    in_degree: int = 0
    out_degree: int = 0
    centrality: float = 0.0
    node_type_counts: Dict[str, int] = Field(default_factory=dict)
    edge_type_counts: Dict[str, int] = Field(default_factory=dict)
    cycle_count: int = 0


class SubGraphDTO(BaseModel):
    nodes: List[GraphNodeDTO] = Field(default_factory=list)
    edges: List[GraphEdgeDTO] = Field(default_factory=list)


class ImpactAnalysisResult(BaseModel):
    target_node_id: str
    target_name: str
    impact_score: float  # Normalized 0.0 - 1.0
    severity: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL
    upstream_callers_count: int
    impacted_files_count: int
    affected_endpoints: List[str] = Field(default_factory=list)
    affected_endpoints_details: List[Dict[str, Any]] = Field(default_factory=list)
    impacted_symbols: List[str] = Field(default_factory=list)
    traversal_depth: int
    score_breakdown: Dict[str, float] = Field(default_factory=dict)


class PathAnalysisResult(BaseModel):
    source_node_id: str
    target_node_id: str
    path_exists: bool
    path_length: int
    call_chain: List[str] = Field(default_factory=list)
    nodes: List[GraphNodeDTO] = Field(default_factory=list)
