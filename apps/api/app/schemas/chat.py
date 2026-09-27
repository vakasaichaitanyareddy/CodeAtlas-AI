from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Payload for submitting a codebase question to the RAG engine."""
    message: str = Field(..., min_length=1, max_length=4000, description="User question or prompt")
    conversation_id: Optional[str] = Field(None, description="Existing conversation ID to continue thread")
    mode: str = Field("hybrid", description="Search mode: hybrid, lexical, semantic")
    stream: bool = Field(False, description="Enable Server-Sent Events (SSE) token streaming")
    commit_sha: Optional[str] = Field(None, description="Commit SHA to ground against")
    top_k: int = Field(10, ge=1, le=50, description="Maximum number of context chunks to retrieve")
    rerank: bool = Field(True, description="Enable neural cross-encoder candidate reranking")


class CitationDTO(BaseModel):
    """Verified citation referencing repository code."""
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


class ContextChunkDTO(BaseModel):
    """Code chunk used as context in the prompt."""
    chunk_id: str
    file_path: str
    symbol_name: Optional[str] = None
    symbol_type: Optional[str] = None
    start_line: int
    end_line: int
    content: str
    score: float
    source: str = "hybrid"


class RetrievalEvidenceDTO(BaseModel):
    """Retrieval metadata explaining context selection and evidence decisions."""
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


class ChatMessageResponse(BaseModel):
    """A single message in a conversation thread."""
    id: str
    conversation_id: str
    role: str
    content: str
    grounding_status: Optional[str] = None
    intent: Optional[str] = None
    citations: List[CitationDTO] = Field(default_factory=list)
    context_chunks: List[ContextChunkDTO] = Field(default_factory=list)
    retrieval_evidence: Optional[RetrievalEvidenceDTO] = None
    provider: Optional[str] = None
    is_mock: bool = False
    tokens_used: Optional[int] = None
    latency_ms: Optional[int] = None
    created_at: str


class ConversationSummary(BaseModel):
    """Summary of a chat session."""
    id: str
    repository_id: str
    title: str
    commit_sha: Optional[str] = None
    message_count: int = 0
    created_at: str
    updated_at: Optional[str] = None


class ConversationDetail(BaseModel):
    """Full detail of a conversation thread including all messages."""
    id: str
    repository_id: str
    title: str
    commit_sha: Optional[str] = None
    created_at: str
    messages: List[ChatMessageResponse] = Field(default_factory=list)
