from sqlalchemy import select
from apps.api.app.database import async_session_factory
from apps.api.app.models.graph import GraphNode, GraphEdge
from apps.api.app.services.chat_service import ChatService
from packages.retrieval.models import SearchRequestDTO, SearchMode, ScoredChunkDTO
from packages.retrieval.tokenizer import CodeTokenizer
from rank_bm25 import BM25Okapi
import asyncio

async def test_combined():
    async with async_session_factory() as s:
        repo_id = '926f0321-4fa0-4880-9c1e-d69d7934623c'
        rag = await ChatService._build_rag_engine(s, repo_id)
        query = 'How does Flask route a request to a view function?'

        # 1. Expand query tokens for process query (route -> dispatch)
        clean_tokens = CodeTokenizer.clean_query_tokens(query)
        if any(t in clean_tokens for t in ['route', 'routing']):
            expanded_tokens = list(clean_tokens) + ['dispatch']
        else:
            expanded_tokens = clean_tokens

        # 2. BM25 search with expanded tokens
        corpus = [
            CodeTokenizer.tokenize(f"{c.get('file_path','')} {c.get('symbol_name','')} {c.get('content','')}")
            for c in rag.hybrid_search.bm25_index.chunks
        ]
        bm25 = BM25Okapi(corpus)
        scores = bm25.get_scores(expanded_tokens)

        scored = []
        for c, sc in zip(rag.hybrid_search.bm25_index.chunks, scores):
            fp = c.get('file_path', '')
            if 'changes' in fp.lower():
                sc *= 0.25
            elif 'test' in fp.lower():
                sc *= 0.75
            elif fp.startswith(('src/', 'flask/')):
                sc *= 1.3
            scored.append((c, sc))

        scored.sort(key=lambda x: x[1], reverse=True)
        print('=== BM25 EXPANDED CANDIDATES ===')
        for c, sc in scored[:6]:
            print(f'  {sc:6.3f} | {c.get("file_path"):30s} L{c.get("start_line"):4d}-{c.get("end_line"):4d} | sym={c.get("symbol_name")}')

        # 3. Take top candidates as ScoredChunkDTO
        candidates = [
            ScoredChunkDTO(
                chunk_id=c['id'],
                file_path=c['file_path'],
                symbol_name=c['symbol_name'],
                symbol_type=c['symbol_type'],
                start_line=c['start_line'],
                end_line=c['end_line'],
                content=c['content'],
                score=sc,
                metadata={'source': 'hybrid'}
            )
            for c, sc in scored[:10]
        ]

        # 4. Graph expansion: Find connected CALLS / DEPENDS_ON nodes
        top_symbols = [c.symbol_name for c in candidates if c.symbol_name and not c.file_path.startswith('tests/')]
        nodes_res = await s.execute(
            select(GraphNode)
            .where(GraphNode.repository_id == repo_id)
            .where(GraphNode.name.in_(top_symbols[:4]))
            .where(~GraphNode.file_path.like('tests/%'))
        )
        nodes = nodes_res.scalars().all()
        node_ids = [n.id for n in nodes]

        edges_res = await s.execute(
            select(GraphEdge, GraphNode)
            .join(GraphNode, (GraphEdge.target_node_id == GraphNode.id) | (GraphEdge.source_node_id == GraphNode.id))
            .where(GraphEdge.repository_id == repo_id)
            .where((GraphEdge.source_node_id.in_(node_ids)) | (GraphEdge.target_node_id.in_(node_ids)))
            .where(~GraphNode.id.in_(node_ids))
            .where(~GraphNode.file_path.like('tests/%'))
        )
        neighbor_nodes = set()
        for e, n in edges_res.all():
            if n.name and len(n.name) > 2 and not n.name.endswith('.py'):
                neighbor_nodes.add((n.name, n.file_path))

        existing_ids = {c.chunk_id for c in candidates}
        for n_name, n_path in neighbor_nodes:
            for c in rag.hybrid_search.bm25_index.chunks:
                if c.get('id') not in existing_ids and c.get('file_path') == n_path and c.get('symbol_name') == n_name:
                    candidates.append(
                        ScoredChunkDTO(
                            chunk_id=c['id'],
                            file_path=c['file_path'],
                            symbol_name=c['symbol_name'],
                            symbol_type=c['symbol_type'],
                            start_line=c['start_line'],
                            end_line=c['end_line'],
                            content=c['content'],
                            score=0.5,
                            metadata={'source': 'graph', 'is_graph_neighbor': True}
                        )
                    )
                    existing_ids.add(c['id'])

        # 5. Rerank
        reranked = await rag.hybrid_search.reranker.rerank(query, candidates, top_k=5)
        print('\n=== FINAL RERANKED RESULTS ===')
        for idx, r in enumerate(reranked, 1):
            src_str = r.metadata.get('source', 'hybrid')
            print(f'  {idx}. {r.file_path}:{r.start_line}-{r.end_line} | sym={r.symbol_name} ({r.symbol_type}) | score={r.score:.4f} | src={src_str}')

if __name__ == '__main__':
    asyncio.run(test_combined())
