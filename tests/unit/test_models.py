import pytest
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from apps.api.app.models import (
    User,
    RefreshToken,
    Repository,
    RepositoryBranch,
    RepositoryCommit,
    RepositoryFile,
    CodeSymbol,
    CodeChunk,
    GraphNode,
    GraphEdge,
    IndexJob,
    Conversation,
    Message,
    PullRequest,
    PullRequestAnalysis,
    SecurityFinding,
    DocumentationArtifact,
    AuditLog,
)


@pytest.mark.asyncio
async def test_models_persistence_and_relationships(db_session: AsyncSession):
    # 1. User
    user = User(
        email="test@codeatlas.dev",
        hashed_password="hashed_pw_test",
        full_name="Atlas Engineer",
        role="ADMIN",
    )
    db_session.add(user)
    await db_session.flush()
    assert user.id is not None

    # 2. RefreshToken
    token = RefreshToken(
        user_id=user.id,
        token_hash="hash123",
        expires_at=datetime.now(timezone.utc),
    )
    db_session.add(token)

    # 3. Repository
    repo = Repository(
        owner_id=user.id,
        name="test-repo",
        full_name="codeatlas/test-repo",
        github_url="https://github.com/codeatlas/test-repo",
        default_branch="main",
    )
    db_session.add(repo)
    await db_session.flush()

    # 4. Branch & Commit
    branch = RepositoryBranch(
        repository_id=repo.id,
        name="main",
        commit_sha="a1b2c3d4",
        is_default=True,
    )
    commit = RepositoryCommit(
        repository_id=repo.id,
        sha="a1b2c3d4",
        message="Initial commit",
        committed_at=datetime.now(timezone.utc),
    )
    db_session.add_all([branch, commit])

    # 5. File, Symbol, Chunk
    file = RepositoryFile(
        repository_id=repo.id,
        commit_sha="a1b2c3d4",
        path="src/main.py",
        language="python",
        loc=42,
        size_bytes=1024,
        content_hash="hash_main_py",
    )
    db_session.add(file)
    await db_session.flush()

    symbol = CodeSymbol(
        file_id=file.id,
        repository_id=repo.id,
        commit_sha="a1b2c3d4",
        name="authenticate_user",
        qualified_name="src.main.authenticate_user",
        symbol_type="FUNCTION",
        start_line=10,
        end_line=25,
    )
    db_session.add(symbol)
    await db_session.flush()

    chunk = CodeChunk(
        repository_id=repo.id,
        file_id=file.id,
        symbol_id=symbol.id,
        commit_sha="a1b2c3d4",
        chunk_index=0,
        content="def authenticate_user(): pass",
        content_hash="chunk_hash_1",
        start_line=10,
        end_line=25,
    )
    db_session.add(chunk)

    # 6. Graph Node & Edge
    node1 = GraphNode(
        repository_id=repo.id,
        commit_sha="a1b2c3d4",
        node_key="src/main.py:func1",
        node_type="FUNCTION",
        name="func1",
    )
    node2 = GraphNode(
        repository_id=repo.id,
        commit_sha="a1b2c3d4",
        node_key="src/main.py:func2",
        node_type="FUNCTION",
        name="func2",
    )
    db_session.add_all([node1, node2])
    await db_session.flush()

    edge = GraphEdge(
        repository_id=repo.id,
        commit_sha="a1b2c3d4",
        source_node_id=node1.id,
        target_node_id=node2.id,
        edge_type="CALLS",
    )
    db_session.add(edge)

    # 7. IndexJob
    job = IndexJob(
        repository_id=repo.id,
        commit_sha="a1b2c3d4",
        status="COMPLETED",
        progress_percent=100,
    )
    db_session.add(job)

    # 8. Conversation & Message
    conv = Conversation(
        user_id=user.id,
        repository_id=repo.id,
        title="Architecture Discussion",
    )
    db_session.add(conv)
    await db_session.flush()

    msg = Message(
        conversation_id=conv.id,
        role="USER",
        content="How does auth work?",
    )
    db_session.add(msg)

    # 9. PullRequest & Analysis
    pr = PullRequest(
        repository_id=repo.id,
        github_pr_number=42,
        title="Add payment validation",
        source_branch="feat/payment",
        target_branch="main",
        base_sha="a1b2c3d4",
        head_sha="e5f6g7h8",
    )
    db_session.add(pr)
    await db_session.flush()

    analysis = PullRequestAnalysis(
        pull_request_id=pr.id,
        head_sha="e5f6g7h8",
        summary="Safe PR",
        risk_score=0.15,
    )
    db_session.add(analysis)

    # 10. SecurityFinding
    sec = SecurityFinding(
        repository_id=repo.id,
        commit_sha="a1b2c3d4",
        file_path="src/main.py",
        line_number=12,
        severity="HIGH",
        category="SECRET",
        title="Potential Hardcoded Token",
        description="Found token pattern",
        masked_evidence="ghp_***12",
    )
    db_session.add(sec)

    # 11. DocumentationArtifact
    doc = DocumentationArtifact(
        repository_id=repo.id,
        commit_sha="a1b2c3d4",
        doc_type="ARCHITECTURE",
        title="System Overview",
        content_markdown="# CodeAtlas System",
    )
    db_session.add(doc)

    # 12. AuditLog
    audit = AuditLog(
        user_id=user.id,
        repository_id=repo.id,
        action="REPOSITORY_INDEXED",
        resource_type="repository",
        resource_id=repo.id,
    )
    db_session.add(audit)

    await db_session.commit()

    # Query back to verify persistence
    stmt = select(Repository).where(Repository.id == repo.id)
    res = await db_session.execute(stmt)
    retrieved_repo = res.scalar_one()
    assert retrieved_repo.name == "test-repo"
