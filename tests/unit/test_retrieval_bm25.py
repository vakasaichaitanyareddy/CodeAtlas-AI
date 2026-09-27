from packages.retrieval.bm25 import BM25Index


def test_bm25_lexical_indexing_and_search():
    chunks = [
        {
            "id": "chunk-1",
            "file_path": "services/auth.py",
            "symbol_name": "AuthService.verify_jwt_token",
            "symbol_type": "METHOD",
            "content": "def verify_jwt_token(token: str):\n    payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])\n    return payload",
            "start_line": 10,
            "end_line": 15,
        },
        {
            "id": "chunk-2",
            "file_path": "services/payment.py",
            "symbol_name": "PaymentService.process_stripe_charge",
            "symbol_type": "METHOD",
            "content": "def process_stripe_charge(amount_cents: int, customer_id: str):\n    stripe.Charge.create(amount=amount_cents, customer=customer_id)",
            "start_line": 20,
            "end_line": 25,
        },
        {
            "id": "chunk-3",
            "file_path": "models/user.py",
            "symbol_name": "UserModel",
            "symbol_type": "CLASS",
            "content": "class UserModel:\n    id: int\n    email: str\n    hashed_password: str",
            "start_line": 1,
            "end_line": 10,
        },
    ]

    index = BM25Index(chunks)

    # 1. Search for jwt token
    jwt_results = index.search("verify_jwt_token", top_k=5)
    assert len(jwt_results) > 0
    assert jwt_results[0].chunk_id == "chunk-1"
    assert jwt_results[0].symbol_name == "AuthService.verify_jwt_token"
    assert jwt_results[0].score > 0.0

    # 2. Search for stripe payment
    stripe_results = index.search("stripe charge customer", top_k=5)
    assert len(stripe_results) > 0
    assert stripe_results[0].chunk_id == "chunk-2"
    assert stripe_results[0].symbol_name == "PaymentService.process_stripe_charge"

    # 3. Empty query returns empty list
    empty_results = index.search("", top_k=5)
    assert empty_results == []


def test_bm25_empty_index():
    index = BM25Index([])
    assert index.search("anything") == []
