from apps.api.app.database import async_session_factory
from apps.api.app.services.chat_service import ChatService
from packages.retrieval.tokenizer import CodeTokenizer
from rank_bm25 import BM25Okapi
import asyncio

async def test_expanded_bm25():
    async with async_session_factory() as s:
        rag = await ChatService._build_rag_engine(s, '926f0321-4fa0-4880-9c1e-d69d7934623c')
        query = 'How does Flask route a request to a view function?'
        tokens = CodeTokenizer.clean_query_tokens(query)
        print('Original tokens:', tokens)
        expanded_tokens = list(tokens) + ['dispatch']
        print('Expanded tokens:', expanded_tokens)

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
        print('=== TOP 10 WITH EXPANDED TOKENS ===')
        for c, sc in scored[:10]:
            print(f'  {sc:6.3f} | {c.get("file_path"):30s} L{c.get("start_line"):4d}-{c.get("end_line"):4d} | sym={c.get("symbol_name")}')

if __name__ == '__main__':
    asyncio.run(test_expanded_bm25())
