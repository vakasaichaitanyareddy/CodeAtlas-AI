from packages.retrieval.fusion import ReciprocalRankFusion
from packages.retrieval.models import ScoredChunkDTO


def test_reciprocal_rank_fusion_merging():
    # Chunk A: rank 1 in lexical, rank 2 in vector
    # Chunk B: rank 2 in lexical, not in vector
    # Chunk C: not in lexical, rank 1 in vector

    lexical_results = [
        ScoredChunkDTO(
            chunk_id="chunk-A",
            repository_id="repo-1",
            file_id="f-1",
            file_path="auth.py",
            start_line=1,
            end_line=10,
            content="token auth",
            score=5.5,
        ),
        ScoredChunkDTO(
            chunk_id="chunk-B",
            repository_id="repo-1",
            file_id="f-1",
            file_path="auth.py",
            start_line=11,
            end_line=20,
            content="refresh auth",
            score=4.0,
        ),
    ]

    vector_results = [
        ScoredChunkDTO(
            chunk_id="chunk-C",
            repository_id="repo-1",
            file_id="f-2",
            file_path="security.py",
            start_line=1,
            end_line=10,
            content="crypto verify",
            score=0.92,
        ),
        ScoredChunkDTO(
            chunk_id="chunk-A",
            repository_id="repo-1",
            file_id="f-1",
            file_path="auth.py",
            start_line=1,
            end_line=10,
            content="token auth",
            score=0.88,
        ),
    ]

    fusion = ReciprocalRankFusion(k=60)
    fused = fusion.fuse(lexical_results, vector_results, top_k=5)

    assert len(fused) == 3
    # Chunk A has 1/(60+1) + 1/(60+2) = 1/61 + 1/62 ≈ 0.01639 + 0.01613 = 0.03252
    # Chunk C has 1/(60+1) = 1/61 ≈ 0.01639
    # Chunk B has 1/(60+2) = 1/62 ≈ 0.01613
    assert fused[0].chunk_id == "chunk-A"
    assert fused[0].lexical_score == 5.5
    assert fused[0].vector_score == 0.88
    assert fused[0].rrf_score is not None

    # Chunk C is rank 2, Chunk B is rank 3
    assert fused[1].chunk_id == "chunk-C"
    assert fused[2].chunk_id == "chunk-B"
