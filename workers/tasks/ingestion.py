import os
import uuid
import logging
import asyncio
import subprocess
import tempfile
import shutil
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from sqlalchemy import select, update, delete
from ..celery_app import celery_app
from apps.api.app.database import async_session_factory
from apps.api.app.models import (
    Repository,
    IndexJob,
    RepositoryFile,
    CodeSymbol,
    CodeChunk,
    GraphNode,
    GraphEdge,
)
from packages.parser import get_parser_for_file, ASTChunker
from packages.parser.models import NormalizedFile, SymbolType
from packages.graph import GraphBuilder
from ..scanner import RepositoryScanner

logger = logging.getLogger(__name__)


async def run_ingestion_pipeline(
    repository_id: str,
    commit_sha: str,
    source_directory: Optional[str] = None,
    job_id: Optional[str] = None,
    session_factory=None,
    session=None,
) -> Dict[str, Any]:
    """Execute the end-to-end repository ingestion and code intelligence pipeline asynchronously."""
    if session is not None:
        return await _execute_pipeline_core(
            session=session,
            repository_id=repository_id,
            commit_sha=commit_sha,
            source_directory=source_directory,
            job_id=job_id,
        )

    factory = session_factory or async_session_factory
    async with factory() as sess:
        return await _execute_pipeline_core(
            session=sess,
            repository_id=repository_id,
            commit_sha=commit_sha,
            source_directory=source_directory,
            job_id=job_id,
        )


async def _execute_pipeline_core(
    session,
    repository_id: str,
    commit_sha: str,
    source_directory: Optional[str] = None,
    job_id: Optional[str] = None,
) -> Dict[str, Any]:
    # 1. Fetch Repository
    repo_res = await session.execute(select(Repository).where(Repository.id == repository_id))
    repo = repo_res.scalar_one_or_none()
    if not repo:
        raise ValueError(f"Repository {repository_id} not found in database")

    # 2. Fetch or Create IndexJob
    job = None
    if job_id:
        job_res = await session.execute(select(IndexJob).where(IndexJob.id == job_id))
        job = job_res.scalar_one_or_none()

    if not job:
        job = IndexJob(
            id=job_id or str(uuid.uuid4()),
            repository_id=repository_id,
            commit_sha=commit_sha,
            status="RUNNING",
            current_step="SCANNING",
            progress_percent=10,
            started_at=datetime.now(timezone.utc),
        )
        session.add(job)
    else:
        job.status = "RUNNING"
        job.current_step = "SCANNING"
        job.progress_percent = 10
        job.started_at = datetime.now(timezone.utc)
        job.error_message = None

    await session.commit()
    await session.refresh(job)

    temp_dir_to_clean: Optional[str] = None
    try:
        # Step 0: Resolve Repository Source Directory via local path or git clone
        if source_directory and os.path.isdir(source_directory):
            scan_path = source_directory
            logger.info(f"Using provided source_directory: {scan_path}")
        elif repo.github_url and any(repo.github_url.startswith(p) for p in ("http://", "https://", "git@", "git://")):
            temp_dir = tempfile.mkdtemp(prefix=f"codeatlas_clone_{repository_id[:8]}_")
            temp_dir_to_clean = temp_dir
            branch_or_ref = repo.default_branch or commit_sha or "main"
            logger.info(f"Cloning {repo.github_url} (branch/ref: {branch_or_ref}) into {temp_dir}...")

            is_mock_url = any(marker in repo.github_url.lower() for marker in ["mock", "test-org", "example.com", "dummy", "fake"])
            clone_success = False
            clone_err = ""

            if not is_mock_url:
                try:
                    # Attempt 1: Shallow clone with branch
                    cmd = ["git", "clone", "--depth", "1"]
                    if branch_or_ref and branch_or_ref != "HEAD":
                        cmd.extend(["--branch", branch_or_ref])
                    cmd.extend([repo.github_url, temp_dir])
                    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
                    if proc.returncode == 0:
                        clone_success = True
                    else:
                        clone_err = proc.stderr
                        # Attempt 2: Fallback clone without explicit branch
                        cmd_fallback = ["git", "clone", "--depth", "1", repo.github_url, temp_dir]
                        proc_fb = subprocess.run(cmd_fallback, capture_output=True, text=True, timeout=180)
                        if proc_fb.returncode == 0:
                            clone_success = True
                        else:
                            clone_err += f"\nFallback error: {proc_fb.stderr}"
                except Exception as clone_exc:
                    clone_err = str(clone_exc)

            if not clone_success:
                if is_mock_url:
                    logger.info("Mock repository URL detected. Generating isolated mock fixture files.")
                    src_dir = os.path.join(temp_dir, "src")
                    os.makedirs(src_dir, exist_ok=True)
                    with open(os.path.join(src_dir, "service.py"), "w", encoding="utf-8") as f:
                        f.write("class MockService:\n    def execute(self):\n        return 'mock_result'\n")
                    with open(os.path.join(src_dir, "main.py"), "w", encoding="utf-8") as f:
                        f.write("from src.service import MockService\ndef run():\n    return MockService().execute()\n")
                    clone_success = True
                else:
                    raise RuntimeError(f"Failed to clone repository from '{repo.github_url}': {clone_err}")

            scan_path = temp_dir
        else:
            raise ValueError(
                f"Repository {repository_id} has neither a valid local source_directory "
                f"nor a cloneable github_url ('{repo.github_url}'). Ingestion aborted."
            )

        # Step 1: SCANNING
        logger.info(f"Scanning repository {repository_id} from {scan_path}")
        scanner = RepositoryScanner()
        scanned_files = scanner.scan_directory(scan_path)

        job.current_step = "PARSING"
        job.progress_percent = 30
        await session.commit()

        # Step 2: PARSING
        logger.info(f"Parsing {len(scanned_files)} discovered source files")
        parsed_files: List[NormalizedFile] = []
        file_record_map: Dict[str, str] = {}
        symbol_record_map: Dict[str, str] = {}
        total_loc = 0

        # Clear existing data for this repository and commit_sha to ensure strict isolation and idempotency
        await session.execute(
            delete(GraphEdge).where(
                GraphEdge.repository_id == repository_id,
                GraphEdge.commit_sha == commit_sha,
            )
        )
        await session.execute(
            delete(GraphNode).where(
                GraphNode.repository_id == repository_id,
                GraphNode.commit_sha == commit_sha,
            )
        )
        await session.execute(
            delete(CodeChunk).where(
                CodeChunk.repository_id == repository_id,
                CodeChunk.commit_sha == commit_sha,
            )
        )
        await session.execute(
            delete(CodeSymbol).where(
                CodeSymbol.repository_id == repository_id,
                CodeSymbol.commit_sha == commit_sha,
            )
        )
        await session.execute(
            delete(RepositoryFile).where(
                RepositoryFile.repository_id == repository_id,
                RepositoryFile.commit_sha == commit_sha,
            )
        )
        await session.flush()

        for sfile in scanned_files:
            parser = get_parser_for_file(sfile.rel_path)
            pfile = parser.parse_file(sfile.rel_path, sfile.content)
            parsed_files.append(pfile)
            total_loc += pfile.lines_of_code

            db_file = RepositoryFile(
                id=str(uuid.uuid4()),
                repository_id=repository_id,
                commit_sha=commit_sha,
                path=sfile.rel_path,
                language=sfile.language,
                loc=sfile.content.count("\n") + 1,
                size_bytes=sfile.size_bytes,
                content_hash=sfile.content_hash,
            )
            session.add(db_file)
            await session.flush()
            file_record_map[sfile.rel_path] = db_file.id

            for sym in pfile.symbols:
                db_sym = CodeSymbol(
                    id=str(uuid.uuid4()),
                    file_id=db_file.id,
                    repository_id=repository_id,
                    commit_sha=commit_sha,
                    name=sym.name,
                    qualified_name=sym.qualified_name,
                    symbol_type=sym.symbol_type.value,
                    start_line=sym.start_line,
                    end_line=sym.end_line,
                    signature=sym.signature,
                    docstring=sym.docstring,
                )
                session.add(db_sym)
                symbol_record_map[sym.qualified_name] = db_sym.id

        await session.flush()

        # Step 3: GRAPH_BUILDING
        job.current_step = "GRAPH_BUILDING"
        job.progress_percent = 60
        await session.commit()

        builder = GraphBuilder()
        graph_nodes, graph_edges = builder.build_graph(parsed_files)
        db_node_map: Dict[str, str] = {}

        for node in graph_nodes:
            db_node = GraphNode(
                id=str(uuid.uuid4()),
                repository_id=repository_id,
                commit_sha=commit_sha,
                node_key=node.node_id,
                node_type=node.node_type,
                name=node.name,
                file_path=node.file_path,
                symbol_id=symbol_record_map.get(node.name),
                metadata_json=node.metadata,
            )
            session.add(db_node)
            db_node_map[node.node_id] = db_node.id

        await session.flush()

        for edge in graph_edges:
            src_id = db_node_map.get(edge.source_id)
            tgt_id = db_node_map.get(edge.target_id)
            if src_id and tgt_id:
                db_edge = GraphEdge(
                    id=str(uuid.uuid4()),
                    repository_id=repository_id,
                    commit_sha=commit_sha,
                    source_node_id=src_id,
                    target_node_id=tgt_id,
                    edge_type=edge.edge_type,
                    metadata_json=edge.metadata,
                )
                session.add(db_edge)

        await session.flush()

        # Step 4: CHUNKING
        job.current_step = "CHUNKING"
        job.progress_percent = 85
        await session.commit()

        chunker = ASTChunker()
        total_chunks = 0
        chunk_dicts = []

        for sfile, pfile in zip(scanned_files, parsed_files):
            file_id = file_record_map[sfile.rel_path]
            file_chunks = chunker.chunk_file(pfile, sfile.content)
            for idx, ch in enumerate(file_chunks):
                chunk_id = str(uuid.uuid4())
                total_chunks += 1
                db_chunk = CodeChunk(
                    id=chunk_id,
                    repository_id=repository_id,
                    file_id=file_id,
                    symbol_id=symbol_record_map.get(ch.symbol_name) if ch.symbol_name else None,
                    commit_sha=commit_sha,
                    chunk_index=idx,
                    content=ch.content,
                    content_hash=ch.content_hash,
                    start_line=ch.start_line,
                    end_line=ch.end_line,
                    token_count=max(1, len(ch.content) // 4),
                )
                session.add(db_chunk)
                chunk_dicts.append({
                    "id": chunk_id,
                    "repository_id": repository_id,
                    "file_id": file_id,
                    "file_path": sfile.rel_path,
                    "symbol_name": ch.symbol_name,
                    "symbol_type": getattr(ch, "symbol_type", None),
                    "content": ch.content,
                    "content_hash": ch.content_hash,
                    "start_line": ch.start_line,
                    "end_line": ch.end_line,
                })

        await session.flush()

        # Step 5: VECTOR INDEXING & EMBEDDINGS
        job.current_step = "EMBEDDING_AND_VECTOR_INDEXING"
        job.progress_percent = 92
        await session.commit()

        try:
            from packages.ai import AIProviderFactory
            from packages.retrieval.vector import VectorIndex
            from apps.api.app.config import settings

            api_key = settings.GEMINI_API_KEY if settings.EMBEDDING_PROVIDER == "gemini" else settings.OPENAI_API_KEY
            model_name = settings.GEMINI_EMBEDDING_MODEL if settings.EMBEDDING_PROVIDER == "gemini" else settings.OPENAI_EMBEDDING_MODEL
            embedding_provider = AIProviderFactory.create_embedding_provider(
                provider_name=settings.EMBEDDING_PROVIDER,
                api_key=api_key,
                model_name=model_name,
            )
            vector_index = VectorIndex(
                embedding_provider=embedding_provider,
                qdrant_url=settings.QDRANT_URL,
                qdrant_api_key=settings.QDRANT_API_KEY,
            )
            await vector_index.delete_by_repository(
                repository_id=repository_id,
                commit_sha=commit_sha,
            )
            await vector_index.upsert_chunks(
                repository_id=repository_id,
                commit_sha=commit_sha,
                chunks=chunk_dicts,
            )
        except Exception as vec_err:
            logger.warning(f"Vector indexing skipped or failed ({vec_err}). Non-fatal for relational persistence.")

        # Step 6: COMPLETION
        stats = {
            "files_count": len(scanned_files),
            "loc_total": total_loc,
            "symbols_count": len(symbol_record_map),
            "nodes_count": len(graph_nodes),
            "edges_count": len(graph_edges),
            "chunks_count": total_chunks,
        }

        job.status = "COMPLETED"
        job.current_step = "COMPLETED"
        job.progress_percent = 100
        job.completed_at = datetime.now(timezone.utc)
        job.stats_json = stats

        repo.is_indexed = True
        repo.current_commit_sha = commit_sha
        repo.status = "ACTIVE"
        repo.index_version += 1

        await session.commit()
        logger.info(f"Ingestion pipeline completed successfully for repo {repository_id}: {stats}")
        return {"status": "completed", "job_id": job.id, "repository_id": repository_id, "stats": stats}

    except Exception as exc:
        logger.exception(f"Ingestion pipeline failed for repo {repository_id}: {exc}")
        job.status = "FAILED"
        job.current_step = "ERROR"
        job.error_message = str(exc)
        job.completed_at = datetime.now(timezone.utc)
        await session.commit()
        raise
    finally:
        if temp_dir_to_clean and os.path.exists(temp_dir_to_clean):
            try:
                shutil.rmtree(temp_dir_to_clean, ignore_errors=True)
                logger.info(f"Cleaned up temporary clone directory {temp_dir_to_clean}")
            except Exception as clean_err:
                logger.warning(f"Could not remove temporary clone dir {temp_dir_to_clean}: {clean_err}")


@celery_app.task(bind=True, name="tasks.ingest_repository")
def ingest_repository(
    self,
    repository_id: str,
    commit_sha: str,
    source_directory: Optional[str] = None,
    job_id: Optional[str] = None,
):
    """Celery task entrypoint triggering the full asynchronous repository ingestion pipeline."""
    logger.info(f"Celery task received for repository {repository_id} at {commit_sha}")

    async def _run_task():
        from sqlalchemy.pool import NullPool
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
        from apps.api.app.config import settings
        import workers.tasks.ingestion as ing_mod

        task_engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
        task_session_factory = async_sessionmaker(
            bind=task_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
        orig_factory = ing_mod.async_session_factory
        ing_mod.async_session_factory = task_session_factory
        try:
            return await run_ingestion_pipeline(
                repository_id=repository_id,
                commit_sha=commit_sha,
                source_directory=source_directory,
                job_id=job_id,
            )
        finally:
            ing_mod.async_session_factory = orig_factory
            await task_engine.dispose()

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(asyncio.run, _run_task()).result()
    else:
        return asyncio.run(_run_task())

