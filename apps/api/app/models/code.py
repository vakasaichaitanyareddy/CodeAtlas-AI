import uuid
from typing import List, Optional
from sqlalchemy import String, Boolean, Integer, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base


class RepositoryFile(Base):
    """File inventory per indexed commit."""
    __tablename__ = "repository_files"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    repository_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    commit_sha: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    path: Mapped[str] = mapped_column(String(1024), nullable=False, index=True)
    language: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    loc: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    repository: Mapped["Repository"] = relationship("Repository", back_populates="files")
    symbols: Mapped[List["CodeSymbol"]] = relationship(
        "CodeSymbol", back_populates="file", cascade="all, delete-orphan"
    )
    chunks: Mapped[List["CodeChunk"]] = relationship(
        "CodeChunk", back_populates="file", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_repo_file_commit_path", "repository_id", "commit_sha", "path", unique=True),
    )


class CodeSymbol(Base):
    """Syntactic AST symbol extracted during file parsing (classes, functions, methods, imports)."""
    __tablename__ = "code_symbols"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    file_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("repository_files.id", ondelete="CASCADE"), nullable=False, index=True
    )
    repository_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    commit_sha: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    qualified_name: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    symbol_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_symbol_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("code_symbols.id", ondelete="SET NULL"), nullable=True
    )
    docstring: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    signature: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    file: Mapped["RepositoryFile"] = relationship("RepositoryFile", back_populates="symbols")
    chunks: Mapped[List["CodeChunk"]] = relationship("CodeChunk", back_populates="symbol")


class CodeChunk(Base):
    """AST-aware code chunk stored for BM25 and vector indexing."""
    __tablename__ = "code_chunks"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    repository_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    file_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("repository_files.id", ondelete="CASCADE"), nullable=False, index=True
    )
    symbol_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("code_symbols.id", ondelete="SET NULL"), nullable=True
    )
    commit_sha: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    qdrant_point_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)

    repository: Mapped["Repository"] = relationship("Repository", back_populates="chunks")
    file: Mapped["RepositoryFile"] = relationship("RepositoryFile", back_populates="chunks")
    symbol: Mapped[Optional["CodeSymbol"]] = relationship("CodeSymbol", back_populates="chunks")

    __table_args__ = (
        Index("ix_chunk_repo_commit", "repository_id", "commit_sha"),
    )
