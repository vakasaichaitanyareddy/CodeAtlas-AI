import asyncio
import re
from rank_bm25 import BM25Okapi
from apps.api.app.database import async_session_factory
from apps.api.app.services.chat_service import ChatService
from packages.retrieval.tokenizer import CodeTokenizer

queries = [
    'How does request context work in Flask?',
    'Where is the Flask application class implemented?',
    'What happens when Flask pushes a request context?',
    'How are request and application contexts different?',
    'How does Flask route a request to a view function?'
]

filler = {
    'how', 'where', 'what', 'when', 'why', 'who', 'which',
    'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'does', 'do', 'did', 'done',
    'can', 'could', 'would', 'should', 'will',
    'work', 'works', 'happen', 'happens',
    'tell', 'show', 'explain', 'give', 'find', 'locate',
    'implemented', 'implementation'
}

def rank_candidates(query, chunks, bm25, top_k=5):
    # 1. Clean query tokens
    q_tokens = [t for t in CodeTokenizer.tokenize(query) if t not in filler]
    if not q_tokens:
        q_tokens = CodeTokenizer.tokenize(query)

    scores = bm25.get_scores(q_tokens)
    
    # 2. Combine with symbol match and source boost
    scored = []
    q_set = set(q_tokens)
    q_lower = query.lower()

    for idx, (c, bm25_sc) in enumerate(zip(chunks, scores)):
        f_path = c.get('file_path', '')
        sym = (c.get('symbol_name') or '').lower()
        content = c.get('content', '')

        # Base score from BM25
        score = float(bm25_sc)

        # Symbol match boost
        if sym and sym in q_set:
            score += 15.0  # Exact symbol match (e.g. sym="flask", sym="request")
        elif sym and any(t in sym for t in q_set):
            score += 8.0   # Partial symbol match (e.g. request_context, AppContext)

        # File path relevance boost
        if any(t in f_path.lower() for t in q_set):
            score += 5.0   # Path match (e.g. ctx.py, app.py, views.py)

        # Priority: src/ and docs/ > tests/ > changelog/legal
        if f_path.startswith('src/'):
            score *= 1.2
        elif f_path.startswith('docs/') and not f_path.startswith('docs/tutorial'):
            score *= 1.1
        elif 'changes' in f_path.lower() or 'changelog' in f_path.lower():
            score *= 0.3   # Demote changelogs for technical Q&A
        elif f_path.startswith('tests/'):
            score *= 0.7   # Demote tests when real code/docs are available

        scored.append((c, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]

async def run_audit():
    repo_id = '926f0321-4fa0-4880-9c1e-d69d7934623c'
    async with async_session_factory() as s:
        rag = await ChatService._build_rag_engine(s, repo_id)
        chunks = rag.hybrid_search.bm25_index.chunks

        corpus = []
        for c in chunks:
            f_path = c.get('file_path', '')
            sym = c.get('symbol_name', '') or ''
            prefix = f"{f_path} {sym}"
            text = f"{prefix} {prefix} {c.get('content', '')}"
            corpus.append(CodeTokenizer.tokenize(text))

        bm25 = BM25Okapi(corpus)

        for q in queries:
            print('=' * 75)
            print('QUERY:', q)
            top = rank_candidates(q, chunks, bm25, top_k=5)
            for rank, (c, sc) in enumerate(top, 1):
                p = c.get('file_path', '')
                sl = c.get('start_line', 0)
                el = c.get('end_line', 0)
                sym = c.get('symbol_name', '')
                print(f'  #{rank} | score={sc:6.2f} | {p:30s} L{sl:4d}-{el:4d} | sym={sym}')

if __name__ == '__main__':
    asyncio.run(run_audit())
