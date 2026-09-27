from packages.retrieval.tokenizer import CodeTokenizer


def test_code_tokenizer_camel_case_splitting():
    tokens = CodeTokenizer.tokenize("getUserProfile")
    assert "getuserprofile" in tokens
    assert "get" in tokens
    assert "user" in tokens
    assert "profile" in tokens


def test_code_tokenizer_snake_case_splitting():
    tokens = CodeTokenizer.tokenize("process_payment_event")
    assert "process_payment_event" in tokens
    assert "process" in tokens
    assert "payment" in tokens
    assert "event" in tokens


def test_code_tokenizer_mixed_code_snippet():
    code = """
    class OrderController:
        async def handle_checkout_request(self, cart_id: str):
            return orderService.processPayment(cart_id)
    """
    tokens = CodeTokenizer.tokenize(code)
    # Check compound symbols
    assert "ordercontroller" in tokens
    assert "handle_checkout_request" in tokens
    assert "orderservice" in tokens
    assert "processpayment" in tokens

    # Check split sub-tokens
    assert "order" in tokens
    assert "controller" in tokens
    assert "checkout" in tokens
    assert "payment" in tokens


def test_code_tokenizer_empty_and_stop_words():
    assert CodeTokenizer.tokenize("") == []
    assert CodeTokenizer.tokenize("   ") == []
    # Test only stop words
    assert CodeTokenizer.tokenize("the a an and or in on at to") == []
