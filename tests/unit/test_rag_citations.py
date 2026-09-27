import pytest
from packages.rag.citations import CitationVerifier
from packages.rag.models import (
    ContextPack,
    ContextChunk,
    QueryAnalysis,
    QueryIntent,
    RetrievalEvidence,
)


def _build_test_context_pack() -> ContextPack:
    analysis = QueryAnalysis(
        raw_query="Find auth logic",
        intent=QueryIntent.FACTUAL_CODE,
    )
    chunk1 = ContextChunk(
        chunk_id="chunk-01",
        file_path="src/auth.py",
        symbol_name="verify_token",
        symbol_type="FUNCTION",
        start_line=10,
        end_line=30,
        content="def verify_token(token):\n    pass",
        score=0.95,
    )
    chunk2 = ContextChunk(
        chunk_id="chunk-02",
        file_path="src/utils.py",
        symbol_name="format_date",
        symbol_type="FUNCTION",
        start_line=5,
        end_line=20,
        content="def format_date(d):\n    return str(d)",
        score=0.80,
    )
    return ContextPack(
        query="Find auth logic",
        analysis=analysis,
        chunks=[chunk1, chunk2],
        total_tokens=50,
        token_budget=4000,
        evidence=RetrievalEvidence(evidence_threshold_met=True),
    )


def test_citation_extraction():
    verifier = CitationVerifier()
    text = (
        "Token verification is handled in [src/auth.py:L10-L25]. "
        "Also see helper at [src/utils.py:L15] and [src/config.py#L1-L10]."
    )
    citations = verifier.extract_citations(text)
    assert len(citations) == 3
    assert citations[0] == ("[src/auth.py:L10-L25]", "src/auth.py", 10, 25)
    assert citations[1] == ("[src/utils.py:L15]", "src/utils.py", 15, 15)
    assert citations[2] == ("[src/config.py#L1-L10]", "src/config.py", 1, 10)


def test_citation_validation_scenarios():
    verifier = CitationVerifier()
    context_pack = _build_test_context_pack()

    file_records = {
        "src/auth.py": {
            "loc": 100,
            "symbols": [{"name": "verify_token", "start_line": 10, "end_line": 30}],
        },
        "src/utils.py": {
            "loc": 50,
            "symbols": [{"name": "format_date", "start_line": 5, "end_line": 20}],
        },
        "src/short.py": {
            "loc": 20,
            "symbols": [],
        },
    }

    # Scenario 1: Valid citation matching file, bounds, context, and symbol
    res_valid = verifier.validate_citations(
        [("[src/auth.py:L10-L25]", "src/auth.py", 10, 25)],
        context_pack,
        file_records,
    )
    assert len(res_valid) == 1
    assert res_valid[0].is_valid is True
    assert res_valid[0].file_exists is True
    assert res_valid[0].lines_in_bounds is True
    assert res_valid[0].overlaps_context is True
    assert res_valid[0].symbol_matches is True
    assert res_valid[0].source_chunk_id == "chunk-01"
    assert res_valid[0].confidence == 1.0

    # Scenario 2: Nonexistent file
    res_nofile = verifier.validate_citations(
        [("[src/ghost.py:L1-L10]", "src/ghost.py", 1, 10)],
        context_pack,
        file_records,
    )
    assert len(res_nofile) == 1
    assert res_nofile[0].is_valid is False
    assert res_nofile[0].file_exists is False
    assert res_nofile[0].validation_reason == "file_does_not_exist_in_repository"

    # Scenario 3: Inverted or negative line numbers
    res_inv = verifier.validate_citations(
        [("[src/auth.py:L50-L20]", "src/auth.py", 50, 20)],
        context_pack,
        file_records,
    )
    assert len(res_inv) == 1
    assert res_inv[0].is_valid is False
    assert res_inv[0].lines_in_bounds is False
    assert res_inv[0].validation_reason == "invalid_or_negative_line_range"

    # Scenario 4: Lines beyond physical file length
    res_overflow = verifier.validate_citations(
        [("[src/short.py:L10-L50]", "src/short.py", 10, 50)],
        context_pack,
        file_records,
    )
    assert len(res_overflow) == 1
    assert res_overflow[0].is_valid is False
    assert res_overflow[0].lines_in_bounds is False
    assert "exceeds_physical_loc" in res_overflow[0].validation_reason

    # Scenario 5: File exists and within bounds, but does NOT overlap any retrieved context chunk
    res_nocontext = verifier.validate_citations(
        [("[src/auth.py:L70-L85]", "src/auth.py", 70, 85)],
        context_pack,
        file_records,
    )
    assert len(res_nocontext) == 1
    assert res_nocontext[0].is_valid is False
    assert res_nocontext[0].file_exists is True
    assert res_nocontext[0].lines_in_bounds is True
    assert res_nocontext[0].overlaps_context is False
    assert res_nocontext[0].validation_reason == "citation_not_supported_by_retrieved_context"
