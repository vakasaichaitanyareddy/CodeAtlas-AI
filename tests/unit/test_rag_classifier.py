import pytest
from packages.rag.classifier import QueryClassifier
from packages.rag.models import QueryIntent


def test_query_classifier_intents():
    classifier = QueryClassifier()

    # 1. Dependency
    q_dep = classifier.analyze_query("What calls the verify_jwt_token function?")
    assert q_dep.intent == QueryIntent.DEPENDENCY
    assert "verify_jwt_token" in q_dep.target_symbols

    # 2. Impact
    q_imp = classifier.analyze_query("What breaks if I change calculate_tax in models.py?")
    assert q_imp.intent == QueryIntent.IMPACT
    assert "calculate_tax" in q_imp.target_symbols
    assert any("models.py" in f for f in q_imp.file_patterns)

    # 3. Architecture
    q_arch = classifier.analyze_query("Explain the high-level architecture and data flow of the payment pipeline.")
    assert q_arch.intent == QueryIntent.ARCHITECTURE

    # 4. Documentation
    q_doc = classifier.analyze_query("How do I setup and run the project locally with docker-compose?")
    assert q_doc.intent == QueryIntent.DOCUMENTATION

    # 5. Factual Code
    q_fact = classifier.analyze_query("Where is the UserAuthenticationService class implemented?")
    assert q_fact.intent == QueryIntent.FACTUAL_CODE
    assert "UserAuthenticationService" in q_fact.target_symbols


def test_query_classifier_entity_extraction():
    classifier = QueryClassifier()

    res = classifier.analyze_query("Inspect processPaymentRequest and refund_customer_balance in apps/billing/service.py")
    assert "processPaymentRequest" in res.target_symbols
    assert "refund_customer_balance" in res.target_symbols
    assert any("service.py" in f for f in res.file_patterns)
    # Check expanded keywords
    assert "process" in res.expanded_terms or "payment" in res.expanded_terms
