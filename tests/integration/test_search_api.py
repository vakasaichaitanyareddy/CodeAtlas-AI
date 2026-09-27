import os
import tempfile
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from workers.tasks.ingestion import run_ingestion_pipeline


@pytest.mark.asyncio
async def test_search_api_hybrid_retrieval_and_multitenancy(client: AsyncClient, db_session: AsyncSession):
    # 1. Register User A and create Repository A
    res_a = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "search_user_a@codeatlas.dev",
            "password": "Password123!",
            "full_name": "Search Alpha",
        },
    )
    token_a = res_a.json()["tokens"]["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    create_a = await client.post(
        "/api/v1/repositories",
        json={
            "github_url": "https://github.com/search-org/payment-service.git",
            "default_branch": "main",
        },
        headers=headers_a,
    )
    assert create_a.status_code == 201
    repo_a = create_a.json()
    repo_a_id = repo_a["id"]

    # 2. Register User B (for cross-tenant attack verification)
    res_b = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "search_user_b@codeatlas.dev",
            "password": "Password123!",
            "full_name": "Search Beta",
        },
    )
    token_b = res_b.json()["tokens"]["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 3. Populate Repository A with real code chunks
    with tempfile.TemporaryDirectory() as temp_dir:
        auth_file = os.path.join(temp_dir, "auth_service.py")
        with open(auth_file, "w", encoding="utf-8") as f:
            f.write('''
import jwt

SECRET_KEY = "super-secret"

def verify_jwt_signature(token: str):
    """Verify cryptographic JWT signature and return payload."""
    payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    return payload

def revoke_user_session(user_id: str):
    """Revoke all active sessions for a user."""
    return True
''')

        billing_file = os.path.join(temp_dir, "billing_service.py")
        with open(billing_file, "w", encoding="utf-8") as f:
            f.write('''
class StripePaymentGateway:
    """Gateway for communicating with the Stripe API."""
    def charge_credit_card(self, customer_id: str, amount_usd: float):
        """Execute a credit card charge via Stripe."""
        return {"status": "succeeded", "amount": amount_usd}

def refund_transaction(transaction_id: str):
    """Issue a full refund for a previous transaction."""
    return {"refunded": True}
''')

        await run_ingestion_pipeline(
            repository_id=repo_a_id,
            commit_sha="c0ffee123456",
            source_directory=temp_dir,
            session=db_session,
        )

    # 4. Verify Hybrid Search Mode (RRF + Reranker)
    search_hybrid = await client.post(
        f"/api/v1/repositories/{repo_a_id}/search",
        json={
            "query": "verify_jwt_signature token",
            "mode": "hybrid",
            "top_k": 5,
            "rerank": True,
        },
        headers=headers_a,
    )
    assert search_hybrid.status_code == 200
    res_data = search_hybrid.json()
    assert res_data["query"] == "verify_jwt_signature token"
    assert res_data["mode"] == "hybrid"
    assert len(res_data["results"]) > 0
    top_hit = res_data["results"][0]
    assert "verify_jwt_signature" in top_hit["content"]
    assert top_hit["file_path"] == "auth_service.py"
    assert top_hit["score"] > 0

    # 5. Verify Lexical Search Mode (BM25 only)
    search_lexical = await client.post(
        f"/api/v1/repositories/{repo_a_id}/search",
        json={
            "query": "charge_credit_card Stripe",
            "mode": "lexical",
            "top_k": 5,
            "rerank": False,
        },
        headers=headers_a,
    )
    assert search_lexical.status_code == 200
    res_lex = search_lexical.json()
    assert res_lex["mode"] == "lexical"
    assert len(res_lex["results"]) > 0
    assert any("charge_credit_card" in hit["content"] for hit in res_lex["results"])

    # 6. Verify Semantic Search Mode (Dense vector only)
    search_semantic = await client.post(
        f"/api/v1/repositories/{repo_a_id}/search",
        json={
            "query": "cryptographic token decoding",
            "mode": "semantic",
            "top_k": 5,
            "rerank": False,
        },
        headers=headers_a,
    )
    assert search_semantic.status_code == 200
    res_sem = search_semantic.json()
    assert res_sem["mode"] == "semantic"
    assert len(res_sem["results"]) > 0

    # 7. Verify Symbol Type Filtering
    search_filtered = await client.post(
        f"/api/v1/repositories/{repo_a_id}/search",
        json={
            "query": "Stripe",
            "mode": "hybrid",
            "symbol_type": "CLASS",
            "top_k": 5,
            "rerank": False,
        },
        headers=headers_a,
    )
    assert search_filtered.status_code == 200
    filtered_hits = search_filtered.json()["results"]
    for hit in filtered_hits:
        assert hit["symbol_type"] == "CLASS"

    # 8. Cross-Tenant Security Isolation Attack:
    # User B attempts to search Repository A -> 403 Forbidden
    cross_attack = await client.post(
        f"/api/v1/repositories/{repo_a_id}/search",
        json={
            "query": "jwt token secret",
            "mode": "hybrid",
            "top_k": 5,
        },
        headers=headers_b,
    )
    assert cross_attack.status_code == 403
    assert cross_attack.json()["error"]["code"] == "FORBIDDEN_REPOSITORY_ACCESS"
