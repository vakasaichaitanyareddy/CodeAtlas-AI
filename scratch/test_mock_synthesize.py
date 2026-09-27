import asyncio
from apps.api.app.database import async_session_factory
from apps.api.app.models import Repository
from apps.api.app.services.chat_service import ChatService
from packages.rag.context import ContextAssembler
from packages.ai.mock_provider import MockLLMProvider

async def test():
    async with async_session_factory() as session:
        repo = await session.get(Repository, '926f0321-4fa0-4880-9c1e-d69d7934623c')
        rag_engine = await ChatService._build_rag_engine(session, repo.id, 'main')
        context_pack = await rag_engine.prepare_context(
            query='How does request context work in Flask?',
            repository_id=repo.id,
            commit_sha='main',
            top_k=5
        )
        context_block = ContextAssembler.format_context_for_prompt(context_pack)
        user_prompt = f"User Question: How does request context work in Flask?\n\n=== Codebase Context Snippets ===\n{context_block}\n\nProvide a clear, grounded answer with exact [filepath:Lstart-Lend] citations."
        
        provider = MockLLMProvider(model_name="mock-gemini")
        resp = await provider.generate(prompt=user_prompt)
        print("Generated response:\n", resp.content)

asyncio.run(test())
