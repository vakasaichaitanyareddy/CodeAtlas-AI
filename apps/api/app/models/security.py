import uuid
from typing import Optional
from sqlalchemy import String, Integer, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base, TimestampMixin


class SecurityFinding(Base, TimestampMixin):
    """Static security finding (secret, injection, crypto vulnerability)."""
    __tablename__ = "security_findings"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    repository_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    commit_sha: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # CRITICAL, HIGH, MEDIUM, LOW
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # SECRET, SQL_INJECTION, etc.
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    masked_evidence: Mapped[str] = mapped_column(Text, nullable=False)  # Never unmasked!
    remediation_advice: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", nullable=False)  # ACTIVE, RESOLVED, IGNORED

    repository: Mapped["Repository"] = relationship("Repository", back_populates="security_findings")

    __table_args__ = (
        Index("ix_sec_repo_severity", "repository_id", "severity"),
    )
