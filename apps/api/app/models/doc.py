import uuid
from sqlalchemy import String, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base, TimestampMixin


class DocumentationArtifact(Base, TimestampMixin):
    """Automatically synthesized codebase documentation artifact."""
    __tablename__ = "documentation_artifacts"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    repository_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    commit_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content_markdown: Mapped[str] = mapped_column(Text, nullable=False)

    repository: Mapped["Repository"] = relationship("Repository", back_populates="documentation_artifacts")

    __table_args__ = (
        Index("ix_doc_repo_type", "repository_id", "doc_type"),
    )
