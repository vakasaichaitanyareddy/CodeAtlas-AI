from typing import List, Optional, Any
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.repository import Repository
from ..models.user import User
from ..models.code import RepositoryFile, CodeSymbol, CodeChunk
from ..models.chat import Conversation
from ..models.graph import GraphNode, GraphEdge
from ..models.job import IndexJob
from ..core.errors import APIError


class RepositoryService:
    """Service managing repository persistence and ownership verification."""

    @staticmethod
    async def create_repository(
        session: AsyncSession,
        user: User,
        github_url: str,
        default_branch: str = "main",
        is_private: bool = False,
    ) -> Repository:
        # Extract name and full_name from github_url
        clean_url = github_url.rstrip("/").removesuffix(".git")
        parts = clean_url.split("/")
        if len(parts) >= 2:
            repo_name = parts[-1]
            owner_name = parts[-2]
            full_name = f"{owner_name}/{repo_name}"
        else:
            repo_name = clean_url
            full_name = clean_url

        # Check for duplicate registration by the same owner
        stmt = select(Repository).where(
            Repository.owner_id == user.id,
            Repository.full_name == full_name,
        )
        existing = (await session.execute(stmt)).scalar_one_or_none()
        if existing:
            raise APIError(
                message=f"Repository '{full_name}' is already connected to your account.",
                code="REPOSITORY_ALREADY_EXISTS",
                status_code=409,
            )

        repo = Repository(
            owner_id=user.id,
            name=repo_name,
            full_name=full_name,
            github_url=github_url,
            default_branch=default_branch,
            is_private=is_private,
            is_indexed=False,
            status="PENDING",
        )
        session.add(repo)
        await session.flush()
        return repo

    @staticmethod
    async def list_repositories(
        session: AsyncSession,
        user: User,
    ) -> List[Repository]:
        """List repositories owned by the user (or all if admin)."""
        if user.role == "ADMIN":
            stmt = select(Repository).order_by(Repository.created_at.desc())
        else:
            stmt = select(Repository).where(Repository.owner_id == user.id).order_by(Repository.created_at.desc())

        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_repository_by_id(
        session: AsyncSession,
        repository_id: str,
        user: User,
    ) -> Repository:
        """Fetch repository enforcing multi-tenant ownership boundaries."""
        stmt = select(Repository).where(Repository.id == repository_id)
        result = await session.execute(stmt)
        repo = result.scalar_one_or_none()

        if not repo:
            raise APIError(
                message=f"Repository '{repository_id}' not found.",
                code="REPOSITORY_NOT_FOUND",
                status_code=404,
            )

        # Multi-tenant boundary check
        if repo.owner_id != user.id and user.role != "ADMIN":
            raise APIError(
                message="You do not have permission to access this repository.",
                code="FORBIDDEN_REPOSITORY_ACCESS",
                status_code=403,
            )

        return repo

    @staticmethod
    async def delete_repository(
        session: AsyncSession,
        repository_id: str,
        user: User,
    ) -> None:
        """Delete repository enforcing multi-tenant ownership boundaries."""
        repo = await RepositoryService.get_repository_by_id(session, repository_id, user)
        await session.delete(repo)
        await session.flush()

    @staticmethod
    async def get_repository_files(
        session: AsyncSession,
        repository_id: str,
        user: User,
    ) -> list:
        """Fetch repository files scoped to tenant ownership."""
        repo = await RepositoryService.get_repository_by_id(session, repository_id, user)
        stmt = select(RepositoryFile).where(RepositoryFile.repository_id == repo.id)
        res = await session.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def get_repository_conversations(
        session: AsyncSession,
        repository_id: str,
        user: User,
    ) -> list:
        """Fetch repository conversations scoped to tenant ownership."""
        repo = await RepositoryService.get_repository_by_id(session, repository_id, user)
        stmt = select(Conversation).where(
            Conversation.repository_id == repo.id,
            Conversation.user_id == user.id,
        )
        res = await session.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    def _find_matching_node(node_dtos: list, query: str) -> Optional[Any]:
        """Resolve a query string to the best matching GraphNodeDTO using prioritized matching."""
        if not query:
            return None
        q = query.strip()
        q_norm = q.replace("\\", "/")

        # 1. Exact node_id match
        for n in node_dtos:
            if n.node_id == q:
                return n

        # 2. Exact qualified_name match
        for n in node_dtos:
            if n.qualified_name == q:
                return n

        # 3. Exact name match
        name_matches = [n for n in node_dtos if n.name == q]
        if name_matches:
            name_matches.sort(
                key=lambda n: (
                    1 if (n.file_path or "").startswith("test") else 0,
                    0 if getattr(n, "node_type", "") == "FILE" else 1,
                    len((n.file_path or "").split("/")),
                )
            )
            return name_matches[0]

        # 4. Exact file_path match
        for n in node_dtos:
            if (n.file_path or "").replace("\\", "/") == q_norm:
                return n

        # 5. Suffix match on file_path (e.g. "app.py" matching "src/flask/app.py")
        suffix_matches = [
            n for n in node_dtos
            if (n.file_path or "").replace("\\", "/").endswith("/" + q_norm)
        ]
        if suffix_matches:
            suffix_matches.sort(
                key=lambda n: (
                    1 if (n.file_path or "").startswith("test") else 0,
                    0 if getattr(n, "node_type", "") == "FILE" else 1,
                    len((n.file_path or "").split("/")),
                )
            )
            return suffix_matches[0]

        # 6. Substring in node_id or qualified_name
        for n in node_dtos:
            if q in n.node_id or q in (n.qualified_name or ""):
                return n

        # 7. Case-insensitive name match
        q_lower = q.lower()
        for n in node_dtos:
            if (n.name or "").lower() == q_lower:
                return n

        # 8. Case-insensitive substring in file_path
        for n in node_dtos:
            if q_lower in (n.file_path or "").lower():
                return n

        return None

    @staticmethod
    async def get_repository_graph(
        session: AsyncSession,
        repository_id: str,
        user: User,
        node_type: Optional[str] = None,
        file_path: Optional[str] = None,
        max_nodes: int = 500,
        focus_symbol: Optional[str] = None,
        commit_sha: Optional[str] = None,
    ) -> dict:
        """Fetch repository graph nodes and edges scoped to tenant ownership and optional filters."""
        from packages.graph import GraphAnalyzer, GraphNodeDTO, GraphEdgeDTO

        repo = await RepositoryService.get_repository_by_id(session, repository_id, user)
        sha = commit_sha or repo.current_commit_sha

        node_stmt = select(GraphNode).where(GraphNode.repository_id == repo.id)
        edge_stmt = select(GraphEdge).where(GraphEdge.repository_id == repo.id)
        if sha:
            node_stmt = node_stmt.where(GraphNode.commit_sha == sha)
            edge_stmt = edge_stmt.where(GraphEdge.commit_sha == sha)

        all_nodes = list((await session.execute(node_stmt)).scalars().all())
        all_edges = list((await session.execute(edge_stmt)).scalars().all())

        node_id_to_key = {n.id: n.node_key for n in all_nodes}
        node_key_to_obj = {n.node_key: n for n in all_nodes}

        node_dtos = [
            GraphNodeDTO(
                node_id=n.node_key,
                node_type=n.node_type,
                name=n.name,
                qualified_name=n.node_key,
                file_path=n.file_path,
                metadata=n.metadata_json or {},
            )
            for n in all_nodes
        ]
        edge_dtos = [
            GraphEdgeDTO(
                source_id=node_id_to_key.get(e.source_node_id, e.source_node_id),
                target_id=node_id_to_key.get(e.target_node_id, e.target_node_id),
                edge_type=e.edge_type,
                metadata=e.metadata_json or {},
            )
            for e in all_edges
            if e.source_node_id in node_id_to_key and e.target_node_id in node_id_to_key
        ]

        analyzer = GraphAnalyzer(node_dtos, edge_dtos)
        metrics_dto = analyzer.get_graph_metrics()

        # If focus_symbol is requested, extract neighborhood subgraph
        if focus_symbol:
            target_dto = RepositoryService._find_matching_node(node_dtos, focus_symbol)
            if target_dto:
                subgraph = analyzer.get_neighborhood_subgraph(target_dto.node_id, depth=2, max_nodes=max_nodes)
                selected_node_keys = {n.node_id for n in subgraph.nodes}
                filtered_nodes = [node_key_to_obj[k] for k in selected_node_keys if k in node_key_to_obj]
                filtered_edges = [
                    e for e in all_edges
                    if node_id_to_key.get(e.source_node_id) in selected_node_keys
                    and node_id_to_key.get(e.target_node_id) in selected_node_keys
                ]
            else:
                filtered_nodes = []
                filtered_edges = []
        else:
            filtered_nodes = all_nodes
            if node_type:
                filtered_nodes = [n for n in filtered_nodes if n.node_type == node_type.upper()]
            if file_path:
                filtered_nodes = [n for n in filtered_nodes if file_path.lower() in (n.file_path or "").lower()]
            if len(filtered_nodes) > max_nodes:
                filtered_nodes = filtered_nodes[:max_nodes]

            allowed_node_ids = {n.id for n in filtered_nodes}
            filtered_edges = [
                e for e in all_edges
                if e.source_node_id in allowed_node_ids and e.target_node_id in allowed_node_ids
            ]

        formatted_nodes = [
            {
                "id": n.id,
                "node_key": n.node_key,
                "node_type": n.node_type,
                "name": n.name,
                "file_path": n.file_path,
                "in_degree": analyzer.graph.in_degree(n.node_key) if n.node_key in analyzer.graph else 0,
                "out_degree": analyzer.graph.out_degree(n.node_key) if n.node_key in analyzer.graph else 0,
                "metadata": n.metadata_json or {},
            }
            for n in filtered_nodes
        ]

        formatted_edges = [
            {
                "id": e.id,
                "source": node_id_to_key.get(e.source_node_id, e.source_node_id),
                "target": node_id_to_key.get(e.target_node_id, e.target_node_id),
                "edge_type": e.edge_type,
                "metadata": e.metadata_json or {},
            }
            for e in filtered_edges
        ]

        return {
            "repository_id": repo.id,
            "commit_sha": sha,
            "nodes": formatted_nodes,
            "edges": formatted_edges,
            "nodes_count": len(formatted_nodes),
            "edges_count": len(formatted_edges),
            "metrics": metrics_dto.model_dump(),
        }

    @staticmethod
    async def get_repository_cycles(
        session: AsyncSession,
        repository_id: str,
        user: User,
        commit_sha: Optional[str] = None,
    ) -> dict:
        """Detect circular dependencies (import cycles, call cycles, mixed cycles) using Tarjan's SCC."""
        from packages.graph import GraphAnalyzer, GraphNodeDTO, GraphEdgeDTO

        repo = await RepositoryService.get_repository_by_id(session, repository_id, user)
        sha = commit_sha or repo.current_commit_sha

        node_stmt = select(GraphNode).where(GraphNode.repository_id == repo.id)
        edge_stmt = select(GraphEdge).where(GraphEdge.repository_id == repo.id)
        if sha:
            node_stmt = node_stmt.where(GraphNode.commit_sha == sha)
            edge_stmt = edge_stmt.where(GraphEdge.commit_sha == sha)

        nodes = list((await session.execute(node_stmt)).scalars().all())
        edges = list((await session.execute(edge_stmt)).scalars().all())

        node_id_to_key = {n.id: n.node_key for n in nodes}
        node_dtos = [
            GraphNodeDTO(
                node_id=n.node_key,
                node_type=n.node_type,
                name=n.name,
                qualified_name=n.node_key,
                file_path=n.file_path,
                metadata=n.metadata_json or {},
            )
            for n in nodes
        ]
        edge_dtos = [
            GraphEdgeDTO(
                source_id=node_id_to_key.get(e.source_node_id, e.source_node_id),
                target_id=node_id_to_key.get(e.target_node_id, e.target_node_id),
                edge_type=e.edge_type,
                metadata=e.metadata_json or {},
            )
            for e in edges
            if e.source_node_id in node_id_to_key and e.target_node_id in node_id_to_key
        ]

        analyzer = GraphAnalyzer(node_dtos, edge_dtos)
        cycles = analyzer.find_circular_dependencies()

        return {
            "repository_id": repo.id,
            "commit_sha": sha,
            "total_cycles": len(cycles),
            "cycles": [c.model_dump() for c in cycles],
        }

    @staticmethod
    async def get_graph_node_details(
        session: AsyncSession,
        repository_id: str,
        node_key: str,
        user: User,
        commit_sha: Optional[str] = None,
    ) -> dict:
        """Fetch detailed node metrics, callers, callees, and bounded neighborhood."""
        from packages.graph import GraphAnalyzer, GraphNodeDTO, GraphEdgeDTO

        repo = await RepositoryService.get_repository_by_id(session, repository_id, user)
        sha = commit_sha or repo.current_commit_sha

        node_stmt = select(GraphNode).where(GraphNode.repository_id == repo.id)
        edge_stmt = select(GraphEdge).where(GraphEdge.repository_id == repo.id)
        if sha:
            node_stmt = node_stmt.where(GraphNode.commit_sha == sha)
            edge_stmt = edge_stmt.where(GraphEdge.commit_sha == sha)

        nodes = list((await session.execute(node_stmt)).scalars().all())
        edges = list((await session.execute(edge_stmt)).scalars().all())

        node_id_to_key = {n.id: n.node_key for n in nodes}
        node_key_to_obj = {n.node_key: n for n in nodes}

        node_dtos = [
            GraphNodeDTO(
                node_id=n.node_key,
                node_type=n.node_type,
                name=n.name,
                qualified_name=n.node_key,
                file_path=n.file_path,
                metadata=n.metadata_json or {},
            )
            for n in nodes
        ]
        edge_dtos = [
            GraphEdgeDTO(
                source_id=node_id_to_key.get(e.source_node_id, e.source_node_id),
                target_id=node_id_to_key.get(e.target_node_id, e.target_node_id),
                edge_type=e.edge_type,
                metadata=e.metadata_json or {},
            )
            for e in edges
            if e.source_node_id in node_id_to_key and e.target_node_id in node_id_to_key
        ]

        analyzer = GraphAnalyzer(node_dtos, edge_dtos)

        target_dto = RepositoryService._find_matching_node(node_dtos, node_key)
        if not target_dto:
            raise APIError(
                message=f"Node '{node_key}' not found in repository graph.",
                code="NODE_NOT_FOUND",
                status_code=404,
            )

        target_id = target_dto.node_id
        metrics = analyzer.get_graph_metrics(target_id)

        incoming_keys = list(analyzer.graph.predecessors(target_id)) if target_id in analyzer.graph else []
        incoming_nodes = [
            {
                "id": node_key_to_obj[k].id if k in node_key_to_obj else k,
                "node_key": k,
                "node_type": analyzer.node_map[k].node_type,
                "name": analyzer.node_map[k].name,
                "file_path": analyzer.node_map[k].file_path,
                "in_degree": analyzer.graph.in_degree(k),
                "out_degree": analyzer.graph.out_degree(k),
                "metadata": analyzer.node_map[k].metadata,
            }
            for k in incoming_keys if k in analyzer.node_map
        ]

        outgoing_keys = list(analyzer.graph.successors(target_id)) if target_id in analyzer.graph else []
        outgoing_nodes = [
            {
                "id": node_key_to_obj[k].id if k in node_key_to_obj else k,
                "node_key": k,
                "node_type": analyzer.node_map[k].node_type,
                "name": analyzer.node_map[k].name,
                "file_path": analyzer.node_map[k].file_path,
                "in_degree": analyzer.graph.in_degree(k),
                "out_degree": analyzer.graph.out_degree(k),
                "metadata": analyzer.node_map[k].metadata,
            }
            for k in outgoing_keys if k in analyzer.node_map
        ]

        subgraph = analyzer.get_neighborhood_subgraph(target_id, depth=2, max_nodes=50)

        target_obj = node_key_to_obj.get(target_id)
        target_response = {
            "id": target_obj.id if target_obj else target_id,
            "node_key": target_id,
            "node_type": target_dto.node_type,
            "name": target_dto.name,
            "file_path": target_dto.file_path,
            "in_degree": metrics.in_degree,
            "out_degree": metrics.out_degree,
            "metadata": target_dto.metadata,
        }

        return {
            "node": target_response,
            "in_degree": metrics.in_degree,
            "out_degree": metrics.out_degree,
            "centrality": metrics.centrality,
            "incoming_callers": incoming_nodes,
            "outgoing_callees": outgoing_nodes,
            "neighborhood_nodes_count": len(subgraph.nodes),
            "neighborhood_edges_count": len(subgraph.edges),
        }

    @staticmethod
    async def trigger_indexing(
        session: AsyncSession,
        repository_id: str,
        user: User,
        commit_sha: Optional[str] = None,
    ) -> IndexJob:
        """Trigger asynchronous repository indexing job via Celery worker."""
        repo = await RepositoryService.get_repository_by_id(session, repository_id, user)
        sha = commit_sha or repo.current_commit_sha or "main"

        job = IndexJob(
            repository_id=repo.id,
            commit_sha=sha,
            status="QUEUED",
            current_step="INITIALIZING",
            progress_percent=0,
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)

        # Trigger Celery task asynchronously
        try:
            from workers.tasks.ingestion import ingest_repository
            ingest_repository.delay(repo.id, sha, job_id=job.id)
        except Exception:
            # If celery broker is not active in isolated environment, job stays in database
            pass

        return job

    @staticmethod
    async def get_indexing_job(
        session: AsyncSession,
        repository_id: str,
        job_id: str,
        user: User,
    ) -> IndexJob:
        """Retrieve the live status and progress of an indexing job."""
        repo = await RepositoryService.get_repository_by_id(session, repository_id, user)
        stmt = select(IndexJob).where(
            IndexJob.id == job_id,
            IndexJob.repository_id == repo.id,
        )
        job = (await session.execute(stmt)).scalar_one_or_none()
        if not job:
            raise APIError(
                message=f"Indexing job '{job_id}' not found for repository '{repository_id}'.",
                code="JOB_NOT_FOUND",
                status_code=404,
            )
        return job

    @staticmethod
    async def get_repository_symbols(
        session: AsyncSession,
        repository_id: str,
        user: User,
        query: Optional[str] = None,
        symbol_type: Optional[str] = None,
    ) -> list:
        """Search and list extracted AST code symbols within the repository."""
        repo = await RepositoryService.get_repository_by_id(session, repository_id, user)
        stmt = select(CodeSymbol).where(CodeSymbol.repository_id == repo.id)
        if query:
            stmt = stmt.where(CodeSymbol.name.ilike(f"%{query}%"))
        if symbol_type:
            stmt = stmt.where(CodeSymbol.symbol_type == symbol_type.upper())
        stmt = stmt.order_by(CodeSymbol.name.asc()).limit(100)
        res = await session.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def get_file_details(
        session: AsyncSession,
        repository_id: str,
        file_id: str,
        user: User,
    ) -> dict:
        """Fetch details and symbols for a specific file."""
        repo = await RepositoryService.get_repository_by_id(session, repository_id, user)
        stmt = select(RepositoryFile).where(
            RepositoryFile.id == file_id,
            RepositoryFile.repository_id == repo.id,
        )
        file = (await session.execute(stmt)).scalar_one_or_none()
        if not file:
            raise APIError(
                message=f"File '{file_id}' not found.",
                code="FILE_NOT_FOUND",
                status_code=404,
            )

        sym_stmt = select(CodeSymbol).where(CodeSymbol.file_id == file.id).order_by(CodeSymbol.start_line.asc())
        symbols = (await session.execute(sym_stmt)).scalars().all()

        return {
            "id": file.id,
            "path": file.path,
            "language": file.language,
            "loc": file.loc,
            "size_bytes": file.size_bytes,
            "content_hash": file.content_hash,
            "symbols": list(symbols),
        }

    @staticmethod
    async def compute_graph_impact(
        session: AsyncSession,
        repository_id: str,
        symbol_name: str,
        user: User,
        commit_sha: Optional[str] = None,
    ):
        """Compute blast radius impact analysis for a given symbol."""
        from packages.graph import GraphAnalyzer, GraphNodeDTO, GraphEdgeDTO

        repo = await RepositoryService.get_repository_by_id(session, repository_id, user)
        sha = commit_sha or repo.current_commit_sha

        node_stmt = select(GraphNode).where(GraphNode.repository_id == repo.id)
        edge_stmt = select(GraphEdge).where(GraphEdge.repository_id == repo.id)
        if sha:
            node_stmt = node_stmt.where(GraphNode.commit_sha == sha)
            edge_stmt = edge_stmt.where(GraphEdge.commit_sha == sha)

        nodes = list((await session.execute(node_stmt)).scalars().all())
        edges = list((await session.execute(edge_stmt)).scalars().all())

        node_id_to_key = {n.id: n.node_key for n in nodes}
        node_dtos = [
            GraphNodeDTO(
                node_id=n.node_key,
                node_type=n.node_type,
                name=n.name,
                qualified_name=n.node_key,
                file_path=n.file_path,
                metadata=n.metadata_json or {},
            )
            for n in nodes
        ]
        edge_dtos = [
            GraphEdgeDTO(
                source_id=node_id_to_key.get(e.source_node_id, e.source_node_id),
                target_id=node_id_to_key.get(e.target_node_id, e.target_node_id),
                edge_type=e.edge_type,
                metadata=e.metadata_json or {},
            )
            for e in edges
            if e.source_node_id in node_id_to_key and e.target_node_id in node_id_to_key
        ]

        analyzer = GraphAnalyzer(node_dtos, edge_dtos)

        # Match target symbol
        target_node = RepositoryService._find_matching_node(node_dtos, symbol_name)
        if not target_node:
            raise APIError(
                message=f"Symbol '{symbol_name}' not found in dependency graph.",
                code="SYMBOL_NOT_FOUND",
                status_code=404,
            )

        return analyzer.compute_impact_analysis(target_node.node_id)

    @staticmethod
    async def compute_graph_path(
        session: AsyncSession,
        repository_id: str,
        source_symbol: str,
        target_symbol: str,
        user: User,
        commit_sha: Optional[str] = None,
    ):
        """Compute shortest path between two symbols in the dependency graph."""
        from packages.graph import GraphAnalyzer, GraphNodeDTO, GraphEdgeDTO

        repo = await RepositoryService.get_repository_by_id(session, repository_id, user)
        sha = commit_sha or repo.current_commit_sha

        node_stmt = select(GraphNode).where(GraphNode.repository_id == repo.id)
        edge_stmt = select(GraphEdge).where(GraphEdge.repository_id == repo.id)
        if sha:
            node_stmt = node_stmt.where(GraphNode.commit_sha == sha)
            edge_stmt = edge_stmt.where(GraphEdge.commit_sha == sha)

        nodes = list((await session.execute(node_stmt)).scalars().all())
        edges = list((await session.execute(edge_stmt)).scalars().all())

        node_id_to_key = {n.id: n.node_key for n in nodes}
        node_dtos = [
            GraphNodeDTO(
                node_id=n.node_key,
                node_type=n.node_type,
                name=n.name,
                qualified_name=n.node_key,
                file_path=n.file_path,
                metadata=n.metadata_json or {},
            )
            for n in nodes
        ]
        edge_dtos = [
            GraphEdgeDTO(
                source_id=node_id_to_key.get(e.source_node_id, e.source_node_id),
                target_id=node_id_to_key.get(e.target_node_id, e.target_node_id),
                edge_type=e.edge_type,
                metadata=e.metadata_json or {},
            )
            for e in edges
            if e.source_node_id in node_id_to_key and e.target_node_id in node_id_to_key
        ]

        analyzer = GraphAnalyzer(node_dtos, edge_dtos)

        src_node = RepositoryService._find_matching_node(node_dtos, source_symbol)
        if not src_node:
            raise APIError(
                message=f"Source symbol '{source_symbol}' not found in dependency graph.",
                code="SYMBOL_NOT_FOUND",
                status_code=404,
            )

        tgt_node = RepositoryService._find_matching_node(node_dtos, target_symbol)
        if not tgt_node:
            raise APIError(
                message=f"Target symbol '{target_symbol}' not found in dependency graph.",
                code="SYMBOL_NOT_FOUND",
                status_code=404,
            )

        return analyzer.find_shortest_path(src_node.node_id, tgt_node.node_id)

    @staticmethod
    async def search_repository(
        session: AsyncSession,
        repository_id: str,
        query: str,
        user: User,
        mode: str = "hybrid",
        top_k: int = 10,
        rerank: bool = True,
        symbol_type: Optional[str] = None,
        file_pattern: Optional[str] = None,
    ) -> dict:
        """Execute multi-tenant hybrid search over repository code chunks."""
        repo = await RepositoryService.get_repository_by_id(session, repository_id, user)

        # 1. Fetch chunks from database for BM25 and metadata enrichment
        chunk_stmt = (
            select(CodeChunk, RepositoryFile.path, CodeSymbol.name, CodeSymbol.symbol_type)
            .join(RepositoryFile, CodeChunk.file_id == RepositoryFile.id)
            .outerjoin(CodeSymbol, CodeChunk.symbol_id == CodeSymbol.id)
            .where(CodeChunk.repository_id == repo.id)
        )
        chunk_res = await session.execute(chunk_stmt)
        rows = chunk_res.all()

        chunks_data = []
        for ch, file_path, sym_name, sym_type in rows:
            display_end_line = ch.end_line
            if sym_type == "CLASS" and (ch.end_line - ch.start_line > 100):
                display_end_line = min(ch.start_line + 40, ch.end_line)

            chunks_data.append({
                "id": ch.id,
                "repository_id": ch.repository_id,
                "file_id": ch.file_id,
                "file_path": file_path,
                "symbol_name": sym_name,
                "symbol_type": sym_type,
                "content": ch.content,
                "content_hash": ch.content_hash,
                "start_line": ch.start_line,
                "end_line": display_end_line,
                "metadata": {},
            })

        # 2. Build or retrieve cached retrieval engines
        from packages.ai import AIProviderFactory
        from packages.retrieval import (
            BM25Index,
            VectorIndex,
            CrossEncoderReranker,
            HybridSearchService,
            SearchMode,
            SearchRequestDTO,
        )
        from ..config import settings

        global _SEARCH_SERVICE_CACHE
        if "_SEARCH_SERVICE_CACHE" not in globals():
            _SEARCH_SERVICE_CACHE = {}

        cache_key = (
            repo.id,
            repo.current_commit_sha or "main",
            len(chunks_data),
            settings.EMBEDDING_PROVIDER,
            settings.RERANKER_PROVIDER,
        )

        if cache_key in _SEARCH_SERVICE_CACHE:
            service = _SEARCH_SERVICE_CACHE[cache_key]
        else:
            bm25_index = BM25Index(chunks_data)

            emb_key = settings.GEMINI_API_KEY if settings.EMBEDDING_PROVIDER == "gemini" else settings.OPENAI_API_KEY
            emb_model = settings.GEMINI_EMBEDDING_MODEL if settings.EMBEDDING_PROVIDER == "gemini" else settings.OPENAI_EMBEDDING_MODEL
            embedding_provider = AIProviderFactory.create_embedding_provider(
                provider_name=settings.EMBEDDING_PROVIDER,
                api_key=emb_key,
                model_name=emb_model,
            )
            vector_index = VectorIndex(
                embedding_provider=embedding_provider,
                qdrant_url=settings.QDRANT_URL,
                qdrant_api_key=settings.QDRANT_API_KEY,
            )
            # Ensure in-memory fallback has points if Qdrant isn't running
            if not vector_index.qdrant_client:
                await vector_index.upsert_chunks(repo.id, repo.current_commit_sha or "main", chunks_data)

            reranker_provider = AIProviderFactory.create_reranker_provider(
                provider_name=settings.RERANKER_PROVIDER,
            )
            reranker = CrossEncoderReranker(reranker_provider)

            service = HybridSearchService(
                bm25_index=bm25_index,
                vector_index=vector_index,
                reranker=reranker,
            )
            _SEARCH_SERVICE_CACHE[cache_key] = service

        search_mode = SearchMode(mode.lower()) if mode.lower() in [m.value for m in SearchMode] else SearchMode.HYBRID
        req = SearchRequestDTO(
            query=query,
            mode=search_mode,
            top_k=top_k,
            rerank=rerank,
            symbol_type=symbol_type,
            file_pattern=file_pattern,
        )

        result_dto = await service.search(
            repository_id=repo.id,
            request=req,
            commit_sha=repo.current_commit_sha,
        )

        return result_dto.model_dump()

