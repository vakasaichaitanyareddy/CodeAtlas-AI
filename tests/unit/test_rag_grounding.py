import pytest
from unittest.mock import AsyncMock
from packages.rag.models import (
    GroundingStatus,
    CitationValidationResult,
    ContextPack,
    ContextChunk,
    QueryAnalysis,
    QueryIntent,
    RetrievalEvidence,
)
from packages.rag.citations import CitationVerifier
from packages.rag.engine import RAGEngine, INSUFFICIENT_EVIDENCE_MESSAGE
from packages.retrieval.models import ScoredChunkDTO, SearchResultDTO


def test_grounding_status_computation():
    verifier = CitationVerifier()
    context = ContextPack(
        query="test query",
        analysis=QueryAnalysis(raw_query="test", intent=QueryIntent.FACTUAL_CODE),
        chunks=[
            ContextChunk(
                chunk_id="c1",
                file_path="src/a.py",
                start_line=1,
                end_line=10,
                content="test",
                score=0.9,
            )
        ],
        evidence=RetrievalEvidence(evidence_threshold_met=True),
    )

    # 1. VERIFIED: all citations valid
    cit_valid = [
        CitationValidationResult(
            raw_citation="[src/a.py:L1-L10]",
            file_path="src/a.py",
            start_line=1,
            end_line=10,
            file_exists=True,
            lines_in_bounds=True,
            overlaps_context=True,
            symbol_matches=True,
            confidence=1.0,
            validation_reason="ok",
            is_valid=True,
        )
    ]
    assert verifier.compute_grounding_status(cit_valid, context, "Here is code") == GroundingStatus.VERIFIED

    # 2. PARTIALLY_VERIFIED: 1 valid, 1 invalid
    cit_mixed = [
        cit_valid[0],
        CitationValidationResult(
            raw_citation="[src/b.py:L1-L10]",
            file_path="src/b.py",
            start_line=1,
            end_line=10,
            file_exists=False,
            lines_in_bounds=False,
            overlaps_context=False,
            symbol_matches=False,
            confidence=0.0,
            validation_reason="no file",
            is_valid=False,
        ),
    ]
    assert verifier.compute_grounding_status(cit_mixed, context, "Here is code") == GroundingStatus.PARTIALLY_VERIFIED

    # 3. UNSUPPORTED: all citations invalid
    assert verifier.compute_grounding_status([cit_mixed[1]], context, "Here is code") == GroundingStatus.UNSUPPORTED

    # 4. UNSUPPORTED: evidence threshold not met
    context_failed = ContextPack(
        query="test query",
        analysis=QueryAnalysis(raw_query="test", intent=QueryIntent.FACTUAL_CODE),
        chunks=[],
        evidence=RetrievalEvidence(evidence_threshold_met=False),
    )
    assert verifier.compute_grounding_status([], context_failed, "answer") == GroundingStatus.UNSUPPORTED


@pytest.mark.asyncio
async def test_hard_insufficient_evidence_fallback():
    """Verify that when context evidence is insufficient, RAGEngine triggers controlled fallback."""
    mock_llm = AsyncMock()
    mock_search = AsyncMock()

    # Search returns empty results
    mock_search.search.return_value = SearchResultDTO(
        query="something obscure",
        mode="hybrid",
        total_candidates=0,
        execution_time_ms=5,
        results=[],
    )

    engine = RAGEngine(
        llm_provider=mock_llm,
        hybrid_search_service=mock_search,
    )

    answer = await engine.generate_answer(
        query="Where is the non_existent_secret_key defined?",
        repository_id="repo-123",
    )

    # 1. Returned message matches mandatory controlled text
    assert answer.answer == INSUFFICIENT_EVIDENCE_MESSAGE
    # 2. Status is UNSUPPORTED
    assert answer.grounding_status == GroundingStatus.UNSUPPORTED
    # 3. No citations were fabricated
    assert len(answer.citations) == 0
    # 4. LLM was NOT invoked, preventing hallucination
    mock_llm.generate.assert_not_called()
    mock_llm.stream.assert_not_called()
    # 5. Retrieval evidence records threshold failure
    assert answer.retrieval_evidence.evidence_threshold_met is False


@pytest.mark.asyncio
async def test_relevance_score_threshold_fallback():
    """Verify that low-scoring candidates trigger threshold fallback."""
    mock_llm = AsyncMock()
    mock_search = AsyncMock()

    # Return low score below min_relevance_score
    mock_search.search.return_value = SearchResultDTO(
        query="auth",
        mode="hybrid",
        total_candidates=1,
        execution_time_ms=5,
        results=[
            ScoredChunkDTO(
                chunk_id="ch-low",
                file_path="src/irrelevant.py",
                content="x = 1",
                start_line=1,
                end_line=2,
                score=0.001,  # below 0.015 default threshold
            )
        ],
    )

    engine = RAGEngine(
        llm_provider=mock_llm,
        hybrid_search_service=mock_search,
    )

    answer = await engine.generate_answer(
        query="auth logic",
        repository_id="repo-123",
    )

    assert answer.answer == INSUFFICIENT_EVIDENCE_MESSAGE
    assert answer.grounding_status == GroundingStatus.UNSUPPORTED
    mock_llm.generate.assert_not_called()
    assert "below_minimum" in answer.retrieval_evidence.threshold_reason
