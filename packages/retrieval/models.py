from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class SearchMode(str, Enum):
    HYBRID = "hybrid"
    LEXICAL = "lexical"
    SEMANTIC = "semantic"


class ScoredChunkDTO(BaseModel):
    chunk_id: str
    repository_id: str = ""
    file_id: str = ""
    file_path: str
    start_line: int
    end_line: int
    symbol_name: Optional[str] = None
    symbol_type: Optional[str] = None
    content: str
    score: float = 0.0
    lexical_score: Optional[float] = None
    vector_score: Optional[float] = None
    rrf_score: Optional[float] = None
    rerank_score: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SearchRequestDTO(BaseModel):
    query: str
    mode: SearchMode = SearchMode.HYBRID
    top_k: int = Field(default=10, ge=1, le=50)
    rerank: bool = True
    symbol_type: Optional[str] = None
    file_pattern: Optional[str] = None


class SearchResultDTO(BaseModel):
    query: str
    mode: str
    total_candidates: int
    results: List[ScoredChunkDTO]
    execution_time_ms: float = 0.0
