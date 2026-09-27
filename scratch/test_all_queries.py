from sqlalchemy import select
from apps.api.app.database import async_session_factory
from apps.api.app.models.graph import GraphNode, GraphEdge
from apps.api.app.services.chat_service import ChatService
from packages.retrieval.models import SearchRequestDTO, SearchMode, ScoredChunkDTO
from packages.retrieval.tokenizer import CodeTokenizer
from rank_bm25 import BM25Okapi
import asyncio

QUERIES = [
    ("A", "How does request context work in Flask?"),
    ("B", "Where is the Flask application class implemented?"),
    ("C", "What happens when Flask pushes a request context?"),
    ("D", "How are request and application contexts different?"),
    ("E", "How does Flask route a request to a view function?"),
]

async def run_queries():
    async with async_session_factory() as s:
        repo_id = '926f0321-4fa0-4880-9c1e-d69d7934623c'
        rag = await ChatService._build_rag_engine(s, repo_id)

        corpus = [
            CodeTokenizer.tokenize(f"{c.get('file_path','')} {c.get('symbol_name','')} {c.get('content','')}")
            for c in rag.hybrid_search.bm25_index.chunks
        ]
        bm25 = BM25Okapi(corpus)

        for label, query in QUERIES:
            print(f"\n=======================================================")
            print(f"QUERY {label}: {query}")
            print(f"=======================================================")

            # Clean query tokens + process synonyms
            tokens = CodeTokenizer.clean_query_tokens(query)
            expanded_query_words = set(tokens)
            if any(w in expanded_query_words for w in ['route', 'routing']):
                expanded_query_words.update(['dispatch', 'dispatch_request', 'url_rule', 'view_functions'])
            if 'function' in expanded_query_words:
                expanded_query_words.add('functions')
            if any(w in expanded_query_words for w in ['context', 'contexts']):
                expanded_query_words.update(['appcontext', 'requestcontext'])

            scores = bm25.get_scores(list(expanded_query_words))
            scored = []
            for c, sc in zip(rag.hybrid_search.bm25_index.chunks, scores):
                fp = c.get('file_path', '')
                if 'changes' in fp.lower(): sc *= 0.25
                elif 'test' in fp.lower(): sc *= 0.75
                elif fp.startswith(('src/', 'flask/')): sc *= 1.3
                scored.append((c, sc))

            scored.sort(key=lambda x: x[1], reverse=True)

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
                for c, sc in scored[:15]
            ]

            # Graph expansion for top implementation symbols
            seed_symbols = [c.symbol_name for c in candidates if c.symbol_name and not c.file_path.startswith('tests/')][:3]
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

            # Rerank
            scored_results = []
            for idx, c in enumerate(candidates):
                meta = c.metadata or {}
                file_path = c.file_path
                symbol_name = c.symbol_name or ""
                doc = c.content

                doc_tokens = set(CodeTokenizer.tokenize(doc))
                file_tokens = set(CodeTokenizer.tokenize(file_path))
                symbol_tokens = set(CodeTokenizer.tokenize(symbol_name))

                c_overlap = len(expanded_query_words.intersection(doc_tokens))
                s_overlap = len(expanded_query_words.intersection(symbol_tokens))
                p_overlap = len(expanded_query_words.intersection(file_tokens))

                score = (
                    (c_overlap / max(1, len(expanded_query_words))) * 0.4
                    + (s_overlap / max(1, len(expanded_query_words))) * 0.4
                    + (p_overlap / max(1, len(expanded_query_words))) * 0.2
                )

                fp_lower = file_path.lower()
                if "changes" in fp_lower or "changelog" in fp_lower: score *= 0.25
                elif "test" in fp_lower: score *= 0.75
                elif fp_lower.startswith(("src/", "flask/")): score *= 1.3

                if meta.get("is_graph_neighbor"):
                    score *= 1.25

                score += 0.005 * (1.0 / (idx + 1))
                c.score = min(1.0, score)
                scored_results.append(c)

            scored_results.sort(key=lambda x: x.score, reverse=True)

            for i, c in enumerate(scored_results[:4], 1):
                src_str = c.metadata.get('source', 'hybrid')
                print(f"  {i}. {c.file_path}:{c.start_line}-{c.end_line} | sym={c.symbol_name} ({c.symbol_type}) | score={c.score:.4f} | src={src_str}")

if __name__ == '__main__':
    asyncio.run(run_queries())
