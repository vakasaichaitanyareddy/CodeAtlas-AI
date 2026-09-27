from sqlalchemy import select
from apps.api.app.database import async_session_factory
from apps.api.app.models.graph import GraphNode, GraphEdge
from apps.api.app.services.chat_service import ChatService
from packages.retrieval.models import SearchRequestDTO, SearchMode, ScoredChunkDTO
from packages.retrieval.tokenizer import CodeTokenizer
import asyncio

async def test_graph_enrichment():
    async with async_session_factory() as s:
        repo_id = '926f0321-4fa0-4880-9c1e-d69d7934623c'
        rag = await ChatService._build_rag_engine(s, repo_id)
        query = 'How does Flask route a request to a view function?'

        # 1. Initial retrieval
        req = SearchRequestDTO(query=query, mode=SearchMode.HYBRID, top_k=6, rerank=True)
        init_res = await rag.hybrid_search.search(repo_id, req)
        print('=== INITIAL CANDIDATES ===')
        for r in init_res.results[:4]:
            print(f'  {r.file_path}:{r.start_line}-{r.end_line} | sym={r.symbol_name} ({r.symbol_type}) | score={r.score:.4f}')

        # 2. Extract top symbols
        seed_symbols = [r.symbol_name for r in init_res.results if r.symbol_name and not r.file_path.startswith('tests/')]
        print('Seed symbols:', seed_symbols[:4])

        # 3. Query graph edges
        nodes_res = await s.execute(
            select(GraphNode)
            .where(GraphNode.repository_id == repo_id)
            .where(GraphNode.name.in_(seed_symbols))
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
        neighbor_symbols = set()
        for e, n in edges_res.all():
            if n.name and len(n.name) > 2 and not n.name.endswith('.py'):
                neighbor_symbols.add((n.name, n.file_path))
        print('Discovered neighbor symbols:', neighbor_symbols)

        # 4. Find matching chunks from bm25_index.chunks for neighbors
        existing_ids = {r.chunk_id for r in init_res.results}
        added_candidates = []
        for n_name, n_path in neighbor_symbols:
            for c in rag.hybrid_search.bm25_index.chunks:
                if c.get('id') not in existing_ids and c.get('file_path') == n_path and c.get('symbol_name') == n_name:
                    added_candidates.append(
                        ScoredChunkDTO(
                            chunk_id=c['id'],
                            file_path=c['file_path'],
                            symbol_name=c['symbol_name'],
                            symbol_type=c['symbol_type'],
                            start_line=c['start_line'],
                            end_line=c['end_line'],
                            content=c['content'],
                            score=0.5,
                            source='graph',
                        )
                    )
                    existing_ids.add(c['id'])

        print(f'Added {len(added_candidates)} graph neighbor chunks: {[c.symbol_name for c in added_candidates]}')

        # 5. Rerank combined
        all_candidates = list(init_res.results) + added_candidates
        reranked = await rag.hybrid_search.reranker.rerank(query, all_candidates, top_k=5)
        print('=== RERANKED COMBINED CANDIDATES ===')
        for idx, r in enumerate(reranked, 1):
            src_str = r.metadata.get('source', 'hybrid')
            print(f'  {idx}. {r.file_path}:{r.start_line}-{r.end_line} | sym={r.symbol_name} ({r.symbol_type}) | score={r.score:.4f} | src={src_str}')

if __name__ == '__main__':
    asyncio.run(test_graph_enrichment())
