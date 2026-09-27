import pytest
from packages.rag.context import ContextAssembler
from packages.rag.models import QueryAnalysis, QueryIntent
from packages.retrieval.models import ScoredChunkDTO


def test_context_assembler_deduplication():
    assembler = ContextAssembler(token_budget=4000)
    analysis = QueryAnalysis(raw_query="payment logic", intent=QueryIntent.FACTUAL_CODE)

    # Two overlapping chunks from same file: lines 10-50 and lines 15-45
    candidates = [
        ScoredChunkDTO(
            chunk_id="c1",
            file_path="src/billing.py",
            symbol_name="process_payment",
            symbol_type="FUNCTION",
            start_line=10,
            end_line=50,
            content="def process_payment():\n    pass",
            score=0.9,
            lexical_score=1.5,
            vector_score=0.88,
        ),
        ScoredChunkDTO(
            chunk_id="c2",
            file_path="src/billing.py",
            symbol_name="process_payment_inner",
            symbol_type="FUNCTION",
            start_line=15,
            end_line=45,
            content="    # inner block\n    pass",
            score=0.85,
            lexical_score=1.2,
            vector_score=0.82,
        ),
        ScoredChunkDTO(
            chunk_id="c3",
            file_path="src/models.py",
            symbol_name="Invoice",
            symbol_type="CLASS",
            start_line=1,
            end_line=20,
            content="class Invoice:\n    pass",
            score=0.75,
            lexical_score=1.0,
            vector_score=0.78,
        ),
    ]

    pack = assembler.assemble_context(analysis, candidates)

    # c2 was discarded due to overlap with higher-scoring c1
    assert len(pack.chunks) == 2
    assert pack.chunks[0].chunk_id == "c1"
    assert pack.chunks[1].chunk_id == "c3"
    assert pack.evidence.selected_count == 2
    assert pack.evidence.discarded_count == 1
    assert len(pack.evidence.bm25_scores) == 3
    assert len(pack.evidence.vector_scores) == 3


def test_context_assembler_token_budget_cap():
    # Set a tiny token budget (e.g. 15 tokens ~ 60 characters)
    assembler = ContextAssembler(token_budget=15)
    analysis = QueryAnalysis(raw_query="test", intent=QueryIntent.FACTUAL_CODE)

    candidates = [
        ScoredChunkDTO(
            chunk_id="c1",
            file_path="src/a.py",
            content="short line",  # ~2 tokens
            start_line=1,
            end_line=2,
            score=0.9,
        ),
        ScoredChunkDTO(
            chunk_id="c2",
            file_path="src/b.py",
            content="another short line",  # ~4 tokens
            start_line=1,
            end_line=2,
            score=0.8,
        ),
        ScoredChunkDTO(
            chunk_id="c3",
            file_path="src/c.py",
            content="A" * 200,  # 50 tokens (exceeds budget)
            start_line=1,
            end_line=10,
            score=0.7,
        ),
    ]

    pack = assembler.assemble_context(analysis, candidates)
    assert len(pack.chunks) == 2
    assert pack.total_tokens <= 15
    assert pack.evidence.discarded_count >= 1


def test_graph_context_injection_for_dependency_queries():
    assembler = ContextAssembler(token_budget=4000)
    analysis = QueryAnalysis(raw_query="What calls calculate_tax?", intent=QueryIntent.DEPENDENCY)

    graph_context = [
        {
            "id": "edge-01",
            "file_path": "graph/dependency",
            "symbol_name": "calculate_tax",
            "description": "Call relationship: OrderService -> calculate_tax (Type: CALL)",
            "start_line": 1,
            "end_line": 1,
        }
    ]

    candidates = [
        ScoredChunkDTO(
            chunk_id="c1",
            file_path="src/tax.py",
            symbol_name="calculate_tax",
            content="def calculate_tax():\n    return 0.1",
            start_line=1,
            end_line=5,
            score=0.9,
        )
    ]

    pack = assembler.assemble_context(analysis, candidates, graph_context=graph_context)
    # Both the graph item and the code chunk are included
    sources = [ch.source for ch in pack.chunks]
    assert "graph" in sources
    assert "hybrid" in sources
