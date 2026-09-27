import pytest
from apps.api.app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_token,
)


def test_password_hashing():
    pw = "SuperSecurePassword123!"
    hashed = hash_password(pw)
    assert hashed != pw
    assert verify_password(pw, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_access_token_generation_and_decoding():
    user_id = "user_12345"
    token = create_access_token(subject=user_id, role="ADMIN")
    payload = decode_token(token)

    assert payload["sub"] == user_id
    assert payload["role"] == "ADMIN"
    assert payload["type"] == "access"
    assert "exp" in payload
    assert "jti" in payload


def test_refresh_token_generation_and_hashing():
    user_id = "user_67890"
    token = create_refresh_token(subject=user_id)
    payload = decode_token(token)

    assert payload["sub"] == user_id
    assert payload["type"] == "refresh"

    thash1 = hash_token(token)
    thash2 = hash_token(token)
    assert thash1 == thash2
    assert len(thash1) == 64  # SHA-256 hex string
