import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import String, Boolean, Integer, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base, TimestampMixin


class Repository(Base, TimestampMixin):
    """Git repository managed within CodeAtlas."""
    __tablename__ = "repositories"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    owner_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    github_url: Mapped[str] = mapped_column(String(512), nullable=False)
    default_branch: Mapped[str] = mapped_column(String(100), default="main", nullable=False)
    is_private: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_indexed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    current_commit_sha: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    index_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False)

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="repositories")
    branches: Mapped[List["RepositoryBranch"]] = relationship(
        "RepositoryBranch", back_populates="repository", cascade="all, delete-orphan"
    )
    commits: Mapped[List["RepositoryCommit"]] = relationship(
        "RepositoryCommit", back_populates="repository", cascade="all, delete-orphan"
    )
    files: Mapped[List["RepositoryFile"]] = relationship(
        "RepositoryFile", back_populates="repository", cascade="all, delete-orphan"
    )
    chunks: Mapped[List["CodeChunk"]] = relationship(
        "CodeChunk", back_populates="repository", cascade="all, delete-orphan"
    )
    index_jobs: Mapped[List["IndexJob"]] = relationship(
        "IndexJob", back_populates="repository", cascade="all, delete-orphan"
    )
    graph_nodes: Mapped[List["GraphNode"]] = relationship(
        "GraphNode", back_populates="repository", cascade="all, delete-orphan"
    )
    graph_edges: Mapped[List["GraphEdge"]] = relationship(
        "GraphEdge", back_populates="repository", cascade="all, delete-orphan"
    )
    conversations: Mapped[List["Conversation"]] = relationship(
        "Conversation", back_populates="repository", cascade="all, delete-orphan"
    )
    pull_requests: Mapped[List["PullRequest"]] = relationship(
        "PullRequest", back_populates="repository", cascade="all, delete-orphan"
    )
    security_findings: Mapped[List["SecurityFinding"]] = relationship(
        "SecurityFinding", back_populates="repository", cascade="all, delete-orphan"
    )
    documentation_artifacts: Mapped[List["DocumentationArtifact"]] = relationship(
        "DocumentationArtifact", back_populates="repository", cascade="all, delete-orphan"
    )


class RepositoryBranch(Base):
    """Git branch state."""
    __tablename__ = "repository_branches"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    repository_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    commit_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    repository: Mapped["Repository"] = relationship("Repository", back_populates="branches")

    __table_args__ = (
        Index("ix_repo_branch_unique", "repository_id", "name", unique=True),
    )


class RepositoryCommit(Base):
    """Git commit ledger entry."""
    __tablename__ = "repository_commits"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    repository_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sha: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    message: Mapped[str] = mapped_column(String(2048), nullable=False)
    author_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    author_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    committed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    repository: Mapped["Repository"] = relationship("Repository", back_populates="commits")

    __table_args__ = (
        Index("ix_repo_commit_unique", "repository_id", "sha", unique=True),
    )
