import uuid
from typing import Optional, Dict, Any, List
from sqlalchemy import String, Integer, Float, Text, ForeignKey, Index, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base, TimestampMixin


class PullRequest(Base, TimestampMixin):
    """Pull request tracked for AI impact and security review."""
    __tablename__ = "pull_requests"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    repository_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    github_pr_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    source_branch: Mapped[str] = mapped_column(String(255), nullable=False)
    target_branch: Mapped[str] = mapped_column(String(255), nullable=False)
    base_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    head_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="OPEN", nullable=False)

    repository: Mapped["Repository"] = relationship("Repository", back_populates="pull_requests")
    analyses: Mapped[List["PullRequestAnalysis"]] = relationship(
        "PullRequestAnalysis", back_populates="pull_request", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_pr_repo_number_unique", "repository_id", "github_pr_number", unique=True),
    )


class PullRequestAnalysis(Base, TimestampMixin):
    """In-depth multi-dimensional AI and graph PR analysis results."""
    __tablename__ = "pull_request_analyses"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    pull_request_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("pull_requests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    head_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    risk_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    changed_files_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    affected_components_json: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    security_findings_json: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    test_gap_analysis_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    ai_review_markdown: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    pull_request: Mapped["PullRequest"] = relationship("PullRequest", back_populates="analyses")
