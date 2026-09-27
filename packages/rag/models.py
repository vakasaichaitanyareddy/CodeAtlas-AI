from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class QueryIntent(str, Enum):
    """Categorized intent of a codebase query."""
    FACTUAL_CODE = "FACTUAL_CODE"        # Locating specific functions, classes, implementations
    ARCHITECTURE = "ARCHITECTURE"        # High-level system design, flow, component interactions
    DEPENDENCY = "DEPENDENCY"            # Callers, callees, import relationships
    IMPACT = "IMPACT"                    # Blast radius, downstream consequences of modifying code
    DOCUMENTATION = "DOCUMENTATION"      # Setup, deployment, README instructions
    GENERAL_QA = "GENERAL_QA"            # General software engineering / codebase question


class GroundingStatus(str, Enum):
    """Grounding status of the emitted answer."""
    VERIFIED = "VERIFIED"                # All claims and citations are supported by verified repository evidence
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"  # Some evidence supported, but one or more claims/citations unverified
    UNSUPPORTED = "UNSUPPORTED"          # Insufficient verified evidence to answer the question reliably


class QueryAnalysis(BaseModel):
    """Structured analysis and extracted entities from a user query."""
    raw_query: str
    intent: QueryIntent
    target_symbols: List[str] = Field(default_factory=list)
    file_patterns: List[str] = Field(default_factory=list)
    expanded_terms: List[str] = Field(default_factory=list)
    confidence: float = 1.0


class ContextChunk(BaseModel):
    """Single code chunk selected as evidence for prompt context."""
    chunk_id: str
    file_path: str
    symbol_name: Optional[str] = None
    symbol_type: Optional[str] = None
    start_line: int
    end_line: int
    content: str
    score: float
    source: str = "hybrid"  # "lexical", "vector", "hybrid", "graph"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RetrievalEvidence(BaseModel):
    """Telemetry detailing why context was selected or discarded."""
    candidate_count: int = 0
    selected_count: int = 0
    discarded_count: int = 0
    bm25_scores: List[float] = Field(default_factory=list)
    vector_scores: List[float] = Field(default_factory=list)
    rrf_scores: List[float] = Field(default_factory=list)
    reranker_scores: List[float] = Field(default_factory=list)
    context_tokens: int = 0
    evidence_threshold_met: bool = True
    threshold_reason: str = "sufficient_evidence"


class ContextPack(BaseModel):
    """Assembled and token-budgeted context ready for prompt injection."""
    query: str
    analysis: QueryAnalysis
    chunks: List[ContextChunk] = Field(default_factory=list)
    total_tokens: int = 0
    token_budget: int = 4000
    evidence: RetrievalEvidence = Field(default_factory=RetrievalEvidence)


class CitationValidationResult(BaseModel):
    """Structured result of validating an individual citation against repository evidence."""
    raw_citation: str
    file_path: str
    start_line: int
    end_line: int
    file_exists: bool
    lines_in_bounds: bool
    overlaps_context: bool
    symbol_matches: bool
    source_chunk_id: Optional[str] = None
    confidence: float
    validation_reason: str
    is_valid: bool


class GenerationResult(BaseModel):
    """Raw generation output before citation validation."""
    answer_text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0


class GroundedAnswer(BaseModel):
    """Complete, citation-validated and grounded answer."""
    answer: str
    grounding_status: GroundingStatus
    intent: QueryIntent
    citations: List[CitationValidationResult] = Field(default_factory=list)
    context_chunks: List[ContextChunk] = Field(default_factory=list)
    retrieval_evidence: RetrievalEvidence = Field(default_factory=RetrievalEvidence)
    provider: Optional[str] = None
    model_name: Optional[str] = None
    is_mock: bool = False
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0
