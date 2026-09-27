import asyncio
import json
import logging
from sqlalchemy import select
from apps.api.app.database import async_session_factory
from apps.api.app.models.user import User
from apps.api.app.models.repository import Repository
from apps.api.app.schemas.chat import ChatRequest
from apps.api.app.services.chat_service import ChatService

logging.basicConfig(level=logging.WARNING)

QUERIES = [
    "How does request context work in Flask?",
    "Where is the Flask application class implemented?",
    "What happens when Flask pushes a request context?",
    "How are request and application contexts different?",
    "How does Flask route a request to a view function?",
]

REPO_ID = "926f0321-4fa0-4880-9c1e-d69d7934623c"

async def main():
    async with async_session_factory() as session:
        repo_res = await session.execute(select(Repository).where(Repository.id == REPO_ID))
        repo = repo_res.scalar_one_or_none()
        if not repo:
            print(f"Error: Repository {REPO_ID} not found")
            return

        user_res = await session.execute(select(User).where(User.id == repo.owner_id))
        user = user_res.scalar_one_or_none()
        if not user:
            print(f"Error: User {repo.owner_id} not found")
            return

        print(f"Testing against Repo: {repo.name} ({repo.id}) - Owner: {user.email}")
        print("=" * 80)

        results = []

        for i, q in enumerate(QUERIES, 1):
            print(f"\n================================================================================")
            print(f"QUERY {i}: \"{q}\"")
            print(f"================================================================================")
            chat_req = ChatRequest(
                message=q,
                mode="hybrid",
                top_k=4,
                rerank=True,
            )

            resp = await ChatService.send_chat_message(
                session=session,
                repository_id=repo.id,
                request=chat_req,
                user=user,
            )

            evidence = resp.retrieval_evidence.model_dump() if resp.retrieval_evidence else {}
            context_chunks = [c.model_dump() for c in resp.context_chunks]

            q_data = {
                "query": q,
                "intent": resp.intent,
                "grounding_status": resp.grounding_status,
                "provider": resp.provider,
                "is_mock": resp.is_mock,
                "citations": [c.model_dump() for c in resp.citations],
                "retrieved_chunks": context_chunks,
                "retrieval_evidence": evidence,
                "answer": resp.content,
            }
            results.append(q_data)

            print(f"Grounding Status : {resp.grounding_status}")
            print(f"Intent           : {resp.intent}")
            print(f"Provider         : {resp.provider} (is_mock={resp.is_mock})")
            print(f"\nTop Retrieved Chunks ({len(context_chunks)}):")
            for idx, c in enumerate(context_chunks, 1):
                sym = c.get('symbol_name') or 'N/A'
                sym_type = c.get('symbol_type') or 'FILE'
                rerank_score = c.get('score', 0.0)
                print(f"  {idx}. {c.get('file_path')}:{c.get('start_line')}-{c.get('end_line')} | Symbol: {sym} ({sym_type}) | Score: {rerank_score:.4f}")

            print(f"\nCitations Emitted ({len(resp.citations)}):")
            for cit in resp.citations:
                valid_str = "VALID" if cit.is_valid else "INVALID"
                print(f"  - [{cit.file_path}:L{cit.start_line}-L{cit.end_line}] -> {valid_str} (Conf: {cit.confidence:.2f}, Reason: {cit.validation_reason})")

            print(f"\nGenerated Answer:")
            print(resp.content)
            print("-" * 80)

        with open("tests/rag_quality_output.json", "w") as f:
            json.dump(results, f, indent=2)
        print("\nSaved full verification results to tests/rag_quality_output.json")

if __name__ == "__main__":
    asyncio.run(main())
