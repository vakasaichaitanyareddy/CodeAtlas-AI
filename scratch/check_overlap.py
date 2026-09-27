from apps.api.app.database import async_session_factory
from apps.api.app.services.chat_service import ChatService
from packages.retrieval.tokenizer import CodeTokenizer
import asyncio

async def check():
    async with async_session_factory() as s:
        rag = await ChatService._build_rag_engine(s, '926f0321-4fa0-4880-9c1e-d69d7934623c')
        for c in rag.hybrid_search.bm25_index.chunks:
            if c.get('file_path') == 'src/flask/app.py' and c.get('symbol_name') == 'dispatch_request':
                print('Found app.py dispatch_request chunk:', c['start_line'], c['end_line'])
                doc_tokens = set(CodeTokenizer.tokenize(c['content']))
                sym_tokens = set(CodeTokenizer.tokenize(c['symbol_name']))
                print('sym_tokens:', sym_tokens)
                targets = {'flask', 'route', 'routing', 'dispatch', 'request', 'view', 'function', 'functions'}
                print('Matches with targets:', doc_tokens.intersection(targets))

if __name__ == '__main__':
    asyncio.run(check())
