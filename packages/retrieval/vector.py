import logging
import math
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from packages.ai.base import EmbeddingProvider
from .models import ScoredChunkDTO

logger = logging.getLogger("codeatlas.retrieval.vector")


class VectorIndex:
    """Dense vector search engine managing embeddings and Qdrant index with repository isolation."""

    COLLECTION_NAME = "codeatlas_chunks"

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        qdrant_url: str = "http://localhost:6333",
        qdrant_api_key: Optional[str] = None,
        prefer_memory_fallback: bool = False,
    ):
        self.embedding_provider = embedding_provider
        self.prefer_memory_fallback = prefer_memory_fallback
        self.qdrant_client: Optional[QdrantClient] = None
        self._in_memory_points: List[Dict[str, Any]] = []

        if not prefer_memory_fallback:
            try:
                clean_key = qdrant_api_key if qdrant_api_key and str(qdrant_api_key).strip() else None
                self.qdrant_client = QdrantClient(url=qdrant_url, api_key=clean_key, timeout=0.5)
                # Test connectivity
                self.qdrant_client.get_collections()
                self._ensure_collection_exists()
            except Exception as e:
                logger.warning(f"Could not connect to Qdrant at {qdrant_url}: {e}. Falling back to in-memory vector index.")
                self.qdrant_client = None

    def _ensure_collection_exists(self) -> None:
        """Create the codeatlas_chunks collection if it does not already exist."""
        if not self.qdrant_client:
            return

        try:
            collections = self.qdrant_client.get_collections().collections
            exists = any(c.name == self.COLLECTION_NAME for c in collections)
            if not exists:
                self.qdrant_client.create_collection(
                    collection_name=self.COLLECTION_NAME,
                    vectors_config=qmodels.VectorParams(
                        size=self.embedding_provider.dimension,
                        distance=qmodels.Distance.COSINE,
                    ),
                )
                logger.info(f"Created Qdrant collection '{self.COLLECTION_NAME}' (dim={self.embedding_provider.dimension})")
        except Exception as e:
            logger.warning(f"Failed to ensure Qdrant collection exists: {e}")

    async def upsert_chunks(
        self,
        repository_id: str,
        commit_sha: str,
        chunks: List[Dict[str, Any]],
    ) -> int:
        """Embed and upsert a batch of code chunks into Qdrant."""
        if not chunks:
            return 0

        texts = [c.get("content", "") for c in chunks]
        embeddings = await self.embedding_provider.embed_documents(texts)

        points = []
        for idx, chunk in enumerate(chunks):
            vector = embeddings[idx]
            payload = {
                "repository_id": repository_id,
                "commit_sha": commit_sha,
                "chunk_id": chunk["id"],
                "file_id": chunk.get("file_id", ""),
                "file_path": chunk.get("file_path", ""),
                "symbol_name": chunk.get("symbol_name"),
                "symbol_type": chunk.get("symbol_type"),
                "start_line": chunk.get("start_line", 1),
                "end_line": chunk.get("end_line", 1),
                "content": chunk.get("content", ""),
                "content_hash": chunk.get("content_hash", ""),
                "metadata": chunk.get("metadata", {}),
            }

            points.append({
                "id": chunk["id"],
                "vector": vector,
                "payload": payload,
            })

            # Also maintain in-memory representation for fallback
            self._in_memory_points.append({
                "id": chunk["id"],
                "vector": vector,
                "payload": payload,
            })

        if self.qdrant_client:
            try:
                q_points = [
                    qmodels.PointStruct(
                        id=p["id"],
                        vector=p["vector"],
                        payload=p["payload"],
                    )
                    for p in points
                ]
                self.qdrant_client.upsert(
                    collection_name=self.COLLECTION_NAME,
                    points=q_points,
                )
                logger.info(f"Upserted {len(q_points)} chunk vectors into Qdrant.")
            except Exception as e:
                logger.warning(f"Qdrant upsert failed ({e}), using in-memory vector storage.")

        return len(points)

    async def delete_by_repository(
        self,
        repository_id: str,
        commit_sha: Optional[str] = None,
    ) -> int:
        """Purge indexed vectors for a repository (and optional commit) to prevent stale/cross-commit leaks."""
        deleted_count = 0
        if self.qdrant_client:
            try:
                filter_conditions = [
                    qmodels.FieldCondition(
                        key="repository_id",
                        match=qmodels.MatchValue(value=repository_id),
                    )
                ]
                if commit_sha:
                    filter_conditions.append(
                        qmodels.FieldCondition(
                            key="commit_sha",
                            match=qmodels.MatchValue(value=commit_sha),
                        )
                    )
                del_filter = qmodels.Filter(must=filter_conditions)
                self.qdrant_client.delete(
                    collection_name=self.COLLECTION_NAME,
                    points_selector=qmodels.FilterSelector(filter=del_filter),
                )
                logger.info(f"Purged vectors from Qdrant for repository_id={repository_id}, commit_sha={commit_sha}")
            except Exception as e:
                logger.warning(f"Failed to purge Qdrant vectors for repository_id={repository_id}: {e}")

        # In-memory points cleanup
        prev_len = len(self._in_memory_points)
        self._in_memory_points = [
            p for p in self._in_memory_points
            if not (
                p.get("payload", {}).get("repository_id") == repository_id
                and (commit_sha is None or p.get("payload", {}).get("commit_sha") == commit_sha)
            )
        ]
        deleted_count = prev_len - len(self._in_memory_points)
        return deleted_count

    async def search(
        self,
        repository_id: str,
        query: str,
        top_k: int = 20,
        commit_sha: Optional[str] = None,
    ) -> List[ScoredChunkDTO]:
        """Perform semantic vector similarity search scoped strictly to repository_id."""
        if not query.strip():
            return []

        query_vector = await self.embedding_provider.embed_query(query)

        # Try Qdrant search first
        if self.qdrant_client:
            try:
                filter_conditions = [
                    qmodels.FieldCondition(
                        key="repository_id",
                        match=qmodels.MatchValue(value=repository_id),
                    )
                ]
                if commit_sha:
                    filter_conditions.append(
                        qmodels.FieldCondition(
                            key="commit_sha",
                            match=qmodels.MatchValue(value=commit_sha),
                        )
                    )

                search_filter = qmodels.Filter(must=filter_conditions)

                if hasattr(self.qdrant_client, "query_points"):
                    query_resp = self.qdrant_client.query_points(
                        collection_name=self.COLLECTION_NAME,
                        query=query_vector,
                        query_filter=search_filter,
                        limit=top_k,
                    )
                    q_results = query_resp.points
                else:
                    q_results = self.qdrant_client.search(
                        collection_name=self.COLLECTION_NAME,
                        query_vector=query_vector,
                        query_filter=search_filter,
                        limit=top_k,
                    )

                results: List[ScoredChunkDTO] = []
                for hit in q_results:
                    p = hit.payload or {}
                    results.append(
                        ScoredChunkDTO(
                            chunk_id=p.get("chunk_id", str(hit.id)),
                            repository_id=p.get("repository_id", repository_id),
                            file_id=p.get("file_id", ""),
                            file_path=p.get("file_path", ""),
                            start_line=p.get("start_line", 1),
                            end_line=p.get("end_line", 1),
                            symbol_name=p.get("symbol_name"),
                            symbol_type=p.get("symbol_type"),
                            content=p.get("content", ""),
                            score=float(hit.score),
                            vector_score=float(hit.score),
                            metadata=p.get("metadata", {}),
                        )
                    )
                return results
            except Exception as e:
                logger.warning(f"Qdrant search error ({e}), falling back to in-memory cosine similarity.")

        # In-memory cosine similarity fallback
        return self._search_in_memory(repository_id, query_vector, top_k, commit_sha)

    def _search_in_memory(
        self,
        repository_id: str,
        query_vector: List[float],
        top_k: int,
        commit_sha: Optional[str] = None,
    ) -> List[ScoredChunkDTO]:
        """Compute cosine similarity over cached in-memory points with tenant filtering."""
        filtered_points = [
            pt for pt in self._in_memory_points
            if pt.get("payload", {}).get("repository_id") == repository_id
            and (commit_sha is None or pt.get("payload", {}).get("commit_sha") == commit_sha)
        ]

        if not filtered_points:
            return []

        try:
            import numpy as np
            vectors_mat = np.array([pt["vector"] for pt in filtered_points], dtype=np.float32)
            q_vec = np.array(query_vector, dtype=np.float32)
            sims = vectors_mat.dot(q_vec)
            actual_k = min(top_k, len(filtered_points))
            top_indices = np.argpartition(sims, -actual_k)[-actual_k:]
            top_indices = top_indices[np.argsort(-sims[top_indices])]
            scored_candidates = [(filtered_points[i], float(sims[i])) for i in top_indices]
        except Exception:
            scored = []
            for pt in filtered_points:
                sim = self._cosine_similarity(query_vector, pt["vector"])
                scored.append((pt, sim))
            scored.sort(key=lambda x: x[1], reverse=True)
            scored_candidates = scored[:top_k]

        results: List[ScoredChunkDTO] = []
        for pt, score in scored_candidates:
            p = pt["payload"]
            results.append(
                ScoredChunkDTO(
                    chunk_id=p.get("chunk_id", pt["id"]),
                    repository_id=p.get("repository_id", repository_id),
                    file_id=p.get("file_id", ""),
                    file_path=p.get("file_path", ""),
                    start_line=p.get("start_line", 1),
                    end_line=p.get("end_line", 1),
                    symbol_name=p.get("symbol_name"),
                    symbol_type=p.get("symbol_type"),
                    content=p.get("content", ""),
                    score=float(score),
                    vector_score=float(score),
                    metadata=p.get("metadata", {}),
                )
            )

        return results

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between two float vectors."""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)
