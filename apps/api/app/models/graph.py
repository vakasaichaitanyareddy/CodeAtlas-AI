import uuid
from typing import Optional, Dict, Any
from sqlalchemy import String, ForeignKey, Index, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base


class GraphNode(Base):
    """Node in the code dependency / architecture graph."""
    __tablename__ = "graph_nodes"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    repository_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    commit_sha: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    node_key: Mapped[str] = mapped_column(String(512), nullable=False)
    node_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    symbol_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("code_symbols.id", ondelete="SET NULL"), nullable=True
    )
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    repository: Mapped["Repository"] = relationship("Repository", back_populates="graph_nodes")

    __table_args__ = (
        Index("ix_graph_node_repo_commit_key", "repository_id", "commit_sha", "node_key", unique=True),
    )


class GraphEdge(Base):
    """Directed edge in the code relationship graph."""
    __tablename__ = "graph_edges"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    repository_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    commit_sha: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_node_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("graph_nodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_node_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("graph_nodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    edge_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    repository: Mapped["Repository"] = relationship("Repository", back_populates="graph_edges")
    source_node: Mapped["GraphNode"] = relationship("GraphNode", foreign_keys=[source_node_id])
    target_node: Mapped["GraphNode"] = relationship("GraphNode", foreign_keys=[target_node_id])

    __table_args__ = (
        Index("ix_graph_edge_source_target_type", "source_node_id", "target_node_id", "edge_type"),
    )
