import asyncio
import json
import logging
import uuid
from typing import List, Dict, Any, Optional, AsyncIterator
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.models.user import User
from apps.api.app.models.repository import Repository
from apps.api.app.models.code import RepositoryFile, CodeSymbol, CodeChunk
from apps.api.app.models.graph import GraphNode, GraphEdge
from apps.api.app.models.chat import Conversation, Message
from apps.api.app.schemas.chat import (
    ChatRequest,
    ChatMessageResponse,
    CitationDTO,
    ContextChunkDTO,
    RetrievalEvidenceDTO,
    ConversationSummary,
    ConversationDetail,
)
from apps.api.app.config import settings
from apps.api.app.core.errors import APIError

from packages.ai import AIProviderFactory
from packages.retrieval.models import SearchMode
from packages.retrieval.bm25 import BM25Index
from packages.retrieval.vector import VectorIndex
from packages.retrieval.reranker import CrossEncoderReranker
from packages.retrieval.hybrid_service import HybridSearchService
from packages.rag.engine import RAGEngine
from packages.rag.models import GroundedAnswer

logger = logging.getLogger("codeatlas.api.services.chat")


class GraphContextList(list):
    """A list wrapper that also stores an adjacency map for symbols.
    ``edges`` is a list of edge description dicts, ``adjacency`` maps a symbol name
    to a list of neighbor dicts {"neighbor_symbol": ..., "neighbor_file": ..., "edge_type": ...}.
    """
    def __init__(self, edges: List[Dict[str, Any]], adjacency: Dict[str, List[Dict[str, Any]]] = None):
        super().__init__(edges)
        self.adjacency = adjacency or {}

class ChatService:
    """Enterprise chat service coordinating grounded RAG and conversation persistence."""

    @staticmethod
    async def _verify_repository_access(
        session: AsyncSession,
        repository_id: str,
        user: User,
    ) -> Repository:
        """Verify repository existence and tenant ownership (403 if foreign tenant)."""
        res = await session.execute(
            select(Repository).where(Repository.id == repository_id)
        )
        repo = res.scalar_one_or_none()
        if not repo:
            raise APIError(
                message=f"Repository '{repository_id}' not found.",
                code="REPOSITORY_NOT_FOUND",
                status_code=404,
            )
        if repo.owner_id != user.id and getattr(user, "role", "USER") != "ADMIN":
            raise APIError(
                message="You do not have access to this repository.",
                code="CROSS_TENANT_ACCESS_DENIED",
                status_code=403,
            )
        return repo

    @staticmethod
    async def _verify_conversation_access(
        session: AsyncSession,
        repository_id: str,
        conversation_id: str,
        user: User,
    ) -> Conversation:
        """Verify conversation belongs to user and repository."""
        res = await session.execute(
            select(Conversation)
            .where(
                Conversation.id == conversation_id,
                Conversation.repository_id == repository_id,
            )
            .options(selectinload(Conversation.messages))
        )
        conv = res.scalar_one_or_none()
        if not conv:
            raise APIError(
                message=f"Conversation '{conversation_id}' not found.",
                code="CONVERSATION_NOT_FOUND",
                status_code=404,
            )
        if conv.user_id != user.id and getattr(user, "role", "USER") != "ADMIN":
            raise APIError(
                message="You do not have access to this conversation.",
                code="CROSS_TENANT_ACCESS_DENIED",
                status_code=403,
            )
        return conv

    @staticmethod
    async def _load_file_records(
        session: AsyncSession,
        repository_id: str,
        commit_sha: Optional[str] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """Load physical files and AST symbols for citation verification."""
        stmt = (
            select(RepositoryFile)
            .where(RepositoryFile.repository_id == repository_id)
            .options(selectinload(RepositoryFile.symbols))
        )
        if commit_sha:
            stmt = stmt.where(RepositoryFile.commit_sha == commit_sha)

        res = await session.execute(stmt)
        files = res.scalars().all()

        file_map: Dict[str, Dict[str, Any]] = {}
        for f in files:
            symbols = [
                {"name": s.name, "start_line": s.start_line, "end_line": s.end_line}
                for s in f.symbols
            ]
            file_map[f.path] = {
                "id": f.id,
                "loc": f.loc,
                "symbols": symbols,
            }
        return file_map

    @staticmethod
    async def _load_graph_context(
        session: AsyncSession,
        repository_id: str,
        commit_sha: Optional[str] = None,
    ) -> GraphContextList:
        """Load call and import relationships for dependency/process queries with symbol adjacency."""
        nodes_stmt = select(GraphNode).where(GraphNode.repository_id == repository_id)
        if commit_sha:
            nodes_stmt = nodes_stmt.where(GraphNode.commit_sha == commit_sha)
        nodes_res = await session.execute(nodes_stmt)
        nodes = nodes_res.scalars().all()
        node_map = {n.id: n for n in nodes}

        edges_stmt = select(GraphEdge).where(GraphEdge.repository_id == repository_id)
        if commit_sha:
            edges_stmt = edges_stmt.where(GraphEdge.commit_sha == commit_sha)
        edges_res = await session.execute(edges_stmt)
        edges = edges_res.scalars().all()

        adjacency: Dict[str, List[Dict[str, Any]]] = {}
        edge_items: List[Dict[str, Any]] = []

        for e in edges:
            src = node_map.get(e.source_node_id)
            tgt = node_map.get(e.target_node_id)
            if not src or not tgt:
                continue

            desc = f"{src.name} ({src.file_path}) --[{e.edge_type}]--> {tgt.name} ({tgt.file_path})"
            edge_items.append({
                "id": e.id,
                "description": desc,
                "source": e.source_node_id,
                "target": e.target_node_id,
                "source_name": src.name,
                "source_file": src.file_path,
                "target_name": tgt.name,
                "target_file": tgt.file_path,
                "edge_type": e.edge_type,
            })

            for s_sym, t_sym, t_file, rel_type in [
                (src.name, tgt.name, tgt.file_path, e.edge_type),
                (tgt.name, src.name, src.file_path, e.edge_type),
            ]:
                if s_sym not in adjacency:
                    adjacency[s_sym] = []
                adjacency[s_sym].append({
                    "neighbor_symbol": t_sym,
                    "neighbor_file": t_file,
                    "edge_type": rel_type,
                })

        return GraphContextList(edge_items, adjacency=adjacency)

    @staticmethod
    async def _build_rag_engine(
        session: AsyncSession,
        repository_id: str,
        commit_sha: Optional[str] = None,
    ) -> RAGEngine:
        """Construct the full RAGEngine with AI providers and retrieval indices."""
        # 1. AI Providers
        llm_api_key = settings.GEMINI_API_KEY if settings.LLM_PROVIDER == "gemini" else settings.OPENAI_API_KEY
        emb_api_key = settings.GEMINI_API_KEY if settings.EMBEDDING_PROVIDER == "gemini" else settings.OPENAI_API_KEY

        if settings.LLM_PROVIDER == "gemini":
            llm_model = settings.GEMINI_LLM_MODEL
        elif settings.LLM_PROVIDER == "openai":
            llm_model = settings.OPENAI_LLM_MODEL
        else:
            llm_model = "mock-llm"

        if settings.EMBEDDING_PROVIDER == "gemini":
            emb_model = settings.GEMINI_EMBEDDING_MODEL
        elif settings.EMBEDDING_PROVIDER == "openai":
            emb_model = settings.OPENAI_EMBEDDING_MODEL
        else:
            emb_model = "mock-embedding"

        llm_provider = AIProviderFactory.create_llm_provider(
            provider_name=settings.LLM_PROVIDER,
            api_key=llm_api_key,
            model_name=llm_model,
        )
        emb_provider = AIProviderFactory.create_embedding_provider(
            provider_name=settings.EMBEDDING_PROVIDER,
            api_key=emb_api_key,
            model_name=emb_model,
        )
        reranker_provider = AIProviderFactory.create_reranker_provider(
            provider_name=settings.RERANKER_PROVIDER,
            model_name=settings.RERANKER_MODEL,
        )

        # 2. Fetch chunks from database for BM25 and Vector indices
        chunk_stmt = (
            select(CodeChunk, RepositoryFile.path, CodeSymbol.name, CodeSymbol.symbol_type)
            .join(RepositoryFile, CodeChunk.file_id == RepositoryFile.id)
            .outerjoin(CodeSymbol, CodeChunk.symbol_id == CodeSymbol.id)
            .where(CodeChunk.repository_id == repository_id)
        )
        if commit_sha:
            chunk_stmt = chunk_stmt.where(CodeChunk.commit_sha == commit_sha)

        res = await session.execute(chunk_stmt)
        rows = res.all()

        chunk_dicts = [
            {
                "id": c.id,
                "repository_id": c.repository_id,
                "file_id": c.file_id,
                "file_path": file_path,
                "symbol_name": sym_name,
                "symbol_type": sym_type,
                "content": c.content,
                "start_line": c.start_line,
                "end_line": c.end_line,
                "metadata": {},
            }
            for c, file_path, sym_name, sym_type in rows
        ]

        # 3. Indices
        bm25_index = BM25Index(chunks=chunk_dicts)

        vector_index = VectorIndex(
            embedding_provider=emb_provider,
            qdrant_url=settings.QDRANT_URL,
            qdrant_api_key=settings.QDRANT_API_KEY,
        )

        reranker = CrossEncoderReranker(provider=reranker_provider)

        hybrid_service = HybridSearchService(
            bm25_index=bm25_index,
            vector_index=vector_index,
            reranker=reranker,
        )

        return RAGEngine(
            llm_provider=llm_provider,
            hybrid_search_service=hybrid_service,
        )

    @staticmethod
    async def send_chat_message(
        session: AsyncSession,
        repository_id: str,
        request: ChatRequest,
        user: User,
    ) -> ChatMessageResponse:
        """Synchronously process a chat message, validate citations, and persist conversation."""
        repo = await ChatService._verify_repository_access(session, repository_id, user)
        sha = request.commit_sha or repo.current_commit_sha

        # Retrieve or create conversation
        if request.conversation_id:
            conv = await ChatService._verify_conversation_access(
                session, repository_id, request.conversation_id, user
            )
        else:
            conv_title = request.message[:50].strip() + ("..." if len(request.message) > 50 else "")
            conv = Conversation(
                id=str(uuid.uuid4()),
                repository_id=repo.id,
                user_id=user.id,
                commit_sha=sha,
                title=conv_title,
            )
            session.add(conv)
            await session.flush()

        # Persist user message
        user_msg = Message(
            id=str(uuid.uuid4()),
            conversation_id=conv.id,
            role="USER",
            content=request.message,
        )
        session.add(user_msg)
        await session.flush()

        # Build RAG engine and load evidence
        rag_engine = await ChatService._build_rag_engine(session, repository_id, sha)
        file_map = await ChatService._load_file_records(session, repository_id, sha)
        graph_context = await ChatService._load_graph_context(session, repository_id, sha)

        # Load recent history
        hist_res = await session.execute(
            select(Message)
            .where(Message.conversation_id == conv.id)
            .order_by(Message.created_at)
        )
        all_msgs = hist_res.scalars().all()
        history_list = [{"role": m.role.lower(), "content": m.content} for m in all_msgs[:-1]]

        # Generate grounded answer
        mode = SearchMode(request.mode.lower()) if request.mode.lower() in ("hybrid", "lexical", "semantic") else SearchMode.HYBRID
        grounded = await rag_engine.generate_answer(
            query=request.message,
            repository_id=repo.id,
            commit_sha=sha,
            search_mode=mode,
            top_k=request.top_k,
            rerank=request.rerank,
            graph_context=graph_context,
            file_records=file_map,
            conversation_history=history_list,
        )

        # Persist assistant message
        citations_json = [c.model_dump() for c in grounded.citations]
        provider_name = grounded.provider or getattr(rag_engine.llm_provider, "provider_name", "mock")
        is_mock = grounded.is_mock or getattr(rag_engine.llm_provider, "is_mock", True)
        model_name = grounded.model_name or getattr(rag_engine.llm_provider, "model_name", "mock-llm")

        metadata_json = {
            "grounding_status": grounded.grounding_status.value,
            "intent": grounded.intent.value,
            "provider": provider_name,
            "model_name": model_name,
            "is_mock": is_mock,
            "retrieval_evidence": grounded.retrieval_evidence.model_dump(),
            "context_chunks": [ch.model_dump() for ch in grounded.context_chunks],
        }

        assistant_msg = Message(
            id=str(uuid.uuid4()),
            conversation_id=conv.id,
            role="ASSISTANT",
            content=grounded.answer,
            citations_json=citations_json,
            retrieval_metadata_json=metadata_json,
            tokens_used=grounded.prompt_tokens + grounded.completion_tokens,
            latency_ms=grounded.latency_ms,
        )
        session.add(assistant_msg)
        await session.commit()
        await session.refresh(assistant_msg)

        return ChatMessageResponse(
            id=assistant_msg.id,
            conversation_id=conv.id,
            role="ASSISTANT",
            content=grounded.answer,
            grounding_status=grounded.grounding_status.value,
            intent=grounded.intent.value,
            provider=provider_name,
            is_mock=is_mock,
            citations=[CitationDTO(**c) for c in citations_json],
            context_chunks=[ContextChunkDTO(**ch.model_dump()) for ch in grounded.context_chunks],
            retrieval_evidence=RetrievalEvidenceDTO(**grounded.retrieval_evidence.model_dump()),
            tokens_used=assistant_msg.tokens_used,
            latency_ms=assistant_msg.latency_ms,
            created_at=assistant_msg.created_at.isoformat(),
        )

    @staticmethod
    async def stream_chat_message(
        session: AsyncSession,
        repository_id: str,
        request: ChatRequest,
        user: User,
    ) -> AsyncIterator[str]:
        """Stream chat tokens via Server-Sent Events (SSE) and commit only upon completion."""
        repo = await ChatService._verify_repository_access(session, repository_id, user)
        sha = request.commit_sha or repo.current_commit_sha

        # Retrieve or create conversation
        if request.conversation_id:
            conv = await ChatService._verify_conversation_access(
                session, repository_id, request.conversation_id, user
            )
        else:
            conv_title = request.message[:50].strip() + ("..." if len(request.message) > 50 else "")
            conv = Conversation(
                id=str(uuid.uuid4()),
                repository_id=repo.id,
                user_id=user.id,
                commit_sha=sha,
                title=conv_title,
            )
            session.add(conv)
            await session.flush()

        user_msg = Message(
            id=str(uuid.uuid4()),
            conversation_id=conv.id,
            role="USER",
            content=request.message,
        )
        session.add(user_msg)
        await session.flush()

        rag_engine = await ChatService._build_rag_engine(session, repository_id, sha)
        file_map = await ChatService._load_file_records(session, repository_id, sha)
        graph_context = await ChatService._load_graph_context(session, repository_id, sha)

        hist_res = await session.execute(
            select(Message)
            .where(Message.conversation_id == conv.id)
            .order_by(Message.created_at)
        )
        all_msgs = hist_res.scalars().all()
        history_list = [{"role": m.role.lower(), "content": m.content} for m in all_msgs[:-1]]

        mode = SearchMode(request.mode.lower()) if request.mode.lower() in ("hybrid", "lexical", "semantic") else SearchMode.HYBRID

        final_grounded: Optional[GroundedAnswer] = None
        try:
            async for token, final_result in rag_engine.stream_answer(
                query=request.message,
                repository_id=repo.id,
                commit_sha=sha,
                search_mode=mode,
                top_k=request.top_k,
                rerank=request.rerank,
                graph_context=graph_context,
                file_records=file_map,
                conversation_history=history_list,
            ):
                if token:
                    data = json.dumps({"event": "token", "delta": token, "conversation_id": conv.id})
                    yield f"data: {data}\n\n"

                if final_result:
                    final_grounded = final_result

            if final_grounded:
                # Persist completed assistant message
                citations_json = [c.model_dump() for c in final_grounded.citations]
                provider_name = final_grounded.provider or getattr(rag_engine.llm_provider, "provider_name", "mock")
                is_mock = final_grounded.is_mock or getattr(rag_engine.llm_provider, "is_mock", True)
                model_name = final_grounded.model_name or getattr(rag_engine.llm_provider, "model_name", "mock-llm")

                metadata_json = {
                    "grounding_status": final_grounded.grounding_status.value,
                    "intent": final_grounded.intent.value,
                    "provider": provider_name,
                    "model_name": model_name,
                    "is_mock": is_mock,
                    "retrieval_evidence": final_grounded.retrieval_evidence.model_dump(),
                    "context_chunks": [ch.model_dump() for ch in final_grounded.context_chunks],
                }

                assistant_msg = Message(
                    id=str(uuid.uuid4()),
                    conversation_id=conv.id,
                    role="ASSISTANT",
                    content=final_grounded.answer,
                    citations_json=citations_json,
                    retrieval_metadata_json=metadata_json,
                    tokens_used=final_grounded.prompt_tokens + final_grounded.completion_tokens,
                    latency_ms=final_grounded.latency_ms,
                )
                session.add(assistant_msg)
                await session.commit()

                # Send completion event with citations and evidence
                complete_payload = {
                    "event": "complete",
                    "conversation_id": conv.id,
                    "message_id": assistant_msg.id,
                    "answer": final_grounded.answer,
                    "grounding_status": final_grounded.grounding_status.value,
                    "intent": final_grounded.intent.value,
                    "provider": provider_name,
                    "model_name": model_name,
                    "is_mock": is_mock,
                    "citations": citations_json,
                    "context_chunks": [ch.model_dump() for ch in final_grounded.context_chunks],
                    "retrieval_evidence": final_grounded.retrieval_evidence.model_dump(),
                    "tokens_used": assistant_msg.tokens_used,
                    "latency_ms": assistant_msg.latency_ms,
                }
                yield f"data: {json.dumps(complete_payload)}\n\n"

        except GeneratorExit:
            logger.info("Client disconnected from streaming RAG; rolling back transaction.")
            await session.rollback()
            raise
        except asyncio.CancelledError:
            logger.info("Task cancelled during streaming RAG; rolling back transaction.")
            await session.rollback()
            raise
        except Exception as e:
            logger.error(f"Error during streaming RAG: {e}", exc_info=True)
            await session.rollback()
            err_payload = {"event": "error", "error": str(e)}
            yield f"data: {json.dumps(err_payload)}\n\n"

    @staticmethod
    async def list_conversations(
        session: AsyncSession,
        repository_id: str,
        user: User,
    ) -> List[ConversationSummary]:
        """List all conversation summaries for this repository owned by the user."""
        await ChatService._verify_repository_access(session, repository_id, user)

        stmt = (
            select(
                Conversation,
                func.count(Message.id).label("message_count"),
            )
            .outerjoin(Message, Conversation.id == Message.conversation_id)
            .where(
                Conversation.repository_id == repository_id,
                Conversation.user_id == user.id,
            )
            .group_by(Conversation.id)
            .order_by(Conversation.created_at.desc())
        )
        res = await session.execute(stmt)
        rows = res.all()

        return [
            ConversationSummary(
                id=c.id,
                repository_id=c.repository_id,
                title=c.title,
                commit_sha=c.commit_sha,
                message_count=count,
                created_at=c.created_at.isoformat(),
                updated_at=c.updated_at.isoformat() if c.updated_at else None,
            )
            for c, count in rows
        ]

    @staticmethod
    async def get_conversation(
        session: AsyncSession,
        repository_id: str,
        conversation_id: str,
        user: User,
    ) -> ConversationDetail:
        """Get full conversation detail including all messages."""
        await ChatService._verify_repository_access(session, repository_id, user)
        conv = await ChatService._verify_conversation_access(
            session, repository_id, conversation_id, user
        )

        msg_dtos = []
        for m in conv.messages:
            meta = m.retrieval_metadata_json or {}
            citations = [CitationDTO(**c) for c in (m.citations_json or [])]
            chunks = [ContextChunkDTO(**ch) for ch in meta.get("context_chunks", [])]
            evidence = RetrievalEvidenceDTO(**meta.get("retrieval_evidence", {})) if "retrieval_evidence" in meta else None

            msg_dtos.append(
                ChatMessageResponse(
                    id=m.id,
                    conversation_id=conv.id,
                    role=m.role,
                    content=m.content,
                    grounding_status=meta.get("grounding_status"),
                    intent=meta.get("intent"),
                    provider=meta.get("provider"),
                    is_mock=meta.get("is_mock", False),
                    citations=citations,
                    context_chunks=chunks,
                    retrieval_evidence=evidence,
                    tokens_used=m.tokens_used,
                    latency_ms=m.latency_ms,
                    created_at=m.created_at.isoformat(),
                )
            )

        return ConversationDetail(
            id=conv.id,
            repository_id=conv.repository_id,
            title=conv.title,
            commit_sha=conv.commit_sha,
            created_at=conv.created_at.isoformat(),
            messages=msg_dtos,
        )

    @staticmethod
    async def delete_conversation(
        session: AsyncSession,
        repository_id: str,
        conversation_id: str,
        user: User,
    ) -> None:
        """Delete conversation thread."""
        await ChatService._verify_repository_access(session, repository_id, user)
        conv = await ChatService._verify_conversation_access(
            session, repository_id, conversation_id, user
        )
        await session.delete(conv)
        await session.commit()
